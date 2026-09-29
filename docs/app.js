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
      tab_alerts: 'Alertes', tab_ongoing: 'En cours', tab_countries: 'Pays', tab_news: 'Fil', tab_sites: 'Mes sites', tab_buddy: 'Travel buddy',
      buddy_title: 'My travel buddy', buddy_ph: 'Votre question (pays, ville, trajet…)', buddy_send: 'Envoyer', buddy_clear: 'Effacer',
      buddy_hello: 'Bonjour ! Posez-moi une question sur une destination : sécurité, trajet, santé, tenue, usages, urgences… Je réponds à partir des avis officiels (MEAE, FCDO, US), des incidents récents et des fiches pays.',
      buddy_examples: ['Quels vaccins faire avant d\'aller au Nigeria ?', 'Comment sécuriser mon trajet entre Lagos et Abuja ?', 'Quelle tenue porter en étant une femme en Indonésie ?', 'Numéros d\'urgence au Kenya ?'],
      buddy_thinking: 'Je rassemble les informations…', buddy_mode_ai: 'Réponse rédigée par IA à partir des données Angor – à vérifier', buddy_mode_local: 'Données Angor (sans IA)',
      buddy_ai_on: 'Assistant IA actif. Ne saisissez pas de données personnelles.', buddy_ai_off: 'Mode sans IA : réponses construites à partir des données Angor.', buddy_ai_down: 'Assistant IA indisponible : réponse construite à partir des données Angor.',
      legend: 'Légende',
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
      layers: 'Couches', lyr_events: 'Alertes', lyr_risk: 'Risque pays', lyr_sites: 'Mes sites', lyr_country: 'Calque pays',
      cl_risk: 'Risque pays (Angor)', cl_meae: 'Heatmap MEAE (France)', cl_fcdo: 'FCDO (Royaume-Uni)', cl_us: 'State Dept (États-Unis)', cl_none: 'Aucun',
      min_levels: { 1: 'Vigilance normale', 2: 'Vigilance renforcée', 3: 'Déconseillé sauf raison impérative', 4: 'Formellement déconseillé' },
      us_levels: { 1: 'Précautions normales', 2: 'Prudence accrue', 3: 'Voyage à reconsidérer', 4: 'Ne pas voyager' },
      zones_note: 'Pointillés : seules certaines zones sont concernées. Couleur = zone la plus sensible. La carte officielle fait foi.',
      official_map: 'Carte officielle', parts: 'certaines zones', no_adv: 'Pas d\'avis connu', updated_on: 'mis à jour',
      loading_hist: 'Chargement de la base historique…', hist_note: (a, b) => `base historique ${a} → ${b} (UCDP, GDELT, USGS, GDACS, NASA, OMS) puis veille en direct`,
      cov_low: 'couverture faible', cov_low_tip: 'Nos sources remontent beaucoup moins d\'incidents que la moyenne historique : la situation est probablement sous-estimée.', cov_notice: (a, b) => `Couverture des sources faible : ${a} incident(s) sûreté sur 30 jours contre ${Math.round(b)} par mois en moyenne historique. Les incidents affichés sont probablement sous-estimés.`, cov_title: 'Zones sous-couvertes', cov_hint: 'Incidents sûreté sur 30 jours / moyenne mensuelle historique (UCDP, GDELT). Indicatif.', per_month: '/ mois',
      bm_fallback: 'Fond de carte indisponible : repli sur un fond plus simple.', sum_ai: 'Résumé IA – à vérifier', sum_source: 'Extrait de la source', sum_auto: 'Résumé automatique',
      basemap: 'Fond', bm_detail: 'Détaillé (routes, villes)', bm_bright: 'Contrasté', bm_clean: 'Épuré', bm_sat: 'Satellite', bm_topo: 'Topographique', bm_esri: 'Gris (Esri)', bm_plain: 'Neutre (hors ligne)',
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
      tab_alerts: 'Alerts', tab_ongoing: 'Ongoing', tab_countries: 'Countries', tab_news: 'Feed', tab_sites: 'My sites', tab_buddy: 'Travel buddy',
      buddy_title: 'My travel buddy', buddy_ph: 'Your question (country, city, route…)', buddy_send: 'Send', buddy_clear: 'Clear',
      buddy_hello: 'Hi! Ask me about a destination: security, routes, health, dress code, customs, emergency numbers… I answer from official advice (MEAE, FCDO, US), recent incidents and country sheets.',
      buddy_examples: ['Which vaccines before travelling to Nigeria?', 'How to secure a road trip from Lagos to Abuja?', 'What should a woman wear in Indonesia?', 'Emergency numbers in Kenya?'],
      buddy_thinking: 'Gathering information…', buddy_mode_ai: 'AI-written answer based on Angor data – to be verified', buddy_mode_local: 'Angor data (no AI)',
      buddy_ai_on: 'AI assistant on. Do not enter personal data.', buddy_ai_off: 'No-AI mode: answers built from Angor data.', buddy_ai_down: 'AI assistant unavailable: answer built from Angor data.',
      legend: 'Legend',
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
      layers: 'Layers', lyr_events: 'Alerts', lyr_risk: 'Country risk', lyr_sites: 'My sites', lyr_country: 'Country layer',
      cl_risk: 'Country risk (Angor)', cl_meae: 'MEAE heatmap (France)', cl_fcdo: 'FCDO (United Kingdom)', cl_us: 'State Dept (United States)', cl_none: 'None',
      min_levels: { 1: 'Normal vigilance', 2: 'Increased vigilance', 3: 'Advised against except essential', 4: 'Advised against all travel' },
      us_levels: { 1: 'Exercise normal precautions', 2: 'Exercise increased caution', 3: 'Reconsider travel', 4: 'Do not travel' },
      zones_note: 'Dashed: only some areas are concerned. Colour = most sensitive area. The official map prevails.',
      official_map: 'Official map', parts: 'some areas', no_adv: 'No known advice', updated_on: 'updated',
      loading_hist: 'Loading historical database…', hist_note: (a, b) => `historical database ${a} → ${b} (UCDP, GDELT, USGS, GDACS, NASA, WHO) then live monitoring`,
      cov_low: 'low coverage', cov_low_tip: 'Our sources report far fewer incidents than the historical average: the situation is probably under-reported.', cov_notice: (a, b) => `Low source coverage: ${a} security incident(s) in 30 days vs ${Math.round(b)} per month historically. Displayed incidents are probably under-reported.`, cov_title: 'Under-covered areas', cov_hint: 'Security incidents in 30 days / historical monthly average (UCDP, GDELT). Indicative.', per_month: '/ month',
      bm_fallback: 'Basemap unavailable: switched to a simpler one.', sum_ai: 'AI summary – to be verified', sum_source: 'From the source', sum_auto: 'Automatic summary',
      basemap: 'Basemap', bm_detail: 'Detailed (roads, towns)', bm_bright: 'High contrast', bm_clean: 'Clean', bm_sat: 'Satellite', bm_topo: 'Topographic', bm_esri: 'Grey (Esri)', bm_plain: 'Neutral (offline)',
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
  /* Base historique (5 ans) : sommaire chargé au démarrage, années et mois chargés à la demande */
  const HIDX = window.VS_HIST_INDEX || null;
  const HIST_UNTIL = HIDX ? Date.parse(HIDX.until + 'T23:59:59Z') : -Infinity;
  const HIST = [];
  const histYears = new Set();
  const HTAGS = [[], ['auto-detected'], ['multi-source'], ['auto-detected', 'multi-source']];
  const GROUP_COLORS = { security: '#B0182E', political: '#E0A21B', natural: '#3F86C6', health: '#7D5BA6', infrastructure: '#5E6B78' };

  const BASEMAPS = ['detail', 'bright', 'clean', 'satellite', 'topo', 'esri', 'plain'];
  /* ------------------------------------------------------------------ état */
  const state = {
    lang: store.get('vs-lang', (D && D.settings && D.settings.default_lang) || 'fr'),
    theme: store.get('vs-theme', window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
    basemap: (b => BASEMAPS.includes(b) ? b : b === 'vector' ? 'clean' : 'detail')(store.get('vs-basemap', 'detail')),
    hours: store.get('vs-hours', 72), range: null, tab: 'alerts', aCountry: '', aGroup: '', aSev: 1, aSource: '', aAuto: true, sort: 'date', limit: 60,
    sev: store.get('vs-sev', { 1: true, 2: true, 3: true, 4: true }),
    cats: new Set(store.get('vs-cats', Object.keys(TAX.categories))),
    onlySites: false, onlyOngoing: false, hideAuto: store.get('vs-hideauto', false),
    selected: null, drawer: null, localSites: store.get('vs-sites', []), picking: false, pick: null,
    countryFilter: '', newsFilter: '', analytics: false,
    legendOpen: store.get('vs-legend', true),
    countryLayer: (v => ['risk', 'meae', 'fcdo', 'us', 'none'].includes(v) ? v : 'risk')(store.get('vs-clayer', 'risk'))
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
  const flagImg = (iso, w = 20) => iso && iso.length === 2 ? `<img class="flag" src="https://flagcdn.com/w${w * 2}/${iso.toLowerCase()}.png" width="${w}" alt="" loading="lazy" onerror="this.remove()">` : '';
  /* Couverture des sources : incidents sûreté des 30 derniers jours comparés à la moyenne mensuelle
     de la base historique (12 derniers mois). Indicatif : signale les zones probablement sous-couvertes. */
  const SEC_CATS = new Set(['armed_conflict', 'attack', 'terrorism', 'crime', 'unrest', 'political']);
  function coverageMap() {
    const base = (HIDX && HIDX.baseline_month) || {};
    const since = Date.now() - 30 * 864e5, live = {};
    EVENTS.forEach(e => { if (!e.hist && e.country && e._t >= since && SEC_CATS.has(e.category)) live[e.country] = (live[e.country] || 0) + 1; });
    const out = {};
    Object.entries(base).forEach(([iso, b]) => {
      if (b < 15) return;
      const ratio = (live[iso] || 0) / b;
      out[iso] = { ratio, live: live[iso] || 0, base: b, level: ratio < 0.2 ? 'low' : ratio < 0.5 ? 'partial' : 'good' };
    });
    return out;
  }

  /** Description lisible (liste) : résumé IA dans la langue choisie, chapeau de la source, titre d'article. */
  function describe(e) {
    const fr = state.lang === 'fr';
    let s = (fr && e.summary_fr) || (e.summary && !/^(Auto-detected|Detected in)/.test(e.summary) ? e.summary : '');
    if (!s && e.snippet) s = e.snippet;
    if (!s && e.headline && e.headline !== e.title) s = e.headline;
    return s || '';
  }
  /** Résumé de 2 à 4 lignes pour la fiche : { text, kind } (kind = ai | source | auto). */
  function summaryOf(e) {
    const s = describe(e);
    const ai = (e.tags || []).includes('ai') && (e.summary_fr || (e.summary && !/^(Auto-detected|Detected in)/.test(e.summary)));
    if (ai) return { text: s, kind: 'ai' };
    if (s && !isAuto(e)) return { text: s, kind: 'source' };
    const auto = autoSummary(e);
    return s && s !== e.title ? { text: `${s.replace(/[.\s]+$/, '')}. ${auto}`, kind: e.snippet ? 'source' : 'auto' } : { text: auto, kind: 'auto' };
  }
  function autoSummary(e) {
    const fr = state.lang === 'fr';
    const where = [e.place, e.country && countryName(e.country) !== e.place ? countryName(e.country) : ''].filter(Boolean).join(', ') || t('at_sea');
    const day = new Date(e.date).toLocaleDateString(fr ? 'fr-FR' : 'en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
    const outlets = [...new Set((e.sources || []).map(x => x.name === 'Press (via GDELT)' ? hostOf(x.url) : x.name).filter(Boolean))];
    let who;
    if (e.source === 'GDELT') {
      const m = /\((\d+) article\(s\), (\d+) outlet/.exec(e.summary || '');
      who = m ? (fr ? `repéré dans ${m[1]} article(s) de ${m[2]} média(s) (GDELT)` : `picked up in ${m[1]} article(s) from ${m[2]} outlet(s) (GDELT)`)
              : (fr ? 'repéré dans la presse (GDELT)' : 'picked up in the press (GDELT)');
    } else {
      const list = outlets.slice(0, 3).join(', ') + (outlets.length > 3 ? '…' : '');
      who = outlets.length > 1 ? (fr ? `rapporté par ${outlets.length} médias (${list})` : `reported by ${outlets.length} outlets (${list})`)
                               : (fr ? `rapporté par ${list || e.source}` : `reported by ${list || e.source}`);
    }
    return fr ? `${catLabel(e.category)} à ${where}, le ${day} : ${who}.${outlets.length > 1 ? ' Plusieurs sources concordent.' : ''}`
              : `${catLabel(e.category)} in ${where} on ${day}: ${who}.${outlets.length > 1 ? ' Several sources concur.' : ''}`;
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
  const map = L.map('map', { zoomControl: false, worldCopyJump: true, minZoom: 2, maxZoom: 18 }).setView([28, 12], 3);
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
  const ESRI_SVC = 'https://server.arcgisonline.com/ArcGIS/rest/services/';
  // Fonds vectoriels OpenFreeMap : nets à tous les zooms et sur écrans haute définition (routes, villes, relief)
  const OFM_STYLES = { detail: ['liberty', 'dark'], bright: ['bright', 'fiord'], clean: ['positron', 'dark'] };
  const DETAILED = new Set(['detail', 'bright', 'satellite', 'topo']);
  function setBasemap() {
    [baseLayer, labelLayer].forEach(l => { if (l) map.removeLayer(l); });
    baseLayer = labelLayer = null;
    map.removeLayer(landLayer);
    const mode = state.basemap;
    const dark = state.theme === 'dark';
    if (OFM_STYLES[mode] && window.maplibregl && L.maplibreGL && (!maplibregl.supported || maplibregl.supported())) {
      try {
        baseLayer = L.maplibreGL({ style: `https://tiles.openfreemap.org/styles/${OFM_STYLES[mode][dark ? 1 : 0]}`, attribution: OFM_ATTR, interactive: false });
        baseLayer.addTo(map);
        const gl = baseLayer.getMaplibreMap && baseLayer.getMaplibreMap();
        if (gl) {
          gl.on('error', ev => { if (!gl.isStyleLoaded || !gl.isStyleLoaded()) fallbackBasemap(); });
          if (gl.isStyleLoaded && gl.isStyleLoaded()) tuneLabels(gl); else gl.once('load', () => tuneLabels(gl));
        }
        refreshRiskStyle();
        return;
      } catch (e) { /* repli ci-dessous */ }
    }
    let ok = 0, ko = 0;
    const watch = l => { l.on('tileload', () => { ok++; }); l.on('tileerror', () => { ko++; if (ko >= 6 && ok === 0) fallbackBasemap(true); }); return l; };
    if (mode === 'satellite') {
      baseLayer = watch(L.tileLayer(`${ESRI_SVC}World_Imagery/MapServer/tile/{z}/{y}/{x}`, { attribution: 'Imagery &copy; Esri, Maxar, Earthstar Geographics', maxNativeZoom: 18, maxZoom: 18 }));
      labelLayer = L.tileLayer(`${ESRI_SVC}Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}`, { pane: 'labels', maxNativeZoom: 18, maxZoom: 18 });
    } else if (mode === 'topo') {
      baseLayer = watch(L.tileLayer(`${ESRI_SVC}World_Topo_Map/MapServer/tile/{z}/{y}/{x}`, { attribution: ESRI_ATTR, maxNativeZoom: 18, maxZoom: 18 }));
    } else if (mode !== 'plain') {
      const v = dark ? 'Dark' : 'Light';
      baseLayer = watch(L.tileLayer(`${ESRI}World_${v}_Gray_Base/MapServer/tile/{z}/{y}/{x}`, { attribution: ESRI_ATTR, maxNativeZoom: 16, maxZoom: 18 }));
      labelLayer = L.tileLayer(`${ESRI}World_${v}_Gray_Reference/MapServer/tile/{z}/{y}/{x}`, { pane: 'labels', maxNativeZoom: 16, maxZoom: 18 });
    }
    if (baseLayer) { baseLayer.addTo(map); if (labelLayer) labelLayer.addTo(map); refreshRiskStyle(); return; }
    landLayer.setStyle(landStyle()); landLayer.addTo(map); landLayer.bringToBack();
    refreshRiskStyle();
  }
  /* Étiquettes du fond vectoriel : noms en alphabet latin uniquement (français ou anglais), et affichage
     progressif – pays en vue monde, régions et capitales à partir du zoom 5, villes à 7, bourgs à 9, villages à 12.
     (Le zoom MapLibre vaut le zoom Leaflet moins 1.) */
  function tuneLabels(gl) {
    try {
      const pref = state.lang === 'fr' ? 'name:fr' : 'name:en';
      const nameExpr = ['coalesce', ['get', pref], ['get', 'name:en'], ['get', 'name_en'], ['get', 'name:latin'], ['get', 'name_int']];
      gl.getStyle().layers.forEach(l => {
        if (l.type !== 'symbol') return;
        const tf = gl.getLayoutProperty(l.id, 'text-field');
        if (tf && /name/.test(JSON.stringify(tf))) gl.setLayoutProperty(l.id, 'text-field', nameExpr);
        if (l['source-layer'] !== 'place') return;
        const id = l.id.toLowerCase();
        const min = /country/.test(id) ? null : /state|province/.test(id) ? 4 : /capital/.test(id) ? 4
          : /city/.test(id) ? 6 : /town/.test(id) ? 8 : /village|hamlet|suburb|quarter|neighbo|other|isolated|island/.test(id) ? 11 : 6;
        if (min != null) gl.setLayerZoomRange(l.id, Math.max(min, l.minzoom || 0), l.maxzoom || 24);
      });
    } catch (e) { /* style inattendu : on garde les étiquettes d'origine */ }
  }
  function fallbackBasemap(toPlain) {
    if (fallbackBasemap.done) return;
    fallbackBasemap.done = true;
    state.basemap = toPlain || state.basemap === 'esri' ? 'plain' : 'esri';
    toast(t('bm_fallback'));
    $('#basemap').value = state.basemap; setBasemap();
  }

  const riskLayer = L.geoJSON(COUNTRIES, {
    style: f => countryStyle(f.properties.iso2),
    onEachFeature: (f, layer) => {
      layer.on('click', ev => { if (state.picking) return; L.DomEvent.stopPropagation(ev); openCountry(f.properties.iso2); });
      layer.on('mouseover', () => { if (!state.picking) layer.setStyle({ weight: 1.6, color: cssVar('--ink-2') }); });
      layer.on('mouseout', () => riskLayer.resetStyle(layer));
      layer.bindTooltip(() => {
        const iso = f.properties.iso2, r = RISK[iso], mode = state.countryLayer;
        if (MIN_SOURCES[mode]) {
          const a = advisoryOf(iso, mode);
          return `<strong>${esc(countryName(iso))}</strong><br>${esc(MIN_SOURCES[mode])} : ${a ? esc(minLabel(a, mode)) : t('no_adv')}`;
        }
        return `<strong>${esc(countryName(iso))}</strong><br>${r ? `${t('risk_level')} : ${r.level} · ${esc(riskLabel(r.level))}` : t('no_data')}`;
      }, { sticky: true, className: 'vs-tip', direction: 'top', offset: [0, -8] });
    }
  });
  /* Calques des ministères des affaires étrangères (niveaux par pays, couleurs de la carte MEAE) */
  const MIN_SOURCES = { meae: 'MEAE (France)', fcdo: 'FCDO (UK)', us: 'US State Dept' };
  const MIN_COLORS = { 1: '#2E9E5B', 2: '#E3B505', 3: '#EE7D22', 4: '#D7263D' };
  function advisoryOf(iso, mode) {
    const r = RISK[iso];
    return r && r.advisories ? r.advisories[MIN_SOURCES[mode]] || null : null;
  }
  const minLevel = (a, mode) => mode === 'us' ? a.level : (a.max || a.level);
  function minLabel(a, mode) {
    const lvl = minLevel(a, mode);
    if (mode === 'fcdo' && a.label) return a.label;
    const base = mode === 'us' ? t('us_levels')[lvl] : t('min_levels')[lvl];
    return base + (a.parts && lvl > 1 ? ` (${t('parts')})` : '');
  }
  function countryStyle(iso) {
    const mode = state.countryLayer, dark = state.theme === 'dark';
    const line = dark ? '#3A4A5B' : '#FFFFFF';
    const k = DETAILED.has(state.basemap) ? 0.6 : 1;
    if (mode === 'none') return { fillOpacity: 0, opacity: 0, weight: 0 };
    if (mode === 'risk') {
      const r = RISK[iso];
      return { fillColor: riskColor(r ? r.level : 0), fillOpacity: r ? (dark ? 0.38 : 0.42) * k : 0.04, color: line, weight: 0.7, dashArray: null };
    }
    const a = advisoryOf(iso, mode);
    if (!a) return { fillColor: '#9AA5B1', fillOpacity: 0.05, color: line, weight: 0.5, dashArray: null };
    return { fillColor: MIN_COLORS[minLevel(a, mode)] || '#9AA5B1', fillOpacity: (a.parts ? 0.32 : 0.55) * k,
      color: a.parts ? MIN_COLORS[minLevel(a, mode)] : line, weight: a.parts ? 1.2 : 0.7, dashArray: a.parts ? '4 3' : null };
  }
  function refreshRiskStyle() { try { riskLayer.setStyle(f => countryStyle(f.properties.iso2)); } catch (e) { /* couche pas encore créée */ } }

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
        <div><div class="n">${c.iso === '_sea' ? '' : flagImg(c.iso)}${esc(c.iso === '_sea' ? t('at_sea') : countryName(c.iso))} <span class="crisis-tag ${crisisLevel(c.evs)}">${t('crisis_' + crisisLevel(c.evs))}</span></div><div class="s">${c.risk ? `${t('risk_level')} ${c.risk} · ${esc(riskLabel(c.risk))}` : ''}</div></div></div>
      <ul class="mini-list">${c.evs.slice(0, 5).map(e => `<li data-event="${esc(e.id)}"><span class="dot" style="background:${sevColor(e.severity)}"></span><span class="t">${esc(e.title)}</span><span class="w">${esc(ago(e.date))}</span></li>`).join('')}</ul>
      ${c.evs.length > 5 ? `<div class="hint">+ ${c.evs.length - 5}</div>` : ''}</li>`).join('') : `<li class="empty">${t('no_ongoing')}</li>`;
  }

  function renderTabs() {
    $$('.tabs button').forEach(b => {
      b.setAttribute('aria-selected', String(b.dataset.tab === state.tab));
      const ic = { alerts: 'siren', ongoing: 'radio-tower', countries: 'globe', news: 'newspaper', sites: 'building-2', buddy: 'message-circle' }[b.dataset.tab];
      let label = icon(ic, 20) + `<span>${esc(t('tab_' + b.dataset.tab))}</span>`;
      const n = b.dataset.tab === 'sites' ? EVENTS.filter(e => inWindow(e) && e._near.length && e.severity >= 2).length
        : b.dataset.tab === 'ongoing' ? EVENTS.filter(isOngoing).length : 0;
      if (n) label += `<span class="badge">${n}</span>`;
      b.innerHTML = label;
    });
    $$('.tab-body').forEach(s => { s.hidden = s.dataset.body !== state.tab; });
    if (state.tab === 'buddy') { renderBuddy(); ensureBuddyData(); }
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
    const cov = coverageMap();
    $('#country-list').innerHTML = rows.length ? rows.map(x => {
      const c = x.r.counts || {};
      const adv = Object.entries(x.r.advisories || {}).map(([src, a]) => `${esc(src.split(' ')[0])} ${a.level}/${a.scale || 4}`).join(' · ');
      const n = (c.security || 0) + (c.hazards || 0);
      return `<li class="country-row" data-iso="${x.iso}"><span class="lvl" style="background:${riskColor(x.r.level)}">${x.r.level}</span>
        <div><div class="n">${flagImg(x.iso)}${esc(x.name)}${cov[x.iso] && cov[x.iso].level === 'low' ? ` <span class="cov-low" title="${esc(t('cov_low_tip'))}">${esc(t('cov_low'))}</span>` : ''}</div><div class="s">${esc(riskLabel(x.r.level))}${adv ? ` · ${adv}` : ''}</div></div>
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
    const open = state.legendOpen;
    $('#legend').classList.toggle('collapsed', !open);
    $('#legend').innerHTML = `<button class="legend-toggle" id="legend-toggle" type="button" aria-expanded="${open}">${esc(t('legend'))}<span class="chev">${icon('chevron-down', 14)}</span></button>` + (open ? `
      <div><div class="card-title">${t('legend_sev')}</div><div class="row">${[1, 2, 3, 4].map(s => `<span class="k"><i class="sw" style="background:${sevColor(s)}"></i>${esc(sevLabel(s))}</span>`).join('')}</div></div>
      ${MIN_SOURCES[state.countryLayer] ? `<div><div class="card-title">${esc(t('cl_' + state.countryLayer))}</div><div class="row">${[1, 2, 3, 4].map(l => `<span class="k"><i class="sq" style="background:${MIN_COLORS[l]}"></i>${esc((state.countryLayer === 'us' ? t('us_levels') : t('min_levels'))[l])}</span>`).join('')}</div>${state.countryLayer === 'us' ? '' : `<div class="legend-note">${t('zones_note')}</div>`}</div>`
        : state.countryLayer === 'risk' ? `<div><div class="card-title">${t('legend_risk')}</div><div class="row">${[1, 2, 3, 4, 5].map(l => `<span class="k"><i class="sq" style="background:${riskColor(l)}"></i>${esc(riskLabel(l))}</span>`).join('')}</div></div>` : ''}
      <div class="legend-note">${t('legend_auto')}</div>` : '');
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
    const sum = summaryOf(e);
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
        <div class="d-sum"><p class="d-desc">${esc(sum.text)}</p><span class="d-sum-kind">${esc(t('sum_' + sum.kind))}</span></div>
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
    const modeOf = { 'MEAE (France)': 'meae', 'FCDO (UK)': 'fcdo', 'US State Dept': 'us' };
    const advs = r && Object.keys(r.advisories || {}).length ? Object.entries(r.advisories)
      .sort(([a], [b]) => (modeOf[b] === state.countryLayer) - (modeOf[a] === state.countryLayer)).map(([src, a]) => {
        const mode = modeOf[src];
        const lvl = mode ? minLevel(a, mode) : a.level;
        const color = mode ? MIN_COLORS[lvl] : riskColor(Math.min(5, a.level + 1));
        const label = mode ? minLabel(a, mode) : a.label || '';
        return `<li class="adv"><span class="dot" style="background:${color}"></span><span><strong>${esc(src)}</strong> · ${t('level')} ${lvl} ${t('of')} ${a.scale || 4}<br><span style="color:var(--muted)">${esc(label)}${a.updated ? ` · ${t('updated_on')} ${esc(String(a.updated).slice(0, 10))}` : ''}</span>
          ${a.map ? `<a class="adv-map" href="${esc(a.map)}" target="_blank" rel="noopener" title="${esc(t('official_map'))}"><img src="${esc(a.map)}" alt="${esc(t('official_map'))} – ${esc(src)}" loading="lazy" referrerpolicy="no-referrer"></a>` : ''}</span><a class="w" href="${esc(a.url)}" target="_blank" rel="noopener">↗</a></li>`;
      }).join('') : '';
    const f = COUNTRIES.features.find(x => x.properties.iso2 === iso);
    if (f && fly) map.flyToBounds(L.geoJSON(f).getBounds(), { padding: [40, 40], maxZoom: 6, duration: 0.8 });
    openDrawer(`
      <div class="d-head">
        <div class="d-kicker">${esc((countryProps[iso] || {}).region || '')}</div>
        <h2 class="d-title">${flagImg(iso, 26)}${esc(name)}</h2>
        ${(c => c && c.level !== 'good' ? `<div class="notice">${esc(t('cov_notice', c.live, c.base))}</div>` : '')(coverageMap()[iso])}
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
      <div class="d-sec"><ul class="mini-list" style="gap:10px">${rows}</ul></div>
      ${(list => list.length ? `<div class="d-sec"><h3>${t('cov_title')}</h3><div class="hint">${t('cov_hint')}</div><ul class="mini-list">${list.map(([iso, c]) => `<li data-country="${iso}"><span class="t">${flagImg(iso)}${esc(countryName(iso) || iso)}</span><span class="w">${c.live} / ${Math.round(c.base)} ${t('per_month')}</span></li>`).join('')}</ul></div>` : '')(
        Object.entries(coverageMap()).filter(([, c]) => c.level !== 'good').sort((a, b) => a[1].ratio - b[1].ratio).slice(0, 25))}`, 'health');
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
    const [h0] = windowBounds();
    if (HIDX && h0 <= HIST_UNTIL && Object.keys(HIDX.years || {}).some(y => !histYears.has(y) && +y >= (isFinite(h0) ? new Date(h0).getUTCFullYear() : 0))) {
      ensureHistory(() => { if (state.analytics) renderAnalytics(); });
      return;
    }
    charts.splice(0).forEach(c => c.destroy());
    const pool = analyticsPool();
    const win = pool.filter(analyticsFilter);
    const inPeriod = pool.filter(inWindow);
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
    el.innerHTML = `<div class="a-head"><div><h2>${t('a_title')}${state.aCountry ? ' — ' + esc(countryName(state.aCountry)) : ''}</h2><div class="hint">${esc(t('a_period', periodLabel()))}${HIDX && h0 <= HIST_UNTIL ? ' · ' + esc(t('hist_note', HIDX.from, HIDX.until)) : ''}</div></div>
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
    if (!isFinite(a0)) a0 = win.length ? win.reduce((m, e) => Math.min(m, e._t), Infinity) : a1 - 30 * 864e5;
    const span = a1 - a0;
    const step = span > 730 * 864e5 ? 30.44 * 864e5 : span > 120 * 864e5 ? 7 * 864e5 : 864e5;
    const nb = Math.max(1, Math.ceil(span / step));
    const lfmt = step > 20 * 864e5 ? { month: 'short', year: '2-digit' } : span > 365 * 864e5 ? { day: 'numeric', month: 'short', year: '2-digit' } : { day: 'numeric', month: 'short' };
    const labels = Array.from({ length: nb }, (_, i) => new Date(a0 + i * step).toLocaleDateString(state.lang, lfmt));
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
      .map(p => `<button data-country="${p.iso2}">${RISK[p.iso2] ? `<span class="pill" style="background:${riskColor(RISK[p.iso2].level)}">${RISK[p.iso2].level}</span>` : ''}${flagImg(p.iso2)}${esc(p['name_' + state.lang])}<span class="kind">${t('country')}</span></button>`);
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
    store.set('vs-hideauto', state.hideAuto); store.set('vs-lang', state.lang); store.set('vs-theme', state.theme); store.set('vs-basemap', state.basemap); store.set('vs-clayer', state.countryLayer);
  }
  /* Analyses sur plusieurs années : lignes compactes de la base historique (jusqu'à la veille de sa création) */
  function ensureHistory(done) {
    const [a0] = windowBounds();
    if (!HIDX || a0 > HIST_UNTIL) return done();
    const y0 = isFinite(a0) ? new Date(a0).getUTCFullYear() : 0;
    const need = Object.keys(HIDX.years || {}).filter(y => +y >= y0 && !histYears.has(y));
    if (!need.length) return done();
    toast(t('loading_hist'), 0);
    let left = need.length;
    need.forEach(y => {
      const sc = document.createElement('script');
      sc.src = `data/history/stats-${y}.js`;
      sc.onload = sc.onerror = () => {
        histYears.add(y);
        const d = (window.VS_HIST || {})[y];
        if (d) {
          d.rows.forEach(r => HIST.push({ _t: r[0] * 864e5 + 432e5, country: r[1] || null, category: HIDX.cats[r[2]], severity: r[3],
            source: HIDX.srcs[r[4]], tags: HTAGS[r[5] & 3], confidence: r[5] & 2 ? 'high' : r[5] & 4 ? 'low' : 'medium', place: d.places[r[6]] || '', hist: true }));
          delete window.VS_HIST[y];
        }
        if (--left === 0) { $('#toast').hidden = true; done(); }
      };
      document.head.appendChild(sc);
    });
  }
  /** Données des analyses : base historique jusqu'à sa date de fin, puis la veille en direct. */
  function analyticsPool() {
    const live = EVENTS.filter(e => !e.hist && e._t > HIST_UNTIL);
    return HIST.length ? HIST.concat(live) : live;
  }
  /* Historique au-delà de 30 jours : archives mensuelles chargées seulement si la période l'exige */
  const loadedMonths = new Set();
  function ensureArchives(done) {
    const [a] = windowBounds();
    const inWin = m => Date.parse(m + '-01T00:00:00Z') + 31 * 864e5 >= a;
    const need = Object.keys((D && D.archives) || {}).filter(m => !loadedMonths.has(m) && inWin(m)).map(m => ['a', m])
      .concat(Object.keys((HIDX && HIDX.map_months) || {}).filter(m => !loadedMonths.has('h' + m) && inWin(m)).map(m => ['h', m]));
    if (!need.length) return done();
    toast(t('loading_archive'), 0);
    let left = need.length;
    need.forEach(([kind, m]) => {
      const sc = document.createElement('script');
      sc.src = kind === 'a' ? `data/archive/${m}.js` : `data/history/map/${m}.js`;
      sc.onload = sc.onerror = () => {
        loadedMonths.add(kind === 'a' ? m : 'h' + m);
        const known = new Set(EVENTS.map(e => e.id));
        const list = kind === 'a' ? (window.VS_ARCHIVE || {})[m] : (window.VS_HMAP || {})[m];
        (list || []).forEach(e => { if (!known.has(e.id)) { if (kind === 'h') e.hist = true; EVENTS.push(e); } });
        if (kind === 'h' && window.VS_HMAP) delete window.VS_HMAP[m];
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
    $('#legend').addEventListener('click', ev => { if (ev.target.closest('#legend-toggle')) { state.legendOpen = !state.legendOpen; store.set('vs-legend', state.legendOpen); renderLegend(); } });
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
    $('#btn-lang').addEventListener('click', () => { state.lang = state.lang === 'fr' ? 'en' : 'fr'; persist(); applyI18n(); renderAll(); reopenDrawer();
      const gl = baseLayer && baseLayer.getMaplibreMap && baseLayer.getMaplibreMap(); if (gl) tuneLabels(gl); });
    $('#btn-theme').addEventListener('click', () => { state.theme = state.theme === 'dark' ? 'light' : 'dark'; persist(); applyTheme(); renderAll(); reopenDrawer(); });
    $('#btn-panel').addEventListener('click', () => $('#app').classList.toggle('panel-open'));
    $('#lyr-events').addEventListener('change', ev => ev.target.checked ? map.addLayer(cluster) : map.removeLayer(cluster));
    $('#country-layer').value = state.countryLayer;
    $('#country-layer').addEventListener('change', ev => { state.countryLayer = ev.target.value; persist(); refreshRiskStyle(); renderLegend(); });
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

  /* ------------------------------------------------------------------ My travel buddy */
  /* Assistant de voyage : repère le(s) pays et villes de la question, rassemble les données Angor
     (risque, avis MEAE/FCDO/US, incidents, fiche culturelle, santé, prestataires) puis :
     - avec un Worker IA configuré (settings.buddy_url) : réponse rédigée par Claude à partir de ce contexte ;
     - sinon : réponse structurée construite localement à partir des mêmes données (gratuit, hors ligne). */
  const BUDDY_URL = (D && D.settings && D.settings.buddy_url) || '';
  const buddy = { log: [], busy: false, loaded: null };
  const norm = s => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[’']/g, ' ');
  function loadScript(src) {
    return new Promise(res => { const s = document.createElement('script'); s.src = src; s.onload = s.onerror = () => res(); document.head.appendChild(s); });
  }
  function ensureBuddyData() {
    if (!buddy.loaded) buddy.loaded = Promise.all(['data/guides.js', 'data/practical.js', 'data/providers.js', 'data/cities.js']
      .filter(src => !document.querySelector(`script[src="${src}"]`)).map(loadScript)).then(buildIndex);
    return buddy.loaded;
  }
  const ALIASES = { usa: 'US', 'etats unis': 'US', amerique: 'US', uk: 'GB', angleterre: 'GB', 'grande bretagne': 'GB', rdc: 'CD', 'congo kinshasa': 'CD',
    'congo brazzaville': 'CG', 'cote d ivoire': 'CI', 'ivory coast': 'CI', birmanie: 'MM', burma: 'MM', emirats: 'AE', dubai: 'AE', 'hong kong': 'HK',
    'coree du sud': 'KR', 'coree du nord': 'KP', russie: 'RU', turquie: 'TR', turkiye: 'TR', holland: 'NL', hollande: 'NL', palestine: 'PS', gaza: 'PS' };
  let NAME_INDEX = [], CITY_INDEX = [];
  function buildIndex() {
    NAME_INDEX = [];
    Object.values(countryProps).forEach(p => [p.name_fr, p.name_en].forEach(n => { if (n && n.length > 3) NAME_INDEX.push([norm(n), p.iso2]); }));
    Object.entries(ALIASES).forEach(([k, v]) => NAME_INDEX.push([k, v]));
    NAME_INDEX.sort((a, b) => b[0].length - a[0].length);
    CITY_INDEX = ((window.VS_CITIES || {}).cities || []).filter(c => c[0].length >= 4).map(c => ({ key: norm(c[0]), name: c[0], iso: c[1], lat: c[2], lon: c[3] }));
  }
  const wordIn = (hay, w) => new RegExp(`(^|[^a-z])${w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}([^a-z]|$)`).test(hay);
  function detect(q) {
    const h = ' ' + norm(q) + ' ';
    const isos = [], cities = [];
    NAME_INDEX.forEach(([n, iso]) => { if (!isos.includes(iso) && wordIn(h, n)) isos.push(iso); });
    for (const c of CITY_INDEX) {
      if (cities.length >= 3) break;
      if (wordIn(h, c.key) && !cities.some(x => x.key === c.key)) { cities.push(c); if (!isos.includes(c.iso)) isos.push(c.iso); }
    }
    if (!isos.length && state.drawer && state.drawer.kind === 'country') isos.push(state.drawer.id);
    return { isos: isos.slice(0, 2), cities };
  }
  const INTENTS = {
    health: /vaccin|sante|health|paludisme|malaria|medecin|docteur|hopita|hospital|maladie|disease|medic|pharma|eau potable|moustique/,
    dress: /tenue|vetement|porter|habill|dress|wear|clothes|voile|foulard/,
    culture: /culture|geste|salu|poignee|greet|affaire|business|cadeau|gift|religion|ramadan|coutume|custom|etiquette|interdit|alcool|photo/,
    women: /femme|woman|women|voyageuse|female/,
    route: /trajet|route|itinera|aller de|entre .* et|voiture|convoi|transport|deplac|axe|road|drive|between|transfer|aeroport|airport/,
    emergency: /urgence|emergency|police|ambulance|numero|number|pompier/,
    security: /securi|risque|risk|danger|safe|sur\b|menace|threat|terror|enlev|kidnap|attentat|situation|manif|protest/,
    providers: /prestataire|protection rapprochee|garde du corps|bodyguard|escort|evacuation|provider|securite privee/,
    telecom: /telephone|sim|reseau|internet|4g|satellite|phone|prise|plug|voltage/,
  };
  const intentsOf = q => Object.entries(INTENTS).filter(([, re]) => re.test(norm(q))).map(([k]) => k);
  function kmToSegment(p, a, b) {
    let best = Infinity;
    for (let i = 0; i <= 20; i++) { const f = i / 20; best = Math.min(best, haversine(p.lat, p.lon, a.lat + (b.lat - a.lat) * f, a.lon + (b.lon - a.lon) * f)); }
    return best;
  }
  const REGION_OF = p => !p ? '' : p.region === 'Western Asia' ? 'Moyen-Orient'
    : ({ Africa: 'Afrique', Europe: 'Europe', Asia: 'Asie', 'North America': 'Amériques', 'South America': 'Amériques', Oceania: 'Océanie' }[p.continent] || '');
  /** Données Angor utiles à la question, pour un pays (et éventuellement un trajet entre deux villes). */
  function collect(iso, det, intents) {
    const r = RISK[iso] || {}, adv = r.advisories || {};
    const g = ((window.VS_GUIDES || {}).countries || {})[iso] || {};
    const pr = ((window.VS_PRACTICAL || {}).countries || {})[iso] || {};
    const prov = (window.VS_PROVIDERS || {}).providers || [];
    const local = ((window.VS_PROVIDERS || {}).local || {})[iso] || [];
    const cities = det.cities.filter(c => c.iso === iso);
    const since = Date.now() - 30 * 864e5;
    let evs = EVENTS.filter(e => !e.hist && e.country === iso && e._t >= since);
    let corridor = null;
    if (cities.length >= 2) {
      corridor = { from: cities[0].name, to: cities[1].name, km: Math.round(haversine(cities[0].lat, cities[0].lon, cities[1].lat, cities[1].lon)) };
      evs = evs.filter(e => kmToSegment(e, cities[0], cities[1]) <= 60);
    } else if (cities.length === 1) {
      evs = evs.filter(e => haversine(e.lat, e.lon, cities[0].lat, cities[0].lon) <= 100);
    }
    evs.sort((a, b) => b.severity - a.severity || b._t - a._t);
    const region = REGION_OF(countryProps[iso]);
    const provs = local.concat(prov.filter(p => !region || p.regions.includes(region)))
      .filter(p => !intents.includes('route') || p.services.some(s => ['ts', 'cp', 'ev'].includes(s))).slice(0, 5);
    const hospitals = (pr.hospitals || []).filter(h => !cities.length || cities.some(c => norm(h.city).includes(c.key))).concat(pr.hospitals || [])
      .filter((h, i, a) => a.findIndex(x => x.name === h.name) === i).slice(0, 5);
    return { iso, name: countryName(iso), level: r.level, levelLabel: r.level ? riskLabel(r.level) : '', adv, guide: g, practical: pr,
      hospitals, events: evs.slice(0, 8), nEvents: evs.length, corridor, cities, provs, ongoing: EVENTS.some(e => e.country === iso && isOngoing(e)) };
  }
  function contextText(c) {
    const L = [];
    L.push(`PAYS: ${c.name} (${c.iso}) — niveau de risque Angor ${c.level || '?'}/5 (${c.levelLabel})${c.ongoing ? ' — crise/alerte en cours' : ''}`);
    Object.entries(c.adv).forEach(([src, a]) => {
      L.push(`AVIS ${src}: niveau ${a.level}/${a.scale || 4} — ${a.label || ''}${a.updated ? ' (maj ' + a.updated + ')' : ''}`);
      (a.excerpt || []).forEach(x => L.push(`  [${src} sécurité] ${x}`));
      (a.health || []).forEach(x => L.push(`  [${src} santé] ${x}`));
    });
    if (c.corridor) L.push(`TRAJET: ${c.corridor.from} → ${c.corridor.to}, ~${c.corridor.km} km à vol d'oiseau`);
    L.push(`INCIDENTS ANGOR 30 J (${c.corridor ? 'corridor ±60 km' : c.cities.length ? 'rayon 100 km' : 'pays'}): ${c.nEvents}`);
    c.events.forEach(e => L.push(`  - ${new Date(e.date).toISOString().slice(0, 10)} ${catLabel(e.category)} gravité ${e.severity}/4 à ${e.place || '?'} : ${e.title}${e.confidence === 'low' ? ' (non vérifié)' : ''}`));
    Object.entries(c.guide).forEach(([k, v]) => L.push(`FICHE ${k.toUpperCase()}: ${(v || []).join(' | ')}`));
    const p = c.practical;
    if (p.emergency) L.push(`URGENCES: ${(p.emergency || []).join(', ')} ; indicatif ${(p.calling_code || []).join(', ')} ; prises ${(p.plugs || []).join(', ')} ; tension ${(p.voltage || []).join('/')} V ; opérateurs ${(p.operators || []).join(', ')}`);
    c.hospitals.forEach(h => L.push(`HÔPITAL: ${h.name} (${h.city || '?'})${h.beds ? ', ' + h.beds + ' lits' : ''}${h.web ? ', ' + h.web : ''}`));
    c.provs.forEach(pv => L.push(`PRESTATAIRE: ${pv.name} — ${(pv.services || []).join(',')} — ${pv.web || ''}`));
    return L.join('\n');
  }
  const li = xs => `<ul>${xs.filter(Boolean).map(x => `<li>${x}</li>`).join('')}</ul>`;
  function routeAdvice(level) {
    const fr = state.lang === 'fr';
    if (level >= 4) return fr ? ['Privilégier un vol intérieur plutôt que la route lorsque c\'est possible.', 'Si la route est indispensable : chauffeur local expérimenté, deux véhicules (convoi), escorte ou prestataire de transport sécurisé.',
      'Rouler uniquement de jour (départ après le lever du soleil, arrivée avant la nuit), sans arrêt non planifié ; varier horaires et itinéraires.',
      'Points de contact (check-in) toutes les 1 à 2 h avec un correspondant, téléphone satellite, trousse de secours et plan d\'évacuation.', 'Se renseigner la veille sur les barrages, manifestations et incidents le long de l\'axe.']
      : ['Prefer a domestic flight over road travel where possible.', 'If road travel is essential: experienced local driver, two vehicles (convoy), escort or secure-transport provider.', 'Daylight only, no unplanned stops; vary times and routes.', 'Check-ins every 1–2 h, satellite phone, first-aid kit and evacuation plan.', 'Check checkpoints, protests and incidents along the route the day before.'];
    if (level === 3) return fr ? ['Véhicule avec chauffeur de confiance (société recommandée par l\'hôtel ou l\'entreprise), pas de taxi hélé dans la rue.', 'Éviter la route de nuit ; prévoir un itinéraire de repli et informer un contact de l\'heure d\'arrivée.', 'Vérifier l\'actualité locale (manifestations, barrages) avant le départ.']
      : ['Vehicle with a trusted driver (hotel/company-recommended), no street-hailed taxis.', 'Avoid night driving; plan an alternative route and share your ETA.', 'Check local news (protests, roadblocks) before departure.'];
    return fr ? ['Précautions usuelles : transports officiels ou VTC reconnus, vigilance aux vols dans les gares et aéroports.', 'Garder sur soi les numéros d\'urgence et une copie des documents.']
      : ['Usual precautions: official transport or reputable ride-hailing, watch for theft at stations and airports.', 'Keep emergency numbers and document copies with you.'];
  }
  function localAnswer(q, det, intents) {
    const fr = state.lang === 'fr';
    if (!det.isos.length) return fr ? `<p>Je n'ai pas reconnu de pays ou de ville dans votre question. Précisez la destination (ex. « Quelle tenue porter en Indonésie ? »), ou ouvrez d'abord la fiche d'un pays.</p>`
      : `<p>I could not recognise a country or city. Please name the destination, or open a country card first.</p>`;
    const out = [];
    const all = intents.length ? intents : ['security', 'culture', 'emergency'];
    det.isos.forEach(iso => {
      const c = collect(iso, det, all);
      const g = c.guide, p = c.practical, meae = c.adv['MEAE (France)'];
      const parts = [`<h4>${flagImg(iso)}${esc(c.name)} — ${t('risk_level')} ${c.level || '?'} · ${esc(c.levelLabel)}</h4>`];
      if (all.includes('security') || all.includes('route')) {
        parts.push(li(Object.entries(c.adv).map(([s, a]) => `<strong>${esc(s)}</strong> : ${esc(a.label || '')}`)));
        if (meae && (meae.excerpt || []).length) parts.push(`<blockquote>${meae.excerpt.slice(0, 3).map(x => `« ${esc(x)} »`).join('<br>')}</blockquote>`);
      }
      if (all.includes('route')) {
        if (c.corridor) parts.push(`<p><strong>${esc(c.corridor.from)} → ${esc(c.corridor.to)}</strong> (~${c.corridor.km} km ${fr ? 'à vol d\'oiseau' : 'as the crow flies'})</p>`);
        parts.push(`<p><strong>${fr ? 'Recommandations' : 'Recommendations'}</strong></p>` + li(routeAdvice(c.level || 2).map(esc)));
      }
      if (all.includes('security') || all.includes('route')) {
        parts.push(`<p><strong>${fr ? 'Incidents récents' : 'Recent incidents'} (30 ${fr ? 'j' : 'd'}${c.corridor ? (fr ? ', le long de l\'axe' : ', along the route') : ''}) : ${c.nEvents}</strong></p>`
          + li(c.events.slice(0, 5).map(e => `<a href="#" data-buddy-event="${esc(e.id)}">${esc(e.title)}</a> <span class="muted">— ${esc(e.place || '')}, ${esc(ago(e.date))}</span>`)));
      }
      if (all.includes('dress') || all.includes('women')) parts.push(`<p><strong>${fr ? 'Tenue' : 'Dress'}</strong></p>` + li((g.tenue || []).map(esc)));
      if (all.includes('women')) parts.push(`<p><strong>${fr ? 'Voyageuses' : 'Women travellers'}</strong></p>` + li((g.voyageuses || []).map(esc)));
      if (all.includes('culture')) ['religion', 'gestes', 'salutations', 'affaires', 'interdits'].forEach(k => {
        if ((g[k] || []).length && (intents.length === 0 || new RegExp({ religion: 'religion|ramadan', gestes: 'geste', salutations: 'salu|greet|poignee', affaires: 'affaire|business|cadeau|gift', interdits: 'interdit|alcool|photo|loi' }[k]).test(norm(q)) || !/religion|ramadan|geste|salu|greet|affaire|business|cadeau|gift|interdit|alcool|photo/.test(norm(q))))
          parts.push(`<p><strong>${esc({ religion: 'Religion', gestes: fr ? 'Gestes à éviter' : 'Gestures', salutations: fr ? 'Salutations' : 'Greetings', affaires: fr ? 'Affaires' : 'Business', interdits: fr ? 'Interdits' : 'Red lines' }[k])}</strong></p>` + li(g[k].map(esc)));
      });
      if (all.includes('health')) {
        const h = (meae && meae.health) || [];
        parts.push(`<p><strong>${fr ? 'Santé' : 'Health'}</strong></p>` + li([
          ...h.slice(0, 4).map(x => `« ${esc(x)} » <span class="muted">(MEAE)</span>`),
          h.length ? '' : esc(fr ? 'Vaccins : consultez un centre de vaccinations internationales 4 à 6 semaines avant le départ (vaccins recommandés ou obligatoires selon la destination, prévention du paludisme).' : 'Vaccines: see a travel clinic 4–6 weeks before departure.'),
          ...c.hospitals.slice(0, 3).map(x => `${esc(x.name)}${x.city ? ' (' + esc(x.city) + ')' : ''}`)]));
      }
      if (all.includes('emergency') || all.includes('health')) parts.push(`<p><strong>${fr ? 'Urgences' : 'Emergency'}</strong> : ${esc((p.emergency || []).join(' · ') || '—')} · ${fr ? 'indicatif' : 'code'} ${esc((p.calling_code || []).join(', ') || '—')}</p>`);
      if (all.includes('telecom')) parts.push(`<p><strong>${fr ? 'Télécoms' : 'Telecoms'}</strong> : ${esc((p.operators || []).join(', ') || '—')} · ${fr ? 'prises' : 'plugs'} ${esc((p.plugs || []).join(', ') || '—')} · ${esc((p.voltage || []).join('/'))} V</p>`);
      if (all.includes('providers') || (all.includes('route') && (c.level || 0) >= 3)) parts.push(`<p><strong>${fr ? 'Prestataires (sécurité / évacuation)' : 'Providers (security / evacuation)'}</strong></p>` + li(c.provs.map(pv => `<a href="${esc(pv.web)}" target="_blank" rel="noopener">${esc(pv.name)}</a>`)));
      parts.push(`<p class="muted"><a href="report.html#${iso}" target="_blank" rel="noopener">${fr ? 'Rapport pays complet (PDF)' : 'Full country report (PDF)'}</a></p>`);
      out.push(parts.join(''));
    });
    return out.join('<hr>') + `<p class="muted">${fr ? 'Réponse construite à partir des données Angor (avis officiels, incidents, fiches) — à vérifier avant décision.' : 'Answer built from Angor data — verify before deciding.'}</p>`;
  }
  function mdToHtml(md) {
    let h = esc(md).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/^#{1,4} (.+)$/gm, '<h4>$1</h4>');
    h = h.replace(/(?:^|\n)((?:[-•] .+(?:\n|$))+)/g, (m, block) => `\n<ul>${block.trim().split('\n').map(l => `<li>${l.replace(/^[-•] /, '')}</li>`).join('')}</ul>\n`);
    return h.split(/\n{2,}/).map(p => /^\s*<(ul|h4)/.test(p) ? p : `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
  }
  async function ask(q) {
    await ensureBuddyData();
    const det = detect(q), intents = intentsOf(q);
    if (!BUDDY_URL || !det.isos.length) return { html: localAnswer(q, det, intents), mode: 'local' };
    const ctx = det.isos.map(iso => contextText(collect(iso, det, intents.length ? intents : ['security']))).join('\n\n').slice(0, 14000);
    try {
      const r = await fetch(BUDDY_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ q, lang: state.lang, context: ctx, history: buddy.log.slice(-4).map(m => ({ role: m.role, content: m.text.slice(0, 1500) })) }) });
      const j = await r.json();
      if (!r.ok || !j.answer) throw new Error(j.error || r.status);
      return { html: mdToHtml(j.answer), mode: 'ai', text: j.answer };
    } catch (e) {
      return { html: `<p class="muted">${t('buddy_ai_down')}</p>` + localAnswer(q, det, intents), mode: 'local' };
    }
  }
  function renderBuddy() {
    const log = $('#buddy-log');
    if (!log) return;
    log.innerHTML = buddy.log.length ? buddy.log.map(m => m.role === 'user'
      ? `<div class="bmsg me">${esc(m.text)}</div>`
      : `<div class="bmsg bot">${m.html}${m.mode ? `<div class="bmode">${esc(t('buddy_mode_' + m.mode))}</div>` : ''}</div>`).join('')
      + (buddy.busy ? `<div class="bmsg bot typing">${esc(t('buddy_thinking'))}</div>` : '')
      : `<div class="bmsg bot">${esc(t('buddy_hello'))}</div>`;
    log.scrollTop = log.scrollHeight;
    $('#buddy-suggest').innerHTML = buddy.log.length ? '' : t('buddy_examples').map(x => `<button type="button" class="chip">${esc(x)}</button>`).join('');
    $('#buddy-mode').textContent = BUDDY_URL ? t('buddy_ai_on') : t('buddy_ai_off');
  }
  async function sendBuddy(q) {
    q = (q || '').trim();
    if (!q || buddy.busy) return;
    buddy.log.push({ role: 'user', text: q }); buddy.busy = true; renderBuddy();
    const a = await ask(q);
    buddy.busy = false;
    buddy.log.push({ role: 'assistant', html: a.html, text: a.text || '', mode: a.mode });
    renderBuddy();
  }
  function bindBuddy() {
    $('#buddy-form').addEventListener('submit', ev => { ev.preventDefault(); const v = $('#buddy-input').value; $('#buddy-input').value = ''; sendBuddy(v); });
    $('#buddy-input').addEventListener('keydown', ev => { if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); $('#buddy-form').requestSubmit(); } });
    $('#buddy-suggest').addEventListener('click', ev => { const b = ev.target.closest('.chip'); if (b) sendBuddy(b.textContent); });
    $('#buddy-log').addEventListener('click', ev => { const a = ev.target.closest('[data-buddy-event]'); if (a) { ev.preventDefault(); openEvent(a.dataset.buddyEvent); } });
    $('#buddy-clear').addEventListener('click', () => { buddy.log = []; renderBuddy(); });
  }

  /* ------------------------------------------------------------------ démarrage */
  if (D && D.settings && D.settings.product_name) { $('#brand-name').textContent = D.settings.product_name; document.title = D.settings.product_name; }
  computeProximity();
  applyI18n();
  applyTheme();
  riskLayer.addTo(map); cluster.addTo(map); sitesLayer.addTo(map);
  bind();
  bindBuddy();
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
