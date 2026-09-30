"""Alerte précoce climat-conflit : docs/data/early_warning.js (onglet « Alerte précoce »).

Pour chaque région suivie (config/early_warning.json), la carte est découpée en unités administratives
(niveau 1 : régions, États, provinces) et croise, mois par mois :
  - le climat      : précipitations, température, humidité du sol – NASA POWER (MERRA-2, API publique, sans clé),
                     comparés aux mêmes mois des 15 années précédentes (moyenne, minimum, maximum) ;
  - la sécurité    : incidents Angor (tous, et ceux liés aux ressources : eau, terres, bétail, pêche…),
                     complétés par la base historique (UCDP, GDELT) si elle est présente ;
  - l'humanitaire  : insécurité alimentaire (part de la population en phase IPC 3+) et personnes déplacées,
                     via HDX HAPI (OCHA, API publique) ;
et en déduit un indice expérimental de convergence des risques (0-100) avec ses facteurs explicatifs.
Limites des unités : geoBoundaries (William & Mary geoLab, CC BY 4.0), simplifiées.

Rythme : les données sont mensuelles. Chaque collecte avance un peu (30 unités NASA POWER par passage,
HDX HAPI chaque semaine), la mémoire est gardée dans data/early_warning.json.
"""
import calendar
import difflib
import gzip
import json
import math
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, http
from .publish import write_js

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "early_warning.json"
HISTORY_PARTS = ROOT / "history_parts"
GB_URL = ("https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/"
          "{iso3}/ADM1/geoBoundaries-{iso3}-ADM1_simplified.geojson")
POWER_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
HAPI = "https://hapi.humdata.org/api/v2"
SECURITY_CATS = {"terrorism", "armed_conflict", "attack", "unrest", "crime"}
RESOURCE_WORDS = ["pastoral", "herder", "herders", "farmer", "farmers", "cattle", "livestock", "grazing", "pasture",
                  "water", "well", "wells", "land dispute", "land", "fishing", "fishermen", "transhumance", "camel",
                  "cow", "cows", "goats", "rustling", "rustlers", "charcoal", "gold mine", "artisanal mining",
                  "eleveur", "eleveurs", "agriculteur", "agriculteurs", "cultivateur", "betail", "troupeau", "paturage",
                  "point d'eau", "puits", "foncier", "terres", "pecheur", "pecheurs", "orpaillage", "orpailleur",
                  "ganado", "agua", "tierra", "vol de betail", "cattle raid", "abigeato"]
ADMIN_ALIASES = {"gezira": "aj jazirah", "al jazirah": "aj jazirah", "abuja federal capital territory": "federal capital territory",
                 "far north": "far north", "extreme nord": "far north", "tombouctou": "timbuktu", "segou": "segou"}
DEFAULT_REGIONS = {
    "horn": {"fr": "Corne de l'Afrique", "en": "Horn of Africa", "countries": ["DJ", "ER", "ET", "KE", "SO", "SS", "SD", "UG"]},
    "sahel": {"fr": "Sahel et bassin du lac Tchad", "en": "Sahel & Lake Chad Basin",
              "countries": ["ML", "BF", "NE", "TD", "MR", "NG", "CM"]},
}


# ------------------------------------------------------------------ outils
def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(region|state|province|county|governorate|prefecture|district|city|zone|wilaya|etat|regional)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _month_key(d):
    return f"{d.year:04d}-{d.month:02d}"


def _months_back(end_ym, n):
    y, m = int(end_ym[:4]), int(end_ym[5:7])
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


def _dp(points, tol):
    """Douglas-Peucker itératif sur une liste de [lon, lat]."""
    if len(points) < 4:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = points[a]
        bx, by = points[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-12
        best, idx = 0.0, None
        for i in range(a + 1, b):
            px, py = points[i]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / norm if (dx or dy) else math.hypot(px - ax, py - ay)
            if d > best:
                best, idx = d, i
        if idx is not None and best > tol:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(points, keep) if k]


def _ring_area(r):
    return 0.5 * sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1))


def simplify_geometry(geom, tol):
    """Polygon / MultiPolygon GeoJSON → liste de polygones [[anneau extérieur, trous…]], coordonnées arrondies."""
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    out = []
    for poly in polys:
        rings = []
        for k, ring in enumerate(poly):
            r = _dp([[round(x, 4), round(y, 4)] for x, y in ring[:]], tol)
            if len(r) < 4 or abs(_ring_area(r)) < (tol * tol * 4 if k == 0 else tol * tol * 20):
                if k == 0:
                    break
                continue
            rings.append([[round(x, 3), round(y, 3)] for x, y in r])
        if rings:
            out.append(rings)
    if not out:  # très petite unité : on garde l'enveloppe brute de son plus grand polygone
        big = max(polys, key=lambda p: abs(_ring_area(p[0])))
        out = [[[[round(x, 3), round(y, 3)] for x, y in big[0]]]]
    return out


def centroid(polys):
    """Centre de gravité du plus grand polygone (point représentatif pour la météo)."""
    ring = max((p[0] for p in polys), key=lambda r: abs(_ring_area(r)))
    a = _ring_area(ring)
    if abs(a) < 1e-9:
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        return [round(sum(ys) / len(ys), 3), round(sum(xs) / len(xs), 3)]
    cx = sum((ring[i][0] + ring[i + 1][0]) * (ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]) for i in range(len(ring) - 1)) / (6 * a)
    cy = sum((ring[i][1] + ring[i + 1][1]) * (ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]) for i in range(len(ring) - 1)) / (6 * a)
    if not point_in_polys(cx, cy, polys):  # forme concave : on prend un sommet médian
        cx, cy = ring[len(ring) // 2]
    return [round(cy, 3), round(cx, 3)]


def _in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def point_in_polys(x, y, polys):
    return any(_in_ring(x, y, p[0]) and not any(_in_ring(x, y, h) for h in p[1:]) for p in polys)


def bbox(polys):
    xs = [pt[0] for p in polys for pt in p[0]]
    ys = [pt[1] for p in polys for pt in p[0]]
    return [min(xs), min(ys), max(xs), max(ys)]


# ------------------------------------------------------------------ limites administratives
def load_units(countries, regions, cache, log, tol):
    units = cache.setdefault("units", {})
    have = {u["iso"] for u in units.values()}
    for rid, reg in regions.items():
        for iso in reg["countries"]:
            if iso in have:
                continue
            item = countries.get(iso)
            if not item:
                continue
            try:
                gj = http.get_json(GB_URL.format(iso3=item["iso3"]), timeout=90)
            except Exception as exc:
                log(f"  Alerte précoce : limites de {iso} indisponibles ({type(exc).__name__})")
                continue
            n = 0
            for f in gj.get("features", []):
                p = f.get("properties") or {}
                name = p.get("shapeName") or p.get("shapeISO") or "?"
                uid = f"{iso}-{_norm(name).replace(' ', '-')[:40] or n}"
                polys = simplify_geometry(f["geometry"], tol)
                units[uid] = {"id": uid, "iso": iso, "n": name, "code": p.get("shapeISO") or "", "g": polys,
                              "c": centroid(polys), "bb": bbox(polys)}
                n += 1
            log(f"  Alerte précoce : {n} unité(s) administrative(s) pour {item['name_fr'] or iso}")
            have.add(iso)
    for u in units.values():
        u["reg"] = next((rid for rid, reg in regions.items() if u["iso"] in reg["countries"]), None)
    return units


def locate_unit(units_by_iso, iso, lat, lon):
    for u in units_by_iso.get(iso, []):
        x0, y0, x1, y1 = u["bb"]
        if x0 <= lon <= x1 and y0 <= lat <= y1 and point_in_polys(lon, lat, u["g"]):
            return u["id"]
    return None


# ------------------------------------------------------------------ climat (NASA POWER)
def power_fetch(lat, lon, start_year, end_year):
    params = {"parameters": "PRECTOTCORR,T2M,GWETROOT", "community": "AG", "longitude": lon, "latitude": lat,
              "start": start_year, "end": end_year, "format": "JSON"}
    data = http.get_json(POWER_URL, params=params, timeout=60)
    par = (data.get("properties") or {}).get("parameter") or {}
    fill = (data.get("header") or {}).get("fill_value", -999)
    out = {}
    for key, short in (("PRECTOTCORR", "P"), ("T2M", "T"), ("GWETROOT", "W")):
        vals = {}
        for ym, v in (par.get(key) or {}).items():
            if len(ym) != 6 or ym[4:] == "13" or v is None or v == fill or v <= -990:
                continue
            y, m = int(ym[:4]), int(ym[4:])
            if short == "P":  # mm/jour → mm/mois
                v = v * calendar.monthrange(y, m)[1]
            vals[f"{y:04d}-{m:02d}"] = round(v, 2)
        out[short] = vals
    return out


def update_climate(units, cache, now, log, per_run, refresh_days):
    clim = cache.setdefault("climate", {})
    last_month = _month_key((now.replace(day=1) - timedelta(days=1)))
    todo = []
    for u in units.values():
        c = clim.get(u["id"]) or {}
        age = (now - datetime.fromisoformat(c["fetched"])).days if c.get("fetched") else 999
        has_last = last_month in ((c.get("data") or {}).get("P") or {})
        if age >= refresh_days or (not has_last and age >= 2 and now.day >= 6):
            todo.append((c.get("fetched", ""), u["id"]))
    todo.sort()
    todo = [uid for _, uid in todo[:per_run]]
    if not todo:
        return 0

    def one(uid):
        u = units[uid]
        try:
            return uid, power_fetch(u["c"][0], u["c"][1], now.year - 15, now.year), None
        except Exception as exc:
            return uid, None, f"{type(exc).__name__}"
    ok, errs = 0, []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for uid, data, err in pool.map(one, todo):
            if data:
                clim[uid] = {"fetched": now.isoformat(), "data": data}
                ok += 1
            else:
                errs.append(err)
    log(f"  Alerte précoce : climat NASA POWER mis à jour pour {ok}/{len(todo)} unité(s)"
        + (f" ({errs[0]})" if errs else ""))
    return ok


def climate_stats(series, months):
    """Valeurs des 12 mois affichés + moyenne, minimum et maximum des mêmes mois les années précédentes."""
    v, avg, mn, mx = [], [], [], []
    for ym in months:
        v.append(series.get(ym))
        prev = [series[f"{int(ym[:4]) - k:04d}{ym[4:]}"] for k in range(1, 16) if f"{int(ym[:4]) - k:04d}{ym[4:]}" in series]
        avg.append(round(sum(prev) / len(prev), 2) if prev else None)
        mn.append(min(prev) if prev else None)
        mx.append(max(prev) if prev else None)
    return {"v": v, "avg": avg, "min": mn, "max": mx}


# ------------------------------------------------------------------ humanitaire (HDX HAPI)
def hapi_rows(path, params, app_id):
    rows, offset = [], 0
    while True:
        q = dict(params, app_identifier=app_id, output_format="json", limit=1000, offset=offset)
        data = http.get_json(f"{HAPI}/{path}", params=q, timeout=60)
        batch = data.get("data") or []
        rows += batch
        if len(batch) < 1000:
            return rows
        offset += 1000


def update_humanitarian(countries, regions, cache, now, log, refresh_days, app_id):
    hum = cache.setdefault("humanitarian", {})
    start = (now - timedelta(days=550)).date().isoformat()
    done, failed = 0, []
    for reg in regions.values():
        for iso in reg["countries"]:
            h = hum.get(iso) or {}
            if h.get("fetched") and (now - datetime.fromisoformat(h["fetched"])).days < refresh_days:
                continue
            item = countries.get(iso)
            if not item:
                continue
            iso3 = item["iso3"]
            out = {"fetched": now.isoformat(), "ipc": {}, "idp": {}, "pop": {}}
            try:
                for r in hapi_rows("food-security-nutrition-poverty/food-security",
                                   {"location_code": iso3, "admin_level": 1, "ipc_phase": "3+", "ipc_type": "current",
                                    "start_date": start}, app_id):
                    k = r.get("admin1_name") or ""
                    if k and (k not in out["ipc"] or r["reference_period_end"] > out["ipc"][k]["e"]):
                        out["ipc"][k] = {"v": r.get("population_fraction_in_phase"), "n": r.get("population_in_phase"),
                                         "e": (r.get("reference_period_end") or "")[:10]}
                for r in hapi_rows("affected-people/idps", {"location_code": iso3, "admin_level": 1, "start_date": start}, app_id):
                    k = r.get("admin1_name") or ""
                    if k and (k not in out["idp"] or r["reference_period_end"] > out["idp"][k]["e"]):
                        out["idp"][k] = {"v": r.get("population"), "e": (r.get("reference_period_end") or "")[:10]}
                for r in hapi_rows("geography-infrastructure/baseline-population",
                                   {"location_code": iso3, "admin_level": 1, "gender": "all", "age_range": "all"}, app_id):
                    k = r.get("admin1_name") or ""
                    if k and (k not in out["pop"] or r["reference_period_end"] > out["pop"][k]["e"]):
                        out["pop"][k] = {"v": r.get("population"), "e": (r.get("reference_period_end") or "")[:10]}
            except Exception as exc:
                failed.append(f"{iso} ({type(exc).__name__})")
                continue
            hum[iso] = out
            done += 1
    if done:
        log(f"  Alerte précoce : données humanitaires HDX HAPI mises à jour pour {done} pays")
    if failed:
        log(f"  Alerte précoce : HDX HAPI indisponible pour {', '.join(failed[:5])}{' …' if len(failed) > 5 else ''}")


def match_admin(name, table):
    """Rapproche un nom d'unité geoBoundaries d'un nom HDX (« Tillabéri » ~ « Tillaberi », « Far North » ~ « Far-North »)."""
    if not table:
        return None
    key = _norm(name)
    norm = {_norm(k): k for k in table}
    if key in norm:
        return table[norm[key]]
    for nk, k in norm.items():
        if nk and (nk.replace(" ", "") == key.replace(" ", "") or (len(nk) > 4 and len(key) > 4 and (
                nk.startswith(key) or key.startswith(nk) or nk.endswith(" " + key) or key.endswith(" " + nk)))):
            return table[k]
    alias = ADMIN_ALIASES.get(key)
    if alias and alias in norm:
        return table[norm[alias]]
    close = difflib.get_close_matches(key, list(norm), n=1, cutoff=0.8)
    return table[norm[close[0]]] if close else None


# ------------------------------------------------------------------ sécurité
def _is_resource(title):
    t = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode().lower()
    return any(re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", t) for w in RESOURCE_WORDS)


def update_security(units, cache, events, now, log):
    """Comptage mensuel des incidents par unité. Les identifiants déjà comptés sont mémorisés : la série
    s'allonge de collecte en collecte au-delà de la durée de conservation de la carte (95 jours)."""
    sec = cache.setdefault("security", {})   # "YYYY-MM" → {unit: [nb, nb ressources]}
    seen = cache.setdefault("security_seen", {})  # "YYYY-MM" → [ids]
    by_iso = {}
    for u in units.values():
        by_iso.setdefault(u["iso"], []).append(u)
    isos = set(by_iso)
    added = 0
    for e in events:
        if e.get("category") not in SECURITY_CATS or e.get("country") not in isos or e.get("lat") is None:
            continue
        ym = e["date"][:7]
        ids = seen.setdefault(ym, [])
        if e["id"] in ids:
            continue
        uid = locate_unit(by_iso, e["country"], e["lat"], e["lon"])
        if not uid:
            continue
        ids.append(e["id"])
        row = sec.setdefault(ym, {}).setdefault(uid, [0, 0])
        row[0] += 1
        if _is_resource(e.get("title", "")):
            row[1] += 1
        added += 1
    # base historique (UCDP, GDELT) : une fois, pour les mois antérieurs aux premiers comptages en direct
    if HISTORY_PARTS.exists() and cache.get("history_done_v2") != sorted(isos):
        n = backfill_history(by_iso, sec, now)
        cache["history_done_v2"] = sorted(isos)  # v2 : 4 ans d'historique (validation sur le Soudan 2023)
        if n:
            log(f"  Alerte précoce : {n} incident(s) historiques rattachés aux unités administratives")
    cutoff = _month_key(now - timedelta(days=1900))
    for d in (sec, seen):
        for ym in [k for k in d if k < cutoff]:
            d.pop(ym)
    return added


def backfill_history(by_iso, sec, now):
    live_months = {ym for ym, units in sec.items() if units and ym >= _month_key(now - timedelta(days=100))}
    first_live = min(live_months) if live_months else _month_key(now)
    for ym in [k for k in sec if k < first_live]:  # on reconstruit l'historique ancien (pas de double comptage)
        sec.pop(ym)
    start = _month_key(now - timedelta(days=1830))
    n = 0
    for f in [HISTORY_PARTS / "ucdp.json.gz", HISTORY_PARTS / "gdelt.json.gz"]:
        if not f.exists():
            continue
        try:
            recs = json.loads(gzip.decompress(f.read_bytes()))
        except Exception:
            continue
        for r in recs:
            ym = (r.get("t") or "")[:7]
            if not ym or ym < start or ym >= first_live or r.get("cat") not in SECURITY_CATS:
                continue
            iso, lat, lon = r.get("iso"), r.get("lat"), r.get("lon")
            if iso not in by_iso or lat is None:
                continue
            uid = locate_unit(by_iso, iso, lat, lon)
            if not uid:
                continue
            row = sec.setdefault(ym, {}).setdefault(uid, [0, 0])
            row[0] += 1
            if _is_resource(r.get("title", "")):
                row[1] += 1
            n += 1
    return n


# ------------------------------------------------------------------ indice de convergence
def score_unit(clim, sec_all, sec_res, hum):
    """Indice expérimental 0-100 (climat 40 · sécurité 35 · humanitaire 25) et facteurs explicatifs."""
    drivers = []
    cl = 0
    p = clim.get("P") or {}
    if p:
        v3 = [x for x in p["v"][-3:] if x is not None]
        a3 = [x for x in p["avg"][-3:] if x is not None]
        if len(v3) == 3 and len(a3) == 3 and sum(a3) >= 30:
            ratio = sum(v3) / sum(a3)
            if ratio < 0.5:
                cl += 25
            elif ratio < 0.7:
                cl += 15
            elif ratio < 0.85:
                cl += 7
            elif ratio > 1.8:
                cl += 15
            elif ratio > 1.4:
                cl += 8
            if ratio < 0.85:
                drivers.append(["rain_deficit", round(ratio * 100)])
            elif ratio > 1.4:
                drivers.append(["rain_excess", round(ratio * 100)])
    t = clim.get("T") or {}
    if t:
        d = [v - a for v, a in zip(t["v"][-3:], t["avg"][-3:]) if v is not None and a is not None]
        if d:
            anom = sum(d) / len(d)
            if anom > 1.5:
                cl += 10
            elif anom > 0.8:
                cl += 5
            if anom > 0.8:
                drivers.append(["heat", round(anom, 1)])
    w = clim.get("W") or {}
    if w and w["v"] and w["v"][-1] is not None and w["avg"][-1] is not None:
        if w["min"][-1] is not None and w["v"][-1] < w["min"][-1]:
            cl += 5
            drivers.append(["soil_record", round(w["v"][-1], 2)])
        elif w["v"][-1] < w["avg"][-1] - 0.1:
            cl += 3
            drivers.append(["soil_dry", round(w["v"][-1] - w["avg"][-1], 2)])
    cl = min(cl, 40)
    co = 0
    n3 = sum(sec_all[-3:])
    base = sum(sec_all[:-3]) / max(1, len(sec_all) - 3) * 3 if len(sec_all) > 3 else 0
    if n3 >= 30:
        co += 20
    elif n3 >= 10:
        co += 14
    elif n3 >= 3:
        co += 8
    elif n3 >= 1:
        co += 3
    if n3 >= 3 and base > 0 and n3 / base >= 1.5:
        co += 10
        drivers.append(["conflict_up", round((n3 / base - 1) * 100)])
    elif n3 >= 3 and base > 0 and n3 / base >= 1.2:
        co += 5
        drivers.append(["conflict_up", round((n3 / base - 1) * 100)])
    elif n3 >= 3 and base == 0:
        co += 8
        drivers.append(["conflict_new", n3])
    if n3 >= 1:
        drivers.append(["incidents", n3])
    r3 = sum(sec_res[-3:])
    if r3:
        co += 5
        drivers.append(["resource", r3])
    co = min(co, 35)
    hu = 0
    ipc = hum.get("ipc3")
    if ipc is not None:
        hu += 15 if ipc >= 0.4 else 10 if ipc >= 0.25 else 5 if ipc >= 0.15 else 0
        if ipc >= 0.15:
            drivers.append(["ipc", round(ipc * 100)])
    idp, pop = hum.get("idp"), hum.get("pop")
    if idp:
        share = idp / pop if pop else None
        if share is not None:
            hu += 10 if share >= 0.1 else 6 if share >= 0.03 else 2
        else:
            hu += 6 if idp >= 100000 else 2
        if idp >= 20000:
            drivers.append(["idp", idp])
    hu = min(hu, 25)
    total = cl + co + hu
    level = 4 if total >= 60 else 3 if total >= 40 else 2 if total >= 20 else 1
    return {"v": total, "lvl": level, "cl": cl, "co": co, "hu": hu, "dr": drivers}


# ------------------------------------------------------------------ assemblage
def load_cache():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def update(store, countries, events, settings, log, now=None):
    now = now or datetime.now(timezone.utc)
    cfg = config.load_json("early_warning.json", {}) or {}
    if cfg.get("enabled") is False:
        return None
    regions = cfg.get("regions") or DEFAULT_REGIONS
    cache = load_cache()
    units = load_units(countries, regions, cache, log, float(cfg.get("simplify_tolerance", 0.015)))
    if not units:
        return None
    update_climate(units, cache, now, log, int(cfg.get("power_per_run", 30)), int(cfg.get("power_refresh_days", 10)))
    app_id = cfg.get("hapi_app_identifier") or "YW5nb3ItaW50ZWxsaWdlbmNlOmNvbnRhY3RAYW5nb3IuZnI="
    update_humanitarian(countries, regions, cache, now, log, int(cfg.get("hapi_refresh_days", 7)), app_id)
    update_security(units, cache, events, now, log)
    save_cache(cache)
    return build(units, cache, regions, now, countries)


def backtest(units, cache, now, months_back=40, horizon=3):
    """Validation a posteriori de l'indice : pour chaque unité et chaque mois passé, indice calculé avec les seules
    données disponibles à ce moment (climat + sécurité ; l'humanitaire n'a pas d'historique ici), puis on regarde si les
    incidents ont nettement augmenté dans les 3 mois suivants (≥ 1,5 fois le rythme des 12 mois précédents et ≥ 3).
    Un indice utile doit montrer un taux d'aggravation croissant avec le niveau."""
    clim_all = cache.get("climate") or {}
    sec = cache.get("security") or {}
    if len(sec) < 18:
        return None
    end = _month_key(now.replace(day=1) - timedelta(days=1))
    all_months = _months_back(end, months_back + horizon + 15)
    stats = {lvl: [0, 0] for lvl in (1, 2, 3, 4)}
    cases = []
    for u in units.values():
        data = (clim_all.get(u["id"]) or {}).get("data") or {}
        counts = [((sec.get(ym) or {}).get(u["id"]) or [0, 0]) for ym in all_months]
        for k in range(15, len(all_months) - horizon):
            m = all_months[k]
            if m < min(sec):
                continue
            win = all_months[k - 11:k + 1]
            clim = {key: climate_stats(data.get(key) or {}, win) for key in ("P", "T", "W") if data.get(key)}
            s_all = [c[0] for c in counts[k - 14:k + 1]]
            s_res = [c[1] for c in counts[k - 14:k + 1]]
            sc = score_unit(clim, s_all, s_res, {})
            v = round(sc["v"] * 100 / 75)  # sans la part humanitaire (25 points)
            lvl = 4 if v >= 60 else 3 if v >= 40 else 2 if v >= 20 else 1
            before = sum(s_all[-12:]) / 12 * horizon
            after = sum(c[0] for c in counts[k + 1:k + 1 + horizon])
            esc = after >= 3 and after >= 1.5 * max(before, 1)
            stats[lvl][0] += 1
            stats[lvl][1] += 1 if esc else 0
            if esc and lvl >= 3 and len(cases) < 400:
                cases.append([u["id"], m, v, after])
    n = sum(v[0] for v in stats.values())
    if not n:
        return None
    base = sum(v[1] for v in stats.values()) / n
    return {"period": [all_months[15], all_months[-horizon - 1]], "horizon_months": horizon, "unit_months": n,
            "base_rate": round(base, 3),
            "by_level": {str(k): {"n": v[0], "rate": round(v[1] / v[0], 3) if v[0] else None} for k, v in stats.items()},
            "hits": cases[-40:]}


def build(units, cache, regions, now, countries):
    clim_all = cache.get("climate") or {}
    # dernier mois disponible dans les données climatiques (sinon le mois précédent)
    latest = [max(c["data"]["P"]) for c in clim_all.values() if (c.get("data") or {}).get("P")]
    end = max(latest) if latest else _month_key(now.replace(day=1) - timedelta(days=1))
    months = _months_back(end, 12)
    sec_months = _months_back(_month_key(now), 15)  # sécurité : jusqu'au mois en cours
    sec = cache.get("security") or {}
    hum = cache.get("humanitarian") or {}
    out_units, levels = [], {}
    for u in sorted(units.values(), key=lambda x: (x["iso"], x["n"])):
        data = (clim_all.get(u["id"]) or {}).get("data") or {}
        clim = {k: climate_stats(data.get(k) or {}, months) for k in ("P", "T", "W") if data.get(k)}
        s_all = [((sec.get(ym) or {}).get(u["id"]) or [0, 0])[0] for ym in sec_months]
        s_res = [((sec.get(ym) or {}).get(u["id"]) or [0, 0])[1] for ym in sec_months]
        h = hum.get(u["iso"]) or {}
        ipc = match_admin(u["n"], h.get("ipc"))
        idp = match_admin(u["n"], h.get("idp"))
        pop = match_admin(u["n"], h.get("pop"))
        hu = {"ipc3": ipc["v"] if ipc else None, "ipc_end": ipc["e"] if ipc else None,
              "ipc_n": ipc.get("n") if ipc else None,
              "idp": idp["v"] if idp else None, "idp_end": idp["e"] if idp else None, "pop": pop["v"] if pop else None}
        score = score_unit(clim, s_all, s_res, hu)
        levels[score["lvl"]] = levels.get(score["lvl"], 0) + 1
        out_units.append({"id": u["id"], "iso": u["iso"], "n": u["n"], "reg": u["reg"], "g": u["g"], "c": u["c"],
                          "clim": clim, "sec": {"all": s_all, "res": s_res}, "hum": hu, "score": score})
    regs = {}
    for rid, reg in regions.items():
        bbs = [u["bb"] for u in units.values() if u["reg"] == rid]
        if bbs:
            regs[rid] = {"fr": reg.get("fr", rid), "en": reg.get("en", rid), "countries": reg["countries"],
                         "bbox": [min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs)]}
    # validation a posteriori : recalculée une fois par jour (quelques secondes)
    val = cache.get("validation")
    if not val or val.get("computed", "")[:10] != now.date().isoformat():
        try:
            val = backtest(units, cache, now)
            if val:
                val["computed"] = now.isoformat()
                cache["validation"] = val
                save_cache(cache)
        except Exception:
            val = None
    payload = {"generated": now.isoformat(), "months": months, "sec_months": sec_months, "regions": regs,
               "validation": val,
               "units": out_units, "levels": levels,
               "credits": "NASA POWER (MERRA-2) · HDX HAPI (OCHA : IPC, OIM-DTM, population) · incidents Angor, UCDP, GDELT · "
                          "limites administratives geoBoundaries (CC BY 4.0)"}
    write_js("early_warning.js", "VS_EW", payload)
    return payload
