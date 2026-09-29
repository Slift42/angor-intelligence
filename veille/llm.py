"""Socle IA commun (API Anthropic) : un seul point d'entrée pour toutes les tâches rédactionnelles du robot.

Sans clé ANTHROPIC_API_KEY (ou avec "ai": {"enabled": false}), chaque fonction renvoie None et l'outil
garde ses textes automatiques : rien ne casse, rien n'est facturé. Avec la clé, chaque tâche peut être
activée ou coupée séparément dans config/settings.json → "ai" → "tasks" :

  event_summaries     résumés FR/EN des titres de presse (veille/ai.py, lots de 25 titres)
  crisis_summaries    synthèse de 2-3 phrases de chaque chronologie de crise active
  digest_editorial    « L'essentiel du jour » en tête du point quotidien Telegram
  pulse_explanations  une phrase qui explique les plus fortes variations du Pulse

Garde-fous communs : budget mensuel lissé jour par jour (monthly_budget_usd, partagé par toutes les tâches),
cache par tâche (un même contenu n'est jamais redemandé), plafond d'appels par collecte (max_calls_per_run).
Le Travel buddy, le go/no-go guidé et le brief utilisent le relais Cloudflare (tools/buddy-worker.js),
car la carte est publique et ne peut pas contenir de clé.
"""
import calendar
import hashlib
import json
import re

from . import http
from .config import secret

API = "https://api.anthropic.com/v1/messages"
DEFAULTS = {"enabled": True, "model": "claude-haiku-4-5", "monthly_budget_usd": 20.0,
            "price_in_per_mtok": 1.0, "price_out_per_mtok": 5.0, "max_calls_per_run": 12,
            "tasks": {"event_summaries": True, "crisis_summaries": True, "digest_editorial": True,
                      "pulse_explanations": True}}
_calls = {"n": 0}


def config(settings):
    cfg = {**DEFAULTS, **(settings.get("ai") or {})}
    cfg["tasks"] = {**DEFAULTS["tasks"], **((settings.get("ai") or {}).get("tasks") or {})}
    return cfg


def available(settings, task):
    """La tâche peut-elle appeler l'IA ? (clé présente, IA activée, tâche activée)"""
    cfg = config(settings)
    return bool(secret("ANTHROPIC_API_KEY")) and cfg["enabled"] and cfg["tasks"].get(task, False)


def month_usage(store, now):
    usage = store.setdefault("state", {}).setdefault("ai_usage", {})
    return usage.setdefault(now.strftime("%Y-%m"), {"in": 0, "out": 0, "usd": 0.0})


def budget_left(store, settings, now):
    """Reste du budget autorisé à ce jour (le budget mensuel est lissé sur les jours du mois)."""
    cfg = config(settings)
    days = calendar.monthrange(now.year, now.month)[1]
    allowed = cfg["monthly_budget_usd"] * min(1.0, (now.day + 1) / days)
    return allowed - month_usage(store, now)["usd"]


def account(store, settings, now, usage):
    cfg = config(settings)
    m = month_usage(store, now)
    m["in"] += usage.get("input_tokens", 0)
    m["out"] += usage.get("output_tokens", 0)
    m["usd"] = round(m["in"] / 1e6 * cfg["price_in_per_mtok"] + m["out"] / 1e6 * cfg["price_out_per_mtok"], 4)


def _cache(store, task):
    return store.setdefault("llm_cache", {}).setdefault(task, {})


def cache_key(*parts):
    return hashlib.sha1(json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:16]


def complete(task, system, prompt, store, settings, now, log=print, key=None, max_tokens=700, want_json=False):
    """Appel unique à Claude pour une tâche. Renvoie le texte (ou l'objet JSON), ou None si indisponible.

    key : clé de cache (même clé → réponse réutilisée sans appel). None = pas de cache.
    """
    cache = _cache(store, task)
    if key and key in cache:
        return cache[key]
    if not available(settings, task):
        return None
    cfg = config(settings)
    if _calls["n"] >= cfg["max_calls_per_run"] or budget_left(store, settings, now) <= 0:
        return None
    body = {"model": cfg["model"], "max_tokens": max_tokens, "system": system,
            "messages": [{"role": "user", "content": prompt}]}
    try:
        _calls["n"] += 1
        r = http.post_json(API, body, headers={"x-api-key": secret("ANTHROPIC_API_KEY"),
                                               "anthropic-version": "2023-06-01"})
    except Exception as exc:
        log(f"  IA ({task}) indisponible : {type(exc).__name__}: {str(exc)[:120]}")
        return None
    account(store, settings, now, r.get("usage", {}))
    text = "".join(c.get("text", "") for c in r.get("content", []) if c.get("type") == "text").strip()
    out = text
    if want_json:
        m = re.search(r"[\[{].*[\]}]", text, re.S)
        try:
            out = json.loads(m.group(0)) if m else None
        except ValueError:
            out = None
    if out is not None and key:
        cache[key] = out
        if len(cache) > 3000:
            for k in list(cache)[:1000]:
                del cache[k]
    return out


# ------------------------------------------------------------------ tâches prêtes à l'emploi
STYLE = ("Tu es analyste sûreté chez Angor Intelligence. Style factuel, neutre, sans spéculation. "
         "N'utilise QUE les faits fournis ; n'invente ni bilan, ni acteur, ni cause. Pas de titre, pas de liste.")


def crisis_summary(crisis, events, store, settings, now, log=print):
    """Synthèse FR/EN d'une chronologie de crise → {"fr": ..., "en": ...} ou None."""
    lines = "\n".join(f"- {e['date'][:16]} | gravité {e['severity']} | {e.get('place') or ''} | {e['title'][:180]}"
                      for e in events[-25:])
    prompt = (f"Chronologie « {crisis['title']} » ({crisis['country']}), {crisis['n']} incidents du "
              f"{crisis['start'][:10]} au {crisis['last'][:10]}. Incidents :\n{lines}\n\n"
              "Rédige une synthèse de 2 à 3 phrases (55 mots max) : nature de la crise, lieux, évolution "
              "(escalade, stabilisation, décrue) et point culminant. Réponds en JSON : {\"fr\": \"...\", \"en\": \"...\"}")
    return complete("crisis_summaries", STYLE, prompt, store, settings, now, log,
                    key=cache_key(crisis["id"], crisis["n"], crisis["last"][:13]), want_json=True, max_tokens=500)


def digest_editorial(blocks, store, settings, now, log=print):
    """« L'essentiel du jour » : 3 phrases en tête du point quotidien, à partir de son contenu."""
    prompt = ("Voici le point quotidien de veille sûreté :\n\n" + "\n\n".join(blocks)[:6000] +
              "\n\nRédige « L'essentiel du jour » en 3 phrases maximum (70 mots), en français, pour un directeur "
              "sûreté : ce qui a le plus changé et ce qui mérite son attention. Texte brut, sans titre.")
    return complete("digest_editorial", STYLE, prompt, store, settings, now, log,
                    key=cache_key(now.strftime("%Y-%m-%d"), blocks[:2]), max_tokens=300)


def pulse_explanation(iso, name, p, events, store, settings, now, log=print):
    lines = "\n".join(f"- {e['date'][:10]} | {e['category']} | gravité {e['severity']} | {e['title'][:150]}"
                      for e in events[:15])
    prompt = (f"Pays : {name}. Indice de stabilité Pulse {p['value']}/100, variation sur 7 jours {p.get('d7')}. "
              f"Causes calculées : {json.dumps(p.get('drivers'), ensure_ascii=False)}. Incidents récents :\n{lines}\n\n"
              "Explique la variation en une phrase (30 mots max). JSON : {\"fr\": \"...\", \"en\": \"...\"}")
    return complete("pulse_explanations", STYLE, prompt, store, settings, now, log,
                    key=cache_key(iso, now.strftime("%Y-%m-%d"), p["value"]), want_json=True, max_tokens=250)
