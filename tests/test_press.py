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
        got = press.is_event(r["titre"], cat)
        tp += want and got
        fp += got and not want
        fn += want and not got
    precision, rappel = tp / max(1, tp + fp), tp / max(1, tp + fn)
    assert precision >= 0.92, f"précision {precision:.0%}"   # v0.23 : 94 % (51 % en v0.22 sur le même jeu)
    assert rappel >= 0.98, f"rappel {rappel:.0%}"


# ------------------------------------------------------------------ contexte : Fil, pas carte (v0.23)
# Un « événement » doit pouvoir toucher physiquement un voyageur ou un site. Cas réels relevés en production.
CONTEXTE = [
    ("Detienen en Lerma a dos hombres y una menor por presunto secuestro y extorsión", "arrestation ou suites"),
    ("Saint-Louis. Menace d'attentat dans son lycée : l'élève de 16 ans a voulu faire une « blague »", "projet déjoué"),
    ("OIC, Arab states condemn drone attack on Saudi Arabia's Medina power station", "déclaration"),
    ("Saudi Arabia rejects Houthi claim of attack on Riyadh", "déclaration"),
    ("Seattle police chief resigns in wake of deadly food festival shooting: Mayor", "déclaration"),
    ("100 anni fa l'attentato a Mussolini a Bologna", "rétrospective ou démenti"),
    ("Pakistan Militant Attacks Hit 12-Year High in September", "analyse"),
    ("Attentato di Modena. Salim era sorvegliato? Scontro sugli 007", "analyse"),
    ("Ariana : 100 MD pour protéger les villes contre les inondations", "prévention, bilan ou suites"),
]
EVENEMENTS = [   # faux rejets corrigés en v0.23
    "Three people transported to hospital after downtown Las Vegas shooting, police say",   # victimes, pas une arrestation
    "The Sudanese Armed Forces (SAF) repelled an attack by the Rapid Support Forces (RSF)",    # « Support Forces »
    "Le Yémen affirme avoir mené des centaines de frappes contre les Houthis",               # annonce d'un fait
    "Ukraine latest: Kyiv bridge hit in Russian air strike as Moscow vows retaliation",
    "Ataque armado en la colonia 5 de Febrero deja un muerto y dos heridos en Culiacán",     # 1 + 2 victimes
    "Matan a juez de paz del municipio de Mazatepec, Morelos en ataque armado",              # cible publique
    "Reportan ataque armado en secundaria de Torreón",
    "Flash Floods Damage Section Of East-West Road, Delta Residents Seek Urgent Intervention",
    "Feuer unter Stromleitungen in Berlin - Anschlag?",                                     # question, mais feu constaté
    "Kathua shooting: CISF Head Constable kills 4 colleagues in Jammu and Kashmir",          # « kills 4 »
    "Israeli strike kills 2 Christian women, lecturer, her mother in new Gaza ceasefire breach",
]


@pytest.mark.parametrize("titre,motif", CONTEXTE)
def test_titres_de_contexte(titre, motif):
    cat, _ = press.classify(titre)
    assert cat and press.context(titre, cat) == motif and not press.is_event(titre, cat)


@pytest.mark.parametrize("titre", EVENEMENTS)
def test_evenements_physiques_gardes(titre):
    cat, _ = press.classify(titre)
    assert press.is_event(titre, cat), (cat, press.not_incident(titre, cat), press.context(titre, cat) if cat else None)


def test_violence_electorale_n_est_pas_un_signal_diplomatique():
    t = "Elecciones 2026 bajo tensión: reportan DISPAROS y ánforas incendiadas en Loreto y Áncash"
    assert press.classify(t)[0] == "unrest" and press.is_event(t, "unrest")


def test_bilan_additionne_morts_et_blesses():
    assert press.casualty_toll(press.norm("deja un muerto y dos heridos")) == 3
    assert press.casualty_toll(press.norm("gunman kills 4 colleagues")) == 4
    assert press.casualty_toll(press.norm("attack in 2026 leaves people worried")) == 0


def test_gdelt_titre_reel_de_l_article():
    """GDELT : la catégorie vient d'un code, le titre réel de l'article dit souvent autre chose."""
    assert press.gdelt_noise("Megyn Kelly Melts Down at 'SVU' Star in Unhinged Rant") == "hors sujet"
    assert press.gdelt_noise("Explainer: Who are the Houthis, Iran") == "hors sujet"
    assert press.gdelt_noise("Retired Major Gen Golam Mohiuddin arrested over attack on New Gini Properties")
    assert press.gdelt_noise("Israeli forces shell village in southern Syria") is None
    assert press.gdelt_noise("Flames, Smoke Reported at Aramco Facility South of Saudi Capital") is None
    assert press.gdelt_noise("Russian attacks kill 6 in Ukraine and damage Kyiv's Northern Bridge") is None
    assert press.gdelt_noise("") is None


def test_contexte_dans_le_fil_pas_sur_la_carte():
    from datetime import datetime, timezone
    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    items = [{"title": t, "url": f"https://x/{i}", "outlet": "X", "date": now, "country_hint": "MX", "lang": "es"}
             for i, t in enumerate(["Detienen en Lerma a dos hombres por presunto secuestro y extorsión en Toluca",
                                    "Ataque armado en Culiacán deja tres muertos"])]
    events, news, _ = press.build(items, [], {}, lambda m: None, now)
    assert len(news) == 2 and [n.get("context") for n in news] == ["arrestation ou suites", None]
    assert all("Detienen" not in e["title"] for e in events)
