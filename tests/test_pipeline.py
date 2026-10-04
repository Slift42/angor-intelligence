"""Dédoublonnage, cotation de l'Amirauté et note de risque pays."""
from conftest import NOW, make

from veille import dedupe, quality, risk


def test_meme_evenement_deux_medias_fusionne():
    a = make("p1", title="Gunmen attack army post near Bamako, 5 killed", tags=["press"])
    b = make("p2", title="Gunmen attack army post near Bamako killing 5 soldiers", tags=["press"])
    a["sources"] = [{"name": "RFI", "url": "u1"}]
    b["sources"] = [{"name": "Reuters", "url": "u2"}]
    out = dedupe.dedupe([a, b])
    assert len(out) == 1
    assert "multi-source" in out[0]["tags"]
    assert len(out[0]["sources"]) == 2


def test_evenements_differents_conserves():
    a = make("p1", title="Gunmen attack army post near Bamako")
    b = make("p2", title="Flood hits Mopti region", category="flood", lat=14.5, lon=-4.2)
    assert len(dedupe.dedupe([a, b])) == 2


def test_cotation_source_officielle():
    e = make(source="USGS", category="earthquake", title="M 6.1 - Turkey", lat=38.4, lon=27.1, country="TR")
    assert quality.rate(dict(e)) == "A1"


def test_note_risque_avis_ne_pas_se_rendre():
    out = risk.compute([make()], {"US State Dept": {"ML": {"level": 4, "scale": 4}}}, NOW)
    assert out["ML"]["level"] >= 4
    assert out["ML"]["data_quality"] == "advisories+events"


def test_diplomatie_hors_note():
    out = risk.compute([make(category="diplomatic")], {}, NOW)
    assert "ML" not in out or out["ML"]["counts"]["security"] == 0
