# Connecteurs (sources de données)

Un connecteur = un module de `veille/connectors/`, déclaré dans `REGISTRY` (`veille/connectors/__init__.py`)
et activé par une entrée de `config/sources.json`. Exemple de référence, court et complet : `usgs.py`.

## Interface

```python
KIND = "events"            # ou "advisories"

def fetch(cfg, ctx):
    """cfg : l'entrée de la source dans config/sources.json (dict).
       ctx : veille.connectors.Context.
       KIND "events"     → renvoie une liste d'événements construits avec model.make_event(...)
       KIND "advisories" → renvoie {ISO2: {"level": 1..4, "scale": 4, "label": str, "url": str, "updated": str, ...}}"""
```

`ctx` (classe `Context`) fournit :

| Attribut | Usage |
|---|---|
| `ctx.countries` | `geo.Countries` : `locate(lat, lon)`, `by_country_name(nom)`, `get(iso2)`, `name(iso2, lang)` |
| `ctx.state` | Dictionnaire **persistant** entre deux collectes (curseurs, cache léger). Utiliser une clé propre à la source |
| `ctx.log(msg)` | Journal de la collecte (visible dans GitHub Actions) |
| `ctx.now` | Heure UTC de la collecte |
| `ctx.news` | Ajouter ici les articles **sans position** (fil d'actualité) |
| `ctx.press`, `ctx.econ` | Titres de presse à trier par `press.py` (le connecteur ne classe pas lui-même) |
| `ctx.prefetch` | Flux RSS déjà téléchargés en parallèle : `{url: réponse ou exception}` |
| `ctx.advisories` | Avis aux voyageurs déjà connus (lecture) |
| `ctx.purge` | Préfixes d'identifiants à effacer de l'historique |

## Règles

- **Réseau** : uniquement via `veille.http` (`get`, `get_json`) : délais, relances et authentification y sont gérés.
  Toujours passer un `timeout` raisonnable ; respecter `robots.txt` et les conditions d'utilisation.
- **Identifiants** : stables d'une collecte à l'autre et préfixés (`usgs-…`). Le préfixe sert à reconstruire
  l'historique quand la configuration d'une source change (`id_prefix` dans `collecte.py`).
- **Erreurs** : lever une exception si la source est indisponible ; `collecte.py` l'isole, compte les échecs
  et met la source en pause 24 h après 3 échecs. Pour une source à authentification, lever `http.AuthMissing`
  quand le secret manque : la source est alors ignorée proprement.
- **Budget** : le robot dispose de 20 minutes au total. Une source lente doit se limiter (`time_budget_s`, `pages_per_run`)
  et reprendre au tour suivant grâce à `ctx.state` (voir `uk_advisories.py`, `practical.py`).
- **robots.txt** (v0.28) : tout connecteur qui lit un site de presse, un flux ou une page passe `robots=True` à
  `http.get` (`rss`, `official_rss`, `outlet_feeds`, `telegram`, `gnews`, `outlets`, titres d'articles GDELT dans
  `enrich.py`). Le robots.txt du site est lu une fois par semaine (`veille/robots.py`, mémoire dans
  `store["state"]["robots"]`) ; une adresse interdite lève `RobotsDisallowed` sans qu'aucune requête parte. Les API
  documentées (USGS, NWS, FMI…) n'y sont pas soumises. Exemption : `"robots_exempt": ["hôte"]` dans la source, affichée
  dans l'état des sources ; à réserver à une transition décidée (aujourd'hui : `news.google.com` pour `gnews` et
  `outlets`, dont le robots.txt interdit `/rss/search`, en attendant que `outlet_feeds` prenne le relais).
- **Données** : événements, jamais personnes. Titre + résumé court + lien, jamais l'article complet.
- **Licence** : renseigner `license` dans `sources.json` et vérifier l'usage commercial avant la vente
  (ex. ACLED, OpenSky, Global Fishing Watch, airplanes.live : non commercial sans licence).

## Ajouter une source : marche à suivre

1. Créer `veille/connectors/ma_source.py` (en-tête : nom, URL, licence, ce que la source apporte).
2. L'ajouter à l'import et à `REGISTRY` dans `veille/connectors/__init__.py`.
3. La déclarer dans `config/sources.json` :
   ```json
   {"id": "ma_source", "type": "ma_source", "enabled": true, "name": "Nom affiché", "license": "CC BY 4.0"}
   ```
   Paramètres libres possibles (lus via `cfg.get(...)`).
4. Écrire un test sans réseau dans `tests/test_sources.py` (réponse simulée par `monkeypatch`, voir `test_avis_americain_motifs`).
5. Tester en réel : `python collecte.py --only ma_source`, puis vérifier « État des sources » sur la carte.
6. Si la source a besoin d'un secret : l'ajouter à `.env.example` (vide), à `collecte.yml` (`env:`) et au guide.
7. Mettre à jour [DONNEES.md](DONNEES.md) si un champ nouveau apparaît, `CHANGELOG.md` et l'aide utilisateur.

## Connecteurs génériques (sans code)

| Type | Usage |
|---|---|
| `rss` | Flux RSS/Atom : presse, bulletins. Tolère les flux mal formés (`parse_xml`) |
| `official_rss` | Bulletins officiels (catégorie et gravité fixées ou déduites de mots-clés, géolocalisation GeoRSS / texte). Option `group` (v0.28) : expression à un groupe (nom de la tempête) ; seul le dernier bulletin de chaque groupe est gardé, sous un identifiant stable (NHC : un cyclone = une fiche) |
| `jsonapi` | API JSON authentifiée (fournisseur payant) : correspondance des champs dans la configuration |
| `gnews`, `outlets` | Presse locale via Google News, en rotation par pays (exemption robots.txt **temporaire**, voir ci-dessous) |
| `outlet_feeds` | Flux RSS propres des médias de `press_outlets.json` : découverte (page d'accueil, puis `/feed/`, `/rss`…), puis lecture par roulement (v0.28) |
| `telegram` | Canaux publics (aperçu `t.me/s/…`), budget de temps |

Liste complète et état : `python collecte.py --list`.

## Langues de la presse (v0.25)

Les mots-clés de recherche (connecteurs `gnews` et `outlets`) et de tri (`press.py`) existent en 56 langues :
21 historiques dans `press.py` et `gnews.py`, 35 dans `veille/langs.py` (langues nordiques et baltes, Europe
centrale, Balkans – `sh` pour le serbe, le croate, le bosnien et le monténégrin en alphabet latin –, grec,
géorgien, arménien, azéri, ouzbek, mongol, hindi, népalais, pachto, tamoul, japonais, coréen, vietnamien, malais, filipino,
birman, khmer, swahili, haoussa). Ajouter une langue : une entrée dans `LANGS` (requête, mots par catégorie, morts et
blessés, arrestations, procédures, sport), son édition Google News dans `EDITIONS` si elle existe, puis des cas
de test dans `tests/test_press.py` (`MULTI_GARDER`, `MULTI_ECARTER`). Les mots de 4 lettres ou moins sont cherchés
en mot entier : vérifier qu'ils n'ont pas un autre sens dans une autre langue (« hari », « sud », « vita »…).

## Santé des médias de référence (v0.25)

`outlets.py` tient, pour chaque média du catalogue, le nombre de requêtes où il figurait et de titres obtenus
(`store["state"]["outlet_stats"]`). Un média sans aucun titre après 30 requêtes est un « média muet » : domaine
erroné, site fermé ou média sans actualité de sûreté. La liste est publiée dans « État des sources » (`outlets_health`)
pour correction dans `tools/outlets_src.py`.

## Filtres des flux officiels et de GDELT (v0.28)

Un flux officiel publie aussi ce qui n'est pas un incident. Filtres en place :

| Connecteur | Écarté | Gardé |
|---|---|---|
| `nws` (`worth_keeping`) | gel, givre, risque d'incendie (« Red Flag », « Fire Weather »), brouillard, fumée, qualité de l'air, avis de vent ou de chaleur, simples veilles (« Watch ») | avertissements (« Warning »), veilles cycloniques, de submersion, de tsunami et de vent extrême ; évacuations, dont la catégorie est lue dans le texte (feu, crue…) |
| `meteoalarm` | zones uniquement maritimes (`marine_only`), brouillard orange | vigilances orange et rouge à terre, brouillard rouge |
| `official_rss` NHC | bulletins précédents d'un même cyclone | le dernier bulletin |
| `gdelt_events` | code CAMEO 192 « occupation de territoire » (une situation, pas un fait daté : `DROP_CODES`) ; fait violent placé à moins de 30 km du centre d'une capitale alors qu'un autre pays figure parmi les acteurs (capitale citée en tête de dépêche : « RIYADH – … frappes au Yémen ») | le reste, sous les seuils habituels |

Les capitales viennent du dictionnaire GeoNames (`geo.capitals()`, code `PPLC`) ; sans ce fichier, la règle ne
s'applique pas. `FILTER_VERSION` de GDELT n'a pas été incrémenté : l'historique n'est pas reconstruit, les anciens
événements « occupation » sont écartés par le tri (`triage`, motif « situation, pas un fait daté »).

## Flux propres des médias et sortie de Google News (v0.28)

Le connecteur `outlet_feeds` examine 40 médias du catalogue par collecte (environ 1 400 hors médias internationaux
« + », soit une journée et demie pour tout le catalogue à raison d'une collecte toutes les 30 minutes) et lit 150 flux
trouvés par collecte, en parallèle. Mémoire : `store["state"]["outlet_feeds"]` (`{domaine: {f: flux, t: date, w: motif,
k: échecs}}`) ; un média sans flux est réexaminé au bout de 30 jours (3 jours si aucun serveur n'a répondu), un flux en échec
5 fois de suite ou devenu interdit par le robots.txt est redécouvert.
Bilan dans « État des sources » (médias examinés, flux trouvés, pays couverts).

**Couper Google News** quand le bilan le permet (par exemple 80 % des pays couverts et des titres comparables sur une
semaine) : `"enabled": false` sur `gnews` et `outlets` dans `config/sources.json` (et retirer `robots_exempt`). Un média
sans flux et important pour un pays peut être remplacé ou complété par une source `rss` déclarée à la main.

## Sources hors connecteurs

Certaines données ne sont pas des événements et ont leur propre module, appelé par `collecte.py` :
`profiles.py`, `practical.py`, `agenda.py`, `reports.py`, `early_warning.py`, `country_detail.py`, `fcdo.py`,
`traffic.py`. Même règles : réseau via `http`, échec isolé, budget de temps, licence documentée en en-tête.
