"""FCDO (Royaume-Uni) – Foreign travel advice, via l'API de contenu GOV.UK (Open Government Licence v3.0).

Pour chaque pays : statut d'alerte (« against all travel », « against all but essential travel »,
au pays entier ou à certaines zones) et carte officielle des zones. Seuls les avis modifiés depuis
la dernière lecture sont relus (champ public_updated_at de l'index).

Niveaux (échelle 1-4, alignée sur les autres gouvernements) :
  4 = déconseillé formellement (tout le pays)      max 4
  3 = déconseillé sauf essentiel (tout le pays), ou formellement déconseillé dans certaines zones
  2 = déconseillé sauf essentiel dans certaines zones
  1 = pas de restriction particulière
« max » = niveau de la zone la plus sensible (utilisé pour colorer la carte).
"""
import re
import time

from .. import http

KIND = "advisories"
INDEX = "https://www.gov.uk/api/content/foreign-travel-advice"
WEB = "https://www.gov.uk"
ALIASES = {"the occupied palestinian territories": "PS", "occupied palestinian territories": "PS",
           "myanmar (burma)": "MM", "burma": "MM", "macao": "MO", "vatican city": "VA", "the gambia": "GM",
           "st lucia": "LC", "st kitts and nevis": "KN", "st vincent and the grenadines": "VC",
           "st maarten": "SX", "st martin": "MF", "st barthélemy": "BL", "st helena, ascension and tristan da cunha": "SH",
           "democratic republic of the congo": "CD", "congo": "CG", "czechia": "CZ", "czech republic": "CZ",
           "north korea": "KP", "south korea": "KR", "usa": "US", "timor-leste": "TL", "cape verde": "CV",
           "ivory coast": "CI", "côte d'ivoire": "CI", "micronesia": "FM", "british virgin islands": "VG",
           "turks and caicos islands": "TC", "cayman islands": "KY", "falkland islands": "FK"}
LABELS = {
    (4, False): "Against all travel (whole country)",
    (3, False): "Against all but essential travel (whole country)",
    (3, True): "Against all travel to parts of the country",
    (2, True): "Against all but essential travel to parts of the country",
    (1, False): "No FCDO travel warning (see advice)",
}


def levels(status):
    s = set(status or [])
    whole_red = "avoid_all_travel_to_whole_country" in s
    whole_orange = "avoid_all_but_essential_travel_to_whole_country" in s
    parts_red = "avoid_all_travel_to_parts" in s
    parts_orange = "avoid_all_but_essential_travel_to_parts" in s
    mx = 4 if (whole_red or parts_red) else 3 if (whole_orange or parts_orange) else 1
    if whole_red:
        return 4, False, mx
    if whole_orange:
        return 3, False, mx
    if parts_red:
        return 3, True, mx
    if parts_orange:
        return 2, True, mx
    return 1, False, mx


def _iso(ctx, name):
    key = name.strip().lower()
    if key in ALIASES:
        return ALIASES[key]
    for cand in (name, re.sub(r"\s*\(.*?\)", "", name), re.sub(r"^the\s+", "", name, flags=re.I)):
        item = ctx.countries.by_country_name(cand)
        if item:
            return item["iso2"]
    return None


def fetch(cfg, ctx):
    cache = ctx.state.setdefault("uk_adv", {})
    index = http.get_json(cfg.get("url", INDEX))
    children = (index.get("links") or {}).get("children") or []
    todo, unmatched = [], []
    for ch in children:
        name = ((ch.get("details") or {}).get("country") or {}).get("name") or ch.get("title", "").replace(" travel advice", "")
        iso = _iso(ctx, name)
        if not iso:
            unmatched.append(name)
            continue
        old = cache.get(iso)
        if not old or old.get("updated") != ch.get("public_updated_at"):
            todo.append((iso, ch))
    budget = time.time() + float(cfg.get("time_budget_s", 60))
    done = 0
    for iso, ch in todo[: int(cfg.get("pages_per_run", 60))]:
        if time.time() > budget:
            break
        try:
            page = http.get_json(ch.get("api_url") or (WEB + "/api/content" + ch["base_path"]), retries=1, timeout=20)
        except Exception:
            continue
        d = page.get("details") or {}
        lvl, parts, mx = levels(d.get("alert_status"))
        cache[iso] = {"level": lvl, "scale": 4, "max": mx, "parts": parts, "label": LABELS.get((lvl, parts), ""),
                      "url": ch.get("web_url") or WEB + ch["base_path"], "updated": ch.get("public_updated_at"),
                      "map": (d.get("image") or {}).get("url"), "status": d.get("alert_status") or []}
        done += 1
    if unmatched:
        ctx.log(f"  FCDO : {len(unmatched)} pays non rapprochés : {', '.join(unmatched[:8])}")
    if todo:
        ctx.log(f"  FCDO : {done} avis relus ({len(todo) - done} restant(s)), {len(cache)} pays connus")
    return dict(cache)
