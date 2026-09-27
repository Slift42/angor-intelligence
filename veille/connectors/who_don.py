"""OMS – Disease Outbreak News. Bulletins officiels d'épidémies. https://www.who.int
Les bulletins ne sont pas géolocalisés : on place l'événement au centre du pays cité dans le titre."""
from datetime import timedelta

from .. import http
from ..model import make_event, parse_iso, to_iso

KIND = "events"
URL = "https://www.who.int/api/news/diseaseoutbreaknews"
ITEM_URL = "https://www.who.int/emergencies/disease-outbreak-news/item/"
HIGH = ("ebola", "marburg", "plague", "nipah", "mers", "h5n1", "avian influenza", "lassa",
        "crimean-congo", "smallpox", "mpox clade i", "cholera", "yellow fever")


def fetch(cfg, ctx):
    params = {"sf_culture": "en", "$orderby": "PublicationDateAndTime desc", "$top": cfg.get("limit", 40)}
    data = http.get_json(cfg.get("url", URL), params=params)
    items = data.get("value", data if isinstance(data, list) else [])
    max_age = timedelta(days=cfg.get("max_age_days", 60))
    out = []
    for it in items:
        title = (it.get("OverrideTitle") or it.get("Title") or "").strip()
        date = parse_iso(it.get("PublicationDateAndTime") or it.get("PublicationDate"))
        if not title or not date or ctx.now - date > max_age:
            continue
        country_name = title.split(" - ")[-1] if " - " in title else ""
        item = ctx.countries.by_country_name(country_name) if country_name else None
        if not item:
            ctx.log(f"  OMS : pays non reconnu dans « {title} » (ignoré)")
            continue
        lat, lon = item["label"][1], item["label"][0]
        severity = 3 if any(w in title.lower() for w in HIGH) else 2
        slug = it.get("UrlName") or it.get("DonId") or ""
        out.append(make_event(
            id=f"who-{it.get('DonId') or it.get('Id')}", source="WHO", category="health",
            severity=severity, title=title, summary="WHO Disease Outbreak News bulletin.",
            date=to_iso(date), lat=lat, lon=lon, url=ITEM_URL + slug, place=item["name_en"],
            precision="country", country=item["iso2"],
        ))
    return out
