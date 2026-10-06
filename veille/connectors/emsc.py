"""EMSC – Centre sismologique euro-méditerranéen (seismicportal.eu, licence CC BY 4.0). v0.25

Deuxième réseau sismologique mondial, indépendant de l'USGS : chaque séisme signalé par les deux est recoupé
(fusion par lieu et heure dans veille/dedupe.py → deux sources officielles, confiance haute), et un écart de
magnitude important est signalé dans la fiche. L'EMSC est aussi plus rapide et plus fin sur l'Europe, la
Méditerranée et le Moyen-Orient (réseaux nationaux : INGV, AFAD, NOA…).

Service FDSN : https://www.seismicportal.eu/fdsnws/event/1/query?format=json&minmag=4&limit=200
Format GeoJSON : properties.{unid, time, lastupdate, lat, lon, depth, mag, magtype, flynn_region, evtype, auth}
"""
from datetime import datetime, timedelta, timezone

from .. import http
from ..model import make_event, parse_iso, to_iso
from .usgs import gravite

KIND = "events"
URL = "https://www.seismicportal.eu/fdsnws/event/1/query"


def fetch(cfg, ctx):
    since = datetime.now(timezone.utc) - timedelta(hours=int(cfg.get("hours", 48)))
    params = {"format": "json", "minmag": cfg.get("min_magnitude", 4.0), "limit": int(cfg.get("limit", 300)),
              "starttime": since.strftime("%Y-%m-%dT%H:%M:%S"), "orderby": "time"}
    data = http.get_json(URL, params=params)
    out = []
    for f in data.get("features", []):
        p = f.get("properties") or {}
        mag = p.get("mag")
        if mag is None or float(mag) < float(cfg.get("min_magnitude", 4.0)):
            continue
        if (p.get("evtype") or "ke") not in ("ke", "se", ""):   # ke = séisme connu ; explosions, carrières… écartées
            continue
        coords = (f.get("geometry") or {}).get("coordinates") or []
        lat = p.get("lat", coords[1] if len(coords) > 1 else None)
        lon = p.get("lon", coords[0] if coords else None)
        if lat is None or lon is None or not p.get("time"):
            continue
        mag = round(float(mag), 1)
        region = (p.get("flynn_region") or "").title()
        depth = p.get("depth")
        summary = f"Magnitude {mag} ({p.get('magtype') or ''})" + (f", depth {round(float(depth))} km" if depth is not None else "")
        if p.get("auth"):
            summary += f". Reporting agency: {p['auth']}"
        uid = p.get("unid") or f.get("id")
        out.append(make_event(
            id=f"emsc-{uid}", source="EMSC", category="earthquake", severity=gravite(mag, None, False),
            title=f"M {mag} – {region}" if region else f"M {mag} earthquake", summary=summary,
            date=to_iso(parse_iso(p["time"])), lat=float(lat), lon=float(lon),
            url=f"https://www.seismicportal.eu/eventdetails.html?unid={uid}", place=region,
            precision="exact", country=ctx.countries.locate(float(lat), float(lon)),
        ))
    return out
