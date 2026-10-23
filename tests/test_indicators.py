"""Indicateurs structurels par pays (v0.27) : lecture des réponses FMI, Banque mondiale et BCE, signaux de seuil."""
import json
from datetime import datetime, timezone

from veille import indicators


class FakeCountries:
    items = [{"iso2": "FR", "iso3": "FRA"}, {"iso2": "DE", "iso3": "DEU"}, {"iso2": "SD", "iso3": "SDN"}, {"iso2": "IT", "iso3": "ITA"}]


ISO3 = {it["iso3"]: it["iso2"] for it in FakeCountries.items}
YEAR = str(datetime.now(timezone.utc).year)


def test_lecture_fmi():
    data = {"values": {"NGDP_RPCH": {"SDN": {"2024": -19.3, YEAR: -2.0, "2031": 8}, "FRA": {YEAR: 0.6}, "XXX": {YEAR: 1}}}}
    out = indicators.parse_imf(data, "NGDP_RPCH", ISO3, [YEAR])
    assert out == {"SD": {YEAR: -2.0}, "FR": {YEAR: 0.6}}


def test_lecture_banque_mondiale():
    data = [{"page": 1, "pages": 1, "total": 3},
            [{"countryiso3code": "FRA", "date": "2025", "value": 61.37}, {"countryiso3code": "SDN", "date": "2025", "value": 1.4},
             {"countryiso3code": "", "date": "2025", "value": 50}, {"countryiso3code": "DEU", "date": "2025", "value": None}]]
    assert indicators.parse_wgi(data, ISO3) == {"FR": [61.4, "2025"], "SD": [1.4, "2025"]}
    assert indicators.parse_wgi([{"message": "erreur"}], ISO3) == {}


def test_lecture_bce():
    csv_text = ("KEY,FREQ,REF_AREA,TIME_PERIOD,OBS_VALUE\n"
                "IRS.M.FR.L.L40.CI.0000.EUR.N.Z,M,FR,2026-09,4.85\n"
                "IRS.M.FR.L.L40.CI.0000.EUR.N.Z,M,FR,2026-08,4.60\n"
                "IRS.M.DE.L.L40.CI.0000.EUR.N.Z,M,DE,2026-09,3.05\n"
                "IRS.M.IT.L.L40.CI.0000.EUR.N.Z,M,IT,2026-09,\n")
    assert indicators.parse_ecb(csv_text) == {"FR": [4.85, "2026-09"], "DE": [3.05, "2026-09"]}


def test_assemblage_et_signaux():
    cache = {"imf": {"growth": {"SD": {YEAR: -2.0}}, "inflation": {"SD": {YEAR: 87.0}}, "debt": {"FR": {YEAR: 117.0}}},
             "wgi": {"stability": {"SD": [1.4, "2025"], "FR": [52.0, "2025"]}},
             "ecb": {"FR": [4.85, "2026-09"], "DE": [3.05, "2026-09"]}}
    out = indicators.assemble(cache)
    assert set(out["SD"]["flags"]) == {"recession", "high_inflation", "unstable"}
    assert out["FR"]["spread"] == 180 and set(out["FR"]["flags"]) == {"heavy_debt", "spread"}
    assert "spread" not in out["DE"] and out["DE"]["flags"] == []


def test_mise_a_jour_hors_ligne(tmp_path, monkeypatch):
    """Sans réseau : la collecte continue, la mémoire précédente est conservée."""
    monkeypatch.setattr(indicators, "CACHE", tmp_path / "indicators.json")
    (tmp_path / "indicators.json").write_text(json.dumps({"imf": {"debt": {"FR": {YEAR: 117.0}}}, "fetched": {}}), encoding="utf-8")

    def boom(*a, **k):
        raise OSError("hors ligne")
    monkeypatch.setattr(indicators.http, "get_json", boom)
    monkeypatch.setattr(indicators.http, "get", boom)
    logs = []
    out = indicators.update(FakeCountries(), logs.append)
    assert out["FR"]["flags"] == ["heavy_debt"] and len(logs) == 3
