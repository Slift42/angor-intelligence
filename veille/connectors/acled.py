"""ACLED – exemple de connecteur pour une source sous licence (DÉSACTIVÉ par défaut).

Depuis 2025, l'accès gratuit d'ACLED n'inclut plus d'API ; l'API demande un compte « Research »
ou supérieur, et la revente de produits dérivés exige une licence commerciale.
Ce module montre comment une source payante se branche : authentification OAuth
(identifiants dans .env ou dans les Secrets GitHub), puis traduction vers le format standard.

⚠ Adresses et noms de champs à vérifier dans la documentation ACLED au moment de l'abonnement :
   https://acleddata.com/api-documentation/getting-started
"""
from datetime import timedelta

from .. import http
from ..model import make_event, parse_iso, to_iso

KIND = "events"
API = "https://acleddata.com/api/acled/read"
AUTH = {"type": "oauth2_password", "token_url": "https://acleddata.com/oauth/token",
        "user_env": "ACLED_EMAIL", "password_env": "ACLED_PASSWORD", "client_id": "acled"}

TYPES = {"Battles": ("armed_conflict", 3), "Explosions/Remote violence": ("attack", 3),
         "Violence against civilians": ("attack", 3), "Riots": ("unrest", 2),
         "Protests": ("unrest", 1), "Strategic developments": ("political", 1)}


def fetch(cfg, ctx):
    since = (ctx.now - timedelta(days=cfg.get("days", 7))).strftime("%Y-%m-%d")
    params = {"event_date": since, "event_date_where": ">=", "limit": cfg.get("limit", 2000),
              "_format": "json"}
    data = http.get_json(cfg.get("url", API), params=params, auth=cfg.get("auth", AUTH))
    out = []
    for it in data.get("data", []):
        category, sev = TYPES.get(it.get("event_type"), ("other", 1))
        fatalities = int(it.get("fatalities") or 0)
        if fatalities >= 10:
            sev = 4
        lat, lon = float(it["latitude"]), float(it["longitude"])
        date = parse_iso(it["event_date"])
        out.append(make_event(
            id=f"acled-{it.get('event_id_cnty')}", source="ACLED", category=category, severity=sev,
            title=f"{it.get('sub_event_type')} – {it.get('location')}, {it.get('country')}",
            summary=f"Fatalities: {fatalities}. Source: {it.get('source', '')}",
            date=to_iso(date), lat=lat, lon=lon, url="https://acleddata.com",
            place=it.get("location", ""), precision="city",
            country=ctx.countries.locate(lat, lon), confidence="high"))
    return out
