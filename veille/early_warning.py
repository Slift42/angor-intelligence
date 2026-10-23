"""Alerte précoce par subdivision : le niveau de détail le plus fin des tendances de risques (v0.27).

Les tendances (veille/foresight.py) décrivent les risques par région et par pays ; l'alerte précoce descend au niveau
administratif 1 (régions, États, provinces, gouvernorats) sur le monde entier, avec les mêmes 17 régions
(config/foresight/regions/). Pour chaque subdivision, mois par mois, elle mesure les facteurs observables à cette
échelle, regroupés comme les familles de facteurs des tendances :
  - climat et environnement : précipitations, température, humidité du sol – NASA POWER (MERRA-2, API publique, sans
    clé), comparées aux mêmes mois des 15 années précédentes (moyenne, minimum, maximum) ;
  - terrorisme, conflits et criminalité : incidents vérifiés d'Angor (et ceux liés aux ressources : eau, terres,
    bétail…), complétés par la base historique (UCDP, GDELT) ;
  - société et politique : troubles civils et crises politiques localisés ;
  - aléas, infrastructures et santé : catastrophes naturelles, pannes et cyberattaques, épidémies (gravité 2 et plus) ;
  - crises humanitaires : insécurité alimentaire (IPC 3+) et déplacés, via HDX HAPI (OCHA), là où ces données existent ;
et en déduit un indice de convergence 0-100 (composante humanitaire absente → indice ramené sur 100), avec ses facteurs
explicatifs et une rétro-évaluation sur les crises passées.

Rythme : chaque collecte avance un peu (limites de quelques pays, une quarantaine de subdivisions NASA POWER, quelques
pays HDX HAPI) ; la couverture mondiale se remplit en deux à trois jours, par ordre de priorité des régions
(config/early_warning.json). Mémoire : data/early_warning.json (climat compact, comptages, humanitaire) et
data/ew_units/<ISO2>.json (limites simplifiées, une fois pour toutes). Limites : geoBoundaries (CC BY 4.0).
Sorties : docs/data/early_warning.js (index : régions, mois, validation) et docs/data/early_warning/<région>.js
(subdivisions d'une région, chargées à la demande).
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
from .publish import OUT_DIR, write_js

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "early_warning.json"
UNITS_DIR = ROOT / "data" / "ew_units"
HISTORY_PARTS = ROOT / "history_parts"
GB_URL = ("https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/"
          "{iso3}/ADM1/geoBoundaries-{iso3}-ADM1_simplified.geojson")
POWER_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
HAPI = "https://hapi.humdata.org/api/v2"
CACHE_VERSION = 3
CLIMATE_YEARS = 16

# comptages mensuels par subdivision : une case par famille de facteurs observable à cette échelle
FAMILIES = ("sec", "res", "unrest", "pol", "haz", "infra", "health")
SEC_CATS = {"terrorism", "armed_conflict", "attack", "crime"}
CAT_FAMILY = {**{c: "sec" for c in SEC_CATS}, "unrest": "unrest", "political": "pol",
              **{c: "haz" for c in ("earthquake", "cyclone", "storm", "flood", "wildfire", "volcano", "drought",
                                     "landslide", "extreme_temp")},
              "infrastructure": "infra", "cyber": "infra", "health": "health"}
MIN_SEVERITY = {"haz": 2, "infra": 2, "health": 2}   # aléas courants (petits séismes, orages) : non comptés
# composantes de l'indice : points maximum et famille de facteurs des tendances correspondante
COMPONENTS = {"cl": {"max": 30, "family": "climate", "fr": "Climat et environnement", "en": "Climate & environment"},
              "co": {"max": 30, "family": "security", "fr": "Terrorisme, conflits et criminalité", "en": "Terrorism, conflict & crime"},
              "so": {"max": 15, "family": "social", "fr": "Société et politique", "en": "Society & politics"},
              "hz": {"max": 10, "family": "infrastructure", "fr": "Aléas, infrastructures et santé", "en": "Hazards, infrastructure & health"},
              "hu": {"max": 15, "family": "humanitarian", "fr": "Crises humanitaires", "en": "Humanitarian crises"}}
RESOURCE_WORDS = ["pastoral", "herder", "herders", "farmer", "farmers", "cattle", "livestock", "grazing", "pasture",
                  "water", "well", "wells", "land dispute", "land", "fishing", "fishermen", "transhumance", "camel",
                  "cow", "cows", "goats", "rustling", "rustlers", "charcoal", "gold mine", "artisanal mining",
                  "eleveur", "eleveurs", "agriculteur", "agriculteurs", "cultivateur", "betail", "troupeau", "paturage",
                  "point d'eau", "puits", "foncier", "terres", "pecheur", "pecheurs", "orpaillage", "orpailleur",
                  "ganado", "agua", "tierra", "vol de betail", "cattle raid", "abigeato"]
ADMIN_ALIASES = {"gezira": "aj jazirah", "al jazirah": "aj jazirah", "abuja federal capital territory": "federal capital territory",
                 "far north": "far north", "extreme nord": "far north", "tombouctou": "timbuktu", "segou": "segou"}


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



def _month_index(c, ym):
    return (int(ym[:4]) - c["y0"]) * 12 + int(ym[5:7]) - 1


def _pad(row):
    row = list(row or [])
    return row + [0] * (len(FAMILIES) - len(row))


# ------------------------------------------------------------------ régions (communes avec les tendances)
def regions_config():
    """Régions des tendances de risques : {id: {fr, en, countries, bbox}} (monde entier)."""
    from . import foresight
    return foresight.regions()


def unit_region(u, iso_reg, regions):
    """Région d'une subdivision : celle de son pays, sauf si elle en est loin (outre-mer) : région géographique."""
    rid = iso_reg.get(u["iso"])
    lat, lon = u["c"]

    def inside(bb, margin=0.0):
        return bb[0] - margin <= lon <= bb[2] + margin and bb[1] - margin <= lat <= bb[3] + margin
    if rid and inside(regions[rid]["bbox"], 8):
        return rid
    for k, r in regions.items():
        if inside(r["bbox"]):
            return k
    return rid


# ------------------------------------------------------------------ limites administratives
def _tolerance(geom, base):
    """Simplification adaptée à la taille : une province russe et un canton luxembourgeois n'ont pas la même échelle."""
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    xs = [pt[0] for p in polys for pt in p[0]]
    ys = [pt[1] for p in polys for pt in p[0]]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) if xs else 1
    return max(0.002, min(base, diag / 150))


def fetch_country_units(iso, iso3, base_tol):
    gj = http.get_json(GB_URL.format(iso3=iso3), timeout=90)
    out, ids = [], set()
    for n, f in enumerate(gj.get("features", [])):
        p = f.get("properties") or {}
        if not f.get("geometry"):
            continue
        name = p.get("shapeName") or p.get("shapeISO") or "?"
        uid = f"{iso}-{_norm(name).replace(' ', '-')[:40] or n}"
        if uid in ids:
            uid = f"{uid}-{n}"
        ids.add(uid)
        polys = simplify_geometry(f["geometry"], _tolerance(f["geometry"], base_tol))
        out.append({"id": uid, "iso": iso, "n": name, "code": p.get("shapeISO") or "", "g": polys,
                    "c": centroid(polys), "bb": bbox(polys)})
    return out


def _write_units(iso, payload):
    UNITS_DIR.mkdir(parents=True, exist_ok=True)
    (UNITS_DIR / f"{iso}.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def load_units(countries, regions, cache, log, base_tol, per_run, now, priority=(), events=()):
    """Subdivisions déjà connues (data/ew_units/) + limites de quelques nouveaux pays par collecte, par priorité :
    ordre des régions (config), puis pays où Angor relève le plus d'incidents."""
    units, files = {}, {}
    if UNITS_DIR.exists():
        for f in UNITS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            files[f.stem] = data
            for u in data.get("units") or []:
                units[u["id"]] = u
    if cache.get("units"):  # mémoire v2 : unités gardées dans le cache → fichiers par pays
        grouped = {}
        for u in cache.pop("units").values():
            grouped.setdefault(u["iso"], []).append({k: u[k] for k in ("id", "iso", "n", "code", "g", "c", "bb") if k in u})
        for iso, us in grouped.items():
            if iso not in files:
                files[iso] = {"v": 1, "fetched": now.isoformat(), "units": us}
                _write_units(iso, files[iso])
                for u in us:
                    units[u["id"]] = u
    iso_reg = {iso: rid for rid, r in regions.items() for iso in r["countries"]}
    rank = {rid: i for i, rid in enumerate(priority)}
    activity = {}
    for e in events:
        if e.get("category") in SEC_CATS | {"unrest"}:
            activity[e.get("country")] = activity.get(e.get("country"), 0) + 1

    def due(iso):
        d = files.get(iso)
        if d is None:
            return True
        if d.get("failed"):
            return (now - datetime.fromisoformat(d["failed"])).days >= 7
        return False
    todo = sorted((iso for iso in iso_reg if due(iso)),
                  key=lambda i: (rank.get(iso_reg[i], len(rank)), -activity.get(i, 0), i))
    done = 0
    for iso in todo[:per_run]:
        item = countries.get(iso)
        if not item or not item.get("iso3"):
            files[iso] = {"v": 1, "units": [], "none": True, "fetched": now.isoformat()}
            _write_units(iso, files[iso])
            continue
        try:
            us = fetch_country_units(iso, item["iso3"], base_tol)
        except Exception as exc:
            log(f"  Alerte précoce : limites de {iso} indisponibles ({type(exc).__name__})")
            files[iso] = {"v": 1, "units": [], "failed": now.isoformat()}
            _write_units(iso, files[iso])
            continue
        files[iso] = {"v": 1, "fetched": now.isoformat(), "units": us}
        _write_units(iso, files[iso])
        for u in us:
            units[u["id"]] = u
        done += 1
    if done:
        log(f"  Alerte précoce : limites administratives de {done} nouveau(x) pays ({len(units)} subdivisions au total)")
    for u in units.values():
        u["reg"] = unit_region(u, iso_reg, regions)
    pending = [iso for iso in todo[per_run:]]
    return units, pending


def locate_unit(units_by_iso, iso, lat, lon):
    for u in units_by_iso.get(iso, []):
        x0, y0, x1, y1 = u["bb"]
        if x0 <= lon <= x1 and y0 <= lat <= y1 and point_in_polys(lon, lat, u["g"]):
            return u["id"]
    return None


# ------------------------------------------------------------------ climat (NASA POWER), stockage compact
def power_fetch(lat, lon, start_year, end_year):
    """{y0, P, T, W} : séries mensuelles (P en mm/mois, T en °C, W humidité racinaire 0-1), None si absent."""
    params = {"parameters": "PRECTOTCORR,T2M,GWETROOT", "community": "AG", "longitude": lon, "latitude": lat,
              "start": start_year, "end": end_year, "format": "JSON"}
    data = http.get_json(POWER_URL, params=params, timeout=60)
    par = (data.get("properties") or {}).get("parameter") or {}
    fill = (data.get("header") or {}).get("fill_value", -999)
    size = (end_year - start_year + 1) * 12
    out = {"y0": start_year}
    for key, short in (("PRECTOTCORR", "P"), ("T2M", "T"), ("GWETROOT", "W")):
        arr = [None] * size
        for ym, v in (par.get(key) or {}).items():
            if len(ym) != 6 or ym[4:] == "13" or v is None or v == fill or v <= -990:
                continue
            y, m = int(ym[:4]), int(ym[4:])
            i = (y - start_year) * 12 + m - 1
            if not 0 <= i < size:
                continue
            if short == "P":  # mm/jour → mm/mois
                v = v * calendar.monthrange(y, m)[1]
            arr[i] = round(v, 2)
        out[short] = arr
    return out


def migrate_climate(c):
    """Format v2 {fetched, data: {P: {"AAAA-MM": v}}} → format compact v3 {fetched, y0, P: [...], ...}."""
    if not c or "data" not in c:
        return c
    data = c.get("data") or {}
    yms = [ym for s in data.values() for ym in s]
    if not yms:
        return {"fetched": c.get("fetched"), "y0": 2000, "P": [], "T": [], "W": []}
    y0, y1 = int(min(yms)[:4]), int(max(yms)[:4])
    out = {"fetched": c.get("fetched"), "y0": y0}
    for k in ("P", "T", "W"):
        arr = [None] * ((y1 - y0 + 1) * 12)
        for ym, v in (data.get(k) or {}).items():
            arr[(int(ym[:4]) - y0) * 12 + int(ym[5:7]) - 1] = v
        out[k] = arr
    return out


def last_month(c):
    arr = (c or {}).get("P") or []
    for i in range(len(arr) - 1, -1, -1):
        if arr[i] is not None:
            y, m = divmod(i, 12)
            return f"{c['y0'] + y:04d}-{m + 1:02d}"
    return None


def update_climate(units, cache, now, log, per_run, refresh_days, rank):
    clim = cache.setdefault("climate", {})
    prev_month = _month_key((now.replace(day=1) - timedelta(days=1)))
    todo = []
    for u in units.values():
        if not u.get("reg"):
            continue
        c = clim.get(u["id"]) or {}
        age = (now - datetime.fromisoformat(c["fetched"])).days if c.get("fetched") else 999
        has_last = (last_month(c) or "") >= prev_month
        if age >= refresh_days or (not has_last and age >= 2 and now.day >= 6):
            todo.append((c.get("fetched", ""), rank.get(u["reg"], 99), u["id"]))
    todo.sort()
    todo = [uid for _, _, uid in todo[:per_run]]
    if not todo:
        return 0

    def one(uid):
        u = units[uid]
        try:
            return uid, power_fetch(u["c"][0], u["c"][1], now.year - CLIMATE_YEARS + 1, now.year), None
        except Exception as exc:
            return uid, None, f"{type(exc).__name__}"
    ok, errs = 0, []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for uid, data, err in pool.map(one, todo):
            if data:
                clim[uid] = {"fetched": now.isoformat(), **data}
                ok += 1
            else:
                errs.append(err)
    log(f"  Alerte précoce : climat NASA POWER mis à jour pour {ok}/{len(todo)} subdivision(s)"
        + (f" ({errs[0]})" if errs else ""))
    return ok


def climate_stats(c, key, months):
    """Valeurs des mois demandés + moyenne, minimum et maximum des mêmes mois les 15 années précédentes."""
    arr = (c or {}).get(key) or []
    v, avg, mn, mx = [], [], [], []
    for ym in months:
        i = _month_index(c, ym) if arr else -1
        v.append(arr[i] if 0 <= i < len(arr) else None)
        prev = [arr[j] for j in (i - 12 * k for k in range(1, 16)) if 0 <= j < len(arr) and arr[j] is not None] if arr else []
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


def update_humanitarian(countries, regions, cache, now, log, cfg, app_id, rank):
    """Insécurité alimentaire, déplacés et population par subdivision (HDX HAPI). Quelques pays par collecte ; les pays
    sans données humanitaires (la plupart hors crises) ne sont relus que tous les 90 jours."""
    hum = cache.setdefault("humanitarian", {})
    start = (now - timedelta(days=550)).date().isoformat()
    refresh, empty_refresh = int(cfg.get("hapi_refresh_days", 7)), int(cfg.get("hapi_empty_refresh_days", 90))
    order = sorted(((rank.get(rid, 99), iso) for rid, reg in regions.items() for iso in reg["countries"]))
    todo = []
    for _, iso in order:
        h = hum.get(iso) or {}
        if h.get("fetched"):
            age = (now - datetime.fromisoformat(h["fetched"])).days
            has = bool(h.get("ipc") or h.get("idp"))
            if age < (refresh if has else empty_refresh):
                continue
        todo.append((h.get("fetched", ""), iso))
    todo.sort()
    done, failed = 0, []
    for _, iso in todo[:int(cfg.get("hapi_per_run", 8))]:
        item = countries.get(iso)
        if not item or not item.get("iso3"):
            hum[iso] = {"fetched": now.isoformat(), "ipc": {}, "idp": {}, "pop": {}}
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
            if out["ipc"] or out["idp"]:  # population : seulement là où il y a une crise à rapporter
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
        log(f"  Alerte précoce : données humanitaires HDX HAPI relues pour {done} pays")
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


# ------------------------------------------------------------------ incidents par subdivision et par famille
def _is_resource(title):
    t = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode().lower()
    return any(re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", t) for w in RESOURCE_WORDS)


def _count(row, fam, title):
    row[FAMILIES.index(fam)] += 1
    if fam == "sec" and _is_resource(title):
        row[1] += 1


def update_security(units, cache, events, now, log):
    """Comptage mensuel des incidents vérifiés par subdivision et par famille de facteurs. Les identifiants déjà
    comptés sont mémorisés : la série s'allonge au-delà de la durée de conservation des incidents."""
    sec = cache.setdefault("security", {})   # "AAAA-MM" → {subdivision: [sec, res, unrest, pol, haz, infra, health]}
    seen = cache.setdefault("security_seen", {})  # "AAAA-MM" → [ids]
    by_iso = {}
    for u in units.values():
        by_iso.setdefault(u["iso"], []).append(u)
    seen_sets = {ym: set(ids) for ym, ids in seen.items()}
    if "live_start" not in cache:
        dates = [e["date"][:7] for e in events if e.get("date")]
        cache["live_start"] = min(dates) if dates else _month_key(now)
    added = 0
    for e in events:
        fam = CAT_FAMILY.get(e.get("category"))
        if not fam or e.get("country") not in by_iso or e.get("lat") is None or not e.get("date"):
            continue
        if (e.get("severity") or 0) < MIN_SEVERITY.get(fam, 0):
            continue
        ym = e["date"][:7]
        ids = seen_sets.setdefault(ym, set())
        if e["id"] in ids:
            continue
        uid = locate_unit(by_iso, e["country"], e["lat"], e["lon"])
        if not uid:
            continue
        ids.add(e["id"])
        months = sec.setdefault(ym, {})
        row = months[uid] = _pad(months.get(uid))
        _count(row, fam, e.get("title", ""))
        added += 1
    cache["security_seen"] = {ym: sorted(ids) for ym, ids in seen_sets.items()}
    # base historique (UCDP, GDELT) : mois antérieurs au comptage en direct, pour les pays pas encore traités
    done = set(cache.get("history_isos") or [])
    new = set(by_iso) - done
    if new and HISTORY_PARTS.exists():
        n = backfill_history({iso: by_iso[iso] for iso in new}, sec, now, cache["live_start"])
        if n:
            log(f"  Alerte précoce : {n} incident(s) historiques rattachés aux subdivisions de {len(new)} pays")
    cache["history_isos"] = sorted(done | set(by_iso))
    cutoff = _month_key(now - timedelta(days=1900))
    for d in (sec, cache["security_seen"]):
        for ym in [k for k in d if k < cutoff]:
            d.pop(ym)
    return added


def backfill_history(by_iso, sec, now, live_start):
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
            fam = CAT_FAMILY.get(r.get("cat"))
            if not ym or ym < start or ym >= live_start or fam not in ("sec", "unrest", "pol"):
                continue
            iso, lat, lon = r.get("iso"), r.get("lat"), r.get("lon")
            if iso not in by_iso or lat is None:
                continue
            uid = locate_unit(by_iso, iso, lat, lon)
            if not uid:
                continue
            months = sec.setdefault(ym, {})
            row = months[uid] = _pad(months.get(uid))
            _count(row, fam, r.get("title", ""))
            n += 1
    return n


def series(rows):
    """Lignes mensuelles [sec, res, unrest, pol, haz, infra, health] → séries par composante."""
    rows = [_pad(r) for r in rows]
    return {"all": [r[0] for r in rows], "res": [r[1] for r in rows], "so": [r[2] + r[3] for r in rows],
            "pol": [r[3] for r in rows], "hz": [r[4] + r[5] + r[6] for r in rows],
            "haz": [r[4] for r in rows], "infra": [r[5] for r in rows], "health": [r[6] for r in rows]}


# ------------------------------------------------------------------ indice de convergence
def _trend(arr):
    """(nombre sur 3 mois, rythme des mois précédents ramené à 3 mois)."""
    n3 = sum(arr[-3:])
    base = sum(arr[:-3]) / max(1, len(arr) - 3) * 3 if len(arr) > 3 else 0
    return n3, base


def score_unit(clim, s, hum, has_hum=True):
    """Indice 0-100 : climat 30 · terrorisme/conflits/criminalité 30 · société et politique 15 · aléas, infrastructures
    et santé 10 · humanitaire 15 (si la donnée existe ; sinon total ramené sur 100). Facteurs explicatifs en clair."""
    drivers = []
    cl = 0
    p = clim.get("P") or {}
    if p:
        v3 = [x for x in p["v"][-3:] if x is not None]
        a3 = [x for x in p["avg"][-3:] if x is not None]
        if len(v3) == 3 and len(a3) == 3 and sum(a3) >= 30:
            ratio = sum(v3) / sum(a3)
            cl += 18 if ratio < 0.5 else 11 if ratio < 0.7 else 5 if ratio < 0.85 else 11 if ratio > 1.8 else 6 if ratio > 1.4 else 0
            if ratio < 0.85:
                drivers.append(["rain_deficit", round(ratio * 100)])
            elif ratio > 1.4:
                drivers.append(["rain_excess", round(ratio * 100)])
    t = clim.get("T") or {}
    if t:
        d = [v - a for v, a in zip(t["v"][-3:], t["avg"][-3:]) if v is not None and a is not None]
        if d:
            anom = sum(d) / len(d)
            cl += 8 if anom > 1.5 else 4 if anom > 0.8 else 0
            if anom > 0.8:
                drivers.append(["heat", round(anom, 1)])
    w = clim.get("W") or {}
    if w and w["v"] and w["v"][-1] is not None and w["avg"][-1] is not None:
        if w["min"][-1] is not None and w["v"][-1] < w["min"][-1]:
            cl += 4
            drivers.append(["soil_record", round(w["v"][-1], 2)])
        elif w["v"][-1] < w["avg"][-1] - 0.1:
            cl += 2
            drivers.append(["soil_dry", round(w["v"][-1] - w["avg"][-1], 2)])
    cl = min(cl, 30)
    # terrorisme, conflits armés, attaques, criminalité
    co = 0
    n3, base = _trend(s.get("all") or [])
    co += 17 if n3 >= 30 else 12 if n3 >= 10 else 7 if n3 >= 3 else 3 if n3 >= 1 else 0
    if n3 >= 3 and base > 0 and n3 / base >= 1.5:
        co += 9
        drivers.append(["conflict_up", round((n3 / base - 1) * 100)])
    elif n3 >= 3 and base > 0 and n3 / base >= 1.2:
        co += 4
        drivers.append(["conflict_up", round((n3 / base - 1) * 100)])
    elif n3 >= 3 and base == 0:
        co += 7
        drivers.append(["conflict_new", n3])
    if n3 >= 1:
        drivers.append(["incidents", n3])
    r3 = sum((s.get("res") or [])[-3:])
    if r3:
        co += 4
        drivers.append(["resource", r3])
    co = min(co, 30)
    # société et politique : troubles civils, crises politiques
    so = 0
    u3, ubase = _trend(s.get("so") or [])
    so += 6 if u3 >= 10 else 4 if u3 >= 3 else 2 if u3 >= 1 else 0
    if u3 >= 3 and ((ubase > 0 and u3 / ubase >= 1.5) or ubase == 0):
        so += 6
        drivers.append(["unrest_up", u3])
    elif u3 >= 1:
        drivers.append(["unrest", u3])
    if sum((s.get("pol") or [])[-3:]) >= 1:
        so += 3
        drivers.append(["political", sum((s.get("pol") or [])[-3:])])
    so = min(so, 15)
    # aléas naturels, infrastructures et cyber, santé (gravité 2 et plus)
    hz = 0
    h3, hbase = _trend(s.get("hz") or [])
    hz += 5 if h3 >= 5 else 3 if h3 >= 2 else 1 if h3 >= 1 else 0
    if h3 >= 2 and ((hbase > 0 and h3 / hbase >= 1.5) or hbase == 0):
        hz += 5
    for key in ("haz", "infra", "health"):
        k3 = sum((s.get(key) or [])[-3:])
        if k3:
            drivers.append([key, k3])
    hz = min(hz, 10)
    # crises humanitaires
    hu = 0
    ipc = hum.get("ipc3")
    if ipc is not None:
        hu += 9 if ipc >= 0.4 else 6 if ipc >= 0.25 else 3 if ipc >= 0.15 else 0
        if ipc >= 0.15:
            drivers.append(["ipc", round(ipc * 100)])
    idp, pop = hum.get("idp"), hum.get("pop")
    if idp:
        share = idp / pop if pop else None
        hu += (6 if share >= 0.1 else 4 if share >= 0.03 else 1) if share is not None else (4 if idp >= 100000 else 1)
        if idp >= 20000:
            drivers.append(["idp", idp])
    hu = min(hu, 15)
    raw = cl + co + so + hz + hu
    total = raw if has_hum else round(raw * 100 / 85)
    level = 4 if total >= 60 else 3 if total >= 40 else 2 if total >= 20 else 1
    return {"v": min(total, 100), "lvl": level, "c": {"cl": cl, "co": co, "so": so, "hz": hz, "hu": hu},
            "hum": bool(has_hum), "dr": drivers}


# ------------------------------------------------------------------ mémoire
def load_cache():
    try:
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    return migrate(cache)


def migrate(cache):
    """Mémoire v2 (Corne et Sahel) → v3 (monde) : climat compact ; comptages refaits par famille de facteurs."""
    if cache.get("v") == CACHE_VERSION:
        return cache
    cache["climate"] = {uid: migrate_climate(c) for uid, c in (cache.get("climate") or {}).items()}
    for k in ("security", "security_seen", "history_done", "history_done_v2", "validation", "live_start", "history_isos"):
        cache.pop(k, None)
    cache["v"] = CACHE_VERSION
    return cache


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


# ------------------------------------------------------------------ assemblage
def update(store, countries, events, settings, log, now=None, fetch=True):
    """Collecte : avance le remplissage (limites, climat, humanitaire) si fetch, compte les incidents, publie.
    events : incidents vérifiés en mémoire (jusqu'à la durée de conservation), pas seulement ceux de la carte."""
    now = now or datetime.now(timezone.utc)
    cfg = config.load_json("early_warning.json", {}) or {}
    if cfg.get("enabled") is False:
        return None
    regions = regions_config()
    priority = cfg.get("priority") or list(regions)
    rank = {rid: i for i, rid in enumerate(priority)}
    cache = load_cache()
    units, pending = load_units(countries, regions, cache, log, float(cfg.get("simplify_tolerance", 0.015)),
                                int(cfg.get("boundaries_per_run", 10)) if fetch else 0, now, priority, events)
    if not units:
        save_cache(cache)
        return None
    if fetch:
        update_climate(units, cache, now, log, int(cfg.get("power_per_run", 40)), int(cfg.get("power_refresh_days", 10)), rank)
        app_id = cfg.get("hapi_app_identifier") or "YW5nb3ItaW50ZWxsaWdlbmNlOmNvbnRhY3RAYW5nb3IuZnI="
        update_humanitarian(countries, regions, cache, now, log, cfg, app_id, rank)
    update_security(units, cache, events, now, log)
    save_cache(cache)
    return build(units, cache, regions, now, pending)


def backtest(units, cache, now, months_back=40, horizon=3):
    """Validation a posteriori : pour chaque subdivision ayant connu au moins un incident et chaque mois passé, indice
    calculé avec les seules données disponibles à ce moment (climat et incidents ; l'humanitaire n'a pas d'historique),
    puis on regarde si les incidents de sécurité ont nettement augmenté dans les 3 mois suivants (≥ 1,5 fois le rythme
    des 12 mois précédents et ≥ 3). Un indice utile montre un taux d'aggravation croissant avec le niveau."""
    clim_all = cache.get("climate") or {}
    sec = cache.get("security") or {}
    if len(sec) < 18:
        return None
    end = _month_key(now.replace(day=1) - timedelta(days=1))
    all_months = _months_back(end, months_back + horizon + 15)
    first = min(sec)
    stats = {lvl: [0, 0] for lvl in (1, 2, 3, 4)}
    cases = []
    for u in units.values():
        rows = [_pad((sec.get(ym) or {}).get(u["id"])) for ym in all_months]
        if not any(r[0] for r in rows):
            continue
        c = clim_all.get(u["id"])
        for k in range(15, len(all_months) - horizon):
            m = all_months[k]
            if m < first:
                continue
            win3 = all_months[k - 2:k + 1]
            clim = {key: climate_stats(c, key, win3) for key in ("P", "T", "W")} if c and c.get("P") else {}
            s = series(rows[k - 14:k + 1])
            sc = score_unit(clim, s, {}, has_hum=False)
            before = sum(s["all"][-12:]) / 12 * horizon
            after = sum(r[0] for r in rows[k + 1:k + 1 + horizon])
            esc = after >= 3 and after >= 1.5 * max(before, 1)
            stats[sc["lvl"]][0] += 1
            stats[sc["lvl"]][1] += 1 if esc else 0
            if esc and sc["lvl"] >= 3 and len(cases) < 400:
                cases.append([u["id"], m, sc["v"], after])
    n = sum(v[0] for v in stats.values())
    if not n:
        return None
    base = sum(v[1] for v in stats.values()) / n
    return {"period": [all_months[15], all_months[-horizon - 1]], "horizon_months": horizon, "unit_months": n,
            "base_rate": round(base, 3),
            "by_level": {str(k): {"n": v[0], "rate": round(v[1] / v[0], 3) if v[0] else None} for k, v in stats.items()},
            "hits": cases[-40:]}


def _write_region(rid, units):
    d = OUT_DIR / "early_warning"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / f"{rid}.js", "w", encoding="utf-8") as fh:
        fh.write("window.VS_EW_R = window.VS_EW_R || {};\nwindow.VS_EW_R[" + json.dumps(rid) + "] = ")
        json.dump({"units": units}, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")


def build(units, cache, regions, now, pending=()):
    clim_all = cache.get("climate") or {}
    latest = [m for m in (last_month(c) for c in clim_all.values()) if m]
    end = max(latest) if latest else _month_key(now.replace(day=1) - timedelta(days=1))
    months = _months_back(end, 12)
    sec_months = _months_back(_month_key(now), 15)  # incidents : jusqu'au mois en cours
    sec = cache.get("security") or {}
    hum = cache.get("humanitarian") or {}
    per_region, summary = {rid: [] for rid in regions}, []
    for u in sorted(units.values(), key=lambda x: (x["iso"], x["n"])):
        rid = u.get("reg")
        if rid not in per_region:
            continue
        c = clim_all.get(u["id"])
        clim = {k: climate_stats(c, k, months) for k in ("P", "T", "W")} if c and c.get("P") else {}
        s = series([(sec.get(ym) or {}).get(u["id"]) for ym in sec_months])
        h = hum.get(u["iso"]) or {}
        has_hum = bool(h.get("ipc") or h.get("idp"))
        ipc, idp, pop = match_admin(u["n"], h.get("ipc")), match_admin(u["n"], h.get("idp")), match_admin(u["n"], h.get("pop"))
        hu = {"ipc3": ipc["v"] if ipc else None, "ipc_end": ipc["e"] if ipc else None, "ipc_n": ipc.get("n") if ipc else None,
              "idp": idp["v"] if idp else None, "idp_end": idp["e"] if idp else None, "pop": pop["v"] if pop else None}
        score = score_unit(clim, s, hu, has_hum)
        per_region[rid].append({"id": u["id"], "iso": u["iso"], "n": u["n"], "g": u["g"], "c": u["c"], "clim": clim,
                                "sec": {k: s[k] for k in ("all", "res", "so", "hz")}, "hum": hu, "score": score,
                                "ok": bool(clim)})
        summary.append({"id": u["id"], "iso": u["iso"], "n": u["n"], "reg": rid, "v": score["v"], "lvl": score["lvl"],
                        "c": score["c"], "ok": bool(clim)})
    # validation a posteriori : recalculée une fois par jour
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
    regs = {}
    pend = set(pending)
    for rid, reg in regions.items():
        us = per_region[rid]
        lv = {}
        for x in us:
            lv[x["score"]["lvl"]] = lv.get(x["score"]["lvl"], 0) + 1
        top = sorted((x for x in us if x["ok"] or x["score"]["v"]), key=lambda x: -x["score"]["v"])[:10]
        regs[rid] = {"fr": reg["fr"], "en": reg["en"], "countries": reg["countries"], "bbox": reg["bbox"],
                     "n": len(us), "with_climate": sum(1 for x in us if x["ok"]), "levels": lv,
                     "pending": [c for c in reg["countries"] if c in pend],
                     "top": [[x["id"], x["n"], x["iso"], x["score"]["v"], x["score"]["lvl"]] for x in top]}
        _write_region(rid, us)
    payload = {"generated": now.isoformat(), "version": CACHE_VERSION, "months": months, "sec_months": sec_months,
               "regions": regs, "components": COMPONENTS, "validation": val, "levels": {},
               "units": len(summary),
               "credits": "NASA POWER (MERRA-2) · HDX HAPI (OCHA : IPC, OIM-DTM, population) · incidents vérifiés Angor, "
                          "UCDP, GDELT · limites administratives geoBoundaries (CC BY 4.0)"}
    for x in summary:
        payload["levels"][x["lvl"]] = payload["levels"].get(x["lvl"], 0) + 1
    write_js("early_warning.js", "VS_EW", payload)
    return {"index": payload, "units": summary}
