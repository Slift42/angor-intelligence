# Tendances de risques et alerte précoce (espace Anticipation, v0.26 → v0.27)

Méthode d'anticipation des menaces, région par région et pays par pays. La page publique
`docs/methodologie.html` expose la méthode aux clients ; ce document explique comment la **faire vivre**
(analyste) et comment elle est **codée** (développeur).

## 1. Principe

Depuis la v0.27, tendances et alerte précoce forment **un seul outil à trois niveaux de détail**, sur les mêmes
17 régions du monde (`config/foresight/regions/`) :

| Niveau | Contenu | Module |
|---|---|---|
| Région | Tendances régionales (analyste), pression de risque, signaux structurels des pays | `foresight.py` |
| Pays | Tendances nationales + régionales héritées, indicateurs structurels (FMI, Banque mondiale, BCE) | `foresight.py`, `indicators.py` |
| Subdivision | Indice de convergence mensuel (climat, sécurité, société, aléas, humanitaire) | `early_warning.py` |

Les liens sont croisés : chaque tendance liste les subdivisions les plus exposées selon la composante qui lui
correspond (climat → `cl`, sécurité et géopolitique → `co`, société et politique → `so`, infrastructures, énergie,
cyber, santé → `hz`, humanitaire → `hu`) ; chaque subdivision liste les tendances de son pays et de sa région.

```
facteurs (13 familles, 27 facteurs, indicateurs + sources)
   └─► tendances (fiche région ou pays) : vraisemblance × impact entreprise / voyageur, horizon, dynamique, confiance
          ├─ signaux datés et sourcés      ├─ indicateurs d'alerte    ├─ scénario de rupture
          ├─ implications, recommandations └─ tendances liées (cascades)
   └─► calcul automatique : score 1–25, niveau, pression 0–100, contrôle qualité, révision due, signal en temps réel
```

Le robot **ne fixe jamais** la vraisemblance ni l'impact : c'est le jugement de l'analyste. Il calcule, contrôle
et signale.

## 2. Fichiers

| Fichier | Contenu |
|---|---|
| `config/foresight/method.json` | Échelles (vraisemblance, impacts, horizons et délais de révision, dynamique, confiance, niveaux, cotation des sources), règles qualité, paramètres du signal en temps réel, secteurs, familles, facteurs et indicateurs, feuille de route des 17 régions |
| `config/foresight/sources.json` | Bibliographie : titre `t`, éditeur `pub` (sert au contrôle d'indépendance), `url`, date `d`, type `kind`, cotation `rel` (A–F), note éventuelle |
| `config/foresight/regions/<id>.json` | Fiche région (17, monde entier) : pays membres, emprise `bbox`, perspective, tendances régionales (vides tant qu'elles ne sont pas rédigées) |
| `config/foresight/countries/<ISO2>.json` | Fiche pays : région parente `parent`, perspective, tendances nationales |
| `veille/foresight.py` | Chargement, contrôle, calcul, publication ; `regions()` pour l'alerte précoce |
| `veille/early_warning.py` | Alerte précoce par subdivision (voir § 6) |
| `veille/indicators.py` | Indicateurs structurels par pays (voir § 7) |
| `config/early_warning.json` | Rythme de remplissage et priorité des régions de l'alerte précoce |
| `docs/foresight.js` | Onglet « Tendances » (`window.AngorFS`) |
| `docs/methodologie.html` | Méthode publique (lit `data/foresight_method.js`) |
| `tools/check_foresight_sources.py` | Vérification des liens de la bibliographie |

Sorties : `docs/data/foresight.js` (`VS_FS`, tendances complètes, **réservé aux comptes validés** par le coffre) et
`docs/data/foresight_method.js` (`VS_FS_METHOD`, méthode et bibliographie sans les tendances, **public**).

## 3. Rédiger ou réviser une tendance (analyste)

Champs d'une tendance (voir les fiches existantes comme modèles) :

| Champ | Règle |
|---|---|
| `id` | unique, préfixé par le périmètre (`fr-`, `weu-`) |
| `family`, `also` | familles de `method.json` |
| `title`, `summary` | `{fr, en}`, phrases courtes, sans jargon |
| `drivers` | identifiants des facteurs de `method.json` |
| `likelihood` | 1–5 : probabilité que la tendance se concrétise **avec l'impact décrit** à l'horizon |
| `impact.business`, `impact.travel` | 1–5, selon les descriptions des échelles |
| `horizon` | `3m`, `12m` ou `36m` (révision au plus tard à 30, 60 ou 120 jours) |
| `momentum` | 1 hausse, 0 stable, −1 baisse |
| `confidence` | `low`, `medium`, `high` (qualité et concordance des sources) |
| `signals` | faits `{fr, en, src: [ids], d: "AAAA-MM-JJ"}` ; chaque fait cite au moins une source |
| `watch` | indicateurs d'alerte `{fr, en}`, avec seuils quand c'est possible |
| `rupture` | scénario du pire plausible `{fr, en}` |
| `implications` | `{business: {fr, en}, travel: {fr, en}}` |
| `actions` | `{business: [{fr, en}], travel: [{fr, en}]}` |
| `sectors` | clés de `method.json → sectors` |
| `live` | catégories d'incidents Angor à surveiller (`unrest`, `terrorism`, `cyber`…) ou `[]` |
| `links` | identifiants de tendances liées |
| `reviewed` | date de la dernière revue (AAAA-MM-JJ) |

Contrôles automatiques (`foresight.validate`, aussi joués par les tests) : au moins **2 sources** venant d'au
moins **2 éditeurs** différents ; au plus **50 %** de sources cotées D–F ; dates jamais dans le futur ; échelles,
facteurs, familles, secteurs, catégories et liens existants ; textes bilingues. Une anomalie est écrite dans le
journal de collecte ; les tests échouent tant qu'elle n'est pas corrigée.

Révision : changer les valeurs, ajouter les nouveaux signaux, mettre à jour `reviewed`. Avant de monter ou de
descendre une tendance de deux niveaux, faire relire (relecture contradictoire).

**Après la décision de Moody's du 23 octobre 2026**, réviser `fr-debt` (et `fr-gov` si besoin).

## 4. Rédiger les tendances d'un pays ou d'une région

Les 17 régions existent déjà (pays, emprise) : l'alerte précoce et les indicateurs les couvrent. Pour les tendances :

1. Région : remplir `perspective` (`outlook`), `reviewed` et `trends` dans `config/foresight/regions/<id>.json`.
2. Pays : créer `config/foresight/countries/<ISO2>.json` sur le modèle de `FR.json` (`"parent"` = sa région), avec au
   moins les tendances propres au pays. Les tendances régionales s'y ajoutent automatiquement.
   Un pays ne peut appartenir qu'à une région (contrôlé par `validate` et les tests).
3. Ajouter les sources nouvelles dans `sources.json` ; lancer `python tools/check_foresight_sources.py`.
4. Lancer `python -m pytest tests/test_foresight.py` : la configuration doit être publiable.

Priorité de rédaction : pays où les clients ont des sites ou des voyageurs, puis pays à risque élevé. Les
subdivisions les plus exposées (alerte précoce) et les signaux structurels aident à choisir et à étayer les tendances.

## 5. Calculs

- `score(t)` : `likelihood × impact` pour l'entreprise, le voyageur, et le maximum des deux (`all`).
- Niveaux : 1–4 faible, 5–9 modéré, 10–14 élevé, 15–19 très élevé, 20–25 critique.
- `pressure(scores)` : moyenne des 5 scores les plus élevés × 4 (0–100). Pays = tendances nationales + régionales ;
  région = régionales + nationales de ses pays.
- `live_signal` : incidents vérifiés des catégories `live` dans le périmètre, 30 derniers jours contre la moyenne
  des 90 jours précédents ramenée à 30 jours ; hausse nette si au moins 3 incidents et rapport ≥ 1,5 ; baisse nette
  si la base atteint 3 incidents et rapport ≤ 0,6. Drapeaux : `live_up` (hausse alors que `momentum ≤ 0`),
  `live_down` (baisse alors que `momentum = 1`), `review_due` (révision dépassée).
- `snapshot` : scores du mois dans `store["state"]["foresight"]["history"]` (36 mois), affichés sur chaque fiche et
  destinés à la rétro-évaluation.

## 6. Alerte précoce par subdivision (`early_warning.py`)

- Subdivisions : geoBoundaries ADM1, `boundaries_per_run` nouveaux pays par collecte (ordre : `priority` des régions,
  puis pays où Angor relève le plus d'incidents), gardées dans `data/ew_units/<ISO2>.json` ; simplification adaptée à
  la taille. Une subdivision loin de la région de son pays (outre-mer) est rattachée à sa région géographique.
- Climat : NASA POWER, 16 ans de séries mensuelles par subdivision (`power_per_run` par collecte, relu tous les
  `power_refresh_days` jours), stockage compact (`y0` + tableaux).
- Incidents : incidents vérifiés en mémoire (toute la durée de conservation), comptés par mois et par famille
  (`FAMILIES`) ; aléas, infrastructures et santé à partir de la gravité 2 ; historique UCDP/GDELT pour les mois
  antérieurs au comptage en direct (`live_start`), une fois par pays.
- Humanitaire : HDX HAPI, `hapi_per_run` pays par collecte ; un pays sans donnée n'est relu que tous les
  `hapi_empty_refresh_days` jours.
- Indice (`score_unit`) : climat 30, sécurité 30, société et politique 15, aléas-infrastructures-santé 10, humanitaire
  15 ; sans humanitaire, total ramené sur 100. Niveaux 20 / 40 / 60.
- Rétro-évaluation (`backtest`, une fois par jour) sur les subdivisions ayant connu au moins un incident.
- Sorties : `docs/data/early_warning.js` (index) et `docs/data/early_warning/<région>.js` (subdivisions) ; `update`
  renvoie aussi un résumé par subdivision, transmis à `foresight.update` pour les liens.
- Migration automatique de la mémoire v2 (Corne, Sahel) : unités → fichiers par pays, climat → format compact,
  comptages refaits par famille.

## 7. Indicateurs structurels (`indicators.py`)

- FMI DataMapper (`NGDP_RPCH`, `PCPIPCH`, `GGXWDG_NGDP`, `LUR`) chaque semaine ; Banque mondiale WGI (source 3,
  scores 0–100 : `GOV_WGI_PV.SC`, `GE`, `RL`, `CC`) chaque mois ; BCE `IRS` (10 ans, UE) tous les 3 jours.
- Signaux (`FLAGS`) : récession, inflation ≥ 10 %, dette ≥ 100 % du PIB, chômage ≥ 15 %, stabilité < 20/100, écart
  avec l'Allemagne ≥ 150 pb. Affichés dans les fiches pays et, pour une région, la liste des pays concernés.
- En cas de panne d'une source, la dernière mémoire est conservée (`data/indicators.json`).

## 8. Pistes

- Indicateurs automatiques supplémentaires : Brent, stocks de gaz AGSI+ (clé gratuite), ruptures de carburant,
  coupures d'Internet (IODA), vigilances Météo-France, affichés à côté des seuils d'alerte.
- Rétro-évaluation : comparer chaque trimestre les scores archivés aux incidents observés.
- Rédaction des tendances des 16 autres régions, en commençant par l'Afrique de l'Ouest et Sahel, l'Afrique de
  l'Est et le Moyen-Orient (alerte précoce déjà historisée).
- Note d'analyse hebdomadaire (offre premium) générée à partir des tendances qui changent.
