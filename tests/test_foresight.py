"""Tendances de risques (v0.26) : configuration publiable, scores, contrôle qualité, signaux en temps réel."""
import copy
from datetime import datetime, timedelta, timezone

import pytest

from veille import foresight

NOW = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def cfg():
    return foresight.load()


def trend(cfg, tid):
    return next(t for s in cfg["scopes"].values() for t in s["trends"] if t["id"] == tid)


def test_configuration_publiable(cfg):
    assert foresight.validate(cfg, NOW) == []


def test_perimetres_europe_ouest_et_france(cfg):
    assert cfg["scopes"]["weu"]["type"] == "region"
    assert cfg["scopes"]["FR"]["parent"] == "weu"
    assert "FR" in cfg["scopes"]["weu"]["countries"]
    assert len(cfg["scopes"]["weu"]["trends"]) >= 10 and len(cfg["scopes"]["FR"]["trends"]) >= 10


def test_toutes_les_familles_sont_utilisees(cfg):
    fams = {t["family"] for s in cfg["scopes"].values() for t in s["trends"]} | \
           {f for s in cfg["scopes"].values() for t in s["trends"] for f in t.get("also", [])}
    assert set(cfg["method"]["families"]) - fams == set()


def test_score_et_niveaux(cfg):
    levels = cfg["method"]["scales"]["levels"]
    t = {"likelihood": 4, "impact": {"business": 4, "travel": 1}}
    assert foresight.score(t) == {"business": 16, "travel": 4, "all": 16}
    assert [foresight.level_of(v, levels) for v in (1, 4, 5, 9, 10, 14, 15, 19, 20, 25)] == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    # chaque case de la matrice 5 × 5 a un niveau
    assert {foresight.level_of(a * b, levels) for a in range(1, 6) for b in range(1, 6)} == {1, 2, 3, 4, 5}


def test_pression():
    assert foresight.pressure([25, 25, 25, 25, 25, 1]) == 100
    assert foresight.pressure([10, 5]) == 30
    assert foresight.pressure([]) == 0


def test_controle_sources(cfg):
    bad = copy.deepcopy(cfg)
    t = bad["scopes"]["FR"]["trends"][0]
    t["signals"] = [{"fr": "x", "en": "x", "src": ["lcp_plf27"], "d": "2026-10-12"}]
    errs = foresight.validate(bad, NOW)
    assert any("moins de 2 sources" in e for e in errs)
    t["signals"].append({"fr": "y", "en": "y", "src": ["assemblee"]})
    t["signals"].append({"fr": "z", "en": "z", "src": ["wiki_fuel", "straits_live", "gdelt"]})
    errs = foresight.validate(bad, NOW)
    assert any("faible cotation" in e for e in errs)


def test_controle_dates_et_echelles(cfg):
    bad = copy.deepcopy(cfg)
    t = bad["scopes"]["weu"]["trends"][0]
    t["signals"][0]["d"] = "2027-01-01"
    t["likelihood"] = 6
    t["horizon"] = "5y"
    t["links"] = ["inconnue"]
    t["live"] = ["meteor"]
    errs = foresight.validate(bad, NOW)
    for frag in ("dans le futur", "vraisemblance hors échelle", "horizon inconnu", "tendance inconnue", "catégorie d'incident inconnue"):
        assert any(frag in e for e in errs), frag


def test_independance_des_editeurs(cfg):
    bad = copy.deepcopy(cfg)
    t = bad["scopes"]["FR"]["trends"][0]
    t["signals"] = [{"fr": "a", "en": "a", "src": ["ecb_proj_sep26"]}, {"fr": "b", "en": "b", "src": ["ecb_fsr"]}]
    assert any("éditeurs indépendants" in e for e in foresight.validate(bad, NOW))


def _ev(cat, iso, days_ago):
    return {"category": cat, "country": iso, "date": (NOW - timedelta(days=days_ago)).isoformat()}


def test_signal_temps_reel(cfg):
    params = cfg["method"]["live"]
    t = {"live": ["unrest"]}
    calm = [_ev("unrest", "FR", d) for d in (40, 70, 100)]
    hot = calm + [_ev("unrest", "FR", d) for d in (1, 2, 3, 5, 8, 13)] + [_ev("unrest", "DE", 1), _ev("crime", "FR", 1)]
    s = foresight.live_signal(t, ["FR"], hot, NOW, params)
    assert s["n"] == 6 and s["base"] == 1.0 and s["dir"] == 1
    s = foresight.live_signal(t, ["FR"], calm, NOW, params)
    assert s["n"] == 0 and s["dir"] == 0          # trop peu d'incidents pour conclure à une baisse
    drop = [_ev("unrest", "FR", d) for d in range(31, 120, 6)]
    assert foresight.live_signal(t, ["FR"], drop, NOW, params)["dir"] == -1
    assert foresight.live_signal({"live": []}, ["FR"], hot, NOW, params) is None


def test_build_vues_pays_et_region(cfg):
    events = [_ev("unrest", "FR", d) for d in (1, 2, 3, 4, 5, 6)] + [_ev("unrest", "FR", 60)]
    p = foresight.build(cfg, events, NOW)
    assert p["trends"][0]["score"]["all"] >= p["trends"][-1]["score"]["all"]
    fr, de, weu = p["scopes"]["FR"], p["scopes"]["DE"], p["scopes"]["weu"]
    assert fr["described"] and not de["described"]
    assert fr["summary"]["n"] == len(cfg["scopes"]["FR"]["trends"]) + len(cfg["scopes"]["weu"]["trends"])
    assert de["summary"]["n"] == len(cfg["scopes"]["weu"]["trends"]) and de["summary"]["own"] == 0
    assert weu["summary"]["n"] == fr["summary"]["n"]
    assert 0 < fr["summary"]["pressure"] <= 100
    # surprise : troubles en forte hausse sur une tendance jugée stable → signalée
    t = next(t for t in p["trends"] if t["id"] == "fr-social")
    assert t["live"]["dir"] == 1 and "live_up" not in t["flags"]          # déjà jugée en hausse
    cfg2 = copy.deepcopy(cfg)
    trend(cfg2, "fr-social")["momentum"] = 0
    t = next(t for t in foresight.build(cfg2, events, NOW)["trends"] if t["id"] == "fr-social")
    assert "live_up" in t["flags"]
    # toutes les sources citées sont publiées
    cited = {k for t in p["trends"] for k in t["sources"]}
    assert cited <= set(p["sources"])


def test_revision_due(cfg):
    later = NOW + timedelta(days=45)
    p = foresight.build(cfg, [], later)
    due = {t["id"] for t in p["trends"] if "review_due" in t["flags"]}
    assert "fr-gov" in due            # horizon 3 mois : revue à 30 jours
    assert "weu-ageing" not in due    # structurel : revue à 120 jours


def test_historique_mensuel(cfg):
    store = {"state": {}}
    p = foresight.build(cfg, [], NOW)
    foresight.snapshot(store, p, NOW)
    foresight.snapshot(store, p, NOW + timedelta(days=31))
    hist = store["state"]["foresight"]["history"]
    assert sorted(hist) == ["2026-10", "2026-11"]
    p2 = foresight.build(cfg, [], NOW + timedelta(days=31), hist)
    assert len(p2["trends"][0]["history"]) == 2


def test_methode_publique_sans_tendances(cfg):
    p = foresight.build(cfg, [], NOW)
    pub = foresight.public_method(cfg, p)
    assert "trends" not in pub and pub["sources"] and pub["drivers"]
    assert {c["id"] for c in pub["coverage"]} == {"weu", "FR"}
    assert next(c for c in pub["coverage"] if c["id"] == "FR")["parent"] == "weu"
