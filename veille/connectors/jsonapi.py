"""Connecteur générique pour une API JSON authentifiée (source payante ou sous licence).

Permet de brancher un nouveau fournisseur SANS écrire de code : on décrit dans
config/sources.json où se trouvent les champs dans sa réponse.

Exemple :
{
  "id": "fournisseur_x", "type": "jsonapi", "enabled": true, "name": "Fournisseur X",
  "url": "https://api.fournisseur-x.com/v1/alerts",
  "params": {"since": "24h"},
  "auth": {"type": "bearer", "env": "FOURNISSEUR_X_TOKEN"},
  "items_path": "data.alerts",
  "fields": {"id": "id", "title": "headline", "summary": "summary", "date": "published_at",
             "lat": "location.latitude", "lon": "location.longitude", "url": "link",
             "category": "type", "severity": "risk_level"},
  "category_map": {"Terrorism": "terrorism", "Civil Unrest": "unrest"},
  "severity_map": {"low": 1, "medium": 2, "high": 3, "extreme": 4}
}
"""
from .. import http
from ..model import make_event, parse_iso, to_iso

KIND = "events"


def _dig(obj, path):
    for part in path.split(".") if path else []:
        if isinstance(obj, list):
            obj = obj[int(part)] if part.isdigit() and int(part) < len(obj) else None
        elif isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


def fetch(cfg, ctx):
    data = http.get_json(cfg["url"], params=cfg.get("params"), auth=cfg.get("auth"),
                         headers=cfg.get("headers"))
    items = _dig(data, cfg.get("items_path", "")) if cfg.get("items_path") else data
    f = cfg["fields"]
    cmap, smap = cfg.get("category_map", {}), cfg.get("severity_map", {})
    out = []
    for it in items or []:
        lat, lon = _dig(it, f.get("lat")), _dig(it, f.get("lon"))
        if lat is None or lon is None:
            continue
        raw_cat, raw_sev = _dig(it, f.get("category")), _dig(it, f.get("severity"))
        sev = smap.get(str(raw_sev).lower(), raw_sev) if raw_sev is not None else cfg.get("severity", 2)
        date = parse_iso(str(_dig(it, f.get("date")) or "")) or ctx.now
        out.append(make_event(
            id=f"{cfg['id']}-{_dig(it, f.get('id'))}", source=cfg.get("name", cfg["id"]),
            category=cmap.get(raw_cat, raw_cat or cfg.get("category", "other")),
            severity=int(sev) if str(sev).isdigit() else 2,
            title=str(_dig(it, f.get("title")) or ""), summary=str(_dig(it, f.get("summary")) or ""),
            date=to_iso(date), lat=float(lat), lon=float(lon), url=_dig(it, f.get("url")) or "",
            precision=cfg.get("precision", "city"), country=ctx.countries.locate(float(lat), float(lon)),
            confidence=cfg.get("confidence", "high")))
    return out
