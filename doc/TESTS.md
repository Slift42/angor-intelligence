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
| `test_press.py` | Tri de la presse : titres à garder / à écarter (cas réels), gravité, langue, seuils sur le jeu étiqueté, cas de l'audit de production v0.28, localisation (ignorée sans le dictionnaire GeoNames) |
| `test_early_warning.py` | Alerte précoce mondiale : régions communes (couverture, pas de doublon, anciennes zones reprises), outre-mer, climat compact et migration, indice à cinq composantes, comptage par famille, sorties par région, priorité de chargement, liens avec les tendances |
| `test_indicators.py` | Indicateurs structurels : lecture FMI, Banque mondiale, BCE, signaux de seuil, fonctionnement hors ligne |
| `test_foresight.py` | Tendances de risques : configuration publiable, scores et niveaux, pression, contrôle des sources (nombre, éditeurs, cotation), dates et échelles, signal en temps réel, vues pays et région, révision due, historique mensuel, méthode publique |
| `test_corroborate.py` | Recoupement : reprises et groupes de presse, rattachement d'un récit de presse à la mesure USGS, séisme non confirmé, démenti, crédibilité |
| `test_connectors.py` | Flux propres des médias (découverte, lecture, robots.txt) ; filtres des flux (v0.28) : NWS (produits sans valeur, évacuations), Meteoalarm (mer, brouillard), NHC (un bulletin par cyclone, identifiant stable), GDELT (occupation de territoire, capitale en tête de dépêche), tri GDELT |
| `test_robots.py` | robots.txt : règles (groupe du robot, règle la plus longue, jokers), statuts 4xx / 5xx, mémoire d'une semaine, exemption, aucune requête vers une adresse interdite |
| `test_triage.py` | Contrôle d'entrée a priori et permanent : verdicts, fiches invalides, GDELT en attente, avis de l'IA, décision de l'analyste, journal, alarme, priorité des titres GDELT récents |
| `test_pipeline.py` | Dédoublonnage (dont regroupement par histoire, mots rares, même cible, GDELT et presse), tri avant regroupement, cotation de l'Amirauté, note de risque |
| `test_sources.py` | XML abîmé, découpage FCDO, numéros d'urgence, motifs des avis américains (réponse simulée), trafic |
| `test_country_detail.py` | Choix des villes, santé, activité, validité de `config/city_notes.json` |
| `test_providers.py` | Catégories et annuaire, fusion inscrits / repérés (même site = une seule ligne), lecture Supabase simulée, grille de qualité identique (SQL, JS, page publiée) |
| `test_legal.py` | Pages légales (références valides vers `config/legal.json`), champs manquants, absence d'appel à Google Fonts / flagcdn, liens légaux, entretien Supabase |
| `test_risk_workbook.py` | Classeur de revue des risques : onglets, réglages identiques au code, simulateurs en formules, pas d'écrasement, version anglaise complète |

Règles :
- Un bug corrigé = un test qui l'aurait détecté (voir les cas commentés dans `test_press.py`).
- Pas d'appel réseau : simuler la réponse avec `monkeypatch.setattr(module.http, "get_json", ...)`.
- Tests rapides et déterministes (date fixe `NOW` dans `conftest.py`).

## Jeu étiqueté du tri (`tests/gold_tri.csv`)

1 077 titres réels classés à la main (garder 1/0, catégorie attendue), dont 426 tirés des données en ligne en v0.23, 95
en v0.28 (audit de 7 jours d'angor.fr, commentaire « prod 2026-10 ») et 436 au second audit (931 titres du 23 octobre
2026, dont 298 à écarter, commentaire « prod 2026-10-23 »).
« Garder » = un fait physique qui peut toucher un voyageur ou un site ; arrestations, déclarations, analyses,
rétrospectives et travaux de prévention valent 0 (ils restent dans le Fil). `tools/eval_tri.py` mesure précision,
rappel et justesse de la catégorie avec `press.is_event` ; `test_press.py` impose des seuils minimaux (précision ≥ 94 %,
rappel ≥ 98 % ; mesurés en v0.28 : 95 %, 99 % et 99 % de catégories justes ; en v0.23 : 94 % et 100 %, contre 51 % de
précision en v0.22). Sur l'échantillon de production de la v0.28, les règles passent de 34 faux positifs sur 95 à 0, puis, au second audit,
de 277 sur 931 à 7 (mesures v0.28 sur 1 077 titres : précision 95 %, rappel 100 %, catégorie 99 %). Contrôle hors
échantillon : sur 756 titres plus anciens non étiquetés, les nouvelles règles n'en retirent que 7, tous à bon droit.
Les règles ayant été réglées sur ce jeu, elles ont été contrôlées sur une seconde moitié de titres en ligne non étiquetée
(relecture des écarts) ; constituer un **jeu de contrôle** étiqueté distinct avant de publier des chiffres.

## Test de fumée du site (`tests/e2e/smoke.mjs`)

Ouvre chaque page (carte, rapport pays, brief, aide, compte, pages légales) sur ordinateur et sur mobile, parcourt les
espaces, la période, les analyses et le trafic, et échoue à la moindre erreur JavaScript ou si une page déborde
horizontalement. Il fonctionne sans données (`docs/data/` vide) comme avec une collecte locale.
Il a révélé à sa création une erreur réelle (carte du rapport pays initialisée dans le mauvais ordre).

## Schéma Supabase sur un PostgreSQL local

Pour vérifier `supabase/schema.sql` sans compte Supabase (PostgreSQL 15 ou plus) :

```bash
createdb angor_test
psql -d angor_test -v ON_ERROR_STOP=1 -f tools/supabase_stub.sql -f supabase/schema.sql   # deux fois : le script doit être relançable
```

`tools/supabase_stub.sql` imite le schéma `auth`, les rôles `anon` / `authenticated` et `auth.uid()` (utilisateur simulé par
`select set_config('request.jwt.claim.sub', '<uuid>', false); set role authenticated;`). Vérifier au minimum : un utilisateur ne
lit que ses lignes, une acceptation pour autrui ou antidatée est refusée, `anon` ne peut exécuter que `ping()`,
`private.housekeeping()` efface les données expirées (pg_cron n'existe pas en local : le lancer à la main).
