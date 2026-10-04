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
