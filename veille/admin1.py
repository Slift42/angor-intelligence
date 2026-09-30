"""Noms et centres des régions administratives (niveau 1 : régions, États, provinces, gouvernorats).

Sert à placer sur la carte un titre qui ne cite qu'une province (« attaque dans le Tillabéri », « combats au
Darfour-Nord ») : précision « région » au lieu de rester sans coordonnées.
Source : geoBoundaries (William & Mary geoLab, CC BY 4.0), téléchargé pays par pays au premier besoin,
réduit à {nom, centre} et gardé dans data/admin1/<ISO2>.json (quelques Ko par pays).
"""
import json
import re
import unicodedata
from pathlib import Path

from . import http

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "admin1"
GB_URL = ("https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/"
          "{iso3}/ADM1/geoBoundaries-{iso3}-ADM1_simplified.geojson")
GENERIC = r"\b(region|state|province|governorate|prefecture|department|departement|oblast|county|district|division|" \
          r"territory|wilaya|muhafazah|estado|provincia|departamento|regiao|land|kraj|voivodeship|municipality|" \
          r"city|capital|federal|autonomous|special|of|the|de|du|des|la|le|el|al)\b"
DIRECTIONS = {"north", "south", "east", "west", "northern", "southern", "eastern", "western", "central", "centre",
              "center", "upper", "lower", "middle", "nord", "sud", "est", "ouest", "norte", "sur", "este", "oeste",
              "coast", "coastal", "islands", "capital", "greater", "new"}
_cache = {}
_country_keys = set()
_fetched = 0
MAX_FETCH_PER_RUN = 15


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9' -]+", " ", s).replace("-", " ").strip()


def _key(name):
    k = re.sub(GENERIC, " ", _norm(name))
    return re.sub(r"\s+", " ", k).strip()


def _centroid(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    best, area = None, -1
    for p in polys:
        ring = p[0]
        a = abs(sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1] for i in range(len(ring) - 1))) / 2
        if a > area:
            best, area = ring, a
    xs, ys = [pt[0] for pt in best], [pt[1] for pt in best]
    return round(sum(ys) / len(ys), 4), round(sum(xs) / len(xs), 4)


def regions(countries, iso, log=None):
    """[(clé normalisée, nom, lat, lon)] pour un pays ; [] si indisponible."""
    global _fetched
    if iso in _cache:
        return _cache[iso]
    path = DIR / f"{iso}.json"
    rows = None
    if path.exists():
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            rows = None
    if rows is None:
        item = countries.get(iso) if countries else None
        if not item or _fetched >= MAX_FETCH_PER_RUN:
            return []  # réessayé à la prochaine collecte
        _fetched += 1
        try:
            gj = http.get_json(GB_URL.format(iso3=item["iso3"]), timeout=60, retries=0)
            rows = []
            for f in gj.get("features", []):
                name = (f.get("properties") or {}).get("shapeName") or ""
                if name and f.get("geometry"):
                    lat, lon = _centroid(f["geometry"])
                    rows.append([name, lat, lon])
        except Exception as exc:
            if log:
                log(f"  Régions de {iso} indisponibles ({type(exc).__name__})")
            rows = []
        DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    if not _country_keys and countries:
        for it in countries.items:
            for n in (it.get("name_en"), it.get("name_fr")):
                if n:
                    _country_keys.add(_norm(n))
    out = []
    for name, lat, lon in rows:
        for k in {_key(name), _norm(name)}:
            words = set(k.split())
            if len(k) >= 5 and not k.isdigit() and not words <= DIRECTIONS and k not in _country_keys:
                out.append((k, name, lat, lon))
    out.sort(key=lambda r: -len(r[0]))  # « darfur nord » avant « darfur »
    _cache[iso] = out
    return out


def find(text, iso, countries, log=None):
    """Région citée dans le texte (mot entier) : {place, lat, lon, precision: "region"} ou None."""
    if not text or not iso:
        return None
    raw = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower().replace("darfour", "darfur")
    d = {"nord": "north", "sud": "south", "est": "east", "ouest": "west"}
    # « Nord-Kivu » → « north kivu », « Darfour-Nord » → « north darfur » (noms anglais de geoBoundaries)
    raw = re.sub(r"\b(nord|sud|ouest)-(\w+)", lambda m: f"{d[m.group(1)]} {m.group(2)} {m.group(0)}", raw)
    raw = re.sub(r"\b(\w+)-(nord|sud|est|ouest)\b", lambda m: f"{d[m.group(2)]} {m.group(1)} {m.group(0)}", raw)
    t = " " + re.sub(r"\s+", " ", _norm(raw)) + " "
    for k, name, lat, lon in regions(countries, iso, log):
        if f" {k} " in t:
            return {"place": name, "lat": lat, "lon": lon, "precision": "region"}
    return None
