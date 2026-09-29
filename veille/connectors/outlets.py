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
from .gnews import EDITIONS, TERMS, URL, parse_items

KIND = "events"
LANG_EDITION = {"fr": "fr-FR", "en": "en-US", "es": "es-MX", "pt": "pt-BR", "de": "de-DE", "it": "it-IT",
                "nl": "nl-NL", "pl": "pl-PL", "tr": "tr-TR", "ru": "ru-RU", "uk": "uk-UA", "ar": "ar-EG",
                "he": "he-IL", "id": "id-ID", "th": "th-TH", "zh": "zh-CN", "bn": "bn-BD",
                # pas d'édition Google News dans ces langues : édition internationale, mots-clés dans la langue du média
                "fa": "en-US", "ur": "en-US", "am": "en-US", "so": "en-US"}
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
                    out.append((iso, lang, theme, f"{name}({sites}) ({terms}) when:2d", [o[0] for o in part]))
    return out


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
    for iso, lang, theme, q, _names in batch:
        if time.time() > budget:
            break
        done += 1
        hl, gl, ceid, _ = EDITIONS[LANG_EDITION[lang]]
        url = URL.format(q=quote(q), hl=hl, gl=gl, ceid=ceid)
        try:
            root = ET.fromstring(http.get(url, retries=1, timeout=20).content)
        except Exception:
            fails += 1
            continue
        found += parse_items(root, ctx, iso, lang, theme, max_age, max_items, feed="Médias de référence")
    ctx.state["outlets_cursor"] = (start + done) % len(qs)
    if fails:
        ctx.log(f"  Médias de référence : {fails}/{done} requête(s) sans réponse")
    ctx.log(f"  Médias de référence : {done} requêtes sur {len(qs)} ({len(catalog)} pays), {found} titres")
    return []
