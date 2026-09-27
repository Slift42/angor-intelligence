"""Département d'État américain – Travel Advisories (niveaux 1 à 4, domaine public).
https://cadataapi.state.gov"""
import re

from .. import http

KIND = "advisories"
URL = "https://cadataapi.state.gov/api/TravelAdvisories"
# Territoires sans polygone propre dans Natural Earth : leur avis ne doit pas écraser celui du pays
IGNORE = {"guadeloupe", "martinique", "french guiana", "french west indies", "bonaire", "saba",
          "sint eustatius", "reunion", "mayotte", "saint martin", "saint barthelemy"}
TITLE_RE = re.compile(r"^(.*?)\s*(?:Travel Advisory)?\s*[-–]\s*Level\s*(\d)\s*:?\s*(.*)$", re.I)


def fetch(cfg, ctx):
    data = http.get_json(cfg.get("url", URL))
    out, unmatched = {}, []
    for it in data if isinstance(data, list) else data.get("value", []):
        m = TITLE_RE.match((it.get("Title") or "").strip())
        if not m:
            continue
        name, level, label = m.group(1).strip(), int(m.group(2)), m.group(3).strip()
        if name.lower() in IGNORE:
            continue
        item = ctx.countries.by_country_name(name)
        if not item:
            for code in it.get("Category") or []:
                item = ctx.countries.by_fips.get(code) or ctx.countries.by_iso2.get(code)
                if item:
                    break
        if not item:
            unmatched.append(name)
            continue
        out[item["iso2"]] = {"level": level, "scale": 4, "label": label,
                             "url": it.get("Link") or "https://travel.state.gov",
                             "updated": it.get("Updated") or it.get("Published")}
    if unmatched:
        ctx.log(f"  US : {len(unmatched)} pays non rapprochés : {', '.join(unmatched[:10])}")
    return out
