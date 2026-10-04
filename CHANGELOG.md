# Historique des versions

Format : une entrée par version, la plus récente en haut. Chaque entrée dit **ce qui change pour l'utilisateur**
puis, si besoin, **ce qui change pour le développeur** (fichiers, données, configuration). Le numéro de version
est dans `veille/__init__.py` (`__version__`) et s'affiche dans « État des sources ».

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
