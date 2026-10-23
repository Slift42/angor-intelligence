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


def test_contexte_des_articles_du_fil_recalcule():
    import collecte
    old = {"id": "press-1", "title": "Detienen en Lerma a dos hombres y una menor por presunto secuestro y extorsión",
           "category": "attack"}   # article du Fil antérieur à la v0.23
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


# ------------------------------------------------------------------ doublons restants en production (v0.28, run 2)
def _ev(id, title, source="Press", category="attack", lat=31.18, lon=35.70, country="JO", date="2026-10-23T14:00:00+00:00",
        place="", headline=None, precision="city"):
    e = _src(make(id, source=source, category=category, title=title, lat=lat, lon=lon, country=country, date=date,
                  place=place, precision=precision, tags=["auto-detected"] + (["press"] if source == "Press" else [])), id)
    if headline:
        e["headline"] = headline
    return e


def test_meme_attaque_crime_et_conflit_fusionnes():
    """Église de Karak (Jordanie) : « crime » d'un côté, « conflit armé » de l'autre, même fait."""
    a = _ev("g1", "Crime – Karak, Jordan", "GDELT", "crime",
            headline="Gunmen open fire inside a church in Jordan, causing deaths and injuries")
    b = _ev("g2", "Military force – Karak, Jordan", "GDELT", "armed_conflict", date="2026-10-23T20:55:00+00:00",
            headline="Seven killed as gunmen open fire at church in Jordan in 'terrorist' attack, authorities say")
    assert len(dedupe.dedupe([a, b])) == 1


def test_meme_cible_autres_mots_fusionnes():
    """Règle E : même pays, même jour, même cible (aéroport) et des mots en commun."""
    a = _ev("p1", "One Killed, Eight Injured in Attack on Saudi Arabia's King Fahd Airport", lat=26.47, lon=49.80,
            country="SA", place="Dammam", date="2026-10-23T01:24:00+00:00")
    b = _ev("p2", "Indian among 2 killed in attack on Dammam airport, 2 other Indians injured", lat=26.43, lon=50.10,
            country="SA", place="Dammam, Ash Sharqiyah", date="2026-10-22T12:22:00+00:00")
    assert len(dedupe.story_merge([a, b])) == 1


def test_gdelt_commune_voisine_meme_fait():
    """GDELT place la fusillade « near Paris » à Trappes (28 km) : même fait si l'article raconte la même chose."""
    g = _ev("g1", "Armed violence – Trappes, France", "GDELT", lat=48.7741, lon=2.0178, country="FR",
            place="Trappes, France", date="2026-10-23T20:55:00+00:00",
            headline="Terror investigation launched after drive-by shooting near Paris")
    p = _ev("p1", "One killed, four injured in drive-by shooting near Paris", lat=48.853, lon=2.349, country="FR",
            place="Paris", date="2026-10-23T10:08:00+00:00")
    assert len(dedupe.dedupe([g, p])) == 1


def test_gdelt_et_presse_sans_rapport_non_fusionnes():
    """Même ville, même jour, mais deux faits : seuls « Gaza » et « Israeli » en commun."""
    g = _ev("g1", "Military force – Gaza", "GDELT", "armed_conflict", lat=31.5, lon=34.47, country="PS", place="Gaza",
            headline="Palestinian child killed as Israeli forces fire on displaced people's tents in central Gaza")
    p = _ev("p1", "'Season of fear': Escalating Israeli attacks on West Bank olive farmers, deadly strikes on Gaza",
            category="armed_conflict", lat=31.5, lon=34.47, country="PS", place="Gaza", date="2026-10-23T01:00:00+00:00")
    assert len(dedupe.dedupe([g, p])) == 2


def test_deux_articles_gdelt_meme_ville_non_fusionnes():
    a = _ev("g1", "Protest – Delhi", "GDELT", "unrest", lat=28.65, lon=77.23, country="IN", place="Delhi, India",
            headline="'India is neither Bangladesh nor France': Rijiju alleges plot to trigger violence")
    b = _ev("g2", "Protest – Delhi", "GDELT", "unrest", lat=28.65, lon=77.23, country="IN", place="Delhi, India",
            date="2026-10-23T20:00:00+00:00", headline="Delhi police seize Cockroach leader as youth defy state!")
    assert len(dedupe.dedupe([a, b])) == 2


def test_crue_meme_ville_deux_articles_fusionnes():
    a = _ev("p1", "Fuertes lluvias en Fusagasugá causan inundaciones y daños", category="flood", lat=4.34, lon=-74.36,
            country="CO", place="Fusagasugá")
    b = _ev("p2", "Emergencia en Fusagasugá, Cundinamarca, por inundaciones tras fuertes lluvias: se reporta desbordamiento",
            category="flood", lat=4.35, lon=-74.37, country="CO", place="Fusagasugá", date="2026-10-22T22:00:00+00:00")
    assert len(dedupe.dedupe([a, b])) == 1


def test_lieux_communs_ne_suffisent_pas():
    """Règle D : « West Bank », « Israeli » ne prouvent pas un même fait (plusieurs par jour)."""
    a = _ev("p1", "West Bank attack wounds 5 Israelis as Netanyahu cancels events", country="PS", place="West Bank",
            lat=31.9, lon=35.2, precision="country")
    b = _ev("p2", "West Bank Olive Harvest Under Attack as Israeli Settlers Target Palestinian Farmers", country="PS",
            place="West Bank", lat=31.9, lon=35.2, precision="country", date="2026-10-22T12:00:00+00:00")
    out = dedupe.story_merge([a, b])
    assert len(out) == 2
