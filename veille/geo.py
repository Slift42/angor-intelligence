"""Outils géographiques sans dépendance externe.

- Rattachement d'un point à un pays (point-dans-polygone sur Natural Earth simplifié)
- Recherche d'un pays par nom (anglais, français, alias) ou par code
- Distance entre deux points (formule de haversine)
"""
import json
import math
import re
import unicodedata

from .config import ROOT

COUNTRIES_JS = ROOT / "docs" / "data" / "countries.js"

# Noms utilisés par certaines sources et absents de Natural Earth
ALIASES = {
    "burma": "MM", "myanmar (burma)": "MM", "cote d'ivoire": "CI", "ivory coast": "CI",
    "the bahamas": "BS", "bahamas, the": "BS", "the gambia": "GM", "gambia, the": "GM",
    "democratic republic of the congo": "CD", "dr congo": "CD", "drc": "CD",
    "congo, democratic republic of the": "CD", "republic of the congo": "CG", "congo": "CG",
    "congo, republic of the": "CG", "north korea": "KP", "korea, north": "KP",
    "democratic people's republic of korea": "KP", "south korea": "KR", "korea, south": "KR",
    "republic of korea": "KR", "russia": "RU", "russian federation": "RU", "syria": "SY",
    "syrian arab republic": "SY", "iran": "IR", "iran (islamic republic of)": "IR",
    "laos": "LA", "lao people's democratic republic": "LA", "vietnam": "VN", "viet nam": "VN",
    "tanzania": "TZ", "united republic of tanzania": "TZ", "bolivia": "BO",
    "bolivia (plurinational state of)": "BO", "venezuela": "VE",
    "venezuela (bolivarian republic of)": "VE", "moldova": "MD", "republic of moldova": "MD",
    "czechia": "CZ", "czech republic": "CZ", "turkiye": "TR", "turkey": "TR",
    "north macedonia": "MK", "macedonia": "MK", "eswatini": "SZ", "swaziland": "SZ",
    "cabo verde": "CV", "cape verde": "CV", "timor-leste": "TL", "east timor": "TL",
    "united states": "US", "united states of america": "US", "usa": "US",
    "united kingdom": "GB", "uk": "GB", "united kingdom of great britain and northern ireland": "GB",
    "micronesia": "FM", "federated states of micronesia": "FM", "brunei": "BN",
    "brunei darussalam": "BN", "palestinian territories": "PS", "west bank and gaza": "PS",
    "israel, the west bank and gaza": "IL", "occupied palestinian territory": "PS", "gaza": "PS",
    "vatican city": "VA", "holy see": "VA", "sao tome and principe": "ST",
    "saint kitts and nevis": "KN", "saint lucia": "LC", "saint vincent and the grenadines": "VC",
    "antigua and barbuda": "AG", "trinidad and tobago": "TT", "bosnia and herzegovina": "BA",
    "kyrgyz republic": "KG", "kyrgyzstan": "KG", "hong kong": "HK", "macau": "MO", "macao": "MO",
    "taiwan": "TW", "kosovo": "XK", "curacao": "CW", "south sudan": "SS",
    "central african republic": "CF", "equatorial guinea": "GQ", "guinea-bissau": "GW",
    "mainland china": "CN", "china": "CN", "people's republic of china": "CN",
}


def normalize(name):
    name = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    name = name.lower().strip()
    name = re.sub(r"\s+", " ", name)
    return name


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def km_to_segment(lat, lon, a, b):
    """Distance (km) d'un point au segment [a, b] (a, b = (lat, lon)), projection locale équirectangulaire."""
    k = math.cos(math.radians(lat))
    ax, ay = (a[1] - lon) * 111.32 * k, (a[0] - lat) * 110.57
    bx, by = (b[1] - lon) * 111.32 * k, (b[0] - lat) * 110.57
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
    return math.hypot(ax + t * dx, ay + t * dy)


def km_to_route(lat, lon, points):
    """Distance (km) d'un point à un trajet (liste de points [lat, lon])."""
    if len(points) == 1:
        return haversine_km(lat, lon, points[0][0], points[0][1])
    return min(km_to_segment(lat, lon, points[i], points[i + 1]) for i in range(len(points) - 1))


def distance_to(target, lat, lon):
    """Distance d'un événement à un site (point) ou à un trajet surveillé (« points »)."""
    if target.get("points"):
        return km_to_route(lat, lon, target["points"])
    return haversine_km(target["lat"], target["lon"], lat, lon)


def _point_in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


class Countries:
    def __init__(self, path=COUNTRIES_JS):
        text = path.read_text(encoding="utf-8")
        data = json.loads(text[text.index("{"): text.rstrip().rstrip(";").rindex("}") + 1])
        self.items = []
        self.by_iso2, self.by_iso3, self.by_fips, self.by_name = {}, {}, {}, {}
        for f in data["features"]:
            p = f["properties"]
            polys = f["geometry"]["coordinates"]
            xs = [pt[0] for poly in polys for pt in poly[0]]
            ys = [pt[1] for poly in polys for pt in poly[0]]
            item = dict(p, polys=polys, bbox=(min(xs), min(ys), max(xs), max(ys)))
            self.items.append(item)
            self.by_iso2.setdefault(p["iso2"], item)
            self.by_iso3.setdefault(p["iso3"], item)
            if p.get("fips"):
                self.by_fips.setdefault(p["fips"], item)
            for n in (p["name_en"], p["name_fr"]):
                if n:
                    self.by_name.setdefault(normalize(n), item)

    def locate(self, lat, lon):
        """Code ISO2 du pays contenant le point, ou None (en pleine mer).
        Les frontières étant simplifiées, une ville côtière peut tomber « à l'eau » :
        on teste alors des points voisins jusqu'à ~25 km."""
        found = self._locate(lat, lon)
        if found:
            return found
        for d in (0.12, 0.25):
            for dy, dx in ((d, 0), (-d, 0), (0, d), (0, -d), (d, d), (d, -d), (-d, d), (-d, -d)):
                found = self._locate(lat + dy, lon + dx)
                if found:
                    return found
        return None

    def _locate(self, lat, lon):
        for item in self.items:
            x0, y0, x1, y1 = item["bbox"]
            if not (x0 <= lon <= x1 and y0 <= lat <= y1):
                continue
            for poly in item["polys"]:
                if _point_in_ring(lon, lat, poly[0]) and not any(
                        _point_in_ring(lon, lat, hole) for hole in poly[1:]):
                    return item["iso2"]
        return None

    def by_country_name(self, name):
        key = normalize(name)
        if key in ALIASES:
            return self.by_iso2.get(ALIASES[key])
        return self.by_name.get(key)

    def get(self, iso2):
        return self.by_iso2.get(iso2)

    def name(self, iso2, lang="en"):
        item = self.by_iso2.get(iso2)
        return item[f"name_{lang}"] if item else iso2

    def label_point(self, iso2):
        item = self.by_iso2.get(iso2)
        return (item["label"][1], item["label"][0]) if item else None
