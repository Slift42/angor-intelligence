"""Recoupement (v0.25) : sources indépendantes, confirmation par les capteurs officiels, démentis, cotation."""
from conftest import make

from veille import corroborate, quality


def _src(name, url, title=""):
    return {"name": name, "url": url, "title": title}


def test_reprises_et_groupes_de_presse_ne_sont_pas_independants():
    e = make("p1", tags=["press"], title="Explosion à Lyon : trois blessés")
    t = "Explosion dans un immeuble de Lyon : trois blessés, le quartier évacué"
    e["sources"] = [_src("Le Progrès", "https://www.leprogres.fr/a", t), _src("DNA", "https://www.dna.fr/b", t),
                    _src("Le Dauphiné", "https://www.ledauphine.com/c", "Lyon : une explosion fait trois blessés"),
                    _src("Le Monde", "https://www.lemonde.fr/d", t), _src("BFMTV", "https://www.bfmtv.com/e", "Lyon : explosion")]
    c = corroborate.independence(e)
    # EBRA (Progrès, DNA, Dauphiné) = 1 ; Le Monde reprend mot pour mot le titre EBRA = reprise ; BFMTV = 1
    assert c["outlets"] == 5 and c["independent"] == 2 and c["copies"] == 3 and c["kinds"] == ["presse"]


def test_recit_de_presse_rattache_a_la_mesure_usgs():
    usgs = make("usgs-1", source="USGS", category="earthquake", title="M 6.1 - 20 km S of Ruteng, Indonesia",
                lat=-8.8, lon=120.4, country="ID", date="2026-10-01T02:00:00+00:00")
    usgs["sources"] = [_src("USGS", "https://usgs/1", usgs["title"])]
    press = make("p-1", category="earthquake", tags=["press"], title="Gempa M 6,1 guncang Flores, warga panik",
                 lat=-8.6, lon=120.5, country="ID", date="2026-10-01T05:00:00+00:00", severity=2)
    press["sources"] = [_src("Kompas", "https://kompas.com/x", press["title"])]
    out = corroborate.run([usgs, press], log=lambda m: None)
    assert [e["id"] for e in out] == ["usgs-1"] and out[0]["press_reports"] == 1 and "p-1" in out[0]["merged"]
    assert len(out[0]["sources"]) == 2 and len(usgs["sources"]) == 1          # la mémoire du robot n'est pas modifiée
    assert quality.rate(out[0]) == "A1"


def test_seisme_chiffre_sans_mesure_officielle():
    p = make("p-2", category="earthquake", tags=["press"], title="Sismo de magnitud 6.2 sacude Oaxaca", lat=17, lon=-96.7,
             country="MX")
    p["sources"] = [_src("Diario", "https://diario.mx/a", p["title"])]
    out = corroborate.run([p], log=lambda m: None)
    assert out[0]["unconfirmed"] == "capteurs" and quality.rate(out[0])[1] == "4"
    q = make("p-3", category="earthquake", tags=["press"], title="Familias afectadas por el terremoto protestan", country="MX")
    assert not corroborate.run([q], log=lambda m: None)[0].get("unconfirmed")    # pas un séisme chiffré : pas d'alerte


def test_dementi_signale():
    e = make("p-4", tags=["press"], title="Shooting at Cavite school leaves students injured", country="PH",
             date="2026-10-02T08:00:00+00:00")
    e["sources"] = [_src("Rappler", "https://rappler.com/a", e["title"]), _src("Inquirer", "https://inquirer.net/b", e["title"] + " (2)")]
    ctx = [{"title": "PNP: fake report of shooting at Cavite school, no students injured", "url": "https://abs-cbn.com/x",
            "source": "ABS-CBN", "country": "PH", "date": "2026-10-02T12:00:00+00:00"}]
    out = corroborate.run([e], ctx, log=lambda m: None)
    assert out[0]["disputed"]["source"] == "ABS-CBN" and quality.rate(out[0])[1] == "4"
    other = [{"title": "Fake news about elections in Manila", "country": "PH", "date": "2026-10-02T12:00:00+00:00"}]
    assert not corroborate.run([e], other, log=lambda m: None)[0].get("disputed")


def test_credibilite_deux_types_de_sources():
    e = make("p-5", tags=["press"], title="Cholera outbreak in Kasai")
    e["corroboration"] = {"independent": 2, "outlets": 2, "copies": 0, "kinds": ["officiel", "presse"]}
    assert quality.credibility(e, "B") == 2
    e["corroboration"] = {"independent": 2, "outlets": 6, "copies": 4, "kinds": ["presse"]}
    assert quality.credibility(e, "B") == 3
