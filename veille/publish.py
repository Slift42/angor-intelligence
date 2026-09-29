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


def write_cities(min_pop=250000):
    """docs/data/cities.js : grandes villes → pays (pour que « My travel buddy » reconnaisse « Lagos » ou
    « Abuja »). Tiré du dictionnaire GeoNames déjà téléchargé (CC BY 4.0)."""
    src = ROOT / "data" / "geonames" / "cities15000.txt"
    if not src.exists():
        return 0
    rows = []
    with open(src, encoding="utf-8") as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 15 or not f[14].isdigit() or int(f[14]) < min_pop:
                continue
            rows.append([f[2] or f[1], f[8], round(float(f[4]), 3), round(float(f[5]), 3), int(f[14])])
    rows.sort(key=lambda r: -r[4])
    write_js("cities.js", "VS_CITIES", {"source": "GeoNames (CC BY 4.0)", "cities": rows})
    return len(rows)


def bust_cache():
    """Ajoute l'empreinte de chaque fichier de code dans les pages (app.js?v=1a2b3c4d) : après une mise à jour,
    le navigateur recharge le nouveau code au lieu de garder l'ancien en cache. Idempotent."""
    import hashlib
    import re
    docs = OUT_DIR.parent
    rx = re.compile(r'((?:src|href)=")([\w/.-]+\.(?:js|css))\?v=[^"]*"')
    for page in docs.glob("*.html"):
        text = page.read_text(encoding="utf-8")

        def sub(m):
            f = docs / m.group(2)
            v = hashlib.sha1(f.read_bytes()).hexdigest()[:8] if f.exists() else "0"
            return f'{m.group(1)}{m.group(2)}?v={v}"'
        new = rx.sub(sub, text)
        if new != text:
            page.write_text(new, encoding="utf-8")
