"""CISA KEV – catalogue des vulnérabilités activement exploitées (agence cyber américaine, domaine public).

https://www.cisa.gov/known-exploited-vulnerabilities-catalog
Chaque vulnérabilité ajoutée récemment rejoint le « Fil » (catégorie cyber) : éditeur, produit, CVE,
exploitation par rançongiciel connue ou non. Pas de position sur la carte (menace sans lieu).
"""
from datetime import datetime, timedelta, timezone

from .. import http
from ..model import to_iso

KIND = "events"
URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


def fetch(cfg, ctx):
    data = http.get_json(URL, timeout=60)
    since = (ctx.now - timedelta(days=int(cfg.get("max_age_days", 3)))).date()
    n = 0
    for v in data.get("vulnerabilities") or []:
        try:
            added = datetime.strptime(v.get("dateAdded", ""), "%Y-%m-%d").date()
        except ValueError:
            continue
        if added < since:
            continue
        cve = v.get("cveID", "")
        ransom = (v.get("knownRansomwareCampaignUse") or "").lower() == "known"
        title = f"{cve} – {v.get('vendorProject', '')} {v.get('product', '')} : {v.get('vulnerabilityName', '')}".strip()
        ctx.news.append({
            "id": f"kev-{cve}", "source": "CISA KEV", "title": ("[Rançongiciel] " if ransom else "") + title,
            "url": f"https://nvd.nist.gov/vuln/detail/{cve}",
            "date": to_iso(datetime(added.year, added.month, added.day, 12, tzinfo=timezone.utc)),
            "lang": "en", "country": None, "category": "cyber", "severity": 3 if ransom else 2,
            "summary_en": (v.get("shortDescription") or "")[:400],
        })
        n += 1
    ctx.log(f"  CISA KEV : {n} vulnérabilité(s) exploitée(s) ajoutée(s) récemment")
    return []
