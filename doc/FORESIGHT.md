# Tendances de risques (espace Anticipation, v0.26)

Méthode d'anticipation des menaces, région par région et pays par pays. La page publique
`docs/methodologie.html` expose la méthode aux clients ; ce document explique comment la **faire vivre**
(analyste) et comment elle est **codée** (développeur).

## 1. Principe

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
| `config/foresight/regions/<id>.json` | Fiche région : pays membres, emprise `bbox`, perspective, tendances régionales |
| `config/foresight/countries/<ISO2>.json` | Fiche pays : région parente `parent`, perspective, tendances nationales |
| `veille/foresight.py` | Chargement, contrôle, calcul, publication |
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

## 4. Ajouter un pays ou une région

1. Pays d'une région déjà couverte : créer `config/foresight/countries/<ISO2>.json` sur le modèle de `FR.json`
   (`"parent": "weu"`), avec au moins les tendances propres au pays. Les tendances régionales s'y ajoutent
   automatiquement.
2. Nouvelle région : créer `config/foresight/regions/<id>.json` (liste `countries`, `bbox` [ouest, sud, est, nord],
   perspective, tendances), puis passer son `status` à `active` dans `method.json → roadmap`.
3. Ajouter les sources nouvelles dans `sources.json` ; lancer `python tools/check_foresight_sources.py`.
4. Lancer `python -m pytest tests/test_foresight.py` : la configuration doit être publiable.

Priorité de couverture : pays où les clients ont des sites ou des voyageurs, puis pays à risque élevé.
Les indices de l'alerte précoce (Corne de l'Afrique, Sahel) alimenteront les fiches de ces régions.

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

## 6. Pistes

- Indicateurs automatiques (taux à 10 ans, Brent, stocks de gaz AGSI+, ruptures de carburant, vigilances
  Météo-France) affichés à côté des seuils d'alerte.
- Rétro-évaluation : comparer chaque trimestre les scores archivés aux incidents observés.
- Fiches « outre-mer » rattachées à leur région géographique.
- Note d'analyse hebdomadaire (offre premium) générée à partir des tendances qui changent.
