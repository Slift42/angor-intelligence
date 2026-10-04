"""Format d'événement standard (veille/model.py) et géographie (veille/geo.py)."""
from conftest import make

from veille import geo, model


def test_make_event_normalise_les_champs():
    e = make(severity=9, category="inconnue", title="  Titre  ")
    assert e["severity"] == 4            # bornée à 1..4
    assert e["category"] == "other"      # catégorie inconnue → other
    assert e["title"] == "Titre"
    assert e["sources"][0]["name"] == "Press"
    assert e["start"] == e["date"]


def test_parse_iso_sans_fuseau_est_utc():
    assert model.parse_iso("2026-09-30T10:00:00").utcoffset().total_seconds() == 0
    assert model.parse_iso("2026-09-30T10:00:00Z").hour == 10
    assert model.parse_iso("") is None


def test_taxonomie_coherente():
    tax = model.taxonomy()
    for key, cat in tax["categories"].items():
        assert cat["group"] in tax["groups"], key
        assert cat["fr"] and cat["en"] and cat["icon"], key


def test_localisation_pays(countries):
    assert countries.locate(48.85, 2.35) == "FR"
    assert countries.locate(12.65, -8.0) == "ML"
    assert countries.by_country_name("Ivory Coast")["iso2"] == "CI"


def test_distances():
    assert 330 < geo.haversine_km(48.85, 2.35, 51.5, -0.12) < 360   # Paris – Londres
    assert geo.km_to_segment(48.85, 2.35, (48.85, 2.0), (48.85, 3.0)) < 1
