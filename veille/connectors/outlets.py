"""Médias de référence par pays (≈ 200 pays, 3 à 5 titres fiables chacun) via Google News.

Le catalogue est dans config/press_outlets.json (généré par tools/outlets_src.py).
Pour chaque pays, une requête par langue : (site:media1 OR site:media2 …) + mots-clés de sûreté.
Les médias régionaux ou internationaux (marqués « + ») sont interrogés avec le nom du pays.
Rotation : chaque collecte n'interroge qu'une partie des pays ; tout le catalogue est couvert
en quelques heures (ou en ~2 h en ligne, collecte toutes les 30 min).

Titre, média et lien uniquement (jamais le texte de l'article).
"""
import time
import xml.etree.ElementTree as ET
from datetime import timedelta
from urllib.parse import quote

from .. import config, http
from ..langs import EDITIONS as LANG_EDITIONS
from ..langs import LANGS
from .gnews import EDITIONS, TERMS, URL, parse_items

KIND = "events"
LANG_EDITION = {"fr": "fr-FR", "en": "en-US", "es": "es-MX", "pt": "pt-BR", "de": "de-DE", "it": "it-IT",
                "nl": "nl-NL", "pl": "pl-PL", "tr": "tr-TR", "ru": "ru-RU", "uk": "uk-UA", "ar": "ar-EG",
                "he": "he-IL", "id": "id-ID", "th": "th-TH", "zh": "zh-CN", "bn": "bn-BD",
                # pas d'édition Google News dans ces langues : édition internationale, mots-clés dans la langue du média
                "fa": "en-US", "ur": "en-US", "am": "en-US", "so": "en-US"}
# langues ajoutées en v0.25 : leur édition Google News si elle existe, sinon l'édition internationale
for _lg in LANGS:
    LANG_EDITION.setdefault(_lg, LANG_EDITIONS[_lg][0] if _lg in LANG_EDITIONS else "en-US")
CHUNK = 6  # médias par requête (au-delà, la requête est découpée)


def queries(catalog, countries, themes=("security",)):
    """[(iso, langue, requête, médias)] – une requête par pays, langue et type (local / « + »)."""
    out = []
    for iso, outlets in sorted(catalog.items()):
        groups = {}
        for o in outlets:
            lang = o[2] if o[2] in LANG_EDITION else "en"
            groups.setdefault((lang, len(o) > 3 and o[3] == "+"), []).append(o)
        for (lang, with_name), items in sorted(groups.items()):
            name = ""
            if with_name:
                n = countries.name(iso, "fr" if lang == "fr" else "en") if countries else iso
                name = f'"{n}" '
            for k in range(0, len(items), CHUNK):
                part = items[k:k + CHUNK]
                sites = " OR ".join(f"site:{o[1]}" for o in part)
                for theme in themes:
                    terms = TERMS[theme].get(lang, TERMS[theme]["en"])
                    out.append((iso, lang, theme, f"{name}({sites}) ({terms}) when:2d", [o[1] for o in part]))
    return out


MUTE_AFTER = 30   # requêtes sans un seul titre : domaine erroné, site fermé ou média sans actualité de sûreté


def _host(domain):
    return domain.split("/")[0].lower()


def record(stats, iso, domains, items, now):
    """Bilan par média : requêtes où il figurait, titres obtenus (v0.25). Sert à repérer les « médias muets »."""
    sites = [it.get("site") or "" for it in items]
    for d in domains:
        h = _host(d)
        st = stats.setdefault(f"{iso}|{d}", {"q": 0, "hits": 0})
        st["q"] += 1
        n = sum(1 for s in sites if s == h or s.endswith("." + h) or h.endswith("." + s))
        if n:
            st["hits"] += n
            st["last"] = now.replace(microsecond=0).isoformat()


def muted(stats, catalog):
    """Médias du catalogue jamais trouvés après MUTE_AFTER requêtes (à vérifier ou remplacer)."""
    names = {f"{iso}|{o[1]}": o[0] for iso, rows in catalog.items() for o in rows}
    out = [{"country": k.split("|")[0], "domain": k.split("|", 1)[1], "name": names[k], "queries": st["q"]}
           for k, st in stats.items() if k in names and st["q"] >= MUTE_AFTER and not st["hits"]]
    return sorted(out, key=lambda r: (-r["queries"], r["country"]))


def fetch(cfg, ctx):
    catalog = (config.load_json(cfg.get("catalog", "press_outlets.json"), {}) or {}).get("countries", {})
    if not catalog:
        raise ValueError("catalogue config/press_outlets.json introuvable ou vide")
    qs = queries(catalog, ctx.countries, tuple(cfg.get("themes", ["security"])))
    per_run = int(cfg.get("queries_per_run", 60))
    start = int(ctx.state.get("outlets_cursor", 0)) % len(qs)
    batch = [qs[(start + i) % len(qs)] for i in range(min(per_run, len(qs)))]
    budget = time.time() + float(cfg.get("time_budget_s", 120))
    max_age = timedelta(hours=int(cfg.get("max_age_hours", 48)))
    max_items = int(cfg.get("max_items_per_query", 25))
    fails = done = found = 0
    stats = ctx.state.setdefault("outlet_stats", {})
    known = {f"{iso}|{o[1]}" for iso, rows in catalog.items() for o in rows}
    for k in [k for k in stats if k not in known]:   # médias retirés du catalogue
        del stats[k]
    for iso, lang, theme, q, domains in batch:
        if time.time() > budget:
            break
        done += 1
        before = len(ctx.press)
        hl, gl, ceid, _ = EDITIONS[LANG_EDITION[lang]]
        url = URL.format(q=quote(q), hl=hl, gl=gl, ceid=ceid)
        try:
            root = ET.fromstring(http.get(url, retries=1, timeout=20).content)
        except Exception:
            fails += 1
            continue
        found += parse_items(root, ctx, iso, lang, theme, max_age, max_items, feed="Médias de référence")
        record(stats, iso, domains, ctx.press[before:], ctx.now)
    ctx.state["outlets_cursor"] = (start + done) % len(qs)
    if fails:
        ctx.log(f"  Médias de référence : {fails}/{done} requête(s) sans réponse")
    ctx.log(f"  Médias de référence : {done} requêtes sur {len(qs)} ({len(catalog)} pays), {found} titres")
    return []
