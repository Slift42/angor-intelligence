"""Signe de vie envoyé à la base des comptes (Supabase) à chaque collecte.

Appelle la fonction SQL public.ping() (supabase/schema.sql) : sans privilège, elle ne lit ni n'écrit aucune donnée,
mais cette activité régulière empêche la mise en pause du projet Supabase gratuit (7 jours sans activité).
L'effacement des données expirées (durées de la politique de confidentialité) est fait par la base elle-même, chaque
nuit (private.housekeeping() planifiée avec pg_cron), sans passer par l'API.
N'utilise que l'URL et la clé publique de config/settings.json → accounts (jamais la clé service_role).
Sans comptes configurés, ne fait rien. Ne fait jamais échouer la collecte.
"""
from . import http


def headers(key):
    """En-têtes d'appel avec la clé publique ({} si absente)."""
    if not key:
        return {}
    h = {"apikey": key}
    if key.startswith("eyJ"):  # ancienne clé « anon » (jeton JWT) ; les nouvelles clés « sb_publishable_… » vont seules
        h["Authorization"] = f"Bearer {key}"
    return h


def ping(settings, log=print):
    acc = settings.get("accounts") or {}
    url, key = (acc.get("supabase_url") or "").rstrip("/"), acc.get("supabase_anon_key") or ""
    if not (url and key):
        return None
    try:
        return http.post_json(f"{url}/rest/v1/rpc/ping", {}, timeout=20, retries=1, headers=headers(key))
    except Exception as exc:  # fonction absente (schéma pas à jour), réseau, projet en pause…
        log(f"  – Base des comptes injoignable ({type(exc).__name__}) : projet en pause ou supabase/schema.sql à relancer")
        return None
