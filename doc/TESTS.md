# Tests

| Niveau | Commande | Durée | Réseau |
|---|---|---|---|
| Analyse statique | `ruff check veille collecte.py historique.py tools tests` | 1 s | non |
| Tests unitaires | `pytest -q` | < 1 s | non (bloqué par `tests/conftest.py`) |
| Qualité du tri de presse | `python tools/eval_tri.py [--erreurs]` | 1 s | non |
| Test de fumée du site | `cd tests/e2e && npm install && npx playwright install chromium && npm test` | 1 min | non (Internet coupé dans le test) |
| Collecte réelle | `python collecte.py --only <source>` | variable | oui |

Les trois premiers et le test de fumée tournent automatiquement à chaque `push` (`.github/workflows/tests.yml`).

## Tests unitaires (`tests/`)

| Fichier | Couvre |
|---|---|
| `conftest.py` | Blocage du réseau, fabrique d'événements `make()`, pays (`countries`) |
| `test_model_geo.py` | Format d'événement, dates, taxonomie, localisation des pays, distances |
| `test_press.py` | Tri de la presse : titres à garder / à écarter (cas réels), gravité, langue, seuils sur le jeu étiqueté |
| `test_pipeline.py` | Dédoublonnage, cotation de l'Amirauté, note de risque |
| `test_sources.py` | XML abîmé, découpage FCDO, numéros d'urgence, motifs des avis américains (réponse simulée), trafic |
| `test_country_detail.py` | Choix des villes, santé, activité, validité de `config/city_notes.json` |

Règles :
- Un bug corrigé = un test qui l'aurait détecté (voir les cas commentés dans `test_press.py`).
- Pas d'appel réseau : simuler la réponse avec `monkeypatch.setattr(module.http, "get_json", ...)`.
- Tests rapides et déterministes (date fixe `NOW` dans `conftest.py`).

## Jeu étiqueté du tri (`tests/gold_tri.csv`)

120 titres réels classés à la main (garder 1/0, catégorie attendue). `tools/eval_tri.py` mesure précision,
rappel et justesse de la catégorie ; `test_press.py` impose des seuils minimaux (précision ≥ 85 %, rappel ≥ 97 %).
Les règles ayant été réglées sur ce jeu, constituer un **jeu de contrôle** distinct avant de publier des chiffres.

## Test de fumée du site (`tests/e2e/smoke.mjs`)

Ouvre chaque page (carte, rapport pays, brief, aide, compte) sur ordinateur et sur mobile, parcourt les
espaces, la période, les analyses et le trafic, et échoue à la moindre erreur JavaScript ou si une page déborde
horizontalement. Il fonctionne sans données (`docs/data/` vide) comme avec une collecte locale.
Il a révélé à sa création une erreur réelle (carte du rapport pays initialisée dans le mauvais ordre).
