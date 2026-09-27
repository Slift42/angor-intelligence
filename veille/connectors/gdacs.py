"""GDACS (ONU / Commission européenne) – alertes catastrophes avec estimation d'impact.
https://www.gdacs.org – réutilisation avec attribution."""
from .. import http
from ..model import make_event, parse_iso, to_iso

KIND = "events"
URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/events4app"

CATEGORIES = {"EQ": "earthquake", "TC": "cyclone", "FL": "flood", "VO": "volcano",
              "DR": "drought", "WF": "wildfire", "TS": "earthquake"}
GRAVITES = {"green": 1, "orange": 3, "red": 4}


def fetch(cfg, ctx):
    data = http.get_json(cfg.get("url", URL))
    out = []
    for f in data.get("features", []):
        p = f.get("properties", {})
        if str(p.get("iscurrent", "true")).lower() != "true":
            continue
        geom = f.get("geometry") or {}
        if geom.get("type") != "Point":
            continue
        lon, lat = geom["coordinates"][:2]
        alert = str(p.get("alertlevel", "")).lower()
        severity = GRAVITES.get(alert, 1)
        category = CATEGORIES.get(p.get("eventtype"), "other")
        min_sev = cfg.get("min_severity_by_category", {}).get(category, cfg.get("min_severity", 1))
        if severity < min_sev:
            continue
        start = parse_iso(p.get("fromdate"))
        end = parse_iso(p.get("todate")) or start
        iso3 = p.get("iso3") or ""
        country_item = ctx.countries.by_iso3.get(iso3) if iso3 else None
        country = country_item["iso2"] if country_item else ctx.countries.locate(lat, lon)
        sev_text = (p.get("severitydata") or {}).get("severitytext", "")
        summary = f"GDACS {p.get('alertlevel', '')} alert. {sev_text}".strip()
        if p.get("country"):
            summary += f" Affected: {p['country']}."
        url = (p.get("url") or {}).get("report") or "https://www.gdacs.org"
        out.append(make_event(
            id=f"gdacs-{p.get('eventtype')}-{p.get('eventid')}", source="GDACS",
            category=category, severity=severity,
            title=p.get("name") or p.get("eventname") or "GDACS alert", summary=summary,
            date=to_iso(end), start=to_iso(start) if start else None, lat=lat, lon=lon, url=url,
            place=p.get("country") or "", precision="region", country=country,
        ))
    return out
