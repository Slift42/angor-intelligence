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
| `official_rss` | Bulletins officiels (catégorie et gravité fixées ou déduites de mots-clés, géolocalisation GeoRSS / texte) |
| `jsonapi` | API JSON authentifiée (fournisseur payant) : correspondance des champs dans la configuration |
| `gnews`, `outlets` | Presse locale via Google News, en rotation par pays |
| `telegram` | Canaux publics (aperçu `t.me/s/…`), budget de temps |

Liste complète et état : `python collecte.py --list`.

## Sources hors connecteurs

Certaines données ne sont pas des événements et ont leur propre module, appelé par `collecte.py` :
`profiles.py`, `practical.py`, `agenda.py`, `reports.py`, `early_warning.py`, `country_detail.py`, `fcdo.py`,
`traffic.py`. Même règles : réseau via `http`, échec isolé, budget de temps, licence documentée en en-tête.
