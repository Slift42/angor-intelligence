# Audit du code et dette technique

Audit réalisé le 4 octobre 2026 (version 0.17), à la demande de l'analyste, sur l'ensemble du dépôt.
À tenir à jour : chaque évolution qui ajoute un raccourci l'inscrit ici ; chaque évolution qui touche une zone
listée la réduit si possible.

## Synthèse

| Question | Réponse |
|---|---|
| Le code est-il réutilisable par un développeur humain ? | **Oui pour le robot Python, avec un effort raisonnable** : modules courts et ciblés, interface de connecteur uniforme, en-têtes explicatifs, une seule dépendance. **Difficilement pour le site** : `app.js` fait 2 800 lignes très denses dans une seule fonction. |
| Que fallait-il pour qu'il le soit ? | Une documentation technique (architecture, contrats de données, procédures), des tests automatiques, des règles de contribution, puis une remise en forme progressive du site (voir le plan ci-dessous). |
| La documentation technique était-elle suffisante ? | **Non.** Il existait une bonne documentation utilisateur (aide, guide de mise en ligne, README) et des en-têtes de module soignés, mais aucune description de l'architecture, des formats de données échangés entre robot et site, ni des tests. Une partie du savoir n'existait que dans l'historique de conversation. **Corrigé en v0.17** (dossier `doc/`). |

## Mesures (v0.17)

| Indicateur | Valeur | Commentaire |
|---|---|---|
| Python | ≈ 8 600 lignes, 45 modules | Modules de 50 à 300 lignes, sauf `press.py` (990), `early_warning.py` (640), `historique.py` (550) |
| JavaScript | ≈ 4 900 lignes, dont `app.js` 2 780 | `app.js` : ≈ 280 fonctions dans une seule closure, 406 lignes de plus de 160 caractères (jusqu'à 540) |
| Tests automatiques | 0 → **32 tests unitaires + test de fumée du site** | Avant l'audit : seul le jeu étiqueté du tri existait |
| Analyse statique (`ruff`, erreurs réelles) | 19 → **0** | Imports inutiles, clés de dictionnaire en double ; les 8 « fermetures en boucle » signalées sont des faux positifs |
| Complexité (McCabe > 15) | 12 fonctions | `collecte.main` 33, `early_warning.score_unit` 32, `historique._gdelt_day` 29, `country_detail.build` 26 |
| `except Exception` | 45 | Voulus (une source en panne ne bloque rien) mais à journaliser systématiquement |

## Défauts trouvés et corrigés pendant l'audit

1. **Tri de la presse** : « Suicide bombing kills 12 at market » était écarté comme un drame privé (le mot
   « suicide » figurait dans la liste des faits divers). Les attentats-suicides sont de nouveau retenus ; test ajouté.
2. **Rapport pays** : la carte des villes plantait dès qu'un pays avait des incidents récents (formes ajoutées à
   la carte avant que sa vue soit fixée). Trouvé par le test de fumée ; corrigé.
3. **Site sans données** : la fiche pays et l'espace Trafic levaient une erreur quand `data.js` est absent
   (première installation, test automatique). Corrigé.
4. Imports inutiles, deux clés en double dans `reports.py`, paramètre par défaut calculé dans `tools/eval_tri.py`.

## Dette restante et plan de remise à niveau

### Priorité 1 – faite en v0.17
- Documentation technique (`doc/`), règles de contribution (`CONTRIBUTING.md`), historique (`CHANGELOG.md`).
- Tests unitaires, test de fumée, analyse statique, tout cela automatisé (`.github/workflows/tests.yml`).

### Priorité 2 – site (prochaines évolutions du front)
- **Découper `app.js`** en modules ES natifs (aucune compilation nécessaire) : `i18n.js` (textes), `state.js`,
  `map.js` (fonds, calques), un fichier par onglet (`tabs/alerts.js`, `tabs/agenda.js`, `tabs/traffic.js`…).
  Méthode : un module à la fois, test de fumée vert à chaque étape.
- **Fonctions partagées** dans `docs/lib/common.js` : `esc`, `icon`, formats de date et de nombre, couleurs de
  risque, liste des pays à majorité musulmane (dupliquée dans `app.js`, `report.js`, `brief.js`), matrice des
  risques (`report.js` / `brief.js`).
- **Lisibilité** : reformater les gabarits HTML très longs (une ligne par élément), JSDoc sur les fonctions publiques.
- **Textes** : sortir le dictionnaire FR/EN (≈ 350 lignes) dans un fichier JSON par langue.

### Priorité 3 – robot
- **`collecte.main`** : découper en étapes nommées (`collect_sources`, `process_press`, `compute_indices`,
  `publish`) pour qu'on puisse lire la chaîne en dix lignes.
- **`press.py`** : séparer les listes de mots-clés (données) de la logique, et élargir le jeu étiqueté avec un
  **jeu de contrôle** indépendant (les règles ont été réglées sur le jeu actuel).
- **Contrats vérifiés** : un schéma JSON de `data.js` et des fiches pays, contrôlé dans les tests.
- **Annotations de types** sur les modules centraux (`model`, `dedupe`, `quality`, `risk`), vérifiées par `mypy`.
- **Journalisation** : chaque `except Exception` écrit au moins le type d'erreur dans le journal.

### Priorité 4 – exploitation
- `publier.bat` produit des messages de commit génériques : encourager des messages explicites (voir `CONTRIBUTING.md`).
- Versions des bibliothèques recopiées : consignées dans `docs/vendor/VERSIONS.md` (v0.17) ; deux versions restent à confirmer.
- Mémoire du robot dans le cache GitHub (expire après 7 jours d'inactivité) : acceptable aujourd'hui ; à migrer vers
  une base (Supabase ou SQLite versionnée) quand les comptes clients seront ouverts.
- Le développement assisté par IA travaille sur une copie du dépôt : **le dépôt Git reste la seule référence** ;
  toute modification passe par un commit lisible.

## Points forts à préserver

- Séparation nette robot / site, contrats de données explicites, aucune dépendance lourde, coût d'hébergement nul.
- Interface de connecteur uniforme ; une source en panne ne bloque jamais la collecte.
- Aucun secret dans le dépôt ni dans le site ; sites clients jamais publiés.
- En-têtes de module explicatifs (sources, licences, choix), commentaires qui expliquent le « pourquoi ».
