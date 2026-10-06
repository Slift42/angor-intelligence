# Angor Intelligence

Angor Intelligence est une plateforme de veille sûreté et d'intelligence économique mondiale. Elle repose uniquement sur des sources ouvertes et gratuites, et elle est prête à accueillir des sources payantes.

Ce qu'elle fait :

- **Carte des alertes** : incidents classés par catégorie et par gravité (1 Faible → 4 Critique). Chaque alerte a une description et affiche clairement ses sources.
- **Risque pays** : note sur 5 niveaux (Minimal → Extrême), comme Crisis24, Riskline ou Amarante.
- **Rapport pays imprimable en PDF**, en cinq parties :
  1. informations générales, façon World Factbook ;
  2. matrice des risques sûreté, avec les incidents à 24 h, 72 h, 7 jours et 90 jours ;
  3. recommandations sûreté pour les personnels et les sites ;
  4. angles business ;
  5. spécificités du pays : gouvernance, corruption, sanctions, société, cadre des affaires.
- **Tableau de bord analytique** : courbes, camemberts, classements.
- **Fil de presse** : environ 120 pays (Google News, éditions locales quand elles existent), plus près de 1 500 médias de référence dans 206 pays, dont la presse nationale et régionale de 25 pays à risque (mots-clés en 56 langues). Titres et liens uniquement.
- **Base historique (5 ans)** : conflits UCDP, détections GDELT, séismes, catastrophes, épidémies, pour l'onglet Analyses et la carte sur les longues périodes.
- **Calques des ministères** : heatmap MEAE (France), FCDO (Royaume-Uni), State Dept (États-Unis), avec la carte officielle de chaque pays.
- **Fonds de carte** : détaillé (routes, villes), contrasté, épuré, satellite, topographique ; noms en alphabet latin, affichage progressif (pays → régions → villes).
- **Rapports pays enrichis** : conseils et carte du MEAE, usages culturels (tenue, religion, gestes, affaires, interdits), urgences, hôpitaux (Wikidata), télécoms, prestataires de sécurité et d'assistance.
- **Couverture des sources** : les pays où nos sources remontent beaucoup moins d'incidents que la moyenne historique sont signalés « couverture faible ».
- **Mes sites** : rayons de vigilance autour de vos sites, alertes de proximité, export PDF de la liste d'alertes.
- **Pulse** : indice de stabilité par pays (0 à 100), tendance 7 et 30 jours, causes de variation, calque dédié et alerte Telegram en cas de chute rapide.
- **Brief de mission** (`brief.html`) : pays, ville, dates, profil du voyageur → recommandation indicative, avis officiels, incidents autour de la ville, mesures à cocher, santé, sources consultées et visas de validation. Imprimable en PDF, trace « duty of care ».
- **Vérifié Angor et cotation de l'Amirauté** : chaque incident porte une cote de A1 à F6 ; l'analyste valide, corrige ou infirme en mode analyste (`?analyste=1`), puis exporte `config/verified.json`.
- **Point quotidien Telegram** : chaque matin, incidents marquants, crises en cours, pays dont le Pulse baisse, vulnérabilités cyber exploitées et focus sur vos pays suivis.
- **Liens partageables, vues enregistrées, pays suivis** : l'adresse de la carte reprend la vue et les filtres ; étoile sur les pays à suivre.
- **Alertes officielles météo et cyber** : NWS (États-Unis), Meteoalarm (38 pays européens, vigilances orange et rouges), CISA KEV (vulnérabilités activement exploitées).
- **Chronologies de crise** : les incidents d'une même crise sont regroupés sur plusieurs jours (tendance escalade / stable / décrue, graphique par jour, affichage sur la carte).
- **Agenda** : jours fériés (Nager.Date), élections et référendums nationaux (Wikidata), grandes fêtes religieuses, vos échéances (`config/calendar.json`) ; repris dans les fiches pays, le brief et le point quotidien.
- **Trajets surveillés** : bande de vigilance autour d'un itinéraire (villes ou tracé sur la carte), alertes comme pour les sites.
- **Go / no-go guidé** (Travel buddy) : questionnaire → matrice menace × vulnérabilité → décision et conditions, reportées dans le brief.
- **Aide intégrée** (`aide.html`, bouton « ? ») : guide d'utilisation complet.
- **IA prête à brancher** : un socle commun (`veille/llm.py`) et un relais Cloudflare multi-tâches ; tout fonctionne sans clé.
- **Interface** : bilingue FR/EN, thème clair ou sombre, utilisable sur mobile.

---

## Utilisation (Windows)

Une seule fois :

```
python -m pip install -r requirements.txt
```

Puis, dans le terminal de VS Code :

```
python collecte.py
start docs\index.html
```

Vous pouvez aussi double-cliquer sur `collecter_et_ouvrir.bat` depuis l'Explorateur Windows. Depuis VS Code, un double-clic ouvre le fichier au lieu de le lancer.

Temps de collecte :

- **Première collecte** : 3 à 5 minutes. Elle télécharge le dictionnaire de villes GeoNames (3 Mo), les profils pays et 12 heures d'historique GDELT.
- **Collectes suivantes** : 1 à 2 minutes.

| Commande | Effet |
|---|---|
| `python collecte.py --list` | Sources et état (ON/off) |
| `python collecte.py --only usgs gdacs` | Collecter certaines sources seulement |
| `python collecte.py --profiles` | Forcer la mise à jour des profils pays (sinon, automatique une fois par semaine) |

Une source qui échoue 3 fois de suite est mise en pause 24 h. Son état est visible dans la carte (bouton « sources » en haut à droite).

**Rapport pays** : cliquez sur un pays, puis sur « Rapport pays (PDF) ». Dans le rapport, le bouton « Imprimer / PDF » propose « Enregistrer au format PDF ».

---

## Sources

| Famille | Sources (gratuites) |
|---|---|
| Catastrophes | USGS et EMSC (séismes, deux réseaux recoupés ; alerte PAGER), GDACS (ONU/UE), NASA EONET, NOAA NHC, Smithsonian GVP, PTWC/NTWC (tsunamis), Copernicus EMS |
| Santé | OMS – Disease Outbreak News, ECDC, CDC (avis sanitaires aux voyageurs, niveaux 1 à 4) |
| Météo officielle | NWS (États-Unis, alertes « Severe » et « Extreme »), Meteoalarm / EUMETNET (vigilances orange et rouges de 38 pays européens) |
| Cyber | CISA KEV (vulnérabilités activement exploitées), CERT-FR |
| Agenda | Nager.Date (jours fériés, ~120 pays), Wikidata (élections nationales), calendrier hégirien calculé, `config/calendar.json` |
| Conflits, attaques, manifestations | GDELT (presse mondiale, 65 langues, filtrée et recoupée) |
| Presse locale | Google News (≈ 120 pays, sûreté + économie, en rotation) et flux RSS : BBC, Guardian, NYT, DW, Euronews, Al Jazeera, France 24, Le Monde, RFI Afrique, Jeune Afrique, Al-Monitor, El País, MercoPress, Kyiv Independent, Times of Israel, Dawn, The Hindu, Premium Times, News24, Japan Times, Franceinfo, Le Parisien, 20 Minutes, Ouest-France |
| Institutions | ONU (Paix et sécurité), OTAN, Crisis Group, Département d'État US, FCDO britannique, CERT-FR |
| Avis aux voyageurs | MEAE (France, conseils aux voyageurs), FCDO (Royaume-Uni), Département d'État US, Gouvernement du Canada |
| Médias de référence | ≈ 1 500 quotidiens, chaînes et sites d'information dans 206 pays, presse nationale et régionale en langue locale, médias en exil (cotés A-F ; « médias muets » signalés) (`config/press_outlets.json`, modifiable dans `tools/outlets_src.py`) |
| Historique (5 ans) | UCDP GED et « candidate events » (Uppsala, CC BY 4.0), GDELT 1.0 quotidien, USGS, GDACS, NASA EONET, OMS – script `historique.py` |
| Économie et gouvernance | Banque mondiale (indicateurs, gouvernance WGI, projets actifs), FMI (prévisions), REST Countries, presse économique (BBC, Guardian, The Economist, Les Echos) |
| Contexte pays | CIA World Factbook (archive : publication arrêtée en février 2026, domaine public) |

**Comment un titre de presse devient une alerte** (`veille/press.py`) :

1. Le titre est classé par mots-clés en 56 langues (dont thaï, chinois, japonais, coréen, vietnamien, hindi, persan, ourdou, bengali, amharique, somali, swahili, haoussa, hébreu, indonésien, langues nordiques, d'Europe centrale, des Balkans et du Caucase) : catégorie et gravité.
2. Le lieu est reconnu : pays cité, puis ville de ce pays, grâce au dictionnaire GeoNames.
3. Le titre n'est placé sur la carte que si une ville est reconnue.
4. Plusieurs médias qui rapportent le même fait, au même endroit et le même jour, forment un seul incident ; les titres qui racontent la même histoire (même dépêche sur plusieurs jours, bilan mis à jour, deux villes) sont regroupés (v0.23).
5. Contrôle d'entrée (v0.24) : seul un fait physique (pas une arrestation, une déclaration, une analyse) va sur la carte ; les autres titres restent dans le Fil.
6. Recoupement (v0.25) : on compte les sources réellement indépendantes (une reprise d'agence ou un même groupe de presse = une source) ; un séisme ou un cyclone rapporté par la presse est rattaché à la mesure officielle ; un démenti publié est signalé sur la fiche.

Tout est marqué « auto » et peut être masqué. Avec une clé IA, chaque incident reçoit un résumé de 2 à 3 phrases en français et en anglais ; sans clé, la fiche affiche le chapeau publié par le média (flux RSS) ou un résumé automatique (nature, lieu, date, médias).

Les formulations de type « Paris met en garde Moscou » ne sont pas placées sur une capitale : le nom de la ville y désigne un gouvernement, pas un lieu.

---

## IA et alertes (optionnel)

**IA (Claude Haiku).** Ajoutez `ANTHROPIC_API_KEY=...` dans `.env`. Chaque nouveau titre de presse est alors lu par l'IA, qui fait trois choses :
- elle écarte les faux positifs (exercices, sport, culture, histoire) ;
- elle fixe la catégorie, la gravité, le pays et la ville ;
- elle rédige un résumé en anglais.

Sans clé, le classement par mots-clés continue de fonctionner. Garde-fous :
- les titres déjà lus sont gardés en mémoire (cache) et ne sont jamais relus ;
- 400 titres maximum par collecte ;
- budget mensuel de 20 $ par défaut (`config/settings.json` → `ai`). Activez aussi un plafond sur la console Anthropic.

**Alertes Telegram et e-mail.** Renseignez `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`, et/ou les paramètres `SMTP_...` dans `.env`. Chaque nouvel incident, partout dans le monde, est alors envoyé une seule fois s'il est assez grave (3 = Élevée par défaut), fiable (confiance non faible) et survenu depuis moins de 6 h. Si l'incident est dans le rayon d'un de vos sites, le message le précise. Réglages dans `config/settings.json` → `alerts` : `min_severity`, `max_age_hours`, `countries` (ex. `["FR","ML"]`, vide = monde), `categories` (ex. `["terrorism","unrest"]`, vide = toutes), `include_auto`. En ligne, vos vrais sites passent par le Secret GitHub `SITES_JSON` et ne sont jamais publiés.

**Onglet « En cours ».** Il retient les alertes de moins de 72 h qui remplissent au moins une condition :
- critique ;
- élevée et fiable ;
- catastrophe active ;
- recoupée par plusieurs sources ;
- évolutive ;
- proche d'un de vos sites.

Elles sont regroupées par pays et classées en crise majeure, crise ou alerte.

## Documentation développeur et historique

- **Documentation technique** (architecture, contrats de données, connecteurs, site, exploitation, tests, dette technique) : [`doc/`](doc/README.md).
- **Règles de contribution** (à lire avant toute modification) : [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **Historique des versions** : [`CHANGELOG.md`](CHANGELOG.md).

## Organisation du projet

```
collecte.py            ← le robot : collecte, calculs, publication (toutes les 30 min en ligne)
historique.py          ← base historique 5 ans (robot GitHub « Historique », manuel)
config/                ← réglages : sources, sites d'exemple, note de risque, alertes, notes villes, santé…
veille/                ← moteur Python (un module par responsabilité, voir doc/ARCHITECTURE.md)
veille/connectors/     ← un fichier par source de données
docs/                  ← le site publié : carte (index.html + app.js), rapport pays, brief, aide, comptes
docs/data/             ← données publiées par le robot (générées, non versionnées sauf référentiels figés)
doc/                   ← documentation technique pour les développeurs
tests/                 ← tests unitaires (pytest), jeu étiqueté du tri, test de fumée du site (tests/e2e)
tools/                 ← outils ponctuels, relais IA Cloudflare, modèles de workflows GitHub
supabase/              ← schéma de la base et fonctions serveur (comptes, safety check, actualisation)
.github/workflows/     ← robots GitHub Actions : collecte, historique, tests
GUIDE_MISE_EN_LIGNE.md ← mise en service pas à pas
```

---

## Brancher une source payante

Les identifiants vont dans `.env` (copie de `.env.example`) sur votre PC, et dans les **Secrets** GitHub pour le robot. Il y a trois modèles dans `config/sources.json` :

- `presse_abonne_exemple` : flux RSS réservé aux abonnés, avec cookie ;
- `fournisseur_exemple` : API d'alertes, branchée sans code ;
- `acled` : OAuth avec licence.

Voir `veille/http.py` pour les types d'authentification. Vérifiez toujours que le contrat autorise la redistribution à vos clients.

---

## Note de risque pays

```
score = 0,6 × avis officiels + 0,3 × activité sécuritaire (7 j) + 0,1 × catastrophes et santé (7 j)
```

Les règles de calcul :

- une détection automatique compte moitié ;
- une source de confiance faible compte à 30 % ;
- un pays déconseillé à 4/4 par un gouvernement est au minimum « Élevé » ;
- vous pouvez corriger un pays dans `config/risk.json`, par exemple `"overrides": {"ML": 5}`.

Dans le rapport pays, chaque risque (terrorisme, conflit, criminalité…) a son propre niveau. Il combine les incidents détectés et des indicateurs structurels : avis officiels, stabilité politique selon la Banque mondiale, taux d'homicides, groupes terroristes recensés.

---

## Limites connues

- Détection de presse par mots-clés : du bruit subsiste. D'où le marquage « auto », les indices de confiance et le recoupement.
- Textes de contexte (Factbook) en anglais. La traduction viendra avec l'étape IA.
- Participation étrangère au capital (exemple : obligation d'associé local à 51 %) : aucune source ouverte fiable et à jour. Le rapport l'indique comme « à vérifier » et cite les sources de référence.
- Fonds de carte : OpenFreeMap (gratuit, sans clé) ; en cas d'échec, OpenStreetMap ou le fond neutre hors ligne.

Crédits : Leaflet (BSD-2), Leaflet.markercluster (MIT), MapLibre GL (BSD-3), Chart.js (MIT), icônes Lucide (ISC), Natural Earth (domaine public), GeoNames (CC BY 4.0), OpenFreeMap et © contributeurs OpenStreetMap.
