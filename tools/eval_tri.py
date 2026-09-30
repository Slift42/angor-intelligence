"""Mesure la fiabilité du tri automatique sur un jeu de titres classés à la main (tests/gold_tri.csv).

Colonnes : titre, pays, garder (1 = incident utile pour une organisation ou un voyageur, 0 = à écarter),
categorie (catégorie attendue si garder = 1), commentaire.
Usage : python tools/eval_tri.py [--erreurs]
Résultat : précision (part des titres gardés qui méritaient de l'être), rappel (part des titres utiles retrouvés),
exactitude de la catégorie (par famille : violence, troubles, catastrophes…), et la liste des erreurs.
Relancez-le après chaque réglage des mots-clés : le chiffre doit monter, jamais baisser.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from veille import press  # noqa: E402

FAMILY = {"attack": "violence", "armed_conflict": "violence", "terrorism": "violence", "crime": "violence",
          "unrest": "troubles", "political": "troubles", "diplomatic": "troubles",
          "cyclone": "tempête", "storm": "tempête"}


def fam(c):
    return FAMILY.get(c, c)


def evaluate(path=Path(__file__).resolve().parent.parent / "tests" / "gold_tri.csv"):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    tp = fp = fn = tn = cat_ok = 0
    errors = []
    for r in rows:
        want = r["garder"].strip() == "1"
        cat, _ = press.classify(r["titre"])
        got = bool(cat) and not press.not_incident(r["titre"], cat)
        if want and got:
            tp += 1
            if fam(cat) == fam(r["categorie"]):
                cat_ok += 1
            else:
                errors.append(("catégorie", r["titre"], f"attendu {r['categorie']}, obtenu {cat}"))
        elif want:
            fn += 1
            errors.append(("oublié", r["titre"], f"attendu {r['categorie']}"))
        elif got:
            fp += 1
            errors.append(("bruit", r["titre"], f"classé {cat}"))
        else:
            tn += 1
    n = len(rows)
    res = {"titres": n, "exactitude": (tp + tn) / n if n else 0, "precision": tp / (tp + fp) if tp + fp else 0,
           "rappel": tp / (tp + fn) if tp + fn else 0, "categorie": cat_ok / tp if tp else 0,
           "gardes": tp + fp, "utiles": tp + fn}
    return res, errors


if __name__ == "__main__":
    res, errors = evaluate()
    print(f"Jeu de test : {res['titres']} titres ({res['utiles']} incidents utiles)")
    print(f"  Exactitude du tri : {res['exactitude']:.0%}")
    print(f"  Précision        : {res['precision']:.0%}  (titres gardés qui sont de vrais incidents)")
    print(f"  Rappel           : {res['rappel']:.0%}  (incidents utiles retrouvés)")
    print(f"  Bonne catégorie  : {res['categorie']:.0%}  (parmi les incidents retrouvés, par famille)")
    if "--erreurs" in sys.argv:
        for kind, title, info in errors:
            print(f"  [{kind}] {title[:100]} → {info}")
