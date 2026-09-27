"""NASA EONET – événements naturels en cours (domaine public). https://eonet.gsfc.nasa.gov"""
from .. import http
from ..model import make_event, parse_iso, to_iso

KIND = "events"
URL = "https://eonet.gsfc.nasa.gov/api/v3/events"

CATEGORIES = {
    "wildfires": "wildfire", "severeStorms": "storm", "volcanoes": "volcano", "floods": "flood",
    "earthquakes": "earthquake", "landslides": "landslide", "drought": "drought",
    "tempExtremes": "extreme_temp", "snow": "storm", "dustHaze": "other", "manmade": "infrastructure",
}
CYCLONE_WORDS = ("tropical", "hurricane", "typhoon", "cyclone")


def _point(geom):
    coords = geom.get("coordinates")
    if geom.get("type") == "Point":
        return coords[1], coords[0]
    ring = coords[0]
    return sum(p[1] for p in ring) / len(ring), sum(p[0] for p in ring) / len(ring)


def _severity(category, geom, title):
    mag, unit = geom.get("magnitudeValue"), (geom.get("magnitudeUnit") or "").lower()
    if category in ("storm", "cyclone") and mag and unit == "kts":
        if mag >= 96:
            return 4
        if mag >= 64:
            return 3
        if mag >= 34:
            return 2
    if category == "volcano":
        return 2
    return 1


def fetch(cfg, ctx):
    params = {"status": "open", "days": cfg.get("days", 30), "limit": cfg.get("limit", 300)}
    data = http.get_json(cfg.get("url", URL), params=params)
    exclude = set(cfg.get("exclude_categories", ["seaLakeIce", "waterColor"]))
    out = []
    for e in data.get("events", []):
        cats = [c["id"] for c in e.get("categories", [])]
        if not cats or cats[0] in exclude or not e.get("geometry"):
            continue
        category = CATEGORIES.get(cats[0], "other")
        title = e.get("title", "")
        if category == "storm" and any(w in title.lower() for w in CYCLONE_WORDS):
            category = "cyclone"
        last, first = e["geometry"][-1], e["geometry"][0]
        lat, lon = _point(last)
        sources = e.get("sources") or []
        url = sources[0]["url"] if sources else e.get("link")
        summary = ""
        if last.get("magnitudeValue"):
            summary = f"Latest measure: {last['magnitudeValue']} {last.get('magnitudeUnit') or ''}".strip()
        if sources:
            summary += (". " if summary else "") + "Reported by " + ", ".join(s["id"] for s in sources)
        out.append(make_event(
            id=f"eonet-{e['id']}", source="NASA EONET", category=category,
            severity=_severity(category, last, title), title=title, summary=summary,
            date=to_iso(parse_iso(last["date"])), start=to_iso(parse_iso(first["date"])),
            lat=lat, lon=lon, url=url, precision="exact" if last.get("type") == "Point" else "region",
            country=ctx.countries.locate(lat, lon), source_url=e.get("link"),
        ))
    return out
