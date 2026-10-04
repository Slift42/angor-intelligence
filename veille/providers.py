"""Annuaire des prestataires de services aux voyageurs → docs/data/providers.js (window.VS_PROVIDERS).

Deux origines :
- prestataires inscrits sur la plateforme (Supabase, table providers) : lus avec la clé publique, qui ne donne accès
  qu'au nom, aux catégories, aux pays couverts, au site web et au niveau de fiabilité (A à D) calculé par la base ;
  contacts, tarifs, garanties et avis restent réservés aux comptes validés (page prestataire.html) ;
- prestataires trouvés par Angor dans des sources publiques (config/providers_directory.json) : niveau E,
  « Non vérifié – à contacter séparément ». Une ligne disparaît dès que le même prestataire (même site web) s'inscrit.
Catégories, groupes et niveaux : config/providers.json. Lu par la carte (fiche pays), le rapport pays, le Travel buddy
et l'espace prestataire. Ne fait jamais échouer la collecte.
"""
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

from . import accounts, http, publish
from .config import ROOT

CONFIG = ROOT / "config" / "providers.json"
DIRECTORY = ROOT / "config" / "providers_directory.json"
FIELDS = "id,name,categories,countries,hq_country,website,tier,score"


def _clean(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


def domain(url):
    """example.com pour https://www.example.com/fr : sert à reconnaître un même prestataire dans les deux listes."""
    host = urlparse(url if "://" in (url or "") else "https://" + (url or "")).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def fetch_registered(settings, log=print):
    """Fiches soumises ou vérifiées, publiées dans l'annuaire (clé publique). [] si les comptes ne sont pas configurés."""
    acc = settings.get("accounts") or {}
    url = (acc.get("supabase_url") or "").rstrip("/")
    headers = accounts.headers(acc.get("supabase_anon_key") or "")
    if not (url and headers):
        return []
    try:
        rows = http.get_json(f"{url}/rest/v1/providers", headers=headers, timeout=20, retries=1,
                             params={"select": FIELDS, "status": "in.(submitted,verified)", "public_listing": "is.true",
                                     "order": "score.desc"})
    except Exception as exc:  # table absente (schéma pas à jour), projet en pause…
        log(f"  – Prestataires inscrits non lus ({type(exc).__name__}) : supabase/schema.sql à relancer ?")
        return []
    return [{"id": r["id"], "name": r["name"], "web": r.get("website") or "", "hq": r.get("hq_country") or "",
             "countries": r.get("countries") or [], "categories": r.get("categories") or [],
             "tier": r.get("tier") or "D", "score": r.get("score") or 0, "source": "self"} for r in rows or []]


def build(registered, cfg=None, directory=None):
    cfg = _clean(cfg if cfg is not None else json.loads(CONFIG.read_text(encoding="utf-8")))
    directory = directory if directory is not None else json.loads(DIRECTORY.read_text(encoding="utf-8"))
    known = {domain(r["web"]) for r in registered if r.get("web")}
    cats = cfg["categories"]

    def angor(p):
        e = {k: v for k, v in p.items() if not k.startswith("_")}
        e["categories"] = [c for c in e.get("categories", []) if c in cats]
        e["services"] = e["categories"]                      # ancien nom du champ (rapport pays, Travel buddy)
        e["tier"], e["source"] = "E", "angor"
        e.setdefault("linkedin", "https://www.linkedin.com/search/results/companies/?keywords="
                     + e["name"].split(" /")[0].replace(" ", "%20"))
        return e

    providers = [angor(p) for p in directory.get("providers", []) if domain(p.get("web")) not in known]
    local = {iso: [angor(p) for p in lst if domain(p.get("web")) not in known]
             for iso, lst in (directory.get("local") or {}).items()}
    for r in registered:
        r["categories"] = [c for c in r["categories"] if c in cats]
        r["services"] = r["categories"]
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": ("Prestataires inscrits sur Angor (niveaux A à D, selon la vérification et la qualité de leur fiche) et "
                 "prestataires repérés par Angor dans des sources publiques (niveau E, non vérifiés, à contacter séparément). "
                 "Aucun classement payant."),
        "groups": cfg["groups"], "categories": cats, "tiers": cfg["tiers"],
        "services": {k: {"fr": v["fr"], "en": v["en"]} for k, v in cats.items()},
        "registered": registered, "providers": providers, "local": local,
    }


def update(settings, log=print):
    try:
        reg = fetch_registered(settings, log)
        data = build(reg)
        publish.write_js("providers.js", "VS_PROVIDERS", data)
        log(f"  ✔ Annuaire des prestataires : {len(reg)} inscrit(s), {len(data['providers'])} repéré(s) par Angor")
    except Exception as exc:
        log(f"  ✘ Annuaire des prestataires non publié ({type(exc).__name__} : {exc})")
