"""MEAE (France) – Conseils aux voyageurs, rubrique « Sécurité » de diplomatie.gouv.fr.

Le ministère ne publie pas de flux de données : la page « Sécurité » de chaque pays est lue et le
niveau déduit des formulations officielles de la carte :
  4 rouge  « formellement déconseillé »          3 orange « déconseillé sauf raison impérative »
  2 jaune  « vigilance renforcée »                1 vert   « vigilance normale » (ou aucune mention)
« max » = zone la plus sensible (couleur de la carte) ; « parts » = plusieurs niveaux dans le pays.
Le niveau retenu pour la note de risque est celui du pays entier, ou le niveau inférieur au plus élevé
quand seules certaines zones sont concernées.

Lecture progressive et polie : quelques dizaines de pages par collecte, chaque page relue tous les
3 jours. Indicatif : la carte officielle (lien et image) fait foi.
"""
import html
import re
import time
import unicodedata
from datetime import datetime, timedelta

from .. import http

KIND = "advisories"
SITE = "https://www.diplomatie.gouv.fr"
PAGE = SITE + "/fr/information-par-pays/{slug}/conseils-aux-voyageurs-securite"
INDEXES = [SITE + "/fr/conseils-aux-voyageurs/conseils-par-pays-destination/", SITE + "/fr/information-par-pays/"]
LINK_RE = re.compile(r'href="(?:https?://www\.diplomatie\.gouv\.fr)?/fr/(?:conseils-aux-voyageurs/conseils-par-pays-destination|information-par-pays)/([a-z0-9-]+)/?[^"]*"[^>]*>([^<]{2,80})<', re.I)
MAP_RE = re.compile(r'((?:https?://www\.diplomatie\.gouv\.fr)?/files/files/cav/[^"\'\s>]+\.(?:jpe?g|png|gif|webp))', re.I)
UPDATED_RE = re.compile(r"Derni[eè]re actualisation le\s*(\d{1,2}/\d{1,2}/\d{4})", re.I)
PHRASES = {4: re.compile(r"formellement deconseill"), 3: re.compile(r"deconseill\w*\s+sauf\s+raison\s+imperative"),
           2: re.compile(r"vigilance\s+renforcee"), 1: re.compile(r"vigilance\s+normale")}
LABELS = {1: "Vigilance normale", 2: "Vigilance renforcée", 3: "Déconseillé sauf raison impérative",
          4: "Formellement déconseillé"}
SLUGS = {"US": "etats-unis", "GB": "royaume-uni", "CD": "republique-democratique-du-congo", "CG": "congo",
         "KR": "coree-du-sud", "KP": "coree-du-nord", "CF": "republique-centrafricaine", "CI": "cote-d-ivoire",
         "MM": "birmanie", "AE": "emirats-arabes-unis", "SA": "arabie-saoudite", "BA": "bosnie-herzegovine",
         "MK": "macedoine-du-nord", "CZ": "republique-tcheque", "TL": "timor-oriental", "CV": "cap-vert",
         "KG": "kirghizstan", "NL": "pays-bas", "NZ": "nouvelle-zelande", "PG": "papouasie-nouvelle-guinee",
         "SB": "iles-salomon", "VA": "saint-siege", "PS": "israel-territoires-palestiniens",
         "IL": "israel-territoires-palestiniens", "DO": "republique-dominicaine", "GQ": "guinee-equatoriale",
         "GW": "guinee-bissao", "FM": "micronesie", "MH": "iles-marshall", "RU": "russie", "BY": "bielorussie",
         "MD": "moldavie", "LA": "laos", "SY": "syrie", "VN": "vietnam", "TW": "taiwan", "SZ": "eswatini"}
# Collectivités françaises et territoires sans page propre
SKIP = {"FR", "GP", "MQ", "GF", "RE", "YT", "PM", "BL", "MF", "WF", "PF", "NC", "TF", "AQ", "HM", "BV", "GS", "IO",
        "UM", "CYN", "KAS", "SOL"}


def plain(text):
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text)).lower()
    text = unicodedata.normalize("NFKD", text)
    return re.sub(r"\s+", " ", "".join(c for c in text if not unicodedata.combining(c)))


def slugify(name):
    s = unicodedata.normalize("NFKD", name.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def _discover(ctx):
    """Slugs officiels depuis les pages d'index (si elles répondent), sinon {}."""
    found = {}
    for url in INDEXES:
        try:
            text = http.get(url, retries=0, timeout=20).text
        except Exception:
            continue
        for slug, label in LINK_RE.findall(text):
            item = ctx.countries.by_country_name(html.unescape(label).strip())
            if item and item["iso2"] not in found:
                found[item["iso2"]] = slug
        if len(found) > 50:
            break
    return found


def assess(counts, baseline):
    """Niveaux présents (au-delà des mentions communes à toutes les pages) → (niveau, zones ?, max)."""
    present = [lvl for lvl in (4, 3, 2) if counts.get(str(lvl), 0) > baseline.get(str(lvl), 0)]
    if not present:
        return 1, False, 1
    mx, lo = max(present), min(present)
    green = counts.get("1", 0) > baseline.get("1", 0)
    parts = len(present) > 1 or green
    level = mx if not parts else max(lo if not green else 1, mx - 1)
    return level, parts, mx


def fetch(cfg, ctx):
    st = ctx.state.setdefault("fr_adv", {"pages": {}, "slugs": {}, "discovered": None})
    now = ctx.now
    if not st.get("discovered") or now - datetime.fromisoformat(st["discovered"]) > timedelta(days=30):
        found = _discover(ctx)
        if found:
            st["slugs"].update(found)
        st["discovered"] = now.isoformat()
    refresh = timedelta(days=float(cfg.get("refresh_days", 3)))
    todo = []
    for item in ctx.countries.items:
        iso = item["iso2"]
        if iso in SKIP or not item.get("name_fr"):
            continue
        page = st["pages"].get(iso)
        if page and now - datetime.fromisoformat(page["fetched"]) < (refresh if page.get("ok") else timedelta(days=7)):
            continue
        todo.append((page["fetched"] if page else "", iso, item))
    todo.sort()  # jamais lus d'abord, puis les plus anciens
    budget = time.time() + float(cfg.get("time_budget_s", 75))
    done = fails = 0
    for _, iso, item in todo[: int(cfg.get("pages_per_run", 45))]:
        if time.time() > budget or fails >= 6:
            break
        slugs = [s for s in dict.fromkeys([st["slugs"].get(iso), SLUGS.get(iso), slugify(item["name_fr"])]) if s]
        text = slug_ok = None
        blocked = False
        for slug in slugs:
            try:
                r = http.get(PAGE.format(slug=slug), retries=0, timeout=20)
                if r.status_code == 200 and "curit" in r.text.lower():
                    text, slug_ok = r.text, slug
                    break
            except Exception as exc:  # 404 = mauvais slug ; autre erreur = site indisponible ou blocage
                code = getattr(getattr(exc, "response", None), "status_code", None)
                blocked = blocked or code != 404
                continue
        entry = {"fetched": now.isoformat(), "ok": bool(text)}
        if text:
            fails = 0
            low = plain(text)
            m = MAP_RE.search(text)
            u = UPDATED_RE.search(html.unescape(text))
            entry.update(slug=slug_ok, counts={str(k): len(rx.findall(low)) for k, rx in PHRASES.items()},
                         map=(SITE + m.group(1) if m and m.group(1).startswith("/") else m.group(1) if m else None),
                         updated=u.group(1) if u else None)
            st["slugs"][iso] = slug_ok
            done += 1
        elif blocked:
            fails += 1
            continue  # site injoignable : on réessaiera à la prochaine collecte
        st["pages"][iso] = entry
        time.sleep(float(cfg.get("pause_s", 0.3)))
    ok = {iso: p for iso, p in st["pages"].items() if p.get("ok")}
    # mentions présentes sur toutes les pages (gabarit, légende) = bruit de fond à ignorer
    if len(ok) < 15:  # trop peu de pages pour distinguer le gabarit du contenu : on attend
        ctx.log(f"  MEAE : {len(ok)} page(s) lue(s) à ce jour, niveaux publiés à partir de 15")
        return {}
    baseline = {k: min(p["counts"].get(k, 0) for p in ok.values()) for k in ("1", "2", "3", "4")}
    out = {}
    for iso, p in ok.items():
        level, parts, mx = assess(p["counts"], baseline)
        out[iso] = {"level": level, "scale": 4, "max": mx, "parts": parts,
                    "label": LABELS[mx] + (" (certaines zones)" if parts and mx > 1 else ""),
                    "url": PAGE.format(slug=p["slug"]), "updated": p.get("updated"), "map": p.get("map")}
    if todo:
        ctx.log(f"  MEAE : {done} page(s) lue(s), {len(todo) - done} en attente, {len(out)} pays connus")
    return out
