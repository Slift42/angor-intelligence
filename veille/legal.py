"""Informations légales : config/legal.json → docs/data/legal.js (window.VS_LEGAL).

Une seule source pour les pages légales du site (mentions légales, CGU, CGV, confidentialité, accord de
sous-traitance, licences) et pour le contrôle des versions acceptées par les utilisateurs (docs/account.js).
Ajoute la liste des sources de données et de leurs licences (config/sources.json) et la liste des champs encore
vides, que les pages affichent « [à compléter : …] ».
Aucune donnée personnelle ni aucun secret : ce fichier est public.

Usage autonome (après avoir modifié config/legal.json, pour voir le résultat sans lancer de collecte) :
    python -m veille.legal
"""
import json

from .config import ROOT
from . import publish

LEGAL_FILE = ROOT / "config" / "legal.json"
SOURCES_FILE = ROOT / "config" / "sources.json"
# Champs obligatoires pour passer en « en vigueur » (chemin dans legal.json → libellé affiché)
REQUIRED = {
    "editeur.nom": "nom de l'éditeur", "editeur.adresse": "adresse", "editeur.siren": "SIREN",
    "editeur.immatriculation": "immatriculation", "editeur.email": "e-mail de contact",
    "editeur.telephone": "téléphone", "editeur.directeur_publication": "directeur de la publication",
    "editeur.contact_donnees": "contact données personnelles", "mediateur.nom": "médiateur de la consommation",
    "mediateur.site": "site du médiateur", "tribunal": "tribunal compétent",
}


def _clean(obj):
    """Retire les clés de commentaire (_comment, _note, _xxx)."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def _get(d, path):
    for part in path.split("."):
        d = d.get(part, "") if isinstance(d, dict) else ""
    return d


def build(legal=None, sources=None):
    """Contenu publié : informations légales nettoyées + licences des sources + champs manquants."""
    legal = _clean(legal if legal is not None else json.loads(LEGAL_FILE.read_text(encoding="utf-8")))
    if sources is None:
        sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8")).get("sources", [])
    legal["sources"] = sorted(({"nom": s.get("name", s.get("id")), "licence": s.get("license", "")}
                               for s in sources if s.get("enabled", True)), key=lambda s: s["nom"].lower())
    legal["missing"] = [label for path, label in REQUIRED.items() if not str(_get(legal, path)).strip()]
    legal["sous_traitants"] = [s for s in legal.get("sous_traitants", []) if s.get("actif", True) and s.get("nom")]
    return legal


def write(log=print):
    """Écrit docs/data/legal.js. Ne fait jamais échouer la collecte."""
    try:
        data = build()
        publish.write_js("legal.js", "VS_LEGAL", data)
        if data["status"] == "en vigueur" and data["missing"]:
            log(f"  ⚠ Mentions légales « en vigueur » mais incomplètes : {', '.join(data['missing'])}")
    except Exception as exc:  # une erreur de saisie dans legal.json ne doit pas bloquer la carte
        log(f"  ✘ Informations légales non publiées ({type(exc).__name__} : {exc}) – vérifiez config/legal.json")


if __name__ == "__main__":
    d = build()
    publish.write_js("legal.js", "VS_LEGAL", d)
    print(f"docs/data/legal.js écrit – statut « {d['status']} »")
    print("Champs à compléter : " + (", ".join(d["missing"]) or "aucun"))
