"""Registre des connecteurs.

Chaque connecteur est un module qui expose :
    KIND  = "events"      → fetch() renvoie une liste d'événements au format standard
          | "advisories"  → fetch() renvoie {iso2: {"level": 1..4, "label": ..., "url": ...}}
    fetch(cfg, ctx)       → cfg = bloc de la source dans config/sources.json
                            ctx = Context (pays, état persistant, journal)

Pour ajouter une source : créer un module ici, l'ajouter à REGISTRY,
puis déclarer la source dans config/sources.json (avec "enabled": true).
"""
from . import (acled, ca_advisories, eonet, fr_advisories, gdacs, gdelt_events, gnews, jsonapi, outlets, rss,
               uk_advisories, us_advisories, usgs, who_don)

REGISTRY = {
    "usgs": usgs,
    "gdacs": gdacs,
    "eonet": eonet,
    "gdelt_events": gdelt_events,
    "who_don": who_don,
    "us_advisories": us_advisories,
    "ca_advisories": ca_advisories,
    "fr_advisories": fr_advisories,  # MEAE – Conseils aux voyageurs (France)
    "uk_advisories": uk_advisories,  # FCDO – Foreign travel advice (Royaume-Uni)
    "gnews": gnews,      # presse locale de ~110 pays via Google News (rotation)
    "outlets": outlets,  # médias de référence par pays (≈ 200 pays), via Google News
    "rss": rss,          # générique : flux RSS/Atom gratuits ou sous abonnement
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
