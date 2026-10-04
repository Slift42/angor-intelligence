"""Tri des titres de presse (veille/press.py) : catégorie, gravité, faux positifs connus.

Chaque cas correspond à une erreur réellement observée en production : ne pas supprimer un cas sans raison.
"""
import csv
from pathlib import Path

import pytest

from veille import press

GARDER = [
    ("Suicide bombing kills 12 at market in Mogadishu", "terrorism"),   # bug corrigé à l'audit v0.17
    ("Attentat-suicide contre une église à Damas", "terrorism"),
    ("Gunmen kill 5 in attack on village in Niger", "attack"),
    ("Earthquake of magnitude 6.2 strikes Turkey", "earthquake"),
    ("Protesters clash with police in Nairobi", "unrest"),
]
ECARTER = [
    "Assassinat de Johnnay à Champigny : la défense tente de torpiller l'enquête",   # procès, pas un attentat
    "Un adolescent se suicide après du harcèlement",                                   # drame privé
    "Football: PSG beat Marseille",
    "Bomberos apagan un incendio en Madrid",                                           # « bomb » ≠ « bomberos »
]


@pytest.mark.parametrize("titre,categorie", GARDER)
def test_titres_retenus(titre, categorie):
    cat, sev = press.classify(titre)
    assert cat == categorie
    assert 1 <= sev <= 4


@pytest.mark.parametrize("titre", ECARTER)
def test_titres_ecartes(titre):
    cat, _ = press.classify(titre)
    assert cat is None or press.not_incident(titre, cat)


def test_gravite_selon_bilan():
    _, sev = press.classify("Suicide bombing kills 60 at market in Mogadishu")
    assert sev == 4


def test_langue():
    assert press.guess_lang("Le gouvernement annonce des mesures") == "fr"
    assert press.guess_lang("The army said on Monday") == "en"


def test_jeu_etiquete_ne_regresse_pas():
    """Seuils minimaux sur tests/gold_tri.csv (voir tools/eval_tri.py). À relever quand le tri progresse."""
    rows = list(csv.DictReader(open(Path(__file__).parent / "gold_tri.csv", encoding="utf-8")))
    tp = fp = fn = 0
    for r in rows:
        want = r["garder"].strip() == "1"
        cat, _ = press.classify(r["titre"])
        got = bool(cat) and not press.not_incident(r["titre"], cat)
        tp += want and got
        fp += got and not want
        fn += want and not got
    precision, rappel = tp / max(1, tp + fp), tp / max(1, tp + fn)
    assert precision >= 0.85, f"précision {precision:.0%}"
    assert rappel >= 0.97, f"rappel {rappel:.0%}"
