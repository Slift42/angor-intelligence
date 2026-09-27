"""Gouvernement du Canada – Conseils aux voyageurs (Licence du gouvernement ouvert).
advisory-state : 0 précautions normales · 1 grande prudence · 2 éviter les voyages non essentiels
                 · 3 éviter tout voyage"""
from .. import http

KIND = "advisories"
URL = "https://data.international.gc.ca/travel-voyage/index-updated.json"
LABELS = {0: "Take normal security precautions", 1: "Exercise a high degree of caution",
          2: "Avoid non-essential travel", 3: "Avoid all travel"}


def fetch(cfg, ctx):
    data = http.get_json(cfg.get("url", URL))
    entries = data.get("data", data)
    out = {}
    for code, it in entries.items():
        if not isinstance(it, dict):
            continue
        iso = it.get("country-iso") or code
        try:
            state = int(it.get("advisory-state"))
        except (TypeError, ValueError):
            continue
        item = ctx.countries.get(iso)
        if not item:
            continue
        out[item["iso2"]] = {"level": state + 1, "scale": 4, "label": LABELS.get(state, ""),
                             "url": "https://travel.gc.ca/travelling/advisories",
                             "updated": (it.get("date-published") or {}).get("date")
                             if isinstance(it.get("date-published"), dict) else it.get("date-published")}
    return out
