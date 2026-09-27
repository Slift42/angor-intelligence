"""Historique local et fichiers publiés pour la carte.

- data/store.json            : mémoire du robot (événements bruts, avis, état des sources). Non publié.
- docs/data/data.js          : tout ce que la carte affiche (lisible même en double-cliquant index.html)
- docs/data/events.geojson   : les mêmes événements au format standard GeoJSON (réutilisable ailleurs)
"""
import json
from datetime import timedelta

from .config import ROOT
from .model import parse_iso

STORE = ROOT / "data" / "store.json"
OUT_DIR = ROOT / "docs" / "data"


def load_store():
    if STORE.exists():
        with open(STORE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"events": {}, "news": {}, "econ": {}, "headlines": {}, "advisories": {}, "state": {}, "status": {}}


def save_store(store):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE, "w", encoding="utf-8") as fh:
        json.dump(store, fh, ensure_ascii=False, separators=(",", ":"))


def merge(store, new_events, new_news, now, retention_days, news_days=3, news_max=800,
          new_econ=(), econ_days=30, econ_per_country=25):
    for key in ("econ", "headlines"):
        store.setdefault(key, {})
    for e in new_econ:
        store["econ"].setdefault(e["id"], e)
    elimit = now - timedelta(days=econ_days)
    per = {}
    for e in sorted(store["econ"].values(), key=lambda x: x["date"], reverse=True):
        if parse_iso(e["date"]) >= elimit and len(per.setdefault(e["country"], [])) < econ_per_country:
            per[e["country"]].append(e)
    store["econ"] = {e["id"]: e for items in per.values() for e in items}
    seen = now.replace(microsecond=0).isoformat()
    for ev in new_events:
        old = store["events"].get(ev["id"])
        ev["first_seen"] = old.get("first_seen", seen) if old else seen
        store["events"][ev["id"]] = ev
    for n in new_news:
        store["news"].setdefault(n["id"], n)
    limit = now - timedelta(days=retention_days)
    store["events"] = {k: v for k, v in store["events"].items() if parse_iso(v["date"]) >= limit}
    nlimit = now - timedelta(days=news_days)
    news = sorted((n for n in store["news"].values() if parse_iso(n["date"]) >= nlimit),
                  key=lambda n: n["date"], reverse=True)[:news_max]
    store["news"] = {n["id"]: n for n in news}


def write_js(name, var, payload):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / name, "w", encoding="utf-8") as fh:
        fh.write(f"window.{var} = ")
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")


def write_outputs(payload):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "data.js", "w", encoding="utf-8") as fh:
        fh.write("/* Généré automatiquement par collecte.py – ne pas modifier à la main */\n")
        fh.write("window.VS_DATA = ")
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    features = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [e["lon"], e["lat"]]},
                 "properties": {k: v for k, v in e.items() if k not in ("lat", "lon")}}
                for e in payload["events"]]
    with open(OUT_DIR / "events.geojson", "w", encoding="utf-8") as fh:
        json.dump({"type": "FeatureCollection", "generated": payload["generated"], "features": features},
                  fh, ensure_ascii=False)


def write_archives(old_events):
    """Événements de plus de 30 jours : un fichier par mois (docs/data/archive/AAAA-MM.js)."""
    by_month = {}
    for e in old_events:
        by_month.setdefault(e["date"][:7], []).append(e)
    folder = OUT_DIR / "archive"
    folder.mkdir(parents=True, exist_ok=True)
    for month, evs in by_month.items():
        with open(folder / f"{month}.js", "w", encoding="utf-8") as fh:
            fh.write(f"(window.VS_ARCHIVE = window.VS_ARCHIVE || {{}})['{month}'] = ")
            json.dump(evs, fh, ensure_ascii=False, separators=(",", ":"))
            fh.write(";\n")
    for f in folder.glob("*.js"):
        if f.stem not in by_month:
            f.unlink()
    return {m: len(v) for m, v in sorted(by_month.items())}
