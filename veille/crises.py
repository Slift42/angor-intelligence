"""Chronologies de crise : regroupe les incidents d'une même crise sur plusieurs jours.

Deux incidents appartiennent à la même crise s'ils sont dans le même pays, de la même famille
(violences armées, troubles, intempéries, séisme, feux, santé, cyber…), proches dans l'espace et séparés
de moins de 72 h ; les liens s'enchaînent (A~B, B~C → A, B, C). Une chronologie est retenue si elle
s'étend sur au moins 2 jours avec 3 incidents, ou 2 incidents dont un grave.

Chaque chronologie donne : dates de début et de fin, nombre d'incidents et de sources, gravité maximale,
lieux touchés, comptes par jour, statut (active / apaisée), tendance (escalade, stable, décrue) et une
synthèse (automatique ; rédigée par l'IA si la tâche « crisis_summaries » est active).
"""
import hashlib
from collections import Counter
from datetime import timedelta

from . import llm
from .geo import haversine_km
from .model import CATEGORIES, parse_iso

# famille : (catégories, distance max en km)
FAMILIES = {
    "violence": ({"armed_conflict", "attack", "terrorism"}, 60),
    "unrest": ({"unrest", "political"}, 40),
    "crime": ({"crime"}, 25),
    "weather": ({"storm", "cyclone", "flood", "landslide", "extreme_temp"}, 300),
    "earthquake": ({"earthquake"}, 150),
    "wildfire": ({"wildfire"}, 60),
    "volcano": ({"volcano"}, 80),
    "health": ({"health"}, 800),
    "cyber": ({"cyber", "infrastructure"}, 400),
}
FAMILY_OF = {c: f for f, (cats, _) in FAMILIES.items() for c in cats}
LABELS = {"violence": ("Violences armées", "Armed violence"), "unrest": ("Troubles et crise politique", "Unrest and political crisis"),
          "crime": ("Criminalité", "Crime"), "weather": ("Intempéries", "Severe weather"), "earthquake": ("Séisme et répliques", "Earthquake and aftershocks"),
          "wildfire": ("Feux de forêt", "Wildfires"), "volcano": ("Activité volcanique", "Volcanic activity"),
          "health": ("Épidémie", "Outbreak"), "cyber": ("Cyber et infrastructures", "Cyber and infrastructure")}
GAP_H = 72


def _reliable(ev):
    tags = ev.get("tags") or []
    return ev.get("confidence") != "low" or "multi-source" in tags or ev.get("verified")


def _main_place(evs):
    places = Counter((e.get("place") or "").split(",")[0].strip() for e in evs if e.get("precision") != "country")
    places.pop("", None)
    return [p for p, _ in places.most_common(5)]


def build(events, now, days=30, store=None, settings=None, log=print, countries=None):
    since = now - timedelta(days=days)
    pool = [e for e in events if e.get("country") and e.get("lat") is not None and _reliable(e)
            and e["category"] in FAMILY_OF and parse_iso(e["date"]) >= since]
    groups = {}
    for e in pool:
        groups.setdefault((e["country"], FAMILY_OF[e["category"]]), []).append(e)
    crises = []
    for (iso, fam), evs in groups.items():
        evs.sort(key=lambda e: e["date"])
        ts = [parse_iso(e["date"]) for e in evs]
        parent = list(range(len(evs)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        dmax = FAMILIES[fam][1]
        for i in range(len(evs)):
            for j in range(i - 1, -1, -1):
                if (ts[i] - ts[j]).total_seconds() > GAP_H * 3600:
                    break
                same_place = evs[i].get("precision") == "country" or evs[j].get("precision") == "country"
                if same_place or haversine_km(evs[i]["lat"], evs[i]["lon"], evs[j]["lat"], evs[j]["lon"]) <= dmax:
                    parent[find(i)] = find(j)
        clusters = {}
        for i in range(len(evs)):
            clusters.setdefault(find(i), []).append(i)
        for idx in clusters.values():
            members = [evs[i] for i in idx]
            day_set = {e["date"][:10] for e in members}
            maxsev = max(e["severity"] for e in members)
            if len(day_set) < 2 or not (len(members) >= 3 or (len(members) >= 2 and maxsev >= 3)):
                continue
            crises.append(_describe(iso, fam, members, now, countries))
    crises.sort(key=lambda c: (c["status"] != "active", -c["max_severity"], -c["n"]))
    crises = crises[:80]
    # synthèses IA (si activées) pour les chronologies actives les plus importantes
    if store is not None and settings is not None:
        by_id = {e["id"]: e for e in pool}
        for c in [c for c in crises if c["status"] == "active"][:12]:
            s = llm.crisis_summary(c, [by_id[i] for i in c["events"] if i in by_id], store, settings, now, log)
            if isinstance(s, dict) and s.get("fr"):
                c["summary_fr"], c["summary_en"], c["summary_kind"] = s["fr"], s.get("en") or s["fr"], "ai"
    return crises


def _describe(iso, fam, members, now, countries=None):
    members.sort(key=lambda e: e["date"])
    first, last = members[0], members[-1]
    places = _main_place(members)
    name = countries.name(iso, "fr") if countries else iso
    name_en = countries.name(iso, "en") if countries else iso
    daily = {}
    for e in members:
        d = daily.setdefault(e["date"][:10], [0, 0])
        d[0] += 1
        d[1] = max(d[1], e["severity"])
    last_t = parse_iso(last["date"])
    status = "active" if now - last_t <= timedelta(hours=48) else "calmed"
    recent = sum(1 for e in members if parse_iso(e["date"]) >= now - timedelta(days=3))
    before = sum(1 for e in members if now - timedelta(days=6) <= parse_iso(e["date"]) < now - timedelta(days=3))
    trend = "escalating" if recent >= before + 2 and recent >= 1.5 * max(before, 1) else \
        "declining" if before >= recent + 2 else "stable"
    if status == "calmed":
        trend = "declining"
    elif now - parse_iso(first["date"]) <= timedelta(hours=72):
        trend = "new"
    peak_day = max(daily.items(), key=lambda kv: (kv[1][1], kv[1][0]))[0]
    cats = Counter(e["category"] for e in members)
    fr, en = LABELS[fam]
    where = places[0] if places else name
    sources = {s.get("name") if s.get("name") != "Press (via GDELT)" else s.get("url", "")[:40]
               for e in members for s in e.get("sources") or []}
    lats = [e["lat"] for e in members]
    lons = [e["lon"] for e in members]
    cid = "crisis-" + hashlib.sha1(f"{iso}{fam}{first['id']}".encode()).hexdigest()[:10]
    pl = ", ".join(places[:4]) or name
    summary_fr = (f"{len(members)} incidents ({', '.join(CATEGORIES[c]['fr'].lower() for c, _ in cats.most_common(3))}) "
                  f"du {first['date'][8:10]}/{first['date'][5:7]} au {last['date'][8:10]}/{last['date'][5:7]} : {pl}. "
                  f"Point culminant le {peak_day[8:10]}/{peak_day[5:7]} (gravité {daily[peak_day][1]}/4). "
                  + {"escalating": "Tendance à l'escalade sur les 3 derniers jours.", "declining": "Tendance à la décrue.",
                     "stable": "Activité stable.", "new": "Crise apparue ces 3 derniers jours."}[trend])
    summary_en = (f"{len(members)} incidents ({', '.join(CATEGORIES[c]['en'].lower() for c, _ in cats.most_common(3))}) "
                  f"from {first['date'][:10]} to {last['date'][:10]}: {pl}. Peak on {peak_day} (severity {daily[peak_day][1]}/4). "
                  + {"escalating": "Escalating over the last 3 days.", "declining": "De-escalating.", "stable": "Stable activity.",
                     "new": "Emerged in the last 3 days."}[trend])
    return {"id": cid, "country": iso, "family": fam, "category": cats.most_common(1)[0][0],
            "title": f"{fr} – {where}" + (f", {name}" if where != name else ""),
            "title_en": f"{en} – {where}" + (f", {name_en}" if where != name else ""),
            "start": first["date"], "last": last["date"], "n": len(members), "n_sources": len(sources),
            "max_severity": max(e["severity"] for e in members), "places": places, "daily": daily,
            "status": status, "trend": trend, "peak": peak_day,
            "bbox": [min(lats), min(lons), max(lats), max(lons)],
            "events": [e["id"] for e in members], "summary_fr": summary_fr, "summary_en": summary_en,
            "summary_kind": "auto"}
