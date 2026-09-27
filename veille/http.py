"""Accès réseau commun à toutes les sources.

Toutes les requêtes passent par ici : délai maximal, relances automatiques,
identification du robot et, pour les sources payantes, injection des
identifiants lus dans les variables d'environnement.

Types d'authentification gérés (clé "auth" d'une source dans config/sources.json) :
  {"type": "none"}
  {"type": "api_key_header", "header": "X-API-Key", "env": "MA_CLE"}
  {"type": "api_key_query",  "param": "apikey",     "env": "MA_CLE"}
  {"type": "bearer",         "env": "MON_JETON"}
  {"type": "basic",          "user_env": "MON_USER", "password_env": "MON_MDP"}
  {"type": "cookie",         "env": "MON_COOKIE"}      # abonnement presse (cookie de session)
  {"type": "oauth2_password", "token_url": "...", "user_env": "...", "password_env": "...",
   "client_id": "..."}                                  # ex. ACLED depuis 2025
"""
import time

import requests

from .config import secret

USER_AGENT = "Mozilla/5.0 (compatible; VeilleSurete/0.1; veille de securite a partir de sources ouvertes)"
DEFAULT_TIMEOUT = 30

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
_oauth_cache = {}


class AuthMissing(Exception):
    """Levée quand une source demande un secret absent : la source est ignorée proprement."""


def _oauth2_password(auth):
    key = auth["token_url"]
    cached = _oauth_cache.get(key)
    if cached and cached["expires"] > time.time() + 60:
        return cached["token"]
    user, password = secret(auth["user_env"]), secret(auth["password_env"])
    if not user or not password:
        raise AuthMissing(f"{auth['user_env']} / {auth['password_env']} non définis")
    data = {"grant_type": "password", "username": user, "password": password,
            "client_id": auth.get("client_id", ""), "scope": auth.get("scope", "")}
    r = _session.post(auth["token_url"], data=data, timeout=DEFAULT_TIMEOUT)
    r.raise_for_status()
    payload = r.json()
    _oauth_cache[key] = {"token": payload["access_token"],
                         "expires": time.time() + int(payload.get("expires_in", 3600))}
    return payload["access_token"]


def apply_auth(auth, headers, params, cookies):
    if not auth or auth.get("type", "none") == "none":
        return
    kind = auth["type"]
    if kind in ("api_key_header", "api_key_query", "bearer", "cookie"):
        value = secret(auth["env"])
        if not value:
            raise AuthMissing(f"variable {auth['env']} non définie")
        if kind == "api_key_header":
            headers[auth.get("header", "X-API-Key")] = value
        elif kind == "api_key_query":
            params[auth.get("param", "apikey")] = value
        elif kind == "bearer":
            headers["Authorization"] = f"Bearer {value}"
        else:
            for part in value.split(";"):
                if "=" in part:
                    k, v = part.strip().split("=", 1)
                    cookies[k] = v
    elif kind == "basic":
        user, password = secret(auth["user_env"]), secret(auth["password_env"])
        if not user or not password:
            raise AuthMissing(f"{auth['user_env']} / {auth['password_env']} non définis")
        import base64
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    elif kind == "oauth2_password":
        headers["Authorization"] = f"Bearer {_oauth2_password(auth)}"
    else:
        raise ValueError(f"type d'authentification inconnu : {kind}")


def get(url, params=None, auth=None, headers=None, retries=2, timeout=DEFAULT_TIMEOUT):
    """GET avec relances (erreurs réseau et codes 429/5xx). Renvoie l'objet Response."""
    params = dict(params or {})
    headers = dict(headers or {})
    cookies = {}
    apply_auth(auth, headers, params, cookies)
    last_error = None
    for attempt in range(retries + 1):
        try:
            r = _session.get(url, params=params, headers=headers, cookies=cookies, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
    raise last_error


def get_json(url, **kwargs):
    return get(url, **kwargs).json()


def post_json(url, body, headers=None, timeout=90, retries=2):
    """POST JSON avec relances (429/5xx) ; renvoie la réponse décodée."""
    last_error = None
    for attempt in range(retries + 1):
        try:
            r = _session.post(url, json=body, headers=dict(headers or {}), timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 529) and attempt < retries:
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(3 * (attempt + 1))
    raise last_error
