"""Google News (flux RSS publics) – presse locale de ~110 pays, dans la langue du pays.

Pour chaque pays, deux requêtes : « sûreté » (attentats, manifestations, catastrophes…) et
« économie » (investissements, contrats, appels d'offres, sanctions…). Pour ménager votre PC
et les serveurs de Google, chaque collecte n'interroge qu'une partie des pays (rotation) :
tous les pays sont couverts en quelques heures.

Titre, source et lien uniquement (jamais le texte de l'article).
"""
import hashlib
import re
import time
import xml.etree.ElementTree as ET
from datetime import timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote

from .. import http

KIND = "events"
URL = "https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"

EDITIONS = {  # clé : (hl, gl, ceid, langue des mots-clés)
    "fr-FR": ("fr", "FR", "FR:fr", "fr"), "fr-BE": ("fr", "BE", "BE:fr", "fr"), "fr-CA": ("fr-CA", "CA", "CA:fr", "fr"),
    "fr-SN": ("fr", "SN", "SN:fr", "fr"), "fr-MA": ("fr", "MA", "MA:fr", "fr"),
    "en-US": ("en-US", "US", "US:en", "en"), "en-GB": ("en-GB", "GB", "GB:en", "en"), "en-IE": ("en-IE", "IE", "IE:en", "en"),
    "en-IN": ("en-IN", "IN", "IN:en", "en"), "en-NG": ("en-NG", "NG", "NG:en", "en"), "en-ZA": ("en-ZA", "ZA", "ZA:en", "en"),
    "en-KE": ("en-KE", "KE", "KE:en", "en"), "en-PK": ("en-PK", "PK", "PK:en", "en"), "en-PH": ("en-PH", "PH", "PH:en", "en"),
    "en-AU": ("en-AU", "AU", "AU:en", "en"), "en-CA": ("en-CA", "CA", "CA:en", "en"), "en-SG": ("en-SG", "SG", "SG:en", "en"),
    "en-GH": ("en-GH", "GH", "GH:en", "en"),
    "es-ES": ("es", "ES", "ES:es", "es"), "es-MX": ("es-419", "MX", "MX:es-419", "es"), "es-AR": ("es-419", "AR", "AR:es-419", "es"),
    "es-CO": ("es-419", "CO", "CO:es-419", "es"), "es-CL": ("es-419", "CL", "CL:es-419", "es"), "es-PE": ("es-419", "PE", "PE:es-419", "es"),
    "es-VE": ("es-419", "VE", "VE:es-419", "es"), "pt-BR": ("pt-BR", "BR", "BR:pt-419", "pt"), "pt-PT": ("pt-PT", "PT", "PT:pt-150", "pt"),
    "de-DE": ("de", "DE", "DE:de", "de"), "de-AT": ("de", "AT", "AT:de", "de"), "it-IT": ("it", "IT", "IT:it", "it"),
    "nl-NL": ("nl", "NL", "NL:nl", "nl"), "pl-PL": ("pl", "PL", "PL:pl", "pl"), "tr-TR": ("tr", "TR", "TR:tr", "tr"),
    "ru-RU": ("ru", "RU", "RU:ru", "ru"), "uk-UA": ("uk", "UA", "UA:uk", "uk"), "ar-EG": ("ar", "EG", "EG:ar", "ar"),
    "ar-SA": ("ar", "SA", "SA:ar", "ar"), "ar-LB": ("ar", "LB", "LB:ar", "ar"), "ar-AE": ("ar", "AE", "AE:ar", "ar"),
    "he-IL": ("he", "IL", "IL:he", "he"), "id-ID": ("id", "ID", "ID:id", "id"),
    "th-TH": ("th", "TH", "TH:th", "th"), "zh-CN": ("zh-CN", "CN", "CN:zh-Hans", "zh"), "bn-BD": ("bn", "BD", "BD:bn", "bn"),
}

TERMS = {
    "security": {
        "fr": 'attentat OR attaque OR explosion OR fusillade OR manifestation OR émeute OR enlèvement OR affrontements OR inondations OR séisme OR "état d\'urgence"',
        "en": 'attack OR explosion OR shooting OR protest OR riot OR kidnapping OR clashes OR militants OR floods OR earthquake OR "state of emergency"',
        "es": "atentado OR ataque OR explosión OR tiroteo OR protesta OR disturbios OR secuestro OR enfrentamientos OR inundaciones OR sismo",
        "pt": "atentado OR ataque OR explosão OR tiroteio OR protesto OR sequestro OR confronto OR enchentes OR terremoto",
        "de": "Anschlag OR Angriff OR Explosion OR Schießerei OR Protest OR Unruhen OR Entführung OR Hochwasser OR Erdbeben",
        "it": "attentato OR attacco OR esplosione OR sparatoria OR protesta OR scontri OR rapimento OR alluvione OR terremoto",
        "nl": "aanslag OR aanval OR explosie OR schietpartij OR protest OR rellen OR ontvoering OR overstroming",
        "pl": "zamach OR atak OR wybuch OR strzelanina OR protest OR zamieszki OR porwanie OR powódź",
        "tr": "saldırı OR patlama OR silahlı OR protesto OR çatışma OR kaçırma OR sel OR deprem",
        "ru": "теракт OR нападение OR взрыв OR стрельба OR протест OR беспорядки OR похищение OR наводнение OR землетрясение",
        "uk": "теракт OR напад OR вибух OR обстріл OR протест OR викрадення OR повінь",
        "ar": "هجوم OR انفجار OR احتجاجات OR اشتباكات OR اختطاف OR فيضانات OR زلزال",
        "he": "פיגוע OR פיצוץ OR ירי OR הפגנה OR חטיפה",
        "id": "serangan OR ledakan OR penembakan OR demo OR kerusuhan OR penculikan OR banjir OR gempa",
        "th": "ระเบิด OR โจมตี OR ยิง OR ประท้วง OR ชุมนุม OR ปะทะ OR น้ำท่วม OR แผ่นดินไหว",
        "zh": "爆炸 OR 袭击 OR 枪击 OR 抗议 OR 冲突 OR 绑架 OR 洪水 OR 地震",
        "bn": "হামলা OR বিস্ফোরণ OR সংঘর্ষ OR বিক্ষোভ OR অপহরণ OR বন্যা OR ভূমিকম্প",
        "fa": "حمله OR انفجار OR تیراندازی OR اعتراض OR درگیری OR سیل OR زلزله",
        "ur": "حملہ OR دھماکہ OR فائرنگ OR احتجاج OR اغوا OR سیلاب OR زلزلہ",
        "am": "ጥቃት OR ፍንዳታ OR ግጭት OR ተቃውሞ OR ጎርፍ",
        "so": "weerar OR qarax OR dagaal OR banaanbax OR fatahaad",
    },
    "economy": {
        "fr": 'investissement OR contrat OR "appel d\'offres" OR privatisation OR usine OR acquisition OR sanctions OR "accord commercial" OR concession',
        "en": 'investment OR contract OR tender OR privatization OR factory OR acquisition OR sanctions OR "trade deal" OR concession',
        "es": "inversión OR contrato OR licitación OR privatización OR fábrica OR adquisición OR sanciones OR concesión",
        "pt": "investimento OR contrato OR licitação OR privatização OR fábrica OR aquisição OR sanções OR concessão",
        "de": "Investition OR Auftrag OR Ausschreibung OR Privatisierung OR Werk OR Übernahme OR Sanktionen",
        "it": "investimento OR contratto OR appalto OR privatizzazione OR stabilimento OR acquisizione OR sanzioni",
        "nl": "investering OR contract OR aanbesteding OR fabriek OR overname OR sancties",
        "pl": "inwestycja OR kontrakt OR przetarg OR prywatyzacja OR fabryka OR przejęcie OR sankcje",
        "tr": "yatırım OR sözleşme OR ihale OR özelleştirme OR fabrika OR yaptırım",
        "ru": "инвестиции OR контракт OR тендер OR приватизация OR завод OR санкции",
        "uk": "інвестиції OR контракт OR тендер OR приватизація OR завод OR санкції",
        "ar": "استثمار OR عقد OR مناقصة OR خصخصة OR مصنع OR عقوبات",
        "he": "השקעה OR חוזה OR מכרז OR מפעל",
        "id": "investasi OR kontrak OR tender OR privatisasi OR pabrik OR akuisisi",
    },
}

# (pays, édition, nom du pays à ajouter à la requête si l'édition n'est pas celle du pays)
COUNTRIES = [
    ("FR", "fr-FR", None), ("BE", "fr-BE", None), ("CA", "en-CA", None), ("SN", "fr-SN", None), ("MA", "fr-MA", None),
    ("US", "en-US", None), ("GB", "en-GB", None), ("IE", "en-IE", None), ("IN", "en-IN", None), ("NG", "en-NG", None),
    ("ZA", "en-ZA", None), ("KE", "en-KE", None), ("PK", "en-PK", None), ("PH", "en-PH", None), ("AU", "en-AU", None),
    ("SG", "en-SG", None), ("GH", "en-GH", None), ("ES", "es-ES", None), ("MX", "es-MX", None), ("AR", "es-AR", None),
    ("CO", "es-CO", None), ("CL", "es-CL", None), ("PE", "es-PE", None), ("VE", "es-VE", None), ("BR", "pt-BR", None),
    ("PT", "pt-PT", None), ("DE", "de-DE", None), ("AT", "de-AT", None), ("IT", "it-IT", None), ("NL", "nl-NL", None),
    ("PL", "pl-PL", None), ("TR", "tr-TR", None), ("RU", "ru-RU", None), ("UA", "uk-UA", None), ("EG", "ar-EG", None),
    ("SA", "ar-SA", None), ("LB", "ar-LB", None), ("AE", "ar-AE", None), ("IL", "he-IL", None), ("ID", "id-ID", None),
    ("CH", "fr-FR", "Suisse"), ("LU", "fr-FR", "Luxembourg"),
    # Afrique francophone, Maghreb, Haïti (édition française + nom du pays)
    ("ML", "fr-FR", "Mali"), ("BF", "fr-FR", '"Burkina Faso"'), ("NE", "fr-FR", "Niger"), ("TD", "fr-FR", "Tchad"),
    ("CI", "fr-FR", '"Côte d\'Ivoire"'), ("CM", "fr-FR", "Cameroun"), ("CD", "fr-FR", "RDC"), ("CF", "fr-FR", "Centrafrique"),
    ("GN", "fr-FR", "Guinée"), ("BJ", "fr-FR", "Bénin"), ("TG", "fr-FR", "Togo"), ("GA", "fr-FR", "Gabon"),
    ("CG", "fr-FR", '"Congo-Brazzaville"'), ("MG", "fr-FR", "Madagascar"), ("DZ", "fr-FR", "Algérie"),
    ("TN", "fr-FR", "Tunisie"), ("HT", "fr-FR", "Haïti"), ("MR", "fr-FR", "Mauritanie"), ("DJ", "fr-FR", "Djibouti"),
    ("RW", "fr-FR", "Rwanda"), ("BI", "fr-FR", "Burundi"), ("NC", "fr-FR", '"Nouvelle-Calédonie"'),
    # reste du monde (édition anglaise + nom du pays)
    ("SD", "en-US", "Sudan"), ("SS", "en-US", '"South Sudan"'), ("SO", "en-US", "Somalia"), ("ET", "en-US", "Ethiopia"),
    ("UG", "en-US", "Uganda"), ("TZ", "en-US", "Tanzania"), ("MZ", "en-US", "Mozambique"), ("ZW", "en-US", "Zimbabwe"),
    ("LY", "en-US", "Libya"), ("YE", "en-US", "Yemen"), ("SY", "en-US", "Syria"), ("IQ", "en-US", "Iraq"),
    ("IR", "en-US", "Iran"), ("AF", "en-US", "Afghanistan"), ("BD", "en-US", "Bangladesh"), ("LK", "en-US", '"Sri Lanka"'),
    ("NP", "en-US", "Nepal"), ("MM", "en-US", "Myanmar"), ("TH", "en-US", "Thailand"), ("VN", "en-US", "Vietnam"),
    ("MY", "en-US", "Malaysia"), ("CN", "en-US", "China"), ("TW", "en-US", "Taiwan"), ("JP", "en-US", "Japan"),
    ("KR", "en-US", '"South Korea"'), ("KP", "en-US", '"North Korea"'), ("KZ", "en-US", "Kazakhstan"),
    ("AZ", "en-US", "Azerbaijan"), ("AM", "en-US", "Armenia"), ("GE", "en-US", "Georgia"), ("RS", "en-US", "Serbia"),
    ("BA", "en-US", "Bosnia"), ("XK", "en-US", "Kosovo"), ("GR", "en-US", "Greece"), ("RO", "en-US", "Romania"),
    ("HU", "en-US", "Hungary"), ("BY", "en-US", "Belarus"), ("MD", "en-US", "Moldova"), ("JO", "en-US", "Jordan"),
    ("KW", "en-US", "Kuwait"), ("QA", "en-US", "Qatar"), ("OM", "en-US", "Oman"), ("PS", "en-US", '(Gaza OR "West Bank")'),
    ("CU", "es-MX", "Cuba"), ("EC", "es-MX", "Ecuador"), ("BO", "es-MX", "Bolivia"), ("NI", "es-MX", "Nicaragua"),
    ("HN", "es-MX", "Honduras"), ("GT", "es-MX", "Guatemala"), ("SV", "es-MX", '"El Salvador"'), ("PA", "es-MX", "Panamá"),
    ("DO", "es-MX", '"República Dominicana"'), ("PY", "es-MX", "Paraguay"), ("UY", "es-MX", "Uruguay"),
    ("AO", "pt-PT", "Angola"), ("GW", "pt-PT", '"Guiné-Bissau"'),
]
TITLE_SOURCE = re.compile(r"^(.*)\s+-\s+([^-]{2,60})$")


def _queries(cfg):
    countries = cfg.get("countries") or COUNTRIES
    themes = cfg.get("themes", ["security", "economy"])
    return [(c, t) for c in countries for t in themes]


def parse_items(root, ctx, iso, lang, theme, max_age, max_items, feed="Google News"):
    """Lit un flux Google News : titres de sûreté → ctx.press, titres économiques → ctx.econ."""
    n = 0
    for it in list(root.iter("item"))[:max_items]:
        raw_title = (it.findtext("title") or "").strip()
        src_el = it.find("source")
        outlet = (src_el.text or "").strip() if src_el is not None and src_el.text else ""
        m = TITLE_SOURCE.match(raw_title)
        title = m.group(1).strip() if m else raw_title
        outlet = outlet or (m.group(2).strip() if m else "Google News")
        try:
            date = parsedate_to_datetime(it.findtext("pubDate"))
        except (TypeError, ValueError):
            date = ctx.now
        if ctx.now - date > max_age or not title:
            continue
        item = {"title": title, "url": (it.findtext("link") or "").strip(), "outlet": outlet,
                "date": date, "country_hint": iso, "lang": lang, "feed": feed}
        site = src_el.get("url") if src_el is not None else ""
        if site:  # domaine du média (sert à sa cotation de fiabilité)
            item["site"] = re.sub(r"^(www|m)\.", "", re.sub(r"^https?://", "", site).split("/")[0].lower())
        if theme == "economy":
            item["id"] = "eco-" + hashlib.sha1(title.lower().encode()).hexdigest()[:12]
            ctx.econ.append(item)
        else:
            ctx.press.append(item)
        n += 1
    return n


def fetch(cfg, ctx):
    queries = _queries(cfg)
    per_run = int(cfg.get("queries_per_run", 40))
    start = int(ctx.state.get("gnews_cursor", 0)) % len(queries)
    batch = [queries[(start + i) % len(queries)] for i in range(min(per_run, len(queries)))]
    budget = time.time() + float(cfg.get("time_budget_s", 90))  # ne jamais monopoliser le PC
    max_age = timedelta(hours=int(cfg.get("max_age_hours", 48)))
    max_items = int(cfg.get("max_items_per_query", 20))
    fails = done = 0
    for (iso, edition, name), theme in batch:
        if time.time() > budget:
            break
        done += 1
        hl, gl, ceid, lang = EDITIONS[edition]
        terms = TERMS[theme].get(lang, TERMS[theme]["en"])
        q = f"{name} ({terms})" if name else f"({terms})"
        q += " when:2d"
        url = URL.format(q=quote(q), hl=hl, gl=gl, ceid=ceid)
        try:
            root = ET.fromstring(http.get(url, retries=1, timeout=20).content)
        except Exception:
            fails += 1
            continue
        parse_items(root, ctx, iso, lang, theme, max_age, max_items)
    ctx.state["gnews_cursor"] = (start + done) % len(queries)
    if fails:
        ctx.log(f"  Google News : {fails}/{done} requête(s) sans réponse")
    ctx.log(f"  Google News : {done} requêtes ({len(queries)} au total, rotation)")
    return []
