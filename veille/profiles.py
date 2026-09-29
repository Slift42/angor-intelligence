"""Profils pays (intelligence économique et contexte), actualisés une fois par semaine.

Sources, toutes gratuites et sans clé :
- Banque mondiale – indicateurs (population, PIB, croissance, inflation, IDE, homicides…) et
  indicateurs de gouvernance WGI (corruption, État de droit, stabilité politique, qualité de la
  réglementation…) – licence CC BY 4.0
- FMI – World Economic Outlook (prévisions de croissance et d'inflation)
- REST Countries (capitale, langues, monnaies, frontières)
- Banque mondiale – projets actifs (marchés financés par bailleurs = pistes business)
- CIA World Factbook (archive 2026, domaine public) : fourni séparément dans docs/data/factbook.js
Résultat : docs/data/profiles.js
"""
import json
import time

from . import http
from .config import ROOT

OUT = ROOT / "docs" / "data" / "profiles.js"
WB = "https://api.worldbank.org/v2/country/all/indicator/{ind}?format=json&per_page=20000&mrnev=1{src}"
INDICATORS = {
    "population": "SP.POP.TOTL", "gdp_usd": "NY.GDP.MKTP.CD", "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    "gdp_per_capita": "NY.GDP.PCAP.CD", "inflation": "FP.CPI.TOTL.ZG", "unemployment": "SL.UEM.TOTL.ZS",
    "fdi_inflows_pct_gdp": "BX.KLT.DINV.WD.GD.ZS", "trade_pct_gdp": "NE.TRD.GNFS.ZS",
    "homicide_rate": "VC.IHR.PSRC.P5", "internet_users": "IT.NET.USER.ZS", "urban_pct": "SP.URB.TOTL.IN.ZS",
    "military_pct_gdp": "MS.MIL.XPND.GD.ZS", "days_to_start_business": "IC.REG.DURS",
    "total_tax_rate": "IC.TAX.TOTL.CP.ZS", "refugees_origin": "SM.POP.REFG.OR",
    "mobile_subs": "IT.CEL.SETS.P2", "broadband_subs": "IT.NET.BBND.P2", "electricity_access": "EG.ELC.ACCS.ZS",
}
WGI = {  # scores de gouvernance 0 (pire) à 100 (meilleur) – édition WGI révisée
    "wgi_corruption": "GOV_WGI_CC.SC", "wgi_rule_of_law": "GOV_WGI_RL.SC", "wgi_stability": "GOV_WGI_PV.SC",
    "wgi_government": "GOV_WGI_GE.SC", "wgi_regulation": "GOV_WGI_RQ.SC", "wgi_voice": "GOV_WGI_VA.SC",
}
SECTORS = {  # secteur déduit du nom du projet
    "Energy": ["energy", "electric", "power", "solar", "hydro", "grid", "renewable", "gas"],
    "Water & sanitation": ["water", "sanitation", "irrigation", "drainage"],
    "Transport": ["transport", "road", "rail", "port", "corridor", "airport", "highway", "mobility"],
    "Health": ["health", "hospital", "nutrition", "pandemic", "disease"],
    "Education & skills": ["education", "school", "skills", "learning", "university", "training"],
    "Agriculture & food": ["agri", "food", "livestock", "fisher", "rural"],
    "Digital": ["digital", "broadband", "ict", "data"],
    "Finance & private sector": ["finance", "financial", "investment", "private sector", "sme", "trade", "competitiveness"],
    "Urban & housing": ["urban", "city", "cities", "housing", "municipal"],
    "Climate & resilience": ["climate", "resilien", "disaster", "flood", "landscape", "forest"],
    "Social protection": ["social", "safety net", "cash transfer", "jobs", "employment"],
    "Governance & public sector": ["governance", "public sector", "fiscal", "revenue", "procurement", "statistic", "reform"],
}
IMF = {"imf_growth": "NGDP_RPCH", "imf_inflation": "PCPIPCH"}
PROJECTS = ("https://search.worldbank.org/api/v2/projects?format=json&fl=id,project_name,countrycode,"
            "totalamt,boardapprovaldate,url&status_exact=Active&rows=500&os={os}")

# Exposition indicative aux régimes de sanctions (UE / États-Unis). À vérifier au cas par cas :
# ces régimes évoluent souvent (ex. levée partielle des sanctions sur la Syrie en 2025).
SANCTIONS = {
    "RU": "extensive", "BY": "extensive", "IR": "extensive", "KP": "extensive", "CU": "extensive_us",
    "SY": "partially_lifted", "VE": "sectoral", "MM": "targeted", "AF": "targeted", "LY": "targeted",
    "SD": "targeted", "SS": "targeted", "SO": "targeted", "YE": "targeted", "CF": "targeted", "CD": "targeted",
    "ML": "targeted", "IQ": "targeted", "LB": "targeted", "NI": "targeted", "HT": "targeted", "ZW": "targeted",
    "GN": "targeted", "GW": "targeted", "BI": "targeted", "NE": "targeted", "MD": "targeted", "TR": "targeted",
    "CN": "targeted", "BA": "targeted",
}


def _wb(ind, countries, log, source=""):
    try:
        data = http.get_json(WB.format(ind=ind, src=source), timeout=60)
    except Exception as exc:
        log(f"  Banque mondiale {ind} : {exc}")
        return {}
    out = {}
    for row in (data[1] if isinstance(data, list) and len(data) > 1 and data[1] else []):
        item = countries.by_iso3.get(row.get("countryiso3code") or "")
        if item and row.get("value") is not None:
            out[item["iso2"]] = {"value": row["value"], "year": row.get("date")}
    return out


def _imf(code, countries, log, years):
    try:
        data = http.get_json(f"https://www.imf.org/external/datamapper/api/v1/{code}?periods={','.join(years)}", timeout=60)
    except Exception as exc:
        log(f"  FMI {code} : {exc}")
        return {}
    out = {}
    for iso3, vals in (data.get("values", {}).get(code, {}) or {}).items():
        item = countries.by_iso3.get(iso3)
        if item:
            out[item["iso2"]] = {y: v for y, v in vals.items() if v is not None and y in years}
    return out


def _restcountries(countries, log):
    try:
        data = http.get_json("https://restcountries.com/v3.1/all?fields=cca2,capital,languages,currencies,"
                             "region,subregion,area,borders,timezones,landlocked", timeout=60)
    except Exception as exc:
        log(f"  REST Countries : {exc}")
        return {}
    out = {}
    for c in data:
        out[c.get("cca2")] = {
            "capital": ", ".join(c.get("capital") or []),
            "languages": list((c.get("languages") or {}).values()),
            "currencies": [f"{v.get('name')} ({k})" for k, v in (c.get("currencies") or {}).items()],
            "area_km2": c.get("area"), "borders": c.get("borders") or [], "landlocked": c.get("landlocked"),
            "timezones": c.get("timezones") or [],
        }
    return out


def _projects(countries, log):
    out = {}
    for page in range(12):
        try:
            data = http.get_json(PROJECTS.format(os=page * 500), timeout=60)
        except Exception as exc:
            log(f"  Projets Banque mondiale : {exc}")
            break
        projects = data.get("projects") or {}
        if not projects:
            break
        for p in projects.values():
            codes = p.get("countrycode")
            code = codes[0] if isinstance(codes, list) and codes else codes
            if not code or not countries.get(code):
                continue
            amt = p.get("totalamt")
            try:
                amt = float(str(amt).replace(",", "")) if amt else 0.0
            except ValueError:
                amt = 0.0
            name = p.get("project_name")
            name = name if isinstance(name, str) else (name or [""])[0] if isinstance(name, list) else ""
            low = name.lower()
            sector = next((k for k, words in SECTORS.items() if any(w in low for w in words)), "Other")
            c = out.setdefault(code, {"count": 0, "total_usd": 0.0, "sectors": {}, "top": []})
            c["count"] += 1
            c["total_usd"] += amt
            if sector:
                c["sectors"][sector] = c["sectors"].get(sector, 0) + amt
            c["top"].append({"name": name, "amount_usd": amt, "sector": sector or "",
                             "url": p.get("url") or f"https://projects.worldbank.org/en/projects-operations/project-detail/{p.get('id')}",
                             "approved": (p.get("boardapprovaldate") or "")[:10]})
        time.sleep(0.5)
    for c in out.values():
        c["top"] = sorted(c["top"], key=lambda x: -x["amount_usd"])[:6]
        c["sectors"] = dict(sorted(c["sectors"].items(), key=lambda kv: -kv[1])[:6])
    return out


def build(countries, log, now):
    log("Profils pays : mise à jour hebdomadaire (Banque mondiale, FMI, REST Countries)…")
    previous = load()
    prof = {}

    def step(name, fn):
        """Chaque source est indépendante : une panne n'empêche pas les autres."""
        try:
            fn()
        except Exception as exc:
            log(f"  Profils – {name} : {type(exc).__name__}: {str(exc)[:150]}")

    def wdi():
        for key, ind in INDICATORS.items():
            for iso, v in _wb(ind, countries, log).items():
                prof.setdefault(iso, {})[key] = v

    def wgi():
        for key, ind in WGI.items():
            for iso, v in _wb(ind, countries, log, source="&source=3").items():
                prof.setdefault(iso, {})[key] = v

    def imf():
        years = [str(now.year - 1), str(now.year), str(now.year + 1)]
        for key, code in IMF.items():
            for iso, v in _imf(code, countries, log, years).items():
                prof.setdefault(iso, {})[key] = v

    def basics():
        for iso, v in _restcountries(countries, log).items():
            if iso:
                prof.setdefault(iso, {})["basics"] = v

    def projects():
        for iso, v in _projects(countries, log).items():
            prof.setdefault(iso, {})["wb_projects"] = v

    for name, fn in (("Banque mondiale", wdi), ("gouvernance WGI", wgi), ("FMI", imf),
                     ("REST Countries", basics), ("projets Banque mondiale", projects)):
        step(name, fn)
    for iso, s in SANCTIONS.items():
        prof.setdefault(iso, {})["sanctions"] = s
    # une source en panne : on garde l'ancienne valeur
    for iso, old in (previous.get("countries") or {}).items():
        for k, v in old.items():
            prof.setdefault(iso, {}).setdefault(k, v)
    payload = {"updated": now.replace(microsecond=0).isoformat(), "countries": prof}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("window.VS_PROFILES = ")
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    log(f"  {len(prof)} profils pays écrits")
    return payload


def load():
    if not OUT.exists():
        return {}
    text = OUT.read_text(encoding="utf-8")
    try:
        return json.loads(text[text.index("{"): text.rstrip().rstrip(";").rindex("}") + 1])
    except ValueError:
        return {}


def is_stale(now, days=7):
    from .model import parse_iso
    p = load()
    return not p.get("updated") or (now - parse_iso(p["updated"])).days >= days
