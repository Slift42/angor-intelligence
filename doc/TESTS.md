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
| `test_press.py` | Tri de la presse : titres à garder / à écarter (cas réels), gravité, langue, seuils sur le jeu étiqueté, cas des audits de production v0.28 et v0.29 (hors échantillon), localisation (ignorée sans le dictionnaire GeoNames) |
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
| `test_help_en.py` | Aide en anglais : chaque texte de `aide.html` a sa traduction dans `tools/aide_en.json`, `help.html` est à jour (`python tools/build_help_en.py`), mêmes ancres, lien d'aide selon la langue |
| `test_risk_workbook.py` | Classeur de revue des risques : onglets, réglages identiques au code, simulateurs en formules, pas d'écrasement, version anglaise complète |

Règles :
- Un bug corrigé = un test qui l'aurait détecté (voir les cas commentés dans `test_press.py`).
- Pas d'appel réseau : simuler la réponse avec `monkeypatch.setattr(module.http, "get_json", ...)`.
- Tests rapides et déterministes (date fixe `NOW` dans `conftest.py`).

## Jeu étiqueté du tri (`tests/gold_tri.csv`)

1 472 titres réels classés à la main (garder 1/0, catégorie attendue), dont 426 tirés des données en ligne en v0.23, 95
en v0.28 (audit de 7 jours d'angor.fr, commentaire « prod 2026-10 »), 436 au second audit (931 titres du 23 octobre
2026, commentaire « prod 2026-10-23 ») et 395 au contrôle hors échantillon de la v0.29 (titres du 24 octobre,
commentaire « prod 2026-10-24, hors échantillon »).
« Garder » = un fait physique qui peut toucher un voyageur ou un site ; arrestations, procès, hommages, déclarations,
analyses, rétrospectives, annonces, prévisions, alertes sans dégâts et travaux de prévention valent 0 (ils restent dans
le Fil). `tools/eval_tri.py` mesure précision, rappel et justesse de la catégorie avec `press.is_event` ;
`test_press.py` impose des seuils minimaux (précision ≥ 88 %, rappel ≥ 98 %). Mesures v0.29 sur 1 472 titres :
précision 89 %, rappel 99 %, catégorie 98 %.

**Pourquoi le seuil de précision est passé de 94 % à 88 % (v0.29)** : les 395 titres ajoutés sont plus difficiles
(prévisions, annonces, faits mêlés de suites), et surtout ils ont montré que la mesure précédente était flatteuse. Les
règles v0.28, mesurées à 95 % sur ce jeu, n'atteignaient que **54 %** sur 559 titres neufs de la carte. Un chiffre mesuré
sur le jeu qui a servi aux réglages ne dit pas la précision réelle : à chaque audit, étiqueter d'abord un lot de titres
**neufs**, mesurer, puis seulement corriger (`tools/eval_tri.py --erreurs` liste les écarts).

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
