"""Agenda des événements prévus (12 prochains mois) : docs/data/calendar.js

Sources :
- Jours fériés : Nager.Date (API publique gratuite, ~120 pays, licence MIT) – date.nager.at ;
  lecture progressive (30 pays par collecte), chaque pays relu tous les 30 jours.
- Élections et référendums nationaux : Wikidata (CC0), une fois par jour ; les scrutins locaux ou
  régionaux sont écartés. Couverture incomplète : complétez avec config/calendar.json.
- Grandes fêtes religieuses musulmanes (début du Ramadan, Aïd el-Fitr, Aïd el-Adha, Achoura) : calcul
  par le calendrier hégirien arithmétique, date indicative à ±1-2 jours (l'observation de la lune fait foi).
- Vos propres échéances (sommets, grèves annoncées, procès, anniversaires sensibles…) : config/calendar.json
  {"events": [{"date": "2026-11-12", "end": "2026-11-13", "country": "FR", "type": "strike",
               "title": "Grève nationale interprofessionnelle", "note": "Transports perturbés", "url": ""}]}
  types : holiday, election, religious, strike, summit, anniversary, sport, other.
"""
import math
import time
from datetime import date, datetime, timedelta

from . import config, http
from .publish import write_js

NAGER = "https://date.nager.at/api/v3"
SPARQL = "https://query.wikidata.org/sparql"
HEADERS = {"Accept": "application/sparql-results+json",
           "User-Agent": "AngorIntelligence/1.0 (veille surete, sources ouvertes; contact via GitHub Slift42)"}
ELECTION_TYPES = ["Q858439", "Q1076105", "Q15283424", "Q43109", "Q1583291", "Q152450", "Q669262"]
LOCAL_WORDS = ("municip", "local", "mayor", "maire", "city council", "conseil municipal", "proposal", "house bill",
               "county", "cantonal", "communal")
TYPE_LABELS = {"holiday": ("Jour férié", "Public holiday"), "election": ("Élection", "Election"),
               "religious": ("Fête religieuse", "Religious festival")}


# ------------------------------------------------------------------ calendrier hégirien (arithmétique)
def _jd_from_hijri(y, m, d):
    return d + math.ceil(29.5 * (m - 1)) + (y - 1) * 354 + (3 + 11 * y) // 30 + 1948439.5 - 1


def _greg_from_jd(jd):
    jd = jd + 0.5
    z = int(jd)
    a = z if z < 2299161 else z + 1 + int((z - 1867216.25) / 36524.25) - int(int((z - 1867216.25) / 36524.25) / 4)
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day = b - d - int(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    return date(year, month, day)


def hijri_to_gregorian(y, m, d):
    return _greg_from_jd(_jd_from_hijri(y, m, d))


def religious(start, end):
    out = []
    feasts = [(9, 1, "Début du Ramadan", "Start of Ramadan", 29), (10, 1, "Aïd el-Fitr", "Eid al-Fitr", 2),
              (12, 10, "Aïd el-Adha", "Eid al-Adha", 3), (1, 10, "Achoura", "Ashura", 0)]
    hy0 = int((start.year - 622) * 1.0307) - 1
    for hy in range(hy0, hy0 + 4):
        for m, d, fr, en, dur in feasts:
            g = hijri_to_gregorian(hy, m, d)
            if start <= g <= end:
                ev = {"d": g.isoformat(), "iso": None, "type": "religious", "t_fr": fr, "t_en": en,
                      "note_fr": "Date indicative (±1-2 j, observation de la lune). Pays à majorité musulmane : "
                                 "rythme de travail modifié, rassemblements, vigilance accrue.",
                      "note_en": "Indicative date (±1-2 days, moon sighting). Muslim-majority countries: changed "
                                 "working hours, gatherings, heightened vigilance.", "src": "calcul"}
                if dur:
                    ev["e"] = (g + timedelta(days=dur)).isoformat()
                out.append(ev)
    return out


# ------------------------------------------------------------------ jours fériés (Nager.Date)
def holidays(countries, state, now, log, per_run=30):
    st = state.setdefault("agenda", {}).setdefault("holidays", {})
    meta = state["agenda"].setdefault("nager", {})
    if not meta.get("countries") or now.isoformat()[:10] > meta.get("next", ""):
        try:
            meta["countries"] = [c["countryCode"] for c in http.get_json(f"{NAGER}/AvailableCountries", timeout=30)]
            meta["next"] = (now + timedelta(days=30)).isoformat()[:10]
        except Exception as exc:
            log(f"  Agenda : liste Nager.Date indisponible ({type(exc).__name__})")
            meta.setdefault("countries", [])
    years = [now.year, now.year + 1]
    todo = []
    for iso in meta["countries"]:
        cur = st.get(iso) or {}
        if cur.get("fetched", "") < (now - timedelta(days=30)).isoformat() or any(str(y) not in cur for y in years):
            todo.append((cur.get("fetched", ""), iso))
    todo.sort()
    done = 0
    t0 = time.time()
    for _, iso in todo[:per_run]:
        if time.time() - t0 > 40:
            break
        cur = {"fetched": now.isoformat()}
        try:
            for y in years:
                rows = http.get_json(f"{NAGER}/PublicHolidays/{y}/{iso}", retries=0, timeout=20)
                cur[str(y)] = [[r["date"], r.get("localName") or r["name"], r["name"],
                                1 if r.get("global", True) else 0] for r in rows or []]
        except Exception:
            continue
        st[iso] = cur
        done += 1
    if todo:
        log(f"  Agenda : jours fériés de {done} pays mis à jour ({len(st)} pays connus)")
    return st


# ------------------------------------------------------------------ élections (Wikidata)
def _sparql(q):
    r = http._session.post(SPARQL, data={"query": q}, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json().get("results", {}).get("bindings", [])


def elections(state, now, log):
    st = state.setdefault("agenda", {})
    if st.get("elections_fetched", "")[:10] == now.isoformat()[:10] and st.get("elections") is not None:
        return st["elections"]
    try:
        cls = _sparql("SELECT DISTINCT ?cls WHERE { VALUES ?t { " + " ".join("wd:" + t for t in ELECTION_TYPES) +
                      " } ?cls wdt:P279 ?t . }")
        types = ELECTION_TYPES + [c["cls"]["value"].rsplit("/", 1)[1] for c in cls]
        d0 = (now - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00Z")
        d1 = (now + timedelta(days=400)).strftime("%Y-%m-%dT00:00:00Z")
        q = ("SELECT ?e ?eLabel ?enLabel ?date ?prec ?iso ?jur ?jurIso WHERE { VALUES ?type { "
             + " ".join("wd:" + t for t in types) + " } ?e wdt:P31 ?type . "
             "?e p:P585/psv:P585 [ wikibase:timeValue ?date ; wikibase:timePrecision ?prec ] . "
             f'FILTER(?date >= "{d0}"^^xsd:dateTime && ?date <= "{d1}"^^xsd:dateTime) '
             "OPTIONAL { ?e wdt:P17 ?c . ?c wdt:P297 ?iso . } "
             "OPTIONAL { ?e wdt:P1001 ?jur . OPTIONAL { ?jur wdt:P297 ?jurIso } } "
             "OPTIONAL { ?e rdfs:label ?enLabel . FILTER(LANG(?enLabel) = 'en') } "
             'SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". } }')
        rows = _sparql(q)
    except Exception as exc:
        log(f"  Agenda : élections Wikidata indisponibles ({type(exc).__name__})")
        return st.get("elections") or []
    out, seen = [], set()
    for r in rows:
        v = lambda k: (r.get(k) or {}).get("value")
        label, iso = v("eLabel") or "", v("iso")
        if not iso or label.startswith("Q") and label[1:].isdigit():
            continue
        if v("jur") and not v("jurIso"):  # scrutin d'une subdivision (État fédéré, région, ville)
            continue
        low = (label + " " + (v("enLabel") or "")).lower()
        if any(w in low for w in LOCAL_WORDS):
            continue
        prec = int(v("prec") or 9)
        d = v("date")[:10]
        key = (iso, label, d)
        if key in seen:
            continue
        seen.add(key)
        out.append({"d": d, "iso": iso, "type": "election", "t_fr": label[:1].upper() + label[1:],
                    "t_en": (v("enLabel") or label), "prec": "day" if prec >= 11 else "month" if prec == 10 else "year",
                    "src": "Wikidata", "url": v("e")})
    st["elections"], st["elections_fetched"] = out, now.isoformat()
    log(f"  Agenda : {len(out)} élection(s) et référendum(s) nationaux à venir (Wikidata)")
    return out


# ------------------------------------------------------------------ assemblage
def update(countries, store, settings, log, now):
    state = store.setdefault("state", {})
    start, end = (now - timedelta(days=2)).date(), (now + timedelta(days=366)).date()
    cfg = settings.get("agenda") or {}
    events = []
    hol = holidays(countries, state, now, log, per_run=int(cfg.get("holidays_per_run", 30)))
    for iso, byyear in hol.items():
        for y, rows in byyear.items():
            if y == "fetched":
                continue
            for d, local, name, is_global in rows:
                if start.isoformat() <= d <= end.isoformat() and is_global:
                    events.append({"d": d, "iso": iso, "type": "holiday", "t_fr": local, "t_en": name, "src": "Nager.Date"})
    events += elections(state, now, log)
    events += religious(start, end)
    for m in (config.load_json("calendar.json", {}) or {}).get("events", []):
        if not m.get("date") or not m.get("title"):
            continue
        if m.get("end", m["date"]) < start.isoformat() or m["date"] > end.isoformat():
            continue
        events.append({"d": m["date"], "e": m.get("end"), "iso": (m.get("country") or "").upper() or None,
                       "type": m.get("type", "other"), "t_fr": m["title"], "t_en": m.get("title_en") or m["title"],
                       "note_fr": m.get("note", ""), "note_en": m.get("note_en") or m.get("note", ""),
                       "url": m.get("url") or None, "src": "Angor"})
    events = [{k: v for k, v in e.items() if v not in (None, "")} for e in events]
    events.sort(key=lambda e: (e["d"], e.get("iso") or ""))
    write_js("calendar.js", "VS_CALENDAR", {"generated": now.isoformat(), "from": start.isoformat(),
                                            "to": end.isoformat(), "events": events})
    return events


def upcoming(events, now, days=7, isos=None, types=None):
    """Événements des N prochains jours (pour le point quotidien)."""
    a, b = now.date().isoformat(), (now + timedelta(days=days)).date().isoformat()
    return [e for e in events if a <= e["d"] <= b and (not isos or e.get("iso") in isos or e.get("iso") is None)
            and (not types or e["type"] in types)]
