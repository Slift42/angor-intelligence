"""ReliefWeb (ONU – OCHA) : rapports de situation, alertes et analyses humanitaires, par pays.

Excellente couverture des zones de crise mal couvertes par la presse (Soudan, RDC, Sahel, Somalie,
Yémen, Haïti…). API gratuite, mais depuis 2025 elle demande un « nom d'application » approuvé :
  1. demander un appname sur https://apidoc.reliefweb.int (formulaire, gratuit) ;
  2. le mettre dans .env et dans les Secrets GitHub : RELIEFWEB_APPNAME=...
  3. passer la source "reliefweb" à "enabled": true dans config/sources.json.
Titres, source et lien uniquement ; les titres passent par le même tri que la presse.
"""
from datetime import timedelta

from .. import http
from ..config import secret
from ..http import AuthMissing
from ..model import parse_iso

KIND = "events"
URL = "https://api.reliefweb.int/v2/reports"


def fetch(cfg, ctx):
    app = secret(cfg.get("appname_env", "RELIEFWEB_APPNAME"))
    if not app:
        raise AuthMissing("RELIEFWEB_APPNAME")
    since = (ctx.now - timedelta(hours=int(cfg.get("max_age_hours", 48)))).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    body = {"limit": int(cfg.get("limit", 300)), "sort": ["date.created:desc"],
            "fields": {"include": ["title", "url_alias", "url", "date.created", "primary_country.iso3", "source.shortname"]},
            "filter": {"conditions": [{"field": "date.created", "value": {"from": since}}]}}
    data = http.post_json(f"{URL}?appname={app}", body)
    n = 0
    for it in data.get("data", []):
        f = it.get("fields", {})
        iso3 = ((f.get("primary_country") or {}).get("iso3") or "").upper()
        item = ctx.countries.by_iso3.get(iso3)
        date = parse_iso((f.get("date") or {}).get("created"))
        if not item or not date or not f.get("title"):
            continue
        src = ", ".join(s.get("shortname", "") for s in (f.get("source") or [])[:2]) or "ReliefWeb"
        ctx.press.append({"title": f["title"], "url": f.get("url_alias") or f.get("url") or "https://reliefweb.int",
                          "outlet": f"ReliefWeb · {src}", "date": date, "country_hint": item["iso2"], "lang": "en",
                          "feed": "ReliefWeb"})
        n += 1
    ctx.log(f"  ReliefWeb : {n} rapports")
    return []
