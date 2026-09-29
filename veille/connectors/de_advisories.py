"""Auswärtiges Amt (Allemagne) – Reise- und Sicherheitshinweise, données ouvertes (sans clé).
https://www.auswaertiges-amt.de/opendata/travelwarning → {"response": {"contentList": [...], "<id>": {...}}}
Chaque pays : countryCode (ISO2), warning (avertissement de voyage), partialWarning (avertissement partiel),
situationWarning / situationPartWarning (mise en garde liée à la situation, pays entier ou partie).
Niveaux Angor (échelle MEAE, 1 à 4) :
  4 Reisewarnung (tout le pays) · 3 Teilreisewarnung (une partie) · 2 mise en garde de situation · 1 aucune."""
from datetime import datetime, timezone

from .. import http

KIND = "advisories"
URL = "https://www.auswaertiges-amt.de/opendata/travelwarning"
PAGE = "https://www.auswaertiges-amt.de/de/ReiseUndSicherheit/reise-und-sicherheitshinweise"
LABELS = {4: "Reisewarnung (avertissement de voyage)", 3: "Teilreisewarnung (avertissement partiel)",
          2: "Sicherheitshinweis (mise en garde liée à la situation)", 1: "Pas d'avertissement"}


def level_of(it):
    if it.get("warning"):
        return 4
    if it.get("partialWarning"):
        return 3
    if it.get("situationWarning") or it.get("situationPartWarning"):
        return 2
    return 1


def fetch(cfg, ctx):
    data = http.get_json(cfg.get("url", URL), timeout=40)
    resp = data.get("response", data)
    ids = resp.get("contentList") or [k for k, v in resp.items() if isinstance(v, dict)]
    out = {}
    for cid in ids:
        it = resp.get(str(cid))
        if not isinstance(it, dict):
            continue
        item = ctx.countries.get((it.get("countryCode") or "").upper()) or \
            ctx.countries.by_iso3.get((it.get("iso3CountryCode") or "").upper())
        if not item:
            continue
        lvl = level_of(it)
        ts = it.get("lastModified") or it.get("effective")
        updated = datetime.fromtimestamp(ts / 1000 if ts and ts > 1e11 else ts, tz=timezone.utc).date().isoformat() if ts else None
        out[item["iso2"]] = {"level": lvl, "max": lvl, "scale": 4, "label": LABELS[lvl],
                             "parts": bool(it.get("partialWarning") or it.get("situationPartWarning")),
                             "url": PAGE, "title": it.get("title", ""), "updated": updated}
    if not out:
        raise RuntimeError("aucun pays reconnu dans la réponse")
    return out
