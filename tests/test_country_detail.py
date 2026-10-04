"""Fiche pays détaillée (veille/country_detail.py) : choix des villes, santé, activité."""
import json
from pathlib import Path

from veille import country_detail as cd

# [nom, nom_fr, iso, lat, lon, population, capitale, région, fuseau, autres noms]
PLACES = [
    ["New Delhi", "New Delhi", "IN", 28.6, 77.2, 300000, 1, "Delhi", "Asia/Kolkata", ""],
    ["Delhi", "Delhi", "IN", 28.66, 77.23, 15000000, 0, "Delhi", "Asia/Kolkata", ""],
    ["Mumbai", "Bombay", "IN", 19.07, 72.88, 18000000, 0, "Maharashtra", "Asia/Kolkata", ""],
    ["Kolkata", "Calcutta", "IN", 22.57, 88.36, 14000000, 0, "West Bengal", "Asia/Kolkata", ""],
    ["Smalltown", "Smalltown", "IN", 20.0, 80.0, 120000, 0, "", "", ""],
]


def test_une_entree_par_agglomeration_capitale_en_tete():
    names = [c[0] for c in cd._select_cities(PLACES, "IN", [])]
    assert names[0] == "New Delhi"                            # la capitale en premier
    assert "New Delhi" in names and "Delhi" not in names     # Delhi absorbée par la capitale (< 25 km)
    assert "Smalltown" not in names


def test_ville_suivie_ajoutee_meme_petite():
    notes = [{"iso": "IN", "city": "Smalltown", "level": 3}]
    assert "Smalltown" in [c[0] for c in cd._select_cities(PLACES, "IN", notes)]


def test_sante_selon_listes():
    cfg = json.loads((Path(__file__).resolve().parent.parent / "config" / "health.json").read_text(encoding="utf-8"))
    ml = cd._health("ML", cfg)
    assert ml["malaria"] == "high"
    assert "yellow_fever_cert" in ml["vaccines"] and "meningitis" in ml["risks"]
    fr = cd._health("FR", cfg)
    assert fr["malaria"] is None and "rabies" not in fr["risks"] and fr["vaccines"] == ["routine"]


def test_activite_incidents():
    assert cd._activity([]) == (0, 0)
    score, level = cd._activity([{"severity": 4}] * 10)
    assert score == 80 and level == 4


def test_notes_de_villes_valides():
    data = json.loads((Path(__file__).resolve().parent.parent / "config" / "city_notes.json").read_text(encoding="utf-8"))
    for n in data["cities"]:
        assert len(n["iso"]) == 2 and n["city"], n
        assert 1 <= n["level"] <= 5, n["city"]
        assert n["summary"], n["city"]
