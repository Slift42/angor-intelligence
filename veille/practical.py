"""Informations pratiques par pays (Wikidata, CC0) pour les rapports pays :
indicatif téléphonique, numéros d'urgence, prises et tension électriques, opérateurs mobiles et
principaux établissements hospitaliers (classés par nombre de lits puis par notoriété).

Lecture progressive (quelques dizaines de pays par collecte, chaque pays relu tous les 30 jours)
pour ménager le service public de Wikidata. Résultat : docs/data/practical.js
⚠ Les hôpitaux listés sont les plus grands ou les plus connus, pas une liste « agréée » :
la référence reste l'assisteur, l'assureur et le consulat.
"""
import time
from datetime import datetime, timedelta

from . import http
from .publish import write_js

SPARQL = "https://query.wikidata.org/sparql"
HEADERS = {"Accept": "application/sparql-results+json",
           "User-Agent": "AngorIntelligence/1.0 (veille surete, sources ouvertes; contact via GitHub Slift42)"}

Q_BASICS = """SELECT ?code ?emergLabel ?plugLabel ?volt WHERE {{
  ?country wdt:P297 "{iso}" .
  OPTIONAL {{ ?country wdt:P474 ?code }}
  OPTIONAL {{ ?country wdt:P2852 ?emerg }}
  OPTIONAL {{ ?country wdt:P2853 ?plug }}
  OPTIONAL {{ ?country wdt:P2884 ?volt }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
}} LIMIT 60"""

Q_HOSPITALS = """SELECT ?h ?hLabel ?cityLabel ?beds ?web ?links WHERE {{
  ?country wdt:P297 "{iso}" .
  ?h wdt:P31/wdt:P279? wd:Q16917 ; wdt:P17 ?country ; wikibase:sitelinks ?links .
  FILTER NOT EXISTS {{ ?h wdt:P576 [] }}
  OPTIONAL {{ ?h wdt:P6801 ?beds }}
  OPTIONAL {{ ?h wdt:P856 ?web }}
  OPTIONAL {{ ?h wdt:P131 ?city }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
}} ORDER BY DESC(?beds) DESC(?links) LIMIT 40"""

Q_OPERATORS = """SELECT DISTINCT ?op ?opLabel ?links WHERE {{
  ?country wdt:P297 "{iso}" .
  ?op wdt:P31 ?cls ; wdt:P17 ?country ; wikibase:sitelinks ?links .
  ?cls rdfs:label "mobile network operator"@en .
  FILTER NOT EXISTS {{ ?op wdt:P576 [] }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
}} ORDER BY DESC(?links) LIMIT 8"""


def _query(q):
    r = http.get(SPARQL, params={"query": q, "format": "json"}, headers=HEADERS, retries=1, timeout=45)
    return r.json().get("results", {}).get("bindings", [])


def _v(row, k):
    return (row.get(k) or {}).get("value")


def country(iso):
    info = {"fetched": datetime.utcnow().isoformat()}
    rows = _query(Q_BASICS.format(iso=iso))
    info["calling_code"] = sorted({_v(r, "code") for r in rows if _v(r, "code")})
    info["emergency"] = sorted({_v(r, "emergLabel") for r in rows if _v(r, "emergLabel")})[:6]
    info["plugs"] = sorted({_v(r, "plugLabel") for r in rows if _v(r, "plugLabel")})
    volts = sorted({round(float(_v(r, "volt"))) for r in rows if _v(r, "volt")})
    info["voltage"] = volts
    time.sleep(1)
    seen, hospitals = set(), []
    for r in _query(Q_HOSPITALS.format(iso=iso)):
        name = _v(r, "hLabel")
        if not name or name in seen or name.startswith("Q") and name[1:].isdigit():
            continue
        seen.add(name)
        beds = _v(r, "beds")
        hospitals.append({"name": name, "city": _v(r, "cityLabel") or "", "beds": int(float(beds)) if beds else None,
                          "web": _v(r, "web") or "", "wikidata": _v(r, "h")})
        if len(hospitals) >= 12:
            break
    info["hospitals"] = hospitals
    time.sleep(1)
    info["operators"] = [_v(r, "opLabel") for r in _query(Q_OPERATORS.format(iso=iso))
                         if _v(r, "opLabel") and not _v(r, "opLabel").startswith("Q")][:8]
    return info


def update(countries, store, log, per_run=25, refresh_days=30, budget_s=90):
    cache = store.setdefault("practical", {})
    now = datetime.utcnow()
    todo = [c["iso2"] for c in countries.items if len(c["iso2"]) == 2 and c.get("name_fr")]
    todo.sort(key=lambda iso: cache.get(iso, {}).get("fetched", ""))
    stop, done, fails = time.time() + budget_s, 0, 0
    for iso in todo[:per_run]:
        old = cache.get(iso)
        if old and now - datetime.fromisoformat(old["fetched"]) < timedelta(days=refresh_days):
            break  # liste triée : les suivants sont encore plus récents
        if time.time() > stop or fails >= 3:
            break
        try:
            cache[iso] = country(iso)
            done += 1
            fails = 0
        except Exception as exc:
            fails += 1
            log(f"  Wikidata {iso} : {type(exc).__name__}")
        time.sleep(1)
    write_js("practical.js", "VS_PRACTICAL", {"generated": now.isoformat(), "countries": cache,
                                             "source": "Wikidata (CC0)"})
    if done:
        log(f"  Infos pratiques (Wikidata) : {done} pays mis à jour, {len(cache)} connus")
