"""Agrégateur de rapports : docs/data/reports.js (onglet « Rapports » et fiche pays).

Les derniers rapports et analyses de fond sur les pays et les crises, publiés par des think tanks, organisations
internationales, ONG et cabinets (config/reports.json). Pour chaque publication : titre, organisation, date, lien et
résumé court fourni par l'éditeur dans son flux (300 caractères maximum) – jamais le texte du rapport.
Les pays, régions et thèmes sont détectés dans le titre et le résumé.
"""
import hashlib
import html
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from . import config, http
from .connectors.rss import TAG_RE, _items, parse_xml
from .geo import ALIASES, normalize
from .model import to_iso
from .publish import write_js

DEMONYMS = {
    "afghan": "AF", "algerian": "DZ", "angolan": "AO", "armenian": "AM", "azerbaijani": "AZ", "bangladeshi": "BD",
    "belarusian": "BY", "beninese": "BJ", "bolivian": "BO", "bosnian": "BA", "brazilian": "BR", "burkinabe": "BF",
    "burundian": "BI", "burmese": "MM", "cambodian": "KH", "cameroonian": "CM", "chadian": "TD", "chilean": "CL",
    "chinese": "CN", "colombian": "CO", "congolese": "CD", "cuban": "CU", "ecuadorian": "EC", "egyptian": "EG",
    "eritrean": "ER", "ethiopian": "ET", "french": "FR", "gabonese": "GA", "georgian": "GE", "german": "DE",
    "ghanaian": "GH", "guatemalan": "GT", "guinean": "GN", "haitian": "HT", "honduran": "HN", "indian": "IN",
    "indonesian": "ID", "iranian": "IR", "iraqi": "IQ", "israeli": "IL", "ivorian": "CI", "japanese": "JP",
    "jordanian": "JO", "kazakh": "KZ", "kenyan": "KE", "kosovar": "XK", "kurdish": "IQ", "kyrgyz": "KG",
    "lebanese": "LB", "liberian": "LR", "libyan": "LY", "malagasy": "MG", "malawian": "MW", "malian": "ML",
    "mauritanian": "MR", "mexican": "MX", "moldovan": "MD", "moroccan": "MA", "mozambican": "MZ", "nepali": "NP",
    "nicaraguan": "NI", "nigerien": "NE", "nigerian": "NG", "north korean": "KP", "pakistani": "PK",
    "palestinian": "PS", "peruvian": "PE", "philippine": "PH", "filipino": "PH", "russian": "RU", "rwandan": "RW",
    "salvadoran": "SV", "saudi": "SA", "senegalese": "SN", "serbian": "RS", "sierra leonean": "SL", "somali": "SO",
    "south african": "ZA", "south korean": "KR", "south sudanese": "SS", "sri lankan": "LK", "sudanese": "SD",
    "syrian": "SY", "taiwanese": "TW", "tajik": "TJ", "tanzanian": "TZ", "thai": "TH", "togolese": "TG",
    "tunisian": "TN", "turkish": "TR", "ugandan": "UG", "ukrainian": "UA", "uzbek": "UZ", "venezuelan": "VE",
    "vietnamese": "VN", "yemeni": "YE", "zambian": "ZM", "zimbabwean": "ZW",
    # français
    "malien": "ML", "malienne": "ML", "burkinabe": "BF", "nigerienne": "NE", "tchadien": "TD", "soudanais": "SD",
    "somalien": "SO", "ethiopien": "ET", "libyen": "LY", "syrien": "SY", "irakien": "IQ", "iranien": "IR",
    "israelien": "IL", "libanais": "LB", "yemenite": "YE", "afghan": "AF", "ukrainien": "UA", "russe": "RU",
    "chinois": "CN", "algerien": "DZ", "marocain": "MA", "tunisien": "TN", "congolais": "CD", "centrafricain": "CF",
    "camerounais": "CM", "senegalais": "SN", "ivoirien": "CI", "haitien": "HT", "venezuelien": "VE", "mexicain": "MX",
}
REGIONS = {
    "sahel": ["sahel", "liptako", "gourma"],
    "horn": ["horn of africa", "corne de l'afrique", "igad"],
    "great_lakes": ["great lakes", "grands lacs"],
    "west_africa": ["west africa", "afrique de l'ouest", "ecowas", "cedeao", "gulf of guinea", "golfe de guinee"],
    "central_africa": ["central africa", "afrique centrale", "lake chad", "lac tchad"],
    "north_africa": ["north africa", "maghreb", "afrique du nord"],
    "middle_east": ["middle east", "moyen-orient", "levant", "mena"],
    "gulf": ["gulf states", "persian gulf", "golfe persique", "gcc", "red sea", "mer rouge", "hormuz", "ormuz"],
    "balkans": ["balkans", "western balkans"],
    "caucasus": ["caucasus", "caucase"],
    "central_asia": ["central asia", "asie centrale"],
    "south_asia": ["south asia", "asie du sud"],
    "southeast_asia": ["southeast asia", "south-east asia", "asean", "asie du sud-est"],
    "indo_pacific": ["indo-pacific", "indo-pacifique", "pacific islands", "south china sea", "mer de chine"],
    "latin_america": ["latin america", "amerique latine", "central america", "amerique centrale", "caribbean",
                      "caraibes", "andes", "amazon"],
    "europe": ["europe", "european union", "union europeenne", "nato", "otan"],
    "arctic": ["arctic", "arctique"],
}
THEMES = {
    "conflict": ["war", "conflict", "armed", "military", "ceasefire", "offensive", "insurgen", "militia", "guerre",
                 "conflit", "militaire", "frappes", "strikes", "fighting", "security"],
    "terrorism": ["terror", "jihad", "islamic state", "isis", "al-qaeda", "al-shabaab", "jnim", "extremis"],
    "politics": ["election", "elections", "coup", "government", "parliament", "president", "democracy", "protest",
                 "electoral", "junta", "junte", "politique", "gouvernance", "governance", "transition"],
    "economy": ["econom", "inflation", "debt", "dette", "trade", "commerce", "imf", "fmi", "sanction", "tariff",
                "investment", "fiscal", "growth", "croissance", "market", "price"],
    "climate": ["climate", "climat", "drought", "secheresse", "flood", "inondation", "environment", "water", "eau"],
    "food": ["food", "famine", "hunger", "faim", "alimentaire", "ipc", "harvest", "crop", "agricultur"],
    "migration": ["migra", "refugee", "refugie", "displace", "deplace", "asylum", "smuggling"],
    "crime": ["crime", "criminal", "cartel", "gang", "trafficking", "trafic", "cocaine", "narco", "illicit"],
    "cyber": ["cyber", "hack", "ransomware", "disinformation", "desinformation", "artificial intelligence", " ai "],
    "energy": ["energy", "energie", "oil", "petrole", "gas", "gaz", "pipeline", "mining", "minerals", "critical minerals"],
    "maritime": ["maritime", "shipping", "piracy", "piraterie", "red sea", "strait", "navy", "naval", "port"],
    "health": ["health", "sante", "epidemic", "outbreak", "cholera", "ebola", "mpox", "disease"],
    "rights": ["human rights", "droits humains", "droits de l'homme", "abuses", "war crimes", "torture", "repression"],
    "diplomacy": ["diplomac", "diplomat", "negotiation", "talks", "summit", "sommet", "peace process", "accord"],
}
TYPES = {"think_tank": "Think tank", "io": "Organisation internationale", "ngo": "ONG", "gov": "Agence publique",
         "consultancy": "Cabinet", "media": "Revue spécialisée"}


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s)


class Tagger:
    """Pays, régions et thèmes cités dans un titre + résumé."""

    def __init__(self, countries):
        names = {}
        for it in countries.items:
            for n in (it.get("name_en"), it.get("name_fr")):
                if n and len(normalize(n)) >= 4:
                    names[normalize(n)] = it["iso2"]
        names.update({k: v for k, v in ALIASES.items() if len(k) >= 4})
        names.update(DEMONYMS)
        # « Niger » ne doit pas trouver « Nigeria », « Guinea » pas « Guinea-Bissau » : les plus longs d'abord
        keys = sorted(names, key=len, reverse=True)
        self.names = names
        self.re = re.compile(r"(?<![\w-])(" + "|".join(re.escape(k) for k in keys) + r")(?![\w-])")
        self.regions = {r: re.compile(r"(?<!\w)(" + "|".join(re.escape(w) for w in ws) + r")(?!\w)") for r, ws in REGIONS.items()}
        self.themes = {t: re.compile(r"(?<!\w)(" + "|".join(re.escape(w.strip()) for w in ws) + r")") for t, ws in THEMES.items()}

    def tag(self, text):
        t = _norm(text)
        isos = []
        for m in self.re.finditer(t):
            iso = self.names[m.group(1)]
            if iso not in isos:
                isos.append(iso)
        regions = [r for r, rx in self.regions.items() if rx.search(t)]
        themes = [k for k, rx in self.themes.items() if rx.search(t)]
        return isos[:8], regions[:4], themes[:4]


def _clean(s):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", html.unescape(s or "")))).strip()


def fetch_feed(feed):
    r = http.get(feed["url"], retries=1, timeout=30)
    return list(_items(parse_xml(r.content)))


def update(store, countries, log, now, fetch=True):
    cfg = config.load_json("reports.json", {}) or {}
    feeds = [f for f in cfg.get("feeds") or [] if f.get("enabled", True) and f.get("url")]
    st = store.setdefault("reports", {})
    status = store.setdefault("state", {}).setdefault("reports_status", {})
    tagger = Tagger(countries)
    max_age = timedelta(days=int(cfg.get("max_age_days", 365)))
    per_feed = int(cfg.get("per_feed", 40))
    t0 = time.time()

    def one(f):
        try:
            return f, fetch_feed(f), None
        except Exception as exc:  # un flux en panne ne bloque jamais les autres
            return f, [], f"{type(exc).__name__}: {exc}"[:200]
    results = []
    if fetch:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(one, feeds))
    new = 0
    for f, items, err in results:
        status[f["id"]] = {"ok": err is None, "error": err, "count": len(items), "checked": now.isoformat()}
        keep = re.compile(f["keep_link"]) if f.get("keep_link") else None
        drop = re.compile(f["drop_title"], re.I) if f.get("drop_title") else None
        for it in items[:per_feed]:
            title, link = _clean(it["title"]), (it["link"] or "").strip()
            if not title or not link or (keep and not keep.search(link)) or (drop and drop.search(title)):
                continue
            date = it["date"] or now
            if now - date > max_age:
                continue
            summary = _clean(it.get("desc"))
            if summary.lower().startswith(title.lower()[:40]):
                summary = summary[len(title):].strip(" .:-–")
            isos, regions, themes = tagger.tag(f"{title}. {summary}")
            if f.get("require_geo") and not isos and not regions:
                continue
            rid = hashlib.sha1(link.split("?")[0].rstrip("/").encode()).hexdigest()[:12]
            if rid not in st:
                new += 1
            st[rid] = {"id": rid, "t": title[:220], "u": link, "d": to_iso(date), "o": f["id"],
                       "s": summary[:300] if len(summary) >= 40 else "", "c": isos, "r": regions, "th": themes,
                       "l": f.get("lang", "en")}
    for m in cfg.get("manual") or []:
        if not m.get("title") or not m.get("url"):
            continue
        rid = "m-" + hashlib.sha1(m["url"].encode()).hexdigest()[:10]
        isos, regions, themes = tagger.tag(f"{m['title']}. {m.get('summary', '')}")
        st[rid] = {"id": rid, "t": m["title"], "u": m["url"], "d": (m.get("date") or now.date().isoformat())[:10] + "T00:00:00Z",
                   "o": "manual:" + (m.get("org") or "Angor"), "s": (m.get("summary") or "")[:300],
                   "c": [c.upper() for c in m.get("countries") or []] or isos, "r": regions, "th": themes,
                   "l": m.get("lang", "fr"), "type": m.get("type", "ngo")}
    cutoff = to_iso(now - max_age)
    items = sorted((v for v in st.values() if v["d"] >= cutoff), key=lambda v: v["d"], reverse=True)[: int(cfg.get("max_items", 1500))]
    store["reports"] = {v["id"]: v for v in items}
    orgs = {f["id"]: {"n": f["org"], "type": f.get("type", "think_tank"), "lang": f.get("lang", "en"), "focus": f.get("focus", "")}
            for f in feeds}
    for v in items:
        if v["o"].startswith("manual:"):
            orgs[v["o"]] = {"n": v["o"][7:], "type": v.get("type", "ngo"), "lang": v.get("l", "fr"), "focus": ""}
    ok = sum(1 for f in feeds if (status.get(f["id"]) or {}).get("ok"))
    write_js("reports.js", "VS_REPORTS", {"generated": now.isoformat(), "orgs": orgs, "types": TYPES,
                                          "items": items, "feeds_ok": ok, "feeds": len(feeds)})
    if fetch:
        log(f"  Rapports : {len(items)} publication(s) de {len({o['n'] for o in orgs.values()})} producteur(s), {new} nouvelle(s) "
            f"({ok}/{len(feeds)} flux en service, {time.time() - t0:.0f} s)")
    return items
