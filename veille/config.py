"""Chargement de la configuration.

- config/*.json : réglages versionnés (sources activées, poids du score, sites).
- .env          : secrets (clés d'API, identifiants). JAMAIS versionné (voir .gitignore).
  Sur GitHub Actions, ces mêmes variables viennent des « Secrets » du dépôt.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"


def load_json(name, default=None):
    path = CONFIG_DIR / name
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_lines(path):
    # utf-8-sig : accepte les fichiers enregistrés par le Bloc-notes (BOM)
    return [l.strip() for l in Path(path).read_text(encoding="utf-8-sig").splitlines()]


def load_dotenv(path=ROOT / ".env"):
    """Lit un fichier .env très simple (CLE=valeur) sans dépendance externe.
    Les variables déjà définies dans l'environnement ne sont pas écrasées."""
    if not Path(path).exists():
        example = ROOT / ".env.example"
        if example.exists() and any(l.split("=", 1)[1].strip() for l in read_lines(example)
                                    if "=" in l and not l.startswith("#") and not l.startswith("SMTP_PORT")):
            print("⚠ Vos clés sont dans .env.example, qui est publié sur GitHub : elles ne sont pas lues.\n"
                  "  Lancez : python tools/telegram_setup.py  (il crée .env et vide .env.example)")
        return
    for line in read_lines(path):
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def secret(name):
    """Renvoie la valeur d'un secret, ou None s'il n'est pas défini."""
    value = os.environ.get(name)
    return value if value else None
