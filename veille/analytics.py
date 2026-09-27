"""Statistiques pour les graphiques et les rapports pays."""
from datetime import timedelta

from .model import CATEGORIES, parse_iso

WINDOWS = {"24h": 1, "72h": 3, "7d": 7, "30d": 30, "90d": 90}


def country_stats(events, now):
    """Nombre d'incidents par pays, par fenêtre de temps, par catégorie et par gravité."""
    out = {}
    for ev in events:
        iso = ev.get("country")
        if not iso:
            continue
        age = now - parse_iso(ev["date"])
        for w, days in WINDOWS.items():
            if age > timedelta(days=days):
                continue
            s = out.setdefault(iso, {}).setdefault(w, {"total": 0, "by_cat": {}, "by_sev": {}})
            s["total"] += 1
            s["by_cat"][ev["category"]] = s["by_cat"].get(ev["category"], 0) + 1
            k = str(ev["severity"])
            s["by_sev"][k] = s["by_sev"].get(k, 0) + 1
    return out


def global_series(events, now, days=90):
    """Séries quotidiennes (90 jours) par famille et par gravité, et répartitions."""
    start = (now - timedelta(days=days - 1)).date()
    dates = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    index = {d: i for i, d in enumerate(dates)}
    groups = {g: [0] * days for g in ("security", "political", "natural", "health", "infrastructure")}
    sev = {str(s): [0] * days for s in (1, 2, 3, 4)}
    by_source = {}
    for ev in events:
        d = parse_iso(ev["date"]).date().isoformat()
        i = index.get(d)
        if i is None:
            continue
        g = CATEGORIES.get(ev["category"], {}).get("group", "natural")
        groups[g][i] += 1
        sev[str(ev["severity"])][i] += 1
        by_source[ev["source"]] = by_source.get(ev["source"], 0) + 1
    return {"dates": dates, "groups": groups, "severity": sev, "by_source": by_source}
