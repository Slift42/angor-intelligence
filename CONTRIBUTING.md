# Contribuer à Angor Intelligence

Ces règles valent pour **toute** évolution, qu'elle soit écrite par un développeur ou par un assistant IA.
Elles existent pour qu'un développeur qui découvre le projet puisse le comprendre, le maintenir et le faire
évoluer sans dépendre de la mémoire de qui que ce soit.

## Définition de « terminé »

Une évolution n'est terminée que si **toutes** les cases sont cochées :

- [ ] **Tests** : `pytest -q` vert ; un test ajouté pour chaque nouvelle fonction de calcul et pour chaque bug corrigé ;
      `ruff check veille collecte.py historique.py tools tests` sans erreur ;
      test de fumée du site (`tests/e2e`) vert si une page web a changé.
- [ ] **Documentation technique** (`doc/`) à jour :
  - nouveau fichier publié, nouveau champ ou changement de format → [`doc/DONNEES.md`](doc/DONNEES.md) ;
  - nouvelle source → [`doc/CONNECTEURS.md`](doc/CONNECTEURS.md) (et licence vérifiée) ;
  - nouveau module ou nouvelle étape du robot → [`doc/ARCHITECTURE.md`](doc/ARCHITECTURE.md) ;
  - nouvel onglet, calque ou section du site → [`doc/FRONTEND.md`](doc/FRONTEND.md) ;
  - nouveau secret, workflow ou panne connue → [`doc/EXPLOITATION.md`](doc/EXPLOITATION.md) ;
  - raccourci assumé ou limite connue → [`doc/DETTE_TECHNIQUE.md`](doc/DETTE_TECHNIQUE.md).
- [ ] **En-tête de module** : tout nouveau fichier commence par un commentaire qui dit ce qu'il fait, ses sources
      (avec licence) et ce qu'il produit.
- [ ] **Documentation utilisateur** : `docs/aide.html` si l'utilisateur voit un changement ; `GUIDE_MISE_EN_LIGNE.md`
      si une manipulation est nécessaire (secret, compte, réglage).
- [ ] **Version** : `__version__` dans `veille/__init__.py` et une entrée dans [`CHANGELOG.md`](CHANGELOG.md).
- [ ] **Sécurité et conformité** : aucun secret dans le code, la configuration ou le site ; aucune donnée
      personnelle (on suit des événements, pas des personnes) ; titre + résumé + lien seulement pour la presse.
- [ ] **RGPD et textes légaux** : nouvelle donnée personnelle, nouveau prestataire ou nouveau service tiers appelé par le
      navigateur → `config/legal.json` (sous-traitants, services tiers), politique de confidentialité et registre de
      [`doc/RGPD.md`](doc/RGPD.md) ; texte légal modifié → nouvelle version dans `config/legal.json`.

## Conventions de code

**Python** (`veille/`, `collecte.py`)
- Python 3.11+, bibliothèque standard + `requests` uniquement (justifier toute nouvelle dépendance).
- Réseau uniquement via `veille/http.py` ; temps borné (`timeout`, budget par collecte).
- Une étape annexe ne doit jamais faire échouer la collecte : `try/except` avec message clair dans le journal.
- Fonctions courtes et nommées par ce qu'elles font ; docstring pour toute fonction publique.
- Lignes de 140 caractères au plus pour le nouveau code.

**JavaScript / CSS** (`docs/`)
- Pas de framework ni de compilation : le dossier `docs/` doit rester publiable tel quel.
- Toute donnée affichée passe par `esc()` ; tout texte affiché a sa traduction FR **et** EN.
- Couleurs via les variables CSS (thèmes clair et sombre) ; vérifier l'affichage mobile (860 px et 390 px).
- Nouveau code : une fonction par responsabilité, lignes lisibles (éviter les gabarits de plus de 160 caractères).
- Les URL de scripts gardent leur empreinte `?v=…` (réécrite par le robot).

**Données et configuration**
- Les fichiers de `config/` sont commentés (`_comment` / `_note`) ; une nouvelle clé y est expliquée.
- Les fichiers générés vont dans `.gitignore` ; les référentiels figés sont versionnés et leur outil de génération est dans `tools/`.

## Messages de commit

Une ligne qui dit ce qui change et pourquoi, au présent : `press : retient les attentats-suicides (faux « drame privé »)`.
`publier.bat` produit un message générique : pour une évolution importante, préférer `git commit -m "…"`
avant de lancer `publier.bat`.

## Avant de commencer une évolution

1. Lire [`doc/README.md`](doc/README.md) et le contrat de données concerné.
2. Lancer les tests pour partir d'un état vert.
3. Consulter [`doc/DETTE_TECHNIQUE.md`](doc/DETTE_TECHNIQUE.md) : ne pas aggraver une dette listée, la réduire si on touche la zone.
