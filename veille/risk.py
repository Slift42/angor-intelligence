"""Note de risque pays, de 1 (Minimal) à 5 (Extrême).

Méthode transparente et réglable (config/risk.json) :
  score = poids_avis × avis officiels + poids_securite × activité sécuritaire récente
        + poids_aleas × catastrophes et épidémies récentes          (score entre 0 et 1)

- Avis officiels : moyenne des niveaux des gouvernements (US 1-4, Canada 1-4…), ramenés entre 0 et 1.
- Activité sécuritaire : événements « sécurité » et « politique » des N derniers jours, pondérés
  par gravité et par confiance (une détection automatique compte moitié), sur une échelle logarithmique (quelques incidents graves pèsent plus que beaucoup de mineurs).
- Aléas : idem pour les catégories naturelles et sanitaires.
Plancher : un pays déconseillé formellement par au moins un gouvernement (niveau 4/4) est
au minimum « Élevé ».

C'est un indicateur automatique d'aide à la décision : votre expertise d'analyste peut le corriger
via "overrides" dans config/risk.json.
"""
import math
from datetime import timedelta

from .model import CATEGORIES, parse_iso

DEFAULTS = {
    "weights": {"advisories": 0.6, "security": 0.3, "hazards": 0.1},
    "window_days": 7,
    "severity_points": {"1": 1, "2": 3, "3": 8, "4": 20},
    "saturation_points": 150,
    "thresholds": [0.15, 0.35, 0.55, 0.75],
    "overrides": {},
    "confidence_weights": {"low": 0.3, "medium": 0.6, "high": 1.0},
    "auto_detected_weight": 0.5,
}


def _activity(points, saturation):
    return min(1.0, math.log1p(points) / math.log1p(saturation)) if points else 0.0


def compute(events, advisories, now, cfg=None):
    cfg = {**DEFAULTS, **(cfg or {})}
    w = cfg["weights"]
    pts = {int(k): v for k, v in cfg["severity_points"].items()}
    since = now - timedelta(days=cfg["window_days"])

    cw = cfg["confidence_weights"]
    sec, haz, counts = {}, {}, {}
    for ev in events:
        iso = ev.get("country")
        if not iso or parse_iso(ev["date"]) < since:
            continue
        group = CATEGORIES.get(ev["category"], {}).get("group")
        if group == "diplomatic":  # signal politique, pas une menace physique : hors note de risque
            continue
        c = counts.setdefault(iso, {"security": 0, "hazards": 0})
        weight = cw.get(ev.get("confidence", "high"), 1.0)
        if "auto-detected" in ev.get("tags", []):
            weight *= cfg["auto_detected_weight"]
        value = pts.get(ev["severity"], 1) * weight
        if group in ("security", "political"):
            sec[iso] = sec.get(iso, 0) + value
            c["security"] += 1
        else:
            haz[iso] = haz.get(iso, 0) + value
            c["hazards"] += 1

    isos = set(sec) | set(haz)
    for per_source in advisories.values():
        isos |= set(per_source)

    out = {}
    for iso in isos:
        advs = {src: a[iso] for src, a in advisories.items() if iso in a}
        adv_norm = [(a["level"] - 1) / (a.get("scale", 4) - 1) for a in advs.values()]
        adv = sum(adv_norm) / len(adv_norm) if adv_norm else None
        s = _activity(sec.get(iso, 0), cfg["saturation_points"])
        h = _activity(haz.get(iso, 0), cfg["saturation_points"])
        if adv is None:
            total_w = w["security"] + w["hazards"]
            score = (w["security"] * s + w["hazards"] * h) / total_w
        else:
            score = w["advisories"] * adv + w["security"] * s + w["hazards"] * h
        level = 1 + sum(score >= t for t in cfg["thresholds"])
        if adv_norm and max(adv_norm) >= 1.0:
            level = max(level, 4)
        basis = "computed"
        if iso in cfg["overrides"]:
            level, basis = int(cfg["overrides"][iso]), "analyst"
        out[iso] = {
            "level": level, "score": round(score, 3), "basis": basis,
            "components": {"advisories": None if adv is None else round(adv, 3),
                           "security": round(s, 3), "hazards": round(h, 3)},
            "counts": counts.get(iso, {"security": 0, "hazards": 0}),
            "advisories": advs,
            "data_quality": "advisories+events" if adv is not None else "events-only",
        }
    return out
