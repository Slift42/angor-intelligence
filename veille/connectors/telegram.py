"""Canaux Telegram publics (aperçu web t.me/s/<canal>, sans compte ni clé).

Dans beaucoup de zones de conflit (Russie, Ukraine, Soudan, Sahel, Moyen-Orient), l'information circule
d'abord sur Telegram. Seuls les canaux PUBLICS sont lus, via la page d'aperçu que Telegram publie pour
tout le monde. Les messages passent ensuite par le même tri que la presse (mots-clés 12 langues ou IA)
et sont marqués « réseaux sociaux – non vérifié », confiance faible.

Options (config/sources.json) :
  "channels": [{"name": "meduzalive", "country": "RU", "lang": "ru", "label": "Meduza"}, …]
  "max_age_hours": 48, "max_items_per_channel": 20
⚠ Choisir des canaux de médias ou d'ONG identifiés. Un canal de belligérant = propagande : à ne suivre
   qu'en connaissance de cause (et à signaler comme tel dans "label").
"""
import html
import re
from datetime import datetime, timedelta

from .. import http

KIND = "events"
URL = "https://t.me/s/{name}"
POST_RE = re.compile(r'data-post="([^"]+)"')
TEXT_RE = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
TIME_RE = re.compile(r'<time[^>]*datetime="([^"]+)"')


def messages(page):
    """[(post, texte html, date iso)] – un bloc par message."""
    out = []
    for block in page.split('class="tgme_widget_message_wrap')[1:]:
        p, b, w = POST_RE.search(block), TEXT_RE.search(block), TIME_RE.search(block)
        if p and w:
            out.append((p.group(1), b.group(1) if b else "", w.group(1)))
    return out
TAG_RE = re.compile(r"<[^>]+>")


def _clean(fragment):
    text = re.sub(r"<br\s*/?>", " ", fragment or "")
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", text))).strip()


def fetch(cfg, ctx):
    max_age = timedelta(hours=int(cfg.get("max_age_hours", 48)))
    per = int(cfg.get("max_items_per_channel", 20))
    ok = 0
    for ch in cfg.get("channels", []):
        name = ch["name"].lstrip("@")
        try:
            page = http.get(URL.format(name=name), retries=1, timeout=20).text
        except Exception as exc:
            ctx.log(f"  Telegram @{name} : {type(exc).__name__}")
            continue
        ok += 1
        for post, body, when in messages(page)[-per:]:
            text = _clean(body)
            if len(text) < 25:
                continue
            try:
                date = datetime.fromisoformat(when.replace("Z", "+00:00"))
            except ValueError:
                continue
            if ctx.now - date > max_age:
                continue
            title = text if len(text) <= 180 else text[:177].rsplit(" ", 1)[0] + "…"
            ctx.press.append({"title": title, "url": f"https://t.me/{post}", "outlet": f"Telegram · {ch.get('label') or '@' + name}",
                              "date": date, "country_hint": ch.get("country"), "lang": ch.get("lang", ""),
                              "feed": "Telegram", "snippet": text[:300] if len(text) > 180 else "", "social": True})
    if not ok and cfg.get("channels"):
        raise RuntimeError("aucun canal Telegram joignable")
    return []
