"""Vérifie les liens de la bibliographie des tendances de risques (config/foresight/sources.json).

Usage (sur votre PC, connexion Internet requise) :
    python tools/check_foresight_sources.py

Affiche chaque lien en erreur (code HTTP ou exception). Un lien cassé se corrige dans sources.json
(adresse de la page, ou page d'accueil de l'éditeur à défaut), puis on relance la collecte.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (compatible; AngorIntelligence-linkcheck/1.0)"}


def check(item):
    key, src = item
    url = src.get("url", "")
    if not url.startswith("http"):
        return key, url, "local"
    try:
        r = requests.head(url, headers=UA, timeout=20, allow_redirects=True)
        if r.status_code in (403, 405) or r.status_code >= 400:
            r = requests.get(url, headers=UA, timeout=25, allow_redirects=True, stream=True)
        return key, url, r.status_code
    except requests.RequestException as exc:
        return key, url, type(exc).__name__


def main():
    sources = json.loads((ROOT / "config" / "foresight" / "sources.json").read_text(encoding="utf-8"))
    items = [(k, v) for k, v in sources.items() if not k.startswith("_")]
    bad = 0
    with ThreadPoolExecutor(8) as pool:
        for key, url, status in pool.map(check, items):
            ok = status == "local" or (isinstance(status, int) and status < 400)
            if not ok:
                bad += 1
                print(f"✘ {key:24} {status}  {url}")
    print(f"{len(items)} lien(s) contrôlé(s), {bad} en erreur.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
