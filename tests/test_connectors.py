"""Flux officiels et GDELT (v0.28) : ce qui n'est pas un incident n'arrive pas sur la carte.

Cas tirés de l'audit de la production d'octobre 2026 (angor.fr, 7 jours d'événements).
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from veille import geo
from veille.connectors import gdelt_events, meteoalarm, nws, official_rss

NOW = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)


def _ctx(countries, **kw):
    logs = []
    ctx = SimpleNamespace(now=NOW, countries=countries, log=logs.append, state={}, purge=[], prefetch={},
                          advisories={}, logs=logs)
    for k, v in kw.items():
        setattr(ctx, k, v)
    return ctx


# ------------------------------------------------------------------ NWS (États-Unis)
@pytest.mark.parametrize("name", ["Hard Freeze Warning", "Frost Advisory", "Red Flag Warning", "Fire Weather Watch",
                                  "Dense Fog Advisory", "Air Quality Alert", "Winter Storm Watch", "Flood Watch",
                                  "Wind Advisory", "Special Weather Statement"])
def test_nws_produits_sans_valeur_incident(name):
    assert not nws.worth_keeping(name)


@pytest.mark.parametrize("name", ["Tornado Warning", "Flash Flood Warning", "Hurricane Watch", "Tsunami Watch",
                                  "Storm Surge Watch", "Extreme Wind Warning", "Evacuation Immediate", "Blizzard Warning"])
def test_nws_alertes_gardees(name):
    assert nws.worth_keeping(name)


def _nws_feature(event, headline, desc, severity="Severe"):
    return {"geometry": {"type": "Polygon", "coordinates": [[[-120.5, 38.5], [-120.4, 38.5], [-120.4, 38.6], [-120.5, 38.5]]]},
            "properties": {"event": event, "headline": headline, "description": desc, "severity": severity,
                           "urgency": "Immediate", "certainty": "Observed", "areaDesc": "Amador County, CA",
                           "sent": "2026-10-23T10:00:00+00:00", "@id": "https://api.weather.gov/alerts/x"}}


def test_nws_evacuation_categorie_lue_dans_le_texte(monkeypatch, countries):
    feats = [_nws_feature("Evacuation Immediate", "Evacuate now due to wildfire", "A fast-moving fire near Pine Grove…"),
             _nws_feature("Frost Advisory", "Frost tonight", "Temperatures near 30."),
             _nws_feature("Civil Danger Warning", "Police activity", "Shelter in place.")]
    monkeypatch.setattr(nws.http, "get_json", lambda *a, **k: {"features": feats})
    out = nws.fetch({}, _ctx(countries))
    cats = {e["title"].split(" –")[0]: e["category"] for e in out}
    assert cats == {"Evacuation Immediate": "wildfire", "Civil Danger Warning": "infrastructure"}


# ------------------------------------------------------------------ Meteoalarm (Europe)
def test_meteoalarm_zones_maritimes():
    assert meteoalarm.marine_only(["Northern Baltic Sea", "Sea of Bothnia"])
    assert meteoalarm.marine_only(["Kattegat"])
    assert not meteoalarm.marine_only(["Uusimaa", "Northern Baltic Sea"])
    assert not meteoalarm.marine_only([])


def _warning(typ, level, area):
    return {"alert": {"msgType": "Alert", "sent": "2026-10-23T06:00:00+00:00",
                      "info": [{"language": "en-GB", "event": "Warning", "expires": "2026-10-24T06:00:00+00:00",
                                "onset": "2026-10-23T08:00:00+00:00",
                                "parameter": [{"valueName": "awareness_level", "value": f"{level}; Severe"},
                                              {"valueName": "awareness_type", "value": f"{typ}; x"}],
                                "area": [{"areaDesc": area}]}]}}


def test_meteoalarm_brouillard_orange_et_mer_ecartes(monkeypatch, countries):
    data = {"warnings": [_warning("4", "3; orange", "Uusimaa"),            # brouillard orange : écarté
                         _warning("1", "3; orange", "Northern Baltic Sea"),  # vent en mer seulement : écarté
                         _warning("10", "4; red", "Lapland")]}               # pluie rouge à terre : gardée
    monkeypatch.setattr(meteoalarm.http, "get_json", lambda *a, **k: data)
    out = meteoalarm.fetch({"countries": ["FI"]}, _ctx(countries))
    assert [(e["category"], e["severity"]) for e in out] == [("flood", 4)]


# ------------------------------------------------------------------ NHC : un cyclone = une fiche
RSS = """<?xml version="1.0"?><rss version="2.0"><channel>{}</channel></rss>"""
ITEM = ("<item><title>{t}</title><description>Location 15.2N 105.3W</description>"
        "<pubDate>{d}</pubDate><link>https://www.nhc.noaa.gov/{n}</link><guid>{n}</guid></item>")


def test_nhc_un_seul_bulletin_par_tempete(countries):
    cfg = {"id": "nhc_epac", "url": "https://www.nhc.noaa.gov/index-ep.xml", "category": "cyclone", "severity": 2,
           "keep": "Public Advisory", "max_age_days": 3, "severity_words": {"hurricane": 3},
           "group": "(?:hurricane|tropical storm|tropical depression)\\s+([a-z]+)"}
    items = [("Hurricane Vance Public Advisory Number 7", 3), ("Hurricane Vance Public Advisory Number 9", 1),
             ("Hurricane Vance Public Advisory Number 8", 2), ("Tropical Storm Wynne Public Advisory Number 2", 1)]
    xml = RSS.format("".join(ITEM.format(t=t, d=(NOW - timedelta(hours=h)).strftime("%a, %d %b %Y %H:%M:%S GMT"), n=i)
                             for i, (t, h) in enumerate(items)))
    ctx = _ctx(countries, prefetch={cfg["url"]: SimpleNamespace(content=xml.encode())})
    out = official_rss.fetch(cfg, ctx)
    assert sorted(e["title"] for e in out) == ["Hurricane Vance Public Advisory Number 9",
                                                "Tropical Storm Wynne Public Advisory Number 2"]
    again = official_rss.fetch(cfg, ctx)
    assert {e["id"] for e in out} == {e["id"] for e in again}          # identifiant stable d'un bulletin à l'autre


# ------------------------------------------------------------------ GDELT
def _row(code, lat, lon, geo_name, actor_cc=("", ""), feature="F1", articles=30, url="https://a.example/x"):
    r = [""] * 61
    c = gdelt_events.C
    r[c["id"]], r[c["sqldate"]], r[c["is_root"]], r[c["code"]], r[c["root"]] = "1", "20261023", "1", code, code[:2]
    r[c["actor1_cc"]], r[c["actor2_cc"]] = actor_cc
    r[c["articles"]], r[c["geo_type"]], r[c["geo_name"]] = str(articles), "4", geo_name
    r[c["lat"]], r[c["lon"]], r[c["feature"]] = str(lat), str(lon), feature
    r[c["added"]], r[c["url"]] = "20261023114500", url
    return r


def _gdelt(monkeypatch, countries, rows):
    monkeypatch.setattr(gdelt_events.http, "get",
                        lambda *a, **k: SimpleNamespace(text="1 2 http://data.gdeltproject.org/gdeltv2/20261023114500.export.CSV.zip"))
    monkeypatch.setattr(gdelt_events, "_rows", lambda stamp, log: rows if stamp.minute == 45 else [])
    monkeypatch.setattr(geo, "_CAPITALS", {"c": {"SA": ("Riyadh", 24.68773, 46.72185), "YE": ("Sanaa", 15.35, 44.2)}})
    ctx = _ctx(countries, state={"gdelt_filter_version": gdelt_events.FILTER_VERSION,
                                 "gdelt_last": "2026-10-23T11:30:00+00:00"},
               advisories={"x": {"SA": {"level": 3}, "YE": {"level": 4}}})
    return gdelt_events.fetch({"max_files_per_run": 1}, ctx)


def test_gdelt_occupation_de_territoire_ecartee(monkeypatch, countries):
    rows = [_row("192", 15.35, 44.2, "Sanaa, Yemen", ("YEM", ""), url=f"https://s{i}.example/a") for i in range(3)]
    assert _gdelt(monkeypatch, countries, rows) == []


def test_gdelt_capitale_en_tete_de_depeche(monkeypatch, countries):
    """« RIYADH – la coalition frappe au Yémen » : le point tombe sur Riyad alors que les acteurs sont yéménites."""
    dateline = [_row("195", 24.69, 46.72, "Riyadh, Saudi Arabia", ("SAU", "YEM"), "R1", url=f"https://s{i}.example/a")
                for i in range(3)]
    local = [_row("195", 17.49, 44.13, "Najran, Saudi Arabia", ("SAU", "YEM"), "N1", url=f"https://n{i}.example/a")
             for i in range(3)]
    out = _gdelt(monkeypatch, countries, dateline + local)
    assert [e["place"] for e in out] == ["Najran, Saudi Arabia"]


def test_gdelt_occupation_de_territoire_au_tri():
    from conftest import make

    from veille import triage
    g = make("g1", source="GDELT", title="Occupation of territory – Gaza", category="armed_conflict",
             tags=["auto-detected"])
    g["headline"] = "Israeli army holds positions in Gaza"
    assert triage.verdict(g, NOW) == ("noise", "situation, pas un fait daté")


# ------------------------------------------------------------------ flux propres des médias (v0.28, run 3)
from veille.connectors import outlet_feeds  # noqa: E402
from veille.robots import RobotsDisallowed  # noqa: E402

FEED = ("<?xml version='1.0'?><rss version='2.0'><channel>" + "".join(
    f"<item><title>Attaque contre un poste militaire à Tillabéri ({i})</title><link>https://actuniger.com/a{i}</link>"
    f"<pubDate>Fri, 23 Oct 2026 0{i}:00:00 +0000</pubDate><description>Des hommes armés ont attaqué…</description></item>"
    for i in range(4)) + "</channel></rss>").encode()


def test_flux_annonce_par_la_page_d_accueil():
    page = ('<head><link rel="alternate" type="application/rss+xml" title="Flux" href="/feed/">'
            '<link rel="alternate" type="application/rss+xml" href="https://x.example/comments/feed/">'
            '<link rel="stylesheet" href="/s.css"></head>')
    assert outlet_feeds.feed_links(page, "https://x.example/") == ["https://x.example/feed/"]


def test_decouverte_du_flux():
    pages = {"https://actuniger.com/": SimpleNamespace(text="<html>sans lien</html>", url="https://actuniger.com/"),
             "https://actuniger.com/feed/": SimpleNamespace(content=FEED)}

    def get(u):
        if u not in pages:
            raise ValueError("404")
        return pages[u]
    assert outlet_feeds.discover("actuniger.com", get) == ("https://actuniger.com/feed/", "")
    assert outlet_feeds.discover("vide.example", get) == ("", "injoignable")      # aucun serveur n'a répondu

    class NotFound(Exception):
        response = SimpleNamespace(status_code=404)

    def get404(u):
        if u == "https://sansflux.example/":
            return SimpleNamespace(text="<html></html>", url=u)
        raise NotFound()
    assert outlet_feeds.discover("sansflux.example", get404) == ("", "aucun flux")

    def forbidden(u):
        raise RobotsDisallowed("interdit")
    assert outlet_feeds.discover("interdit.example", forbidden) == ("", "robots.txt")


def test_lecture_par_roulement(monkeypatch, countries):
    catalog = {"NE": [["ActuNiger", "actuniger.com", "fr"], ["RFI", "rfi.fr", "fr", "+"]],
               "ML": [["Maliweb", "maliweb.net", "fr"]]}
    monkeypatch.setattr(outlet_feeds.config, "load_json", lambda *a, **k: {"countries": catalog})
    monkeypatch.setattr(outlet_feeds, "discover",
                        lambda d: ("https://actuniger.com/feed/", "") if d == "actuniger.com" else ("", "aucun flux"))

    def get(url, **kw):
        assert kw.get("robots") is True
        return SimpleNamespace(content=FEED)
    monkeypatch.setattr(outlet_feeds.http, "get", get)
    ctx = _ctx(countries)
    ctx.press = []
    assert outlet_feeds.fetch({"discover_per_run": 10}, ctx) == []
    assert set(ctx.state["outlet_feeds"]) == {"actuniger.com", "maliweb.net"}      # « + » (RFI) non examiné
    assert len(ctx.press) == 4 and ctx.press[0]["country_hint"] == "NE" and ctx.press[0]["site"] == "actuniger.com"
    s = outlet_feeds.summary(ctx.state, catalog)
    assert s == {"outlets": 2, "checked": 2, "feeds": 1, "robots": 0, "countries": 2, "covered": 1}
    # flux devenu interdit : retiré, redécouvert plus tard
    monkeypatch.setattr(outlet_feeds.http, "get", lambda url, **kw: (_ for _ in ()).throw(RobotsDisallowed("x")))
    outlet_feeds.fetch({"discover_per_run": 0}, ctx)
    assert ctx.state["outlet_feeds"]["actuniger.com"]["f"] == "" and \
        ctx.state["outlet_feeds"]["actuniger.com"]["w"] == "robots.txt"
