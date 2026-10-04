"""Fiche pays détaillée (rapport pays) : villes, aéroports, secours, santé, conseils FCDO.

Écrit un fichier par pays, docs/data/country/<ISO2>.js, chargé à la demande par le rapport pays.

Sources (toutes gratuites, sans clé) :
- Natural Earth – populated places (domaine public) : grandes villes, capitales, noms français, fuseaux
- OurAirports (domaine public) : aéroports internationaux et régionaux avec vols réguliers
- World Emergency & Crisis Hotlines (worldhotlines.org) : numéros d'urgence par service, avec niveau de vérification
- FCDO (Open Government Licence v3.0) : texte détaillé des conseils aux voyageurs (voir veille/fcdo.py)
- config/health.json : risques sanitaires du voyageur (listes OMS/CDC/HCSP, indicatives)
- config/city_notes.json : notes d'analyste par ville (à valider)
- les incidents collectés par l'outil (90 derniers jours) pour l'activité par ville

Les référentiels (villes, aéroports, numéros) sont relus une fois par semaine et gardés dans data/.
"""
import csv
import io
import json
import math
import re
import time
import unicodedata
from datetime import timedelta

from . import fcdo, http
from .config import ROOT
from .model import CATEGORIES, parse_iso

DATA = ROOT / "data"
OUT = ROOT / "docs" / "data" / "country"
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_populated_places.geojson"
AIRPORTS_URL = "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv"
HOTLINES_URL = "https://raw.githubusercontent.com/craigrallen/world-emergency-hotlines/main/hotlines.json"
WEEK = 7 * 86400
LEFT_DRIVING = set("AG AI AU BB BD BM BN BS BT BW CC CK CX CY DM FJ FK GB GD GG GY HK IE IM IN JE JM JP KE KI KN KY LC LK LS "
                   "MO MS MT MU MV MW MY MZ NA NF NP NR NU NZ PG PK PN SB SC SG SH SR SZ TC TH TL TO TT TV TZ UG VC VG VI WS "
                   "ZA ZM ZW".split())
SEV_W = {1: 1, 2: 2, 3: 4, 4: 8}


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _km(a, b, c, d):
    r = math.radians
    h = math.sin(r(c - a) / 2) ** 2 + math.cos(r(a)) * math.cos(r(c)) * math.sin(r(d - b) / 2) ** 2
    return 12742 * math.asin(math.sqrt(min(1, h)))


def _cached(name, url, reduce, log, max_age=WEEK, timeout=120):
    """Référentiel téléchargé au plus une fois par semaine ; en cas d'échec, on garde l'ancien."""
    path = DATA / name
    if path.exists() and time.time() - path.stat().st_mtime < max_age:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            pass
    try:
        r = http.get(url, timeout=timeout, retries=1)
        data = reduce(r)
        DATA.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        if log:
            log(f"  Référentiel {name} mis à jour")
        return data
    except Exception as exc:
        if log:
            log(f"  Référentiel {name} indisponible ({type(exc).__name__}) : ancienne version conservée")
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                return None
        return None


def _reduce_places(r):
    out = []
    for f in r.json().get("features", []):
        p = f.get("properties") or {}
        pop = p.get("POP_MAX") or 0
        cap = 1 if p.get("ADM0CAP") == 1 else 0
        iso = p.get("ISO_A2")
        if not iso or iso == "-99":
            iso = {"SOL": "SO", "KOS": "XK", "CYN": "CY", "SAH": "EH", "PSX": "PS", "KAS": "IN"}.get(p.get("ADM0_A3") or "", iso)
        if not iso or iso == "-99" or (pop < 100000 and not cap):
            continue
        out.append([p.get("NAME"), p.get("NAME_FR") or p.get("NAME"), iso, round(p.get("LATITUDE"), 4),
                    round(p.get("LONGITUDE"), 4), int(pop), cap, p.get("ADM1NAME") or "", p.get("TIMEZONE") or "",
                    p.get("NAMEALT") or ""])
    return out


def _reduce_airports(r):
    out = []
    for row in csv.DictReader(io.StringIO(r.text)):
        if row["type"] not in ("large_airport", "medium_airport") or row["scheduled_service"] != "yes" or not row["iata_code"]:
            continue
        out.append([row["name"], row["iata_code"], row["icao_code"] or row["gps_code"], row["iso_country"],
                    row["municipality"], round(float(row["latitude_deg"]), 4), round(float(row["longitude_deg"]), 4),
                    1 if row["type"] == "large_airport" else 0])
    return out


def _reduce_hotlines(r):
    out = {}
    for c in r.json().get("countries", []):
        iso = c.get("alpha-2")
        if not iso:
            continue
        lines = []
        for h in c.get("hotlines", []):
            if h.get("category") != "emergency" or not h.get("voice_numbers"):
                continue
            lines.append({"name": h.get("name"), "numbers": h["voice_numbers"][:4], "status": h.get("verification_status")})
        out[iso] = {"general": c.get("general_emergency") or [], "notes": c.get("notes") or "", "lines": lines[:6]}
    return out


def _select_cities(places, iso, notes):
    rows = sorted((p for p in places if p[2] == iso), key=lambda p: -p[5])
    if not rows:
        return []
    # une seule entrée par agglomération (New Delhi / Delhi, Islamabad / Rawalpindi…) : on garde la capitale ou la plus peuplée
    caps_first = sorted(rows, key=lambda p: (-p[6], -p[5]))
    kept = []
    for p in caps_first:
        if not any(_km(p[3], p[4], q[3], q[4]) < 25 for q in kept):
            kept.append(p)
    rows = sorted(kept, key=lambda p: -p[5])
    chosen = []
    caps = [p for p in rows if p[6]]
    if caps:
        chosen.append(caps[0])
    for p in rows:
        if len(chosen) >= 6:
            break
        if p not in chosen and p[5] >= 1_000_000:
            chosen.append(p)
    for p in rows:
        if len(chosen) >= 4:
            break
        if p not in chosen and p[5] >= 200_000:
            chosen.append(p)
    # villes suivies par l'analyste, même petites (Goma, Maiduguri, Hargeisa, Culiacán…)
    for n in notes:
        keys = {_norm(n["city"])} | {_norm(a) for a in n.get("aliases", [])}
        match = next((p for p in rows if _norm(p[0]) in keys or _norm(p[1]) in keys), None)
        if match and match not in chosen and len(chosen) < 9:
            chosen.append(match)
    return chosen


def _note_for(city, notes):
    keys = {_norm(city[0]), _norm(city[1])} | {_norm(x) for x in (city[9] or "").split("|") if x}
    for n in notes:
        if _norm(n["city"]) in keys or any(_norm(a) in keys for a in n.get("aliases", [])):
            return n
    return None


def _mentions(city, sentences, notes_entry):
    names = {city[0], city[1]} | set((notes_entry or {}).get("aliases", []))
    names = {n for n in names if n and len(n) >= 4}
    out = []
    for s in sentences:
        if any(re.search(r"\b" + re.escape(n) + r"\b", s) for n in names):
            if s not in out:
                out.append(s)
    # d'abord les phrases qui parlent de menaces
    out.sort(key=lambda s: -len(re.findall(r"attack|kidnap|terror|crime|protest|avoid|robber|violen|explos|shoot|curfew", s, re.I)))
    return out[:4]


def _sentences(fcdo_data):
    out = []
    for para in fcdo.plain_text(fcdo_data):
        out.extend(x.strip() for x in re.split(r"(?<=[.!?])\s+", para) if 30 <= len(x.strip()) <= 420)
    return out


def _activity(evs):
    score = sum(SEV_W.get(e.get("severity", 1), 1) for e in evs)
    level = 0 if not evs else 1 if score < 6 else 2 if score < 20 else 3 if score < 60 else 4
    return score, level


def _event_row(e):
    return {"id": e["id"], "t": e.get("title"), "tf": e.get("title_fr"), "te": e.get("title_en"), "d": e["date"],
            "s": e.get("severity", 1), "c": e.get("category"), "src": e.get("source"), "u": e.get("url")}


def _health(iso, cfg):
    L = {k: set(v.split()) for k, v in cfg.get("lists", {}).items()}
    risks, vacc = [], ["routine"]
    if iso not in L.get("hep_a_low", set()):
        vacc.append("hep_a")
    if iso in L.get("yellow_fever", set()):
        risks.append("yellow_fever")
        vacc.append("yellow_fever_cert" if iso in L.get("yellow_fever_cert", set()) else "yellow_fever")
    malaria = "high" if iso in L.get("malaria_high", set()) else "limited" if iso in L.get("malaria_limited", set()) else None
    if malaria:
        risks.append("malaria")
    for key, disease in (("dengue", "dengue"), ("meningitis_belt", "meningitis"), ("japanese_encephalitis", "japanese_encephalitis"),
                         ("tb_high", "tuberculosis"), ("polio", "polio"), ("cholera_recurrent", "cholera"), ("altitude", "altitude")):
        if iso in L.get(key, set()):
            risks.append(disease)
    if iso not in L.get("hep_a_low", set()):
        risks.append("travellers_diarrhoea")
        vacc.append("typhoid")
        vacc.append("hep_b")
    if iso not in L.get("rabies_low", set()):
        risks.append("rabies")
        if iso not in L.get("hep_a_low", set()):
            vacc.append("rabies")
    for key, v in (("meningitis_belt", "meningitis"), ("japanese_encephalitis", "japanese_encephalitis"), ("polio", "polio"),
                   ("cholera_recurrent", "cholera")):
        if iso in L.get(key, set()):
            vacc.append(v)
    return {"risks": risks, "vaccines": vacc, "malaria": malaria}


def build(events, countries, now, log=None):
    """Écrit docs/data/country/<ISO>.js pour chaque pays connu. Renvoie le nombre de fiches."""
    t0 = time.time()
    places = _cached("ne_places.json", NE_URL, _reduce_places, log, timeout=180) or []
    airports = _cached("airports.json", AIRPORTS_URL, _reduce_airports, log, timeout=180) or []
    hotlines = _cached("hotlines.json", HOTLINES_URL, _reduce_hotlines, log) or {}
    try:
        notes_all = json.loads((ROOT / "config" / "city_notes.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        notes_all = {"cities": []}
    try:
        health_cfg = json.loads((ROOT / "config" / "health.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        health_cfg = {}
    notes_by_iso = {}
    for n in notes_all.get("cities", []):
        notes_by_iso.setdefault(n["iso"], []).append(n)

    since = now - timedelta(days=90)
    since30 = now - timedelta(days=30)
    ev_by_iso = {}
    for e in events:
        if e.get("country") and e.get("lat") is not None and parse_iso(e["date"]) >= since:
            if CATEGORIES.get(e.get("category"), {}).get("group") == "diplomatic":
                continue
            ev_by_iso.setdefault(e["country"], []).append(e)
    ap_by_iso = {}
    for a in airports:
        ap_by_iso.setdefault(a[3], []).append(a)

    OUT.mkdir(parents=True, exist_ok=True)
    # textes de référence santé (maladies, vaccins) pour le rapport pays
    with open(OUT.parent / "health.js", "w", encoding="utf-8") as fh:
        fh.write("window.VS_HEALTH = ")
        json.dump({k: health_cfg.get(k) for k in ("diseases", "vaccines")}, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    written = 0
    for item in countries.items:
        iso = item.get("iso2")
        if not iso or len(iso) != 2:
            continue
        notes = notes_by_iso.get(iso, [])
        fc = fcdo.load(iso)
        sentences = _sentences(fc) if fc else []
        evs = ev_by_iso.get(iso, [])
        aps = sorted(ap_by_iso.get(iso, []), key=lambda a: -a[7])
        cities = []
        for c in _select_cities(places, iso, notes):
            radius = 40 if c[5] >= 5_000_000 else 30 if c[5] >= 1_000_000 else 20
            near = [e for e in evs if _km(c[3], c[4], e["lat"], e["lon"]) <= radius]
            score, level = _activity(near)
            by_cat = {}
            for e in near:
                by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
            top = sorted(near, key=lambda e: (-(e.get("severity") or 1), e["date"]), reverse=False)
            top = sorted(top[:12], key=lambda e: (e.get("severity") or 1, e["date"]), reverse=True)[:4]
            ap = min(((a, _km(c[3], c[4], a[5], a[6])) for a in aps), key=lambda x: x[1], default=None)
            note = _note_for(c, notes)
            cities.append({
                "name": c[0], "name_fr": c[1], "lat": c[3], "lon": c[4], "pop": c[5], "capital": bool(c[6]),
                "adm1": c[7], "tz": c[8], "radius_km": radius,
                "airport": {"name": ap[0][0], "iata": ap[0][1], "icao": ap[0][2], "km": round(ap[1])} if ap and ap[1] <= 80 else None,
                "stats": {"n90": len(near), "n30": sum(1 for e in near if parse_iso(e["date"]) >= since30),
                          "severe90": sum(1 for e in near if (e.get("severity") or 1) >= 3), "score": score, "level": level,
                          "by_cat": by_cat, "share": round(len(near) / len(evs), 2) if evs else 0},
                "top": [_event_row(e) for e in top],
                "fcdo": _mentions(c, sentences, note),
                "note": note,
            })
        country_score, _ = _activity(evs)
        payload = {
            "iso": iso, "generated": now.replace(microsecond=0).isoformat(),
            "cities": cities, "country_activity": country_score,
            "airports": [{"name": a[0], "iata": a[1], "icao": a[2], "city": a[4], "lat": a[5], "lon": a[6], "large": bool(a[7])} for a in aps[:8]],
            "emergency": {**(hotlines.get(iso) or {}), "fcdo": (fc or {}).get("emergency", [])},
            "driving": "left" if iso in LEFT_DRIVING else "right",
            "health": _health(iso, health_cfg),
            "fcdo": ({k: fc.get(k) for k in ("updated", "reviewed", "url", "parts")} if fc else None),
        }
        with open(OUT / f"{iso}.js", "w", encoding="utf-8") as fh:
            fh.write(f"(window.VS_CDETAIL = window.VS_CDETAIL || {{}})['{iso}'] = ")
            json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
            fh.write(";\n")
        written += 1
    if log:
        log(f"  Fiches pays détaillées : {written} ({sum(1 for i in countries.items if fcdo.has(i.get('iso2') or ''))} avec texte FCDO) "
            f"en {time.time() - t0:.1f} s")
    return written
