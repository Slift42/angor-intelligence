"""Conseils aux voyageurs du FCDO (Royaume-Uni) – texte détaillé par pays.

Source : API de contenu GOV.UK, Open Government Licence v3.0 (réutilisation libre, y compris commerciale,
avec la mention « Contains public sector information licensed under the Open Government Licence v3.0 »).
Le connecteur uk_advisories relit déjà chaque page modifiée ; ce module la découpe en rubriques
(terrorisme, criminalité, enlèvements, lois et usages, transports, catastrophes naturelles, santé, secours…)
et la garde dans data/fcdo/<ISO2>.json pour le rapport pays.
"""
import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "fcdo"
KEEP_PARTS = {"warnings-and-insurance": "warnings", "entry-requirements": "entry", "safety-and-security": "safety",
              "health": "health", "getting-help": "help"}
# rubriques propres au Royaume-Uni ou sans intérêt pour un lecteur non britannique
SKIP_HEAD = re.compile(r"uk government|travel insurance|about (the )?fcdo|travel advice updates|contact your travel provider|"
                       r"refunds|support from fcdo|help abroad|help in the uk|british (embassy|high commission|consulate)|"
                       r"mental health|dual national|passport validity|this advice|renewing|uk emergency travel|"
                       r"if you.re travelling from|get advice|consular|for british|british nationals", re.I)
SKIP_TEXT = re.compile(r"^(read |find out|see |sign up|your travel insurance could|check the latest|contact the british|for more (detail|information)|"
                       r"the foreign, commonwealth|fcdo cannot provide tailored)", re.I)


class _Parser(HTMLParser):
    """HTML GOV.UK → [{"h": titre, "l": niveau, "b": [["p", texte] | ["ul", [items]]]}]"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections = [{"h": "", "l": 1, "b": []}]
        self.buf, self.mode, self.items, self.depth_li = [], None, None, 0

    def handle_starttag(self, tag, attrs):
        if tag in ("h2", "h3", "h4"):
            self._flush()
            self.mode = tag
        elif tag == "p" and self.mode not in ("h2", "h3", "h4"):
            self._flush()
            self.mode = self.mode if self.mode == "li" else "p"
        elif tag in ("ul", "ol"):
            self._flush()
            self.items = []
        elif tag == "li":
            self._flush_li()
            self.mode = "li"
        elif tag == "br":
            self.buf.append(" ")

    def handle_endtag(self, tag):
        if tag in ("h2", "h3", "h4"):
            text = _clean("".join(self.buf))
            self.buf = []
            self.mode = None
            if text:
                self.sections.append({"h": text, "l": int(tag[1]), "b": []})
        elif tag == "p" and self.mode == "p":
            self._flush()
        elif tag == "li":
            self._flush_li()
        elif tag in ("ul", "ol"):
            self._flush_li()
            if self.items:
                self.sections[-1]["b"].append(["ul", self.items])
            self.items = None
            self.mode = None

    def handle_data(self, data):
        self.buf.append(data)

    def _flush_li(self):
        if self.mode == "li":
            text = _clean("".join(self.buf))
            if text and self.items is not None:
                self.items.append(text)
            self.buf = []
            self.mode = None

    def _flush(self):
        text = _clean("".join(self.buf))
        self.buf = []
        if self.mode == "li":
            if text and self.items is not None:
                self.items.append(text)
        elif text:
            self.sections[-1]["b"].append(["p", text])
        if self.mode != "li":
            self.mode = None

    def close(self):
        super().close()
        self._flush()
        return self.sections


def _clean(s):
    s = unescape(s or "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def parse_body(html):
    p = _Parser()
    p.feed(html or "")
    out = []
    skipping = 0
    for sec in p.close():
        if sec["l"] == 2:
            skipping = bool(SKIP_HEAD.search(sec["h"]))
        elif sec["l"] >= 3 and SKIP_HEAD.search(sec["h"]):
            continue
        if skipping:
            continue
        blocks = []
        for kind, val in sec["b"]:
            if kind == "p":
                if SKIP_TEXT.search(val) or len(val) < 3:
                    continue
                blocks.append(["p", val[:1200]])
            else:
                items = [x[:400] for x in val if not SKIP_TEXT.search(x)][:25]
                if items:
                    blocks.append(["ul", items])
        if blocks or (sec["h"] and sec["l"] == 2):
            out.append({"h": sec["h"], "l": sec["l"], "b": blocks})
    # titres sans contenu (sauf s'ils introduisent des sous-rubriques)
    cleaned = []
    for i, s in enumerate(out):
        nxt = out[i + 1] if i + 1 < len(out) else None
        if not s["b"] and not (nxt and nxt["l"] > s["l"]):
            continue
        cleaned.append(s)
    return cleaned


PHONE_RE = re.compile(r"(police|ambulance|fire|medical|emergency|tourist police|telephone|coast ?guard)[^:\d]{0,40}:?\s*"
                      r"((?:\+?\d[\d\s/-]{1,12}\d|\d{2,4})(?:\s*(?:or|/|,)\s*\d{2,6})*)(?:\s*\(([^)]{2,40})\))?", re.I)


def emergency(sections):
    """Numéros d'urgence cités dans « Emergency services in … » : [{"service", "number"}]."""
    out = []
    for s in sections:
        if not re.search(r"emergency services", s["h"], re.I):
            continue
        for kind, val in s["b"]:
            for line in (val if kind == "ul" else [val]):
                for m in PHONE_RE.finditer(line):
                    service = (m.group(3) or m.group(1)).strip().lower()
                    number = re.sub(r"\s+", " ", m.group(2)).strip(" ,/")
                    if service == "telephone":
                        service = "emergency"
                    if number and not any(o["number"] == number and o["service"] == service for o in out):
                        out.append({"service": service, "number": number})
    return out[:8]


def parse_page(page):
    d = page.get("details") or {}
    parts = {}
    for p in d.get("parts") or []:
        key = KEEP_PARTS.get(p.get("slug"))
        if key:
            parts[key] = parse_body(p.get("body"))
    return {"updated": page.get("public_updated_at") or d.get("updated_at"), "reviewed": d.get("reviewed_at"),
            "url": "https://www.gov.uk" + (page.get("base_path") or ""), "parts": parts,
            "emergency": emergency(parts.get("help", []))}


def save(iso, page):
    try:
        data = parse_page(page)
    except Exception:
        return None
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / f"{iso}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return data


def load(iso):
    path = DIR / f"{iso}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def has(iso):
    return (DIR / f"{iso}.json").exists()


def plain_text(data):
    """Tout le texte (pour chercher les mentions d'une ville)."""
    out = []
    for secs in (data or {}).get("parts", {}).values():
        for s in secs:
            for kind, val in s["b"]:
                out.extend(val if kind == "ul" else [val])
    return out
