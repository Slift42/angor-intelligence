"""Génère config/country_names.json : noms de pays dans 28 langues (données CLDR via Babel), pour la géolocalisation
des titres de presse (veille/press.py, Gazetteer). À relancer seulement pour ajouter une langue (v0.28).

    pip install babel && python tools/build_country_names.py

Écartés : noms de 3 lettres ou moins, noms partagés par deux pays, mots courants (« island » = Islande en suédois,
« indie » = Inde en polonais, « mali » = petit en croate, « peru » = dindon en portugais, « monaco » = Munich en
italien, « granada », « salvador »…) et, pour les écritures sans espaces, les noms gérés à la main dans
press.SCRIPT_COUNTRY_ALIASES.
"""
import json
import unicodedata
from pathlib import Path

from babel import Locale

ROOT = Path(__file__).resolve().parent.parent
LANGS = ["es", "pt", "de", "it", "nl", "pl", "ro", "tr", "id", "ms", "sv", "da", "nb", "fi", "cs", "sk", "hu", "el", "ru",
         "uk", "bg", "ar", "fa", "ur", "he", "hi", "vi", "ca"]
AMBIGUOUS = {"island", "indie", "mali", "peru", "monaco", "granada", "salvador", "jersey", "guinea", "guine", "guinee",
             "georgia", "jordan", "chad", "dominica", "misir", "chile", "turkey", "man", "congo", "kongo", "sudan",
             "niger", "panama", "cuba", "india", "malta", "oman", "عمان", "togo", "samoa", "tonga", "nauru", "palau",
             "laos", "iran", "irak", "iraq", "polen", "china", "chiny", "japan", "jemen", "macao", "macau", "aruba",
             "curacao", "bermuda", "guadalupe", "canarias", "na uy", "chili", "sark", "kina", "kena", "gana", "sili", "yaman", "gibraltar", "greenland", "gronland", "hongkong", "hong kong", "taiwan", "kosovo",
             "vatican", "vaticano", "hindistan", "brasil", "france", "francia", "franca", "frankrijk", "georgie",
             "gruzja", "georgien", "jordanie", "tsjaad", "cad", "czad", "ciad", "tchad", "nigeria"}
# noms d'États trop proches d'un mot courant dans une autre langue : on garde l'entrée anglaise ou française déjà présente
KEEP = {"france", "francia", "franca", "frankreich", "frankrijk", "brasil", "hindistan", "jordania", "giordania",
        "jordanien", "nigeria", "irak", "iraq"}


def norm(s):
    s = unicodedata.normalize("NFKD", s.translate({0x2019: "'"}))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def main():
    en = Locale("en").territories
    isos = [k for k in en if len(k) == 2 and k.isalpha() and k not in ("ZZ", "EU", "EZ", "UN", "QO", "XA", "XB", "IC", "EA", "DG", "CP", "TA", "AC")]
    seen = {}
    for lang in LANGS:
        terr = Locale.parse(lang).territories
        for iso in isos:
            name = terr.get(iso)
            if not name:
                continue
            k = norm(name)
            if len(k) <= 3 or (k in AMBIGUOUS and k not in KEEP):
                continue
            seen.setdefault(k, set()).add(iso)
    out = {k: sorted(v)[0] for k, v in sorted(seen.items()) if len(v) == 1}
    path = ROOT / "config" / "country_names.json"
    path.write_text(json.dumps({"_comment": "Généré par tools/build_country_names.py (CLDR via Babel) – ne pas modifier à la main",
                                "names": out}, ensure_ascii=False, indent=0, sort_keys=False), encoding="utf-8")
    print(f"{len(out)} noms écrits dans {path}")


if __name__ == "__main__":
    main()
