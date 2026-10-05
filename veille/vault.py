"""Coffre des données réservées aux comptes validés (v0.22).

En ligne (GitHub Pages, variable VS_PUBLIC=1) et quand les comptes sont configurés (config/settings.json → accounts),
les fichiers produits par la collecte ne doivent plus être publiés tels quels : le site est public et quiconque
pourrait les lire (docs/data/data.js…). Ce module :

1. écrit docs/data/guest.js, la version allégée de la carte des visiteurs (7 derniers jours ; titre, catégorie,
   gravité, lieu, date et position seulement : ni résumé, ni sources, ni notes de risque) ;
2. envoie les fichiers réservés dans le compartiment privé « angor-data » de Supabase Storage, avec la clé secrète
   SUPABASE_SERVICE_KEY (Secret GitHub uniquement, jamais dans un fichier) ; seuls les fichiers modifiés depuis la
   collecte précédente partent (empreintes dans data/vault_manifest.json) ;
3. retire ces fichiers de docs/data avant la publication du site (copie dans data/private/, mémoire du robot) :
   ils ne sont plus servis par GitHub Pages, même si l'envoi a échoué (fermeture par défaut).

Les pages les lisent ensuite avec le jeton de session de l'utilisateur (docs/vault.js) ; la base n'autorise la lecture
qu'aux comptes validés (politique « angor_data_read » de supabase/schema.sql).

Restent publics : la carte des pays, les réglages publics, les textes légaux, l'annuaire public des prestataires, les
villes (GeoNames), le Factbook et les guides (déjà publics dans le dépôt), la base historique (dépôt) et guest.js.
Sur votre PC (sans VS_PUBLIC), rien ne change : les fichiers restent dans docs/data pour un usage local.
"""
import hashlib
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

from . import accounts, publish
from .config import ROOT, secret

BUCKET = "angor-data"
OUT = publish.OUT_DIR
PUBLIC = {"config.js", "countries.js", "legal.js", "providers.js", "cities.js", "factbook.js", "guides.js", "guest.js"}
PUBLIC_DIRS = {"history"}
KEEP = ROOT / "data" / "private"
MANIFEST = ROOT / "data" / "vault_manifest.json"
GUEST_DAYS = 7
GUEST_MAX = 1500
GUEST_FIELDS = ("id", "category", "severity", "title", "title_en", "headline", "date", "lat", "lon", "place", "country",
                "precision", "confidence", "tags", "admiralty", "source")
TYPES = {".js": "text/javascript; charset=utf-8", ".json": "application/json", ".geojson": "application/geo+json"}


def enabled(settings):
    """Coffre actif : site en ligne et comptes configurés (sinon, fonctionnement local inchangé)."""
    acc = (settings or {}).get("accounts") or {}
    return os.environ.get("VS_PUBLIC") == "1" and bool(acc.get("supabase_url") and acc.get("supabase_anon_key"))


def is_public(rel):
    """rel : chemin relatif à docs/data, avec des « / »."""
    first = rel.split("/", 1)[0]
    return rel in PUBLIC or first in PUBLIC_DIRS


def private_files(root=None):
    root = root or OUT
    if not root.exists():
        return []
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and "__pycache__" not in rel and not is_public(rel):
            out.append(rel)
    return out


def guest_payload(payload, now=None):
    """Carte des visiteurs : même structure que data.js (la carte n'a rien à adapter), contenu réduit."""
    now = now or datetime.now(timezone.utc)
    limit = (now - timedelta(days=GUEST_DAYS)).isoformat()
    events = [e for e in payload.get("events", []) if str(e.get("date", "")) >= limit[:19]]
    events.sort(key=lambda e: (e.get("severity") or 0, str(e.get("date"))), reverse=True)  # plafond : les plus graves
    events = sorted(events[:GUEST_MAX], key=lambda e: str(e.get("date")), reverse=True)
    s, cov = payload.get("settings") or {}, payload.get("coverage") or {}
    return {
        "generated": payload.get("generated"), "version": payload.get("version"), "guest": True,
        "taxonomy": payload.get("taxonomy"),
        "events": [{k: e[k] for k in GUEST_FIELDS if k in e} for e in events],
        "countries": {}, "news": [], "status": [], "source_quality": {},
        "coverage": {"total": cov["total"]} if "total" in cov else None, "sites": [], "corridors": [],
        "site_alerts": [], "crises": [], "country_stats": {}, "archives": [], "analytics": {}, "pulse": {}, "verified": {},
        "settings": {k: s.get(k) for k in ("product_name", "default_lang") if k in s},
    }


def write_guest(payload, now=None):
    publish.write_js("guest.js", "VS_DATA", guest_payload(payload, now))


def restore():
    """Début de collecte en ligne : remet les fichiers que la collecte réutilise (profils pays, mis à jour chaque semaine)."""
    src, dst = KEEP / "profiles.js", OUT / "profiles.js"
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _upload(session, url, key, rel, body):
    ext = os.path.splitext(rel)[1]
    h = dict(accounts.headers(key))
    h.update({"x-upsert": "true", "content-type": TYPES.get(ext, "application/octet-stream"), "cache-control": "no-cache"})
    target = f"{url}/storage/v1/object/{BUCKET}/{rel}"
    r = session.post(target, data=body, headers=h, timeout=60)
    if r.status_code in (401, 403) and "Authorization" not in h:   # selon le type de clé, la passerelle veut aussi l'en-tête
        h["Authorization"] = f"Bearer {key}"
        r = session.post(target, data=body, headers=h, timeout=60)
    r.raise_for_status()


def publish_private(settings, log=print, session=None):
    """Envoie les fichiers réservés dans le coffre et les retire du site. Renvoie un résumé, ou None si inactif."""
    if not enabled(settings):
        return None
    url = settings["accounts"]["supabase_url"].rstrip("/")
    key = secret("SUPABASE_SERVICE_KEY")
    files = private_files()
    done, failed = [], []
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    except (OSError, ValueError):
        manifest = {}
    if not key:
        log("✘ Coffre : Secret GitHub SUPABASE_SERVICE_KEY absent – les données réservées ne sont PAS publiées "
            "(les comptes validés ne les voient pas tant qu'il manque ; voir GUIDE_MISE_EN_LIGNE.md, partie H10)")
    else:
        todo = [(rel, _digest(OUT / rel)) for rel in files]
        todo = [(rel, h) for rel, h in todo if manifest.get(rel) != h]
        session = session or requests.Session()

        def send(item):
            rel, h = item
            try:
                _upload(session, url, key, rel, (OUT / rel).read_bytes())
                return rel, h, None
            except Exception as exc:  # réseau, clé refusée, compartiment absent (schéma pas relancé)…
                return rel, h, f"{type(exc).__name__}: {str(exc)[:120]}"

        with ThreadPoolExecutor(max_workers=8) as pool:
            for rel, h, err in pool.map(send, todo):
                if err:
                    failed.append((rel, err))
                else:
                    done.append(rel)
                    manifest[rel] = h
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(manifest, indent=0, sort_keys=True), encoding="utf-8")
        if failed:
            log(f"✘ Coffre : {len(failed)} fichier(s) non envoyé(s), ex. {failed[0][0]} ({failed[0][1]}) – "
                "supabase/schema.sql relancé ? clé secrète correcte ?")
        log(f"  Coffre : {len(done)} fichier(s) réservé(s) envoyé(s), {len(files) - len(done) - len(failed)} inchangé(s)")
    # fermeture par défaut : quoi qu'il arrive, les fichiers réservés quittent le site public
    for rel in files:
        src, dst = OUT / rel, KEEP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    for d in sorted((p for p in OUT.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()
    return {"files": len(files), "uploaded": len(done), "failed": len(failed), "key": bool(key)}
