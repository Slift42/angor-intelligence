"""Flux RSS propres des médias du catalogue (v0.28, run 3) : remplacement progressif de Google News.

Le robots.txt de news.google.com interdit aux robots les recherches RSS utilisées par les connecteurs « gnews » et
« outlets ». Ce connecteur lit directement le flux de chaque média du catalogue (config/press_outlets.json), dans le
respect du robots.txt de chaque site (veille/robots.py).

Deux temps à chaque collecte :
1. Découverte : pour quelques dizaines de médias pas encore examinés, recherche du flux annoncé par la page d'accueil
   (<link rel="alternate" type="application/rss+xml">), puis des adresses usuelles (/feed/, /rss, /rss.xml…). Un flux
   est retenu s'il contient au moins 3 articles. Un média sans flux est réexaminé au bout de `recheck_days` jours.
2. Lecture : les flux trouvés sont lus par roulement (`feeds_per_run` par collecte, en parallèle). Les titres passent
   ensuite par le tri de la presse (veille/press.py), comme ceux des autres flux.

Médias « + » du catalogue (internationaux, interrogés avec le nom du pays) : écartés, leur flux général couvre le
monde entier et ne dit rien du pays. Titre, lien et chapeau (300 caractères) uniquement, jamais l'article.
"""
import html
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

from .. import config, http
from ..robots import RobotsDisallowed
from .rss import TAG_RE, _items, parse_xml

KIND = "events"
CANDIDATES = ["/feed/", "/rss", "/rss.xml", "/feed", "/index.xml", "/rss/", "/feed.xml", "/atom.xml", "/?feed=rss2"]
MIN_ITEMS = 3
_LINK_RE = re.compile(r"<link\b[^>]*>", re.I)
_ATTR_RE = re.compile(r'([a-zA-Z-]+)\s*=\s*["\']([^"\']*)["\']')


def outlets(catalog):
    """Médias examinés : [(iso, nom, domaine, langue, cotation)] – hors médias internationaux « + »."""
    out = []
    for iso, rows in sorted(catalog.items()):
        for o in rows:
            if len(o) > 3 and o[3] == "+":
                continue
            out.append((iso, o[0], o[1], o[2] if len(o) > 2 else "", o[4] if len(o) > 4 else ""))
    return out


def feed_links(page, base):
    """Flux annoncés par une page d'accueil (balises <link rel="alternate">), adresses absolues."""
    found = []
    for tag in _LINK_RE.findall(page or ""):
        a = {k.lower(): v for k, v in _ATTR_RE.findall(tag)}
        if "alternate" not in a.get("rel", "").lower() or not re.search(r"rss|atom", a.get("type", ""), re.I):
            continue
        href = html.unescape(a.get("href", "")).strip()
        if not href or "comments" in href.lower():
            continue
        href = urljoin(base, href)
        if href not in found:
            found.append(href)
    return found


def _count_items(content):
    try:
        return sum(1 for it in _items(parse_xml(content)) if it.get("title"))
    except Exception:
        return 0


def discover(domain, get=None):
    """Adresse du flux d'un média, ou ("", motif). `get` : fonction de lecture (tests)."""
    get = get or (lambda u: http.get(u, retries=0, timeout=12, robots=True))
    base = "https://" + domain.strip("/")
    tried, answered = [], False
    try:
        home = get(base + "/")
        answered = True
        links = feed_links(home.text[:400000], str(getattr(home, "url", "") or base + "/"))
    except RobotsDisallowed:
        return "", "robots.txt"
    except Exception as exc:
        answered = getattr(exc, "response", None) is not None
        links = []
    for url in links[:3] + [base + c for c in CANDIDATES]:
        if url in tried or len(tried) >= 8:
            continue
        tried.append(url)
        try:
            r = get(url)
            answered = True
        except RobotsDisallowed:
            continue
        except Exception as exc:
            answered = answered or getattr(exc, "response", None) is not None
            continue
        if _count_items(r.content) >= MIN_ITEMS:
            return url, ""
    # aucun serveur n'a répondu (panne réseau, site hors ligne) : nouvel essai dans quelques jours, pas dans un mois
    return "", "aucun flux" if answered else "injoignable"


def _parse_items(content, iso, name, domain, lang, rel, now, max_age, max_items):
    out = []
    for it in list(_items(parse_xml(content)))[:max_items]:
        title = re.sub(r"\s+", " ", TAG_RE.sub("", html.unescape(it["title"] or ""))).strip()
        if not title:
            continue
        date = it["date"] or now
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        if now - date > max_age:
            continue
        snippet = html.unescape(re.sub(r"\s+", " ", TAG_RE.sub(" ", html.unescape(it.get("desc") or "")))).strip()
        if snippet.lower().startswith(title.lower()[:40]):
            snippet = snippet[len(title):].strip(" .:-–")
        out.append({"title": title, "url": it["link"], "outlet": name, "date": date, "country_hint": iso, "lang": lang,
                    "feed": "Flux des médias", "site": domain.split("/")[0].lower().removeprefix("www."),
                    "snippet": snippet[:300] if len(snippet) >= 40 else ""})
    return out


def summary(state, catalog):
    """Bilan pour l'état des sources : médias examinés, flux trouvés, pays couverts (v0.28)."""
    mem = (state or {}).get("outlet_feeds") or {}
    rows = outlets(catalog)
    checked = [r for r in rows if r[2] in mem]
    with_feed = [r for r in checked if mem[r[2]].get("f")]
    countries = {r[0] for r in rows}
    covered = {r[0] for r in with_feed}
    return {"outlets": len(rows), "checked": len(checked), "feeds": len(with_feed),
            "robots": sum(1 for r in checked if mem[r[2]].get("w") == "robots.txt"),
            "countries": len(countries), "covered": len(covered)}


def fetch(cfg, ctx):
    catalog = (config.load_json(cfg.get("catalog", "press_outlets.json"), {}) or {}).get("countries", {})
    if not catalog:
        raise ValueError("catalogue config/press_outlets.json introuvable ou vide")
    rows = outlets(catalog)
    mem = ctx.state.setdefault("outlet_feeds", {})
    known = {r[2] for r in rows}
    for d in [d for d in mem if d not in known]:   # médias retirés du catalogue
        del mem[d]
    now = ctx.now
    stamp = now.replace(microsecond=0).isoformat()
    workers = int(cfg.get("workers", 8))
    recheck = timedelta(days=int(cfg.get("recheck_days", 30)))

    # 1. découverte
    retry = timedelta(days=int(cfg.get("unreachable_retry_days", 3)))

    def due(d):
        m = mem.get(d)
        wait = retry if (m or {}).get("w") == "injoignable" else recheck
        return not m or (not m.get("f") and now - datetime.fromisoformat(m["t"]) > wait)
    todo = list(dict.fromkeys(r[2] for r in rows if due(r[2])))[: int(cfg.get("discover_per_run", 40))]
    t0 = time.time()
    found = 0
    if todo:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for d, (url, why) in zip(todo, pool.map(discover, todo)):
                mem[d] = {"f": url, "t": stamp, "w": why, "k": 0}
                found += bool(url)
        ctx.log(f"  Flux des médias : {len(todo)} média(s) examiné(s), {found} flux trouvé(s) ({time.time() - t0:.0f} s)")

    # 2. lecture par roulement
    feeds = [r for r in rows if (mem.get(r[2]) or {}).get("f")]
    if not feeds:
        return []
    per_run = int(cfg.get("feeds_per_run", 150))
    start = int(ctx.state.get("outlet_feeds_cursor", 0)) % len(feeds)
    batch = [feeds[(start + i) % len(feeds)] for i in range(min(per_run, len(feeds)))]
    max_age = timedelta(hours=int(cfg.get("max_age_hours", 48)))
    max_items = int(cfg.get("max_items", 30))

    def read(r):
        try:
            return r, http.get(mem[r[2]]["f"], retries=0, timeout=15, robots=True).content, None
        except Exception as exc:
            return r, None, exc
    ok = fails = titles = 0
    t1 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for r, content, exc in pool.map(read, batch):
            m = mem[r[2]]
            try:
                if exc:
                    raise exc
                items = _parse_items(content, r[0], r[1], r[2], r[3], r[4], now, max_age, max_items)
            except Exception as err:
                fails += 1
                m["k"] = m.get("k", 0) + 1
                if isinstance(err, RobotsDisallowed) or m["k"] >= 5:   # flux perdu : nouvelle découverte plus tard
                    m.update(f="", t=stamp, w="robots.txt" if isinstance(err, RobotsDisallowed) else "flux en échec")
                continue
            m["k"] = 0
            ok += 1
            titles += len(items)
            ctx.press.extend(items)
    ctx.state["outlet_feeds_cursor"] = (start + len(batch)) % len(feeds)
    ctx.log(f"  Flux des médias : {ok}/{len(batch)} flux lus ({len(feeds)} connus), {titles} titre(s) récent(s), "
            f"{fails} échec(s) ({time.time() - t1:.0f} s)")
    return []
