"""Fusion des doublons entre sources.

Un même séisme peut être signalé par l'USGS, GDACS et EONET. On fusionne deux événements
s'ils sont de la même famille, proches dans l'espace ET dans le temps, et issus de sources
différentes. On garde la fiche de la source la plus précise, la gravité la plus haute,
et la liste de toutes les sources (recoupement = confiance accrue).

v0.23 : avant ce passage, un regroupement « par histoire » (story_merge) rassemble les titres de presse et de GDELT
qui racontent la même chose malgré des lieux, des jours ou des catégories différents : même dépêche reprise plusieurs
jours de suite, même article placé dans deux villes, bilan mis à jour (« 9 morts » puis « 10 morts »), titre Google
News suivi d'un texte parasite, même crash classé « attaque » ici et « infrastructure » là.
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


# ------------------------------------------------------------------ regroupement par histoire (v0.23)
STORY_SOURCES = {"Press", "GDELT"}
STORY_HOURS = 120          # une même histoire se raconte sur 5 jours au plus
STORY_KM = 100             # règle A : même pays, lieux proches, moins de 48 h d'écart…
STORY_SIMILAR_HOURS = 48   # (au-delà, deux bilans quotidiens semblables sont deux événements)
STORY_SIMILAR = 0.5        # … et titres semblables (indice de Jaccard sur les mots significatifs)
STORY_SAME = 0.8           # règle B : titres quasi identiques, où que ce soit
STORY_PREFIX = 8           # règle C : mêmes 8 premiers mots (titre suivi d'un texte parasite)
STORY_TOKENS = 14
PRECISION_RANK = {"exact": 0, "city": 1, "region": 2, "country": 3}
STORY_STOP = set(("the and for with from after amid over into near this that than are was were has have its their "
                  "dans pour avec apres contre des les une sur par aux est ont qui que del las los por con tras para "
                  "una uno que sus der die das und mit von den dem nach bei des della delle degli per con nel dai "
                  "says said say dit selon segun news live direct video photos").split())


def _story_text(e):
    """Texte qui raconte l'événement : titre réel de l'article pour GDELT (son titre est un code + un lieu)."""
    t = (e.get("headline") if e.get("source") == "GDELT" else e.get("title")) or ""
    t = re.sub(r"https?://\S+", " ", t)
    t = re.split(r"\s[|–—]\s|\s-\s(?=[A-Z][^-]{0,40}$)", t)[0]   # « … - Le Monde », « … | France 24 »
    return t


def story_tokens(e):
    t = unicodedata.normalize("NFKD", _story_text(e)).encode("ascii", "ignore").decode().lower()
    words = [w for w in re.findall(r"[a-z]{3,}", t) if w not in STORY_STOP]
    return words[:STORY_TOKENS]


def _same_story(a, b, ta, tb, hours):
    if hours > STORY_HOURS or not ta or not tb:
        return False
    sa, sb = set(ta), set(tb)
    jac = len(sa & sb) / len(sa | sb)
    if jac >= STORY_SAME and min(len(sa), len(sb)) >= 4:
        return True
    n = min(len(ta), len(tb))
    if n >= STORY_PREFIX and ta[:STORY_PREFIX] == tb[:STORY_PREFIX]:
        return True
    if jac >= STORY_SIMILAR and hours <= STORY_SIMILAR_HOURS and min(len(sa), len(sb)) >= 3 \
            and a.get("country") and a.get("country") == b.get("country"):
        same_place = (a.get("place") or "").lower() == (b.get("place") or "").lower() and a.get("place")
        if same_place or (a.get("lat") is not None and b.get("lat") is not None
                          and haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) <= STORY_KM):
            return True
    return False


def _combine(group):
    """Fiche fusionnée : la première du groupe sert de base ; gravité max, dernière date, toutes les sources."""
    primary = dict(group[0])
    primary["severity"] = max(g.get("severity") or 1 for g in group)
    primary["sources"] = [x for g in group for x in (g.get("sources") or [])][:25]
    outlets = {(x.get("site") or x.get("name") or "").lower() for x in primary["sources"]}
    tags = set(primary.get("tags") or [])
    primary["tags"] = sorted(tags | ({"multi-source"} if len(outlets) >= 2 else set()))
    auto_only = all("auto-detected" in (g.get("tags") or []) for g in group)
    primary["confidence"] = "high" if not auto_only or len(outlets) >= 4 else "medium" if len(outlets) >= 2 \
        else primary.get("confidence", "low")
    primary["date"] = max(g["date"] for g in group)  # dernière information connue
    primary["start"] = min(g.get("start") or g["date"] for g in group)
    if not primary.get("headline"):
        primary["headline"] = next((g.get("headline") for g in group if g.get("headline")), "")
    primary["merged"] = list(dict.fromkeys(list(primary.get("merged") or []) +
                                           [i for g in group[1:] for i in [g["id"]] + list(g.get("merged") or [])]))
    return primary


def story_merge(events):
    """Rassemble les titres de presse et de GDELT qui racontent la même histoire (voir l'en-tête du module)."""
    items = [e for e in events if e.get("source") in STORY_SOURCES and e.get("date")]
    if len(items) < 2:
        return events
    toks = [story_tokens(e) for e in items]
    times = [parse_iso(e["date"]) for e in items]
    index = {}
    for i, ws in enumerate(toks):
        for w in set(ws):
            index.setdefault(w, []).append(i)
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, ws in enumerate(toks):
        shared = {}
        for w in set(ws):
            posting = index[w]
            if len(posting) > 300:        # mot trop courant (« attack », « police ») : pas un indice d'histoire
                continue
            for j in posting:
                if j > i:
                    shared[j] = shared.get(j, 0) + 1
        for j, n in shared.items():
            if n < 2 or find(i) == find(j):
                continue
            hours = abs((times[j] - times[i]).total_seconds()) / 3600
            if _same_story(items[i], items[j], ws, toks[j], hours):
                parent[find(j)] = find(i)
    groups = {}
    for i in range(len(items)):
        groups.setdefault(find(i), []).append(items[i])
    replace, gone = {}, set()
    for group in groups.values():
        if len(group) < 2:
            continue
        # base : le lieu le plus précis, puis la presse (titre lisible), puis le plus ancien signalement
        group.sort(key=lambda e: (PRECISION_RANK.get(e.get("precision"), 4), e.get("source") != "Press",
                                  e.get("start") or e["date"]))
        merged = _combine(group)
        replace[merged["id"]] = merged
        gone |= {g["id"] for g in group[1:]}
    if not replace:
        return events
    return [replace.get(e["id"], e) for e in events if e["id"] not in gone]


def dedupe(events):
    events = story_merge(events)
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
                primary = _combine(group)
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
