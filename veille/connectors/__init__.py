"""Registre des connecteurs.

Chaque connecteur est un module qui expose :
    KIND  = "events"      → fetch() renvoie une liste d'événements au format standard
          | "advisories"  → fetch() renvoie {iso2: {"level": 1..4, "label": ..., "url": ...}}
    fetch(cfg, ctx)       → cfg = bloc de la source dans config/sources.json
                            ctx = Context (pays, état persistant, journal)

Pour ajouter une source : créer un module ici, l'ajouter à REGISTRY,
puis déclarer la source dans config/sources.json (avec "enabled": true).
"""
from . import (acled, ca_advisories, cisa_kev, de_advisories, emsc, eonet, fr_advisories, gdacs, gdelt_events, gnews, jsonapi,
               meteoalarm, nws, official_rss, outlets, reliefweb, rss, telegram, uk_advisories, us_advisories, usgs,
               who_don)

REGISTRY = {
    "usgs": usgs,
    "emsc": emsc,      # 2e réseau sismologique mondial (recoupement USGS, v0.25)
    "gdacs": gdacs,
    "eonet": eonet,
    "gdelt_events": gdelt_events,
    "who_don": who_don,
    "nws": nws,                # alertes météo officielles États-Unis (Severe/Extreme)
    "meteoalarm": meteoalarm,  # vigilances orange/rouge des services météo européens
    "cisa_kev": cisa_kev,      # vulnérabilités activement exploitées (CISA) → fil cyber
    "us_advisories": us_advisories,
    "ca_advisories": ca_advisories,
    "fr_advisories": fr_advisories,  # MEAE – Conseils aux voyageurs (France)
    "uk_advisories": uk_advisories,  # FCDO – Foreign travel advice (Royaume-Uni)
    "de_advisories": de_advisories,  # Auswärtiges Amt – Reise- und Sicherheitshinweise (Allemagne)
    "official_rss": official_rss,    # bulletins officiels RSS/Atom (NOAA NHC, GVP, Copernicus EMS, tsunamis…)
    "gnews": gnews,      # presse locale de ~110 pays via Google News (rotation)
    "outlets": outlets,  # médias de référence par pays (≈ 200 pays), via Google News
    "rss": rss,          # générique : flux RSS/Atom gratuits ou sous abonnement
    "telegram": telegram,  # canaux Telegram publics (aperçu t.me/s/…)
    "reliefweb": reliefweb,  # ONU OCHA – rapports humanitaires par pays (nom d'application requis)
    "jsonapi": jsonapi,  # générique : API JSON authentifiée (sources payantes)
    "acled": acled,      # exemple de source sous licence (désactivée par défaut)
}


class Context:
    def __init__(self, countries, state, log, now):
        self.countries = countries
        self.state = state      # dictionnaire persistant entre deux exécutions
        self.log = log
        self.now = now          # datetime UTC de l'exécution
        self.news = []          # articles sans coordonnées → « Fil d'actualité »
        self.advisories = {}    # avis aux voyageurs connus {source: {iso2: {...}}}
        self.purge = []         # préfixes d'identifiants à effacer de l'historique
        self.press = []         # titres de presse à analyser (sûreté)
        self.econ = []          # titres de presse économique
        self.prefetch = {}      # flux RSS déjà téléchargés (en parallèle) : url → réponse ou exception
