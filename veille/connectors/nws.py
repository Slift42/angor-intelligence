"""NWS (National Weather Service, États-Unis) – alertes météo officielles « Severe » et « Extreme ».

API publique et gratuite (domaine public) : https://api.weather.gov/alerts/active
Le service demande un User-Agent identifiable (fourni par veille/http.py).
Position : centre du polygone d'alerte ; à défaut, centre de l'État concerné (précision « région »).
Les alertes maritimes (houle, embruns verglaçants…) sont ignorées.
"""
import hashlib
import re

from .. import http
from ..model import make_event, parse_iso, to_iso

KIND = "events"
URL = "https://api.weather.gov/alerts/active"
SEV = {"Extreme": 4, "Severe": 3}
# centre approximatif de chaque État (lat, lon) et code FIPS
STATES = {
    "AL": ("01", 32.8, -86.8), "AK": ("02", 64.0, -152.0), "AZ": ("04", 34.3, -111.7), "AR": ("05", 34.9, -92.4),
    "CA": ("06", 37.2, -119.5), "CO": ("08", 39.0, -105.5), "CT": ("09", 41.6, -72.7), "DE": ("10", 39.0, -75.5),
    "DC": ("11", 38.9, -77.0), "FL": ("12", 28.6, -82.4), "GA": ("13", 32.7, -83.4), "HI": ("15", 20.3, -156.4),
    "ID": ("16", 44.4, -114.6), "IL": ("17", 40.0, -89.2), "IN": ("18", 39.9, -86.3), "IA": ("19", 42.1, -93.5),
    "KS": ("20", 38.5, -98.4), "KY": ("21", 37.5, -85.3), "LA": ("22", 31.1, -92.0), "ME": ("23", 45.4, -69.2),
    "MD": ("24", 39.0, -76.8), "MA": ("25", 42.3, -71.8), "MI": ("26", 44.3, -85.4), "MN": ("27", 46.3, -94.3),
    "MS": ("28", 32.7, -89.7), "MO": ("29", 38.4, -92.5), "MT": ("30", 47.0, -109.6), "NE": ("31", 41.5, -99.8),
    "NV": ("32", 39.3, -116.6), "NH": ("33", 43.7, -71.6), "NJ": ("34", 40.2, -74.7), "NM": ("35", 34.4, -106.1),
    "NY": ("36", 42.9, -75.5), "NC": ("37", 35.6, -79.4), "ND": ("38", 47.5, -100.5), "OH": ("39", 40.3, -82.8),
    "OK": ("40", 35.6, -97.5), "OR": ("41", 43.9, -120.6), "PA": ("42", 40.9, -77.8), "RI": ("44", 41.7, -71.5),
    "SC": ("45", 33.9, -80.9), "SD": ("46", 44.4, -100.2), "TN": ("47", 35.9, -86.4), "TX": ("48", 31.5, -99.3),
    "UT": ("49", 39.3, -111.7), "VT": ("50", 44.1, -72.7), "VA": ("51", 37.5, -78.9), "WA": ("53", 47.4, -120.5),
    "WV": ("54", 38.6, -80.6), "WI": ("55", 44.6, -89.9), "WY": ("56", 43.0, -107.6), "PR": ("72", 18.2, -66.5),
    "GU": ("66", 13.44, 144.79), "VI": ("78", 18.34, -64.9), "AS": ("60", -14.3, -170.7), "MP": ("69", 15.2, 145.75),
}
FIPS = {v[0]: k for k, v in STATES.items()}
MARINE = re.compile(r"marine|small craft|gale|freezing spray|hazardous seas|storm warning$|hurricane force wind|"
                    r"special marine|brisk wind|low water|rip current|beach hazards|high surf", re.I)
CATS = [(r"tornado", "storm"), (r"hurricane|tropical storm|typhoon", "cyclone"), (r"flood|hydrologic", "flood"),
        (r"fire|red flag", "wildfire"), (r"heat|cold|freeze|frost|wind chill|hypothermia", "extreme_temp"),
        (r"blizzard|winter|ice storm|snow|dust|wind|thunderstorm|storm", "storm"), (r"tsunami", "flood"),
        (r"volcan|ash", "volcano"), (r"avalanche|debris flow", "landslide"),
        (r"civil|law enforcement|shelter|evacuation|nuclear|hazardous materials|radiological|911", "infrastructure")]


def category(event):
    for rx, cat in CATS:
        if re.search(rx, event, re.I):
            return cat
    return "other"


def _centroid(geom):
    if not geom:
        return None
    coords = geom.get("coordinates") or []
    if geom.get("type") == "MultiPolygon":
        coords = [ring for poly in coords for ring in poly]
    pts = [p for ring in coords for p in ring]
    if not pts:
        return None
    return sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts)


def _state_point(props):
    gc = props.get("geocode") or {}
    codes = [u[:2] for u in gc.get("UGC") or []] + [FIPS.get(s[1:3]) for s in gc.get("SAME") or [] if len(s) == 6]
    for c in codes:
        if c in STATES:
            return STATES[c][1], STATES[c][2], c
    return None


def fetch(cfg, ctx):
    params = {"status": "actual", "message_type": "alert,update",
              "severity": ",".join(cfg.get("severities", ["Extreme", "Severe"]))}
    data = http.get_json(URL, params=params, headers={"Accept": "application/geo+json"}, timeout=40)
    out, seen = [], set()
    for f in data.get("features", []):
        p = f.get("properties") or {}
        ev_name = p.get("event") or ""
        if MARINE.search(ev_name) or p.get("severity") not in SEV:
            continue
        if p.get("urgency") in ("Past",) or p.get("certainty") in ("Unlikely",):
            continue
        c = _centroid(f.get("geometry"))
        precision = "region"
        if c:
            lat, lon = c
            precision = "exact" if (f.get("geometry") or {}).get("type") == "Polygon" else "region"
        else:
            sp = _state_point(p)
            if not sp:
                continue
            lat, lon, _ = sp
        area = p.get("areaDesc") or ""
        key = (ev_name, area[:120])
        if key in seen:  # même alerte réémise (mise à jour) : une seule fiche
            continue
        seen.add(key)
        sent = parse_iso(p.get("sent") or p.get("effective"))
        if not sent:
            continue
        desc = re.sub(r"\s+", " ", p.get("description") or "").strip()
        summary = (p.get("headline") or "") + (". " + desc[:320] if desc else "")
        uid = hashlib.sha1((ev_name + area).encode()).hexdigest()[:12]
        out.append(make_event(
            id=f"nws-{uid}-{sent:%Y%m%d}", source="NWS", category=category(ev_name), severity=SEV[p["severity"]],
            title=f"{ev_name} – {area[:110]}{'…' if len(area) > 110 else ''}", summary=summary,
            date=to_iso(sent), start=to_iso(parse_iso(p.get("onset")) or sent), lat=lat, lon=lon,
            url=p.get("@id") or "https://www.weather.gov/", source_url="https://alerts.weather.gov/",
            place=area[:160], precision=precision, country=ctx.countries.locate(lat, lon) or "US",
            confidence="high" if p.get("certainty") in ("Observed", "Likely") else "medium",
        ))
    ctx.log(f"  NWS : {len(out)} alerte(s) sévère(s) ou extrême(s)")
    return out
