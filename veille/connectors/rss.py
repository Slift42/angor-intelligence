"""Connecteur générique RSS / Atom / RDF – presse et institutions, gratuites aujourd'hui, sous abonnement demain.

Options (config/sources.json) :
  "url"      : adresse du flux
  "auth"     : voir veille/http.py (cookie, clé… pour un flux réservé aux abonnés)
  "filter"   : "security" (défaut) → seuls les titres relevant de la sûreté sont gardés, classés et, si un
                                     lieu est reconnu, placés sur la carte (confiance faible) ;
               "economy"           → titres économiques, pour les rapports pays ;
               "none"              → tout va dans le Fil (ex. alertes CERT-FR) ;
  "country"  : pays par défaut du flux (presse locale), ex. "ML"
  "lang"     : langue du flux (information)
Titre, lien et chapeau (300 caractères maximum, publié par le média dans son flux) – jamais le texte
des articles (droit d'auteur).
"""
import hashlib
import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from .. import http
from ..model import parse_iso, to_iso

KIND = "events"
TAG_RE = re.compile(r"<[^>]+>")


def _local(tag):
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _child(el, name):
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _text(el, name):
    c = _child(el, name)
    return (c.text or "").strip() if c is not None and c.text else ""


def _date(value):
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            return parse_iso(value)
        except ValueError:
            return None


_BAD_AMP = re.compile(r"&(?!#?\w+;)")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def parse_xml(content):
    """Analyse un flux, en réparant les défauts courants (texte avant l'en-tête, « & » non échappé,
    caractères de contrôle) qui font échouer un analyseur strict."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        text = content.decode("utf-8", "replace") if isinstance(content, bytes) else content
        text = text.lstrip("\ufeff \r\n\t")
        start = text.find("<")
        if start < 0:
            raise
        text = _CTRL.sub("", _BAD_AMP.sub("&amp;", text[start:]))
        text = re.sub(r"^<\?xml[^>]*\?>", "", text)  # l'encodage déclaré ne s'applique plus à une chaîne
        root = ET.fromstring(text)
    if _local(root.tag).lower() == "html":
        raise ValueError("page HTML au lieu d'un flux RSS")
    return root


def _items(root):
    """RSS 2.0, RDF (RSS 1.0) et Atom, quels que soient les espaces de noms."""
    for el in root.iter():
        kind = _local(el.tag)
        if kind == "item":
            link = _text(el, "link") or el.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about", "")
            yield {"title": _text(el, "title"), "link": link, "desc": _text(el, "description"),
                   "date": _date(_text(el, "pubDate") or _text(el, "date"))}
        elif kind == "entry":
            link_el = _child(el, "link")
            yield {"title": _text(el, "title"), "link": link_el.get("href") if link_el is not None else "",
                   "desc": _text(el, "summary"), "date": _date(_text(el, "updated") or _text(el, "published"))}


def fetch(cfg, ctx):
    r = (getattr(ctx, "prefetch", None) or {}).get(cfg["url"])
    if isinstance(r, Exception):
        raise r
    if r is None:
        r = http.get(cfg["url"], auth=cfg.get("auth"), retries=1, timeout=25)
    root = parse_xml(r.content)
    name = cfg.get("name", cfg["id"])
    mode = cfg.get("filter", "security")
    keywords = [k.lower() for k in cfg.get("keywords", [])]
    n = 0
    for it in list(_items(root))[: int(cfg.get("max_items", 60))]:
        title = re.sub(r"\s+", " ", TAG_RE.sub("", it["title"])).strip()
        if not title or (keywords and not any(k in title.lower() for k in keywords)):
            continue
        date = it["date"] or ctx.now
        snippet = html.unescape(re.sub(r"\s+", " ", TAG_RE.sub(" ", html.unescape(it.get("desc") or "")))).strip()
        if snippet.lower().startswith(title.lower()[:40]):
            snippet = snippet[len(title):].strip(" .:-–")
        item = {"title": title, "url": it["link"], "outlet": name, "date": date,
                "snippet": snippet[:300] if len(snippet) >= 40 else "",
                "country_hint": cfg.get("country"), "lang": cfg.get("lang", ""), "feed": name,
                "site": re.sub(r"^(www|m|feeds)\.", "", (it["link"] or cfg["url"]).split("/")[2].lower()) if "//" in (it["link"] or cfg["url"]) else ""}
        if mode == "none":
            uid = hashlib.sha1((it["link"] or title).encode()).hexdigest()[:12]
            ctx.news.append({"id": f"rss-{cfg['id']}-{uid}", "source": name, "title": title, "url": it["link"],
                             "date": to_iso(date), "lang": cfg.get("lang", ""), "country": cfg.get("country"),
                             "category": cfg.get("category")})
        elif mode == "economy":
            item["id"] = "eco-" + hashlib.sha1(title.lower().encode()).hexdigest()[:12]
            ctx.econ.append(item)
        else:
            ctx.press.append(item)
        n += 1
    return []
