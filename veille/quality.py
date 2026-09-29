"""Qualité de l'information : validation par l'analyste (« Vérifié Angor ») et cotation de l'Amirauté.

1. Validation par l'analyste – config/verified.json (exporté depuis la carte en mode analyste : angor.fr/?analyste=1)
   {"events": {"<id de l'incident>": {"status": "verified" | "false" | "corrected",
                                      "severity": 3, "category": "unrest", "title": "…", "place": "…",
                                      "note": "commentaire libre", "date": "2026-09-30"}}}
   - verified  : badge « Vérifié Angor », confiance haute, poids plein dans la note pays ;
   - corrected : mêmes effets, avec les champs corrigés (gravité, catégorie, titre, lieu) ;
   - false     : l'incident est retiré de la carte, des alertes et des calculs.

2. Cotation de l'Amirauté (grille OTAN, de A1 à F6) sur chaque incident :
   fiabilité de la source (lettre) × crédibilité de l'information (chiffre).
   A  totalement fiable     : capteurs et organismes officiels (USGS, GDACS, NASA, OMS, UCDP, services météo, CISA)
   B  habituellement fiable : médias de référence (catalogue config/press_outlets.json, grands flux RSS)
   C  assez fiable          : autre presse
   D  pas toujours fiable   : détection automatique GDELT (codage machine de la presse mondiale)
   E  peu fiable            : réseaux sociaux, canaux Telegram
   F  fiabilité inconnue
   1  confirmée (validée par l'analyste, ou mesure officielle)   2  probablement vraie (≥ 3 sources indépendantes)
   3  possiblement vraie (2 sources, ou 1 source bien classée)    4  douteuse (source unique, classement incertain)
   5  improbable (infirmée par l'analyste)                        6  invérifiable
Cotation automatique, indicative : l'analyste la corrige via verified.json (champ "admiralty").
"""
import re

from . import config

OFFICIAL = {"USGS", "GDACS", "NASA EONET", "WHO", "UCDP", "NWS", "Meteoalarm", "CISA", "MEAE", "FCDO"}
SENSORS = {"USGS", "GDACS", "NASA EONET", "NWS", "Meteoalarm", "CISA"}  # mesure ou bulletin officiel direct
REFERENCE_EXTRA = {
    "Reuters", "AFP", "Associated Press", "AP", "BBC", "BBC World", "The Guardian", "New York Times", "Le Monde",
    "Deutsche Welle", "DW", "France 24", "RFI", "Al Jazeera", "Euronews", "Franceinfo", "Le Figaro", "Financial Times",
    "The Economist", "Les Echos", "Ouest-France", "Le Parisien", "20 Minutes", "Jeune Afrique", "El País",
    "UN News", "International Crisis Group", "Radio Okapi", "Kyiv Independent", "The Hindu", "Dawn", "Japan Times",
}
_REF = None
_LETTER = None  # domaine ou nom du média → lettre de fiabilité (catalogue : 5e champ, sinon « B »)


def _dom(u):
    return re.sub(r"^(www|m|feeds)\.", "", re.sub(r"^https?://", "", u or "").split("/")[0].lower())


def _reference():
    """Noms des médias de référence : catalogue par pays + flux RSS configurés + grandes agences."""
    global _REF, _LETTER
    if _REF is None:
        names = set(REFERENCE_EXTRA)
        _LETTER = {}
        cat = config.load_json("press_outlets.json", {}) or {}
        for rows in (cat.get("countries") or {}).values():
            for row in rows:
                if row:
                    names.add(str(row[0]))
                    letter = row[4] if len(row) > 4 and row[4] in "ABCDEF" else "B"
                    _LETTER[str(row[0]).lower()] = _LETTER[_dom(row[1])] = letter
        for s in (config.load_json("sources.json", {}) or {}).get("sources", []):
            if s.get("type") == "telegram":
                for ch in s.get("channels") or []:
                    if ch.get("reliability") and ch.get("name"):
                        _LETTER["t.me/" + ch["name"].lstrip("@").lower()] = ch["reliability"].upper()
            if s.get("type") == "rss" and s.get("name"):
                names.add(s["name"].split(" – ")[0].split(" (")[0])
                if s.get("reliability"):
                    _LETTER[s["name"].lower()] = _LETTER[_dom(s.get("url"))] = s["reliability"]
        _REF = {n.lower() for n in names if n}
    return _REF


def _letter(src):
    """Lettre de fiabilité d'une source d'incident (domaine d'abord, puis nom), ou None si inconnue."""
    _reference()
    for k in (src.get("site"), _dom(src.get("url")), (src.get("name") or "").lower()):
        if k and k in _LETTER:
            return _LETTER[k]
    return None


def _is_reference(name):
    n = (name or "").lower()
    if not n:
        return False
    ref = _reference()
    return n in ref or n.split(" – ")[0].split(" (")[0] in ref or any(n.startswith(r + " ") for r in ref if len(r) > 3)


def reliability(ev):
    src = ev.get("source") or ""
    if src in OFFICIAL or src.startswith("UCDP"):
        return "A"
    tags = ev.get("tags") or []
    if src == "GDELT" or "gdelt" in ev.get("id", "")[:6]:
        return "D"
    names = [s.get("name", "") for s in ev.get("sources") or []]
    letters = [x for x in (_letter(s) for s in ev.get("sources") or []) if x]
    if letters:  # fiabilité notée dans le catalogue (ex. médias d'État « D ») : la meilleure source l'emporte
        return min(letters)
    if "social" in tags and not any(_is_reference(n) for n in names):
        return "E"
    if any(_is_reference(n) for n in names) or _is_reference(src):
        return "B"
    if names or src:
        return "C"
    return "F"


def credibility(ev, rel):
    v = ev.get("verified") or {}
    if v.get("status") == "false":
        return 5
    if v.get("status") in ("verified", "corrected"):
        return 1
    if rel == "A" and (ev.get("source") in SENSORS or "auto-detected" not in (ev.get("tags") or [])):
        return 1
    outlets = {(s.get("name") if s.get("name") != "Press (via GDELT)" else s.get("url", "")[:40])
               for s in ev.get("sources") or []}
    n = len(outlets)
    conf = ev.get("confidence", "medium")
    if n >= 3 and conf != "low":
        return 2
    if n >= 2 or conf == "high":
        return 3
    if conf == "low":
        return 4
    return 3 if rel in "AB" else 4


def rate(ev):
    rel = reliability(ev)
    return f"{rel}{credibility(ev, rel)}"


def load_verified():
    data = config.load_json("verified.json", {}) or {}
    return {k: v for k, v in (data.get("events") or {}).items() if isinstance(v, dict) and v.get("status")}


def filter_and_rate(events, verified=None):
    """Applique les décisions de l'analyste et la cotation ; renvoie la liste sans les incidents infirmés."""
    verified = load_verified() if verified is None else verified
    kept = []
    for ev in events:
        ev = dict(ev)  # copie : la mémoire du robot garde la version d'origine
        v = verified.get(ev["id"])
        if v and v["status"] == "false":
            continue
        if v:
            for k in ("severity", "category", "title", "place"):
                if v.get(k) not in (None, ""):
                    ev[k] = int(v[k]) if k == "severity" else v[k]
            ev["verified"] = {"status": v["status"], "note": v.get("note", ""), "date": v.get("date", "")}
            ev["confidence"] = "high"
            ev["tags"] = [t for t in ev.get("tags") or [] if t not in ("unverified", "auto-detected")] + ["verified"]
        ev["admiralty"] = (v or {}).get("admiralty") or rate(ev)
        kept.append(ev)
    return kept
