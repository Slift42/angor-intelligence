"""robots.txt (v0.28, run 3) : règles RFC 9309, mémoire, exemptions, contrôle avant toute lecture d'un flux."""
from datetime import datetime, timedelta, timezone

import pytest
import requests

from veille import http, robots

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
GOOGLE_NEWS = """User-agent: *
Disallow: /
Allow: /$
Allow: /home$
Allow: /topics/

User-agent: GPTBot
Disallow: /
"""


def test_google_news_interdit_la_recherche_rss():
    rules = robots.parse(GOOGLE_NEWS)
    assert not robots.verdict(rules, "/rss/search?q=Niger&hl=fr")
    assert robots.verdict(rules, "/") and robots.verdict(rules, "/topics/abc")
    assert not robots.verdict(rules, "/home/x")          # « $ » : /home seulement


def test_groupe_du_robot_prioritaire_et_regle_la_plus_longue():
    text = "User-agent: *\nDisallow: /\n\nUser-agent: VeilleSurete\nDisallow: /private/\nAllow: /private/feed\n"
    rules = robots.parse(text)
    assert robots.verdict(rules, "/feed/")
    assert not robots.verdict(rules, "/private/x")
    assert robots.verdict(rules, "/private/feed.xml")    # règle la plus longue : Allow
    assert robots.verdict(robots.parse("User-agent: *\nDisallow:\n"), "/tout")   # « Disallow: » vide = tout permis
    assert not robots.verdict(robots.parse("User-agent: *\nDisallow: /*.php$\n"), "/index.php")


def _fake(monkeypatch, responses):
    calls = []

    def fetch(scheme, host):
        calls.append(host)
        return responses[host]
    monkeypatch.setattr(robots, "_fetch", fetch)
    return calls


def test_memoire_et_statuts(monkeypatch):
    calls = _fake(monkeypatch, {"a.example": ({"s": 404, "r": []}, None),
                                "b.example": ({"s": 403, "r": [["d", "/"]]}, None),
                                "c.example": (None, "robots.txt de c.example injoignable (Timeout)")})
    assert robots.allowed("https://a.example/feed/", NOW)            # pas de robots.txt : permis
    assert not robots.allowed("https://b.example/feed/", NOW)        # 403 : prudence
    assert robots.allowed("https://c.example/feed/", NOW)            # injoignable, sans mémoire : lu, noté
    assert robots.messages() == ["robots.txt de c.example injoignable (Timeout)"]
    robots.allowed("https://a.example/autre", NOW + timedelta(days=2))
    assert calls.count("a.example") == 1                              # une semaine de mémoire
    robots.allowed("https://a.example/autre", NOW + timedelta(days=8))
    assert calls.count("a.example") == 2
    state = {}
    robots.save(state)
    assert set(state["robots"]) == {"a.example", "b.example"}


def test_reponse_connue_gardee_si_site_injoignable(monkeypatch):
    robots.configure([], {"robots": {"d.example": {"t": "2026-10-01T00:00:00+00:00", "s": 200, "r": [["d", "/"]]}}})
    _fake(monkeypatch, {"d.example": (None, "erreur 503")})
    assert not robots.allowed("https://d.example/feed", NOW)


def test_exemption_declaree_par_la_source(monkeypatch):
    _fake(monkeypatch, {"news.google.com": ({"s": 200, "r": robots.parse(GOOGLE_NEWS)}, None)})
    url = "https://news.google.com/rss/search?q=x"
    assert not robots.allowed(url, NOW)
    robots.configure([{"id": "gnews", "enabled": True, "robots_exempt": ["news.google.com"]}], {})
    assert robots.allowed(url, NOW)


def test_http_get_ne_lit_pas_une_adresse_interdite(monkeypatch):
    from importlib import reload
    real = reload(http)          # vraie fonction (la fixture bloque http.get)
    _fake(monkeypatch, {"x.example": ({"s": 200, "r": [["d", "/"]]}, None)})

    def no_request(*a, **k):
        raise AssertionError("aucune requête ne doit partir")
    monkeypatch.setattr(real._session, "get", no_request)
    with pytest.raises(robots.RobotsDisallowed):
        real.get("https://x.example/feed/", robots=True)
    with pytest.raises(AssertionError):
        real.get("https://x.example/api", robots=False)   # API documentée : pas de contrôle
    assert issubclass(real.RobotsDisallowed, Exception) and not issubclass(real.RobotsDisallowed,
                                                                             requests.RequestException)
