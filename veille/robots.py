"""Respect du fichier robots.txt des sites lus par le robot (v0.28, run 3).

Règle du projet : on ne lit un flux ou une page que si le robots.txt du site l'autorise. Ce module lit le robots.txt
d'un site (une fois par semaine au plus), garde les règles qui s'appliquent au robot (groupe « VeilleSurete », sinon
« * ») et répond à « ai-je le droit de lire cette adresse ? ». Interprétation de la RFC 9309 :
- règle la plus longue applicable ; à longueur égale, « Allow » l'emporte ; jokers « * » et « $ » ;
- robots.txt absent (404 ou autre 4xx) : tout est permis ; 401 / 403 : rien n'est permis (prudence) ;
- site injoignable ou erreur 5xx : on garde la dernière réponse connue, à défaut on lit (nouvel essai à la collecte
  suivante) et on le note dans le journal.

Seuls les connecteurs qui lisent des sites de presse ou des pages (flux RSS, médias, Telegram, titres d'articles
GDELT) demandent ce contrôle (`http.get(..., robots=True)`). Les API documentées (USGS, NWS, FMI, Banque mondiale…)
sont faites pour être interrogées par programme et n'y sont pas soumises.

Exemptions : une source peut déclarer `"robots_exempt": ["news.google.com"]` dans config/sources.json. C'est une
exception temporaire, visible dans l'état des sources et dans le journal, à n'utiliser qu'en connaissance de cause.
"""
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import requests

AGENT = "veillesurete"          # nom du robot dans l'en-tête User-Agent (« VeilleSurete/0.1 »)
REFRESH = timedelta(days=7)
TIMEOUT = 10
MAX_HOSTS = 3000                # mémoire bornée (sites les plus anciens oubliés d'abord)

_cache = {}                     # hôte → {"t": iso, "s": statut, "r": [["a"|"d", motif], …]}
EXEMPT = set()                  # hôtes exemptés (déclarés par les sources)
_log = []                       # messages à afficher dans le journal de collecte
_unreachable = set()            # robots.txt injoignables pendant cette collecte (pas de nouvel essai avant la suivante)
_session = requests.Session()


class RobotsDisallowed(Exception):
    """Adresse interdite au robot par le robots.txt du site : la source est mise de côté proprement."""


def configure(sources, state):
    """Début de collecte : exemptions déclarées et mémoire des robots.txt (store["state"]["robots"])."""
    EXEMPT.clear()
    for s in sources:
        if s.get("enabled"):
            EXEMPT.update(h.lower() for h in (s.get("robots_exempt") or []))
    _cache.clear()
    _cache.update(state.get("robots") or {})
    del _log[:]
    _unreachable.clear()


def save(state):
    """Fin de collecte : la mémoire est rangée dans l'état persistant (bornée à MAX_HOSTS sites)."""
    items = sorted(_cache.items(), key=lambda kv: kv[1].get("t", ""), reverse=True)[:MAX_HOSTS]
    state["robots"] = dict(items)


def messages():
    out = list(_log)
    del _log[:]
    return out


def parse(text):
    """Règles applicables au robot : groupe qui nomme « veillesurete », sinon groupe « * »."""
    groups, agents, rules, in_rules = [], [], [], False
    for raw in (text or "").splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if in_rules:
                groups.append((agents, rules))
                agents, rules, in_rules = [], [], False
            agents.append(value.lower())
        elif key in ("allow", "disallow"):
            in_rules = True
            if value or key == "allow":
                rules.append(["a" if key == "allow" else "d", value])
    if agents:
        groups.append((agents, rules))
    mine = [r for a, r in groups if any(x != "*" and x in AGENT for x in a)]
    if mine:
        return [x for r in mine for x in r]
    return [x for a, r in groups if "*" in a for x in r]


def _pattern(rule):
    """Motif robots.txt → expression régulière (« * » = n'importe quoi, « $ » = fin d'adresse)."""
    end = rule.endswith("$")
    body = re.escape(rule[:-1] if end else rule).replace(r"\*", ".*")
    return re.compile(body + ("$" if end else ""))


def verdict(rules, path):
    """True si le chemin (avec sa requête) est autorisé par ces règles."""
    best_len, allowed = -1, True
    for kind, rule in rules:
        if not rule:
            continue
        if _pattern(rule).match(path):
            n = len(rule)
            if n > best_len or (n == best_len and kind == "a"):
                best_len, allowed = n, kind == "a"
    return allowed


def _fetch(scheme, host):
    url = f"{scheme}://{host}/robots.txt"
    try:
        r = _session.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0 (compatible; VeilleSurete/0.1)"},
                         allow_redirects=True)
    except requests.RequestException as exc:
        return None, f"robots.txt de {host} injoignable ({type(exc).__name__})"
    if r.status_code in (401, 403):
        return {"s": r.status_code, "r": [["d", "/"]]}, None
    if 400 <= r.status_code < 500:
        return {"s": r.status_code, "r": []}, None
    if r.status_code >= 500:
        return None, f"robots.txt de {host} : erreur {r.status_code}"
    return {"s": r.status_code, "r": parse(r.text[:200000])}, None


def allowed(url, now=None):
    """Le robot peut-il lire cette adresse ? (mémoire d'une semaine par site)"""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if not host or host in EXEMPT:
        return True
    now = now or datetime.now(timezone.utc)
    entry = _cache.get(host)
    stale = not entry or now - datetime.fromisoformat(entry["t"]) > REFRESH
    if stale and host not in _unreachable:
        fresh, err = _fetch(parts.scheme or "https", host)
        if fresh:
            fresh["t"] = now.replace(microsecond=0).isoformat()
            _cache[host] = entry = fresh
        else:
            _unreachable.add(host)
            if err and len(_log) < 50:
                _log.append(err)
        if not entry:
            return True
    path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    return verdict(entry.get("r") or [], path)


def check(url):
    """Lève RobotsDisallowed si le robots.txt du site interdit l'adresse."""
    if not allowed(url):
        raise RobotsDisallowed(f"interdit par le robots.txt de {urlsplit(url).hostname}")
