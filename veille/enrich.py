"""Enrichissement : titre de l'article source pour les détections GDELT.

GDELT ne fournit que des codes (« Military force – Balochistan »). On va lire le titre de l'article
source (balise og:title ou <title>) pour donner une description lisible de l'incident.
Seul le titre est conservé (droit d'auteur). Résultats mis en cache pour ne jamais relire deux fois.
"""
import html
import re
from concurrent.futures import ThreadPoolExecutor

from . import http

OG_RE = re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', re.I)
OG_RE2 = re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title', re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
SUFFIX_RE = re.compile(r"\s+[|\-–—:]\s+[^|\-–—:]{2,40}$")


def _fetch_title(url):
    try:
        r = http.get(url, retries=0, timeout=6, headers={"Range": "bytes=0-150000"})
        text = r.content[:150000].decode(r.encoding or "utf-8", errors="replace")
    except Exception:
        return ""
    m = OG_RE.search(text) or OG_RE2.search(text) or TITLE_RE.search(text)
    if not m:
        return ""
    title = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
    title = SUFFIX_RE.sub("", title).strip()
    return title if 15 <= len(title) <= 300 else ""


def add_headlines(events, cache, log, max_fetch=150, workers=8):
    todo = []
    for ev in events:
        if ev.get("headline") or ev["source"] != "GDELT":
            continue
        urls = [s["url"] for s in ev.get("sources", [])[:2] if s.get("url")]
        cached = [cache[u] for u in urls if cache.get(u)]
        if cached:
            ev["headline"] = cached[0]
        elif any(u not in cache for u in urls):
            todo.append((ev, [u for u in urls if u not in cache]))
    todo = todo[:max_fetch]
    if not todo:
        return
    urls = sorted({u for _, us in todo for u in us})
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for url, title in zip(urls, pool.map(_fetch_title, urls)):
            cache[url] = title
    n = 0
    for ev, us in todo:
        for u in us:
            if cache.get(u):
                ev["headline"] = cache[u]
                n += 1
                break
    log(f"  Titres d'articles : {n}/{len(todo)} incidents GDELT décrits")
    if len(cache) > 8000:  # le cache ne grossit pas indéfiniment
        for k in list(cache)[: len(cache) - 6000]:
            del cache[k]
