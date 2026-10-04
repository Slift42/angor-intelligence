# Historique des versions

Format : une entrée par version, la plus récente en haut. Chaque entrée dit **ce qui change pour l'utilisateur**
puis, si besoin, **ce qui change pour le développeur** (fichiers, données, configuration). Le numéro de version
est dans `veille/__init__.py` (`__version__`) et s'affiche dans « État des sources ».

## v0.21 – Carte réservée aux comptes, nouveaux marqueurs, fond réaliste, justificatifs prestataires (octobre 2026)

- **Mode visiteur** : sans compte validé, seule la carte des évènements s'affiche (ni panneau, ni filtres, ni couches, ni fiches
  pays, ni détail). Un clic sur un marqueur ouvre une bulle résumée (catégorie, gravité, lieu, date) avec « Créer un compte » et
  « Se connecter » ; un compte en attente voit « Compte en attente de validation ». Les comptes validés retrouvent l'outil complet.
  Limite : masquage d'interface – les fichiers de données restent publics tant qu'ils ne sont pas servis depuis Supabase.
- **Marqueurs redessinés** : pastilles en relief (dégradé, anneau translucide, ombre), apparition animée, ondes concentriques pour
  les gravités élevées et critiques, point blanc pour les incidents de moins de 6 h, contour pointillé pour la détection automatique,
  effet au survol ; animations coupées si le système demande moins de mouvement.
- **Groupes** : nombre sur disque sombre et anneau découpé par gravité ; **au survol**, les catégories du groupe se déploient en
  étoile autour du nombre (icône, nombre, nom au survol), reliées par des traits ; clic = zoom sur ces seuls incidents (ou ouverture
  s'il n'y en a qu'un).
- **Fond « Réaliste (relief) »** : carte physique (relief ombré, teintes d'altitude, fonds marins) avec étiquettes d'atlas jusqu'au
  zoom 8, puis imagerie satellite ; calque pays plus transparent sur ce fond.
- **Justificatifs des prestataires** : nouveaux types (registre du commerce, licence ou autorisation professionnelle, assurance RC
  pro avec date de fin obligatoire, certification ISO…, CV des équipes clés, attestation fiscale ou sociale) et liste de contrôle
  avec points et état de chaque pièce. **Nouvelle grille** : les justificatifs pèsent 55 points sur 100 (sans eux, plafond à 45 et
  niveau D) ; l'extrait d'immatriculation est **obligatoire pour soumettre** la fiche, et sa validation pour la vérifier (règles
  appliquées par la base). Administration : bouton « Vérifier » bloqué tant que l'immatriculation n'est pas validée.
- Conditions de l'annuaire 1.1 (critères publiés) et politique de confidentialité 1.2 (CV des équipes des prestataires) : à accepter
  de nouveau à la connexion suivante.
- Développeur : **relancer `supabase/schema.sql`** (contrainte `provider_documents_kind_check`, `private.doc_active`, nouvelle
  `private.provider_score`, garde de soumission / vérification, recalcul des scores) ; `docs/providers-lib.js` (`DOC_KINDS`,
  `docActive`, `canSubmit`, `canVerify`) ; `app.js` (`GUEST`, `applyGuest`, `guestPopup`, `clusterIcon`, `showBurst`, `zoomToCat`) ;
  `compte.html?mode=signup` ; tests `test_providers.py` (types et obligations) et e2e (mode visiteur).

## v0.20 – Annuaire des prestataires de services aux voyageurs (octobre 2026)

- **Comptes « prestataire »** : à l'inscription, choix Client / Prestataire de services (jets privés, sécurité, sûreté,
  assistance médicale, chauffeurs, taxis, meet & greet… 25 catégories en 4 groupes, cumulables). Inscription et référencement
  gratuits, sans option payante.
- **Espace prestataire** (`prestataire.html`) : fiche d'identification et de services (identité légale, catégories, pays et villes,
  présentation FR/EN, contacts 24/7, tarifs fixes, assurance, agréments et certifications, justificatifs privés, photos, liens vidéo,
  site web, LinkedIn et autres liens), **score de qualité en direct** (0 à 100) avec la liste de ce qui manque, soumission à
  l'annuaire, demandes de devis et avis reçus avec droit de réponse.
- **Fiche publique** pour les clients validés : contacts, tarifs, garanties, photos, avis (un par client, sans contrepartie,
  contrôlés a posteriori) et formulaire de demande de devis.
- **Niveaux de fiabilité** A à E (vert → rouge) : A/B vérifié par Angor, C/D inscrit (selon la complétude), E repéré par Angor
  « non vérifié – à contacter séparément ». Classement = niveau puis score ; les avis n'y entrent pas.
- **Fiche pays (carte)** : « N prestataires de services disponibles » avant « À venir », catégories avec leur nombre, couleur du
  meilleur niveau disponible, liste au clic ; lien « Référencez-vous gratuitement ». Rapport pays : même annuaire, avec niveaux.
- **Administration → Prestataires** : vérification des fiches et des justificatifs (ouverture par lien temporaire), suspension,
  modération des avis ; badge « prestataire » dans la liste des utilisateurs.
- **Conditions de l'annuaire** (`annuaire.html`, acceptées par les prestataires) : critères de classement publiés (L111-7 Code de la
  consommation, règlement P2B), règles des avis, visibilité des informations ; CGU et politique de confidentialité en version 1.1.
- Développeur : **relancer `supabase/schema.sql`** (tables providers, provider_documents, provider_reviews, provider_requests,
  compartiments de fichiers, colonne profiles.account_type) ; `config/providers.json` (catégories, niveaux),
  `config/providers_directory.json` (prestataires repérés, remplace `tools/providers_src.py`), `veille/providers.py`,
  `docs/providers-lib.js` (grille de qualité identique à la base, vérifiée par `tests/test_providers.py`).

## v0.19.1 – Base des comptes durcie (conseiller de sécurité Supabase)

- Plus aucune fonction à privilèges exécutable sans connexion ; toutes fixent leur `search_path`.
- Fonctions des règles d'accès déplacées dans un schéma `private` non exposé par l'API (`public.is_admin()` /
  `is_approved()` restent, sans privilège, pour les fonctions Edge).
- `accept_legal` sans privilège : insertion autorisée par une règle d'accès, uniquement pour soi, sans pouvoir fixer la date.
- Effacement des données expirées planifié **dans la base** chaque nuit (pg_cron) au lieu d'être déclenché par le robot ;
  le robot n'envoie plus qu'un signe de vie (`ping()`) pour éviter la mise en pause du projet gratuit.
- Deux avertissements restent attendus (`admin_set_status`, `delete_my_account`), documentés dans le guide (H2).
- Développeur : **relancer `supabase/schema.sql`** ; test `test_schema_supabase_durci` ; `tools/supabase_stub.sql` imite les
  droits par défaut de Supabase.

## v0.19 – Informations légales, RGPD et préparation des comptes clients (octobre 2026)

- **Pages légales** (projet à compléter et relire) : mentions légales, CGU, CGV (professionnels et consommateurs : rétractation
  avec « Renoncer au contrat ici », résiliation en ligne, médiation, garantie légale), politique de confidentialité et cookies,
  accord de sous-traitance (art. 28 RGPD) pour les clients professionnels, sources et licences ; page d'accueil
  « Informations légales ». Identité de l'éditeur, prestataires, offres et versions dans **un seul fichier** :
  `config/legal.json` (champs vides signalés « [à compléter] », bandeau « Projet » tant que le statut n'est pas « en vigueur »).
- **Comptes** : case « J'accepte les CGU et j'ai pris connaissance de la politique de confidentialité » à l'inscription,
  preuve horodatée et versionnée (table `legal_acceptances`), nouvelle acceptation demandée quand une version change,
  colonne « Conditions » dans Administration, liens légaux sur toutes les pages.
- **Durées de conservation appliquées automatiquement** (`housekeeping()` appelée par le robot) : réponses aux safety checks
  12 mois, position 30 jours, demandes jamais validées 6 mois. Le même appel évite la mise en pause du projet Supabase gratuit.
- **Plus aucun appel à Google** : polices et drapeaux hébergés sur le site (`docs/vendor/fonts`, `docs/vendor/flags`).
- **Guide de mise en ligne, partie H** réécrite : projet Supabase pas à pas, réglages de connexion, e-mails en français
  (`supabase/templates/`) et serveur d'envoi européen, test du parcours client, sécurité et exploitation.
- Développeur : `veille/legal.py`, `veille/accounts.py`, `docs/legal.js`, `docs/legal.css`, `doc/RGPD.md` (registre des
  traitements, check-list avant commercialisation) ; **relancer `supabase/schema.sql`** ; `tools/supabase_stub.sql` pour tester
  le schéma sur un PostgreSQL local ; liens d'e-mail redirigés vers `compte.html` ; cache du service worker v3 ; tests
  `tests/test_legal.py` et pages légales dans le test de fumée.

## v0.18.1 – Classeur de revue en anglais (octobre 2026)

- **Version anglaise** du classeur : `python tools/build_risk_workbook.py --lang en` →
  `revue/Angor_risk_analysis_review.xlsx`. Mêmes onglets, réglages, simulateurs et résultats ; onglets, en-têtes,
  explications, listes déroulantes, textes des formules, notes de villes et noms de pays traduits. Les noms de médias,
  mots-clés, titres du jeu de test et identifiants restent dans leur langue d'origine.
- Développeur : traduction après construction (`tools/workbook_i18n.py`) à partir de la table
  `tools/risk_workbook_en.json` (≈ 1 000 textes ; nombres variables en `{0}`) ; `--missing` liste les textes à ajouter.
  Liens du sommaire désormais internes (ils pointaient vers le nom du fichier, cassés si on le renommait).
  Test : la version anglaise ne laisse aucun texte non traduit hors notes de villes.

## v0.18 – Classeur de revue de l'analyse des risques (octobre 2026)

- **Classeur Excel** `revue/Analyse_des_risques_Angor.xlsx`, produit par `python tools/build_risk_workbook.py` :
  19 onglets (échelles, catégories, règles de gravité, note pays, matrice des menaces, Pulse, cotation, médias,
  sources, mots-clés, jeu de test, fiabilité et alertes, alerte précoce, go / no-go, recommandations, villes,
  santé, journal des décisions). Chaque onglet montre la **valeur actuelle** lue dans le code et une colonne
  jaune pour la proposition de l'analyste ; cinq **simulateurs** en formules Excel reproduisent les calculs
  (note pays, matrice des menaces, Pulse, alerte précoce, go / no-go) pour tester un réglage avant de le retenir.
- Développeur : `revue/` est ignoré par Git (choix de méthode non publiés) ; un classeur existant n'est jamais
  écrasé (le nouveau prend la date, sauf `--force`) ; `openpyxl` ajouté à `requirements-dev.txt` ;
  test `tests/test_risk_workbook.py` (les réglages affichés sont bien ceux du code).

## v0.17 – Audit du code et documentation technique (octobre 2026)

- **Documentation technique** complète dans `doc/` : architecture, contrats de données, connecteurs, site,
  exploitation, tests, dette technique. Règles de contribution dans `CONTRIBUTING.md`, historique déplacé ici.
- **Tests automatiques** : 32 tests unitaires sans réseau (`pytest -q`), test de fumée du site sur ordinateur et
  mobile (`tests/e2e/`), analyse statique (`ruff`), lancés à chaque envoi (`.github/workflows/tests.yml`).
- **Corrections trouvées par l'audit** :
  - « Suicide bombing kills 12… » était écarté comme un drame privé (mot « suicide ») : les attentats-suicides sont de nouveau retenus ;
  - la carte du rapport pays plantait pour les pays ayant des incidents récents (ordre d'initialisation Leaflet) ;
  - sans données publiées, la fiche pays et l'espace Trafic provoquaient une erreur ;
  - imports inutiles et clés en double supprimés.

## v0.16 – Trafic sur la carte

- **Avions** : `veille/traffic.py` lit adsb.lol (ODbL, sans inscription) à chaque collecte → `docs/data/traffic.js` : militaires du monde entier, codes de détresse 7500/7600/7700, tous les vols de 7 zones d'intérêt. Instantané (30 min), car l'API refuse les appels directs depuis un navigateur.
- **Navires** : Baltique en direct depuis le navigateur (Digitraffic, AIS ouvert, CC BY 4.0), actualisé chaque minute.

## v0.15 – Analyses multi-catégories et espace Trafic

- **Analyses** : plusieurs catégories cochables à la fois ; l'évolution affiche une courbe par sélection, superposées pour comparer.
- **Espace Trafic** (préparé) : onglets Aérien et Maritime, liens vers Flightradar24, ADS-B Exchange, adsb.lol, airplanes.live, MarineTraffic, VesselFinder et MyShipTracking calés sur la vue de la carte, aperçu intégré quand le service l'autorise, zones d'intérêt (Bab el-Mandeb, Ormuz, Suez, mer Noire…). Flux sur la carte à brancher via `config/settings.json` → `traffic` (clés dans les secrets).

## v0.14 – Dossier pays et carte

- **Période** : menu déroulant (24 h → tout l'historique, période personnalisée).
- **Carte** : plus de zones noires au déplacement (rendu étendu autour de l'écran) ; thème sombre « Angor Night » (mers bleu nuit, terres ardoise, relief Natural Earth) et couleurs de risque lumineuses.
- **Rapport pays refondu** (`docs/report.html`, `report.js`, `dossier.css`) : couverture, synthèse, sûreté détaillée par menace avec le texte FCDO, villes, voyage, santé et secours, calendrier… PDF A4 avec pied de page numéroté.
- **Données** : `veille/fcdo.py` (texte FCDO découpé en rubriques, OGL v3), `veille/country_detail.py` → `docs/data/country/<ISO>.js` (villes Natural Earth, aéroports OurAirports, numéros d'urgence worldhotlines.org, santé `config/health.json`, notes `config/city_notes.json`), motifs des avis américains (`reasons`).

## v0.13 – Lot 1 : crédibilité et ergonomie

- **Quatre espaces** (Veille, Pays, Mes sites, Anticipation) avec sous-onglets, sur ordinateur et sur mobile.
- **Mode fiable** par défaut : détections automatiques cotées D/E/F masquées tant qu'elles ne sont pas recoupées.
- **Recherche unique** : pays, villes, vos sites, incidents, rapports.
- **Fiches d'alerte** : une ligne « pourquoi c'est important » (distance au site, crise, pays suivi, recoupement…), un seul badge.
- **Dédoublonnage** : fusion des fiches d'une même source (presse sur plusieurs jours, alertes NWS/Meteoalarm par zone).
- **Géolocalisation** : ville cherchée dans le chapeau, puis province (`veille/admin1.py`, geoBoundaries) ; incidents GDELT régionaux précisés par le titre de l'article.
- **Langue** devinée pour chaque titre (écriture, mots-outils) : la traduction automatique en profite.
- **Fiabilité mesurée** : `tests/gold_tri.csv` (120 titres étiquetés) et `python tools/eval_tri.py --erreurs` ; qualité des sources apprise des décisions de l'analyste (`quality.learn`).
- **Boucle analyste** : boutons Valider / Fausse alerte dans chaque fiche, enregistrement direct dans `config/verified.json`.
- **Alerte précoce** : validation a posteriori sur 40 mois (dont Soudan 2023), affichée dans « Méthode ».

## v0.12 – Actualiser et traduire

- **Bouton ⟳** : recharge les dernières données ; pour un utilisateur validé, lance une collecte immédiate via la fonction Supabase `supabase/functions/trigger-collect` (jeton GitHub côté serveur, garde-fous anti-abus). Guide, partie J.
- **Traduction automatique** des titres (alertes, fil, rapports) : robot (IA, champs `title_fr` / `title_en`) quand la clé Anthropic est branchée, sinon traduction sur l'appareil (API Translator de Chrome / Edge), sinon lien Google Traduction.
- Correctif : le service worker gardait d'anciennes versions des bibliothèques (icônes manquantes) ; icône Rapports en forme de livre.

## v0.11 – Rapports, alerte précoce et sources

- **Tri du contenu renforcé** (`veille/press.py`) : une « attaque » n'est retenue que si elle est violente et pertinente (bilan lourd, lieu public ou cible institutionnelle, groupe armé, enlèvement) ; écartés : sport, métaphores (« Google attaque… »), animaux, accidents domestiques, feux d'artifice, suites judiciaires et hommages, menaces sans suite, séismes faibles déjà couverts par l'USGS.
- **Sources** : ≈ 45 nouveaux flux (presse Afrique, Amérique latine, Asie, Moyen-Orient, Ukraine, presse régionale française, ONU), avertissements de l'Auswärtiges Amt (calque « Allemagne »), bulletins officiels NOAA NHC, tsunamis PTWC/NTWC, Smithsonian GVP, Copernicus EMS, ECDC (`veille/connectors/official_rss.py`, `de_advisories.py`). Flux RSS téléchargés en parallèle. Le compteur affiche le volume réel surveillé (flux + médias du catalogue + canaux Telegram + producteurs de rapports).
- **Onglet Rapports** (`veille/reports.py`, `config/reports.json`) : dernières publications d'une trentaine de think tanks, ONG et organisations internationales, avec pays, régions et thèmes détectés ; rapports récents dans la fiche pays. Ajout manuel possible (`"manual"`).
- **Onglet Alerte précoce** (`veille/early_warning.py`, `docs/ew.js`, `config/early_warning.json`) : par unité administrative (Corne de l'Afrique, Sahel – lac Tchad), précipitations, température et humidité du sol (NASA POWER), incidents et conflits liés aux ressources, insécurité alimentaire IPC et déplacés (HDX HAPI), indice expérimental de convergence des risques.

## v0.10 – Comptes, safety check et application mobile

- **Mobile** : barre de navigation en bas, fiches en bas d'écran, couches repliables ; installable comme application (PWA : `docs/manifest.webmanifest`, `docs/sw.js`), consultable hors connexion.
- **Comptes** (`docs/compte.html`) : inscription par e-mail et mot de passe, **validation par un administrateur**, profil, préférences synchronisées entre appareils, sites et trajets, notifications, suppression du compte.
- **Administration** (`docs/admin.html`) : validation, refus, suspension et rôles ; création et suivi des **safety checks** (tous, un pays, un rayon autour d'un lieu ; option organisation), avec notifications Web Push et tableau des réponses.
- **Catégorie Diplomatie / politique** : élections, démissions, sanctions, expulsions de diplomates ; hors note de risque et hors Pulse.
- Serveur : Supabase (offre gratuite) – `supabase/schema.sql` (tables et règles d'accès RLS) et `supabase/functions/safety-push`. Mise en place : `GUIDE_MISE_EN_LIGNE.md`, partie H. Sans configuration, l'outil fonctionne sans compte.

## Versions antérieures

- **v0.9.1** : presse de 25 pays à risque (216 médias, 21 langues), cotation par média, tri des faits divers et du judiciaire.
- **v0.9** : trajets surveillés, chronologies de crise, agenda, go / no-go guidé, aide intégrée, socle IA.
- **v0.8** : Pulse, brief de mission, « Vérifié Angor » et cotation de l'Amirauté, point quotidien Telegram, liens partageables, alertes NWS / Meteoalarm / CISA.
- **v0.1 – v0.7** : carte, connecteurs de base (USGS, GDACS, NASA, OMS, GDELT, avis officiels), note de risque pays, rapport pays, fil de presse, base historique.
