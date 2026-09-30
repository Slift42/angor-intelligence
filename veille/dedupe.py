"""Fusion des doublons entre sources.

Un même séisme peut être signalé par l'USGS, GDACS et EONET. On fusionne deux événements
s'ils sont de la même famille, proches dans l'espace ET dans le temps, et issus de sources
différentes. On garde la fiche de la source la plus précise, la gravité la plus haute,
et la liste de toutes les sources (recoupement = confiance accrue).
"""
import re
import unicodedata

from .geo import haversine_km
from .model import parse_iso

# famille : (distance max en km, écart max en heures)
FAMILIES = {
    "earthquake": ("earthquake", 100, 3),
    "cyclone": ("storm", 400, 72), "storm": ("storm", 400, 72),
    "flood": ("flood", 150, 96), "wildfire": ("wildfire", 30, 72),
    "volcano": ("volcano", 50, 240), "drought": ("drought", 500, 720),
    "health": ("health", 300, 240),
    # incidents de sécurité : GDELT et presse locale se confirment mutuellement
    "attack": ("violence", 20, 24), "terrorism": ("violence", 20, 24), "armed_conflict": ("violence", 20, 24),
    "unrest": ("unrest", 15, 24),
}
# plus le chiffre est petit, plus la source fait référence pour la fiche fusionnée
# Sources dont deux fiches peuvent décrire le même événement : presse (plusieurs médias, plusieurs jours),
# GDELT, et alertes météo découpées par zone (un même épisode d'inondation couvre des dizaines de comtés).
SAME_SOURCE_OK = {"Press", "GDELT", "NWS", "Meteoalarm"}
STOP = set("the and for with from after amid over into near dans pour avec apres contre des les une sur par".split())


def _words(e):
    t = unicodedata.normalize("NFKD", e.get("headline") or e.get("title") or "").encode("ascii", "ignore").decode().lower()
    return {w for w in re.findall(r"[a-z]{4,}", t) if w not in STOP}


def _same_event(a, b, fam):
    """Deux fiches d'une même source : même épisode si les titres se ressemblent, ou même lieu pour des
    manifestations, ou même type d'alerte météo."""
    if a["source"] in ("NWS", "Meteoalarm"):
        return (a["title"].split(" – ")[0] == b["title"].split(" – ")[0]) and a.get("category") == b.get("category")
    wa, wb = _words(a), _words(b)
    jac = len(wa & wb) / max(1, len(wa | wb))
    if jac >= 0.3:
        return True
    return fam == "unrest" and a.get("place") and (a.get("place") or "").lower() == (b.get("place") or "").lower()


PRIORITY = {"USGS": 0, "WHO": 0, "NWS": 1, "Meteoalarm": 1, "GDACS": 1, "NASA EONET": 2, "GDELT": 3, "Press": 4}


def dedupe(events):
    buckets = {}
    for ev in events:
        fam = FAMILIES.get(ev["category"])
        if fam and ev["lat"] is not None:
            buckets.setdefault(fam[0], []).append(ev)
    merged_ids = set()
    replacements = {}
    for fam_name, items in buckets.items():
        _, max_km, max_h = next(v for v in FAMILIES.values() if v[0] == fam_name)
        items.sort(key=lambda e: PRIORITY.get(e["source"], 9))
        # index spatial en grille : on ne compare que les voisins proches (rapide même avec 10 000 événements)
        cell = max(max_km / 111.0, 0.05)
        grid = {}
        for idx, ev in enumerate(items):
            grid.setdefault((int(ev["lat"] // cell), int(ev["lon"] // cell)), []).append(idx)
        times = [parse_iso(e["date"]) for e in items]
        used = set()
        for i, a in enumerate(items):
            if a["id"] in used:
                continue
            group, srcs = [a], {a["source"]}
            same_ok = a["source"] in SAME_SOURCE_OK
            ci, cj = int(a["lat"] // cell), int(a["lon"] // cell)
            cand = sorted(j for di in (-1, 0, 1) for dj in (-1, 0, 1) for j in grid.get((ci + di, cj + dj), ()) if j > i)
            for j in cand:
                b = items[j]
                if b["id"] in used:
                    continue
                same = b["source"] in srcs
                if same and not (same_ok and b["source"] == a["source"]):
                    continue
                if abs((times[j] - times[i]).total_seconds()) > max_h * 3600:
                    continue
                if haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) > max_km:
                    continue
                if same and not _same_event(a, b, fam_name):
                    continue
                group.append(b)
                srcs.add(b["source"])
            if len(group) > 1:
                primary = dict(group[0])
                primary["severity"] = max(g["severity"] for g in group)
                primary["sources"] = [s for g in group for s in g["sources"]]
                primary["sources"] = primary["sources"][:25]
                multi = len({(x.get("site") or x.get("name") or "").lower() for x in primary["sources"]}) >= 2
                primary["tags"] = sorted(set(primary.get("tags", [])) | ({"multi-source"} if multi else set()))
                auto_only = all("auto-detected" in g.get("tags", []) for g in group)
                outlets = {(s.get("site") or s.get("name") or "").lower() for s in primary["sources"]}
                primary["confidence"] = "high" if not auto_only or len(outlets) >= 4 else "medium" if len(outlets) >= 2 else primary.get("confidence", "low")
                primary["date"] = max(g["date"] for g in group)  # dernière information connue
                primary["start"] = min(g.get("start") or g["date"] for g in group)
                if not primary.get("headline"):
                    primary["headline"] = next((g.get("headline") for g in group if g.get("headline")), "")
                primary["merged"] = [g["id"] for g in group[1:]]
                replacements[primary["id"]] = primary
                for g in group:
                    used.add(g["id"])
                    merged_ids.add(g["id"])
    out = []
    for ev in events:
        if ev["id"] in replacements:
            out.append(replacements[ev["id"]])
        elif ev["id"] not in merged_ids:
            out.append(ev)
    return out
