"""Indice de stabilité « Pulse » par pays, de 0 (très instable) à 100 (stable), et ses causes.

Là où la note de risque (1 à 5) bouge lentement (avis officiels), le Pulse suit la dynamique :
    instabilité = 0,45 × avis officiels            (composante « advisories » de la note pays, 0 à 1)
                + 0,30 × activité sécuritaire 7 j   (composante « security », échelle log)
                + 0,15 × anomalie                   (incidents sécurité des 7 derniers jours / moyenne des 23 jours précédents)
                + 0,10 × catastrophes et santé 7 j  (composante « hazards »)
    Pulse = 100 × (1 − instabilité)
Historique quotidien conservé 120 jours (mémoire du robot) → tendance 7 j et 30 j, courbe sur 30 j.
Causes (« drivers ») : catégories dont le poids a le plus augmenté sur 7 jours, changement d'avis officiel.
Alertes Telegram (config/settings.json → "pulse") : chute d'au moins `drop_alert` points en 7 jours,
ou passage sous le seuil `threshold`, pour les pays suivis (ou tous si la liste est vide).
"""
from datetime import timedelta

from .model import CATEGORIES, parse_iso

SEC_GROUPS = ("security", "political")
PTS = {1: 1, 2: 3, 3: 8, 4: 20}
CONF = {"low": 0.3, "medium": 0.6, "high": 1.0}
DEFAULTS = {"threshold": 40, "drop_alert": 12, "countries": [], "alerts": True, "min_gap_days": 5}


def _weight(ev):
    w = PTS.get(ev["severity"], 1) * CONF.get(ev.get("confidence", "high"), 1.0)
    if "auto-detected" in (ev.get("tags") or []):
        w *= 0.5
    return w


def compute(events, country_risk, store, now):
    """Renvoie {iso: {value, d7, d30, spark, drivers, anomaly}} et met à jour l'historique."""
    hist = store.setdefault("state", {}).setdefault("pulse_hist", {})
    d7, d30 = now - timedelta(days=7), now - timedelta(days=30)
    recent, prior = {}, {}
    cats_recent, cats_prior = {}, {}
    for ev in events:
        iso = ev.get("country")
        if not iso:
            continue
        t = parse_iso(ev["date"])
        if t < d30:
            continue
        grp = CATEGORIES.get(ev["category"], {}).get("group")
        if grp == "diplomatic":
            continue
        w = _weight(ev)
        if t >= d7:
            if grp in SEC_GROUPS:
                recent[iso] = recent.get(iso, 0) + w
            cr = cats_recent.setdefault(iso, {})
            cr[ev["category"]] = cr.get(ev["category"], 0) + w
        else:
            if grp in SEC_GROUPS:
                prior[iso] = prior.get(iso, 0) + w
            cp = cats_prior.setdefault(iso, {})
            cp[ev["category"]] = cp.get(ev["category"], 0) + w
    today = now.strftime("%Y-%m-%d")
    out = {}
    for iso, r in country_risk.items():
        comp = r.get("components") or {}
        adv = comp.get("advisories") or 0.0
        sec = comp.get("security") or 0.0
        haz = comp.get("hazards") or 0.0
        base = prior.get(iso, 0) / 23 * 7  # attendu sur 7 jours
        rec = recent.get(iso, 0)
        if rec < 3:  # trop peu d'activité pour parler d'anomalie
            anomaly = 0.0
        elif base <= 0.5:
            anomaly = min(1.0, rec / 20)
        else:
            anomaly = max(0.0, min(1.0, (rec / base - 1) / 2))  # 3× la normale = anomalie maximale
        inst = 0.45 * adv + 0.30 * sec + 0.15 * anomaly + 0.10 * haz
        value = int(round(100 * (1 - min(1.0, inst))))
        series = hist.setdefault(iso, [])
        if series and series[-1][0] == today:
            series[-1][1] = value
        else:
            series.append([today, value])
        del series[:-120]

        def ago(days):
            target = (now - timedelta(days=days)).strftime("%Y-%m-%d")
            old = [v for d, v in series if d <= target]
            return value - old[-1] if old else None
        drivers = []
        cr, cp = cats_recent.get(iso, {}), cats_prior.get(iso, {})
        for c in sorted(cr, key=lambda c: -(cr[c] - cp.get(c, 0) / 23 * 7)):
            delta = cr[c] - cp.get(c, 0) / 23 * 7
            if delta >= 2 and len(drivers) < 3:
                drivers.append({"type": "category", "category": c, "delta": round(delta, 1)})
        # changement d'avis officiel : cause affichée pendant 30 jours
        adv_mem = store["state"].setdefault("pulse_adv", {})
        prev_adv = adv_mem.get(iso) or {}
        cur_adv = {k: v.get("level") for k, v in (r.get("advisories") or {}).items() if v.get("level")}
        changes = store["state"].setdefault("pulse_adv_changes", {}).setdefault(iso, [])
        for src, lvl in cur_adv.items():
            if prev_adv.get(src) and lvl != prev_adv[src]:
                changes.append({"type": "advisory", "source": src, "from": prev_adv[src], "to": lvl, "date": today})
        adv_mem[iso] = cur_adv
        changes[:] = [c for c in changes if c["date"] >= (now - timedelta(days=30)).strftime("%Y-%m-%d")][-4:]
        drivers += changes[-2:]
        out[iso] = {"value": value, "d7": ago(7), "d30": ago(30), "anomaly": round(anomaly, 2),
                    "spark": [v for _, v in series[-30:]], "drivers": drivers}
    return out


def alerts(pulse, store, settings, now):
    """Pays à signaler : chute rapide ou passage sous le seuil (une alerte par pays tous les N jours)."""
    cfg = {**DEFAULTS, **(settings.get("pulse") or {})}
    if not cfg["alerts"]:
        return []
    follow = {c.upper() for c in cfg.get("countries") or []}
    sent = store["state"].setdefault("pulse_alerted", {})
    gap = (now - timedelta(days=cfg["min_gap_days"])).isoformat()
    out = []
    for iso, p in pulse.items():
        if follow and iso not in follow:
            continue
        hist = store["state"].get("pulse_hist", {}).get(iso, [])
        if len(hist) < 3:  # pas encore d'historique : pas d'alerte au démarrage
            continue
        week = [v for _, v in hist[-8:-1]]
        crossed = p["value"] <= cfg["threshold"] - 3 and max(week) >= cfg["threshold"]  # marge : pas d'alerte en yo-yo
        drop = p["d7"] is not None and p["d7"] <= -cfg["drop_alert"]
        if (crossed or drop) and sent.get(iso, "") < gap:
            out.append({"iso": iso, **p, "reason": "threshold" if crossed else "drop"})
            sent[iso] = now.isoformat()
    return sorted(out, key=lambda a: a["value"])


def explain(pulse, events, store, settings, now, log=print, countries=None, min_move=8, limit=6):
    """Phrase explicative (IA, si la tâche « pulse_explanations » est active) pour les plus fortes variations."""
    from . import llm
    movers = sorted([(iso, p) for iso, p in pulse.items() if p.get("d7") is not None and abs(p["d7"]) >= min_move],
                    key=lambda x: x[1]["d7"])[:limit]
    for iso, p in movers:
        evs = sorted([e for e in events if e.get("country") == iso], key=lambda e: (-e["severity"], e["date"]))
        name = countries.name(iso, "fr") if countries else iso
        r = llm.pulse_explanation(iso, name, p, evs, store, settings, now, log)
        if isinstance(r, dict) and r.get("fr"):
            p["explain_fr"], p["explain_en"] = r["fr"], r.get("en") or r["fr"]
