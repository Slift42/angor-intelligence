"""Étape IA : lecture des titres de presse par un modèle léger (Claude Haiku).

Pour chaque titre, l'IA renvoie une fiche structurée :
  relevant (incident réel et actuel ?), category, severity (1-4), country (ISO2), place (ville),
  summary_en (résumé neutre en anglais, 25 mots maximum).

Activation : définir ANTHROPIC_API_KEY dans .env (ou dans les Secrets GitHub) et laisser
"ai": {"enabled": true} dans config/settings.json. Sans clé, l'outil garde le classement par mots-clés.

Maîtrise des coûts :
- seuls les titres jamais vus sont envoyés (cache dans data/store.json) ;
- plafond par collecte (max_items_per_run) et budget mensuel en dollars (monthly_budget_usd) ;
- titres envoyés par lots de 40 (une seule requête pour 40 titres).
"""
import json
import re

from . import http
from .config import secret

API = "https://api.anthropic.com/v1/messages"
DEFAULTS = {"enabled": True, "model": "claude-haiku-4-5", "max_items_per_run": 400, "batch_size": 40,
            "monthly_budget_usd": 20.0, "price_in_per_mtok": 1.0, "price_out_per_mtok": 5.0}
CATEGORIES = ["terrorism", "armed_conflict", "attack", "crime", "unrest", "political", "cyber", "infrastructure",
              "health", "earthquake", "cyclone", "storm", "flood", "wildfire", "volcano", "landslide",
              "extreme_temp", "drought"]

SYSTEM = f"""You are a security intelligence analyst triaging news headlines for a crisis-monitoring map.
For each numbered headline, decide whether it reports an ACTUAL, CURRENT safety/security/crisis event
(attack, armed clash, terrorism, violent crime, protest/strike/riot, coup or political crisis, cyberattack,
infrastructure failure, disease outbreak, natural disaster). Mark relevant=false for: drills and exercises,
sport, culture/entertainment, anniversaries and history, opinion pieces, court rulings on old events,
policy announcements, prevention campaigns, and anything that is not a new incident.

Return ONLY a JSON array, one object per headline, in the same order:
{{"i": <number>, "relevant": true|false, "category": one of {CATEGORIES} or null,
  "severity": 1-4 (1 low/local nuisance, 2 moderate: injuries or local disruption, 3 high: deaths or major
  disruption, 4 critical: mass casualties, war escalation, national emergency),
  "country": ISO 3166-1 alpha-2 code of where the event happens (not the outlet's country) or null,
  "place": most precise city/locality name in English where it happens, or null,
  "summary_en": neutral English summary, max 25 words, no speculation}}"""


def _parse(text):
    m = re.search(r"\[.*\]", text, re.S)
    return json.loads(m.group(0)) if m else []


def _month(now):
    return now.strftime("%Y-%m")


def analyze(items, store, settings, log, now):
    """items : liste de titres de presse ({title, outlet, country_hint, lang}). Renvoie {titre: fiche}."""
    cfg = {**DEFAULTS, **(settings.get("ai") or {})}
    key = secret("ANTHROPIC_API_KEY")
    cache = store.setdefault("ai_cache", {})
    results = {it["title"]: cache[it["title"]] for it in items if it["title"] in cache}
    if not cfg["enabled"] or not key:
        return results
    usage = store.setdefault("state", {}).setdefault("ai_usage", {})
    month = usage.setdefault(_month(now), {"in": 0, "out": 0, "usd": 0.0})
    todo, seen = [], set()
    for it in items:
        if it["title"] not in cache and it["title"] not in seen:
            seen.add(it["title"])
            todo.append(it)
    todo = todo[: int(cfg["max_items_per_run"])]
    done = 0
    for start in range(0, len(todo), int(cfg["batch_size"])):
        if month["usd"] >= cfg["monthly_budget_usd"]:
            log(f"  IA : budget mensuel atteint ({month['usd']:.2f} $) – retour aux mots-clés")
            break
        batch = todo[start:start + int(cfg["batch_size"])]
        lines = "\n".join(f"{i + 1}. [{b.get('country_hint') or '?'} | {b.get('outlet', '')}] {b['title']}"
                          for i, b in enumerate(batch))
        body = {"model": cfg["model"], "max_tokens": 4000, "system": SYSTEM,
                "messages": [{"role": "user", "content": f"Headlines (country hint | outlet):\n{lines}"}]}
        try:
            r = http.post_json(API, body, headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
            text = "".join(c.get("text", "") for c in r.get("content", []) if c.get("type") == "text")
            rows = _parse(text)
        except Exception as exc:
            log(f"  IA : lot ignoré ({type(exc).__name__}: {str(exc)[:120]})")
            continue
        u = r.get("usage", {})
        month["in"] += u.get("input_tokens", 0)
        month["out"] += u.get("output_tokens", 0)
        month["usd"] = round(month["in"] / 1e6 * cfg["price_in_per_mtok"] + month["out"] / 1e6 * cfg["price_out_per_mtok"], 4)
        for row in rows:
            try:
                b = batch[int(row["i"]) - 1]
            except (KeyError, ValueError, IndexError, TypeError):
                continue
            if row.get("category") not in CATEGORIES:
                row["relevant"] = False
            row["severity"] = max(1, min(4, int(row.get("severity") or 1)))
            if row.get("country"):
                row["country"] = str(row["country"]).upper()[:2]
            fiche = {k: row.get(k) for k in ("relevant", "category", "severity", "country", "place", "summary_en")}
            cache[b["title"]] = results[b["title"]] = fiche
            done += 1
    if len(cache) > 20000:  # le cache ne grossit pas indéfiniment
        for k in list(cache)[: len(cache) - 15000]:
            del cache[k]
    if todo:
        log(f"  IA : {done}/{len(todo)} titres analysés · ce mois-ci {month['usd']:.2f} $ / {cfg['monthly_budget_usd']} $")
    return results
