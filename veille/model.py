"""Format d'événement standard et taxonomie.

Chaque source est traduite vers ce format unique, le seul que la carte connaisse.
Les libellés sont bilingues (fr/en) ; le contenu (titres) est restitué en anglais.
"""
from datetime import datetime, timezone

# Gravité d'un événement : 1 à 4
SEVERITY = {
    1: {"fr": "Faible", "en": "Low"},
    2: {"fr": "Modérée", "en": "Moderate"},
    3: {"fr": "Élevée", "en": "High"},
    4: {"fr": "Critique", "en": "Critical"},
}

# Niveau de risque pays : 1 à 5 (échelle des grands acteurs : Minimal → Extrême)
RISK_LEVELS = {
    1: {"fr": "Minimal", "en": "Minimal",
        "desc_fr": "Environnement favorable, menaces isolées.",
        "desc_en": "Benign environment, isolated threats."},
    2: {"fr": "Faible", "en": "Low",
        "desc_fr": "Environnement globalement permissif, précautions de base.",
        "desc_en": "Generally permissive, basic precautions."},
    3: {"fr": "Modéré", "en": "Moderate",
        "desc_fr": "Menaces sérieuses nécessitant des mesures d'atténuation.",
        "desc_en": "Serious threats requiring some mitigation."},
    4: {"fr": "Élevé", "en": "High",
        "desc_fr": "Environnement hostile, planification sûreté complète.",
        "desc_en": "Hostile environment, comprehensive security planning."},
    5: {"fr": "Extrême", "en": "Extreme",
        "desc_fr": "Menaces directes et généralisées, déplacements à proscrire sauf nécessité impérative.",
        "desc_en": "Pervasive direct threats; travel only if essential."},
}

GROUPS = {
    "security": {"fr": "Sécurité & conflits", "en": "Security & conflict"},
    "political": {"fr": "Politique & troubles", "en": "Political & unrest"},
    "natural": {"fr": "Catastrophes naturelles", "en": "Natural hazards"},
    "health": {"fr": "Santé", "en": "Health"},
    "infrastructure": {"fr": "Infrastructures & cyber", "en": "Infrastructure & cyber"},
}

CATEGORIES = {
    "armed_conflict": {"group": "security", "icon": "swords", "fr": "Conflit armé", "en": "Armed conflict"},
    "attack": {"group": "security", "icon": "bomb", "fr": "Attaque / attentat", "en": "Attack / bombing"},
    "terrorism": {"group": "security", "icon": "crosshair", "fr": "Terrorisme", "en": "Terrorism"},
    "crime": {"group": "security", "icon": "siren", "fr": "Criminalité", "en": "Crime"},
    "unrest": {"group": "political", "icon": "megaphone", "fr": "Troubles civils", "en": "Civil unrest"},
    "political": {"group": "political", "icon": "building-2", "fr": "Crise politique", "en": "Political crisis"},
    "earthquake": {"group": "natural", "icon": "activity", "fr": "Séisme", "en": "Earthquake"},
    "cyclone": {"group": "natural", "icon": "tornado", "fr": "Cyclone", "en": "Tropical cyclone"},
    "storm": {"group": "natural", "icon": "cloud-lightning", "fr": "Tempête", "en": "Severe storm"},
    "flood": {"group": "natural", "icon": "waves", "fr": "Inondation", "en": "Flood"},
    "wildfire": {"group": "natural", "icon": "flame", "fr": "Feu de forêt", "en": "Wildfire"},
    "volcano": {"group": "natural", "icon": "mountain", "fr": "Volcan", "en": "Volcano"},
    "drought": {"group": "natural", "icon": "sun", "fr": "Sécheresse", "en": "Drought"},
    "landslide": {"group": "natural", "icon": "mountain-snow", "fr": "Glissement de terrain", "en": "Landslide"},
    "extreme_temp": {"group": "natural", "icon": "thermometer", "fr": "Température extrême", "en": "Extreme temperature"},
    "health": {"group": "health", "icon": "biohazard", "fr": "Épidémie", "en": "Disease outbreak"},
    "cyber": {"group": "infrastructure", "icon": "radio-tower", "fr": "Cyber", "en": "Cyber"},
    "infrastructure": {"group": "infrastructure", "icon": "building-2", "fr": "Infrastructure", "en": "Infrastructure"},
    "other": {"group": "natural", "icon": "circle-alert", "fr": "Autre", "en": "Other"},
}

# Précision de la localisation (du plus précis au moins précis)
PRECISION = ("exact", "city", "region", "country")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def to_iso(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(value):
    """Lit une date ISO 8601 (avec ou sans 'Z' / fuseau). Sans fuseau → UTC."""
    if not value:
        return None
    value = value.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def make_event(*, id, source, category, severity, title, date, lat, lon, url,
               summary="", start=None, precision="exact", place="", country=None,
               confidence="high", source_url=None, tags=None):
    """Construit un événement au format standard. Les champs obligatoires sont nommés."""
    if category not in CATEGORIES:
        category = "other"
    severity = max(1, min(4, int(severity)))
    return {
        "id": id,
        "source": source,
        "sources": [{"name": source, "url": source_url or url}],
        "category": category,
        "severity": severity,
        "title": title.strip(),
        "summary": (summary or "").strip(),
        "date": date,
        "start": start or date,
        "lat": round(float(lat), 4),
        "lon": round(float(lon), 4),
        "precision": precision,
        "place": place or "",
        "country": country,
        "url": url,
        "confidence": confidence,
        "tags": tags or [],
    }


def taxonomy():
    """Exporté vers la carte pour que libellés et icônes aient une seule source de vérité."""
    return {"severity": SEVERITY, "risk_levels": RISK_LEVELS, "groups": GROUPS, "categories": CATEGORIES}
