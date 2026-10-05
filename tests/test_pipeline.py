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


# ------------------------------------------------------------------ regroupement par histoire (v0.23), cas réels
def _src(e, name):
    e["sources"] = [{"name": name, "url": "https://example.org/" + e["id"]}]
    return e


def test_meme_titre_plusieurs_jours_fusionne():
    t = "Pentagon IDs 4 American troops killed in Kuwait"
    evs = [_src(make(f"k{i}", title=t, category="armed_conflict", date=f"2026-10-0{d}T08:00:00+00:00", lat=29.37,
                     lon=47.98, country="KW", tags=["press"]), f"M{i}") for i, d in enumerate((1, 3, 4))]
    out = dedupe.story_merge(evs)
    assert len(out) == 1 and out[0]["date"].startswith("2026-10-04") and out[0]["start"].startswith("2026-10-01")
    assert sorted(out[0]["merged"]) == ["k1", "k2"] and "multi-source" in out[0]["tags"]


def test_meme_article_deux_villes_et_deux_categories():
    t = "Nuclear-capable Russian Tu-95 bomber plane crashes during training flight in Amur, 6 killed"
    a = make("a", title=t, category="attack", lat=50.0, lon=127.5, country="RU", precision="city")
    b = make("b", title=t, category="infrastructure", lat=51.0, lon=128.0, country="RU", precision="region", severity=2)
    out = dedupe.story_merge([b, a])
    assert len(out) == 1 and out[0]["id"] == "a" and out[0]["severity"] == 3   # le lieu le plus précis sert de base


def test_titre_google_news_avec_texte_parasite():
    base = "First Visuals Of Japan Tsunami: Waves SURGE In Tomakomai After Huge 7.7 Earthquake Jolts Nation"
    a = make("a", title=base + " Ugo Humbert", category="earthquake", lat=42.6, lon=141.6, country="JP")
    b = make("b", title=base + " Catherine", category="earthquake", lat=42.6, lon=141.6, country="JP",
             date="2026-10-01T10:00:00+00:00")
    assert len(dedupe.story_merge([a, b])) == 1


def test_bilan_mis_a_jour_fusionne_mais_pas_deux_jours_de_bilans():
    a = make("a", title="Pakistani airstrikes in Afghanistan kill 9 civilians, Kabul says", category="armed_conflict",
             lat=34.5, lon=69.2, country="AF")
    b = make("b", title="Pakistani airstrikes in Afghanistan kill 10 civilians, Kabul says", category="armed_conflict",
             lat=34.5, lon=69.2, country="AF", date="2026-10-01T09:00:00+00:00")
    assert len(dedupe.story_merge([a, b])) == 1
    c = make("c", title="Russians attack Dnipropetrovsk region more than 20 times in one day, one person injured",
             lat=48.45, lon=35.05, country="UA", date="2026-09-27T10:00:00+00:00")
    d = make("d", title="Russians attack Dnipropetrovsk region more than 30 times since morning, four injured",
             lat=48.45, lon=35.05, country="UA", date="2026-09-30T10:00:00+00:00")
    assert len(dedupe.story_merge([c, d])) == 2      # semblables mais 3 jours d'écart : deux événements


def test_histoires_differentes_conservees():
    a = make("a", title="Gunmen attack bus near Masyaf, seven killed", lat=35.06, lon=36.34, country="SY")
    b = make("b", title="Gunmen attack checkpoint near Homs, two soldiers killed", lat=34.73, lon=36.72, country="SY")
    c = make("c", title="Gunmen attack bus near Masyaf, seven killed", lat=35.06, lon=36.34, country="SY",
             date="2026-10-12T10:00:00+00:00")      # même titre 12 jours plus tard : autre événement
    assert len(dedupe.story_merge([a, b, c])) == 3
    g = make("g", source="GDELT", title="Armed violence – Homs, Syria", lat=34.73, lon=36.72, country="SY")
    assert dedupe.story_tokens(g) == []          # GDELT sans titre d'article : pas de regroupement par histoire
    g["headline"] = "Gunmen attack checkpoint near Homs, two soldiers killed - Reuters"
    assert len(dedupe.story_merge([b, g])) == 1


def test_tri_avant_regroupement():
    import collecte
    noise = make("n", title="Detienen en Lerma a dos hombres y una menor por presunto secuestro y extorsión",
                 tags=["press"], country="MX")
    real = make("r", title="Ataque armado en Culiacán deja tres muertos", tags=["press"], country="MX")
    gd = make("g", source="GDELT", title="Military force – Culiacán", tags=["auto-detected"], country="MX")
    gd["headline"] = "Megyn Kelly Melts Down at 'SVU' Star in Unhinged Rant"
    assert collecte.triage_reason(noise) == "contexte" and collecte.triage_reason(real) is None
    assert collecte.triage_reason(gd) == "hors sujet"
    old = {"id": "press-1", "title": noise["title"], "category": "attack"}   # article du Fil antérieur à la v0.23
    assert collecte.with_context(old)["context"] == "arrestation ou suites" and "context" not in old
    kev = {"id": "kev-CVE-1", "title": "CVE-1 – Arrested Vendor", "category": "cyber"}
    assert collecte.with_context(kev) is kev


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
