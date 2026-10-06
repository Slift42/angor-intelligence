"""Lecture des sources : XML abîmé, conseils FCDO, avis américains, trafic aérien."""
from conftest import NOW

from veille import fcdo, traffic
from veille.connectors import Context, rss, us_advisories


def test_xml_avec_esperluette_repare():
    root = rss.parse_xml(b'<?xml version="1.0"?><rss><channel><item><title>A & B</title></item></channel></rss>')
    assert root.tag == "rss"


SAFETY = """<h2>Terrorism</h2><p>There is a high threat of terrorist attack.</p>
<h3>Terrorism in Mali</h3><p>Attacks are likely in Bamako.</p><ul><li>hotels</li><li><p>markets</p></li></ul>
<h2>UK government support</h2><p>Ignored.</p>"""


def test_fcdo_decoupe_en_rubriques():
    secs = fcdo.parse_body(SAFETY)
    assert [s["h"] for s in secs] == ["Terrorism", "Terrorism in Mali"]
    assert secs[1]["b"][1] == ["ul", ["hotels", "markets"]]


def test_fcdo_numeros_urgence():
    secs = fcdo.parse_body("<h2>Emergency services in Mali</h2><p>Police: 17</p><p>Ambulance: 15</p><p>Telephone: 119 (police)</p>")
    got = {(e["service"], e["number"]) for e in fcdo.emergency(secs)}
    assert {("police", "17"), ("ambulance", "15"), ("police", "119")} <= got


def test_avis_americain_motifs(monkeypatch, countries):
    sample = [{"Title": "Afghanistan - Level 4: Do Not Travel", "Category": ["AF"], "Link": "https://t", "Updated": "2026-02-19",
               "Summary": "Do not travel<p>due to <b>civil unrest</b>, <b>crime, terrorism</b>, <b>risk of wrongful detention</b>, <b>kidnapping</b>.</p><p>More.</p>"}]
    monkeypatch.setattr(us_advisories.http, "get_json", lambda *a, **k: sample)
    out = us_advisories.fetch({}, Context(countries, {}, print, NOW))
    assert out["AF"]["level"] == 4
    assert {"terrorism", "crime", "unrest", "kidnapping", "detention"} <= set(out["AF"]["reasons"])


def test_trafic_format_compact():
    a = {"hex": "ae01c2", "flight": "GHOST52 ", "r": "165152", "t": "GLF4", "lat": 21.8034, "lon": -158.8315,
         "alt_baro": 9850, "gs": 410.4, "track": 120.2, "squawk": "2271", "dbFlags": 1}
    assert traffic._compact(a) == ["ae01c2", "GHOST52", "165152", "GLF4", 21.803, -158.832, 9850, 410, 120, "2271", 1]
    assert traffic._compact({"hex": "x"}) is None          # sans position : ignoré


def test_emsc_seismes(monkeypatch, countries):
    """v0.25 : EMSC (seismicportal.eu, FDSN GeoJSON) – recoupe l'USGS."""
    from veille.connectors import emsc
    sample = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": "20261005_0000101", "geometry": {"type": "Point", "coordinates": [26.9, 38.3, -10]},
         "properties": {"unid": "20261005_0000101", "time": "2026-10-05T21:14:03.2Z", "lat": 38.3, "lon": 26.9, "depth": 10,
                        "mag": 5.2, "magtype": "mw", "flynn_region": "WESTERN TURKEY", "evtype": "ke", "auth": "KOERI"}},
        {"type": "Feature", "id": "x2", "properties": {"unid": "x2", "time": "2026-10-05T20:00:00Z", "lat": 45, "lon": 7,
                                                       "mag": 4.4, "evtype": "qb", "flynn_region": "QUARRY"}}]}
    monkeypatch.setattr(emsc.http, "get_json", lambda *a, **k: sample)
    out = emsc.fetch({"min_magnitude": 4.0}, Context(countries, {}, print, NOW))
    assert [e["id"] for e in out] == ["emsc-20261005_0000101"]          # explosion de carrière (qb) écartée
    e = out[0]
    assert e["source"] == "EMSC" and e["title"] == "M 5.2 – Western Turkey" and e["severity"] == 2 and e["country"] == "TR"
    assert "KOERI" in e["summary"]


def test_medias_muets():
    """v0.25 : un média jamais trouvé après 30 requêtes est signalé (domaine erroné ou site fermé)."""
    from veille.connectors import outlets
    stats = {}
    for _ in range(30):
        outlets.record(stats, "NG", ["dailytrust.com", "bbc.com/hausa"], [{"site": "bbc.com"}], NOW)
    cat = {"NG": [["Daily Trust", "dailytrust.com", "en"], ["BBC Hausa", "bbc.com/hausa", "ha"]]}
    assert stats["NG|bbc.com/hausa"]["hits"] == 30
    assert outlets.muted(stats, cat) == [{"country": "NG", "domain": "dailytrust.com", "name": "Daily Trust", "queries": 30}]


def test_catalogue_des_medias():
    """v0.25 : ≈ 1 500 médias, langue de recherche connue, pas de doublon de domaine dans un même pays."""
    import json

    from conftest import ROOT

    from veille.connectors import outlets
    cat = json.loads((ROOT / "config" / "press_outlets.json").read_text(encoding="utf-8"))["countries"]
    rows = [(iso, o) for iso, lst in cat.items() for o in lst]
    assert len(cat) >= 200 and len(rows) >= 1400
    for iso, o in rows:
        assert o[2] in outlets.LANG_EDITION, (iso, o)
        assert not o[1].startswith(("http", "www.")) and " " not in o[1], (iso, o)
        assert len(o) < 5 or o[4] in "ABCDEF", (iso, o)
    for iso, lst in cat.items():
        doms = [o[1] for o in lst]
        assert len(doms) == len(set(doms)), iso
