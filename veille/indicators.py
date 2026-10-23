"""Indicateurs structurels par pays (v0.27), pour les fiches pays des tendances de risques.

Sources publiques, sans clé, interrogées une fois par semaine (au plus) et gardées dans data/indicators.json :
- FMI, World Economic Outlook via l'API DataMapper : croissance du PIB réel, inflation, dette publique (% du PIB),
  chômage – année en cours et suivante (projections) ;
- Banque mondiale, Worldwide Governance Indicators (source 3 de l'API) : stabilité politique et absence de violence,
  efficacité des pouvoirs publics, État de droit, maîtrise de la corruption (scores de 0 à 100) ;
- BCE, taux d'intérêt à long terme de convergence (jeu IRS, 10 ans, pays de l'UE) : rendement souverain et écart avec
  l'Allemagne.
Chaque pays reçoit des « signaux structurels » quand un seuil est franchi (récession, inflation forte, dette lourde,
chômage élevé, forte instabilité, écart de taux tendu). Ils éclairent les tendances économiques, financières et
politiques ; ils ne remplacent pas l'analyse.
"""
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from . import http

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "indicators.json"
IMF_URL = "https://www.imf.org/external/datamapper/api/v1/{code}"
IMF = {"growth": "NGDP_RPCH", "inflation": "PCPIPCH", "debt": "GGXWDG_NGDP", "unemployment": "LUR"}
WB_URL = "https://api.worldbank.org/v2/country/all/indicator/{code}"
WGI = {"stability": "GOV_WGI_PV.SC", "effectiveness": "GOV_WGI_GE.SC", "rule_of_law": "GOV_WGI_RL.SC",
       "corruption": "GOV_WGI_CC.SC"}
ECB_URL = "https://data-api.ecb.europa.eu/service/data/IRS/M..L.L40.CI.0000.EUR.N.Z"
REFRESH_DAYS = {"imf": 7, "wgi": 30, "ecb": 3}
# seuils des signaux structurels : (clé, test, libellé de l'indicateur)
FLAGS = {"recession": lambda r: _imf(r, "growth") is not None and _imf(r, "growth") < 0,
         "high_inflation": lambda r: _imf(r, "inflation") is not None and _imf(r, "inflation") >= 10,
         "heavy_debt": lambda r: _imf(r, "debt") is not None and _imf(r, "debt") >= 100,
         "high_unemployment": lambda r: _imf(r, "unemployment") is not None and _imf(r, "unemployment") >= 15,
         "unstable": lambda r: (r.get("wgi") or {}).get("stability") is not None and r["wgi"]["stability"][0] < 20,
         "spread": lambda r: r.get("spread") is not None and r["spread"] >= 150}
SOURCES = {"imf": "imf_datamapper", "wgi": "wgi", "ecb": "ecb_irs"}  # identifiants de config/foresight/sources.json


def _imf(rec, key):
    """Valeur FMI de l'année en cours (projection), sinon de la plus récente disponible."""
    vals = (rec.get("imf") or {}).get(key) or {}
    year = str(datetime.now(timezone.utc).year)
    if year in vals:
        return vals[year]
    return vals[max(vals)] if vals else None


def parse_imf(data, code, iso3_to_iso2, years):
    out = {}
    for iso3, series in ((data.get("values") or {}).get(code) or {}).items():
        iso2 = iso3_to_iso2.get(iso3)
        if not iso2 or not isinstance(series, dict):
            continue
        vals = {y: round(float(series[y]), 1) for y in years if series.get(y) is not None}
        if vals:
            out[iso2] = vals
    return out


def parse_wgi(data, iso3_to_iso2):
    """Réponse de l'API Banque mondiale : [métadonnées, [lignes]] → {iso2: [score, année]}."""
    rows = data[1] if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list) else []
    out = {}
    for r in rows:
        iso2 = iso3_to_iso2.get(r.get("countryiso3code") or "")
        if iso2 and r.get("value") is not None:
            if iso2 not in out or str(r.get("date")) > out[iso2][1]:
                out[iso2] = [round(float(r["value"]), 1), str(r.get("date"))]
    return out


def parse_ecb(text):
    """CSV SDMX de la BCE → {iso2: [taux, mois]} (dernière observation de chaque pays)."""
    out = {}
    for r in csv.DictReader(io.StringIO(text)):
        area, period, value = r.get("REF_AREA"), r.get("TIME_PERIOD"), r.get("OBS_VALUE")
        if not area or not period or value in (None, ""):
            continue
        if area not in out or period > out[area][1]:
            out[area] = [round(float(value), 2), period]
    return out


def _due(cache, key, now):
    last = (cache.get("fetched") or {}).get(key)
    return not last or (now - datetime.fromisoformat(last)).days >= REFRESH_DAYS[key]


def load_cache():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def update(countries, log, now=None):
    """Met à jour ce qui est dû (FMI, Banque mondiale, BCE) et renvoie {iso2: indicateurs + signaux}."""
    now = now or datetime.now(timezone.utc)
    cache = load_cache()
    fetched = cache.setdefault("fetched", {})
    iso3_to_iso2 = {it["iso3"]: it["iso2"] for it in getattr(countries, "items", []) if it.get("iso3")}
    years = [str(now.year - 1), str(now.year), str(now.year + 1)]
    if _due(cache, "imf", now):
        try:
            imf = {}
            for key, code in IMF.items():
                imf[key] = parse_imf(http.get_json(IMF_URL.format(code=code), timeout=60, retries=1), code, iso3_to_iso2, years)
            cache["imf"] = imf
            fetched["imf"] = now.isoformat()
            log(f"  Indicateurs : FMI mis à jour ({len(imf.get('growth') or {})} pays)")
        except Exception as exc:
            log(f"  Indicateurs : FMI indisponible ({type(exc).__name__})")
    if _due(cache, "wgi", now):
        try:
            wgi = {}
            for key, code in WGI.items():
                data = http.get_json(WB_URL.format(code=code), params={"format": "json", "source": 3, "mrv": 1, "per_page": 500},
                                     timeout=60, retries=1)
                wgi[key] = parse_wgi(data, iso3_to_iso2)
            cache["wgi"] = wgi
            fetched["wgi"] = now.isoformat()
            log(f"  Indicateurs : Banque mondiale (gouvernance) mise à jour ({len(wgi.get('stability') or {})} pays)")
        except Exception as exc:
            log(f"  Indicateurs : Banque mondiale indisponible ({type(exc).__name__})")
    if _due(cache, "ecb", now):
        try:
            text = http.get(ECB_URL, params={"format": "csvdata", "lastNObservations": 1}, timeout=60, retries=1).text
            ecb = parse_ecb(text)
            if ecb:
                cache["ecb"] = ecb
                fetched["ecb"] = now.isoformat()
                log(f"  Indicateurs : taux souverains BCE mis à jour ({len(ecb)} pays)")
        except Exception as exc:
            log(f"  Indicateurs : BCE indisponible ({type(exc).__name__})")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return assemble(cache)


def assemble(cache):
    out = {}
    for key, by_iso in (cache.get("imf") or {}).items():
        for iso, vals in by_iso.items():
            out.setdefault(iso, {}).setdefault("imf", {})[key] = vals
    for key, by_iso in (cache.get("wgi") or {}).items():
        for iso, val in by_iso.items():
            out.setdefault(iso, {}).setdefault("wgi", {})[key] = val
    ecb = cache.get("ecb") or {}
    de = (ecb.get("DE") or [None])[0]
    for iso, (v, period) in ecb.items():
        rec = out.setdefault(iso, {})
        rec["yield"] = [v, period]
        if de is not None and iso != "DE":
            rec["spread"] = round((v - de) * 100)
    for iso, rec in out.items():
        rec["flags"] = [k for k, test in FLAGS.items() if test(rec)]
    return out
