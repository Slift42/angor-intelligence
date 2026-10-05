"""Contrôle d'entrée des événements : vérification a priori et permanente (v0.24).

Chaque événement passe ce contrôle **avant** d'entrer sur la carte (a priori), puis **à chaque collecte** tant qu'il
reste en mémoire (permanent : une règle améliorée s'applique aussi aux fiches déjà connues, un titre d'article lu
plus tard peut changer le verdict). Rien n'atteint la carte, les alertes e-mail/Telegram, les notes de risque ou
Pulse sans un verdict « ok ».

Verdicts (champ « triage » de l'événement en mémoire) :
- ok        : fait physique vérifié par les règles → carte ;
- context   : titre de sûreté sans fait physique (arrestation, déclaration, analyse…) → Fil seulement ;
- noise     : hors sujet, fait divers, procédure judiciaire → écarté ;
- invalid   : fiche inutilisable (position impossible, date absente ou dans le futur, titre vide) → écartée ;
- pending   : GDELT dont le titre réel de l'article n'est pas encore lu → en attente, hors carte ;
- unverifiable : GDELT dont l'article est illisible (page bloquée, sans titre) → hors carte.

Décision de l'analyste (config/verified.json, mode analyste de la carte) : « verified » ou « corrected » force
l'entrée, « false » l'interdit. C'est le seul moyen de passer outre les règles.

Le journal (store["state"]["triage"]) garde les chiffres des dernières collectes et les derniers titres écartés,
affichés dans « État des sources » pour la relecture : un faux rejet se rétablit d'un clic en mode analyste.
"""
import hashlib
import json
from datetime import timedelta
from pathlib import Path

from . import press
from .model import parse_iso

# Empreinte des règles : une fiche déjà contrôlée avec les mêmes règles et le même contenu n'est pas relue (le tri
# par mots-clés coûte ~2 ms par titre : 30 000 fiches en mémoire = 1 minute). Règles modifiées → tout est relu.
RULES = hashlib.sha1(b"".join(Path(m).read_bytes() for m in (press.__file__, __file__))).hexdigest()[:10]

ON_MAP = "ok"
LABELS = {"ok": "retenus", "context": "contexte (Fil)", "noise": "écartés", "invalid": "invalides",
          "pending": "en attente", "unverifiable": "invérifiables"}
# alertes, bulletins et prévisions peuvent porter une date à venir (début de validité) ; jamais un attentat
FUTURE_OK = {"earthquake", "cyclone", "storm", "flood", "wildfire", "volcano", "landslide", "extreme_temp", "drought",
             "health", "infrastructure"}
FUTURE_DAYS = 10
JOURNAL_RECENT = 150
JOURNAL_RUNS = 48
ALARM_MIN = 20          # alarme : au moins 20 nouveautés d'une source…
ALARM_RATE = 0.85       # … dont plus de 85 % refusées (flux devenu hors sujet, ou règle trop stricte)
CONTEXT_REASONS = {"arrestation ou suites", "projet déjoué", "déclaration", "analyse", "rétrospective ou démenti",
                   "prévention, bilan ou suites", "annonce militaire", "annonce de sécurité", "signal politique"}


def sanity(e, now):
    """Fiche inutilisable (motif) ou None."""
    lat, lon = e.get("lat"), e.get("lon")
    if lat is None or lon is None:
        return "position absente"
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return "position illisible"
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return "position impossible"
    if abs(lat) < 0.01 and abs(lon) < 0.01:
        return "position nulle (0, 0)"
    if not (e.get("title") or "").strip():
        return "titre vide"
    try:
        d = parse_iso(e.get("date"))
    except (TypeError, ValueError):
        d = None
    if d is None:
        return "date illisible"
    limit = now + (timedelta(days=FUTURE_DAYS) if e.get("category") in FUTURE_OK else timedelta(hours=2))
    if d > limit:
        return "date dans le futur"
    return None


def verdict(e, now, verified=None):
    """(statut, motif) d'un événement, selon les règles du moment et les décisions de l'analyste."""
    v = (verified or {}).get(e["id"])
    if v and v.get("status") in ("verified", "corrected"):
        return "ok", "validé par l'analyste"
    if v and v.get("status") == "false":
        return "noise", "infirmé par l'analyste"
    bad = sanity(e, now)
    if bad:
        return "invalid", bad
    tags = e.get("tags") or []
    if "press" in tags:
        if press.not_incident(e["title"], e["category"]):
            return "noise", press.not_incident(e["title"], e["category"])
        if "ai" in tags and e.get("physical") is True:   # l'IA a lu le titre : fait physique confirmé
            return "ok", None
        if "ai" in tags and e.get("physical") is False:
            return "context", "contexte (IA)"
        if "ai" not in tags and not press.classify(e["title"])[0]:
            return "noise", "hors sujet"
        ctx = press.context(e["title"], e["category"])
        return ("context", ctx) if ctx else ("ok", None)
    if e.get("source") == "GDELT":
        if not e.get("headline"):
            return ("unverifiable", "article illisible") if e.get("headline_failed") else ("pending", "titre de l'article à lire")
        why = press.gdelt_noise(e["headline"])
        if why:
            return ("context", why) if why in CONTEXT_REASONS else ("noise", why)
        return "ok", None
    return "ok", None   # sources officielles (USGS, GDACS, NWS, OMS…) : déjà des événements vérifiés



def _signature(e):
    keys = ("title", "category", "headline", "headline_failed", "physical", "tags", "source")
    return RULES + hashlib.sha1(json.dumps([e.get(k) for k in keys], ensure_ascii=False, default=str).encode()).hexdigest()[:12]


def check(events, now, verified=None):
    """Pose le verdict sur chaque événement (champ « triage ») ; renvoie {statut: nombre}.
    Le verdict garde sa date d'origine tant qu'il ne change pas (« since »)."""
    counts = {}
    stamp = now.replace(microsecond=0).isoformat()
    for e in events:
        old = e.get("triage") or {}
        sig = _signature(e)
        if old.get("sig") == sig and e["id"] not in (verified or {}) and not old.get("analyst") \
                and not sanity(e, now) and old.get("status") != "invalid":
            status, reason = old["status"], old.get("reason")      # même contenu, mêmes règles : verdict inchangé
        else:
            status, reason = verdict(e, now, verified)
        since = old.get("since") if old.get("status") == status else stamp
        e["triage"] = {"status": status, **({"reason": reason} if reason else {}), "since": since, "sig": sig,
                       **({"analyst": True} if e["id"] in (verified or {}) else {})}
        counts[status] = counts.get(status, 0) + 1
    return counts


def on_map(events):
    return [e for e in events if (e.get("triage") or {}).get("status") == ON_MAP]


def summary(counts):
    return ", ".join(f"{n} {LABELS.get(k, k)}" for k, n in sorted(counts.items(), key=lambda kv: -kv[1]))


def alarms(new_events):
    """Sources dont presque toutes les nouveautés sont refusées : flux à revoir ou règle trop stricte."""
    per = {}
    for e in new_events:
        src = e.get("source") or "?"
        st = (e.get("triage") or {}).get("status")
        tot, ko = per.get(src, (0, 0))
        per[src] = (tot + 1, ko + (st in ("noise", "invalid", "unverifiable")))
    return [f"{src} : {ko}/{tot} nouveautés refusées" for src, (tot, ko) in sorted(per.items())
            if tot >= ALARM_MIN and ko / tot > ALARM_RATE]


def journal(store, now, new_counts, all_counts, all_events, alarm_list):
    """Mémoire du contrôle : chiffres des dernières collectes et derniers titres refusés (relecture de l'analyste)."""
    j = store.setdefault("state", {}).setdefault("triage", {})
    runs = j.setdefault("runs", [])
    runs.append({"date": now.replace(microsecond=0).isoformat(), "new": new_counts, "all": all_counts,
                 **({"alarms": alarm_list} if alarm_list else {})})
    del runs[:-JOURNAL_RUNS]
    refused = [e for e in all_events if (e.get("triage") or {}).get("status") not in (ON_MAP, "pending")]
    refused.sort(key=lambda e: (e["triage"].get("since", ""), e.get("date", "")), reverse=True)
    j["recent"] = [{"id": e["id"], "source": e.get("source"), "category": e.get("category"), "country": e.get("country"),
                    "title": (e.get("headline") if e.get("source") == "GDELT" and e.get("headline") else e.get("title")),
                    "url": e.get("url"), "date": e.get("date"),
                    **{k: v for k, v in e["triage"].items() if k not in ("sig", "analyst")}} for e in refused[:JOURNAL_RECENT]]
    return j


def payload(store):
    """Résumé publié pour « État des sources » (données réservées aux comptes validés)."""
    j = (store.get("state") or {}).get("triage") or {}
    runs = j.get("runs") or []
    if not runs:
        return None
    last = runs[-1]
    day = [r for r in runs if r["date"] >= runs[-1]["date"][:10]]
    new_day = {}
    for r in day:
        for k, n in (r.get("new") or {}).items():
            new_day[k] = new_day.get(k, 0) + n
    return {"last": last, "today": new_day, "recent": j.get("recent", [])[:80],
            "alarms": [a for r in runs[-6:] for a in r.get("alarms", [])]}
