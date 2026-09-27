"""USGS – séismes mondiaux (domaine public). https://earthquake.usgs.gov"""
from datetime import datetime, timezone

from .. import http
from ..model import make_event, to_iso

KIND = "events"
BASE = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{feed}.geojson"
PAGER = {"green": 1, "yellow": 2, "orange": 3, "red": 4}


def gravite(magnitude, alert, tsunami):
    """Priorité à l'alerte PAGER (impact humain estimé) ; sinon, magnitude."""
    if alert in PAGER:
        level = PAGER[alert]
    elif magnitude is None:
        level = 1
    elif magnitude >= 7:
        level = 4
    elif magnitude >= 6:
        level = 3
    elif magnitude >= 5:
        level = 2
    else:
        level = 1
    if tsunami:
        level += 1
    return min(level, 4)


def fetch(cfg, ctx):
    data = http.get_json(BASE.format(feed=cfg.get("feed", "2.5_day")))
    min_mag = cfg.get("min_magnitude", 4.0)
    out = []
    for f in data.get("features", []):
        p = f["properties"]
        mag = p.get("mag")
        if mag is None or mag < min_mag:
            continue
        lon, lat = f["geometry"]["coordinates"][:2]
        date = to_iso(datetime.fromtimestamp(p["time"] / 1000, tz=timezone.utc))
        depth = f["geometry"]["coordinates"][2] if len(f["geometry"]["coordinates"]) > 2 else None
        summary = f"Magnitude {mag} ({p.get('magType', '')})"
        if depth is not None:
            summary += f", depth {round(depth)} km"
        if p.get("alert"):
            summary += f". USGS PAGER alert: {p['alert']}"
        if p.get("tsunami"):
            summary += ". Tsunami flag raised"
        out.append(make_event(
            id=f"usgs-{f['id']}", source="USGS", category="earthquake",
            severity=gravite(mag, p.get("alert"), p.get("tsunami")),
            title=p.get("title") or f"M {mag} earthquake", summary=summary,
            date=date, lat=lat, lon=lon, url=p.get("url"), place=p.get("place") or "",
            precision="exact", country=ctx.countries.locate(lat, lon),
        ))
    return out
