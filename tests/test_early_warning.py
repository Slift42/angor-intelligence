"""Alerte précoce mondiale par subdivision (v0.27) : régions communes avec les tendances, mémoire compacte,
comptages par famille de facteurs, indice à cinq composantes, sorties par région, liens avec les tendances."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from veille import early_warning as ew
from veille import foresight

NOW = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
SQUARE = [[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]]


def unit(uid, iso, x0, y0, size=1.0, name=None):
    g = [[[[x0, y0], [x0 + size, y0], [x0 + size, y0 + size], [x0, y0 + size], [x0, y0]]]]
    return {"id": uid, "iso": iso, "n": name or uid, "code": "", "g": g, "c": [y0 + size / 2, x0 + size / 2],
            "bb": [x0, y0, x0 + size, y0 + size]}


@pytest.fixture
def tmp_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(ew, "CACHE", tmp_path / "early_warning.json")
    monkeypatch.setattr(ew, "UNITS_DIR", tmp_path / "ew_units")
    monkeypatch.setattr(ew, "HISTORY_PARTS", tmp_path / "history_parts")
    monkeypatch.setattr(ew, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr("veille.publish.OUT_DIR", tmp_path / "out")
    return tmp_path


def test_regions_communes_couvrent_le_monde():
    regs = foresight.regions()
    assert len(regs) == 17 and {"weu", "wafr", "eafr", "mena", "nam", "oce"} <= set(regs)
    text = open("docs/data/countries.js", encoding="utf-8").read()
    isos = {f["properties"]["iso2"] for f in json.loads(text[text.index("=") + 1:].rstrip().rstrip(";"))["features"]}
    seen = [c for r in regs.values() for c in r["countries"]]
    assert len(seen) == len(set(seen))                                   # aucun pays dans deux régions
    assert isos - set(seen) == {"AQ", "GS", "HM", "IO", "TF"}            # seuls les territoires inhabités sont hors champ
    # les anciennes zones de l'alerte précoce sont entièrement reprises
    assert {"DJ", "ER", "ET", "KE", "SO", "SS", "SD", "UG"} <= set(regs["eafr"]["countries"])
    assert {"ML", "BF", "NE", "TD", "MR", "NG"} <= set(regs["wafr"]["countries"]) and "CM" in regs["cafr"]["countries"]


def test_outre_mer_rattache_a_sa_region_geographique():
    regs = foresight.regions()
    iso_reg = {iso: rid for rid, r in regs.items() for iso in r["countries"]}
    paris = {"iso": "FR", "c": [48.8, 2.3]}
    guadeloupe = {"iso": "FR", "c": [16.2, -61.5]}
    reunion = {"iso": "FR", "c": [-21.1, 55.5]}
    assert ew.unit_region(paris, iso_reg, regs) == "weu"
    assert ew.unit_region(guadeloupe, iso_reg, regs) == "cam"
    assert ew.unit_region(reunion, iso_reg, regs) == "safr"


def test_climat_compact_et_migration():
    old = {"fetched": "2026-10-01T00:00:00+00:00", "data": {"P": {"2025-09": 10.0, "2026-09": 4.0, "2011-09": 12.0},
                                                             "T": {"2026-09": 30.0}, "W": {}}}
    c = ew.migrate_climate(old)
    assert c["y0"] == 2011 and c["P"][ew._month_index(c, "2026-09")] == 4.0
    st = ew.climate_stats(c, "P", ["2026-09"])
    assert st["v"] == [4.0] and st["avg"] == [11.0] and st["min"] == [10.0] and st["max"] == [12.0]
    assert ew.last_month(c) == "2026-09"


def test_score_cinq_composantes():
    s = {"all": [0] * 12 + [5, 5, 5], "res": [0] * 12 + [1, 0, 0], "so": [0] * 12 + [2, 2, 1], "pol": [0] * 12 + [0, 0, 1],
         "hz": [0] * 15, "haz": [0] * 15, "infra": [0] * 15, "health": [0] * 15}
    sc = ew.score_unit({}, s, {}, has_hum=False)
    assert sc["c"]["co"] == 12 + 7 + 4 and sc["c"]["so"] == 4 + 6 + 3 and sc["c"]["hu"] == 0
    assert sc["v"] == round((23 + 13) * 100 / 85)                         # sans humanitaire : ramené sur 100
    keys = [d[0] for d in sc["dr"]]
    assert {"conflict_new", "incidents", "resource", "unrest_up", "political"} <= set(keys)
    with_hum = ew.score_unit({}, s, {"ipc3": 0.45, "idp": 50000, "pop": 400000}, has_hum=True)
    assert with_hum["c"]["hu"] == 9 + 6 and with_hum["v"] == 23 + 13 + 15


def test_comptage_par_famille(tmp_paths):
    units = {"FR-a": unit("FR-a", "FR", 0, 45), "FR-b": unit("FR-b", "FR", 2, 45)}
    cache = {"live_start": "2026-01"}

    def ev(i, cat, x, sev=2, title="x", days=3):
        return {"id": f"e{i}", "category": cat, "country": "FR", "lat": 45.5, "lon": x, "severity": sev,
                "date": (NOW - timedelta(days=days)).isoformat(), "title": title}
    events = [ev(1, "unrest", 0.5), ev(2, "terrorism", 0.5), ev(3, "crime", 0.5, title="vol de bétail : des éleveurs attaqués"),
              ev(4, "earthquake", 0.5, sev=1), ev(5, "flood", 2.5), ev(6, "cyber", 2.5), ev(7, "political", 2.5),
              ev(8, "unrest", 9.0)]                                                # hors de toute subdivision
    assert ew.update_security(units, cache, events, NOW, print) == 6
    row_a = cache["security"]["2026-10"]["FR-a"]
    row_b = cache["security"]["2026-10"]["FR-b"]
    assert row_a == [2, 1, 1, 0, 0, 0, 0]          # séisme de gravité 1 non compté
    assert row_b == [0, 0, 0, 1, 1, 1, 0]
    assert ew.update_security(units, cache, events, NOW, print) == 0                # déjà comptés


def test_migration_v2_et_sorties_par_region(tmp_paths):
    v2 = {"units": {"ML-bamako": dict(unit("ML-bamako", "ML", -8, 12), reg="sahel"),
                    "FR-ile-de-france": dict(unit("FR-ile-de-france", "FR", 2, 48), reg=None)},
          "climate": {"ML-bamako": {"fetched": NOW.isoformat(), "data": {"P": {"2026-09": 100.0}}}},
          "security": {"2026-09": {"ML-bamako": [3, 1]}}, "security_seen": {"2026-09": ["x"]}, "humanitarian": {}}
    ew.CACHE.write_text(json.dumps(v2), encoding="utf-8")
    cache = ew.load_cache()
    assert cache["v"] == ew.CACHE_VERSION and "security" not in cache and cache["climate"]["ML-bamako"]["y0"] == 2026
    regs = foresight.regions()
    units, pending = ew.load_units({}, regs, cache, print, 0.015, 0, NOW)
    assert (ew.UNITS_DIR / "ML.json").exists() and units["ML-bamako"]["reg"] == "wafr" and units["FR-ile-de-france"]["reg"] == "weu"
    events = [{"id": f"m{i}", "category": "attack", "country": "ML", "lat": 12.5, "lon": -7.5, "severity": 3,
               "date": (NOW - timedelta(days=2 + i)).isoformat(), "title": "attaque"} for i in range(4)]
    ew.update_security(units, cache, events, NOW, print)
    out = ew.build(units, cache, regs, NOW, pending)
    idx = out["index"]
    assert set(idx["regions"]) == set(regs) and idx["regions"]["wafr"]["n"] == 1
    assert idx["regions"]["wafr"]["top"][0][0] == "ML-bamako"
    text = (ew.OUT_DIR / "early_warning" / "wafr.js").read_text(encoding="utf-8")
    assert text.startswith("window.VS_EW_R = window.VS_EW_R || {};")
    data = json.loads(text.split("] = ", 1)[1].rstrip().rstrip(";"))
    u = data["units"][0]
    assert u["score"]["c"]["co"] > 0 and u["sec"]["all"][-1] == 4 and len(u["sec"]["all"]) == 15
    # lien avec les tendances : une tendance « sécurité » du Mali pointerait vers Bamako
    summ = next(x for x in out["units"] if x["id"] == "ML-bamako")
    assert summ["reg"] == "wafr" and summ["c"]["co"] > 0


def test_nouveaux_pays_par_priorite(tmp_paths, monkeypatch):
    calls = []

    def fake(iso, iso3, tol):
        calls.append(iso)
        return [unit(f"{iso}-x", iso, 0, 0)]
    monkeypatch.setattr(ew, "fetch_country_units", fake)

    class C:
        items = []

        def get(self, iso):
            return {"iso2": iso, "iso3": iso + "X"}
    regs = {"a": {"fr": "A", "en": "A", "countries": ["AA", "AB"], "bbox": [-10, -10, 10, 10]},
            "b": {"fr": "B", "en": "B", "countries": ["BA"], "bbox": [-10, -10, 10, 10]}}
    events = [{"category": "attack", "country": "AB"}] * 3
    units, pending = ew.load_units(C(), regs, {}, print, 0.015, 2, NOW, ["a", "b"], events)
    assert calls == ["AB", "AA"] and pending == ["BA"]
    units, pending = ew.load_units(C(), regs, {}, print, 0.015, 2, NOW, ["a", "b"], events)
    assert calls == ["AB", "AA", "BA"] and pending == []


def test_tendances_reliees_aux_subdivisions():
    cfg = foresight.load()
    units = [{"id": "FR-ile-de-france", "iso": "FR", "n": "Île-de-France", "reg": "weu", "v": 40, "lvl": 3, "ok": True,
              "c": {"cl": 2, "co": 12, "so": 13, "hz": 3, "hu": 0}},
             {"id": "FR-occitanie", "iso": "FR", "n": "Occitanie", "reg": "weu", "v": 30, "lvl": 2, "ok": True,
              "c": {"cl": 20, "co": 3, "so": 2, "hz": 5, "hu": 0}},
             {"id": "DE-berlin", "iso": "DE", "n": "Berlin", "reg": "weu", "v": 10, "lvl": 1, "ok": True,
              "c": {"cl": 0, "co": 4, "so": 2, "hz": 0, "hu": 0}}]
    ind = {"FR": {"imf": {"debt": {"2026": 116.0}}, "flags": ["heavy_debt"]}}
    p = foresight.build(cfg, [], NOW, ew={"units": units}, ind=ind)
    t = {x["id"]: x for x in p["trends"]}
    assert t["fr-heat"]["units"]["comp"] == "cl" and t["fr-heat"]["units"]["top"][0][0] == "FR-occitanie"
    assert t["fr-social"]["units"]["top"][0][0] == "FR-ile-de-france"
    assert "units" not in t["fr-failures"]                                # économie : pas de composante locale
    assert t["weu-terror"]["units"]["top"][0][0] == "FR-ile-de-france"    # région : toutes ses subdivisions
    assert p["scopes"]["FR"]["ew"]["high"] == 1 and p["scopes"]["weu"]["ew"]["n"] == 3
    assert p["scopes"]["FR"]["ind"]["flags"] == ["heavy_debt"] and "ind" not in p["scopes"]["DE"]
