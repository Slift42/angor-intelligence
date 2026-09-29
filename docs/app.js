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
      m_map: 'Carte', m_alerts: 'Alertes', m_ongoing: 'En cours', m_travel: 'Voyage', m_more: 'Plus', m_account: 'Mon compte', m_admin: 'Administration',
      m_install: 'Installer l’application', layers_btn: 'Couches', offline: d => `Hors ligne : dernière situation enregistrée (${d}).`,
      sc_title: 'Safety check', sc_safe: 'Je suis en sécurité', sc_help: 'J’ai besoin d’aide', sc_nc: 'Pas concerné', sc_later: 'Plus tard',
      sc_done: 'Réponse envoyée. Merci.', sc_err: 'Réponse non envoyée : vérifiez votre connexion.', sc_launch: 'Lancer un safety check',
      acc_login: 'Se connecter', acc_pending: 'Compte en attente de validation',
      tab_agenda: 'Agenda', help: 'Aide',
      chrono_title: 'Chronologies de crise (30 j)', chrono_n: (a, b) => `${a} active${a > 1 ? 's' : ''} · ${b} au total`, chrono_all: 'Toutes', chrono_active: 'Actives',
      chrono_none: 'Aucune chronologie sur la période.', trend: { escalating: 'Escalade', stable: 'Stable', declining: 'Décrue', new: 'Nouvelle' },
      status_active: 'Active', status_calmed: 'Apaisée', chrono_days: n => `${n} jour${n > 1 ? 's' : ''}`, chrono_inc: n => `${n} incident${n > 1 ? 's' : ''}`,
      chrono_show: 'Afficher sur la carte', chrono_focus: t2 => `Chronologie affichée : ${t2}`, chrono_exit: 'Revenir à toutes les alertes',
      chrono_part: 'Fait partie de la chronologie', chrono_daily: 'Incidents par jour', chrono_timeline: 'Chronologie', sum_ai_crisis: 'Synthèse IA – à vérifier',
      n_sources: n => `${n} source${n > 1 ? 's' : ''}`, peak: 'Pic', max_sev: 'Gravité max',
      ag_hint: 'Jours fériés, élections et référendums nationaux, grandes fêtes religieuses et échéances ajoutées par l’analyste. Les rassemblements et fermetures peuvent perturber vos déplacements.',
      ag_range: { 7: '7 jours', 30: '30 jours', 90: '3 mois', 365: '12 mois' }, ag_scope_all: 'Tous les pays', ag_scope_watch: 'Mes pays suivis',
      ag_types: { holiday: 'Fériés', election: 'Élections', religious: 'Religieux', other: 'Analyste' }, ag_empty: 'Rien de prévu sur la période.',
      ag_loading: 'Chargement de l’agenda…', ag_missing: 'Agenda pas encore disponible : il sera créé à la prochaine collecte.',
      ag_world: 'Monde', ag_muslim: 'Pays à majorité musulmane', ag_month: 'date à préciser dans le mois', ag_year: 'Échéances sans date précise',
      ag_type: { holiday: 'Jour férié', election: 'Élection', religious: 'Fête religieuse', strike: 'Grève', summit: 'Sommet', anniversary: 'Anniversaire sensible', sport: 'Sport', other: 'Échéance' },
      upcoming: 'À venir (90 j)', no_upcoming: 'Rien de prévu dans nos sources.',
      corridors: 'Trajets surveillés', add_corridor: 'Ajouter un trajet', cor_from: 'Départ (ville)', cor_to: 'Arrivée (ville)', cor_via: 'Étapes (facultatif, séparées par des virgules)',
      cor_buffer: 'Largeur de vigilance de part et d’autre (km)', cor_name: 'Nom du trajet', cor_draw: 'Tracer sur la carte', cor_draw_hint: 'Cliquez les étapes du trajet sur la carte, puis « Terminer ».',
      cor_finish: 'Terminer', cor_points: n => `${n} point${n > 1 ? 's' : ''}`, cor_saved: 'Trajet enregistré dans ce navigateur', cor_city_err: c => `Ville non reconnue : ${c}. Essayez une grande ville proche, ou tracez le trajet sur la carte.`,
      cor_km: n => `≈ ${n} km`, cor_hits: n => n ? `${n} alerte${n > 1 ? 's' : ''} le long du trajet` : 'Aucune alerte le long du trajet', cor_watch: 'Surveiller ce trajet',
      cor_hint: 'Un trajet surveillé est une bande de vigilance autour d’un itinéraire (ex. Lagos – Abuja). Les incidents dans cette bande sont signalés comme pour vos sites.',
      on_route: 'trajet',
      gng_open: 'Go / no-go guidé', gng_title: 'Go / no-go guidé', gng_intro: 'Répondez aux questions : la menace est calculée à partir des données Angor, la vulnérabilité à partir de vos réponses.',
      gng_country: 'Pays', gng_city: 'Ville principale', gng_from: 'Départ', gng_to: 'Retour', gng_eval: 'Évaluer', gng_cancel: 'Annuler',
      gng_threat: 'Menace', gng_vuln: 'Vulnérabilité', gng_resid: 'Risque résiduel', gng_factors: 'Facteurs de menace (données Angor)', gng_conditions: 'Conditions à remplir avant le départ',
      gng_noconds: 'Aucune condition supplémentaire : appliquer les mesures standard.', gng_brief: 'Ouvrir le brief de mission (avec cette évaluation)', gng_ai: 'Avis rédigé par l’IA',
      gng_disclaimer: 'Évaluation indicative : la décision finale revient au responsable sûreté ou à la direction.',
      pulse: 'Pulse', pulse_title: 'Pulse – indice de stabilité', cl_pulse: 'Pulse (stabilité)', legend_pulse: 'Pulse – stabilité (0 à 100)',
      pulse_hint: 'De 0 (très instable) à 100 (stable). Suit la dynamique : avis officiels, activité sécuritaire des 7 derniers jours, anomalie par rapport aux 3 semaines précédentes, catastrophes.',
      pulse_drivers: 'Causes principales', pulse_none: 'Pas de variation notable.', pulse_na: 'Tendance disponible après 7 jours d’historique.',
      drv_cat: (c, d) => `Hausse : ${c} (+${d} pts pondérés en 7 j)`, drv_adv: (s, a, b, d) => `Avis ${s} : niveau ${a} → ${b} (${d})`,
      pulse_scale: ['Très instable', 'Instable', 'Fragile', 'Plutôt stable', 'Stable'],
      sort_risk: 'Risque', sort_pulse: 'Pulse (plus instables)', sort_move: 'Pulse (plus forte baisse)',
      adm: 'Cotation', adm_title: 'Cotation (grille de l’Amirauté)', adm_rel: { A: 'Source totalement fiable', B: 'Source habituellement fiable', C: 'Source assez fiable', D: 'Source pas toujours fiable', E: 'Source peu fiable', F: 'Fiabilité inconnue' },
      adm_cred: { 1: 'information confirmée', 2: 'probablement vraie', 3: 'possiblement vraie', 4: 'douteuse', 5: 'improbable', 6: 'invérifiable' },
      adm_note: 'Lettre = fiabilité de la source, chiffre = crédibilité de l’information (grille OTAN, A1 à F6). Cotation automatique, corrigée par l’analyste.',
      verified: 'Vérifié Angor', verified_notice: d => `Incident vérifié par un analyste Angor${d ? ' le ' + d : ''}.`, corrected_notice: 'Fiche corrigée par l’analyste.',
      only_verified: 'Uniquement les incidents vérifiés Angor', only_watch: 'Uniquement mes pays suivis',
      watch_add: 'Suivre ce pays', watch_remove: 'Ne plus suivre ce pays', watch_filter: 'Suivis', watch_copy: 'Copier pour Telegram',
      watch_copied: 'Liste copiée : collez-la dans config/settings.json → "digest" → "countries", puis publier.bat. Le point quotidien Telegram suivra ces pays.',
      watch_empty: 'Aucun pays suivi : cliquez sur l’étoile dans la fiche d’un pays.', watch_added: 'Pays ajouté à vos pays suivis', watch_removed: 'Pays retiré de vos pays suivis',
      share: 'Partager', share_done: 'Lien copié : il ouvre la carte avec la même vue et les mêmes filtres.', views: 'Vues', views_title: 'Vues enregistrées',
      view_ph: 'Nom de la vue (ex. Sahel – 7 j)', view_save: 'Enregistrer la vue actuelle', views_empty: 'Aucune vue enregistrée.', view_saved: 'Vue enregistrée dans ce navigateur', view_link: 'Copier le lien',
      brief: 'Brief de mission',
      an_mode: 'Mode analyste', an_valid: 'Valider', an_false: 'Infirmer', an_fix: 'Corriger', an_reset: 'Annuler ma décision', an_note: 'Note : source de confirmation, commentaire…',
      an_export: n => `Exporter verified.json (${n})`, an_exit: 'Quitter', an_done: 'Fichier téléchargé : remplacez config/verified.json par ce fichier, puis double-cliquez sur publier.bat.',
      an_status: { verified: 'Validé', false: 'Infirmé', corrected: 'Corrigé' }, an_local: 'Décision enregistrée dans ce navigateur – à exporter', an_hint: 'Vos décisions s’appliquent tout de suite ici ; exportez-les pour les publier sur angor.fr.',
      an_sev: 'Gravité', an_cat: 'Catégorie',
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
      m_map: 'Map', m_alerts: 'Alerts', m_ongoing: 'Ongoing', m_travel: 'Travel', m_more: 'More', m_account: 'My account', m_admin: 'Administration',
      m_install: 'Install the app', layers_btn: 'Layers', offline: d => `Offline: last saved situation (${d}).`,
      sc_title: 'Safety check', sc_safe: 'I am safe', sc_help: 'I need help', sc_nc: 'Not concerned', sc_later: 'Later',
      sc_done: 'Answer sent. Thank you.', sc_err: 'Answer not sent: check your connection.', sc_launch: 'Launch a safety check',
      acc_login: 'Sign in', acc_pending: 'Account awaiting approval',
      tab_agenda: 'Agenda', help: 'Help',
      chrono_title: 'Crisis timelines (30 d)', chrono_n: (a, b) => `${a} active · ${b} in total`, chrono_all: 'All', chrono_active: 'Active',
      chrono_none: 'No timeline over the period.', trend: { escalating: 'Escalating', stable: 'Stable', declining: 'Declining', new: 'New' },
      status_active: 'Active', status_calmed: 'Calmed', chrono_days: n => `${n} day${n > 1 ? 's' : ''}`, chrono_inc: n => `${n} incident${n > 1 ? 's' : ''}`,
      chrono_show: 'Show on map', chrono_focus: t2 => `Timeline shown: ${t2}`, chrono_exit: 'Back to all alerts',
      chrono_part: 'Part of the timeline', chrono_daily: 'Incidents per day', chrono_timeline: 'Timeline', sum_ai_crisis: 'AI summary – to be verified',
      n_sources: n => `${n} source${n > 1 ? 's' : ''}`, peak: 'Peak', max_sev: 'Max severity',
      ag_hint: 'Public holidays, national elections and referendums, major religious festivals and analyst-added dates. Gatherings and closures may disrupt travel.',
      ag_range: { 7: '7 days', 30: '30 days', 90: '3 months', 365: '12 months' }, ag_scope_all: 'All countries', ag_scope_watch: 'My followed countries',
      ag_types: { holiday: 'Holidays', election: 'Elections', religious: 'Religious', other: 'Analyst' }, ag_empty: 'Nothing scheduled over the period.',
      ag_loading: 'Loading agenda…', ag_missing: 'Agenda not available yet: it will be created at the next collection.',
      ag_world: 'World', ag_muslim: 'Muslim-majority countries', ag_month: 'date to be confirmed within the month', ag_year: 'Dates not yet set',
      ag_type: { holiday: 'Public holiday', election: 'Election', religious: 'Religious festival', strike: 'Strike', summit: 'Summit', anniversary: 'Sensitive anniversary', sport: 'Sport', other: 'Event' },
      upcoming: 'Upcoming (90 d)', no_upcoming: 'Nothing scheduled in our sources.',
      corridors: 'Watched routes', add_corridor: 'Add a route', cor_from: 'From (city)', cor_to: 'To (city)', cor_via: 'Waypoints (optional, comma-separated)',
      cor_buffer: 'Watch width on each side (km)', cor_name: 'Route name', cor_draw: 'Draw on map', cor_draw_hint: 'Click the route waypoints on the map, then “Finish”.',
      cor_finish: 'Finish', cor_points: n => `${n} point${n > 1 ? 's' : ''}`, cor_saved: 'Route saved in this browser', cor_city_err: c => `City not recognised: ${c}. Try a nearby large city, or draw the route on the map.`,
      cor_km: n => `≈ ${n} km`, cor_hits: n => n ? `${n} alert${n > 1 ? 's' : ''} along the route` : 'No alert along the route', cor_watch: 'Watch this route',
      cor_hint: 'A watched route is a vigilance band around an itinerary (e.g. Lagos – Abuja). Incidents in the band are flagged like your sites.',
      on_route: 'route',
      gng_open: 'Guided go / no-go', gng_title: 'Guided go / no-go', gng_intro: 'Answer the questions: threat is computed from Angor data, vulnerability from your answers.',
      gng_country: 'Country', gng_city: 'Main city', gng_from: 'Departure', gng_to: 'Return', gng_eval: 'Assess', gng_cancel: 'Cancel',
      gng_threat: 'Threat', gng_vuln: 'Vulnerability', gng_resid: 'Residual risk', gng_factors: 'Threat factors (Angor data)', gng_conditions: 'Conditions to meet before departure',
      gng_noconds: 'No additional condition: apply standard measures.', gng_brief: 'Open the mission brief (with this assessment)', gng_ai: 'AI-written opinion',
      gng_disclaimer: 'Indicative assessment: the final decision lies with the security manager or management.',
      pulse: 'Pulse', pulse_title: 'Pulse – stability index', cl_pulse: 'Pulse (stability)', legend_pulse: 'Pulse – stability (0 to 100)',
      pulse_hint: 'From 0 (very unstable) to 100 (stable). Tracks momentum: official advisories, security activity over 7 days, anomaly versus the previous 3 weeks, hazards.',
      pulse_drivers: 'Main drivers', pulse_none: 'No significant change.', pulse_na: 'Trend available after 7 days of history.',
      drv_cat: (c, d) => `Rise: ${c} (+${d} weighted pts in 7 d)`, drv_adv: (s, a, b, d) => `${s} advisory: level ${a} → ${b} (${d})`,
      pulse_scale: ['Very unstable', 'Unstable', 'Fragile', 'Fairly stable', 'Stable'],
      sort_risk: 'Risk', sort_pulse: 'Pulse (least stable)', sort_move: 'Pulse (biggest drop)',
      adm: 'Rating', adm_title: 'Rating (Admiralty grading)', adm_rel: { A: 'Completely reliable source', B: 'Usually reliable source', C: 'Fairly reliable source', D: 'Not usually reliable source', E: 'Unreliable source', F: 'Reliability unknown' },
      adm_cred: { 1: 'confirmed', 2: 'probably true', 3: 'possibly true', 4: 'doubtful', 5: 'improbable', 6: 'cannot be judged' },
      adm_note: 'Letter = source reliability, digit = information credibility (NATO grading, A1 to F6). Automatic rating, corrected by the analyst.',
      verified: 'Angor verified', verified_notice: d => `Incident verified by an Angor analyst${d ? ' on ' + d : ''}.`, corrected_notice: 'Record corrected by the analyst.',
      only_verified: 'Angor-verified incidents only', only_watch: 'My followed countries only',
      watch_add: 'Follow this country', watch_remove: 'Unfollow this country', watch_filter: 'Followed', watch_copy: 'Copy for Telegram',
      watch_copied: 'List copied: paste it into config/settings.json → "digest" → "countries", then publier.bat. The daily Telegram digest will follow these countries.',
      watch_empty: 'No followed country: click the star on a country card.', watch_added: 'Country added to your followed countries', watch_removed: 'Country removed from your followed countries',
      share: 'Share', share_done: 'Link copied: it opens the map with the same view and filters.', views: 'Views', views_title: 'Saved views',
      view_ph: 'View name (e.g. Sahel – 7 d)', view_save: 'Save current view', views_empty: 'No saved view.', view_saved: 'View saved in this browser', view_link: 'Copy link',
      brief: 'Mission brief',
      an_mode: 'Analyst mode', an_valid: 'Validate', an_false: 'Reject', an_fix: 'Correct', an_reset: 'Undo my decision', an_note: 'Note: confirming source, comment…',
      an_export: n => `Export verified.json (${n})`, an_exit: 'Exit', an_done: 'File downloaded: replace config/verified.json with it, then double-click publier.bat.',
      an_status: { verified: 'Validated', false: 'Rejected', corrected: 'Corrected' }, an_local: 'Decision saved in this browser – export it', an_hint: 'Your decisions apply here immediately; export them to publish on angor.fr.',
      an_sev: 'Severity', an_cat: 'Category',
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
  const GROUP_COLORS = { security: '#B0182E', political: '#E0A21B', natural: '#3F86C6', health: '#7D5BA6', infrastructure: '#5E6B78', diplomatic: '#4B6BAF' };

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
    countryLayer: (v => ['risk', 'pulse', 'meae', 'fcdo', 'us', 'none'].includes(v) ? v : 'risk')(store.get('vs-clayer', 'risk')),
    onlyVerified: false, onlyWatch: false, countrySort: 'risk', watch: new Set(store.get('vs-watch', [])),
    localCorridors: store.get('vs-corridors', []), drawing: null, crisisFocus: null, chronoAll: false,
    agRange: 30, agScope: 'all', agTypes: new Set(['holiday', 'election', 'religious', 'other']),
    analyst: /[?&]analyste?=1/.test(location.search) || store.get('vs-analyst', false)
  };
  const PULSE = (D && D.pulse) || {};
  const CRISES = (D && D.crises) || [];
  const CRISIS_OF = {};
  CRISES.forEach(c => c.events.forEach(id => { if (!CRISIS_OF[id] || CRISIS_OF[id].status !== 'active') CRISIS_OF[id] = c; }));
  const AI_URL = (D && D.settings && (D.settings.ai_url || D.settings.buddy_url)) || '';
  /** Appel au relais IA (Cloudflare Worker) pour une tâche : buddy, gonogo, brief. Lève une erreur si indisponible. */
  async function aiCall(task, q, context, history) {
    if (!AI_URL) throw new Error('no_ai');
    const r = await fetch(AI_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task, q, lang: state.lang, context: String(context || '').slice(0, 14000), history: history || [] }) });
    const j = await r.json();
    if (!r.ok || !j.answer) throw new Error(j.error || r.status);
    return j.answer;
  }
  /* ------------------------------------------------------------------ liens partageables (paramètres d'URL) */
  const PARAMS = new URLSearchParams(location.search);
  (function applyParams() {
    const P = PARAMS;
    if (P.has('h')) { const h = P.get('h'); state.hours = h === 'all' ? 'all' : (+h || state.hours); }
    if (P.get('from') && P.get('to')) state.range = { from: P.get('from'), to: P.get('to') };
    if (P.has('sev')) { const v = P.get('sev'); state.sev = { 1: v.includes('1'), 2: v.includes('2'), 3: v.includes('3'), 4: v.includes('4') }; }
    if (P.has('cats')) { const c = P.get('cats').split(',').filter(k => TAX.categories[k]); if (c.length) state.cats = new Set(c); }
    if (P.has('auto')) state.hideAuto = P.get('auto') === '0';
    if (P.get('verified') === '1') state.onlyVerified = true;
    if (P.get('watch') === '1') state.onlyWatch = true;
    if (P.has('watchlist')) P.get('watchlist').split(',').filter(x => /^[A-Z]{2}$/.test(x)).forEach(x => state.watch.add(x));
    if (['risk', 'pulse', 'meae', 'fcdo', 'us', 'none'].includes(P.get('layer'))) state.countryLayer = P.get('layer');
    if (BASEMAPS.includes(P.get('base'))) state.basemap = P.get('base');
    if (['fr', 'en'].includes(P.get('lang'))) state.lang = P.get('lang');
    if (['alerts', 'ongoing', 'countries', 'news', 'sites', 'buddy', 'agenda'].includes(P.get('tab'))) state.tab = P.get('tab');
    if (P.get('focus')) state.crisisFocus = P.get('focus');
    if (P.get('analyste') === '0') state.analyst = false;
    try { localStorage.setItem('vs-analyst', JSON.stringify(state.analyst)); } catch (e) { /* stockage indisponible */ }
  })();

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
  const isAuto = e => (e.tags || []).includes('auto-detected') && !e.verified;
  const hostOf = u => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return ''; } };

  const countryProps = {};
  COUNTRIES.features.forEach(f => { countryProps[f.properties.iso2] = f.properties; });
  const countryName = iso => iso && countryProps[iso] ? countryProps[iso]['name_' + state.lang] : '';
  const pulseColor = v => v < 25 ? '#9E1B32' : v < 45 ? '#E0592A' : v < 65 ? '#E3B505' : v < 80 ? '#8DBF4E' : '#2E9E5B';
  const pulseLabel = v => t('pulse_scale')[v < 25 ? 0 : v < 45 ? 1 : v < 65 ? 2 : v < 80 ? 3 : 4];
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
  function allCorridors() {
    const cfg = ((D && D.corridors) || []).map((c, i) => ({ ...c, kind: 'corridor', origin: 'config', key: 'k' + i, radius_km: c.buffer_km || 25 }));
    const loc = state.localCorridors.map((c, i) => ({ ...c, kind: 'corridor', origin: 'local', key: 'r' + i, radius_km: c.buffer_km || 25 }));
    return cfg.concat(loc);
  }
  /** Distance (km) d'un point à un trajet : projection locale sur chaque segment. */
  function routeKm(lat, lon, pts) {
    let best = Infinity;
    const k = Math.cos(lat * Math.PI / 180);
    for (let i = 0; i < pts.length - 1; i++) {
      const ax = (pts[i][1] - lon) * 111.32 * k, ay = (pts[i][0] - lat) * 110.57, bx = (pts[i + 1][1] - lon) * 111.32 * k, by = (pts[i + 1][0] - lat) * 110.57;
      const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
      const tt = l2 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / l2)) : 0;
      best = Math.min(best, Math.hypot(ax + tt * dx, ay + tt * dy));
    }
    return best;
  }
  const routeLength = pts => Math.round(pts.slice(1).reduce((n, p, i) => n + haversine(pts[i][0], pts[i][1], p[0], p[1]), 0));
  function computeProximity() {
    const sites = allSites().concat(allCorridors());
    EVENTS.forEach(e => {
      e._t = Math.min(Date.parse(e.date), Date.now());
      e._near = e.lat == null ? [] : sites.map(s => ({ site: s, d: s.points ? routeKm(e.lat, e.lon, s.points) : haversine(s.lat, s.lon, e.lat, e.lon) }))
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
      layer.on('click', ev => { if (state.picking || state.drawing) return; L.DomEvent.stopPropagation(ev); openCountry(f.properties.iso2); });
      layer.on('mouseover', () => { if (!state.picking) layer.setStyle({ weight: 1.6, color: cssVar('--ink-2') }); });
      layer.on('mouseout', () => riskLayer.resetStyle(layer));
      // pas d'étiquette au survol : seul le contour du pays est surligné (clic = fiche pays)
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
    if (mode === 'pulse') {
      const p = PULSE[iso];
      return { fillColor: p ? pulseColor(p.value) : '#9AA5B1', fillOpacity: p ? (dark ? 0.42 : 0.5) * k : 0.04, color: line, weight: 0.7, dashArray: null };
    }
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
  const baseFilter = e => (!state.onlyOngoing || isOngoing(e)) && inWindow(e) && state.cats.has(e.category) && !(state.hideAuto && isAuto(e)) && !(state.onlySites && !e._near.length)
    && !(e._false && !state.analyst) && !(state.onlyVerified && !e.verified) && !(state.onlyWatch && !state.watch.has(e.country));
  const visible = () => state.crisisFocus ? EVENTS.filter(e => (CRISES.find(c => c.id === state.crisisFocus) || { events: [] }).events.includes(e.id))
    : EVENTS.filter(e => baseFilter(e) && state.sev[e.severity]);
  const sorted = list => list.slice().sort(state.sort === 'severity'
    ? (a, b) => b.severity - a.severity || b._t - a._t
    : (a, b) => b._t - a._t || b.severity - a.severity);

  /* ------------------------------------------------------------------ rendu */
  function renderAll() {
    const list = visible();
    renderSevSummary(); renderFilters(); renderAlerts(list); renderMap(list);
    renderCountries(); renderNews(); renderSites(); renderOngoing(); renderChrono(); renderLegend(); renderHealth(); renderTabs();
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

  const crisisTitle = c => state.lang === 'fr' ? c.title : (c.title_en || c.title);
  function dailyBars(c, w = 120, h = 26) {
    const days = [];
    for (let d = new Date(c.start.slice(0, 10) + 'T12:00:00Z'); d.toISOString().slice(0, 10) <= c.last.slice(0, 10); d.setUTCDate(d.getUTCDate() + 1)) days.push(d.toISOString().slice(0, 10));
    const mx = Math.max(...days.map(d => (c.daily[d] || [0])[0]), 1), bw = w / days.length;
    return `<svg class="bars" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" preserveAspectRatio="none">${days.map((d, i) => { const v = (c.daily[d] || [0, 0]); const bh = Math.max(v[0] ? 2 : 0, v[0] / mx * (h - 2));
      return `<rect x="${(i * bw + 0.5).toFixed(1)}" y="${(h - bh).toFixed(1)}" width="${Math.max(1, bw - 1).toFixed(1)}" height="${bh.toFixed(1)}" fill="${v[1] ? sevColor(v[1]) : 'transparent'}"><title>${d} : ${v[0]}</title></rect>`; }).join('')}</svg>`;
  }
  const trendChip = c => `<span class="trend t-${c.status === 'calmed' ? 'calmed' : c.trend}">${esc(c.status === 'calmed' ? t('status_calmed') : t('trend')[c.trend])}</span>`;
  function renderChrono() {
    const list = CRISES.filter(c => state.chronoAll || c.status === 'active').filter(c => !(state.onlyWatch && !state.watch.has(c.country)));
    $('#chrono-count').textContent = t('chrono_n', CRISES.filter(c => c.status === 'active').length, CRISES.length);
    $('#chrono-all').textContent = state.chronoAll ? t('chrono_active') : t('chrono_all');
    $('#chrono-list').innerHTML = list.length ? list.map(c => `<li class="chrono" data-crisis="${c.id}">
      <span class="lvl" style="background:${sevColor(c.max_severity)}">${c.n}</span>
      <div><div class="n">${flagImg(c.country)}${esc(crisisTitle(c))}</div>
        <div class="s">${esc(fmtDay(c.start.slice(0, 10)))} → ${esc(fmtDay(c.last.slice(0, 10)))} · ${esc(t('chrono_days', Object.keys(c.daily).length))} ${trendChip(c)}</div></div>
      ${dailyBars(c, 70, 22)}</li>`).join('') : `<li class="empty">${t('chrono_none')}</li>`;
  }
  function openCrisis(id, fly = true) {
    const c = CRISES.find(x => x.id === id); if (!c) return;
    closeAnalytics();
    const evs = EVENTS.filter(e => c.events.includes(e.id)).sort((a, b) => b._t - a._t);
    const byDay = {};
    evs.forEach(e => { (byDay[e.date.slice(0, 10)] = byDay[e.date.slice(0, 10)] || []).push(e); });
    if (fly) map.flyToBounds([[c.bbox[0], c.bbox[1]], [c.bbox[2], c.bbox[3]]], { padding: [60, 60], maxZoom: 9, duration: 0.8 });
    const sum = state.lang === 'fr' ? c.summary_fr : c.summary_en;
    openDrawer(`<div class="d-head">
        <div class="d-kicker">${icon('activity', 14)} ${esc(t('chrono_timeline'))} · ${trendChip(c)}</div>
        <h2 class="d-title">${flagImg(c.country, 26)}${esc(crisisTitle(c))}</h2>
        <div class="d-sum"><p class="d-desc">${esc(sum)}</p><span class="d-sum-kind">${esc(c.summary_kind === 'ai' ? t('sum_ai_crisis') : t('sum_auto'))}</span></div>
        <div class="site-actions"><button class="btn primary" data-focus="${c.id}">${icon('map', 15)}${esc(t('chrono_show'))}</button>
          <a class="btn" href="#" data-country="${c.country}">${icon('globe', 15)}${esc(countryName(c.country))}</a></div>
      </div>
      <div class="d-sec"><div class="stats">
        <div class="stat"><div class="n">${c.n}</div><div class="l">${esc(t('incidents'))}</div></div>
        <div class="stat"><div class="n">${Object.keys(c.daily).length}</div><div class="l">${esc(t('chrono_days', Object.keys(c.daily).length).replace(/^\d+ /, ''))}</div></div>
        <div class="stat"><div class="n">${c.n_sources}</div><div class="l">${esc(t('sources'))}</div></div>
        <div class="stat"><div class="n" style="color:${sevColor(c.max_severity)}">${c.max_severity}/4</div><div class="l">${esc(t('max_sev'))}</div></div></div></div>
      <div class="d-sec"><h3>${t('chrono_daily')}</h3>${dailyBars(c, 320, 60)}<div class="hint">${esc(t('peak'))} : ${esc(fmtDay(c.peak))} · ${esc((c.places || []).join(', '))}</div></div>
      <div class="d-sec"><h3>${t('chrono_timeline')}</h3><div class="timeline">${Object.entries(byDay).map(([d, list]) => `<div class="tl-day"><div class="tl-date">${esc(fmtDay(d))}</div>
        <ul class="mini-list">${list.map(e => `<li data-event="${esc(e.id)}"><span class="dot" style="background:${sevColor(e.severity)}"></span><span class="t">${esc(e.title)}<br><span class="muted small">${esc(new Date(e.date).toLocaleTimeString(state.lang === 'fr' ? 'fr-FR' : 'en-GB', { hour: '2-digit', minute: '2-digit' }))} · ${esc(e.place || '')}</span></span><span class="w">${admBadge(e)}</span></li>`).join('')}</ul></div>`).join('')}</div></div>`, 'crisis', id);
  }
  function focusCrisis(id) {
    state.crisisFocus = id; state.tab = 'alerts'; renderTabs(); renderAll();
    const c = CRISES.find(x => x.id === id);
    if (c) map.flyToBounds([[c.bbox[0], c.bbox[1]], [c.bbox[2], c.bbox[3]]], { padding: [60, 60], maxZoom: 9, duration: 0.8 });
  }

  /* ------------------------------------------------------------------ agenda */
  function ensureCalendar(done) {
    if (window.VS_CALENDAR || ensureCalendar.failed) return done();
    loadScript('data/calendar.js').then(() => { if (!window.VS_CALENDAR) ensureCalendar.failed = true; done(); }, () => { ensureCalendar.failed = true; done(); });
  }
  // pays à majorité musulmane (fêtes religieuses calculées affichées dans leur fiche)
  const MUSLIM = new Set('AF AL AZ BH BD BN BF TD KM DJ EG GM GN ID IR IQ JO KZ XK KW KG LB LY MY MV ML MR MA NE NG OM PK PS QA SA SN SL SO SD SY TJ TN TR TM AE UZ EH YE'.split(' '));
  const agTypeOf = e => ['holiday', 'election', 'religious'].includes(e.type) ? e.type : 'other';
  const agPlace = e => e.iso ? flagImg(e.iso) + esc(countryName(e.iso) || e.iso) : esc(e.type === 'religious' ? t('ag_muslim') : t('ag_world'));
  const agTitle = e => state.lang === 'fr' ? e.t_fr : (e.t_en || e.t_fr);
  function agendaItems(from, to, isos) {
    return (((window.VS_CALENDAR || {}).events) || []).filter(e => (e.e || e.d) >= from && e.d <= to && (!isos || !e.iso || isos.has(e.iso)));
  }
  function renderAgenda() {
    const el = $('#agenda-list');
    if (!window.VS_CALENDAR) { el.innerHTML = `<li class="empty">${esc(ensureCalendar.failed ? t('ag_missing') : t('ag_loading'))}</li>`; if (!ensureCalendar.failed) ensureCalendar(renderAgenda); return; }
    $('#ag-range').value = String(state.agRange); $('#ag-scope').value = state.agScope;
    $('#ag-types').innerHTML = Object.entries(t('ag_types')).map(([k, v]) => `<button class="chip" data-agt="${k}" aria-pressed="${state.agTypes.has(k)}">${esc(v)}</button>`).join('');
    const today = new Date().toISOString().slice(0, 10), end = new Date(Date.now() + state.agRange * 864e5).toISOString().slice(0, 10);
    const isos = state.agScope === 'watch' ? state.watch : null;
    const items = agendaItems(today, end, isos).filter(e => state.agTypes.has(agTypeOf(e)));
    const dated = items.filter(e => e.prec !== 'year'), undated = agendaItems(today, new Date(Date.now() + 400 * 864e5).toISOString().slice(0, 10), isos).filter(e => e.prec === 'year' && state.agTypes.has('election'));
    const byDay = {};
    dated.forEach(e => { const d = e.d < today ? today : e.d; (byDay[d] = byDay[d] || []).push(e); });
    const row = e => `<li class="ag-item"${e.iso ? ` data-country="${e.iso}"` : ''}><span class="ag-type ag-${agTypeOf(e)}">${esc(t('ag_type')[e.type] || t('ag_type').other)}</span>
      <div><div class="n">${agPlace(e)}</div><div class="s">${esc(agTitle(e))}${e.e && e.e !== e.d ? ` → ${esc(fmtDay(e.e))}` : ''}${e.prec === 'month' ? ` <span class="muted">(${esc(t('ag_month'))})</span>` : ''}</div>
      ${e.note_fr ? `<div class="muted small">${esc(state.lang === 'fr' ? e.note_fr : e.note_en || e.note_fr)}</div>` : ''}</div></li>`;
    el.innerHTML = (Object.keys(byDay).length ? Object.entries(byDay).sort().map(([d, list]) => `<li class="ag-day">${esc(new Date(d + 'T12:00:00').toLocaleDateString(state.lang === 'fr' ? 'fr-FR' : 'en-GB', { weekday: 'short', day: 'numeric', month: 'short' }))}</li>${list.map(row).join('')}`).join('')
      : `<li class="empty">${t('ag_empty')}</li>`) + (undated.length ? `<li class="ag-day">${esc(t('ag_year'))}</li>` + undated.map(e => row({ ...e, t_fr: e.t_fr, prec: 'year' })).join('') : '');
  }
  function upcomingSection(iso) {
    if (!window.VS_CALENDAR) return '';
    const today = new Date().toISOString().slice(0, 10), end = new Date(Date.now() + 90 * 864e5).toISOString().slice(0, 10);
    const items = agendaItems(today, end, new Set([iso])).filter(e => e.iso === iso || (e.type === 'religious' && MUSLIM.has(iso))).slice(0, 8);
    const later = agendaItems(end, new Date(Date.now() + 400 * 864e5).toISOString().slice(0, 10), new Set([iso])).filter(e => e.iso === iso && e.type === 'election').slice(0, 2);
    const all = items.concat(later);
    return `<div class="d-sec"><h3>${icon('calendar', 14)} ${t('upcoming')}</h3>${all.length ? `<ul class="mini-list">${all.map(e => `<li><span class="dot ag-${agTypeOf(e)}"></span><span class="t">${esc(agTitle(e))}</span><span class="w">${e.prec === 'year' ? esc(e.d.slice(0, 4)) : esc(fmtDay(e.d))}</span></li>`).join('')}</ul>` : `<div class="hint">${t('no_upcoming')}</div>`}</div>`;
  }

  /* ------------------------------------------------------------------ trajets surveillés */
  function cityPoint(name) {
    const k = norm(name).trim(); if (!k) return null;
    const c = CITY_INDEX.find(x => x.key === k) || CITY_INDEX.find(x => x.key.startsWith(k));
    return c ? [c.lat, c.lon, c.name, c.iso] : null;
  }
  function saveCorridor(c) {
    state.localCorridors.push(c); store.set('vs-corridors', state.localCorridors);
    computeProximity(); renderAll(); toast(t('cor_saved'));
    map.flyToBounds(L.latLngBounds(c.points), { padding: [60, 60], duration: 0.8 });
  }
  function startDrawing() {
    state.drawing = []; $('#app').classList.add('picking'); closePanelMobile();
    $('#draw-bar').hidden = false; renderDrawBar();
  }
  function renderDrawBar() {
    $('#draw-bar').innerHTML = `<span>${esc(t('cor_draw_hint'))}</span><strong>${esc(t('cor_points', state.drawing.length))}</strong>
      <button class="btn small primary" id="draw-finish"${state.drawing.length < 2 ? ' disabled' : ''}>${esc(t('cor_finish'))}</button><button class="btn small" id="draw-cancel">${esc(t('cancel'))}</button>`;
  }
  function stopDrawing(keep) {
    const pts = state.drawing; state.drawing = null; $('#draw-bar').hidden = true; $('#app').classList.remove('picking'); renderSiteLayer();
    if (keep && pts && pts.length >= 2) {
      saveCorridor({ name: $('#cor-name').value.trim() || `${t('on_route')} ${state.localCorridors.length + 1}`, points: pts.map(p => [+p[0].toFixed(4), +p[1].toFixed(4)]),
        buffer_km: +$('#cor-buffer').value || 25, min_severity: 1 });
      $('#corridor-form').hidden = true;
    }
  }
  function bindCorridors() {
    $('#btn-add-corridor').addEventListener('click', () => { $('#corridor-form').hidden = !$('#corridor-form').hidden; ensureBuddyData(); $('#cor-draw').innerHTML = icon('map', 14) + esc(t('cor_draw')); });
    $('#corridor-form').addEventListener('submit', async ev => {
      ev.preventDefault(); await ensureBuddyData();
      const names = [$('#cor-from').value, ...$('#cor-via').value.split(','), $('#cor-to').value].map(x => x.trim()).filter(Boolean);
      const pts = [];
      for (const n of names) { const p = cityPoint(n); if (!p) { toast(t('cor_city_err', n), 5000); return; } pts.push([p[0], p[1]]); }
      if (pts.length < 2) return;
      saveCorridor({ name: $('#cor-name').value.trim() || names[0] + ' – ' + names[names.length - 1], points: pts, buffer_km: +$('#cor-buffer').value || 25, min_severity: 1 });
      $('#corridor-form').hidden = true; $('#corridor-form').reset();
    });
    $('#cor-cancel').addEventListener('click', () => { $('#corridor-form').hidden = true; });
    $('#cor-draw').addEventListener('click', startDrawing);
    $('#draw-bar').addEventListener('click', ev => { if (ev.target.closest('#draw-finish')) stopDrawing(true); if (ev.target.closest('#draw-cancel')) stopDrawing(false); });
    map.on('click', ev => { if (!state.drawing) return; state.drawing.push([ev.latlng.lat, L.Util.wrapNum(ev.latlng.lng, [-180, 180], true)]); renderSiteLayer(); renderDrawBar(); });
    $('#corridor-list').addEventListener('click', ev => {
      const del = ev.target.closest('[data-cdel]');
      if (del) { state.localCorridors.splice(+del.dataset.cdel.slice(1), 1); store.set('vs-corridors', state.localCorridors); computeProximity(); renderAll(); return; }
      const row = ev.target.closest('[data-cor]'); const c = row && allCorridors().find(x => x.key === row.dataset.cor);
      if (c) { map.flyToBounds(L.latLngBounds(c.points), { padding: [60, 60], duration: 0.8 }); closePanelMobile(); }
    });
  }

  function renderTabs() {
    $$('.tabs button').forEach(b => {
      b.setAttribute('aria-selected', String(b.dataset.tab === state.tab));
      const ic = { alerts: 'siren', ongoing: 'radio-tower', countries: 'globe', news: 'newspaper', sites: 'building-2', buddy: 'message-circle', agenda: 'calendar' }[b.dataset.tab];
      let label = icon(ic, 20) + `<span>${esc(t('tab_' + b.dataset.tab))}</span>`;
      const n = b.dataset.tab === 'sites' ? EVENTS.filter(e => inWindow(e) && e._near.length && e.severity >= 2).length
        : b.dataset.tab === 'ongoing' ? EVENTS.filter(isOngoing).length : 0;
      if (n) label += `<span class="badge">${n}</span>`;
      b.innerHTML = label;
    });
    $$('.tab-body').forEach(s => { s.hidden = s.dataset.body !== state.tab; });
    if (state.tab === 'buddy') { renderBuddy(); ensureBuddyData(); }
    if (state.tab === 'agenda') renderAgenda();
    renderMobileNav();
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
    $('#only-verified').checked = state.onlyVerified; $('#only-watch').checked = state.onlyWatch;
    const nf = [state.onlyVerified, state.onlyWatch, state.onlySites, state.hideAuto].filter(Boolean).length;
    if (nf) $('#filter-count').textContent = ($('#filter-count').textContent ? $('#filter-count').textContent + ' · ' : '') + '+' + nf;
  }

  function nearLabel(e) {
    if (!e._near.length) return '';
    const n = e._near[0];
    return `<span class="near">${n.site.kind === 'corridor' ? '⟿ ' + esc(t('on_route')) + ' ' : '◉ '}${esc(n.site.name)} · ${Math.round(n.d)} ${t('km')}</span>`;
  }

  function renderAlerts(list) {
    const all = sorted(list);
    $('#alerts-count').textContent = t('n_alerts', all.length);
    const fc = state.crisisFocus && CRISES.find(c => c.id === state.crisisFocus);
    $('#focus-bar').hidden = !fc;
    if (fc) $('#focus-bar').innerHTML = `${icon('activity', 14)}<span>${esc(t('chrono_focus', crisisTitle(fc)))}</span><button class="btn small" id="focus-exit">${esc(t('chrono_exit'))}</button>`;
    if (!all.length) { $('#alert-list').innerHTML = `<li class="empty">${t('no_alerts')}</li>`; return; }
    const shown = all.slice(0, state.limit);
    $('#alert-list').innerHTML = shown.map(e => {
      const place = e.place || countryName(e.country) || t('at_sea');
      const desc = describe(e);
      return `<li class="alert${state.selected === e.id ? ' active' : ''}${e._false ? ' is-false' : ''}" data-id="${esc(e.id)}">
        <span class="stripe" style="background:${sevColor(e.severity)}"></span>
        <span class="ico" style="background:${sevColor(e.severity)}">${icon(cat(e.category).icon)}</span>
        <div><div class="t">${esc(e.title)}</div>
          ${desc ? `<div class="d">${esc(desc)}</div>` : ''}
          <div class="m"><span>${esc(catLabel(e.category))}</span><span>${esc(ago(e.date))}</span><span>${esc(place)}</span>${nearLabel(e)}</div>
          <div class="m src"><span class="tag${isAuto(e) ? ' auto' : ''}">${icon('newspaper', 11)} ${esc(sourceLabel(e))}</span>${isAuto(e) ? `<span class="tag auto">auto</span>` : ''}${admBadge(e)}${verBadge(e)}</div></div></li>`;
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

  /** Bande de vigilance d'un trajet : rectangles par segment + disques aux étapes (approximation à l'écran). */
  function corridorShapes(c) {
    const b = c.radius_km || 25, pts = c.points, out = [];
    const style = { stroke: false, fillColor: cssVar('--accent'), fillOpacity: 0.07, interactive: false };
    pts.forEach(p => out.push(L.circle(p, { ...style, radius: b * 1000 })));
    for (let i = 0; i < pts.length - 1; i++) {
      const [a, z] = [pts[i], pts[i + 1]];
      const k = Math.cos((a[0] + z[0]) / 2 * Math.PI / 180);
      const dx = (z[1] - a[1]) * 111.32 * k, dy = (z[0] - a[0]) * 110.57, len = Math.hypot(dx, dy) || 1;
      const ox = -dy / len * b / (111.32 * k), oy = dx / len * b / 110.57;
      out.push(L.polygon([[a[0] + oy, a[1] + ox], [z[0] + oy, z[1] + ox], [z[0] - oy, z[1] - ox], [a[0] - oy, a[1] - ox]], style));
    }
    out.push(L.polyline(pts, { color: cssVar('--accent'), weight: 2.5, dashArray: '6 5' })
      .bindTooltip(`<strong>${esc(c.name)}</strong><br>${esc(t('cor_km', routeLength(pts)))} · ± ${b} ${t('km')}`, { className: 'vs-tip', sticky: true }));
    return out;
  }
  function renderSiteLayer() {
    sitesLayer.clearLayers();
    allCorridors().forEach(c => corridorShapes(c).forEach(l => l.addTo(sitesLayer)));
    if (state.drawing && state.drawing.length) L.polyline(state.drawing, { color: cssVar('--accent'), weight: 3 }).addTo(sitesLayer);
    allSites().forEach(s => {
      L.circle([s.lat, s.lon], { radius: (s.radius_km || 50) * 1000, color: cssVar('--accent'), weight: 1.2, dashArray: '4 4', fillOpacity: 0.05, interactive: false }).addTo(sitesLayer);
      L.marker([s.lat, s.lon], { icon: L.divIcon({ className: '', iconSize: [22, 22], html: `<div class="site-mk">${icon('building-2')}</div>` }), zIndexOffset: 1000 })
        .bindTooltip(`<strong>${esc(s.name)}</strong><br>${t('radius')} ${s.radius_km || 50} ${t('km')}`, { className: 'vs-tip', direction: 'top', offset: [0, -12] })
        .addTo(sitesLayer);
    });
  }

  function renderCountries() {
    const q = state.countryFilter.toLowerCase();
    const pv = iso => (PULSE[iso] || {}).value ?? 101, pd = iso => (PULSE[iso] || {}).d7 ?? 0;
    const rows = Object.entries(RISK)
      .map(([iso, r]) => ({ iso, r, name: countryName(iso) || iso }))
      .filter(x => (!q || x.name.toLowerCase().includes(q)) && (!state.countryWatch || state.watch.has(x.iso)))
      .sort(state.countrySort === 'pulse' ? (a, b) => pv(a.iso) - pv(b.iso) || b.r.level - a.r.level
        : state.countrySort === 'move' ? (a, b) => pd(a.iso) - pd(b.iso) || pv(a.iso) - pv(b.iso)
        : (a, b) => b.r.level - a.r.level || b.r.score - a.r.score || a.name.localeCompare(b.name));
    $('#country-watch').setAttribute('aria-pressed', String(!!state.countryWatch));
    $('#country-watch').innerHTML = icon('star', 13) + `${esc(t('watch_filter'))} <span class="c">${state.watch.size}</span>`;
    $('#watch-copy').hidden = !state.watch.size; $('#watch-copy').innerHTML = icon('clipboard-check', 13) + esc(t('watch_copy'));
    const cov = coverageMap();
    $('#country-list').innerHTML = rows.length ? rows.map(x => {
      const c = x.r.counts || {};
      const adv = Object.entries(x.r.advisories || {}).map(([src, a]) => `${esc(src.split(' ')[0])} ${a.level}/${a.scale || 4}`).join(' · ');
      const n = (c.security || 0) + (c.hazards || 0);
      return `<li class="country-row" data-iso="${x.iso}"><span class="lvl" style="background:${riskColor(x.r.level)}">${x.r.level}</span>
        <div><div class="n">${flagImg(x.iso)}${esc(x.name)}${state.watch.has(x.iso) ? `<span class="star-mini">${icon('star', 11)}</span>` : ''}${cov[x.iso] && cov[x.iso].level === 'low' ? ` <span class="cov-low" title="${esc(t('cov_low_tip'))}">${esc(t('cov_low'))}</span>` : ''}</div><div class="s">${esc(riskLabel(x.r.level))}${adv ? ` · ${adv}` : ''}</div></div>
        <div class="s">${pulseChip(x.iso)}${n ? `<div>${esc(t('n_alerts', n))}</div>` : ''}</div></li>`;
    }).join('') : `<li class="empty">${state.countryWatch && !state.watch.size ? t('watch_empty') : t('no_data')}</li>`;
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
    $('#btn-add-corridor').innerHTML = icon('plus') + esc(t('add_corridor'));
    const cors = allCorridors();
    $('#corridor-list').innerHTML = cors.map(c => {
      const hits = win.filter(e => e._near.some(n => n.site.key === c.key));
      const max = hits.length ? Math.max(...hits.map(e => e.severity)) : 0;
      return `<li class="site-row corridor-row" data-cor="${c.key}">
        <div class="h"><span class="n">⟿ ${esc(c.name)}</span>${c.origin === 'local' ? `<button class="del" data-cdel="${c.key}" title="${t('delete')}">${icon('trash-2')}</button>` : ''}</div>
        <div class="s">${esc(t('cor_km', routeLength(c.points)))} · ± ${c.radius_km} ${t('km')} · ${c.origin === 'config' ? t('site_config') : t('site_local')}</div>
        <div class="hits" style="color:${max ? sevColor(max) : 'var(--muted)'}">${t('cor_hits', hits.length)}</div></li>`;
    }).join('') || `<li class="hint">${esc(t('cor_hint'))}</li>`;
  }

  function renderLegend() {
    const open = state.legendOpen;
    $('#legend').classList.toggle('collapsed', !open);
    $('#legend').innerHTML = `<button class="legend-toggle" id="legend-toggle" type="button" aria-expanded="${open}">${esc(t('legend'))}<span class="chev">${icon('chevron-down', 14)}</span></button>` + (open ? `
      <div><div class="card-title">${t('legend_sev')}</div><div class="row">${[1, 2, 3, 4].map(s => `<span class="k"><i class="sw" style="background:${sevColor(s)}"></i>${esc(sevLabel(s))}</span>`).join('')}</div></div>
      ${MIN_SOURCES[state.countryLayer] ? `<div><div class="card-title">${esc(t('cl_' + state.countryLayer))}</div><div class="row">${[1, 2, 3, 4].map(l => `<span class="k"><i class="sq" style="background:${MIN_COLORS[l]}"></i>${esc((state.countryLayer === 'us' ? t('us_levels') : t('min_levels'))[l])}</span>`).join('')}</div>${state.countryLayer === 'us' ? '' : `<div class="legend-note">${t('zones_note')}</div>`}</div>`
        : state.countryLayer === 'pulse' ? `<div><div class="card-title">${t('legend_pulse')}</div><div class="row">${[10, 35, 55, 72, 90].map(v => `<span class="k"><i class="sq" style="background:${pulseColor(v)}"></i>${esc(pulseLabel(v))}</span>`).join('')}</div></div>`
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
        ${e.verified && e.verified.status !== 'false' ? `<div class="notice verified-notice">${icon('badge-check', 15)} ${esc(t('verified_notice', e.verified.date ? fmtDay(e.verified.date) : ''))}${e.verified.status === 'corrected' ? ' ' + esc(t('corrected_notice')) : ''}${e.verified.note ? `<br><span class="muted">${esc(e.verified.note)}</span>` : ''}</div>` : ''}
      </div>
      ${CRISIS_OF[e.id] ? `<div class="d-sec"><a href="#" class="crisis-link" data-crisis="${CRISIS_OF[e.id].id}">${icon('activity', 14)} ${esc(t('chrono_part'))} : <strong>${esc(crisisTitle(CRISIS_OF[e.id]))}</strong> (${esc(t('chrono_inc', CRISIS_OF[e.id].n))}) →</a></div>` : ''}
      ${ACC.profile && ACC.profile.role === 'admin' && ACC.profile.status === 'approved' ? `<div class="d-sec"><a class="btn" href="admin.html?tab=checks&check_title=${encodeURIComponent(e.title.slice(0, 110))}&lat=${e.lat}&lon=${e.lon}&place=${encodeURIComponent((e.place || '').split(',')[0])}&iso=${e.country || ''}&event=${encodeURIComponent(e.id)}">${icon('shield', 15)}${esc(t('sc_launch'))}</a></div>` : ''}
      ${state.analyst ? analystPanel(e) : ''}
      <div class="d-sec"><dl class="kv">
        <dt>${t('date')}</dt><dd>${esc(fmtDate(e.date))} <span style="color:var(--muted)">(${esc(ago(e.date))})</span><br><span class="mono">${esc(fmtUTC(e.date))}</span></dd>
        ${e.start && e.start !== e.date ? `<dt>${t('start')}</dt><dd>${esc(fmtDate(e.start))}</dd>` : ''}
        <dt>${t('place')}</dt><dd>${esc(e.place || '—')}</dd>
        <dt>${t('country')}</dt><dd>${e.country ? `<a href="#" data-country="${e.country}">${esc(countryName(e.country))}</a>${r ? ` <span class="pill" style="background:${riskColor(r.level)}">${r.level} · ${esc(riskLabel(r.level))}</span>` : ''}` : esc(t('at_sea'))}</dd>
        <dt>${t('precision')}</dt><dd>${esc(t('prec')[e.precision] || e.precision)}</dd>
        <dt>${t('coords')}</dt><dd class="mono">${e.lat.toFixed(3)}, ${e.lon.toFixed(3)}</dd>
        <dt>${t('confidence')}</dt><dd>${esc(t('conf')[e.confidence] || e.confidence)}</dd>
        ${e.admiralty ? `<dt>${t('adm')}</dt><dd>${admBadge(e, true)} ${esc(admText(e.admiralty))}<br><span class="muted small">${esc(t('adm_note'))}</span></dd>` : ''}
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
    else if (d.kind === 'crisis') openCrisis(d.id, false);
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
        <h2 class="d-title">${flagImg(iso, 26)}${esc(name)}<button class="star-btn${state.watch.has(iso) ? ' on' : ''}" data-watch="${iso}" title="${esc(t(state.watch.has(iso) ? 'watch_remove' : 'watch_add'))}" aria-pressed="${state.watch.has(iso)}">${icon('star', 18)}</button></h2>
        ${(c => c && c.level !== 'good' ? `<div class="notice">${esc(t('cov_notice', c.live, c.base))}</div>` : '')(coverageMap()[iso])}
        <div class="risk-big"><span class="lvl" style="background:${riskColor(lvl)}">${lvl || '–'}</span>
          <div><div class="name">${r ? esc(riskLabel(lvl)) : t('no_data')}</div><div class="desc">${esc(desc)}</div></div></div>
        <div class="site-actions"><a class="btn primary" href="report.html#${iso}" target="_blank" rel="noopener">${icon('file-text')}${t('country_report')}</a>
        <a class="btn" href="brief.html#${iso}" target="_blank" rel="noopener">${icon('plane')}${t('brief')}</a></div>
        ${r && r.basis === 'analyst' ? `<div class="notice" style="border-style:solid">${t('analyst')}</div>` : ''}
        ${r && r.data_quality === 'events-only' ? `<div class="notice">${t('events_only')}</div>` : ''}
      </div>
      ${pulseSection(iso)}
      ${(cs => cs.length ? `<div class="d-sec"><h3>${icon('activity', 14)} ${t('chrono_title')}</h3><ul class="mini-list">${cs.map(c => `<li data-crisis="${c.id}"><span class="dot" style="background:${sevColor(c.max_severity)}"></span><span class="t">${esc(crisisTitle(c))}</span><span class="w">${trendChip(c)}</span></li>`).join('')}</ul></div>` : '')(CRISES.filter(c => c.country === iso).slice(0, 5))}
      ${upcomingSection(iso)}
      <div class="d-sec"><h3>${t('incidents')}</h3><div class="stats">${counts}</div></div>
      ${r ? `<div class="d-sec"><h3>${t('components')}</h3>${bars}</div>` : ''}
      ${advs ? `<div class="d-sec"><h3>${t('advisories')}</h3><ul class="mini-list">${advs}</ul></div>` : ''}
      <div class="d-sec"><h3>${t('recent')}</h3>${recent.length ? `<ul class="mini-list">${recent.map(e => `<li data-event="${esc(e.id)}"><span class="dot" style="background:${sevColor(e.severity)}"></span><span class="t">${esc(e.title)}</span><span class="w">${esc(ago(e.date))}</span></li>`).join('')}</ul>` : `<div class="hint">${t('no_recent')}</div>`}</div>
      <div class="d-sec"><div class="hint">${t('risk_notice')}</div></div>`, 'country', iso);
    if (!window.VS_CALENDAR && !ensureCalendar.failed) ensureCalendar(() => { if (state.drawer && state.drawer.kind === 'country' && state.drawer.id === iso) openCountry(iso, false); });
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
    $$('#ag-range option').forEach(o => { o.textContent = t('ag_range')[o.value]; });
    $('#btn-help') && $('#btn-help').setAttribute('title', t('help'));
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
    store.set('vs-watch', [...state.watch]);
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
    $('#only-verified').addEventListener('change', ev => { state.onlyVerified = ev.target.checked; refresh(); });
    $('#only-watch').addEventListener('change', ev => { state.onlyWatch = ev.target.checked; if (state.onlyWatch && !state.watch.size) toast(t('watch_empty')); refresh(); });
    $('#country-sort').value = state.countrySort;
    $('#country-sort').addEventListener('change', ev => { state.countrySort = ev.target.value; renderCountries(); });
    $('#country-watch').addEventListener('click', () => { state.countryWatch = !state.countryWatch; renderCountries(); });
    $('#watch-copy').addEventListener('click', () => copyText(JSON.stringify([...state.watch]), t('watch_copied'), 9000));
    bindShare();
    bindCorridors();
    bindGng();
    $('#btn-help').innerHTML = icon('circle-help', 17);
    $('#chrono-all').addEventListener('click', () => { state.chronoAll = !state.chronoAll; renderChrono(); });
    $('#chrono-list').addEventListener('click', ev => { const c = ev.target.closest('[data-crisis]'); if (c) { openCrisis(c.dataset.crisis); closePanelMobile(); } });
    $('#focus-bar').addEventListener('click', ev => { if (ev.target.closest('#focus-exit')) { state.crisisFocus = null; renderAll(); } });
    $('#ag-range').addEventListener('change', ev => { state.agRange = +ev.target.value; renderAgenda(); });
    $('#ag-scope').addEventListener('change', ev => { state.agScope = ev.target.value; if (state.agScope === 'watch' && !state.watch.size) toast(t('watch_empty')); renderAgenda(); });
    $('#ag-types').addEventListener('click', ev => { const b = ev.target.closest('[data-agt]'); if (!b) return; const k = b.dataset.agt; state.agTypes.has(k) ? state.agTypes.delete(k) : state.agTypes.add(k); renderAgenda(); });
    $('#agenda-list').addEventListener('click', ev => { const c = ev.target.closest('[data-country]'); if (c) { openCountry(c.dataset.country); closePanelMobile(); } });
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
      const w = ev.target.closest('[data-watch]'); const an = ev.target.closest('[data-an]');
      const cr = ev.target.closest('[data-crisis]'); const fo = ev.target.closest('[data-focus]');
      if (fo) { focusCrisis(fo.dataset.focus); return; }
      if (cr) { ev.preventDefault(); openCrisis(cr.dataset.crisis); return; }
      if (w) { toggleWatch(w.dataset.watch); return; }
      if (an) { analystAction(an.dataset.an, an.dataset.id); return; }
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
      const corridors = allCorridors().map(({ origin, key, kind, radius_km, ...c }) => ({ ...c, buffer_km: c.buffer_km || radius_km }));
      const blob = new Blob([JSON.stringify({ sites, corridors }, null, 2)], { type: 'application/json' });
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'sites.local.json';
      document.body.appendChild(a); a.click(); a.remove(); toast(t('export_done'), 6000);
    });
  }
  function stopPicking() { state.picking = false; $('#app').classList.remove('picking'); $('#toast').hidden = true; }
  function closePanelMobile() { if (window.innerWidth <= 860) { $('#app').classList.remove('panel-open'); renderMobileNav(); } }



  /* ------------------------------------------------------------------ mobile : barre de navigation basse */
  const MOBILE = () => window.innerWidth <= 860;
  function buildMobileNav() {
    const nav = document.createElement('nav');
    nav.className = 'mnav'; nav.id = 'mnav'; nav.setAttribute('aria-label', 'Navigation');
    document.body.appendChild(nav);
    const menu = document.createElement('div');
    menu.className = 'mmenu'; menu.id = 'mmenu'; menu.hidden = true;
    document.body.appendChild(menu);
    nav.addEventListener('click', ev => {
      ev.stopPropagation();  // le menu est reconstruit : la cible serait détachée pour l'écouteur du document
      const b = ev.target.closest('[data-m]'); if (!b) return;
      const m = b.dataset.m;
      if (m === 'more') { menu.hidden = !menu.hidden; renderMobileNav(); return; }
      menu.hidden = true;
      if (m === 'map') { $('#app').classList.remove('panel-open'); closeAnalytics(); }
      else { state.tab = m; renderTabs(); $('#app').classList.add('panel-open'); closeDrawer(); }
      renderMobileNav();
    });
    menu.addEventListener('click', ev => {
      ev.stopPropagation();
      const b = ev.target.closest('[data-mm]'); if (!b) return;
      const k = b.dataset.mm; menu.hidden = true;
      if (['countries', 'news', 'agenda', 'sites'].includes(k)) { state.tab = k; renderTabs(); $('#app').classList.add('panel-open'); closeDrawer(); }
      else if (k === 'analytics') { $('#app').classList.remove('panel-open'); $('#btn-analytics').click(); }
      else if (k === 'lang') $('#btn-lang').click();
      else if (k === 'theme') $('#btn-theme').click();
      else if (k === 'share') $('#btn-share').click();
      else if (k === 'install' && installEvt) { installEvt.prompt(); installEvt = null; }
      renderMobileNav();
    });
    document.addEventListener('click', ev => { if (!ev.target.closest('#mmenu') && !ev.target.closest('#mnav')) { if (!menu.hidden) { menu.hidden = true; renderMobileNav(); } } });
    renderMobileNav();
  }
  function renderMobileNav() {
    const nav = $('#mnav'), menu = $('#mmenu'); if (!nav) return;
    const open = $('#app').classList.contains('panel-open');
    const cur = !menu.hidden ? 'more' : !open ? 'map' : ['alerts', 'ongoing', 'buddy'].includes(state.tab) ? state.tab : 'more';
    const n = EVENTS.filter(isOngoing).length;
    nav.innerHTML = [['map', 'map', 'm_map'], ['alerts', 'siren', 'm_alerts'], ['ongoing', 'radio-tower', 'm_ongoing'], ['buddy', 'message-circle', 'm_travel'], ['more', 'list', 'm_more']]
      .map(([k, ic, lb]) => `<button data-m="${k}" class="${cur === k ? 'on' : ''}" aria-label="${esc(t(lb))}">${icon(ic, 22)}<span>${esc(t(lb))}</span>${k === 'ongoing' && n ? `<b class="nb">${n}</b>` : ''}</button>`).join('');
    const acc = window.AngorAccount && window.AngorAccount.enabled;
    menu.innerHTML = [['countries', 'globe', t('tab_countries')], ['news', 'newspaper', t('tab_news')], ['agenda', 'calendar', t('tab_agenda')], ['sites', 'building-2', t('tab_sites')],
      ['analytics', 'chart-column', t('analytics')], ['share', 'share-2', t('share')], ...(acc ? [['account', 'users', t('m_account')]] : []),
      ...(ACC.profile && ACC.profile.role === 'admin' ? [['admin', 'shield', t('m_admin')]] : []), ['help', 'circle-help', t('help')],
      ['lang', 'globe', state.lang === 'fr' ? 'English' : 'Français'], ['theme', state.theme === 'dark' ? 'sun-medium' : 'moon', state.theme === 'dark' ? 'Clair' : 'Sombre'],
      ...(installEvt ? [['install', 'download', t('m_install')]] : [])]
      .map(([k, ic, lb]) => k === 'account' ? `<a class="mm" href="compte.html">${icon(ic, 20)}<span>${esc(lb)}</span></a>` : k === 'admin' ? `<a class="mm" href="admin.html">${icon(ic, 20)}<span>${esc(lb)}</span></a>`
        : k === 'help' ? `<a class="mm" href="aide.html">${icon(ic, 20)}<span>${esc(lb)}</span></a>` : `<button class="mm" data-mm="${k}">${icon(ic, 20)}<span>${esc(lb)}</span></button>`).join('');
  }
  /* Couches repliables sur mobile */
  function bindLayersToggle() {
    const card = $('#layers');
    const btn = document.createElement('button');
    btn.className = 'layers-toggle'; btn.type = 'button'; btn.innerHTML = icon('layers', 18) + `<span>${esc(t('layers_btn'))}</span>`;
    card.prepend(btn);
    btn.addEventListener('click', () => card.classList.toggle('open'));
  }

  /* ------------------------------------------------------------------ application installable (PWA) */
  let installEvt = null;
  window.addEventListener('beforeinstallprompt', ev => { ev.preventDefault(); installEvt = ev; renderMobileNav(); });
  if ('serviceWorker' in navigator && location.protocol === 'https:') navigator.serviceWorker.register('sw.js').catch(() => {});
  function offlineNotice() { if (!navigator.onLine && D) toast(t('offline', fmtDate(D.generated)), 6000); }
  window.addEventListener('offline', offlineNotice);

  /* ------------------------------------------------------------------ compte, préférences, safety check */
  const ACC = { profile: null };
  async function initAccount() {
    const A = window.AngorAccount;
    const btn = $('#btn-account');
    if (!A || !A.enabled) { if (btn) btn.hidden = true; return; }
    btn.hidden = false;
    const paint = () => {
      const p = ACC.profile;
      btn.innerHTML = p ? `<span class="avatar${p.status === 'approved' ? '' : ' pending'}">${esc((p.full_name || p.email || '?').trim().split(/\s+/).map(x => x[0]).slice(0, 2).join('').toUpperCase())}</span>` : icon('users', 17);
      btn.title = p ? (p.status === 'approved' ? (p.full_name || p.email) : t('acc_pending')) : t('acc_login');
    };
    paint();
    if (!A.session) return;
    try { ACC.profile = await A.profile(); } catch (e) { ACC.profile = null; }
    paint(); renderMobileNav();
    const p = ACC.profile;
    if (!p || p.status !== 'approved') return;
    // préférences du compte → cette session (pays suivis fusionnés, sites et trajets complétés)
    const pr = p.prefs || {};
    let changed = false;
    (pr.watch || []).forEach(iso => { if (!state.watch.has(iso)) { state.watch.add(iso); changed = true; } });
    const key = x => (x.name || '') + '|' + (x.lat || ((x.points || [[0]])[0] || [0])[0]);
    const addAll = (arr, from, k) => { const seen = new Set(arr.map(key)); from.forEach(x => { if (!seen.has(key(x))) { arr.push(x); changed = true; } }); store.set(k, arr); };
    addAll(state.localSites, p.sites || [], 'vs-sites'); addAll(state.localCorridors, p.corridors || [], 'vs-corridors');
    if (changed) { persist(); computeProximity(); renderAll(); }
    // position (volontaire), au plus toutes les 30 minutes
    if (p.consent_location && navigator.geolocation && (!p.location || Date.now() - Date.parse(p.location.at) > 30 * 60e3)) {
      navigator.geolocation.getCurrentPosition(pos => {
        const lat = +pos.coords.latitude.toFixed(3), lon = +pos.coords.longitude.toFixed(3);
        const f = COUNTRIES.features.find(ft => L.geoJSON(ft).getBounds().contains([lat, lon]) && pointIn(ft.geometry, lon, lat));
        A.updateProfile({ location: { lat, lon, iso: f ? f.properties.iso2 : null, at: new Date().toISOString() } }).then(np => { ACC.profile = np || ACC.profile; }).catch(() => {});
      }, () => {}, { timeout: 15000, maximumAge: 600000 });
    }
    // réponse directe depuis une notification (?safety=ID&answer=safe|help)
    const sid = PARAMS.get('safety'), ans = PARAMS.get('answer');
    if (sid && ['safe', 'help'].includes(ans)) { try { await A.respond(sid, ans); toast(t('sc_done')); } catch (e) { toast(t('sc_err')); } }
    pollChecks();
    setInterval(pollChecks, 120000);
  }
  function pointIn(g, x, y) {
    const inRing = r => { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { if (((r[i][1] > y) !== (r[j][1] > y)) && (x < (r[j][0] - r[i][0]) * (y - r[i][1]) / (r[j][1] - r[i][1]) + r[i][0])) c = !c; } return c; };
    return (g.type === 'Polygon' ? [g.coordinates] : g.coordinates).some(p => inRing(p[0]));
  }
  async function pollChecks() {
    const A = window.AngorAccount, p = ACC.profile;
    if (!A || !p || p.status !== 'approved' || document.hidden) return;
    try {
      const [checks, resp] = await Promise.all([A.openChecks(), A.myResponses()]);
      const answered = new Set((resp || []).map(r => r.check_id));
      const later = store.get('vs-sc-later', {});
      const c = (checks || []).find(x => !answered.has(x.id) && A.concerned(x, p) && !(later[x.id] > Date.now()));
      showCheck(c || null);
    } catch (e) { /* hors ligne */ }
  }
  function showCheck(c) {
    let el = $('#safety');
    if (!c) { if (el) el.remove(); return; }
    if (!el) { el = document.createElement('div'); el.id = 'safety'; el.className = 'safety'; el.setAttribute('role', 'alertdialog'); document.body.appendChild(el); }
    el.innerHTML = `<div class="sc-k">${icon('shield', 16)} ${esc(t('sc_title'))}</div><div class="sc-t">${esc(c.title)}</div>${c.message ? `<div class="sc-m">${esc(c.message)}</div>` : ''}
      <div class="sc-b"><button class="btn sc-safe" data-sc="safe">${esc(t('sc_safe'))}</button><button class="btn sc-help" data-sc="help">${esc(t('sc_help'))}</button></div>
      <div class="sc-b2"><button class="btn small ghost" data-sc="not_concerned">${esc(t('sc_nc'))}</button><button class="btn small ghost" data-sc="later">${esc(t('sc_later'))}</button></div>`;
    el.onclick = async ev => {
      const b = ev.target.closest('[data-sc]'); if (!b) return;
      if (b.dataset.sc === 'later') { const l = store.get('vs-sc-later', {}); l[c.id] = Date.now() + 30 * 60e3; store.set('vs-sc-later', l); el.remove(); return; }
      b.disabled = true;
      let pos = null;
      if (ACC.profile.consent_location && navigator.geolocation) pos = await new Promise(r => navigator.geolocation.getCurrentPosition(x => r({ lat: +x.coords.latitude.toFixed(3), lon: +x.coords.longitude.toFixed(3) }), () => r(null), { timeout: 8000, maximumAge: 300000 }));
      try { await window.AngorAccount.respond(c.id, b.dataset.sc, null, pos); el.remove(); toast(t('sc_done')); pollChecks(); }
      catch (e) { b.disabled = false; toast(t('sc_err')); }
    };
  }

  /* ------------------------------------------------------------------ Pulse, cotation, vérification, suivis, partage */
  function pulseChip(iso) {
    const p = PULSE[iso]; if (!p) return '';
    const d = p.d7;
    const tr = d == null ? '' : d <= -3 ? `<span class="tr down">▼${-d}</span>` : d >= 3 ? `<span class="tr up">▲${d}</span>` : '';
    return `<span class="pulse-chip" title="${esc(t('pulse_title'))}"><i style="background:${pulseColor(p.value)}"></i>${p.value}${tr}</span>`;
  }
  function spark(vals, w = 220, h = 44) {
    if (!vals || vals.length < 2) return '';
    const mn = Math.max(0, Math.min(...vals) - 5), mx = Math.min(100, Math.max(...vals) + 5), span = Math.max(1, mx - mn);
    const pts = vals.map((v, i) => `${(i / (vals.length - 1) * (w - 4) + 2).toFixed(1)},${(h - 2 - (v - mn) / span * (h - 4)).toFixed(1)}`).join(' ');
    const last = vals[vals.length - 1];
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" width="100%" height="${h}" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="${pulseColor(last)}" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>`;
  }
  function driverText(d) {
    if (d.type === 'category') return t('drv_cat', catLabel(d.category).toLowerCase(), d.delta);
    if (d.type === 'advisory') return t('drv_adv', d.source, d.from, d.to, fmtDay(d.date));
    return '';
  }
  function pulseSection(iso) {
    const p = PULSE[iso]; if (!p) return '';
    const fmt = v => v == null ? '—' : (v > 0 ? '+' : '') + v;
    return `<div class="d-sec"><h3>${icon('activity', 14)} ${t('pulse_title')}</h3>
      <div class="pulse-big"><span class="pv" style="background:${pulseColor(p.value)}">${p.value}</span>
        <div><div class="name">${esc(pulseLabel(p.value))}</div><div class="desc">7 ${state.lang === 'fr' ? 'j' : 'd'} : <strong>${fmt(p.d7)}</strong> · 30 ${state.lang === 'fr' ? 'j' : 'd'} : <strong>${fmt(p.d30)}</strong></div></div></div>
      ${spark(p.spark)}
      ${p.d7 == null ? `<div class="hint">${t('pulse_na')}</div>` : ''}
      <div class="small"><strong>${t('pulse_drivers')}</strong></div>
      ${(p.drivers || []).length ? `<ul class="plain">${p.drivers.map(d => `<li>${esc(driverText(d))}</li>`).join('')}</ul>` : `<div class="hint">${t('pulse_none')}</div>`}
      <div class="hint">${t('pulse_hint')}</div></div>`;
  }
  function admText(code) {
    if (!code) return '';
    return `${t('adm_rel')[code[0]] || ''}, ${t('adm_cred')[code[1]] || ''}`;
  }
  function admBadge(e, big) {
    if (!e.admiralty) return '';
    const c = e.admiralty, cls = 'adm adm-' + c[0].toLowerCase() + (big ? ' big' : '');
    return `<span class="${cls}" title="${esc(t('adm_title') + ' : ' + c + ' – ' + admText(c))}">${esc(c)}</span>`;
  }
  const verBadge = e => e.verified && e.verified.status !== 'false' ? `<span class="tag verified" title="${esc(t('verified'))}">${icon('badge-check', 11)} ${esc(t('verified'))}</span>` : '';
  function toggleWatch(iso) {
    if (state.watch.has(iso)) { state.watch.delete(iso); toast(t('watch_removed')); } else { state.watch.add(iso); toast(t('watch_added')); }
    persist(); renderCountries(); reopenDrawer(); if (state.onlyWatch) refresh();
  }
  function copyText(text, msg, ms) {
    const done = () => toast(msg, ms || 4000);
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, () => fallbackCopy(text, done));
    else fallbackCopy(text, done);
  }
  function fallbackCopy(text, done) {
    const ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch (e) { /* copie impossible */ }
    ta.remove(); done();
  }
  /** Paramètres d'URL décrivant la vue courante (période, filtres, calques, carte, fiche ouverte). */
  function viewParams() {
    const P = new URLSearchParams();
    if (state.range) { P.set('from', state.range.from); P.set('to', state.range.to); } else P.set('h', String(state.hours));
    const sev = [1, 2, 3, 4].filter(x => state.sev[x]).join(''); if (sev !== '1234') P.set('sev', sev);
    if (state.cats.size < Object.keys(TAX.categories).length) P.set('cats', [...state.cats].join(','));
    if (state.hideAuto) P.set('auto', '0');
    if (state.onlyVerified) P.set('verified', '1');
    if (state.onlyWatch) { P.set('watch', '1'); if (state.watch.size) P.set('watchlist', [...state.watch].join(',')); }
    if (state.countryLayer !== 'risk') P.set('layer', state.countryLayer);
    if (state.basemap !== 'detail') P.set('base', state.basemap);
    if (state.tab !== 'alerts') P.set('tab', state.tab);
    const c = map.getCenter(); P.set('m', `${c.lat.toFixed(3)},${L.Util.wrapNum(c.lng, [-180, 180], true).toFixed(3)},${map.getZoom()}`);
    if (state.crisisFocus) P.set('focus', state.crisisFocus);
    if (state.drawer && !$('#drawer').hidden) P.set({ event: 'e', country: 'c', crisis: 'k' }[state.drawer.kind] || 'x', state.drawer.id || '');
    P.delete('x');
    return P.toString();
  }
  const viewUrl = () => location.origin + location.pathname + '?' + viewParams();
  function renderViews() {
    const views = store.get('vs-views', []);
    $('#views-pop').innerHTML = `<div class="card-title">${t('views_title')}</div>
      <form id="view-form" class="view-form"><input class="field" id="view-name" maxlength="60" placeholder="${esc(t('view_ph'))}"><button class="btn primary small" type="submit">${icon('bookmark', 13)}${esc(t('view_save'))}</button></form>
      ${views.length ? `<ul class="views-list">${views.map((v, i) => `<li><a href="?${esc(v.q)}" data-view="${i}">${esc(v.name)}</a>
        <button class="icon-btn small" data-vlink="${i}" title="${esc(t('view_link'))}">${icon('link', 13)}</button><button class="icon-btn small" data-vdel="${i}" title="${esc(t('delete'))}">${icon('trash-2', 13)}</button></li>`).join('')}</ul>` : `<p class="hint">${t('views_empty')}</p>`}`;
  }
  function bindShare() {
    $('#btn-share').innerHTML = icon('share-2', 15) + `<span>${esc(t('share'))}</span>`;
    $('#btn-views').innerHTML = icon('bookmark', 15) + `<span>${esc(t('views'))}</span>`;
    $('#btn-share').addEventListener('click', () => { const u = viewUrl(); history.replaceState(null, '', '?' + viewParams()); copyText(u, t('share_done')); });
    $('#btn-views').addEventListener('click', ev => { ev.stopPropagation(); const pop = $('#views-pop'); pop.hidden = !pop.hidden; if (!pop.hidden) { renderViews(); $('#view-name').focus(); } });
    $('#views-pop').addEventListener('submit', ev => {
      ev.preventDefault();
      const name = $('#view-name').value.trim() || `${periodLabel()} – ${new Date().toLocaleDateString()}`;
      const views = store.get('vs-views', []); views.unshift({ name, q: viewParams() }); store.set('vs-views', views.slice(0, 30));
      renderViews(); toast(t('view_saved'));
    });
    $('#views-pop').addEventListener('click', ev => {
      ev.stopPropagation();
      const views = store.get('vs-views', []);
      const del = ev.target.closest('[data-vdel]'), lk = ev.target.closest('[data-vlink]');
      if (del) { views.splice(+del.dataset.vdel, 1); store.set('vs-views', views); renderViews(); }
      else if (lk) copyText(location.origin + location.pathname + '?' + views[+lk.dataset.vlink].q, t('share_done'));
    });
    document.addEventListener('click', ev => { if (!ev.target.closest('#views-pop') && !ev.target.closest('#btn-views')) $('#views-pop').hidden = true; });
  }
  /* Mode analyste (?analyste=1) : valider, infirmer ou corriger un incident ; décisions gardées dans ce navigateur
     puis exportées en config/verified.json (publiées par le robot à la collecte suivante). */
  const LOCAL_V = store.get('vs-verified-local', {});
  function applyDecision(e, v) {
    if (!e._orig) e._orig = { severity: e.severity, category: e.category, title: e.title, verified: e.verified, admiralty: e.admiralty, confidence: e.confidence };
    const o = e._orig;
    Object.assign(e, { severity: o.severity, category: o.category, title: o.title, verified: o.verified, admiralty: o.admiralty, confidence: o.confidence });
    e._false = false;
    if (!v) return;
    if (v.status === 'false') { e._false = true; e.verified = null; if (e.admiralty) e.admiralty = e.admiralty[0] + '5'; return; }
    if (v.severity) e.severity = +v.severity;
    if (v.category && TAX.categories[v.category]) e.category = v.category;
    e.verified = { status: v.status, note: v.note || '', date: v.date || '' };
    e.confidence = 'high';
    if (e.admiralty) e.admiralty = e.admiralty[0] + '1';
  }
  function applyLocalDecisions() { EVENTS.forEach(e => { if (LOCAL_V[e.id] || e._orig) applyDecision(e, LOCAL_V[e.id]); }); }
  function analystPanel(e) {
    const v = LOCAL_V[e.id] || (D && D.verified || {})[e.id] || null;
    const sevOpts = [1, 2, 3, 4].map(s => `<option value="${s}"${s === e.severity ? ' selected' : ''}>${esc(sevLabel(s))}</option>`).join('');
    const catOpts = Object.keys(TAX.categories).map(k => `<option value="${k}"${k === e.category ? ' selected' : ''}>${esc(catLabel(k))}</option>`).join('');
    return `<div class="d-sec analyst-panel"><h3>${icon('clipboard-check', 14)} ${t('an_mode')}${v ? ` · <span class="an-st an-${v.status}">${esc(t('an_status')[v.status])}</span>` : ''}</h3>
      ${LOCAL_V[e.id] ? `<div class="hint">${t('an_local')}</div>` : ''}
      <div class="an-grid"><label>${t('an_sev')}<select class="field" id="an-sev">${sevOpts}</select></label><label>${t('an_cat')}<select class="field" id="an-cat">${catOpts}</select></label></div>
      <input class="field" id="an-note" maxlength="300" placeholder="${esc(t('an_note'))}" value="${esc((v && v.note) || '')}">
      <div class="site-actions"><button class="btn primary small" data-an="verified" data-id="${esc(e.id)}">${icon('check', 13)}${t('an_valid')}</button>
        <button class="btn small" data-an="corrected" data-id="${esc(e.id)}">${icon('pencil', 13)}${t('an_fix')}</button>
        <button class="btn small danger" data-an="false" data-id="${esc(e.id)}">${icon('circle-x', 13)}${t('an_false')}</button>
        ${LOCAL_V[e.id] ? `<button class="btn small ghost" data-an="reset" data-id="${esc(e.id)}">${t('an_reset')}</button>` : ''}</div></div>`;
  }
  function analystAction(kind, id) {
    const e = EVENTS.find(x => x.id === id); if (!e) return;
    if (kind === 'reset') delete LOCAL_V[id];
    else {
      const v = { status: kind, note: ($('#an-note') || {}).value || '', date: new Date().toISOString().slice(0, 10) };
      if (kind === 'corrected') { v.severity = +$('#an-sev').value; v.category = $('#an-cat').value; }
      LOCAL_V[id] = v;
    }
    store.set('vs-verified-local', LOCAL_V);
    applyDecision(e, LOCAL_V[id]);
    renderAll(); openEvent(id, false); renderAnalystBar();
  }
  function renderAnalystBar() {
    let bar = $('#analyst-bar');
    if (!state.analyst) { if (bar) bar.remove(); return; }
    if (!bar) { bar = document.createElement('div'); bar.id = 'analyst-bar'; bar.className = 'analyst-bar'; $('.map-wrap').appendChild(bar);
      bar.addEventListener('click', ev => {
        if (ev.target.closest('#an-export')) exportVerified();
        if (ev.target.closest('#an-exit')) { state.analyst = false; store.set('vs-analyst', false); renderAnalystBar(); renderAll(); reopenDrawer(); }
      }); }
    const n = Object.keys(LOCAL_V).length;
    bar.title = t('an_hint');
    bar.innerHTML = `${icon('clipboard-check', 15)}<strong>${t('an_mode')}</strong>
      <button class="btn small primary" id="an-export">${icon('download', 13)}${esc(t('an_export', n))}</button><button class="btn small ghost" id="an-exit">${esc(t('an_exit'))}</button>`;
  }
  function exportVerified() {
    const events = Object.assign({}, (D && D.verified) || {}, LOCAL_V);
    const out = { _comment: 'Décisions de l’analyste Angor (mode analyste de la carte). status : verified | corrected | false.', events };
    const blob = new Blob([JSON.stringify(out, null, 2)], { type: 'application/json' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'verified.json';
    document.body.appendChild(a); a.click(); a.remove(); toast(t('an_done'), 8000);
  }


  /* ------------------------------------------------------------------ go / no-go guidé */
  const GNG = window.AngorGNG || null;
  /** Boutons d'action ajoutés sous une réponse du Travel buddy : surveiller le trajet, go/no-go guidé. */
  function buddyExtras(det, intents) {
    const btns = [];
    const cs = det.cities || [];
    if (intents.includes('route') && cs.length >= 2 && cs[0].iso === cs[1].iso) {
      const data = esc(JSON.stringify({ name: cs[0].name + ' – ' + cs[1].name, points: [[cs[0].lat, cs[0].lon], [cs[1].lat, cs[1].lon]] }));
      btns.push(`<button class="btn small" data-buddy-corridor="${data}">⟿ ${esc(t('cor_watch'))}</button>`);
    }
    if (GNG && det.isos.length) btns.push(`<button class="btn small" data-gng-start="${det.isos[0]}"${cs[0] ? ` data-gng-city="${esc(cs[0].name)}"` : ''}>${icon('clipboard-check', 13)}${esc(t('gng_open'))}</button>`);
    return btns.length ? `<div class="site-actions buddy-actions">${btns.join('')}</div>` : '';
  }
  function gngForm(iso, city) {
    const lang = state.lang, d0 = new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10), d1 = new Date(Date.now() + 11 * 864e5).toISOString().slice(0, 10);
    const opts = Object.values(countryProps).sort((a, b) => a['name_' + lang].localeCompare(b['name_' + lang]))
      .map(p => `<option value="${p.iso2}"${p.iso2 === iso ? ' selected' : ''}>${esc(p['name_' + lang])}</option>`).join('');
    const saved = store.get('vs-gng', {});
    $('#gng-panel').innerHTML = `<div class="buddy-head"><h3>${esc(t('gng_title'))}</h3></div><p class="hint">${esc(t('gng_intro'))}</p>
      <form id="gng-form" class="gng-form">
        <label>${esc(t('gng_country'))}<select class="field" name="iso">${opts}</select></label>
        <label>${esc(t('gng_city'))}<input class="field" name="city" value="${esc(city || '')}" list="gng-cities"></label>
        <label>${esc(t('gng_from'))}<input class="field" type="date" name="from" value="${d0}"></label>
        <label>${esc(t('gng_to'))}<input class="field" type="date" name="to" value="${d1}"></label>
        ${GNG.QUESTIONS.map(q => `<label class="wide">${esc(lang === 'fr' ? q.fr : q.en)}<select class="field" name="${q.id}">${q.opts.map(o => `<option value="${o[0]}"${(saved[q.id] || GNG.DEFAULTS[q.id]) === o[0] ? ' selected' : ''}>${esc(lang === 'fr' ? o[1] : o[2])}</option>`).join('')}</select></label>`).join('')}
        <div class="site-actions wide"><button class="btn primary" type="submit">${esc(t('gng_eval'))}</button><button class="btn" type="button" id="gng-cancel">${esc(t('gng_cancel'))}</button></div>
      </form><datalist id="gng-cities"></datalist>`;
    $('#gng-cities').innerHTML = CITY_INDEX.filter(c => c.iso === iso).slice(0, 50).map(c => `<option value="${esc(c.name)}">`).join('');
  }
  async function openGng(iso, city) {
    if (!GNG) return;
    await ensureBuddyData();
    await new Promise(r => ensureCalendar(r));
    iso = iso || (state.drawer && state.drawer.kind === 'country' ? state.drawer.id : '') || buddy.lastIso || 'FR';
    gngForm(iso, city);
    $('#gng-panel').hidden = false; $('#buddy-log').hidden = true; $('#buddy-suggest').hidden = true; $('#buddy-form').hidden = true;
    $('#gng-panel').scrollIntoView({ block: 'start' });
  }
  function closeGng() { $('#gng-panel').hidden = true; $('#buddy-log').hidden = false; $('#buddy-suggest').hidden = false; $('#buddy-form').hidden = false; }
  function gngResultHtml(f, th, res) {
    const lang = state.lang, fr = lang === 'fr';
    const q = new URLSearchParams({ c: f.iso, from: f.from, to: f.to, p: res.answers.profile, g: GNG.encode(res.answers) });
    if (f.city) q.set('city', f.city);
    return `<h4>${flagImg(f.iso)}${esc(countryName(f.iso))}${f.city ? ' · ' + esc(f.city) : ''} — ${esc(t('gng_title'))}</h4>
      <div class="gng-res"><div class="gng-dec" style="border-color:${res.color}"><span class="dl" style="background:${res.color}"></span><strong>${esc(res.label)}</strong></div>
        <div class="gng-grid">${GNG.matrix(res.T, res.V, lang, 170)}<div class="gng-nums"><div><span>${esc(t('gng_threat'))}</span><strong>${res.T}/5</strong></div>
          <div><span>${esc(t('gng_vuln'))}</span><strong>${res.V}/5</strong></div><div><span>${esc(t('gng_resid'))}</span><strong>${res.R}/25</strong></div></div></div></div>
      ${res.note ? `<p><strong>${esc(res.note)}</strong></p>` : ''}
      <p><strong>${esc(t('gng_factors'))}</strong></p>${li(th.factors.map(esc))}
      <p><strong>${esc(t('gng_conditions'))}</strong></p>${res.conditions.length ? li(res.conditions.map(esc)) : `<p>${esc(t('gng_noconds'))}</p>`}
      <div class="site-actions buddy-actions"><a class="btn small primary" href="brief.html?${q.toString()}" target="_blank" rel="noopener">${icon('file-text', 13)}${esc(t('gng_brief'))}</a>
        ${AI_URL ? `<button class="btn small" data-gng-ai="${esc(JSON.stringify({ iso: f.iso, city: f.city, from: f.from, to: f.to, T: res.T, V: res.V, R: res.R, label: res.label, cond: res.conditions, factors: th.factors }))}">${esc(t('gng_ai'))}</button>` : ''}</div>
      <p class="muted">${esc(t('gng_disclaimer'))}</p>`;
  }
  function evalGng(form) {
    const fd = Object.fromEntries(new FormData(form).entries());
    const f = { iso: fd.iso, city: (fd.city || '').trim(), from: fd.from, to: fd.to };
    const answers = {}; GNG.QUESTIONS.forEach(q => { answers[q.id] = fd[q.id]; });
    store.set('vs-gng', answers);
    const cp = f.city ? cityPoint(f.city) : null;
    const th = GNG.threat({ iso: f.iso, point: cp && cp[3] === f.iso ? { lat: cp[0], lon: cp[1] } : null, from: f.from, to: f.to, lang: state.lang });
    const res = GNG.evaluate(answers, th, state.lang);
    buddy.log.push({ role: 'user', text: `${t('gng_title')} : ${countryName(f.iso)}${f.city ? ' (' + f.city + ')' : ''}, ${f.from} → ${f.to}` });
    buddy.log.push({ role: 'assistant', html: gngResultHtml(f, th, res), text: `${res.label} (M${res.T} × V${res.V})`, mode: 'local' });
    closeGng(); renderBuddy();
  }
  async function gngAi(data) {
    buddy.busy = true; renderBuddy();
    const c = collect(data.iso, { cities: [], isos: [data.iso] }, ['security', 'route']);
    const cal = ((window.VS_CALENDAR || {}).events || []).filter(e => e.iso === data.iso && e.d >= data.from && e.d <= data.to).map(e => `AGENDA: ${e.d} ${e.t_fr}`).join('\n');
    const q = `Évaluation go/no-go : ${countryName(data.iso)}${data.city ? ' (' + data.city + ')' : ''}, du ${data.from} au ${data.to}. Menace ${data.T}/5, vulnérabilité ${data.V}/5, risque résiduel ${data.R}/25. Décision calculée : ${data.label}. Facteurs : ${data.factors.join(' ; ')}. Conditions : ${data.cond.join(' ; ') || 'aucune'}.`;
    try {
      const answer = await aiCall('gonogo', q, contextText(c) + (cal ? '\n' + cal : ''));
      buddy.log.push({ role: 'assistant', html: mdToHtml(answer), text: answer, mode: 'ai' });
    } catch (e) { buddy.log.push({ role: 'assistant', html: `<p class="muted">${esc(t('buddy_ai_down'))}</p>`, mode: 'local' }); }
    buddy.busy = false; renderBuddy();
  }
  function bindGng() {
    $('#gng-open').innerHTML = icon('clipboard-check', 13) + esc(t('gng_open'));
    $('#gng-open').hidden = !GNG;
    $('#gng-open').addEventListener('click', () => openGng());
    $('#gng-panel').addEventListener('submit', ev => { ev.preventDefault(); evalGng(ev.target); });
    $('#gng-panel').addEventListener('click', ev => { if (ev.target.closest('#gng-cancel')) closeGng(); });
    $('#gng-panel').addEventListener('change', ev => { if (ev.target.name === 'iso') $('#gng-cities').innerHTML = CITY_INDEX.filter(c => c.iso === ev.target.value).slice(0, 50).map(c => `<option value="${esc(c.name)}">`).join(''); });
  }

  /* ------------------------------------------------------------------ My travel buddy */
  /* Assistant de voyage : repère le(s) pays et villes de la question, rassemble les données Angor
     (risque, avis MEAE/FCDO/US, incidents, fiche culturelle, santé, prestataires) puis :
     - avec un Worker IA configuré (settings.buddy_url) : réponse rédigée par Claude à partir de ce contexte ;
     - sinon : réponse structurée construite localement à partir des mêmes données (gratuit, hors ligne). */
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
    agenda: /ferie|holiday|election|vote|scrutin|referendum|ramadan|aid |eid|fete|agenda|calendrier|calendar|greve|strike/,
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
    const pu = PULSE[c.iso]; if (pu) L.push(`PULSE (stabilité 0-100): ${pu.value}${pu.d7 != null ? ', variation 7 j ' + pu.d7 : ''}`);
    CRISES.filter(x => x.country === c.iso && x.status === 'active').slice(0, 3).forEach(x => L.push(`CRISE EN COURS: ${x.title} — ${x.n} incidents depuis ${x.start.slice(0, 10)}, tendance ${x.trend} — ${x.summary_fr}`));
    const today = new Date().toISOString().slice(0, 10), end = new Date(Date.now() + 120 * 864e5).toISOString().slice(0, 10);
    agendaItems(today, end, new Set([c.iso])).filter(e => e.iso === c.iso || (e.type === 'religious' && MUSLIM.has(c.iso))).slice(0, 10)
      .forEach(e => L.push(`AGENDA: ${e.d}${e.e ? '→' + e.e : ''} ${e.type} — ${e.t_fr}${e.prec && e.prec !== 'day' ? ' (date approximative)' : ''}`));
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
      if (all.includes('agenda')) {
        const today = new Date().toISOString().slice(0, 10), end = new Date(Date.now() + 120 * 864e5).toISOString().slice(0, 10);
        const items = agendaItems(today, end, new Set([iso])).filter(e => e.iso === iso || (e.type === 'religious' && MUSLIM.has(iso))).slice(0, 10);
        parts.push(`<p><strong>${fr ? 'Agenda (4 prochains mois)' : 'Agenda (next 4 months)'}</strong></p>` + (items.length ? li(items.map(e => `${e.prec === 'year' ? esc(e.d.slice(0, 4)) + ` (${fr ? 'date à préciser' : 'date tbc'})` : esc(fmtDay(e.d))} — ${esc(agTitle(e))}${e.type === 'religious' ? ` <span class="muted">(${fr ? 'date indicative' : 'indicative date'})</span>` : ''}`)) : `<p class="muted">${esc(t('no_upcoming'))}</p>`));
      }
      if (all.includes('telecom')) parts.push(`<p><strong>${fr ? 'Télécoms' : 'Telecoms'}</strong> : ${esc((p.operators || []).join(', ') || '—')} · ${fr ? 'prises' : 'plugs'} ${esc((p.plugs || []).join(', ') || '—')} · ${esc((p.voltage || []).join('/'))} V</p>`);
      if (all.includes('providers') || (all.includes('route') && (c.level || 0) >= 3)) parts.push(`<p><strong>${fr ? 'Prestataires (sécurité / évacuation)' : 'Providers (security / evacuation)'}</strong></p>` + li(c.provs.map(pv => `<a href="${esc(pv.web)}" target="_blank" rel="noopener">${esc(pv.name)}</a>`)));
      parts.push(`<p class="muted"><a href="report.html#${iso}" target="_blank" rel="noopener">${fr ? 'Rapport pays complet (PDF)' : 'Full country report (PDF)'}</a> · <a href="brief.html#${iso}${(cc => cc ? '|' + encodeURIComponent(cc.name) : '')((det.cities || []).find(x => x.iso === iso))}" target="_blank" rel="noopener">${fr ? 'Préparer un brief de mission' : 'Prepare a mission brief'}</a></p>`);
      out.push(parts.join(''));
    });
    return out.join('<hr>') + buddyExtras(det, intents) + `<p class="muted">${fr ? 'Réponse construite à partir des données Angor (avis officiels, incidents, fiches) — à vérifier avant décision.' : 'Answer built from Angor data — verify before deciding.'}</p>`;
  }
  function mdToHtml(md) {
    let h = esc(md).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/^#{1,4} (.+)$/gm, '<h4>$1</h4>');
    h = h.replace(/(?:^|\n)((?:[-•] .+(?:\n|$))+)/g, (m, block) => `\n<ul>${block.trim().split('\n').map(l => `<li>${l.replace(/^[-•] /, '')}</li>`).join('')}</ul>\n`);
    return h.split(/\n{2,}/).map(p => /^\s*<(ul|h4)/.test(p) ? p : `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
  }
  async function ask(q) {
    await ensureBuddyData();
    await new Promise(r => ensureCalendar(r));
    const det = detect(q), intents = intentsOf(q);
    if (det.isos.length) buddy.lastIso = det.isos[0];
    if (!AI_URL || !det.isos.length) return { html: localAnswer(q, det, intents), mode: 'local' };
    const ctx = det.isos.map(iso => contextText(collect(iso, det, intents.length ? intents : ['security']))).join('\n\n').slice(0, 14000);
    try {
      const answer = await aiCall('buddy', q, ctx, buddy.log.slice(-4).map(m => ({ role: m.role, content: m.text.slice(0, 1500) })));
      return { html: mdToHtml(answer) + buddyExtras(det, intents), mode: 'ai', text: answer };
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
    $('#buddy-mode').textContent = AI_URL ? t('buddy_ai_on') : t('buddy_ai_off');
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
    $('#buddy-log').addEventListener('click', ev => {
      const a = ev.target.closest('[data-buddy-event]'); if (a) { ev.preventDefault(); openEvent(a.dataset.buddyEvent); return; }
      const cor = ev.target.closest('[data-buddy-corridor]'); if (cor) { const c = JSON.parse(cor.dataset.buddyCorridor); saveCorridor({ ...c, buffer_km: 25, min_severity: 1 }); return; }
      const g = ev.target.closest('[data-gng-start]'); if (g) { openGng(g.dataset.gngStart, g.dataset.gngCity || ''); return; }
      const ai = ev.target.closest('[data-gng-ai]'); if (ai) { ai.disabled = true; gngAi(JSON.parse(ai.dataset.gngAi)); }
    });
    $('#buddy-clear').addEventListener('click', () => { buddy.log = []; renderBuddy(); });
  }

  /* ------------------------------------------------------------------ démarrage */
  if (D && D.settings && D.settings.product_name) { $('#brand-name').textContent = D.settings.product_name; document.title = D.settings.product_name; }
  applyLocalDecisions();
  computeProximity();
  applyI18n();
  applyTheme();
  riskLayer.addTo(map); cluster.addTo(map); sitesLayer.addTo(map);
  bind();
  bindBuddy();
  buildMobileNav();
  bindLayersToggle();
  initAccount();
  offlineNotice();
  renderAnalystBar();
  const mv = (PARAMS.get('m') || '').split(',').map(Number);
  if (mv.length === 3 && mv.every(isFinite)) map.setView([mv[0], mv[1]], mv[2]);
  ensureArchives(() => {
    renderAll();
    const ce = PARAMS.get('e'), cc = (PARAMS.get('c') || PARAMS.get('country') || '').toUpperCase(), ck = PARAMS.get('k');
    if (ck && CRISES.some(x => x.id === ck)) openCrisis(ck, mv.length !== 3);
    else if (ce && EVENTS.some(x => x.id === ce)) openEvent(ce, !mv.length || mv.length !== 3);
    else if (cc && countryProps[cc]) openCountry(cc, mv.length !== 3);
  });
  const hash = decodeURIComponent(location.hash.slice(1));
  if (hash && countryProps[hash]) openCountry(hash);
  if (!D) {
    const el = $('#empty');
    el.innerHTML = `<div class="box"><h2>${t('empty_title')}</h2><p>${t('empty_body')}</p><p><code>python collecte.py</code></p><p>${t('empty_after')}</p></div>`;
    el.hidden = false;
  }
  window.addEventListener('resize', () => map.invalidateSize());
})();
