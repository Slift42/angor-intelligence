# Le site (`docs/`)

HTML + CSS + JavaScript « vanilla », sans framework ni étape de compilation : le dossier `docs/` est publié
tel quel. Chaque script est une fonction auto-exécutée (IIFE) qui n'expose que le strict nécessaire sur `window`.

## Chargement d'une page

1. `index.html` charge les bibliothèques (`vendor/`), puis les données (`data/countries.js`, `data/data.js`,
   `data/config.js`), puis les scripts (`account.js`, `gonogo.js`, `ew.js`, `app.js`).
2. Les données lourdes ou rares sont chargées **à la demande** avec `loadScript()` : agenda (`calendar.js`),
   rapports, archives mensuelles, historique, fiches pays (`country/<ISO>.js`), trafic, données du Travel buddy.
3. Les URL des scripts portent une empreinte `?v=…` réécrite par le robot (`publish.bust_cache`) : après une
   mise à jour, le navigateur charge le nouveau code. **Ne jamais retirer ces `?v=`**.
4. `sw.js` (service worker) : réseau d'abord pour les pages et les données, cache d'abord pour `vendor/` et `icons/`
   (adresse complète, empreinte comprise). Changer `CACHE` dans `sw.js` invalide tout le cache.

## `app.js` : plan du fichier

Le fichier est découpé en sections repérées par `/* ---- nom */` (rechercher la ligne pour s'y rendre) :

| Section | Contenu |
|---|---|
| textes | Dictionnaire `I18N.fr` / `I18N.en` ; fonction `t(clé, ...args)` (une valeur peut être une fonction) |
| état | Objet `state` (langue, thème, période, filtres, onglet, sélection…) ; `store` = `localStorage` protégé (clés `vs-…`) |
| liens partageables | Lecture des paramètres d'URL (`?h=`, `layer=`, `tab=`, `c=`…) et `bindShare()` (bouton Partager) |
| sites, carte | Carte Leaflet, fonds (MapLibre / Esri / neutre ; « réaliste » = Esri World Physical Map + World Reference Overlay jusqu'au zoom 8, puis World Imagery + Boundaries and Places), thème sombre « Angor Night », calques pays, marqueurs (`markerIcon`), groupes (`clusterIcon`, anneau par gravité) et étoile des catégories au survol (`showBurst` / `zoomToCat`, souris seulement) |
| filtrage | `inWindow`, `hiddenByReliable`, `isOngoing`, `crisisLevel` |
| rendu | `renderAll()` : liste d'alertes, compteurs, légende, marqueurs |
| agenda, traduction automatique, actualiser, rapports, trajets surveillés | Un onglet ou une fonction par section |
| trafic aérien et maritime | Espace Trafic : liens, aperçus, calques avions (`VS_TRAFFIC`) et navires (Digitraffic) |
| fiches | `openEvent`, `openCountry`, `openHealth` : contenu du tiroir latéral (`openDrawer(html, kind, id)`) |
| analyses | Tableau de bord Chart.js (`renderAnalytics`) avec filtres, dont la sélection multiple de catégories |
| recherche, interactions | Recherche unifiée ; tous les écouteurs d'événements (`bind()`) |
| mobile, PWA, compte | Barre de navigation basse, installation, comptes et safety check |
| Pulse, cotation, vérification, partage | Mode analyste (Valider / Fausse alerte), export de `verified.json` |
| go / no-go, Travel buddy | Questionnaire guidé (`gonogo.js`), assistant conversationnel (relais IA) |
| démarrage | Ordre d'initialisation |

## Conventions

- **Sécurité du rendu** : tout le HTML est produit par des gabarits (`` `…${…}` ``). **Toute** valeur issue des
  données passe par `esc()` (ou `ttl()` / `trHtml()` pour les titres traduits). Ne jamais injecter un texte brut.
- **Traductions** : chaque texte affiché a une clé dans `I18N.fr` **et** `I18N.en`. Les libellés de catégories
  viennent de `VS_DATA.taxonomy` (source unique : `veille/model.py`).
- **Couleurs** : variables CSS de `:root` et `:root[data-theme="dark"]` (`app.css`). Les couleurs de risque
  `--risk1…5` et de gravité `--sev1…4` sont lues en JavaScript par `cssVar()`.
- **Mobile** : point de rupture principal à 860 px ; vérifier qu'aucune page ne défile horizontalement (test e2e).
- **Stockage local** : uniquement des préférences (`vs-…`), toujours via `store` (protégé par try/catch).
- **Icônes** : Lucide, dans `vendor/icons.js` (`window.VS_ICONS`). Ajouter une icône = ajouter son tracé SVG.

## Ajouter un onglet

1. `index.html` : une section `<section class="tab-body" data-body="mon_onglet" hidden></section>`.
2. `app.js` : ajouter la clé à un espace de `SPACES` (ou créer un espace + un bouton `data-space` dans la barre
   de gauche, + `SPACE_ICON`), une icône dans `TAB_ICON`, les textes `tab_mon_onglet` (FR et EN).
3. Dans `renderTabs()`, appeler la fonction de rendu quand `state.tab === 'mon_onglet'`.
4. Si l'onglet doit être ouvrable par lien : ajouter la clé à la liste des `tab` acceptés (paramètres d'URL).
5. Mobile : vérifier la barre basse (`renderMobileNav`) ou le menu « Plus ».

## Ajouter un calque sur la carte

Créer un `L.layerGroup()`, l'ajouter / le retirer selon l'onglet ou une case à cocher (exemple complet :
`trafficLayers()` dans la section trafic). Les formes vectorielles utilisent le moteur SVG commun
(`renderer: L.svg({ padding: 0.9 })`), dessiné bien au-delà de l'écran pour éviter les zones vides au déplacement.

## Autres pages

- `report.js` (rapport pays) : liste `SECTIONS` (identifiant, titre, sous-titre) et une fonction `xxxHtml(iso)` par
  section, toutes assemblées dans `render()`. Ajouter une section = une entrée dans `SECTIONS` + une fonction.
  La carte Leaflet du rapport doit recevoir sa vue (`fitBounds`) **avant** toute forme vectorielle.
  Impression : `dossier.css` (`@page`, couverture pleine page, pied de page numéroté via les boîtes de marge `@page`).
- `ew.js` (alerte précoce) : branché par `window.AngorEW.init(pont)`, ouvert / fermé par `app.js`.
- `gonogo.js` : moteur de décision partagé par la carte et le brief (`window.AngorGNG`).
- `account.js` : client Supabase minimal (Auth + REST), désactivé si `VS_CONFIG.accounts` est vide. Conditions : `legalRequired()`,
  `legalMissing()`, `acceptLegal()` ; l'inscription envoie les versions acceptées (`data.accepted`).
- `providers-lib.js` (`window.AngorProviders`) : annuaire commun à la carte, au rapport pays, à l'espace prestataire et à
  l'administration : `forCountry(iso)`, `byCategory`, libellés et couleurs des niveaux, `score()` (même grille que la base,
  POIDS vérifiés par test) et `tierOf()`. Fiche pays : `providersSection()` dans `app.js`, chargée à la demande (`ensureProviders`).
- `prestataire.js` : éditeur de la fiche (sans paramètre) et fiche publique (`?id=`) ; fichiers via `AngorAccount.upload`,
  `signedUrl`, `publicUrl`, `removeFile` (Supabase Storage).
- `legal.js` (pages légales) : remplit `data-v` (champ de `VS_LEGAL`, ou « [à compléter] »), `data-list` (tableaux),
  `data-if` / `data-ifnot`, ajoute version, bandeau « Projet », sommaire et navigation. Le texte est dans chaque page ;
  l'identité de l'éditeur et les listes sont dans `config/legal.json`.
- Ressources tierces : aucune police ni image chargée depuis un autre domaine (`docs/vendor/fonts`, `docs/vendor/flags`) ;
  seuls les fonds de carte (OpenFreeMap, Esri), Digitraffic et Supabase sont appelés, et ils sont listés dans la politique
  de confidentialité (`tiers_techniques`). Tout nouveau service tiers doit y être ajouté.

## Mode visiteur (v0.21)

Quand les comptes sont configurés (`VS_CONFIG.accounts`) et qu'aucun compte **validé** n'est connecté, `app.js` passe en mode
visiteur (`GUEST.on`, classe `body.guest`) : la carte et les marqueurs seulement. Le CSS masque panneau, recherche, période,
couches, légende, barre mobile et volet ; `applyGuest()` retire le calque pays et les sites, ajoute « Créer un compte / Se connecter »
(ou « Compte en attente de validation ») ; un clic sur un marqueur ouvre une bulle résumée (`guestPopup`) au lieu de la fiche.
La période est fixée à 7 jours, tous filtres levés, et `persist()` ne mémorise que la langue et le thème.

`localStorage['vs-member']` mémorise qu'un compte validé s'est connecté sur l'appareil (pas de passage par l'affichage visiteur à
chaque ouverture) ; `initAccount()` le corrige et recharge la page si le statut a changé ; `account.js` l'efface à la déconnexion.

**Limite** : c'est un masquage d'interface. Les fichiers de données (`docs/data/*.js`) restent publics sur GitHub Pages ; pour
réellement réserver les données aux abonnés, il faudra les servir depuis Supabase (lecture protégée par RLS) ou un dépôt privé.
Sans configuration Supabase (usage local), l'outil reste complet.
