# Contrats de données

Le robot et le site ne communiquent **que** par les fichiers de `docs/data/`. Toute modification d'un champ
listé ici est une modification d'interface : mettre à jour ce document, le producteur, **tous** les
consommateurs (recherche : `grep -rn "NOM_DU_CHAMP" docs/*.js`) et les tests.

Les fichiers publiés sont des scripts (`window.VS_XXX = {…};`) plutôt que du JSON : ils se chargent avec une
simple balise `<script>`, y compris en ouvrant `docs/index.html` depuis le disque, sans serveur.

## 1. Événement (format standard)

Produit par `veille/model.py → make_event`, complété au fil de la chaîne. C'est le seul format que la carte connaît.

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `id` | str | oui | Identifiant stable, préfixé par la source (`usgs:…`, `press:…`) : sert au dédoublonnage et à la purge |
| `source` | str | oui | Nom affiché de la source principale |
| `sources` | list[{name, url}] | oui | Toutes les sources ayant rapporté l'événement (après fusion), 25 au plus |
| `category` | str | oui | Clé de `model.CATEGORIES` (`attack`, `unrest`, `earthquake`…) ; inconnue → `other` |
| `severity` | int 1–4 | oui | Faible, modérée, élevée, critique |
| `title` | str | oui | Titre d'origine (langue de la source) |
| `title_fr`, `title_en` | str | non | Traductions produites par l'IA quand la clé est branchée |
| `lang` | str | non | Langue détectée du titre (`fr`, `en`, `es`…) |
| `summary` | str | non | Résumé court (jamais l'article complet) |
| `headline` | str | non | Titre de l'article lié (GDELT, `enrich.py`) |
| `date` | ISO 8601 UTC | oui | Date de l'événement (dernière mise à jour si fusionné) |
| `start` | ISO 8601 UTC | oui | Début (le plus ancien des événements fusionnés) |
| `first_seen` | ISO 8601 UTC | — | Première détection par le robot |
| `lat`, `lon` | float (4 décimales) | oui | Position |
| `precision` | `exact` \| `city` \| `region` \| `country` | oui | Précision de la position |
| `place` | str | non | Lieu lisible |
| `country` | ISO2 | non | Pays (calculé par point dans polygone si absent) |
| `url` | str | oui | Lien vers la source |
| `confidence` | `high` \| `medium` \| `low` | oui | Confiance (multi-source = `high`) |
| `tags` | list[str] | oui | `press`, `auto-detected`, `ai`, `multi-source`, `verified`… |
| `merged` | list[str] | — | Identifiants absorbés par le dédoublonnage |
| `triage` | dict | — | Verdict du contrôle d'entrée (mémoire du robot, v0.24) : `status` (ok, context, noise, invalid, pending, unverifiable), `reason`, `since` (date du verdict), `sig` (empreinte règles + contenu) |
| `physical` | bool | — | Avis de l'IA : fait physique confirmé (titres analysés par l'IA) |
| `headline_failed` | bool | — | GDELT : aucun article lisible (page bloquée, sans titre) |
| `corroboration` | dict | — | Recoupement (v0.25) : `independent` (sources indépendantes), `outlets` (médias), `copies` (reprises d'une même dépêche ou d'un même groupe), `kinds` (types : capteur, officiel, presse, détection automatique, réseaux sociaux) |
| `press_reports` | int | — | Fiche officielle (USGS, GDACS…) : articles de presse qui lui ont été rattachés |
| `unconfirmed` | str | — | `capteurs` : séisme chiffré rapporté par la presse sans mesure officielle correspondante (crédibilité 4) |
| `disputed` | dict | — | Démenti publié (titre, lien, média, date) : crédibilité 4 jusqu'à la décision de l'analyste |
| `mag_spread` | [float, float] | — | Séisme vu par deux réseaux (USGS, EMSC) avec un écart de magnitude ≥ 0,5 |
| `admiralty` | str `A1`–`F6` | — | Cotation de l'Amirauté (`quality.py`) |
| `verified` | dict | — | Validation de l'analyste (`config/verified.json`) |

## 2. Fichiers publiés (`docs/data/`)

| Fichier | Variable | Producteur | Rythme | Consommateurs |
|---|---|---|---|---|
| `data.js` | `VS_DATA` | `collecte.py` → `publish.write_outputs` | 30 min | toutes les pages |
| `events.geojson` | — | `publish.write_outputs` | 30 min | réutilisation externe (« API » statique) |
| `archive/AAAA-MM.js` | `VS_ARCHIVE[mois]` | `publish.write_archives` | 30 min | `app.js` (périodes > 30 j) |
| `history/index.js`, `stats-AAAA.js`, `map/AAAA-MM.js` | `VS_HIST_INDEX`, `VS_HIST`, `VS_HMAP` | `historique.py` (manuel) | mensuel | `app.js` (Analyses) |
| `profiles.js` | `VS_PROFILES` | `profiles.py` | hebdo | `report.js`, `brief.js`, `app.js` |
| `practical.js` | `VS_PRACTICAL` | `practical.py` (Wikidata, progressif) | 30 min | `report.js`, Travel buddy |
| `calendar.js` | `VS_CALENDAR` | `agenda.py` | 30 min | Agenda, fiche pays, rapport |
| `reports.js` | `VS_REPORTS` | `reports.py` (flux toutes les 3 h) | 30 min | onglet Rapports, fiche pays |
| `early_warning.js` | `VS_EW` | `early_warning.py` | 30 min | `ew.js` |
| `country/<ISO2>.js` | `VS_CDETAIL[iso]` | `country_detail.py` | 30 min | `report.js`, fiche pays (villes) |
| `health.js` | `VS_HEALTH` | `country_detail.py` (copie de `config/health.json`) | 30 min | `report.js` |
| `traffic.js` | `VS_TRAFFIC` | `traffic.py` | 30 min | espace Trafic |
| `econ.js` | `VS_ECON` | `collecte.py` | 30 min | rapport pays |
| `cities.js` | `VS_CITIES` | `publish.write_cities` (GeoNames) | 30 min | recherche, Travel buddy |
| `config.js` | `VS_CONFIG` | `collecte.py` | 30 min | comptes, trafic (aucun secret : URL et clé **publique** Supabase seulement) |
| `providers.js` | `VS_PROVIDERS` | `veille/providers.py` | 30 min | `categories`, `groups`, `tiers` (config/providers.json), `registered` (fiches inscrites : id, name, web, hq, countries, categories, tier, score), `providers` (repérés par Angor, niveau E : name, web, hq, regions, categories, note) et `local` (par pays) ; `services` = ancien nom des catégories |
| `legal.js` | `VS_LEGAL` | `veille/legal.py` | 30 min | informations légales de `config/legal.json` (sans les clés `_…`), `sources` (nom, licence des sources actives), `missing` (champs obligatoires vides) ; lu par les pages légales et `account.js` (versions à accepter) |
| `countries.js` | `VS_COUNTRIES` | `tools/build_countries.py` | figé (versionné) | toutes les pages |
| `factbook.js`, `guides.js`, `providers.js` | `VS_FACTBOOK`, `VS_GUIDES`, `VS_PROVIDERS` | outils ponctuels | figés (versionnés) | rapport, Travel buddy |

Les fichiers générés sont listés dans `.gitignore` : ils sont produits par le robot en ligne et déployés avec
le site, jamais versionnés (sauf les fichiers « figés »).

### `data.js` (`VS_DATA`)

| Clé | Contenu |
|---|---|
| `generated`, `version` | Date de génération (ISO), version du robot |
| `taxonomy` | `{severity, risk_levels, groups, categories}` exportés de `model.py` |
| `events` | Événements des 30 derniers jours (`settings.map_days`) |
| `countries` | `{ISO2: {level 1–5, score, basis "computed"/"analyst", components{advisories, security, hazards}, counts, advisories{nom: avis}, data_quality}}` |
| `countries[iso].advisories[nom]` | `{level, scale, label, url, updated}` + selon la source : `max`, `parts` (zones), `map` (carte officielle), `excerpt` (MEAE), `reasons` (motifs US : `terrorism`, `crime`, `unrest`, `kidnapping`, `detention`, `conflict`, `health`, `natural`, `landmines`) |
| `news` | Fil d'actualité (titres sans position, et titres de contexte : champ `context` = motif, v0.23) |
| `status` | État de chaque source : `ok`, `count`, `error`, `last_success`, `fail_streak`, `paused`, `duration_s`, `license` |
| `coverage`, `source_quality` | Couverture par pays, qualité mesurée par source |
| `sites`, `corridors`, `site_alerts` | Vides en ligne (`VS_PUBLIC=1`) |
| `settings` | Réglages publics (nom du produit, langue, URL du relais IA, configuration publique des comptes) |
| `crises` | Chronologies de crise |
| `country_stats` | `{ISO2: {"24h"/"72h"/"7d"/"30d"/"90d": {total, by_cat}}}` |
| `archives` | `{"AAAA-MM": nombre}` des archives disponibles |
| `analytics` | Séries quotidiennes par groupe (onglet Analyses) |
| `pulse` | `{ISO2: {value 0–100, d7, d30, anomaly, spark, drivers}}` |
| `verified` | Validations de l'analyste (statut, gravité, catégorie, note) |

### `country/<ISO2>.js` (`VS_CDETAIL[iso]`)

`{iso, generated, cities[], country_activity, airports[], emergency, driving, health, fcdo}`

- `cities[]` : `{name, name_fr, lat, lon, pop, capital, adm1, tz, radius_km, airport{name, iata, icao, km}, stats{n90, n30, severe90, score, level 0–4, by_cat, share}, top[événements compacts], fcdo[phrases], note}`
  - `note` : copie de l'entrée de `config/city_notes.json` (niveau, résumé, zones, conseils, usages)
  - événement compact : `{id, t, tf, te, d, s, c, src, u}` = titre, titre FR, titre EN, date, gravité, catégorie, source, lien
- `emergency` : `{general[], notes, lines[], fcdo[{service, number}]}`
- `health` : `{risks[], vaccines[], malaria: "high" | "limited" | null}` — clés de `config/health.json`
- `fcdo` : `{updated, reviewed, url, parts{warnings, entry, safety, health, help}}`, chaque partie étant une liste de rubriques `{h: titre, l: niveau 2–4, b: [["p", texte] | ["ul", [éléments]]]}`

### `traffic.js` (`VS_TRAFFIC`)

`{generated, source, license, mil[], emergency[], zones{id: {n, mil, ac[]}}}`.
Aéronef compact (liste, pour réduire la taille) :
`[hex, indicatif, immatriculation, type, lat, lon, altitude_ft | 0 au sol | null, vitesse_kt, cap, squawk, militaire 0/1]`,
plus pour `emergency` un 12e élément : `hijack` | `radio` | `emergency`.

## 3. Configuration (`config/`)

| Fichier | Rôle | Modifié par |
|---|---|---|
| `settings.json` | Réglages généraux : nom, langue, rétention, IA, alertes, point quotidien, Pulse, comptes, trafic | analyste / développeur |
| `sources.json` | Liste des sources : `{id, type, enabled, name, license, …paramètres du connecteur}` | développeur |
| `risk.json` | Pondérations et seuils de la note de risque, niveaux imposés par l'analyste (`overrides`) | analyste |
| `verified.json` | Validations « Vérifié Angor » et fausses alertes | analyste (mode analyste du site) |
| `sites.json` | Sites et trajets **d'exemple** ; les vrais vont dans `sites.local.json` (ignoré par git) ou le secret `SITES_JSON` | analyste |
| `calendar.json` | Échéances ajoutées à la main | analyste |
| `reports.json` | Flux de rapports et ajouts manuels | analyste |
| `early_warning.json` | Régions de l'alerte précoce et paramètres | développeur |
| `press_outlets.json` | Médias de référence par pays et cotation | développeur |
| `city_notes.json` | Notes d'analyste par ville (à valider) | analyste |
| `health.json` | Listes de pays par risque sanitaire, textes maladies et vaccins | analyste / développeur |
| `providers.json` | Catégories de services des prestataires (code, groupe, libellés), niveaux de fiabilité A–E et couleurs | développeur |
| `providers_directory.json` | Prestataires repérés par Angor dans des sources publiques (non vérifiés), par grande région ou par pays (`local`) | analyste |
| `legal.json` | Identité de l'éditeur, médiateur, hébergeurs, sous-traitants, services tiers, offres, crédits, statut et versions des documents légaux (voir [RGPD.md](RGPD.md)) | éditeur |

## 4. Mémoire du robot (`data/`, jamais versionnée)

Conservée entre deux collectes par le cache GitHub Actions. Si elle est perdue, le robot repart de zéro sans
planter (l'historique se reconstitue en quelques collectes, les référentiels se retéléchargent).

| Élément | Contenu |
|---|---|
| `store.json` | `events` (95 jours), `news`, `econ`, `headlines`, `advisories` (dernier état par source), `status`, `state` (curseurs, signatures de configuration, alertes déjà envoyées, historique Pulse…), caches IA |
| `fcdo/<ISO2>.json` | Texte FCDO découpé (voir `fcdo.py`) |
| `admin1/<ISO2>.json` | Centres des régions administratives (geoBoundaries) |
| `ne_places.json`, `airports.json`, `hotlines.json` | Référentiels hebdomadaires (Natural Earth, OurAirports, worldhotlines.org) |
| `geonames/` | Dictionnaire de villes GeoNames |
| `early_warning.json` | Cache climat / humanitaire / sécurité de l'alerte précoce |

## 5. Base des comptes (Supabase, `supabase/schema.sql`)

| Table / fonction | Contenu | Accès |
|---|---|---|
| `profiles` | Profil, rôle (`user`/`admin`), statut (`pending`/`approved`/`rejected`/`suspended`), préférences, sites, trajets, position facultative | soi-même ; administrateurs |
| `safety_checks`, `safety_responses` | Safety checks et réponses | comptes validés ; administrateurs |
| `push_subscriptions` | Abonnements Web Push par appareil | soi-même |
| `legal_acceptances` | `(user_id, doc, version, accepted_at)` – `doc` ∈ `cgu`, `confidentialite`, `cgv`, `dpa` ; version suffixée `-projet` tant que les textes sont au statut « projet » | lecture : soi-même, administrateurs ; écriture : `accept_legal()` et le déclencheur d'inscription (`raw_user_meta_data.accepted`) |
| `private.housekeeping()` | Effacement selon les durées de conservation ; renvoie le nombre de lignes traitées | hors API ; planifiée chaque nuit par pg_cron (`angor-housekeeping`) |
| `private.is_admin()`, `private.is_approved()` | Fonctions des règles d'accès (security definer, hors API) ; `public.is_admin()` / `is_approved()` en sont des copies sans privilège pour les fonctions Edge | utilisateurs connectés |
| `ping()` | Signe de vie (renvoie l'heure), sans privilège | clé publique (robot, toutes les 30 min) |
| `profiles.account_type` | `client` ou `provider`, fixé à l'inscription (non modifiable par l'utilisateur) | – |
| `providers` | Fiche prestataire (identité, catégories, pays, contacts, tarifs, garanties, médias, `status` draft/submitted/verified/suspended, `score`, `tier` calculés par la base) | public : nom, catégories, pays, site, niveau ; comptes validés : tout ; propriétaire et admin : écriture |
| `provider_documents` | Justificatifs (fichier privé `provider-docs/<id>/docs/…`, statut pending/validated/rejected) | propriétaire et admin ; validation : admin |
| `provider_reviews` | Avis (note 1-5, commentaire, réponse du prestataire, statut published/hidden) ; un par client et par prestataire | comptes validés ; écriture : clients validés, réponse : prestataire, masquage : admin |
| `provider_requests` | Demandes de devis (message, catégorie, pays, période, statut) | demandeur, prestataire concerné, admin |
| Stockage | `provider-media` (public, photos 5 Mo), `provider-docs` (privé, 10 Mo) ; dossier = identifiant de la fiche | règles sur `storage.objects` |

## Données publiques et données réservées (v0.22)

En ligne (robot GitHub Actions, `VS_PUBLIC=1`) et comptes configurés, `veille/vault.py` sépare les sorties de `docs/data` :

| Publics (GitHub Pages) | Réservés (Supabase Storage, compartiment privé `angor-data`) |
|---|---|
| `config.js`, `countries.js`, `legal.js`, `providers.js`, `cities.js`, `factbook.js`, `guides.js`, `history/`, `guest.js` | tout le reste : `data.js`, `events.geojson`, `reports.js`, `early_warning.js`, `calendar.js`, `econ.js`, `profiles.js`, `practical.js`, `health.js`, `traffic.js`, `country/`, `archive/` |

`guest.js` = carte des visiteurs (7 jours, champs : id, catégorie, gravité, titre, date, position, lieu, pays, précision,
fiabilité). Les fichiers réservés sont envoyés s'ils ont changé (`data/vault_manifest.json`), puis retirés de `docs/data`
(copie dans `data/private/`) avant la publication, même si l'envoi échoue. Clé : Secret GitHub `SUPABASE_SERVICE_KEY`.

## Tri des titres et regroupement des doublons (v0.23, sans IA)

**Qu'est-ce qu'un événement ?** Un fait physique qui peut toucher un voyageur ou un site : attaque, combat, manifestation,
catastrophe, épidémie, panne. Le tri (`veille/press.py`) se fait en trois temps :

1. `classify` : catégorie et gravité par mots-clés (toutes langues) ; `None` = hors sûreté (sport, culture, people…).
2. `not_incident` : bruit écarté partout (faits divers privés, procès, séisme faible, accident de chantier…).
3. `context` : titre de sûreté qui n'est pas un fait physique. Motifs : « arrestation ou suites », « projet déjoué »,
   « déclaration » (condamnation, visite, sommet, démission…), « analyse » (décryptage, statistique, question),
   « rétrospective ou démenti », « prévention, bilan ou suites » (catastrophes, santé), « annonce militaire »,
   « annonce de sécurité », « signal politique » (diplomatie). Ces titres restent dans le **Fil** (étiquette « Contexte »,
   champ `context`) mais ne sont plus placés sur la carte. Exceptions : une déclaration qui décrit une attaque précise
   (« frappes contre », « repoussé une attaque ») reste un événement, sauf démenti ou condamnation ; un bilan ou un mot de
   fait récent (tué, blessé) garde l'événement.

`is_event(titre, catégorie)` résume les trois. Pour **GDELT**, dont le titre est un code (« Military force – Kyiv »),
`gdelt_noise` lit le vrai titre de l'article (`headline`) et n'écarte que ce qui n'a manifestement rien de physique.
Dans `collecte.py`, `triage_reason` applique ces règles à tous les événements en mémoire **avant** le regroupement (un
titre écarté ne peut pas servir de base à une fiche fusionnée). Les titres retenus par l'IA (étiquette `ai`) ne sont
pas re-triés par les mots-clés de contexte.

**Regroupement par histoire** (`dedupe.story_merge`, presse et GDELT) avant la fusion par lieu et famille :

| Règle | Condition | Exemple réel |
|---|---|---|
| A | même pays, ≤ 100 km ou même lieu, ≤ 48 h, mots significatifs communs ≥ 50 % | « kill 9 civilians » puis « kill 10 civilians » |
| B | mots communs ≥ 80 %, ≤ 5 jours, où que ce soit, toutes catégories | même dépêche sur 3 jours ; même article placé à Metz et à Nancy ; crash classé « attaque » et « infrastructure » |
| C | 8 premiers mots identiques, ≤ 5 jours | titre Google News suivi d'un texte parasite |

La fiche de base est celle dont le lieu est le plus précis (puis la presse, puis la plus ancienne) ; elle prend la
gravité maximale, la dernière date, la première date (`start`), toutes les sources (25 au plus) et la liste `merged`.
Deux bilans quotidiens semblables à plus de 48 h d'écart restent deux événements. Sur les données en ligne du 5 octobre
2026 (1 500 événements), le regroupement par histoire en rattache 31, la fusion complète 79 (50 avec la seule fusion par lieu).

## Contrôle d'entrée : vérification a priori et permanente (v0.24)

`veille/triage.py` est la porte unique entre les sources et la carte. Rien n'atteint la carte, les alertes e-mail et
Telegram, les notes de risque, Pulse ni les chronologies sans un verdict `ok`.

1. **A priori** (à l'arrivée, avant la mémoire) : `collecte.py` lit d'abord le titre réel des nouvelles détections GDELT
   (`enrich.add_headlines`, les plus récentes en premier), puis `triage.check` pose un verdict sur chaque nouveauté.
   Les fiches `invalid` (position absente, impossible ou (0, 0) ; titre vide ; date illisible ; date à venir pour un
   fait de violence – une alerte météo ou une crue peut, elle, commencer dans les 10 jours) ne sont jamais stockées.
2. **Permanent** (à chaque collecte) : toute la mémoire repasse le contrôle. Une règle améliorée s'applique aussitôt
   aux fiches déjà connues ; une détection GDELT `pending` devient `ok`, `context` ou `noise` dès que son article est
   lu, `unverifiable` s'il est illisible. Pour rester rapide, une fiche dont le contenu et les règles n'ont pas changé
   garde son verdict (`sig` = empreinte de `press.py` et `triage.py` + du contenu) : le premier passage après une
   modification des règles relit tout (≈ 2 ms par fiche), les suivants prennent moins d'une seconde.
3. **Décision de l'analyste** : `config/verified.json` passe avant les règles (`verified`/`corrected` : retenu ;
   `false` : écarté). Dans « État des sources », en mode analyste, « Rétablir » sur un titre refusé crée cette
   décision (exportée avec `verified.json`, appliquée à la collecte suivante).
4. **Journal et alarme** : `store["state"]["triage"]` garde les chiffres des 48 dernières collectes et les 150 derniers
   refus (publiés dans `data.js` → `triage`, section « Contrôle des événements » d'« État des sources »). Une source dont
   plus de 85 % d'au moins 20 nouveautés sont refusées déclenche une ligne `✘ Contrôle d'entrée` dans le journal du
   robot : flux devenu hors sujet, ou règle trop stricte.
5. **IA** (si clé) : en plus de la pertinence, l'IA dit si le titre décrit un fait physique (`physical`) ; sinon le
   titre va au Fil (« contexte (IA) »). Ancienne fiche IA sans cet avis : règles par mots-clés.

Le verdict des sources officielles (USGS, GDACS, NWS, Météo-France, OMS…) est `ok` dès que la fiche est plausible :
ce sont des événements déjà vérifiés par leur producteur.

## Recoupement des sources et des contenus (v0.25)

`veille/corroborate.py`, après le regroupement des doublons et avant la cotation de l'Amirauté :

| Contrôle | Règle | Effet |
|---|---|---|
| Sources indépendantes | un témoin par domaine, par groupe de presse (`MEDIA_GROUPS` : EBRA, Schibsted, Gannett, ARD, RFE/RL…) et par titre identique repris mot pour mot | `corroboration` ; crédibilité 2 dès 3 sources indépendantes, ou 2 de types différents (officiel + presse) |
| Confirmation par les capteurs | séisme (300 km, article publié dans les 72 h), cyclone (900 km, 5 jours), éruption (150 km, 14 jours) rapportés par la presse ou GDELT, rattachés à la fiche officielle (USGS, EMSC, GDACS, NOAA, GVP…) | une seule fiche, articles en sources (`press_reports`) ; séisme chiffré sans mesure : `unconfirmed`, crédibilité 4 |
| Deux réseaux sismiques | USGS et EMSC fusionnés par lieu et heure | confiance haute ; écart de magnitude ≥ 0,5 : `mag_spread` |
| Démentis | titre de contexte contenant un démenti (« fake », « hoax », « démenti », « desmiente », « no factual basis »…) qui partage au moins 3 mots significatifs (25 %) avec l'événement, même pays, ± 3 jours | `disputed`, crédibilité 4, lien vers le démenti sur la fiche |

L'analyste garde le dernier mot (`config/verified.json`). Le recoupement travaille sur des copies : la mémoire du robot
n'est jamais modifiée.

