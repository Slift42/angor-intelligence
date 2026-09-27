/* Angor Intelligence – application cartographique (Leaflet, sans framework) */
(function () {
  'use strict';

  const D = window.VS_DATA || null;
  const COUNTRIES = window.VS_COUNTRIES || { type: 'FeatureCollection', features: [] };
  const ICONS = window.VS_ICONS || {};
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* stockage indisponible */ } }
  };

  /* ------------------------------------------------------------------ textes */
  const I18N = {
    fr: {
      search_ph: 'Rechercher un pays, une ville, un événement…',
      crisis_major: 'Crise majeure', crisis_crisis: 'Crise', crisis_alert: 'Alerte', loading_archive: 'Chargement de l’historique…',
      tab_alerts: 'Alertes', tab_ongoing: 'En cours', tab_countries: 'Pays', tab_news: 'Fil', tab_sites: 'Mes sites',
      ongoing_hint: 'Alertes des 72 dernières heures jugées actives : gravité élevée ou critique, catastrophe en cours, situation évolutive, recoupée par plusieurs sources ou proche de vos sites. Regroupées par pays.',
      only_ongoing: 'Afficher uniquement les alertes en cours sur la carte', no_ongoing: 'Aucune crise en cours.',
      n_crises: (c, n) => `${c} pays · ${n} alerte${n > 1 ? 's' : ''} en cours`, range: 'Période personnalisée', range_from: 'Du', range_to: 'au', apply: 'Appliquer',
      range_err: 'Dates invalides : format JJ/MM/AAAA, date de début avant la date de fin.',
      all_countries: 'Tous les pays', risk_cat: 'Catégorie de risque', min_sev: 'Gravité', incl_auto: 'Inclure les détections auto',
      k_multi: 'Recoupées (multi-sources)', k_auto: 'Part de détections auto', c_places: 'Lieux les plus touchés',
      filters: 'Filtres', only_sites: 'Uniquement près de mes sites', hide_auto: 'Masquer les détections automatiques non vérifiées',
      sort_date: 'Plus récentes', sort_sev: 'Plus graves', all: 'Tout', none: 'Aucun', export_pdf: 'PDF',
      n_alerts: n => `${n} alerte${n > 1 ? 's' : ''}`, show_more: n => `Afficher ${n} de plus`,
      no_alerts: 'Aucune alerte ne correspond à ces filtres sur la période.',
      countries_hint: 'Niveau de risque pays de 1 (Minimal) à 5 (Extrême), calculé à partir des avis officiels et de l’activité récente. Cliquez sur un pays pour son rapport.',
      country_ph: 'Filtrer les pays…', news_hint: 'Titres de presse (≈ 110 pays, 12 langues) relevant de la sûreté. Titre et lien uniquement.',
      news_ph: 'Filtrer le fil (pays, mot-clé)…', no_news: 'Aucun article pour le moment.',
      sites_hint: 'Vos sites et leur rayon de vigilance. Les alertes dans ce rayon sont signalées partout dans l’outil.',
      add_site: 'Ajouter un site', export_sites: 'Exporter (sites.json)', site_name: 'Nom du site', site_radius: 'Rayon de vigilance (km)',
      save: 'Enregistrer', cancel: 'Annuler', pick_site: 'Cliquez sur la carte pour placer le site', site_saved: 'Site enregistré dans ce navigateur',
      site_config: 'Défini dans config/sites.json', site_local: 'Ajouté dans ce navigateur', delete: 'Supprimer',
      hits: n => n ? `${n} alerte${n > 1 ? 's' : ''} dans le rayon` : 'Aucune alerte dans le rayon', radius: 'rayon',
      export_done: 'Fichier téléchargé : copiez-le dans config/sites.local.json pour que le robot surveille ces sites.',
      layers: 'Couches', lyr_events: 'Alertes', lyr_risk: 'Risque pays', lyr_sites: 'Mes sites',
      basemap: 'Fond', bm_esri: 'Épuré (Esri)', bm_vector: 'Vectoriel (OpenFreeMap)', bm_plain: 'Neutre (hors ligne)',
      legend_sev: 'Gravité', legend_risk: 'Risque pays', legend_auto: 'Contour pointillé : détection automatique',
      sources_ok: (a, b) => `${a}/${b} <span class="src-word">sources</span>`, updated: 'Mise à jour', stale: 'Données anciennes',
      source_status: 'État des sources', ok: 'OK', error: 'Erreur', items: 'éléments', last_success: 'Dernier succès', paused: 'En pause (3 échecs)',
      date: 'Date', start: 'Début', place: 'Lieu', country: 'Pays', precision: 'Précision', coords: 'Coordonnées',
      confidence: 'Confiance', sources: 'Sources', source_lbl: 'Source', outlets: n => `${n} média${n > 1 ? 's' : ''}`,
      near_sites: 'Sites concernés', zoom: 'Centrer la carte', open_source: 'Ouvrir la source', description: 'Description',
      auto_notice: 'Détection automatique à partir de la presse, non vérifiée. Lieu et nature de l’événement à confirmer avant toute décision.',
      multi_source: 'Recoupé par plusieurs sources',
      conf: { low: 'Faible', medium: 'Moyenne', high: 'Élevée' },
      prec: { exact: 'Point précis', city: 'Ville', region: 'Région', country: 'Pays (centre)' },
      risk_level: 'Niveau de risque', components: 'Composantes du score', comp_adv: 'Avis officiels', comp_sec: 'Activité sécuritaire (7 j)',
      comp_haz: 'Catastrophes et santé (7 j)', advisories: 'Avis aux voyageurs', recent: 'Alertes récentes dans le pays',
      no_recent: 'Aucune alerte récente.', no_data: 'Pas de données', risk_notice: 'Évaluation automatique d’aide à la décision. Votre analyse peut la corriger (config/risk.json → overrides).',
      analyst: 'Niveau fixé par l’analyste', events_only: 'Aucun avis officiel disponible : note fondée sur l’activité récente uniquement.',
      level: 'Niveau', of: 'sur', km: 'km', country_report: 'Rapport pays (PDF)', incidents: 'Incidents',
      empty_title: 'Aucune donnée pour l’instant', empty_body: 'Lancez la collecte dans le terminal, depuis le dossier du projet :',
      empty_after: 'puis rechargez cette page.', at_sea: 'En mer',
      analytics: 'Analyses', close: 'Fermer', a_title: 'Tableau de bord analytique', a_period: p => `Période : ${p}`,
      k_events: 'Alertes sur la période', k_critical: 'Critiques / élevées', k_countries: 'Pays à risque élevé ou extrême', k_sources: 'Sources actives', k_press: 'Titres de presse (3 j)',
      c_daily: 'Évolution des alertes par famille', c_cats: 'Répartition par catégorie', c_top: 'Pays les plus touchés', c_sev: 'Répartition par gravité',
      c_risk: 'Pays par niveau de risque', c_src: 'Contribution des sources',
      print_title: 'Extraction des alertes', print_filters: 'Filtres', print_generated: 'Généré le',
      period_lbl: { 24: '24 h', 72: '72 h', 168: '7 j', 720: '30 j', 2160: '3 mois', 4320: '6 mois', 8760: '1 an', all: 'Tout' }
    },
    en: {
      search_ph: 'Search a country, city or event…',
      crisis_major: 'Major crisis', crisis_crisis: 'Crisis', crisis_alert: 'Alert', loading_archive: 'Loading history…',
      tab_alerts: 'Alerts', tab_ongoing: 'Ongoing', tab_countries: 'Countries', tab_news: 'Feed', tab_sites: 'My sites',
      ongoing_hint: 'Alerts from the last 72 hours considered active: high or critical severity, ongoing disaster, evolving situation, corroborated by several sources or close to your sites. Grouped by country.',
      only_ongoing: 'Show only ongoing alerts on the map', no_ongoing: 'No ongoing crisis.',
      n_crises: (c, n) => `${c} countries · ${n} ongoing alert${n > 1 ? 's' : ''}`, range: 'Custom period', range_from: 'From', range_to: 'to', apply: 'Apply',
      range_err: 'Invalid dates: use DD/MM/YYYY, start before end.',
      all_countries: 'All countries', risk_cat: 'Risk category', min_sev: 'Severity', incl_auto: 'Include auto-detections',
      k_multi: 'Corroborated (multi-source)', k_auto: 'Share of auto-detections', c_places: 'Most affected places',
      filters: 'Filters', only_sites: 'Only near my sites', hide_auto: 'Hide unverified auto-detections',
      sort_date: 'Most recent', sort_sev: 'Most severe', all: 'All', none: 'None', export_pdf: 'PDF',
      n_alerts: n => `${n} alert${n > 1 ? 's' : ''}`, show_more: n => `Show ${n} more`,
      no_alerts: 'No alert matches these filters for the period.',
      countries_hint: 'Country risk level from 1 (Minimal) to 5 (Extreme), computed from official advisories and recent activity. Click a country for its report.',
      country_ph: 'Filter countries…', news_hint: 'Security-related headlines (≈ 110 countries, 12 languages). Title and link only.',
      news_ph: 'Filter the feed (country, keyword)…', no_news: 'No article yet.',
      sites_hint: 'Your sites and their watch radius. Alerts inside the radius are flagged throughout the tool.',
      add_site: 'Add a site', export_sites: 'Export (sites.json)', site_name: 'Site name', site_radius: 'Watch radius (km)',
      save: 'Save', cancel: 'Cancel', pick_site: 'Click on the map to place the site', site_saved: 'Site saved in this browser',
      site_config: 'Defined in config/sites.json', site_local: 'Added in this browser', delete: 'Delete',
      hits: n => n ? `${n} alert${n > 1 ? 's' : ''} within radius` : 'No alert within radius', radius: 'radius',
      export_done: 'File downloaded: copy it to config/sites.local.json so the collector monitors these sites.',
      layers: 'Layers', lyr_events: 'Alerts', lyr_risk: 'Country risk', lyr_sites: 'My sites',
      basemap: 'Basemap', bm_esri: 'Clean (Esri)', bm_vector: 'Vector (OpenFreeMap)', bm_plain: 'Neutral (offline)',
      legend_sev: 'Severity', legend_risk: 'Country risk', legend_auto: 'Dashed outline: auto-detection',
      sources_ok: (a, b) => `${a}/${b} <span class="src-word">sources</span>`, updated: 'Updated', stale: 'Stale data',
      source_status: 'Source status', ok: 'OK', error: 'Error', items: 'items', last_success: 'Last success', paused: 'Paused (3 failures)',
      date: 'Date', start: 'Start', place: 'Location', country: 'Country', precision: 'Precision', coords: 'Coordinates',
      confidence: 'Confidence', sources: 'Sources', source_lbl: 'Source', outlets: n => `${n} outlet${n > 1 ? 's' : ''}`,
      near_sites: 'Affected sites', zoom: 'Center map', open_source: 'Open source', description: 'Description',
      auto_notice: 'Automatically detected from news coverage, unverified. Confirm location and nature before any decision.',
      multi_source: 'Corroborated by several sources',
      conf: { low: 'Low', medium: 'Medium', high: 'High' },
      prec: { exact: 'Exact point', city: 'City', region: 'Region', country: 'Country (centroid)' },
      risk_level: 'Risk level', components: 'Score components', comp_adv: 'Official advisories', comp_sec: 'Security activity (7 d)',
      comp_haz: 'Hazards and health (7 d)', advisories: 'Travel advisories', recent: 'Recent alerts in the country',
      no_recent: 'No recent alert.', no_data: 'No data', risk_notice: 'Automated decision-support rating. Your analysis can override it (config/risk.json → overrides).',
      analyst: 'Level set by analyst', events_only: 'No official advisory available: rating based on recent activity only.',
      level: 'Level', of: 'of', km: 'km', country_report: 'Country report (PDF)', incidents: 'Incidents',
      empty_title: 'No data yet', empty_body: 'Run the collector in the terminal, from the project folder:',
      empty_after: 'then reload this page.', at_sea: 'At sea',
      analytics: 'Analytics', close: 'Close', a_title: 'Analytics dashboard', a_period: p => `Period: ${p}`,
      k_events: 'Alerts in period', k_critical: 'Critical / high', k_countries: 'High or extreme risk countries', k_sources: 'Active sources', k_press: 'Press headlines (3 d)',
      c_daily: 'Alerts over time by family', c_cats: 'Breakdown by category', c_top: 'Most affected countries', c_sev: 'Breakdown by severity',
      c_risk: 'Countries by risk level', c_src: 'Source contribution',
      print_title: 'Alert extract', print_filters: 'Filters', print_generated: 'Generated on',
      period_lbl: { 24: '24 h', 72: '72 h', 168: '7 d', 720: '30 d', 2160: '3 months', 4320: '6 months', 8760: '1 year', all: 'All' }
    }
  };

  const FALLBACK_TAX = {
    severity: { 1: { fr: 'Faible', en: 'Low' }, 2: { fr: 'Modérée', en: 'Moderate' }, 3: { fr: 'Élevée', en: 'High' }, 4: { fr: 'Critique', en: 'Critical' } },
    risk_levels: { 1: { fr: 'Minimal', en: 'Minimal' }, 2: { fr: 'Faible', en: 'Low' }, 3: { fr: 'Modéré', en: 'Moderate' }, 4: { fr: 'Élevé', en: 'High' }, 5: { fr: 'Extrême', en: 'Extreme' } },
    groups: {}, categories: {}
  };
  const TAX = (D && D.taxonomy) || FALLBACK_TAX;
  const EVENTS = (D && D.events) || [];
  const RISK = (D && D.countries) || {};
  const NEWS = (D && D.news) || [];
  const STATUS = (D && D.status) || [];
  const GROUP_COLORS = { security: '#B0182E', political: '#E0A21B', natural: '#3F86C6', health: '#7D5BA6', infrastructure: '#5E6B78' };

  /* ------------------------------------------------------------------ état */
  const state = {
    lang: store.get('vs-lang', (D && D.settings && D.settings.default_lang) || 'fr'),
    theme: store.get('vs-theme', window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
    basemap: ['esri', 'vector', 'plain'].includes(store.get('vs-basemap', 'esri')) ? store.get('vs-basemap', 'esri') : 'esri',
    hours: store.get('vs-hours', 72), range: null, tab: 'alerts', aCountry: '', aGroup: '', aSev: 1, aSource: '', aAuto: true, sort: 'date', limit: 60,
    sev: store.get('vs-sev', { 1: true, 2: true, 3: true, 4: true }),
    cats: new Set(store.get('vs-cats', Object.keys(TAX.categories))),
    onlySites: false, onlyOngoing: false, hideAuto: store.get('vs-hideauto', false),
    selected: null, drawer: null, localSites: store.get('vs-sites', []), picking: false, pick: null,
    countryFilter: '', newsFilter: '', analytics: false
  };

  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));
  const t = (k, ...a) => { const v = I18N[state.lang][k]; return typeof v === 'function' ? v(...a) : (v ?? k); };
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const icon = (n, size) => `<svg viewBox="0 0 24 24"${size ? ` width="${size}" height="${size}"` : ''} fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[n] || ICONS['circle-alert'] || ''}</svg>`;
  const cssVar = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const sevColor = s => cssVar('--sev' + s);
  const riskColor = l => cssVar('--risk' + (l || 0));
  const cat = c => TAX.categories[c] || { icon: 'circle-alert', fr: c, en: c, group: 'natural' };
  const catLabel = c => cat(c)[state.lang];
  const sevLabel = s => (TAX.severity[s] || {})[state.lang] || s;
  const riskLabel = l => (TAX.risk_levels[l] || {})[state.lang] || '—';
  const isAuto = e => (e.tags || []).includes('auto-detected');
  const hostOf = u => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return ''; } };

  const countryProps = {};
  COUNTRIES.features.forEach(f => { countryProps[f.properties.iso2] = f.properties; });
  const countryName = iso => iso && countryProps[iso] ? countryProps[iso]['name_' + state.lang] : '';

  /** Description lisible : titre de l'article (presse, GDELT) ou résumé de la source officielle. */
  function describe(e) {
    if (e.headline && e.headline !== e.title) return e.headline;
    if (e.summary && !/^(Auto-detected|Detected in)/.test(e.summary)) return e.summary;
    return '';
  }
  /** Libellé clair des sources : « GDELT · 5 médias » ou « USGS + GDACS ». */
  function sourceLabel(e) {
    const srcs = e.sources || [];
    if (e.source === 'GDELT' || e.source === 'Press') {
      const outlets = new Set(srcs.map(s => s.name === 'Press (via GDELT)' ? hostOf(s.url) : s.name).filter(Boolean));
      if (e.source === 'Press') { const o = [...outlets]; return o.length > 2 ? `${o.slice(0, 2).join(', ')} +${o.length - 2}` : o.join(', ') || t('sources'); }
      return `GDELT · ${t('outlets', outlets.size || 1)}`;
    }
    const names = [...new Set(srcs.map(s => s.name))];
    return names.length > 1 ? names.join(' + ') : e.source;
  }

  function fmtDate(iso) {
    try { return new Intl.DateTimeFormat(state.lang === 'fr' ? 'fr-FR' : 'en-GB', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso)); }
    catch (e) { return iso; }
  }
  function fmtUTC(iso) { return new Date(iso).toISOString().slice(0, 16).replace('T', ' ') + ' UTC'; }
  function ago(iso) {
    const diff = Math.min(0, (Date.parse(iso) - Date.now()) / 1000);
    const rtf = new Intl.RelativeTimeFormat(state.lang, { numeric: 'auto', style: 'short' });
    const a = Math.abs(diff);
    if (a < 3600) return rtf.format(Math.round(diff / 60), 'minute');
    if (a < 86400) return rtf.format(Math.round(diff / 3600), 'hour');
    return rtf.format(Math.round(diff / 86400), 'day');
  }
  function haversine(la1, lo1, la2, lo2) {
    const r = 6371, p1 = la1 * Math.PI / 180, p2 = la2 * Math.PI / 180;
    const dp = p2 - p1, dl = (lo2 - lo1) * Math.PI / 180;
    const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
    return 2 * r * Math.asin(Math.sqrt(a));
  }
  function toast(msg, ms = 2800) {
    const el = $('#toast'); el.textContent = msg; el.hidden = false;
    clearTimeout(toast._t); if (ms) toast._t = setTimeout(() => { el.hidden = true; }, ms);
  }

  /* ------------------------------------------------------------------ sites */
  function allSites() {
    const cfg = ((D && D.sites) || []).map((s, i) => ({ ...s, origin: 'config', key: 'c' + i }));
    const loc = state.localSites.map((s, i) => ({ ...s, origin: 'local', key: 'l' + i }));
    return cfg.concat(loc);
  }
  function computeProximity() {
    const sites = allSites();
    EVENTS.forEach(e => {
      e._t = Math.min(Date.parse(e.date), Date.now());
      e._near = sites.map(s => ({ site: s, d: haversine(s.lat, s.lon, e.lat, e.lon) }))
        .filter(x => x.d <= (x.site.radius_km || 50)).sort((a, b) => a.d - b.d);
    });
  }

  /* ------------------------------------------------------------------ carte */
  const map = L.map('map', { zoomControl: false, worldCopyJump: true, minZoom: 2, maxZoom: 16 }).setView([28, 12], 3);
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  const OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
  const OFM_ATTR = '<a href="https://openfreemap.org">OpenFreeMap</a> ' + OSM_ATTR;
  let baseLayer = null;

  // Fond neutre : pays dessinés à partir de Natural Earth, fonctionne sans Internet
  const landLayer = L.geoJSON(COUNTRIES, { interactive: false, style: () => landStyle() });
  function landStyle() {
    return { fillColor: cssVar('--land'), fillOpacity: 1, color: cssVar('--land-line'), weight: 0.6 };
  }
  map.createPane('labels'); map.getPane('labels').style.zIndex = 450; map.getPane('labels').style.pointerEvents = 'none';
  const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/';
  const ESRI_ATTR = 'Tiles &copy; Esri — Esri, HERE, Garmin, ' + OSM_ATTR;
  let labelLayer = null;
  function setBasemap() {
    [baseLayer, labelLayer].forEach(l => { if (l) map.removeLayer(l); });
    baseLayer = labelLayer = null;
    map.removeLayer(landLayer);
    const mode = state.basemap;
    if (mode === 'vector' && window.maplibregl && L.maplibreGL && maplibregl.supported && maplibregl.supported()) {
      try {
        baseLayer = L.maplibreGL({ style: `https://tiles.openfreemap.org/styles/${state.theme === 'dark' ? 'dark' : 'positron'}`, attribution: OFM_ATTR, interactive: false });
        baseLayer.addTo(map);
        const gl = baseLayer.getMaplibreMap && baseLayer.getMaplibreMap();
        if (gl) gl.on('error', () => fallbackBasemap());
        return;
      } catch (e) { /* repli ci-dessous */ }
    }
    if (mode === 'esri' || mode === 'vector') {
      const v = state.theme === 'dark' ? 'Dark' : 'Light';
      baseLayer = L.tileLayer(`${ESRI}World_${v}_Gray_Base/MapServer/tile/{z}/{y}/{x}`, { attribution: ESRI_ATTR, maxZoom: 16 });
      labelLayer = L.tileLayer(`${ESRI}World_${v}_Gray_Reference/MapServer/tile/{z}/{y}/{x}`, { pane: 'labels', maxZoom: 16 });
      let ok = 0, ko = 0;
      baseLayer.on('tileload', () => { ok++; });
      baseLayer.on('tileerror', () => { ko++; if (ko >= 6 && ok === 0) fallbackBasemap(true); });
      baseLayer.addTo(map); labelLayer.addTo(map);
      return;
    }
    landLayer.setStyle(landStyle()); landLayer.addTo(map); landLayer.bringToBack();
  }
  function fallbackBasemap(toPlain) {
    if (fallbackBasemap.done) return;
    fallbackBasemap.done = true;
    state.basemap = toPlain || state.basemap === 'esri' ? 'plain' : 'esri';
    $('#basemap').value = state.basemap; setBasemap();
  }

  const riskLayer = L.geoJSON(COUNTRIES, {
    style: f => countryStyle(f.properties.iso2),
    onEachFeature: (f, layer) => {
      layer.on('click', ev => { if (state.picking) return; L.DomEvent.stopPropagation(ev); openCountry(f.properties.iso2); });
      layer.on('mouseover', () => { if (!state.picking) layer.setStyle({ weight: 1.6, color: cssVar('--ink-2') }); });
      layer.on('mouseout', () => riskLayer.resetStyle(layer));
      layer.bindTooltip(() => {
        const r = RISK[f.properties.iso2];
        return `<strong>${esc(countryName(f.properties.iso2))}</strong><br>${r ? `${t('risk_level')} : ${r.level} · ${esc(riskLabel(r.level))}` : t('no_data')}`;
      }, { sticky: true, className: 'vs-tip', direction: 'top', offset: [0, -8] });
    }
  });
  function countryStyle(iso) {
    const r = RISK[iso];
    return { fillColor: riskColor(r ? r.level : 0), fillOpacity: r ? (state.theme === 'dark' ? 0.38 : 0.42) : 0.04,
      color: state.theme === 'dark' ? '#3A4A5B' : '#FFFFFF', weight: 0.7 };
  }

  const cluster = L.markerClusterGroup({
    showCoverageOnHover: false, maxClusterRadius: 42, disableClusteringAtZoom: 9, spiderfyOnMaxZoom: true,
    iconCreateFunction: c => {
      const max = Math.max(...c.getAllChildMarkers().map(m => m.options.sev || 1));
      return L.divIcon({ className: '', html: `<div class="cl" style="background:${sevColor(max)}">${c.getChildCount()}</div>`, iconSize: [36, 36] });
    }
  });
  const markers = {};
  const sitesLayer = L.layerGroup();

  function markerIcon(e, selected) {
    const s = e.severity, size = s === 4 ? 32 : 26;
    return L.divIcon({ className: '', iconSize: [size, size],
      html: `<div class="mk s${s}${isAuto(e) ? ' auto' : ''}${selected ? ' sel' : ''}" style="background:${sevColor(s)}">${icon(cat(e.category).icon)}</div>` });
  }

  /* ------------------------------------------------------------------ filtrage */
  function windowBounds() {
    if (state.range) return [Date.parse(state.range.from + 'T00:00:00'), Date.parse(state.range.to + 'T23:59:59')];
    return [state.hours === 'all' ? -Infinity : Date.now() - state.hours * 3600e3, Infinity];
  }
  const inWindow = e => { const [a, b] = windowBounds(); return e._t >= a && e._t <= b; };
  function periodLabel() {
    if (state.range) return `${fmtDay(state.range.from)} → ${fmtDay(state.range.to)}`;
    return t('period_lbl')[state.hours] || state.hours;
  }
  const fmtDay = d => new Date(d + 'T12:00:00').toLocaleDateString(state.lang === 'fr' ? 'fr-FR' : 'en-GB');
  /* Alerte « en cours » (72 h) : critique ; élevée et fiable ; catastrophe active ; recoupée ;
     évolutive ; ou proche d'un de vos sites. Les détections isolées de confiance faible sont exclues. */
  function isOngoing(e) {
    if (Date.now() - e._t > 72 * 3600e3) return false;
    const reliable = e.confidence !== 'low';
    const evolving = e.start && Date.parse(e.date) - Date.parse(e.start) > 6 * 3600e3;
    return e.severity >= 4 || (e.severity >= 3 && reliable) ||
      (e.source === 'GDACS' && e.severity >= 3) || (e.source === 'NASA EONET' && e.severity >= 2) ||
      ((e.tags || []).includes('multi-source') && e.severity >= 2) || (evolving && e.severity >= 2 && reliable) ||
      (e._near.length > 0 && e.severity >= 2 && reliable);
  }
  function crisisLevel(evs) {
    if (evs.some(e => e.severity >= 4) || evs.length >= 5) return 'major';
    return evs.length >= 2 ? 'crisis' : 'alert';
  }
  const baseFilter = e => (!state.onlyOngoing || isOngoing(e)) && inWindow(e) && state.cats.has(e.category) && !(state.hideAuto && isAuto(e)) && !(state.onlySites && !e._near.length);
  const visible = () => EVENTS.filter(e => baseFilter(e) && state.sev[e.severity]);
  const sorted = list => list.slice().sort(state.sort === 'severity'
    ? (a, b) => b.severity - a.severity || b._t - a._t
    : (a, b) => b._t - a._t || b.severity - a.severity);

  /* ------------------------------------------------------------------ rendu */
  function renderAll() {
    const list = visible();
    renderSevSummary(); renderFilters(); renderAlerts(list); renderMap(list);
    renderCountries(); renderNews(); renderSites(); renderOngoing(); renderLegend(); renderHealth(); renderTabs();
    $('#btn-analytics').innerHTML = icon('chart-column') + `<span>${esc(t('analytics'))}</span>`;
    $('#btn-export').innerHTML = icon('printer') + esc(t('export_pdf'));
    if (state.analytics) renderAnalytics();
  }

  function renderOngoing() {
    const on = EVENTS.filter(e => isOngoing(e) && !(state.hideAuto && isAuto(e)));
    const by = {};
    on.forEach(e => { const k = e.country || '_sea'; (by[k] = by[k] || []).push(e); });
    const crises = Object.entries(by).map(([iso, evs]) => ({ iso, evs: evs.sort((a, b) => b.severity - a.severity || b._t - a._t),
      max: Math.max(...evs.map(e => e.severity)), risk: (RISK[iso] || {}).level || 0 }))
      .sort((a, b) => ({ major: 2, crisis: 1, alert: 0 }[crisisLevel(b.evs)] - { major: 2, crisis: 1, alert: 0 }[crisisLevel(a.evs)]) || b.max - a.max || b.risk - a.risk || b.evs.length - a.evs.length);
    $('#ongoing-count').textContent = t('n_crises', crises.length, on.length);
    $('#only-ongoing').checked = state.onlyOngoing;
    $('#ongoing-list').innerHTML = crises.length ? crises.map(c => `<li class="crisis">
      <div class="c-head" data-country="${c.iso === '_sea' ? '' : c.iso}"><span class="lvl" style="background:${sevColor(c.max)}">${c.evs.length}</span>
        <div><div class="n">${esc(c.iso === '_sea' ? t('at_sea') : countryName(c.iso))} <span class="crisis-tag ${crisisLevel(c.evs)}">${t('crisis_' + crisisLevel(c.evs))}</span></div><div class="s">${c.risk ? `${t('risk_level')} ${c.risk} · ${esc(riskLabel(c.risk))}` : ''}</div></div></div>
      <ul class="mini-list">${c.evs.slice(0, 5).map(e => `<li data-event="${esc(e.id)}"><span class="dot" style="background:${sevColor(e.severity)}"></span><span class="t">${esc(e.title)}</span><span class="w">${esc(ago(e.date))}</span></li>`).join('')}</ul>
      ${c.evs.length > 5 ? `<div class="hint">+ ${c.evs.length - 5}</div>` : ''}</li>`).join('') : `<li class="empty">${t('no_ongoing')}</li>`;
  }

  function renderTabs() {
    $$('.tabs button').forEach(b => {
      b.setAttribute('aria-selected', String(b.dataset.tab === state.tab));
      const ic = { alerts: 'siren', ongoing: 'radio-tower', countries: 'globe', news: 'newspaper', sites: 'building-2' }[b.dataset.tab];
      let label = icon(ic, 20) + `<span>${esc(t('tab_' + b.dataset.tab))}</span>`;
      const n = b.dataset.tab === 'sites' ? EVENTS.filter(e => inWindow(e) && e._near.length && e.severity >= 2).length
        : b.dataset.tab === 'ongoing' ? EVENTS.filter(isOngoing).length : 0;
      if (n) label += `<span class="badge">${n}</span>`;
      b.innerHTML = label;
    });
    $$('.tab-body').forEach(s => { s.hidden = s.dataset.body !== state.tab; });
  }

  function renderSevSummary() {
    const base = EVENTS.filter(baseFilter);
    $('#sev-summary').innerHTML = [4, 3, 2, 1].map(s => {
      const n = base.filter(e => e.severity === s).length;
      return `<button class="sev-tile" data-sev="${s}" aria-pressed="${!!state.sev[s]}"><div class="n">${n}</div><div class="l"><i style="background:${sevColor(s)}"></i>${esc(sevLabel(s))}</div></button>`;
    }).join('');
  }

  function renderFilters() {
    const counts = {};
    EVENTS.filter(inWindow).forEach(e => { counts[e.category] = (counts[e.category] || 0) + 1; });
    const groups = {};
    Object.entries(TAX.categories).forEach(([k, c]) => { (groups[c.group] = groups[c.group] || []).push(k); });
    $('#filter-groups').innerHTML = Object.entries(TAX.groups).map(([g, gl]) => {
      const cats = (groups[g] || []).filter(k => counts[k]);
      if (!cats.length) return '';
      const chips = cats.map(k => `<button class="chip" data-cat="${k}" aria-pressed="${state.cats.has(k)}">${icon(cat(k).icon)}${esc(catLabel(k))} <span class="c">${counts[k]}</span></button>`).join('');
      return `<div><div class="fgroup-title"><span>${esc(gl[state.lang])}</span><span><button data-gall="${g}">${t('all')}</button> · <button data-gnone="${g}">${t('none')}</button></span></div><div class="chips">${chips}</div></div>`;
    }).join('');
    const total = Object.keys(TAX.categories).length;
    $('#filter-count').textContent = state.cats.size < total ? `${state.cats.size}/${total}` : '';
    $('#only-sites').checked = state.onlySites; $('#hide-auto').checked = state.hideAuto;
  }

  function nearLabel(e) {
    if (!e._near.length) return '';
    const n = e._near[0];
    return `<span class="near">◉ ${esc(n.site.name)} · ${Math.round(n.d)} ${t('km')}</span>`;
  }

  function renderAlerts(list) {
    const all = sorted(list);
    $('#alerts-count').textContent = t('n_alerts', all.length);
    if (!all.length) { $('#alert-list').innerHTML = `<li class="empty">${t('no_alerts')}</li>`; return; }
    const shown = all.slice(0, state.limit);
    $('#alert-list').innerHTML = shown.map(e => {
      const place = e.place || countryName(e.country) || t('at_sea');
      const desc = describe(e);
      return `<li class="alert${state.selected === e.id ? ' active' : ''}" data-id="${esc(e.id)}">
        <span class="stripe" style="background:${sevColor(e.severity)}"></span>
        <span class="ico" style="background:${sevColor(e.severity)}">${icon(cat(e.category).icon)}</span>
        <div><div class="t">${esc(e.title)}</div>
          ${desc ? `<div class="d">${esc(desc)}</div>` : ''}
          <div class="m"><span>${esc(catLabel(e.category))}</span><span>${esc(ago(e.date))}</span><span>${esc(place)}</span>${nearLabel(e)}</div>
          <div class="m src"><span class="tag${isAuto(e) ? ' auto' : ''}">${icon('newspaper', 11)} ${esc(sourceLabel(e))}</span>${isAuto(e) ? `<span class="tag auto">auto</span>` : ''}</div></div></li>`;
    }).join('') + (all.length > shown.length ? `<li><button class="more" id="more">${t('show_more', Math.min(60, all.length - shown.length))}</button></li>` : '');
  }

  function renderMap(list) {
    cluster.clearLayers();
    Object.keys(markers).forEach(k => delete markers[k]);
    const ms = list.map(e => {
      const m = L.marker([e.lat, e.lon], { icon: markerIcon(e, e.id === state.selected), sev: e.severity, riseOnHover: true, zIndexOffset: e.severity * 100 });
      m.bindTooltip(`<strong>${esc(e.title)}</strong><br>${esc(sevLabel(e.severity))} · ${esc(ago(e.date))} · ${esc(sourceLabel(e))}`, { className: 'vs-tip', direction: 'top', offset: [0, -14] });
      m.on('click', () => openEvent(e.id, false));
      markers[e.id] = m;
      return m;
    });
    cluster.addLayers(ms);
    renderSiteLayer();
  }

  function renderSiteLayer() {
    sitesLayer.clearLayers();
    allSites().forEach(s => {
      L.circle([s.lat, s.lon], { radius: (s.radius_km || 50) * 1000, color: cssVar('--accent'), weight: 1.2, dashArray: '4 4', fillOpacity: 0.05, interactive: false }).addTo(sitesLayer);
      L.marker([s.lat, s.lon], { icon: L.divIcon({ className: '', iconSize: [22, 22], html: `<div class="site-mk">${icon('building-2')}</div>` }), zIndexOffset: 1000 })
        .bindTooltip(`<strong>${esc(s.name)}</strong><br>${t('radius')} ${s.radius_km || 50} ${t('km')}`, { className: 'vs-tip', direction: 'top', offset: [0, -12] })
        .addTo(sitesLayer);
    });
  }

  function renderCountries() {
    const q = state.countryFilter.toLowerCase();
    const rows = Object.entries(RISK)
      .map(([iso, r]) => ({ iso, r, name: countryName(iso) || iso }))
      .filter(x => !q || x.name.toLowerCase().includes(q))
      .sort((a, b) => b.r.level - a.r.level || b.r.score - a.r.score || a.name.localeCompare(b.name));
    $('#country-list').innerHTML = rows.length ? rows.map(x => {
      const c = x.r.counts || {};
      const adv = Object.entries(x.r.advisories || {}).map(([src, a]) => `${esc(src.split(' ')[0])} ${a.level}/${a.scale || 4}`).join(' · ');
      const n = (c.security || 0) + (c.hazards || 0);
      return `<li class="country-row" data-iso="${x.iso}"><span class="lvl" style="background:${riskColor(x.r.level)}">${x.r.level}</span>
        <div><div class="n">${esc(x.name)}</div><div class="s">${esc(riskLabel(x.r.level))}${adv ? ` · ${adv}` : ''}</div></div>
        <div class="s">${n ? esc(t('n_alerts', n)) : ''}</div></li>`;
    }).join('') : `<li class="empty">${t('no_data')}</li>`;
  }

  function renderNews() {
    const q = state.newsFilter.toLowerCase();
    const items = NEWS.filter(n => !q || (n.title + ' ' + n.source + ' ' + countryName(n.country)).toLowerCase().includes(q)).slice(0, 200);
    $('#news-list').innerHTML = items.length ? items.map(n =>
      `<li class="news-item"><a href="${esc(n.url)}" target="_blank" rel="noopener"><div class="t">${esc(n.title)}</div>
        <div class="m">${n.severity ? `<i class="dot" style="background:${sevColor(n.severity)}"></i>` : ''}${esc(n.source)} · ${esc(ago(n.date))}${n.country ? ' · ' + esc(countryName(n.country)) : ''}${n.category ? ' · ' + esc(catLabel(n.category)) : ''}${n.lang ? ' · ' + esc(n.lang.toUpperCase()) : ''}</div></a></li>`
    ).join('') : `<li class="empty">${t('no_news')}</li>`;
  }

  function renderSites() {
    $('#btn-add-site').innerHTML = icon('plus') + esc(t('add_site'));
    $('#btn-export-sites').innerHTML = icon('download') + esc(t('export_sites'));
    const win = EVENTS.filter(inWindow);
    $('#site-list').innerHTML = allSites().map(s => {
      const hits = win.filter(e => e._near.some(n => n.site.key === s.key));
      const max = hits.length ? Math.max(...hits.map(e => e.severity)) : 0;
      return `<li class="site-row" data-lat="${s.lat}" data-lon="${s.lon}">
        <div class="h"><span class="n">${esc(s.name)}</span>${s.origin === 'local' ? `<button class="del" data-del="${s.key}" title="${t('delete')}">${icon('trash-2')}</button>` : ''}</div>
        <div class="s">${t('radius')} ${s.radius_km || 50} ${t('km')} · ${s.origin === 'config' ? t('site_config') : t('site_local')}</div>
        <div class="hits" style="color:${max ? sevColor(max) : 'var(--muted)'}">${t('hits', hits.length)}</div></li>`;
    }).join('');
  }

  function renderLegend() {
    $('#legend').innerHTML = `
      <div><div class="card-title">${t('legend_sev')}</div><div class="row">${[1, 2, 3, 4].map(s => `<span class="k"><i class="sw" style="background:${sevColor(s)}"></i>${esc(sevLabel(s))}</span>`).join('')}</div></div>
      <div><div class="card-title">${t('legend_risk')}</div><div class="row">${[1, 2, 3, 4, 5].map(l => `<span class="k"><i class="sq" style="background:${riskColor(l)}"></i>${esc(riskLabel(l))}</span>`).join('')}</div></div>
      <div class="legend-note">${t('legend_auto')}</div>`;
  }

  function renderHealth() {
    const el = $('#health');
    if (!D) { el.hidden = true; return; }
    const active = STATUS.filter(s => !s.paused);
    const ok = active.filter(s => s.ok).length;
    const ageH = (Date.now() - Date.parse(D.generated)) / 3600e3;
    el.className = 'health' + (ok < active.length ? ' warn' : '') + (ageH > 3 || ok === 0 ? ' bad' : '');
    el.innerHTML = `<span class="dot"></span><span>${t('sources_ok', ok, STATUS.length)}</span><span class="lbl">· ${ageH > 3 ? t('stale') : t('updated')} ${esc(ago(D.generated))}</span>`;
  }

  /* ------------------------------------------------------------------ fiches */
  function openDrawer(html, kind, id) { state.drawer = { kind, id }; $('#drawer-body').innerHTML = html; $('#drawer').hidden = false; $('#drawer').scrollTop = 0; }
  function closeDrawer() {
    $('#drawer').hidden = true; state.drawer = null;
    if (state.selected && markers[state.selected]) {
      const e = EVENTS.find(x => x.id === state.selected);
      if (e) markers[state.selected].setIcon(markerIcon(e, false));
    }
    state.selected = null;
    $$('.alert.active').forEach(el => el.classList.remove('active'));
  }

  function openEvent(id, fly = true) {
    const e = EVENTS.find(x => x.id === id);
    if (!e) return;
    closeAnalytics();
    if (state.selected && markers[state.selected]) {
      const prev = EVENTS.find(x => x.id === state.selected);
      if (prev) markers[state.selected].setIcon(markerIcon(prev, false));
    }
    state.selected = id;
    $$('.alert').forEach(el => el.classList.toggle('active', el.dataset.id === id));
    const m = markers[id];
    if (fly) map.flyTo([e.lat, e.lon], Math.max(map.getZoom(), e.precision === 'country' ? 5 : 7), { duration: 0.8 });
    if (m) {
      const show = () => { if (markers[id]) markers[id].setIcon(markerIcon(e, true)); };
      if (fly) cluster.zoomToShowLayer(m, show); else show();
    }
    const r = RISK[e.country];
    const desc = describe(e);
    const srcs = (e.sources || []).map(s => {
      const outlet = s.name === 'Press (via GDELT)' ? hostOf(s.url) : s.name;
      return `<li><strong>${esc(outlet)}</strong>${s.title ? ` — ${esc(s.title)}` : ''}<br><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(shortUrl(s.url))} ${icon('external-link', 11)}</a></li>`;
    }).join('');
    const near = e._near.length ? `<div class="d-sec"><h3>${t('near_sites')}</h3><ul class="mini-list">${e._near.map(n => `<li><span class="dot" style="background:var(--accent)"></span><span class="t">${esc(n.site.name)}</span><span class="w">${Math.round(n.d)} ${t('km')}</span></li>`).join('')}</ul></div>` : '';
    openDrawer(`
      <div class="d-head">
        <div class="d-kicker"><span class="pill" style="background:${sevColor(e.severity)}">${esc(sevLabel(e.severity))}</span>
          <span style="display:inline-flex;gap:5px;align-items:center">${icon(cat(e.category).icon, 14)}${esc(catLabel(e.category))}</span></div>
        <h2 class="d-title">${esc(e.title)}</h2>
        ${desc ? `<p class="d-desc">${esc(desc)}</p>` : ''}
        <div class="d-source">${icon('newspaper', 14)}<span><strong>${t('source_lbl')} :</strong> ${esc(sourceLabel(e))}</span></div>
        ${isAuto(e) ? `<div class="notice">${t('auto_notice')}</div>` : ''}
        ${(e.tags || []).includes('multi-source') ? `<div class="notice" style="border-style:solid">✓ ${t('multi_source')}</div>` : ''}
      </div>
      <div class="d-sec"><dl class="kv">
        <dt>${t('date')}</dt><dd>${esc(fmtDate(e.date))} <span style="color:var(--muted)">(${esc(ago(e.date))})</span><br><span class="mono">${esc(fmtUTC(e.date))}</span></dd>
        ${e.start && e.start !== e.date ? `<dt>${t('start')}</dt><dd>${esc(fmtDate(e.start))}</dd>` : ''}
        <dt>${t('place')}</dt><dd>${esc(e.place || '—')}</dd>
        <dt>${t('country')}</dt><dd>${e.country ? `<a href="#" data-country="${e.country}">${esc(countryName(e.country))}</a>${r ? ` <span class="pill" style="background:${riskColor(r.level)}">${r.level} · ${esc(riskLabel(r.level))}</span>` : ''}` : esc(t('at_sea'))}</dd>
        <dt>${t('precision')}</dt><dd>${esc(t('prec')[e.precision] || e.precision)}</dd>
        <dt>${t('coords')}</dt><dd class="mono">${e.lat.toFixed(3)}, ${e.lon.toFixed(3)}</dd>
        <dt>${t('confidence')}</dt><dd>${esc(t('conf')[e.confidence] || e.confidence)}</dd>
      </dl></div>
      ${near}
      <div class="d-sec"><h3>${t('sources')} (${(e.sources || []).length})</h3><ul class="src-list">${srcs}</ul>
        <div class="site-actions"><button class="btn" data-zoom="${esc(e.id)}">${icon('locate-fixed')}${t('zoom')}</button>
        ${e.country ? `<a class="btn" href="report.html#${e.country}" target="_blank" rel="noopener">${icon('file-text')}${t('country_report')}</a>` : ''}</div></div>`, 'event', id);
  }

  function reopenDrawer() {
    const d = state.drawer; if (!d || $('#drawer').hidden) return;
    if (d.kind === 'event') openEvent(d.id, false);
    else if (d.kind === 'country') openCountry(d.id, false);
    else if (d.kind === 'health') openHealth();
  }
  function shortUrl(u) { try { const x = new URL(u); return x.hostname.replace(/^www\./, '') + (x.pathname.length > 1 ? x.pathname.slice(0, 32) + (x.pathname.length > 32 ? '…' : '') : ''); } catch (e) { return u; } }

  function openCountry(iso, fly = true) {
    closeAnalytics();
    const r = RISK[iso];
    const name = countryName(iso) || iso;
    const lvl = r ? r.level : 0;
    const desc = r ? (TAX.risk_levels[lvl] || {})['desc_' + state.lang] || '' : t('no_data');
    const recent = EVENTS.filter(e => e.country === iso && e._t >= Date.now() - 30 * 86400e3)
      .sort((a, b) => b.severity - a.severity || b._t - a._t).slice(0, 10);
    const stats = ((D && D.country_stats) || {})[iso] || {};
    const counts = ['24h', '72h', '7d', '90d'].map(w => `<div class="stat"><div class="n">${(stats[w] || {}).total || 0}</div><div class="l">${w.replace('d', state.lang === 'fr' ? ' j' : ' d').replace('h', ' h')}</div></div>`).join('');
    const bars = r ? [['comp_adv', r.components.advisories], ['comp_sec', r.components.security], ['comp_haz', r.components.hazards]]
      .map(([k, v]) => `<div class="bar"><span>${t(k)}</span><span class="track"><span class="fill" style="width:${v == null ? 0 : Math.round(v * 100)}%"></span></span><span class="v">${v == null ? '—' : Math.round(v * 100)}</span></div>`).join('') : '';
    const advs = r && Object.keys(r.advisories || {}).length ? Object.entries(r.advisories).map(([src, a]) =>
      `<li><span class="dot" style="background:${riskColor(Math.min(5, a.level + 1))}"></span><span><strong>${esc(src)}</strong> · ${t('level')} ${a.level} ${t('of')} ${a.scale || 4}<br><span style="color:var(--muted)">${esc(a.label || '')}</span></span><a class="w" href="${esc(a.url)}" target="_blank" rel="noopener">↗</a></li>`).join('') : '';
    const f = COUNTRIES.features.find(x => x.properties.iso2 === iso);
    if (f && fly) map.flyToBounds(L.geoJSON(f).getBounds(), { padding: [40, 40], maxZoom: 6, duration: 0.8 });
    openDrawer(`
      <div class="d-head">
        <div class="d-kicker">${esc((countryProps[iso] || {}).region || '')}</div>
        <h2 class="d-title">${esc(name)}</h2>
        <div class="risk-big"><span class="lvl" style="background:${riskColor(lvl)}">${lvl || '–'}</span>
          <div><div class="name">${r ? esc(riskLabel(lvl)) : t('no_data')}</div><div class="desc">${esc(desc)}</div></div></div>
        <a class="btn primary" href="report.html#${iso}" target="_blank" rel="noopener">${icon('file-text')}${t('country_report')}</a>
        ${r && r.basis === 'analyst' ? `<div class="notice" style="border-style:solid">${t('analyst')}</div>` : ''}
        ${r && r.data_quality === 'events-only' ? `<div class="notice">${t('events_only')}</div>` : ''}
      </div>
      <div class="d-sec"><h3>${t('incidents')}</h3><div class="stats">${counts}</div></div>
      ${r ? `<div class="d-sec"><h3>${t('components')}</h3>${bars}</div>` : ''}
      ${advs ? `<div class="d-sec"><h3>${t('advisories')}</h3><ul class="mini-list">${advs}</ul></div>` : ''}
      <div class="d-sec"><h3>${t('recent')}</h3>${recent.length ? `<ul class="mini-list">${recent.map(e => `<li data-event="${esc(e.id)}"><span class="dot" style="background:${sevColor(e.severity)}"></span><span class="t">${esc(e.title)}</span><span class="w">${esc(ago(e.date))}</span></li>`).join('')}</ul>` : `<div class="hint">${t('no_recent')}</div>`}</div>
      <div class="d-sec"><div class="hint">${t('risk_notice')}</div></div>`, 'country', iso);
  }

  function openHealth() {
    const rows = STATUS.map(s => `<li><span class="dot" style="background:${s.paused ? 'var(--muted)' : s.ok ? 'var(--risk1)' : 'var(--sev4)'}"></span>
      <span><strong>${esc(s.name)}</strong> <span style="color:var(--muted)">· ${esc(s.license || '')}</span><br>
      <span style="color:var(--muted)">${s.paused ? t('paused') : s.ok ? `${s.count} ${t('items')}` : esc(s.error || t('error'))}${s.last_success ? ` · ${t('last_success')} ${esc(ago(s.last_success))}` : ''}</span></span></li>`).join('');
    openDrawer(`<div class="d-head"><h2 class="d-title">${t('source_status')}</h2>
      <div class="hint">${t('updated')} ${esc(fmtDate(D.generated))} · v${esc(D.version)}</div></div>
      <div class="d-sec"><ul class="mini-list" style="gap:10px">${rows}</ul></div>`, 'health');
  }

  /* ------------------------------------------------------------------ analyses */
  const charts = [];
  function closeAnalytics() {
    if (!state.analytics) return;
    state.analytics = false; $('#analytics').hidden = true; $('#btn-analytics').classList.remove('on');
    charts.splice(0).forEach(c => c.destroy());
  }
  function analyticsFilter(e) {
    if (!inWindow(e)) return false;
    if (!state.aAuto && isAuto(e)) return false;
    if (state.aCountry && e.country !== state.aCountry) return false;
    if (state.aGroup) {
      const [k, v] = state.aGroup.split(':');
      if (k === 'g' && cat(e.category).group !== v) return false;
      if (k === 'c' && e.category !== v) return false;
    }
    if (e.severity < state.aSev) return false;
    if (state.aSource && e.source !== state.aSource) return false;
    return true;
  }
  function renderAnalytics() {
    const el = $('#analytics');
    charts.splice(0).forEach(c => c.destroy());
    const win = EVENTS.filter(analyticsFilter);
    const inPeriod = EVENTS.filter(inWindow);
    const countries = [...new Set(inPeriod.map(e => e.country).filter(Boolean))].sort((a, b) => countryName(a).localeCompare(countryName(b)));
    const sources = [...new Set(inPeriod.map(e => e.source))].sort();
    const grpOpts = Object.entries(TAX.groups).map(([g, gl]) => `<optgroup label="${esc(gl[state.lang])}"><option value="g:${g}">${esc(gl[state.lang])} — ${t('all')}</option>${
      Object.entries(TAX.categories).filter(([, c]) => c.group === g).map(([k]) => `<option value="c:${k}">${esc(catLabel(k))}</option>`).join('')}</optgroup>`).join('');
    const rC = state.aCountry ? RISK[state.aCountry] : null;
    const kpis = [
      [t('k_events'), win.length], [t('k_critical'), win.filter(e => e.severity >= 3).length],
      state.aCountry ? [t('risk_level'), rC ? `${rC.level} · ${riskLabel(rC.level)}` : '—'] : [t('k_countries'), Object.values(RISK).filter(r => r.level >= 4).length],
      [t('k_multi'), win.filter(e => (e.tags || []).includes('multi-source')).length], [t('k_auto'), win.length ? Math.round(100 * win.filter(isAuto).length / win.length) + ' %' : '—']
    ];
    el.innerHTML = `<div class="a-head"><div><h2>${t('a_title')}${state.aCountry ? ' — ' + esc(countryName(state.aCountry)) : ''}</h2><div class="hint">${esc(t('a_period', periodLabel()))}</div></div>
      <button class="icon-btn" id="a-close" aria-label="${t('close')}">${icon('x')}</button></div>
      <div class="a-filters">
        <label>${t('country')}<select id="af-country"><option value="">${t('all_countries')}</option>${countries.map(c => `<option value="${c}">${esc(countryName(c))}</option>`).join('')}</select></label>
        <label>${t('risk_cat')}<select id="af-group"><option value="">${t('all')}</option>${grpOpts}</select></label>
        <label>${t('min_sev')}<select id="af-sev">${[1, 2, 3, 4].map(v => `<option value="${v}">${v === 1 ? t('all') : '≥ ' + esc(sevLabel(v))}</option>`).join('')}</select></label>
        <label>${t('source_lbl')}<select id="af-source"><option value="">${t('all')}</option>${sources.map(x => `<option>${esc(x)}</option>`).join('')}</select></label>
        <label class="switch"><input type="checkbox" id="af-auto"${state.aAuto ? ' checked' : ''}><span>${t('incl_auto')}</span></label>
        ${state.aCountry ? `<a class="btn small" href="report.html#${state.aCountry}" target="_blank" rel="noopener">${icon('file-text')}${t('country_report')}</a>` : ''}
      </div>
      <div class="kpis">${kpis.map(([l, v]) => `<div class="kpi"><div class="n">${esc(v)}</div><div class="l">${esc(l)}</div></div>`).join('')}</div>
      <div class="a-grid">
        <div class="a-card wide"><h3>${t('c_daily')}</h3><div class="cv"><canvas id="ch-daily"></canvas></div></div>
        <div class="a-card"><h3>${t('c_cats')}</h3><div class="cv"><canvas id="ch-cats"></canvas></div></div>
        <div class="a-card"><h3>${state.aCountry ? t('c_places') : t('c_top')}</h3><div class="cv"><canvas id="ch-top"></canvas></div></div>
        <div class="a-card"><h3>${t('c_sev')}</h3><div class="cv"><canvas id="ch-sev"></canvas></div></div>
        <div class="a-card"><h3>${t('c_src')}</h3><div class="cv"><canvas id="ch-src"></canvas></div></div>
        ${state.aCountry ? '' : `<div class="a-card"><h3>${t('c_risk')}</h3><div class="cv"><canvas id="ch-risk"></canvas></div></div>`}
      </div>`;
    $('#af-country').value = state.aCountry; $('#af-group').value = state.aGroup; $('#af-sev').value = String(state.aSev); $('#af-source').value = state.aSource;
    el.hidden = false;
    if (!window.Chart) return;
    const ink = cssVar('--ink-2'), grid = cssVar('--line');
    Chart.defaults.font.family = cssVar('--font') || 'system-ui';
    Chart.defaults.color = ink;
    const base = { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { boxWidth: 10, boxHeight: 10 } } } };
    const axes = { x: { grid: { color: grid } }, y: { grid: { color: grid }, beginAtZero: true, ticks: { precision: 0 } } };
    // série temporelle calculée sur la période choisie (par jour, ou par semaine au-delà de 120 jours)
    let [a0, a1] = windowBounds();
    a1 = Math.min(a1, Date.now());
    if (!isFinite(a0)) a0 = win.length ? Math.min(...win.map(e => e._t)) : a1 - 30 * 864e5;
    const step = (a1 - a0) > 120 * 864e5 ? 7 * 864e5 : 864e5;
    const nb = Math.max(1, Math.ceil((a1 - a0) / step));
    const labels = Array.from({ length: nb }, (_, i) => new Date(a0 + i * step).toLocaleDateString(state.lang, { day: 'numeric', month: 'short' }));
    const series = {};
    Object.keys(GROUP_COLORS).forEach(g => { series[g] = new Array(nb).fill(0); });
    win.forEach(e => { const i = Math.min(nb - 1, Math.floor((e._t - a0) / step)); if (i >= 0) series[cat(e.category).group][i]++; });
    charts.push(new Chart($('#ch-daily'), { type: 'line', data: { labels, datasets: Object.entries(series).filter(([, v]) => v.some(Boolean)).map(([g, v]) => ({
      label: (TAX.groups[g] || {})[state.lang] || g, data: v, borderColor: GROUP_COLORS[g], backgroundColor: GROUP_COLORS[g] + '55', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 1.5 })) },
      options: { ...base, interaction: { mode: 'index', intersect: false }, scales: { x: { ...axes.x, ticks: { maxTicksLimit: 12 } }, y: { ...axes.y, stacked: true } } } }));
    const count = f => { const o = {}; win.forEach(e => { const k = f(e); if (k) o[k] = (o[k] || 0) + 1; }); return Object.entries(o).sort((a, b) => b[1] - a[1]); };
    const cats = count(e => e.category);
    charts.push(new Chart($('#ch-cats'), { type: 'doughnut', data: { labels: cats.map(([c]) => catLabel(c)), datasets: [{
      data: cats.map(([, n]) => n), backgroundColor: cats.map(([c], i) => shade(GROUP_COLORS[cat(c).group] || '#888', i)), borderColor: cssVar('--surface'), borderWidth: 2 }] },
      options: { ...base, cutout: '62%', plugins: { legend: { position: 'right', labels: { boxWidth: 10, boxHeight: 10 } } } } }));
    const top = (state.aCountry ? count(e => e.place) : count(e => e.country)).slice(0, 10);
    charts.push(new Chart($('#ch-top'), { type: 'bar', data: { labels: top.map(([i]) => state.aCountry ? i : (countryName(i) || i)), datasets: [{ label: t('incidents'), data: top.map(([, n]) => n),
      backgroundColor: top.map(([i]) => state.aCountry ? cssVar('--accent') : riskColor((RISK[i] || {}).level || 0)), borderRadius: 4 }] },
      options: { ...base, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: axes.y, y: { grid: { display: false } } } } }));
    charts.push(new Chart($('#ch-sev'), { type: 'bar', data: { labels: [1, 2, 3, 4].map(sevLabel), datasets: [{ data: [1, 2, 3, 4].map(v => win.filter(e => e.severity === v).length),
      backgroundColor: [1, 2, 3, 4].map(sevColor), borderRadius: 4 }] }, options: { ...base, plugins: { legend: { display: false } }, scales: axes } }));
    const srcs = count(e => e.source);
    charts.push(new Chart($('#ch-src'), { type: 'bar', data: { labels: srcs.map(([x]) => x), datasets: [{ data: srcs.map(([, n]) => n), backgroundColor: cssVar('--accent'), borderRadius: 4 }] },
      options: { ...base, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: axes.y, y: { grid: { display: false } } } } }));
    if (!state.aCountry) charts.push(new Chart($('#ch-risk'), { type: 'bar', data: { labels: [1, 2, 3, 4, 5].map(riskLabel), datasets: [{ data: [1, 2, 3, 4, 5].map(l => Object.values(RISK).filter(r => r.level === l).length),
      backgroundColor: [1, 2, 3, 4, 5].map(riskColor), borderRadius: 4 }] }, options: { ...base, plugins: { legend: { display: false } }, scales: axes } }));
  }
  function shade(hex, i) {
    const n = parseInt(hex.slice(1), 16); const f = 1 - (i % 4) * 0.16;
    const r = Math.round(((n >> 16) & 255) * f), g = Math.round(((n >> 8) & 255) * f), b = Math.round((n & 255) * f);
    return `rgb(${r},${g},${b})`;
  }

  /* ------------------------------------------------------------------ export PDF de la liste */
  function exportList() {
    const list = sorted(visible());
    const cats = state.cats.size < Object.keys(TAX.categories).length ? [...state.cats].map(catLabel).join(', ') : t('all');
    const sevs = [1, 2, 3, 4].filter(s => state.sev[s]).map(sevLabel).join(', ');
    $('#print-area').innerHTML = `<header class="p-head"><div class="p-brand">${esc((D && D.settings && D.settings.product_name) || 'Angor Intelligence')}</div>
      <h1>${t('print_title')} — ${esc(periodLabel())}</h1>
      <div class="p-meta">${t('print_generated')} ${esc(fmtDate(new Date().toISOString()))} · ${t('n_alerts', list.length)} · ${t('print_filters')} : ${esc(cats)} / ${esc(sevs)}${state.hideAuto ? ' / ' + esc(t('hide_auto')) : ''}</div></header>
      <table class="p-table"><thead><tr><th>${t('legend_sev')}</th><th>${t('date')}</th><th>${t('description')}</th><th>${t('place')}</th><th>${t('sources')}</th></tr></thead><tbody>
      ${list.map(e => `<tr><td><span class="p-sev" style="background:${sevColor(e.severity)}"></span>${esc(sevLabel(e.severity))}</td><td>${esc(fmtUTC(e.date))}</td>
        <td><strong>${esc(e.title)}</strong>${describe(e) ? `<br>${esc(describe(e))}` : ''}<br><em>${esc(catLabel(e.category))}${isAuto(e) ? ' · auto' : ''}</em></td>
        <td>${esc(e.place || '')}${e.country ? `<br>${esc(countryName(e.country))}` : ''}</td><td>${esc(sourceLabel(e))}<br><span class="p-url">${esc(shortUrl(e.url || ''))}</span></td></tr>`).join('')}
      </tbody></table>`;
    document.body.classList.add('printing');
    setTimeout(() => { window.print(); setTimeout(() => document.body.classList.remove('printing'), 500); }, 50);
  }

  /* ------------------------------------------------------------------ recherche */
  function runSearch(q) {
    const box = $('#search-results');
    q = q.trim().toLowerCase();
    if (q.length < 2) { box.hidden = true; return; }
    const cs = COUNTRIES.features.map(f => f.properties)
      .filter(p => (p.name_fr || '').toLowerCase().includes(q) || (p.name_en || '').toLowerCase().includes(q)).slice(0, 5)
      .map(p => `<button data-country="${p.iso2}">${RISK[p.iso2] ? `<span class="pill" style="background:${riskColor(RISK[p.iso2].level)}">${RISK[p.iso2].level}</span>` : ''}${esc(p['name_' + state.lang])}<span class="kind">${t('country')}</span></button>`);
    const es = EVENTS.filter(e => (e.title + ' ' + e.place + ' ' + (e.headline || '')).toLowerCase().includes(q)).slice(0, 8)
      .map(e => `<button data-event="${esc(e.id)}"><span class="pill" style="background:${sevColor(e.severity)}">${e.severity}</span>${esc(e.title)}<span class="kind">${esc(ago(e.date))}</span></button>`);
    box.innerHTML = cs.concat(es).join('') || `<div class="empty">—</div>`;
    box.hidden = false;
  }

  /* ------------------------------------------------------------------ interactions */
  function applyI18n() {
    document.documentElement.lang = state.lang;
    $$('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    $$('[data-i18n-placeholder]').forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); });
    $('#btn-lang').textContent = state.lang === 'fr' ? 'EN' : 'FR';
    $$('#time-seg button[data-h]').forEach(b => { b.textContent = t('period_lbl')[b.dataset.h]; });
  }
  function applyTheme() {
    document.documentElement.dataset.theme = state.theme;
    $('#btn-theme').innerHTML = icon(state.theme === 'dark' ? 'sun-medium' : 'moon');
    setBasemap();
    riskLayer.setStyle(f => countryStyle(f.properties.iso2));
  }
  function persist() {
    store.set('vs-hours', state.hours); store.set('vs-sev', state.sev); store.set('vs-cats', [...state.cats]);
    store.set('vs-hideauto', state.hideAuto); store.set('vs-lang', state.lang); store.set('vs-theme', state.theme); store.set('vs-basemap', state.basemap);
  }
  /* Historique au-delà de 30 jours : archives mensuelles chargées seulement si la période l'exige */
  const loadedMonths = new Set();
  function ensureArchives(done) {
    const months = Object.keys((D && D.archives) || {});
    const [a] = windowBounds();
    const need = months.filter(m => !loadedMonths.has(m) && Date.parse(m + '-01T00:00:00Z') + 31 * 864e5 >= a);
    if (!need.length) return done();
    toast(t('loading_archive'), 0);
    let left = need.length;
    need.forEach(m => {
      const sc = document.createElement('script');
      sc.src = `data/archive/${m}.js`;
      sc.onload = sc.onerror = () => {
        loadedMonths.add(m);
        const known = new Set(EVENTS.map(e => e.id));
        ((window.VS_ARCHIVE || {})[m] || []).forEach(e => { if (!known.has(e.id)) EVENTS.push(e); });
        if (--left === 0) { computeProximity(); $('#toast').hidden = true; done(); }
      };
      document.head.appendChild(sc);
    });
  }
  function refresh() { persist(); state.limit = 60; ensureArchives(renderAll); }

  function bind() {
    $('#search .search-ico').innerHTML = icon('search');
    $('#drawer-close').innerHTML = icon('x');
    $('#btn-panel').innerHTML = icon('list');
    $('#basemap').value = state.basemap;
    const markPeriod = () => {
      $$('#time-seg button[data-h]').forEach(x => x.setAttribute('aria-pressed', String(!state.range && String(state.hours) === x.dataset.h)));
      $('#btn-range').setAttribute('aria-pressed', String(!!state.range));
      $('#btn-range').innerHTML = icon('calendar', 15) + (state.range ? `<span>${esc(periodLabel())}</span>` : '');
    };
    $$('#time-seg button[data-h]').forEach(b => b.addEventListener('click', () => {
      state.hours = b.dataset.h === 'all' ? 'all' : +b.dataset.h; state.range = null; $('#range-pop').hidden = true; markPeriod(); refresh();
    }));
    $('#btn-range').addEventListener('click', () => { $('#range-pop').hidden = !$('#range-pop').hidden; });
    $('#range-pop').addEventListener('submit', ev => {
      ev.preventDefault();
      const parse = v => { v = v.trim(); const m = v.match(/^(\d{1,2})[\/.-](\d{1,2})[\/.-](\d{4})$/); return m ? `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}` : (/^\d{4}-\d{2}-\d{2}$/.test(v) ? v : null); };
      const from = parse($('#range-from').value), to = parse($('#range-to').value);
      if (!from || !to || from > to) { toast(t('range_err')); return; }
      state.range = { from, to }; $('#range-pop').hidden = true; markPeriod(); refresh();
    });
    $('#range-pick-from').addEventListener('change', ev => { const [y, m, d] = ev.target.value.split('-'); $('#range-from').value = `${d}/${m}/${y}`; });
    $('#range-pick-to').addEventListener('change', ev => { const [y, m, d] = ev.target.value.split('-'); $('#range-to').value = `${d}/${m}/${y}`; });
    markPeriod();
    $('.tabs').addEventListener('click', ev => { const b = ev.target.closest('button[data-tab]'); if (b) { state.tab = b.dataset.tab; renderTabs(); } });
    $('#sev-summary').addEventListener('click', ev => {
      const b = ev.target.closest('[data-sev]'); if (!b) return;
      const s = +b.dataset.sev; state.sev[s] = !state.sev[s];
      if (![1, 2, 3, 4].some(x => state.sev[x])) state.sev = { 1: true, 2: true, 3: true, 4: true };
      refresh();
    });
    $('#filter-groups').addEventListener('click', ev => {
      const chip = ev.target.closest('[data-cat]');
      const all = ev.target.closest('[data-gall]'); const none = ev.target.closest('[data-gnone]');
      const keysOf = g => Object.entries(TAX.categories).filter(([, c]) => c.group === g).map(([k]) => k);
      if (chip) { const k = chip.dataset.cat; state.cats.has(k) ? state.cats.delete(k) : state.cats.add(k); }
      else if (all) keysOf(all.dataset.gall).forEach(k => state.cats.add(k));
      else if (none) keysOf(none.dataset.gnone).forEach(k => state.cats.delete(k));
      else return;
      ev.preventDefault(); refresh();
    });
    $('#only-ongoing').addEventListener('change', ev => { state.onlyOngoing = ev.target.checked; refresh(); });
    $('#ongoing-list').addEventListener('click', ev => {
      const e = ev.target.closest('[data-event]'); const c = ev.target.closest('[data-country]');
      if (e) { openEvent(e.dataset.event); closePanelMobile(); } else if (c && c.dataset.country) { openCountry(c.dataset.country); closePanelMobile(); }
    });
    $('#only-sites').addEventListener('change', ev => { state.onlySites = ev.target.checked; refresh(); });
    $('#hide-auto').addEventListener('change', ev => { state.hideAuto = ev.target.checked; refresh(); });
    $('#sort').addEventListener('change', ev => { state.sort = ev.target.value; renderAlerts(visible()); });
    $('#btn-export').addEventListener('click', exportList);
    $('#alert-list').addEventListener('click', ev => {
      if (ev.target.id === 'more') { state.limit += 60; renderAlerts(visible()); return; }
      const li = ev.target.closest('.alert'); if (li) { openEvent(li.dataset.id); closePanelMobile(); }
    });
    $('#country-list').addEventListener('click', ev => { const li = ev.target.closest('[data-iso]'); if (li) { openCountry(li.dataset.iso); closePanelMobile(); } });
    $('#country-filter').addEventListener('input', ev => { state.countryFilter = ev.target.value; renderCountries(); });
    $('#news-filter').addEventListener('input', ev => { state.newsFilter = ev.target.value; renderNews(); });
    $('#drawer').addEventListener('click', ev => {
      const c = ev.target.closest('[data-country]'); const e = ev.target.closest('[data-event]'); const z = ev.target.closest('[data-zoom]');
      if (c) { ev.preventDefault(); openCountry(c.dataset.country); }
      else if (e) openEvent(e.dataset.event);
      else if (z) { const x = EVENTS.find(y => y.id === z.dataset.zoom); if (x) map.flyTo([x.lat, x.lon], 9, { duration: 0.8 }); }
    });
    $('#drawer-close').addEventListener('click', closeDrawer);
    $('#health').addEventListener('click', openHealth);
    $('#btn-analytics').addEventListener('click', () => {
      if (state.analytics) { closeAnalytics(); return; }
      state.analytics = true; $('#btn-analytics').classList.add('on'); closeDrawer(); renderAnalytics();
    });
    $('#analytics').addEventListener('click', ev => { if (ev.target.closest('#a-close')) closeAnalytics(); });
    $('#analytics').addEventListener('change', ev => {
      const id = ev.target.id;
      if (id === 'af-country') state.aCountry = ev.target.value;
      else if (id === 'af-group') state.aGroup = ev.target.value;
      else if (id === 'af-sev') state.aSev = +ev.target.value;
      else if (id === 'af-source') state.aSource = ev.target.value;
      else if (id === 'af-auto') state.aAuto = ev.target.checked;
      else return;
      renderAnalytics();
    });
    $('#btn-lang').addEventListener('click', () => { state.lang = state.lang === 'fr' ? 'en' : 'fr'; persist(); applyI18n(); renderAll(); reopenDrawer(); });
    $('#btn-theme').addEventListener('click', () => { state.theme = state.theme === 'dark' ? 'light' : 'dark'; persist(); applyTheme(); renderAll(); reopenDrawer(); });
    $('#btn-panel').addEventListener('click', () => $('#app').classList.toggle('panel-open'));
    $('#lyr-events').addEventListener('change', ev => ev.target.checked ? map.addLayer(cluster) : map.removeLayer(cluster));
    $('#lyr-risk').addEventListener('change', ev => ev.target.checked ? map.addLayer(riskLayer) : map.removeLayer(riskLayer));
    $('#lyr-sites').addEventListener('change', ev => ev.target.checked ? map.addLayer(sitesLayer) : map.removeLayer(sitesLayer));
    $('#basemap').addEventListener('change', ev => { state.basemap = ev.target.value; fallbackBasemap.done = false; persist(); setBasemap(); });

    const input = $('#search-input');
    input.addEventListener('input', () => runSearch(input.value));
    input.addEventListener('keydown', ev => { if (ev.key === 'Enter') { const first = $('#search-results button'); if (first) first.click(); } });
    $('#search-results').addEventListener('click', ev => {
      const c = ev.target.closest('[data-country]'); const e = ev.target.closest('[data-event]');
      if (c) openCountry(c.dataset.country); if (e) openEvent(e.dataset.event);
      $('#search-results').hidden = true; input.value = '';
    });
    document.addEventListener('click', ev => { if (!ev.target.closest('#search')) $('#search-results').hidden = true; });
    document.addEventListener('keydown', ev => { if (ev.key === 'Escape') { closeDrawer(); closeAnalytics(); $('#search-results').hidden = true; stopPicking(); } });

    // sites
    $('#btn-add-site').addEventListener('click', () => { state.picking = true; $('#app').classList.add('picking'); closePanelMobile(); toast(t('pick_site'), 0); });
    map.on('click', ev => {
      if (!state.picking) return;
      state.pick = ev.latlng; stopPicking();
      $('#site-form').hidden = false; $('#site-name').value = ''; $('#site-name').focus();
      $('#site-coords').textContent = `${ev.latlng.lat.toFixed(4)}, ${ev.latlng.lng.toFixed(4)}`;
      state.tab = 'sites'; renderTabs(); $('#app').classList.add('panel-open');
    });
    $('#site-form').addEventListener('submit', ev => {
      ev.preventDefault();
      if (!state.pick) return;
      state.localSites.push({ name: $('#site-name').value.trim() || 'Site', lat: +state.pick.lat.toFixed(4), lon: +L.Util.wrapNum(state.pick.lng, [-180, 180], true).toFixed(4), radius_km: +$('#site-radius').value || 25, min_severity: 1 });
      store.set('vs-sites', state.localSites); state.pick = null; $('#site-form').hidden = true;
      computeProximity(); renderAll(); toast(t('site_saved'));
    });
    $('#site-cancel').addEventListener('click', () => { $('#site-form').hidden = true; state.pick = null; });
    $('#site-list').addEventListener('click', ev => {
      const del = ev.target.closest('[data-del]');
      if (del) { state.localSites.splice(+del.dataset.del.slice(1), 1); store.set('vs-sites', state.localSites); computeProximity(); renderAll(); return; }
      const row = ev.target.closest('.site-row'); if (row) { map.flyTo([+row.dataset.lat, +row.dataset.lon], 9, { duration: 0.8 }); closePanelMobile(); }
    });
    $('#btn-export-sites').addEventListener('click', () => {
      const sites = allSites().map(({ origin, key, ...s }) => s);
      const blob = new Blob([JSON.stringify({ sites }, null, 2)], { type: 'application/json' });
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'sites.local.json';
      document.body.appendChild(a); a.click(); a.remove(); toast(t('export_done'), 6000);
    });
  }
  function stopPicking() { state.picking = false; $('#app').classList.remove('picking'); $('#toast').hidden = true; }
  function closePanelMobile() { if (window.innerWidth <= 860) $('#app').classList.remove('panel-open'); }

  /* ------------------------------------------------------------------ démarrage */
  if (D && D.settings && D.settings.product_name) { $('#brand-name').textContent = D.settings.product_name; document.title = D.settings.product_name; }
  computeProximity();
  applyI18n();
  applyTheme();
  riskLayer.addTo(map); cluster.addTo(map); sitesLayer.addTo(map);
  bind();
  ensureArchives(renderAll);
  const hash = decodeURIComponent(location.hash.slice(1));
  if (hash && countryProps[hash]) openCountry(hash);
  if (!D) {
    const el = $('#empty');
    el.innerHTML = `<div class="box"><h2>${t('empty_title')}</h2><p>${t('empty_body')}</p><p><code>python collecte.py</code></p><p>${t('empty_after')}</p></div>`;
    el.hidden = false;
  }
  window.addEventListener('resize', () => map.invalidateSize());
})();
