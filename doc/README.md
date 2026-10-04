# Documentation technique – Angor Intelligence

Documentation destinée aux développeurs qui reprennent, maintiennent ou font évoluer l'outil.
La documentation utilisateur est ailleurs : `docs/aide.html` (aide en ligne), `GUIDE_MISE_EN_LIGNE.md`
(mise en service pas à pas pour un non-développeur) et `README.md` (présentation et historique fonctionnel).

| Document | Contenu |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Vue d'ensemble, chaîne de collecte, modules Python, pages web, hébergement |
| [DONNEES.md](DONNEES.md) | Contrats de données : format d'un événement, fichiers publiés (`docs/data/*.js`), configuration (`config/*.json`), mémoire du robot (`data/`) |
| [CONNECTEURS.md](CONNECTEURS.md) | Ajouter ou modifier une source (interface d'un connecteur, déclaration, licences) |
| [FRONTEND.md](FRONTEND.md) | Le site : pages, organisation de `app.js`, état, traductions, ajout d'un onglet ou d'un calque |
| [EXPLOITATION.md](EXPLOITATION.md) | Faire tourner en local, déployer, secrets, robots GitHub Actions, pannes connues, classeur de revue des risques |
| [RGPD.md](RGPD.md) | Textes légaux (où ils sont, comment les modifier), check-list avant commercialisation, registre des traitements, procédures RGPD |
| [TESTS.md](TESTS.md) | Tests unitaires, test de fumée du site, jeu étiqueté du tri, analyse statique |
| [DETTE_TECHNIQUE.md](DETTE_TECHNIQUE.md) | Audit du code (octobre 2026), limites connues et plan de remise à niveau |

Règles de contribution (dont l'obligation de tenir cette documentation à jour) : [`CONTRIBUTING.md`](../CONTRIBUTING.md).
Historique des versions : [`CHANGELOG.md`](../CHANGELOG.md).

## Prise en main en 30 minutes

1. Lire [ARCHITECTURE.md](ARCHITECTURE.md) (10 min) : le schéma suffit à comprendre le flux.
2. Installer et lancer en local (voir [EXPLOITATION.md](EXPLOITATION.md#faire-tourner-en-local)) :
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   python collecte.py --only usgs gdacs us_advisories   # collecte partielle, 1 minute
   python -m http.server 8000 --directory docs           # puis http://localhost:8000
   ```
3. Lancer les tests : `pytest -q` (moins d'une seconde, sans réseau).
4. Lire le contrat de données qui concerne votre évolution dans [DONNEES.md](DONNEES.md).

## Langue

Le code, les commentaires et la documentation sont en français (équipe et clients francophones).
Les identifiants techniques (noms de fonctions, clés JSON) sont en anglais. Les textes affichés sont bilingues FR/EN.
