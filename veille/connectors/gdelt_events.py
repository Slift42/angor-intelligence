"""GDELT 2.0 Events – événements de sécurité détectés automatiquement dans la presse mondiale
(65 langues), codés selon la nomenclature CAMEO et géolocalisés. Mise à jour toutes les 15 min.
Libre, y compris usage commercial (citer GDELT). https://www.gdeltproject.org

⚠ Détection automatique non vérifiée : bruit, erreurs de lieu, faits anciens repris par la presse.
   D'où les filtres ci-dessous et l'indice de confiance affiché sur la carte.
"""
import csv
import io
import zipfile
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone

from .. import http
from ..model import make_event, to_iso

KIND = "events"
BASE = "http://data.gdeltproject.org/gdeltv2/"

# Colonnes du fichier « export » GDELT 2.0 (61 colonnes, séparées par des tabulations)
C = {"id": 0, "sqldate": 1, "actor1": 6, "actor1_cc": 7, "actor2": 16, "actor2_cc": 17, "is_root": 25, "code": 26, "root": 28,
     "sources": 32, "articles": 33, "tone": 34, "geo_type": 51, "geo_name": 52, "geo_cc": 53,
     "lat": 56, "lon": 57, "feature": 58, "added": 59, "url": 60}

# code CAMEO → (catégorie, gravité, libellé anglais)
CAMEO = {
    "140": ("unrest", 1, "Protest"), "141": ("unrest", 1, "Demonstration / rally"),
    "142": ("unrest", 1, "Hunger strike"), "143": ("unrest", 1, "Strike / boycott"),
    "144": ("unrest", 1, "Blockade / obstruction"), "145": ("unrest", 2, "Violent protest / riot"),
    "180": ("attack", 2, "Unconventional violence"), "181": ("attack", 2, "Abduction / hostage-taking"),
    "182": ("crime", 1, "Physical assault"), "183": ("attack", 3, "Bombing"),
    "184": ("attack", 2, "Use as human shield"), "185": ("attack", 3, "Assassination attempt"),
    "186": ("attack", 3, "Assassination"), "190": ("armed_conflict", 2, "Military force"),
    "191": ("armed_conflict", 2, "Military blockade"), "192": ("armed_conflict", 3, "Occupation of territory"),
    "193": ("armed_conflict", 2, "Armed clashes (small arms)"),
    "194": ("armed_conflict", 3, "Artillery / tank fire"), "195": ("armed_conflict", 3, "Airstrike"),
    "196": ("armed_conflict", 2, "Ceasefire violation"), "200": ("armed_conflict", 4, "Mass violence"),
    "201": ("armed_conflict", 4, "Mass expulsion"), "202": ("armed_conflict", 4, "Mass killing"),
    "203": ("armed_conflict", 4, "Ethnic cleansing"), "204": ("armed_conflict", 4, "Weapons of mass destruction"),
}
PRECISION = {"1": "country", "2": "region", "3": "city", "4": "city", "5": "region"}


def _stamp(dt):
    return dt.strftime("%Y%m%d%H%M%S")


def _intervals(last_done, latest, max_files):
    """Liste des horodatages (tranches de 15 min) à télécharger depuis la dernière exécution."""
    stamps, t = [], latest
    while len(stamps) < max_files and (last_done is None or t > last_done):
        stamps.append(t)
        t -= timedelta(minutes=15)
    return list(reversed(stamps))


def _rows(stamp, log):
    url = f"{BASE}{_stamp(stamp)}.export.CSV.zip"
    try:
        raw = http.get(url, retries=1, timeout=60).content
    except Exception as exc:  # un fichier manquant ne doit pas bloquer les autres
        log(f"  GDELT {_stamp(stamp)} indisponible : {exc}")
        return []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        text = z.read(z.namelist()[0]).decode("utf-8", errors="replace")
    return list(csv.reader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE))


FILTER_VERSION = 2  # à incrémenter quand les filtres changent : l'historique GDELT est alors reconstruit

# Seuils de publication : (articles minimum, sites de presse distincts minimum)
# « calme » = pays dont aucun gouvernement ne déconseille le voyage (avis ≤ 2/4 ou inconnu)
DEFAULT_THRESHOLDS = {
    "calm": {"14": [3, 2], "18": [6, 2], "19": [20, 3], "20": [20, 3]},
    "tense": {"14": [3, 1], "18": [3, 2], "19": [3, 2], "20": [3, 2]},
}


def _domain(url):
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _max_advisory(ctx, iso2):
    levels = [a[iso2]["level"] for a in getattr(ctx, "advisories", {}).values() if iso2 in a]
    return max(levels) if levels else 0


def fetch(cfg, ctx):
    if ctx.state.get("gdelt_filter_version") != FILTER_VERSION:
        ctx.log("  GDELT : filtres mis à jour, reconstruction de l'historique")
        ctx.purge.append("gdelt-")
        ctx.state.pop("gdelt_last", None)
        ctx.state["gdelt_filter_version"] = FILTER_VERSION
    latest_line = http.get(BASE + "lastupdate.txt").text.split("\n")[0]
    latest = datetime.strptime(latest_line.split("/")[-1][:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    last_done = ctx.state.get("gdelt_last")
    last_done = datetime.fromisoformat(last_done) if last_done else None
    max_files = int(cfg.get("backfill_hours", 12) * 4) if last_done is None else int(cfg.get("max_files_per_run", 16))
    stamps = _intervals(last_done, latest, max_files)
    ctx.log(f"  GDELT : {len(stamps)} fichier(s) de 15 min à lire")

    roots = set(cfg.get("root_codes", ["14", "18", "19", "20"]))
    geo_types = set(cfg.get("geo_types", ["2", "3", "4", "5"]))
    max_age = timedelta(days=int(cfg.get("max_event_age_days", 3)))
    thresholds = cfg.get("thresholds", DEFAULT_THRESHOLDS)
    agg = {}
    for stamp in stamps:
        for row in _rows(stamp, ctx.log):
            if len(row) != 61 or row[C["root"]] not in roots:
                continue
            if cfg.get("root_events_only", True) and row[C["is_root"]] != "1":
                continue
            if row[C["geo_type"]] not in geo_types or not row[C["lat"]] or not row[C["lon"]]:
                continue
            code = row[C["code"]][:3]
            if code not in CAMEO:
                code = row[C["root"]] + "0"
                if code not in CAMEO:
                    continue
            category, base_sev, label = CAMEO[code]
            try:
                event_day = datetime.strptime(row[C["sqldate"]], "%Y%m%d").replace(tzinfo=timezone.utc)
                added = datetime.strptime(row[C["added"]], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                lat, lon = float(row[C["lat"]]), float(row[C["lon"]])
                articles = int(row[C["articles"]] or 0)
            except ValueError:
                continue
            if added - event_day > max_age:
                continue  # fait ancien évoqué dans l'actualité
            place = row[C["feature"]] or f"{round(lat, 2)},{round(lon, 2)}"
            key = f"{place}-{code}-{row[C['sqldate']]}"
            a = agg.setdefault(key, {"row": row, "code": code, "root": row[C["root"]], "category": category,
                                     "sev": base_sev, "label": label, "articles": 0, "urls": [],
                                     "domains": set(), "actor_cc": set(), "actor_names": set(),
                                     "added": added, "first": added, "lat": lat, "lon": lon})
            a["articles"] += articles
            a["added"] = max(a["added"], added)
            a["first"] = min(a["first"], added)
            for col in ("actor1_cc", "actor2_cc"):
                if row[C[col]]:
                    a["actor_cc"].add(row[C[col]])
            for col in ("actor1", "actor2"):
                if row[C[col]]:
                    a["actor_names"].add(row[C[col]].upper())
            url = row[C["url"]]
            if url:
                a["domains"].add(_domain(url))
                if url not in a["urls"] and len(a["urls"]) < 5:
                    a["urls"].append(url)

    out, dropped = [], {"seuil": 0, "lieu": 0}
    for key, a in agg.items():
        row = a["row"]
        country = ctx.countries.locate(a["lat"], a["lon"])
        item = ctx.countries.get(country) if country else None
        violent = a["root"] in ("18", "19", "20")
        # 1. Effet « dateline » : article écrit depuis une capitale sur un conflit étranger
        city = row[C["geo_name"]].split(",")[0].strip().upper()
        if violent and (city in a["actor_names"] or
                        (item and a["actor_cc"] and item["iso3"] not in a["actor_cc"])):
            dropped["lieu"] += 1
            continue
        # 2. Seuils selon le contexte du pays
        context = "tense" if country and _max_advisory(ctx, country) >= 3 else "calm"
        min_art, min_dom = thresholds[context].get(a["root"], [3, 2])
        if a["articles"] < min_art or len(a["domains"]) < min_dom:
            dropped["seuil"] += 1
            continue
        category, label, base = a["category"], a["label"], a["sev"]
        if context == "calm" and a["root"] in ("19", "20"):
            # Hors zone de conflit, un « usage de la force militaire » est presque toujours
            # une fusillade, une opération de police ou un attentat : on le requalifie.
            category, label, base = "attack", "Armed violence", min(base, 3)
        sev = base + (1 if a["articles"] >= cfg.get("escalate_articles", 20) and len(a["domains"]) >= 3 else 0)
        if len(a["domains"]) >= 3 and a["articles"] >= 10:
            confidence = "high"
        elif len(a["domains"]) >= 2:
            confidence = "medium"
        else:
            confidence = "low"
        place = row[C["geo_name"]]
        actors = " / ".join(x.title() for x in (row[C["actor1"]], row[C["actor2"]]) if x)
        summary = (f"Auto-detected from news coverage ({a['articles']} article(s), "
                   f"{len(a['domains'])} outlet(s)).")
        if actors:
            summary += f" Actors: {actors}."
        ev = make_event(
            id=f"gdelt-{key}", source="GDELT", category=category, severity=sev,
            title=f"{label} – {place}", summary=summary, date=to_iso(min(a["added"], ctx.now)),
            start=to_iso(min(a["first"], ctx.now)), lat=a["lat"], lon=a["lon"], url=a["urls"][0] if a["urls"] else BASE,
            place=place, precision=PRECISION.get(row[C["geo_type"]], "region"),
            country=country, confidence=confidence, tags=["auto-detected", "unverified"],
        )
        ev["sources"] = [{"name": "Press (via GDELT)", "url": u} for u in a["urls"]]
        out.append(ev)
    ctx.log(f"  GDELT : {len(out)} retenus, {dropped['seuil']} sous les seuils, "
            f"{dropped['lieu']} lieux douteux écartés")
    if stamps:
        ctx.state["gdelt_last"] = stamps[-1].isoformat()
    return out
