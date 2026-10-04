# Bibliothèques recopiées dans `docs/vendor/`

Recopiées pour que le site fonctionne sans dépendre d'un CDN (et hors ligne via le service worker).
Mettre à jour ce tableau à chaque remplacement d'un fichier, puis lancer le test de fumée (`tests/e2e`).

| Dossier | Bibliothèque | Version | Licence | Source |
|---|---|---|---|---|
| `leaflet/` | Leaflet | 1.9.4 | BSD-2 | https://leafletjs.com |
| `markercluster/` | Leaflet.markercluster | à vérifier (1.5.x) | MIT | https://github.com/Leaflet/Leaflet.markercluster |
| `maplibre/maplibre-gl.js` | MapLibre GL JS | 4.7.1 | BSD-3 | https://maplibre.org |
| `maplibre/leaflet-maplibre-gl.js` | Pont Leaflet ↔ MapLibre (options `padding` et `updateInterval` réglées par `app.js`) | à vérifier | ISC | https://github.com/maplibre/maplibre-gl-leaflet |
| `chartjs/` | Chart.js | 4.5.1 | MIT | https://www.chartjs.org |
| `icons.js` | Icônes Lucide (sélection, tracés SVG) | — | ISC | https://lucide.dev |
| `fonts/` | Polices Instrument Sans, Instrument Serif, IBM Plex Mono (paquets `@fontsource/*`, sous-ensembles latin et latin-ext, woff2) – remplacent Google Fonts (v0.19) | 5.3.0 | SIL OFL 1.1 | https://fontsource.org |
| `flags/` | Drapeaux `flag-icons` (SVG 4:3) – remplacent flagcdn.com (v0.19) | 7.5.0 | MIT | https://github.com/lipis/flag-icons |
