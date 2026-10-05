"""Contrôle d'entrée des événements (v0.24) : vérification a priori (avant la carte) et permanente (à chaque collecte)."""
from datetime import datetime, timedelta, timezone

from conftest import make

from veille import enrich, triage

NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)


def _st(e, verified=None):
    return triage.verdict(e, NOW, verified)


def test_presse_fait_physique_contexte_et_bruit():
    ok = make("p1", title="Ataque armado en Culiacán deja tres muertos", tags=["press"], country="MX")
    ctx = make("p2", title="Detienen en Lerma a dos hombres y una menor por presunto secuestro y extorsión", tags=["press"])
    bruit = make("p3", title="Football: PSG beat Marseille", tags=["press"])
    assert _st(ok) == ("ok", None)
    assert _st(ctx) == ("context", "arrestation ou suites")
    assert _st(bruit)[0] == "noise"


def test_avis_de_l_ia():
    e = make("a1", title="Seattle police chief resigns in wake of deadly food festival shooting: Mayor",
             tags=["press", "ai"])
    assert _st(e)[0] == "context"                     # ancienne fiche IA sans avis : règles par mots-clés
    e["physical"] = True
    assert _st(e) == ("ok", None)                      # l'IA a confirmé un fait physique
    e["physical"] = False
    assert _st(e) == ("context", "contexte (IA)")


def test_gdelt_en_attente_puis_verifie():
    g = make("g1", source="GDELT", title="Military force – Kyiv", category="armed_conflict", tags=["auto-detected"],
             lat=50.45, lon=30.52, country="UA")
    assert _st(g) == ("pending", "titre de l'article à lire")          # jamais sur la carte sans son article
    g["headline"] = "Megyn Kelly Melts Down at 'SVU' Star in Unhinged Rant"
    assert _st(g) == ("noise", "hors sujet")
    g["headline"] = "Russian attacks kill 6 in Ukraine and damage Kyiv's Northern Bridge"
    assert _st(g) == ("ok", None)
    g["headline"] = "Saudi Arabia rejects Houthi claim of attack on Riyadh"
    assert _st(g) == ("context", "déclaration")
    h = make("g2", source="GDELT", title="Military force – Kyiv", tags=["auto-detected"])
    h["headline_failed"] = True
    assert _st(h)[0] == "unverifiable"


def test_fiches_invalides():
    assert _st(make("x1", lat=0, lon=0))[0] == "invalid"
    assert _st(make("x2", lat=95, lon=10))[0] == "invalid"
    assert _st(make("x3", title="  "))[0] == "invalid"
    futur = (NOW + timedelta(days=3)).isoformat()
    assert _st(make("x4", date=futur)) == ("invalid", "date dans le futur")          # un attentat n'est pas annoncé
    assert _st(make("x5", source="GDACS", category="flood", date=futur))[0] == "ok"   # une alerte crue, si


def test_l_analyste_a_le_dernier_mot():
    ctx = make("p2", title="Detienen en Lerma a dos hombres y una menor por presunto secuestro y extorsión", tags=["press"])
    assert _st(ctx, {"p2": {"status": "verified"}}) == ("ok", "validé par l'analyste")
    usgs = make("u1", source="USGS", category="earthquake", title="M 6.1 – Chile")
    assert _st(usgs, {"u1": {"status": "false"}})[0] == "noise"


def test_controle_permanent_et_journal():
    old = make("p9", title="Detienen en Lerma a dos hombres y una menor por presunto secuestro y extorsión", tags=["press"])
    old["triage"] = {"status": "ok", "since": "2026-09-01T00:00:00+00:00"}   # entrée avant la v0.24
    real = make("p8", title="Ataque armado en Culiacán deja tres muertos", tags=["press"])
    counts = triage.check([old, real], NOW)
    assert counts == {"context": 1, "ok": 1} and triage.on_map([old, real]) == [real]
    assert old["triage"]["since"] == NOW.isoformat()                       # changement de verdict daté
    triage.check([real], NOW + timedelta(hours=1))
    assert real["triage"]["since"] == NOW.isoformat()                      # verdict inchangé : date d'origine gardée
    store = {"state": {}}
    triage.journal(store, NOW, counts, counts, [old, real], [])
    p = triage.payload(store)
    assert p["last"]["all"] == counts and [r["id"] for r in p["recent"]] == ["p9"]
    assert p["recent"][0]["reason"] == "arrestation ou suites"


def test_alarme_source_presque_entierement_refusee():
    evs = [make(f"g{i}", source="GDELT", tags=["auto-detected"]) for i in range(25)]
    for e in evs:
        e["headline"] = "Megyn Kelly Melts Down at 'SVU' Star"
    triage.check(evs, NOW)
    assert triage.alarms(evs) == ["GDELT : 25/25 nouveautés refusées"]
    assert triage.alarms(evs[:5]) == []                                    # trop peu pour conclure


def test_titres_gdelt_les_plus_recents_d_abord(monkeypatch):
    calls = []
    monkeypatch.setattr(enrich, "_fetch_title", lambda u: calls.append(u) or ("" if "bad" in u else "Titre réel de l'article"))
    a = make("a", source="GDELT", date="2026-10-01T00:00:00+00:00")
    b = make("b", source="GDELT", date="2026-10-05T00:00:00+00:00")
    c = make("c", source="GDELT", date="2026-10-04T00:00:00+00:00")
    c["sources"] = [{"name": "x", "url": "https://bad.example/1"}]
    cache = {}
    assert enrich.add_headlines([a, b, c], cache, lambda m: None, max_fetch=2) == 2
    assert b.get("headline") and c.get("headline_failed") and not a.get("headline")   # a : au prochain tour
    assert enrich.add_headlines([a], cache, lambda m: None, max_fetch=2) == 1 and a.get("headline")
