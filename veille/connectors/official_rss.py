"""Bulletins officiels en RSS / Atom → incidents sur la carte (cotation A : organismes officiels).

Pour les flux d'institutions qui publient des alertes datées mais pas d'API : NOAA NHC (cyclones),
Smithsonian GVP (volcans, bulletin hebdomadaire), Copernicus EMS (activations de cartographie d'urgence),
PTWC / NTWC (tsunamis), etc.

Options (config/sources.json) :
  "url"        : adresse du flux
  "source"     : nom court affiché (ex. "NOAA NHC")
  "category"   : catégorie fixe (ex. "cyclone"), ou "auto" (déduite du titre, voir AUTO_CATEGORY)
  "severity"   : gravité par défaut (1 à 4) ; "severity_words" : {"hurricane": 3, "warning": 4} (le plus élevé l'emporte)
  "keep"       : expression régulière – seuls les titres correspondants sont gardés (ex. "Public Advisory")
  "drop"       : expression régulière – titres écartés
  "keep_desc"  : expression régulière que le résumé doit contenir (ex. « Category: (Advisory|Watch|Warning) »)
  "title_prefix": texte ajouté devant le titre (ex. « Tsunami – »)
  "geo"        : "georss" (coordonnées dans le flux), "text" (lat/lon écrits dans le texte, ex. « 25.3N 70.1W »),
                 "country" (pays cité dans le titre : « … , Spain », « Krakatau (Indonesia) ») ; plusieurs
                 méthodes sont essayées dans l'ordre georss → text → country
  "max_age_days": ancienneté maximale (défaut 10)
Titre, lien et résumé court uniquement."""
import hashlib
import html
import re
import xml.etree.ElementTree as ET
from datetime import timedelta

from .. import http
from ..model import make_event, to_iso
from .rss import TAG_RE, _date, _local

KIND = "events"
AUTO_CATEGORY = [("flood", r"flood|inondation|crue"), ("wildfire", r"wildfire|forest fire|incendie|fire"),
                 ("earthquake", r"earthquake|séisme|seisme|tsunami"), ("cyclone", r"cyclone|hurricane|typhoon|tropical storm"),
                 ("storm", r"storm|tempête|tornado"), ("landslide", r"landslide|glissement|mudslide"),
                 ("volcano", r"volcan|eruption"), ("infrastructure", r"explosion|industrial|dam |collapse"),
                 ("health", r"outbreak|epidemic|ebola|cholera|disease"), ("extreme_temp", r"heat|drought|canicule")]
LATLON_RE = re.compile(r"(\d{1,2}(?:\.\d+)?)\s*°?\s*([NS])[\s,/]+(\d{1,3}(?:\.\d+)?)\s*°?\s*([EW])")
LATLON2_RE = re.compile(r"Lat/Lon:\s*(-?\d+(?:\.\d+)?)\s*/\s*(-?\d+(?:\.\d+)?)")


def _entries(root):
    for el in root.iter():
        kind = _local(el.tag)
        if kind not in ("item", "entry"):
            continue
        d = {"title": "", "link": "", "desc": "", "date": None, "lat": None, "lon": None, "id": ""}
        for c in el:
            name, txt = _local(c.tag), (c.text or "").strip()
            if name == "title":
                d["title"] = txt
            elif name == "link":
                d["link"] = d["link"] or c.get("href") or txt
            elif name in ("description", "summary", "content") and not d["desc"]:
                d["desc"] = txt or "".join(c.itertext())
            elif name in ("pubDate", "updated", "published", "date") and not d["date"]:
                d["date"] = _date(txt)
            elif name in ("guid", "id"):
                d["id"] = txt
            elif name == "point" and txt:  # georss:point « lat lon »
                parts = txt.replace(",", " ").split()
                if len(parts) >= 2:
                    d["lat"], d["lon"] = float(parts[0]), float(parts[1])
            elif name == "lat" and txt:
                d["lat"] = float(txt)
            elif name in ("long", "lon") and txt:
                d["lon"] = float(txt)
        yield d


def _category(cfg, text):
    cat = cfg.get("category", "auto")
    if cat != "auto":
        return cat
    low = text.lower()
    for c, rx in AUTO_CATEGORY:
        if re.search(rx, low):
            return c
    return None


def _severity(cfg, text):
    sev = int(cfg.get("severity", 2))
    low = text.lower()
    for word, s in (cfg.get("severity_words") or {}).items():
        if word.lower() in low:
            sev = max(sev, int(s))
    return min(sev, 4)


def _country(ctx, title):
    """Pays cité en fin de titre : « Wildfire in Huelva Province, Spain », « Krakatau (Indonesia) »."""
    cands = re.findall(r"\(([^()]+)\)", title) + [title.split(",")[-1], title.split(" in ")[-1], title.split(" - ")[-1]]
    for c in cands:
        c = re.sub(r"[^\w\s'’-]", " ", c).strip()
        for n in (c, " ".join(c.split()[-2:]), c.split()[-1] if c.split() else ""):
            item = ctx.countries.by_country_name(n) if n else None
            if item:
                return item
    return None


def fetch(cfg, ctx):
    r = (getattr(ctx, "prefetch", None) or {}).get(cfg["url"])
    if isinstance(r, Exception):
        raise r
    if r is None:
        r = http.get(cfg["url"], retries=1, timeout=30)
    root = ET.fromstring(r.content)
    keep = re.compile(cfg["keep"], re.I) if cfg.get("keep") else None
    drop = re.compile(cfg["drop"], re.I) if cfg.get("drop") else None
    max_age = timedelta(days=int(cfg.get("max_age_days", 10)))
    source = cfg.get("source") or cfg.get("name", cfg["id"])
    out = []
    for it in list(_entries(root))[: int(cfg.get("max_items", 60))]:
        title = re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", it["title"]))).strip()
        desc = re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", html.unescape(it["desc"] or "")))).strip()
        if not title or (keep and not keep.search(title)) or (drop and drop.search(title)):
            continue
        if cfg.get("keep_desc") and not re.search(cfg["keep_desc"], desc, re.I):
            continue
        title = (cfg.get("title_prefix") or "") + title
        date = it["date"] or ctx.now
        if ctx.now - date > max_age:
            continue
        text = f"{title} {desc}"
        cat = _category(cfg, text)
        if not cat:
            continue
        lat, lon, precision, iso, place = it["lat"], it["lon"], "exact", None, ""
        if lat is None:
            m = LATLON2_RE.search(desc) or None
            if m:
                lat, lon = float(m.group(1)), float(m.group(2))
            else:
                m = LATLON_RE.search(text)
                if m:
                    lat = float(m.group(1)) * (1 if m.group(2) == "N" else -1)
                    lon = float(m.group(3)) * (1 if m.group(4) == "E" else -1)
        if lat is not None:
            iso = ctx.countries.locate(lat, lon)
        else:
            item = _country(ctx, title)
            if not item:
                continue
            lat, lon = item["label"][1], item["label"][0]
            iso, precision, place = item["iso2"], "country", item["name_en"]
        uid = hashlib.sha1((it["id"] or it["link"] or title).encode()).hexdigest()[:12]
        out.append(make_event(
            id=f"{cfg['id']}-{uid}", source=source, category=cat, severity=_severity(cfg, text), title=title,
            summary=desc[:280], date=to_iso(date), lat=lat, lon=lon, url=it["link"] or cfg["url"],
            place=place or title.split(",")[0][:80], precision=precision, country=iso))
    return out
