# Historique des versions

Format : une entrée par version, la plus récente en haut. Chaque entrée dit **ce qui change pour l'utilisateur**
puis, si besoin, **ce qui change pour le développeur** (fichiers, données, configuration). Le numéro de version
est dans `veille/__init__.py` (`__version__`) et s'affiche dans « État des sources ».

## v0.29 – Affinage, lot 4 : contrôle hors échantillon du tri, aide en anglais (octobre 2026)

Quatrième lot de l'affinage de tout le site (plan et avancement : `claude/finetune_angor.md` dans le projet).

- **Mesure honnête du tri** : 559 titres de presse placés sur la carte le 24 octobre, jamais vus pendant les réglages,
  ont été relus un à un. Seuls 300 étaient de vrais incidents : **précision réelle 54 %**, loin des 95 % mesurés sur
  les titres qui avaient servi aux réglages. Après correction, il reste 45 faux positifs et 1 incident perdu.
- **Ne vont plus sur la carte** (ils restent dans le Fil, étiquette « Contexte ») : annonces et interdictions de
  manifester, prévisions et alertes météo sans dégâts (« braces for Hurricane », « à quoi s'attendre »), présentations
  de suspects et procès, analyses, déploiements et exercices militaires sans attaque. **Écartés** : sport (clubs, scores),
  culture, économie, brèves locales en hindi.
- **Gardés à coup sûr** : une alerte qui décrit des dégâts (« alerte rouge … pour inondations »), une manifestation qui a
  eu lieu même si le titre en annonce une autre, « Russia launches mass missile attack ». En roumain, « peste 200 » veut
  dire « plus de 200 » et n'est plus pris pour l'épidémie de peste.
- **Aide en anglais** : nouvelle page `help.html`, ouverte par le bouton « ? » et le menu Plus quand la plateforme est en
  anglais ; lien « English / Français » en haut des deux pages. Le texte « Contexte » de l'aide liste les nouveaux cas.
- **Recommandation** : la précision ne progressera plus beaucoup par mots-clés. Le tri par IA (déjà codé) s'active en
  ajoutant le secret GitHub `ANTHROPIC_API_KEY` (budget plafonné dans `config/settings.json`).

Pour le développeur : `audit3_noise` et `audit3_context` (`veille/press.py`), 395 titres ajoutés à `tests/gold_tri.csv`
(1 472), seuil de précision de `test_press.py` ramené à 88 % (voir `doc/TESTS.md`), `tools/build_help_en.py` +
`tools/aide_en.json` (aide anglaise générée, `tests/test_help_en.py` échoue si un texte n'est pas traduit ou si
`help.html` n'est pas à jour), cache hors ligne `angor-v12`.

## v0.28 – Affinage : ce qui n'est pas un incident quitte la carte, doublons, localisation, sources (octobre 2026)

Trois premiers lots de l'affinage de tout le site (plan et avancement : `claude/finetune_angor.md` dans le projet),
publiés ensemble.

### Lot 3 : sources, respect des robots.txt

- **Conformité** : le robot respecte désormais le fichier robots.txt de chaque site qu'il lit (flux RSS, médias,
  Telegram, pages d'articles lues pour GDELT). Une adresse interdite n'est plus demandée. Les API publiques documentées
  (USGS, NWS, FMI, Banque mondiale…) ne sont pas concernées.
- **Google News** : son robots.txt interdit aux robots les recherches utilisées par les connecteurs « Google News » et
  « Médias de référence » (environ 70 % des titres de presse). Décision : les remplacer, puis les couper. En attendant,
  ils bénéficient d'une **exemption temporaire**, signalée dans « État des sources ».
- **Nouveau : flux propres des médias** : le robot cherche le flux RSS de chacun des ≈ 1 400 médias nationaux et
  régionaux du catalogue (40 par collecte), puis les lit par roulement (150 par collecte). Le bilan (flux trouvés, pays
  couverts) s'affiche dans « État des sources » ; il dira quand Google News peut être coupé. À titre égal, le lien
  direct du média est préféré au lien Google News.

### Lot 2 : second audit, doublons, localisation

- **Second audit de la carte** (931 titres de presse du 23 octobre) : **277 n'étaient pas des incidents (30 %)** ;
  il en reste 7. Ne vont plus sur la carte :
  - suites d'un fait : hommages, funérailles, témoignages, enquête, procès, arrestations (« victims remembered »,
    « suspect ID'd », « dictan presidio perpetuo ») ;
  - menaces et projets (« les États-Unis pourraient frapper l'Iran »), réactions, appels au calme ;
  - analyses (« Comment la manifestation a dégénéré », résumés quotidiens du front) ;
  - sujets militaires sans incident (achats d'armes, nouveau ministre, exercices) ;
  - prévention et préparation : travaux contre les crues, alertes sans dégâts, vaccinations, exercices de séisme ;
  - bruit : « protesters flood Belgrade » (troubles, pas une crue), « landslide victory », football, films, saisies
    de drogue, querelles familiales, interventions de police au Brésil, petits séismes japonais, faits divers locaux
    en hindi et en ourdou.
- **Catégories** : « Russian forces strike energy facility » est une frappe, pas une grève ; les heurts avec la police
  lors des manifestations (France, Belgique, Espagne, Italie) sont des troubles civils ; la grève des mineurs de Vulcan
  (Roumanie) n'est plus une éruption.
- **Doublons** :
  - même fait raconté avec d'autres mots, grâce aux mots rares communs (palais présidentiel d'Aden) ou à la même cible
    le même jour (attaque de l'église de Karak, de l'aéroport de Dammam) ;
  - une fusillade classée « crime » ici et « conflit » là ;
  - deux articles sur la crue d'une même ville ;
  - GDELT et la presse ne fusionnent plus deux faits sans rapport dans une même ville (Gaza, Delhi), mais
    reconnaissent un même fait placé dans la commune voisine (Trappes pour « near Paris »).
- **Localisation** :
  - noms de pays reconnus en 28 langues de plus (« França », « Ucrânia ») ;
  - États américains (« in Virginia » n'est plus en Afrique du Sud) ;
  - le pays auteur d'une frappe n'est plus pris pour le lieu (« Russia hits central Kyiv » → Ukraine) ;
  - une ville précédée de « in », « at » ou « on » l'emporte sur la ville d'origine d'une victime ou d'un vol
    (« Hyderabad man killed in Riyadh airport attack » → Riyad) ;
  - Paris n'est plus Parys (Afrique du Sud) ni Paris (Texas), ni Salvador (Brésil) le Salvador ;
  - noms de journaux et mots arabes courants (« la ville », « les martyrs ») ne sont plus des lieux.
  Les fusillades près de Paris et de l'église de Karak, vues trois fois chacune, n'ont plus qu'une fiche.

### Lot 1 : premier audit

- **Audit de la carte publique** (7 jours, 178 événements) : 34 faux positifs sur 95 titres de presse relus. Chacun
  a donné une règle ; l'échantillon passe à **0 erreur**. Ne vont plus sur la carte :
  - prévisions sans impact constaté (« alerte aux crues », « pourrait devenir un cyclone ») et travaux de prévention ;
  - suites d'une catastrophe ou d'émeutes, contrôles sanitaires, témoignages, convocations ;
  - annonces de cessez-le-feu, mises en garde (« warns against »), démentis, tirs d'essai de missiles ;
  - hors sujet : « enlèvement » de marchandises, égouts qui débordent, intervention de police, avis de recherche,
    brèves de faits divers locaux.

  Ces titres restent dans le Fil, marqués « Contexte ».
- **Catégories** : un piratage décrit avec des mots d'attaque est classé cyber ; des affrontements lors d'une
  manifestation ou d'un blocage (sans militaires) sont classés troubles civils, et non conflit armé.
- **Localisation** :
  - les noms de médias ne sont plus des lieux (« The New York Times » n'est plus New York) ;
  - un gentilé situe le pays (« Ukrainian city of… ») ;
  - le pays cité dans le titre l'emporte sur celui du flux (fusillade près de Paris relayée par un flux américain) ;
  - noms de pays reconnus en chinois, japonais, thaï, arabe, persan, hébreu et hindi ;
  - plus de village homonyme pris au hasard dans un titre chinois ;
  - Monterey Park n'est plus Monterrey (Mexique).
- **Flux officiels** :
  - NWS (États-Unis) : plus d'alertes gel, givre, risque d'incendie, brouillard, qualité de l'air ni de simples
    veilles, sauf cycloniques, de submersion et de tsunami ;
  - les ordres d'évacuation prennent la catégorie de l'aléa (feu, crue) ;
  - Meteoalarm : plus de vigilances en mer seule ni de brouillard orange ;
  - NHC : un cyclone = une seule fiche, mise à jour à chaque bulletin, au lieu d'une fiche par bulletin.
- **GDELT** :
  - « occupation de territoire » est écartée : c'est une situation, pas un fait daté ;
  - un fait violent placé au centre d'une capitale alors qu'un autre pays est en cause est écarté (capitale citée
    en tête de dépêche).

Pour le développeur :
- `press.py` : `audit_noise`, `audit_context`, `strip_media`, `demonym_place`, `SCRIPT_COUNTRY_ALIASES`,
  `PLACE_SUFFIX` ; corrections de catégorie dans `classify` ; seuils des villes en écriture sans espaces.
- `nws.worth_keeping`, `meteoalarm.marine_only`, option `group` d'`official_rss` (NHC Atlantique et Pacifique Est),
  `gdelt_events.DROP_CODES` et `CAPITAL_RADIUS_KM`, `geo.capitals()` (GeoNames `PPLC`). `FILTER_VERSION` de GDELT
  inchangé (pas de reconstruction de l'historique).
- `triage` : GDELT « Occupation of territory » → bruit.
- `tests/gold_tri.csv` : 641 titres (+95 de production) ; seuil de précision relevé à 94 % (mesuré : 95 %, rappel
  99 %). Nouveau `tests/test_connectors.py` (25 cas) ; `test_press.py` : audit et localisation.
- Cache du service worker : `angor-v11`.
- Lot 3 : `veille/robots.py` (RFC 9309, mémoire d'une semaine dans `store["state"]["robots"]`, exemptions
  `robots_exempt`), `http.get(..., robots=True)` et `RobotsDisallowed` ; connecteur `outlet_feeds` (découverte et lecture
  des flux, `summary` pour `outlets_health.direct`) ; état des sources : mention de l'exemption ; tests `test_robots.py`
  (6) et 3 cas dans `test_connectors.py`.
- Lot 2 :
  - `press.py` : `audit_context2` et nouvelles listes (suites, menaces, analyses, prévention, bruit) ;
  - `Gazetteer` : `country_mentions` (guillemets, acteurs), recherche par mots, `_cldr_country_names`, `US_STATES`,
    `LOC_PREP_STRONG` ;
  - `config/country_names.json` et `tools/build_country_names.py` (CLDR via Babel, à relancer seulement pour
    ajouter une langue) ;
  - `dedupe.py` : règles D (mots rares, idf) et E (`TARGETS`), `COMPATIBLE`, `_cross_source_ok`, famille
    `landslide`, `crime` dans « violence », crues d'une même ville ;
  - `tests/gold_tri.csv` : 1 077 titres (+436), précision 95 %, rappel 100 % ; tests ajoutés dans
    `test_press.py` (audit 2, localisation, noms de pays) et `test_pipeline.py` (7 cas de doublons).

## v0.27 – Tendances et alerte précoce fusionnées, monde entier, sources étoffées (octobre 2026)

- **Un seul onglet, trois niveaux de détail** : « Tendances · alerte précoce » (espace Anticipation) remplace les
  onglets Tendances et Alerte précoce. Le sélecteur « Niveau de détail » passe de **Région et pays** (tendances,
  indicateurs) à **Subdivisions** (alerte précoce par région, État ou province). L'ancien lien `?tab=ew` ouvre
  directement le niveau Subdivisions.
- **Monde entier, 17 régions** communes aux deux niveaux. Chaque pays appartient à une seule région, et les
  outre-mer sont rattachés à leur région géographique pour l'alerte précoce. Les anciennes zones Corne de l'Afrique
  et Sahel sont reprises dans « Afrique de l'Est et Corne » et « Afrique de l'Ouest et Sahel » (le Cameroun est en
  Afrique centrale).
- **Alerte précoce généralisée** : l'indice de convergence (0-100) compte désormais cinq composantes calquées sur les
  familles de facteurs des tendances :
  - climat et environnement (30 points) ;
  - terrorisme, conflits et criminalité (30) ;
  - société et politique (15, nouveau) ;
  - aléas, infrastructures et santé (10, nouveau) ;
  - crises humanitaires (15).

  Là où il n'y a pas de donnée humanitaire, l'indice est ramené sur 100. Les nouvelles séries mensuelles par
  subdivision (troubles civils et politiques ; aléas, pannes, cyber et épidémies) ont leurs graphiques dans la fiche.
- **Liens croisés** : chaque tendance liste les subdivisions les plus exposées selon la composante qui lui correspond,
  et un clic y descend. Chaque subdivision liste, elle, les tendances de son pays et de sa région.
- **Indicateurs structurels par pays** (nouveau), mis à jour automatiquement et sans clé :
  - FMI : croissance, inflation, dette publique, chômage ;
  - Banque mondiale : stabilité politique, efficacité des pouvoirs publics, État de droit, corruption ;
  - BCE : taux souverain à 10 ans et écart avec l'Allemagne.

  Des signaux apparaissent au-delà d'un seuil (récession, inflation forte, dette lourde, chômage élevé, forte
  instabilité, tension sur les taux). Pour une région, la liste des pays concernés est affichée.
- **Sources étoffées** :
  - bibliographie portée de 72 à 162 sources cotées ;
  - 14 familles de facteurs, dont la nouvelle famille « Crises humanitaires », et 34 facteurs (7 nouveaux :
    séismes, volcans et cyclones ; conflits armés ; sûreté maritime ; coupures d'Internet ; gouvernance ;
    insécurité alimentaire ; déplacements).

  Chaque facteur a au moins deux sources de suivi. Les indicateurs alimentés automatiquement sont marqués
  « intégré », et les licences sont signalées (ACLED, GTD : non intégrés sans licence ; services payants cités
  seulement).
- **Page de méthode** : nouvelles sections « Alerte précoce par subdivision » et « Indicateurs structurels »,
  couverture des 17 régions, badges « intégré ».

Pour le développeur :
- `config/foresight/regions/` : 17 régions (16 nouvelles, tendances vides). `foresight.regions()` les fournit à
  l'alerte précoce. `validate` contrôle qu'un pays n'appartient qu'à une région.
- `veille/early_warning.py` réécrit :
  - limites par pays dans `data/ew_units/<ISO2>.json`, avec un plafond de nouveaux pays par collecte et une
    priorité configurable ;
  - climat compact (`y0` + tableaux) ;
  - comptages mensuels par famille `[sec, res, unrest, pol, haz, infra, health]` sur tous les incidents vérifiés
    en mémoire ;
  - HDX HAPI plafonné par collecte ;
  - mémoire v3, migrée automatiquement depuis la v2 ;
  - sorties `early_warning.js` (index) et `early_warning/<région>.js` ;
  - `update(..., fetch)` renvoie un résumé par subdivision.
- `config/early_warning.json` : plus de `regions`, nouveaux paramètres `priority`, `boundaries_per_run`,
  `hapi_per_run`, `hapi_empty_refresh_days` ; `power_per_run` passe à 40.
- `veille/indicators.py` (nouveau) : mémoire `data/indicators.json`, API `update`, `assemble`.
- `foresight.build(..., ew, ind)` : `trend.units`, `scope.ew`, `scope.ind`.
- `method.json` 1.1 : famille `humanitarian`, champ `auto` sur les indicateurs, `roadmap` sans statut (couverture
  calculée).
- Front : `ew.js` réécrit et piloté par `foresight.js` (`mount`, `unmount`, `openUnit`) ; `AngorFS.openTrend`.
  Onglet `ew` retiré de `SPACES`. Cache du service worker : `angor-v10`.
- `collecte.py` : alerte précoce sur tous les incidents en mémoire (`all_events`), puis indicateurs, puis tendances.
- Tests : `test_early_warning.py` (8), `test_indicators.py` (5), `test_foresight.py` mis à jour ; test de fumée :
  niveau Subdivisions.

## v0.26 – Tendances de risques : méthode d'anticipation, Europe de l'Ouest et France (octobre 2026)

- **Nouvel onglet « Tendances »** (espace Anticipation, en premier) : les tendances de risques qui peuvent toucher
  l'entreprise et le voyageur, **région par région et pays par pays**. Premier périmètre : **Europe de l'Ouest**
  (12 tendances régionales) et **France** (11 tendances nationales). Les autres pays de la région héritent des
  tendances régionales (pointillés sur la carte) ; les 16 autres régions du monde sont planifiées.
- **13 familles de facteurs** : climat, géopolitique, politique, société, terrorisme et criminalité, cyber,
  économie, finances publiques, énergie, infrastructures, santé, démographie, technologies. 27 facteurs, chacun
  avec ses indicateurs et ses sources de suivi.
- **Chaque tendance** : vraisemblance (1 à 5, fourchettes de probabilité ICD 203 / PHIA), impact entreprise et
  impact voyageur (1 à 5), horizon (0–3 mois, 3–12 mois, 1–3 ans), dynamique, confiance ; signaux **datés et
  sourcés** ; indicateurs d'alerte ; scénario de rupture ; implications et recommandations ; secteurs exposés ;
  tendances liées (risques en cascade) ; évolution mensuelle du score.
- **Score** = vraisemblance × impact (1 à 25, cinq niveaux) ; **matrice** interactive ; **pression de risque**
  (0–100) par périmètre ; vue Global / Entreprise / Voyageur ; filtres par horizon et par famille.
- **Contrôle qualité automatique** : au moins 2 sources et 2 éditeurs indépendants par tendance, au plus 50 % de
  sources de cotation D–F, dates jamais dans le futur, échelles respectées, textes bilingues ; fiche signalée
  **« révision due »** après 30, 60 ou 120 jours selon l'horizon.
- **Signal en temps réel** : les incidents vérifiés d'Angor du périmètre (30 derniers jours contre les 90
  précédents) ; une hausse nette sur une tendance non jugée en hausse est signalée comme **surprise** à réexaminer.
- **Page publique « Méthode des tendances de risques »** (`methodologie.html`) : principes, cycle d'anticipation,
  facteurs et indicateurs, échelles, score, contrôle qualité et biais, repères tirés de l'AXA Future Risks Report
  2026, du WEF Global Risks Report 2026 et de l'Allianz Risk Barometer 2026, couverture, limites et bibliographie
  complète (72 sources cotées).

Pour le développeur :
- `veille/foresight.py` (chargement, `validate`, `score`, `live_signal`, `build`, `snapshot`, `public_method`,
  `update`), appelé par `collecte.py` après l'alerte précoce.
- Configuration : `config/foresight/method.json`, `sources.json`, `regions/weu.json`, `countries/FR.json`.
  Ajouter un pays = créer `countries/<ISO2>.json` (voir `doc/FORESIGHT.md`).
- Sorties : `docs/data/foresight.js` (`window.VS_FS`, réservé aux comptes validés) et `docs/data/foresight_method.js`
  (`window.VS_FS_METHOD`, public, ajouté à `vault.PUBLIC`). Historique mensuel des scores dans
  `store["state"]["foresight"]["history"]` (36 mois).
- Front : `docs/foresight.js` (`window.AngorFS`), onglet `trends`, styles `.fs-*` ; pont carte commun avec l'alerte
  précoce (`mapBridge`). Cache du service worker : `angor-v9`.
- `tools/check_foresight_sources.py` : vérifie les liens de la bibliographie (à lancer sur le PC).
- Tests : `tests/test_foresight.py` (13 tests).

## v0.25 – Sources étoffées, 56 langues, recoupement des sources et des contenus (octobre 2026)

- **Médias de référence : 797 → 1 528** dans 206 pays. Presse nationale et **régionale** en langue locale (ex.
  Mexique : Sinaloa, Guerrero, Michoacán, Tamaulipas… ; Nigeria : nord-est et nord-ouest ; Inde : Cachemire,
  Manipur ; Philippines : Mindanao ; Indonésie : Papouasie, Aceh ; Thaïlande : provinces du Sud ; Birmanie : Rakhine,
  Kachin ; France : grande presse régionale), agences, chaînes d'info, médias en exil (Russie, Biélorussie, Iran,
  Érythrée, Nicaragua…). Médias d’État cotés « D ». 63 langues de recherche corrigées (médias nordiques, baltes,
  d'Europe centrale, du Japon ou de Corée interrogés en anglais alors qu'ils publient dans leur langue).
- **56 langues** de mots-clés (21 → 56) pour chercher et trier les titres : japonais, coréen, vietnamien, hindi,
  népalais, tamoul, pachto, langues nordiques et baltes, tchèque, slovaque, hongrois, roumain, bulgare, macédonien,
  serbo-croate, slovène, albanais, grec, géorgien, arménien, azéri, ouzbek, mongol, malais, filipino, birman, khmer,
  swahili, haoussa. Google News : éditions locales pour 16 pays de plus (Japon, Corée, Viêt Nam, Thaïlande, Grèce,
  Roumanie, Hongrie, Tchéquie, Slovaquie, Bulgarie, Suède, Norvège, Lituanie, Lettonie, Slovénie, Inde en hindi).
  Apostrophes typographiques reconnues (« coup d’État »). Bilans lus dans ces langues (« två döda », « 3 morți »,
  « три человека погибли »).
- **Nouvelles sources officielles** : **EMSC** (deuxième réseau sismologique mondial, recoupe l'USGS) et **CDC**
  (avis sanitaires aux voyageurs par pays, niveaux 1 à 4).
- **Recoupement des sources** : une fiche compte désormais ses **sources indépendantes** – un même groupe de presse
  (EBRA, Schibsted, Gannett, ARD, RFE/RL…) ou un titre repris mot pour mot ne comptent qu'une fois. La cote de
  l'Amirauté s'appuie dessus (2 = au moins 3 sources indépendantes, ou une source officielle et une presse).
  Ligne « Recoupement » dans la fiche : nombre de sources indépendantes, types (capteur, officiel, presse…), reprises.
- **Recoupement des contenus** :
  - un séisme, un cyclone ou une éruption rapportés par la presse ou GDELT sont **rattachés à la mesure
    officielle** (USGS, EMSC, GDACS, NOAA, GVP) : une seule fiche, les articles en sources ;
  - un séisme chiffré qu'aucun réseau n'a mesuré est marqué **« Non confirmé par les capteurs officiels »**
    (crédibilité 4) ;
  - un **démenti** publié qui raconte la même histoire (« fake », « hoax », « démenti », « desmiente »…) marque
    l'événement **« Démenti signalé »** avec le lien (crédibilité 4) ;
  - USGS et EMSC en désaccord sur la magnitude (écart ≥ 0,5) : écart signalé.
- **Médias muets** : le robot compte, pour chaque média, les requêtes et les titres obtenus ; un média sans aucun titre
  après 30 requêtes (domaine erroné, site fermé) est listé dans « État des sources » → « Médias de référence ».
- **Annuaire des prestataires : 316 → 383 locaux, 107 → 153 pays**, 51 régionaux (États-Unis, Australie, Russie,
  Pologne, Irlande, pays nordiques et baltes, Europe centrale, Caraïbes, Mongolie, Laos, Botswana, Namibie,
  Palestine, Syrie, Maldives, Timor oriental…). Toujours « non vérifié – à contacter séparément » (niveau E).
- **Robot** : machine du robot de tests et du robot historique aussi figées sur Ubuntu 24.04 (modèles
  `tools/github-actions-*.yml`).
- Développeur : `veille/langs.py` ; `veille/corroborate.py` (`independence`, `sensor_check`, `denials`, `run`,
  `MEDIA_GROUPS`) ; `veille/connectors/emsc.py` ; `outlets.record`, `outlets.muted`, `collecte.outlets_health` ;
  `quality.credibility` (sources indépendantes, démentis, capteurs) ; `tools/outlets_src.py` (`AJOUTS_V25`,
  `LANGUE_V25`) ; `config/sources.json` (emsc, cdc_thn ; rotation outlets 90 requêtes, gnews 45) ; champs
  `corroboration`, `press_reports`, `unconfirmed`, `disputed`, `mag_spread`, `outlets_health` ; tests
  `tests/test_corroborate.py`, cas multilingues (`tests/test_press.py`), EMSC, médias muets et catalogue
  (`tests/test_sources.py`) ; doc `doc/DONNEES.md`, `doc/CONNECTEURS.md`, `doc/ARCHITECTURE.md`, `doc/TESTS.md`,
  README, aide ; cache hors ligne `angor-v8`.

## v0.24 – Contrôle d'entrée des événements : vérification a priori et permanente (octobre 2026)

- **Chaque nouveauté est vérifiée avant d'entrer sur la carte**, plus seulement au moment de l'affichage : fait
  physique (presse, GDELT), fiche plausible (position, date, titre), article réellement lu pour GDELT. Rien n'atteint
  la carte, les alertes e-mail et Telegram, les notes de risque ni Pulse sans ce feu vert.
- **GDELT** : une détection reste **en attente, hors carte**, tant que le titre de son article n'a pas été lu ; si
  l'article est illisible, elle n'apparaît pas (« invérifiable »). Les détections les plus récentes sont lues en
  premier.
- **Fiches invalides** (position impossible ou (0, 0), titre vide, date illisible, attentat daté dans le futur) :
  refusées à l'entrée, jamais gardées en mémoire. Une alerte météo ou une crue peut, elle, commencer dans les 10 jours.
- **Contrôle permanent** : toute la mémoire (95 jours) repasse le contrôle à chaque collecte. Une règle améliorée
  s'applique aussitôt aux fiches déjà connues. Seules les fiches modifiées sont relues (moins d'une seconde par
  collecte ; la première collecte après une modification des règles relit tout, environ 2 ms par fiche).
- **Avec l'IA** (si une clé est configurée) : l'IA dit aussi si le titre décrit un fait physique ; sinon il va au Fil.
- **« État des sources » → « Contrôle des événements »** : nouveautés de la dernière collecte et de la journée, état
  de la mémoire (retenus, contexte, écartés, en attente), alarmes, et les 40 derniers titres refusés avec leur motif.
  En mode analyste, **« Rétablir »** corrige un faux refus (décision exportée dans `verified.json`, appliquée à la
  collecte suivante). La décision de l'analyste passe toujours avant les règles.
- **Alarme** dans le journal du robot (`✘ Contrôle d'entrée`) quand une source voit plus de 85 % de ses nouveautés
  refusées (au moins 20) : flux devenu hors sujet, ou règle trop stricte.
- Développeur : `veille/triage.py` (`verdict`, `sanity`, `check`, `on_map`, `alarms`, `journal`, `payload`) ; champs
  `triage`, `physical`, `headline_failed` ; `enrich.add_headlines` renvoie le nombre d'articles lus (budget partagé
  entre nouveautés et attente) ; prompt IA (`physical`) ; `collecte.triage_reason` remplacé par le contrôle ; tests
  `tests/test_triage.py` ; doc `doc/DONNEES.md` (contrôle d'entrée), `doc/ARCHITECTURE.md`, `doc/TESTS.md` ; cache
  hors ligne `angor-v7`.

## v0.23 – Moins de doublons, seulement de vrais événements sur la carte (octobre 2026)

- **Un événement = un fait physique** qui peut toucher un voyageur ou un site. Les titres de sûreté qui n'en sont pas
  (arrestation et suites d'enquête, attentat déjoué ou fausse alerte, déclaration, condamnation, visite, démission,
  analyse ou statistique, rétrospective ou démenti, travaux de prévention et aides après une catastrophe, annonce
  militaire, signal diplomatique) restent dans le **Fil** avec l'étiquette « Contexte », mais **ne sont plus sur la
  carte**, y compris ceux déjà en mémoire. Sans clé d'IA, par mots-clés dans toutes les langues suivies.
- **Mesure** sur 546 titres réels classés à la main (dont 426 tirés des données en ligne) : précision du tri **94 %**
  (51 % en v0.22 sur le même jeu), rappel 100 %. Corrigé au passage : « transporté à l'hôpital » pris pour une
  arrestation, « Rapid Support Forces » pris pour un « soutien », violence électorale classée en signal diplomatique,
  bilans « un mort et deux blessés » et « kills 4 » non comptés, séisme « temblor » non reconnu, frappes aériennes
  écartées faute de mot de violence.
- **GDELT** : le vrai titre de l'article est relu ; les articles manifestement hors sujet (people, procès, tribunes) ne
  sont plus placés sur la carte.
- **Doublons** : regroupement « par histoire » avant la fusion habituelle. Même dépêche reprise plusieurs jours, même
  article placé dans deux villes, bilan mis à jour, titre Google News suivi d'un texte parasite, même crash classé dans
  deux catégories : une seule fiche, avec toutes les sources, la gravité la plus haute et le lieu le plus précis
  (sur les 1 500 événements en ligne du 5 octobre : 79 fiches rattachées, contre 50 avec la seule fusion par lieu).
- **Robot** : machine figée sur Ubuntu 24.04 (`ubuntu-latest` passe à Ubuntu 26 le 19 octobre 2026) dans les fichiers
  modèles `tools/github-actions-*.yml` ; recopier `tools/github-actions-collecte.yml` dans `.github/workflows/collecte.yml`.
- Développeur : `press.context`, `press.is_event`, `press.gdelt_noise` ; `dedupe.story_merge` et `dedupe._combine` ;
  `collecte.triage_reason` (tri **avant** le regroupement) ; champ `context` des articles du Fil ; `tools/eval_tri.py`
  mesure `is_event` ; seuils de `tests/test_press.py` relevés (précision ≥ 92 %, rappel ≥ 98 %) ; tests de contexte, de
  GDELT et de regroupement (`tests/test_press.py`, `tests/test_pipeline.py`) ; doc `doc/DONNEES.md` (tri et
  regroupement), `doc/TESTS.md`, `doc/ARCHITECTURE.md`, aide (Fil de presse) ; cache hors ligne `angor-v6`.

## v0.22 – Données réservées aux comptes validés, onglet Prestataires (octobre 2026)

- **Vraie protection des données** : en ligne, la carte complète (incidents détaillés, sources, fil, chronologies, notes de
  risque, Pulse, alerte précoce, rapports, fiches pays, calendrier…) n'est plus publiée sur le site. Le robot la dépose dans
  un compartiment **privé** de Supabase ; la base ne la donne qu'aux comptes validés (contrôle côté serveur, pas seulement
  à l'écran). `angor.fr/data/data.js` n'existe plus en ligne.
- **Visiteurs** : carte allégée (7 jours ; titre, catégorie, gravité, lieu, date). **Rapport pays et brief** : verrouillés
  sans compte validé (invitation à se connecter ou à créer un compte).
- **Hors ligne** : la dernière situation consultée par un compte validé reste disponible sur l'appareil, effacée à la
  déconnexion.
- **Onglet Prestataires** (barre de gauche ; menu « Plus » sur mobile) : tout l'annuaire avec recherche, pays, catégorie,
  portée **locaux / régionaux / mondiaux** (avec le nombre de chaque) et « vérifiés seulement » ; drapeaux cliquables (fiche
  pays) ; lien « Voir tous les prestataires du pays » depuis chaque fiche pays.
- Développeur : `veille/vault.py` (coffre, `guest.js`), `docs/vault.js` (chargeur, `AngorVault.ready / script / text`),
  `AngorAccount.storageText`, `AngorProviders.scopeOf / catalogue` ; compartiment `angor-data` et politique `angor_data_read`
  dans `supabase/schema.sql` ; Secret GitHub `SUPABASE_SERVICE_KEY` et ligne correspondante dans
  `tools/github-actions-collecte.yml` (à recopier dans `.github/workflows/collecte.yml`) – guide H10 ; tests
  `tests/test_vault.py` et e2e (coffre, onglet Prestataires).
- Restent publics : code et configuration (dépôt public), base historique, guides pays, Factbook, annuaire public.
- **Annuaire étoffé** : 316 prestataires locaux dans 107 pays et 47 régionaux (en plus des 23 internationaux), repérés et
  vérifiés sur leur site officiel (lien de vérification et date conservés dans `config/providers_directory.json`) :
  cliniques et hôpitaux privés, médecins et assistance sur place, ambulances aériennes, sécurité privée, chauffeurs,
  véhicules blindés, hélicoptères. Toujours « non vérifié – à contacter séparément » (niveau E) tant que le prestataire ne
  s'inscrit pas.
- **Nouvelles catégories** : « Cliniques et hôpitaux privés » et « Medical Care & Assistance » (médecin 24/7, visites,
  téléconsultation) ; le groupe santé devient « Soins médicaux et assistance ». Les régionaux déclarent leurs pays couverts
  (`countries`) : ils n'apparaissent plus que sur les fiches de ces pays. Onglet Prestataires : liste par pages de 60.

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
