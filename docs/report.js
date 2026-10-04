/* Angor Intelligence – dossier pays : écran + PDF A4 (impression du navigateur)
   Sections : couverture, synthèse, risques, sûreté détaillée, recommandations, incidents, villes, avis officiels,
   voyage, santé et secours, culture, calendrier, économie, contexte, prestataires, sources. */
(function () {
  'use strict';
  const D = window.VS_DATA || {};
  const P = (window.VS_PROFILES || {}).countries || {};
  const FB = window.VS_FACTBOOK || {};
  const ECON = (window.VS_ECON || {}).countries || {};
  const GUIDES = (window.VS_GUIDES || {}).countries || {};
  const GUIDES_NOTE = ((window.VS_GUIDES || {}).meta || {}).note || '';
  const PRACT = (window.VS_PRACTICAL || {}).countries || {};
  const PROV = window.VS_PROVIDERS || { providers: [], services: {}, local: {} };
  const FEATURES = (window.VS_COUNTRIES || { features: [] }).features;
  const COUNTRIES = FEATURES.map(f => f.properties);
  const ICONS = window.VS_ICONS || {};
  const TAX = D.taxonomy || { categories: {}, risk_levels: {}, severity: {} };
  const RISK = D.countries || {};
  const STATS = D.country_stats || {};
  const EVENTS = D.events || [];
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* stockage indisponible */ } }
  };
  let lang = store.get('vs-lang', 'fr') === 'en' ? 'en' : 'fr';
  let ISO = 'FR';

  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const icon = (n, s = 16) => `<svg viewBox="0 0 24 24" width="${s}" height="${s}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[n] || ICONS['circle-alert'] || ''}</svg>`;
  const L = (fr, en) => lang === 'fr' ? fr : en;
  const flag = (iso, w = 40) => iso && iso.length === 2 ? `<img class="flag" src="https://flagcdn.com/w${w}/${iso.toLowerCase()}.png" alt="" loading="lazy" onerror="this.remove()">` : '';
  const RC = { 0: '#AEB8C2', 1: '#3E9B6B', 2: '#95B443', 3: '#E3A92B', 4: '#E0722C', 5: '#C23347' };
  const SEV = { 1: '#3F86C6', 2: '#E0A21B', 3: '#E0622B', 4: '#B0182E' };
  const MIN_COLORS = { 1: '#2E9E5B', 2: '#E3B505', 3: '#EE7D22', 4: '#D7263D' };
  const riskName = l => (TAX.risk_levels[l] || {})[lang] || '—';
  const riskDesc = l => (TAX.risk_levels[l] || {})['desc_' + lang] || '';
  const catName = c => (TAX.categories[c] || {})[lang] || c;
  const catIcon = c => (TAX.categories[c] || {}).icon || 'circle-alert';
  const SUBREG = { 'Southern Asia': 'Asie du Sud', 'South-Eastern Asia': 'Asie du Sud-Est', 'Eastern Asia': 'Asie de l\'Est', 'Central Asia': 'Asie centrale', 'Western Asia': 'Moyen-Orient',
    'Northern Africa': 'Afrique du Nord', 'Western Africa': 'Afrique de l\'Ouest', 'Middle Africa': 'Afrique centrale', 'Eastern Africa': 'Afrique de l\'Est', 'Southern Africa': 'Afrique australe',
    'Northern Europe': 'Europe du Nord', 'Western Europe': 'Europe de l\'Ouest', 'Southern Europe': 'Europe du Sud', 'Eastern Europe': 'Europe de l\'Est',
    'Northern America': 'Amérique du Nord', 'Central America': 'Amérique centrale', 'Caribbean': 'Caraïbes', 'South America': 'Amérique du Sud',
    'Australia and New Zealand': 'Australie et Nouvelle-Zélande', 'Melanesia': 'Mélanésie', 'Micronesia': 'Micronésie', 'Polynesia': 'Polynésie' };
  const regionOf = iso => { const r = (COUNTRIES.find(c => c.iso2 === iso) || {}).region || ''; return lang === 'fr' ? (SUBREG[r] || r) : r; };
  const cname = iso => { const p = COUNTRIES.find(c => c.iso2 === iso); return p ? p['name_' + lang] : iso; };
  const locale = () => lang === 'fr' ? 'fr-FR' : 'en-GB';
  const num = (v, d = 1) => v == null || isNaN(v) ? '—' : Number(v).toLocaleString(locale(), { maximumFractionDigits: d });
  const big = v => {
    if (v == null) return '—';
    const a = Math.abs(v);
    if (a >= 1e12) return lang === 'fr' ? num(v / 1e9, 0) + ' Md $' : num(v / 1e12, 2) + ' tn $';
    if (a >= 1e9) return num(v / 1e9, 1) + L(' Md $', ' bn $');
    if (a >= 1e6) return num(v / 1e6, 1) + L(' M', ' m');
    return num(v, 0);
  };
  const pop = v => v == null ? '—' : v >= 1e6 ? num(v / 1e6, 1) + L(' M hab.', 'm people') : num(v, 0) + L(' hab.', ' people');
  const money = v => v == null ? '—' : big(v) + (Math.abs(v) < 1e9 ? ' $' : '');
  const val = (p, k) => p && p[k] ? p[k].value : null;
  const yr = (p, k) => p && p[k] ? p[k].year : '';
  const fmtDate = d => new Date(d).toLocaleDateString(locale(), { day: 'numeric', month: 'short', year: 'numeric' });
  const fmtLong = d => new Date(d).toLocaleDateString(locale(), { day: 'numeric', month: 'long', year: 'numeric' });
  const norm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const lvlBadge = (l, cls = '') => `<span class="lvl ${cls}" style="background:${RC[l || 0]}">${l || '–'}</span>`;
  const loadScript = src => new Promise((ok, ko) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = ko; document.head.appendChild(s); });
  const detail = () => (window.VS_CDETAIL || {})[ISO] || null;

  /* ------------------------------------------------ traduction des extraits (API Translator de Chrome / Edge, sur l'appareil) */
  const trKey = (tgt, text) => tgt + '|' + text;
  const TRMEM = (() => { try { return JSON.parse(localStorage.getItem('vs-tr') || '{}') || {}; } catch (e) { return {}; } })();
  // Texte dans une langue différente de celle du rapport : marqué pour la traduction (déjà traduit s'il est en mémoire)
  function tx(text, src) {
    if (!text) return '';
    if (src === lang) return esc(text);
    const done = TRMEM[trKey(lang, text)];
    if (done) return `<span class="tr-done" title="${esc(L('Texte original', 'Original text'))} : ${esc(text)}">${esc(done)}</span>`;
    return `<span class="tr" data-src="${src}" lang="${src}">${esc(text)}</span>`;
  }
  async function translateAll(btn) {
    if (!('Translator' in self)) { alert(L('La traduction automatique sur l\'appareil nécessite un navigateur Chrome ou Edge récent. Utilisez sinon le lien « Google Traduction » de chaque source.', 'On-device translation needs a recent Chrome or Edge. Otherwise use the Google Translate link of each source.')); return; }
    const els = $$('.tr[data-src]');
    if (!els.length) return;
    btn.disabled = true;
    const pairs = {};
    let n = 0;
    for (const el of els) {
      let src = el.dataset.src; const text = el.textContent;
      try {
        if (src === 'xx') {
          if (!('LanguageDetector' in self)) continue;
          pairs._det = pairs._det || await self.LanguageDetector.create();
          const d = await pairs._det.detect(text);
          src = d && d[0] && d[0].confidence > 0.5 ? d[0].detectedLanguage.slice(0, 2) : '';
          if (!src || src === lang) continue;
        }
        if (!(src in pairs)) {
          const av = await self.Translator.availability({ sourceLanguage: src, targetLanguage: lang });
          pairs[src] = av === 'unavailable' ? null : await self.Translator.create({ sourceLanguage: src, targetLanguage: lang });
        }
        if (!pairs[src]) continue;
        const out = await pairs[src].translate(text);
        if (out) { TRMEM[trKey(lang, text)] = out; el.textContent = out; el.className = 'tr-done'; el.title = L('Texte original', 'Original text') + ' : ' + text; el.removeAttribute('data-src'); }
        if (++n % 10 === 0) btn.querySelector('.lbl').textContent = `${Math.round(100 * n / els.length)} %`;
      } catch (e) { /* on garde l'original */ }
    }
    try { localStorage.setItem('vs-tr', JSON.stringify(TRMEM)); } catch (e) { /* stockage plein */ }
    btn.disabled = false; btn.querySelector('.lbl').textContent = L('Traduit', 'Translated'); btn.setAttribute('aria-pressed', 'true');
  }

  /* ------------------------------------------------ matrice des risques */
  const RISK_ROWS = [
    { key: 'terrorism', fr: 'Terrorisme', en: 'Terrorism', cats: ['terrorism'] },
    { key: 'conflict', fr: 'Conflit armé / violence politique', en: 'Armed conflict / political violence', cats: ['armed_conflict'] },
    { key: 'attack', fr: 'Attaques, enlèvements, violences armées', en: 'Attacks, kidnapping, armed violence', cats: ['attack'] },
    { key: 'unrest', fr: 'Troubles civils, manifestations, grèves', en: 'Civil unrest, protests, strikes', cats: ['unrest'] },
    { key: 'political', fr: 'Instabilité politique', en: 'Political instability', cats: ['political'] },
    { key: 'crime', fr: 'Criminalité', en: 'Crime', cats: ['crime'] },
    { key: 'cyber', fr: 'Cyber et infrastructures', en: 'Cyber and infrastructure', cats: ['cyber', 'infrastructure'] },
    { key: 'natural', fr: 'Catastrophes naturelles et climat', en: 'Natural hazards and climate', cats: ['earthquake', 'cyclone', 'storm', 'flood', 'wildfire', 'volcano', 'drought', 'landslide', 'extreme_temp'] },
    { key: 'health', fr: 'Santé et épidémies', en: 'Health and epidemics', cats: ['health'] },
  ];
  const countFor = (stats, w, cats) => { const s = (stats[w] || {}).by_cat || {}; return cats.reduce((n, c) => n + (s[c] || 0), 0); };
  const incidentLevel = n90 => n90 >= 60 ? 5 : n90 >= 20 ? 4 : n90 >= 5 ? 3 : n90 >= 1 ? 2 : 1;
  const usReasons = iso => ((((RISK[iso] || {}).advisories || {})['US State Dept'] || {}).reasons) || [];
  function rateRows(iso) {
    const st = STATS[iso] || {}, pr = P[iso] || {}, fb = FB[iso] || {}, r = RISK[iso];
    const maxAdv = r ? Math.max(0, ...Object.values(r.advisories || {}).map(a => a.level)) : 0;
    const stab = val(pr, 'wgi_stability'), hom = val(pr, 'homicide_rate');
    const us = usReasons(iso);
    return RISK_ROWS.map(row => {
      const c = { h24: countFor(st, '24h', row.cats), h72: countFor(st, '72h', row.cats), d7: countFor(st, '7d', row.cats), d90: countFor(st, '90d', row.cats) };
      let lvl = incidentLevel(c.d90);
      const basis = [];
      const bump = (v, why) => { if (v > lvl) lvl = v; if (why) basis.push(why); };
      if (row.key === 'terrorism' && fb.terrorist_groups) bump(maxAdv >= 4 ? 4 : 3, L('groupes terroristes actifs', 'active terrorist groups'));
      if (row.key === 'terrorism' && us.includes('terrorism')) bump(3, L('cité par le Département d\'État', 'cited by US State Dept'));
      if (row.key === 'conflict' && maxAdv >= 4) bump(4, L('avis « ne pas se rendre »', '“do not travel” advisory'));
      if (row.key === 'attack' && us.includes('kidnapping')) bump(maxAdv >= 4 ? 5 : 4, L('risque d\'enlèvement (États-Unis)', 'kidnapping risk (US)'));
      if (row.key === 'unrest' && us.includes('unrest')) bump(3, L('troubles civils cités (États-Unis)', 'civil unrest cited (US)'));
      if (row.key === 'political' && stab != null) bump(stab < 15 ? 5 : stab < 30 ? 4 : stab < 50 ? 3 : stab < 70 ? 2 : 1, L(`stabilité politique ${num(stab, 0)}/100`, `political stability ${num(stab, 0)}/100`));
      if (row.key === 'crime' && hom != null) bump(hom >= 20 ? 5 : hom >= 10 ? 4 : hom >= 5 ? 3 : hom >= 2 ? 2 : 1, L(`${num(hom)} homicides/100 000 hab.`, `${num(hom)} homicides per 100k`));
      if (row.key === 'crime' && us.includes('crime')) bump(3, L('criminalité citée (États-Unis)', 'crime cited (US)'));
      if (row.key === 'natural' && fb.natural_hazards) bump(2, L('aléas naturels connus', 'known natural hazards'));
      if (row.key === 'natural' && us.includes('natural')) bump(3, L('catastrophes naturelles citées (États-Unis)', 'natural disasters cited (US)'));
      if (row.key === 'cyber') bump(2, L('menace mondiale de fond', 'global baseline threat'));
      if (row.key === 'health' && us.includes('health')) bump(3, L('offre de soins limitée (États-Unis)', 'limited health care (US)'));
      if (c.d90) basis.push(L(`${c.d90} incident(s) sur 90 j`, `${c.d90} incident(s) in 90 d`));
      const weekly = c.d90 / 13;
      const trend = c.d90 < 3 ? 0 : c.d7 > weekly * 1.5 ? 1 : c.d7 < weekly * 0.5 ? -1 : 0;
      return { ...row, lvl: Math.min(5, lvl), c, trend, basis };
    }).sort((a, b) => b.lvl - a.lvl || b.c.d90 - a.c.d90);
  }

  /* ------------------------------------------------ rubriques des conseils FCDO (texte officiel britannique, OGL v3) */
  const THEMES = [
    { k: 'terrorism', icon: 'crosshair', fr: 'Terrorisme', en: 'Terrorism', row: 'terrorism', us: ['terrorism'] },
    { k: 'conflict', icon: 'swords', fr: 'Conflit armé et violence politique', en: 'Armed conflict and political violence', row: 'conflict', us: ['conflict', 'landmines'] },
    { k: 'kidnap', icon: 'user-x', fr: 'Enlèvements', en: 'Kidnapping', row: 'attack', us: ['kidnapping'] },
    { k: 'detention', icon: 'gavel', fr: 'Détention arbitraire et espionnage', en: 'Wrongful detention and espionage', us: ['detention'] },
    { k: 'crime', icon: 'siren', fr: 'Criminalité', en: 'Crime', row: 'crime', us: ['crime'] },
    { k: 'unrest', icon: 'megaphone', fr: 'Troubles civils et manifestations', en: 'Civil unrest and protests', row: 'unrest', us: ['unrest'] },
    { k: 'surveillance', icon: 'eye', fr: 'Surveillance, photographie et communications', en: 'Surveillance, photography and communications' },
    { k: 'natural', icon: 'waves', fr: 'Catastrophes naturelles et climat', en: 'Natural hazards and climate', row: 'natural', us: ['natural'] },
    { k: 'cyber', icon: 'radio-tower', fr: 'Cyber et infrastructures', en: 'Cyber and infrastructure', row: 'cyber' },
    { k: 'other', icon: 'shield-alert', fr: 'Autres points de vigilance', en: 'Other points of vigilance' },
  ];
  // ordre de reconnaissance des titres (du plus précis au plus général)
  const MATCH = [
    ['kidnap', /kidnap|hostage/i], ['detention', /detention|detain|arrest|espionage|spying|possible charges/i],
    ['surveillance', /photograph|camera|drone|surveillance|internet|mobile phone|communications|social media|satellite phone|telecommunication/i],
    ['terrorism', /terror/i], ['unrest', /protest|demonstration|political situation|strike|unrest|elections?\b|curfew|riot|political tension/i],
    ['conflict', /conflict|military|border|landmine|unexploded|hostilities|missile|air raid|shelling|\bwar\b|security situation|fighting|tensions|armed groups|militia|insurgen|regional risk/i],
    ['crime', /crime|robber|theft|scam|fraud|spiking|sexual|personal attack|carjack|pickpocket|mugging|burglar|violence against|drink|romance|dating|extortion|cartel|gang/i],
    ['culture', /laws|cultural|dress|religio|alcohol|drugs|lgbt|women|ramadan|money|antiquit|smoking|vaping|same-sex|relationship|behaviour|customs|food|pork|gambling|public displays|identification|id documents|visas? overstay|dual|marriage|wildlife product|currency|tipping|language|clothing|swearing|sharia|blasphemy|conversion|holidays/i],
    ['natural', /weather|natural disaster|earthquake|flood|hurricane|cyclone|typhoon|monsoon|volcan|wildfire|bushfire|tsunami|heat|rainy season|landslide|avalanche|sandstorm|dust|climate|storm|snow|cold/i],
    ['transport', /transport|road|driving|drive|taxi|air travel|airline|flight|sea travel|rail|train|bus|boat|ferr|motorbike|motorcycle|cycling|piracy|maritime|river|metro|car hire|licen[cs]e/i],
    ['outdoor', /outdoor|adventure|swimming|beach|hiking|trekking|mountain|diving|wildlife|safari|water sports|climbing|skiing|desert travel|jungle/i],
    ['cyber', /cyber|power cut|electricity|infrastructure|outage/i],
  ];
  function bucketOf(h) { for (const [k, rx] of MATCH) if (rx.test(h)) return k; return null; }
  function fcdoBuckets(fc) {
    const out = {};
    const add = (k, s) => (out[k] = out[k] || []).push(s);
    ((fc && fc.parts && fc.parts.safety) || []).forEach((s, i, arr) => {
      if (s.l <= 2) s._b = bucketOf(s.h) || 'other';
      else {
        let parent = null;
        for (let j = i - 1; j >= 0; j--) if (arr[j].l < s.l) { parent = arr[j]; break; }
        s._b = bucketOf(s.h) || (parent && parent._b) || 'other';
      }
      if (s.b.length || s.l <= 2) add(s._b, s);
    });
    return out;
  }
  function fcdoHtml(secs, opts = {}) {
    if (!secs || !secs.length) return '';
    const body = secs.map(s => {
      const blocks = s.b.map(([k, v]) => k === 'ul' ? `<ul>${v.map(x => `<li>${tx(x, 'en')}</li>`).join('')}</ul>` : `<p>${tx(v, 'en')}</p>`).join('');
      if (!blocks && !opts.keepEmpty) return '';
      return `${s.h && !opts.noHead ? `<h4>${tx(s.h, 'en')}</h4>` : ''}${blocks}`;
    }).join('');
    if (!body) return '';
    const fc = (detail() || {}).fcdo || {};
    return `<div class="official">${body}<div class="src">FCDO (${L('Royaume-Uni', 'UK')}) · ${fc.updated ? L('mis à jour le ', 'updated ') + fmtDate(fc.updated) : ''} · <a href="${esc(fc.url || 'https://www.gov.uk/foreign-travel-advice')}">gov.uk</a> · Open Government Licence v3.0</div></div>`;
  }

  /* ------------------------------------------------ villes */
  const ACT_LBL = () => [L('aucun incident', 'no incident'), L('faible', 'low'), L('modérée', 'moderate'), L('élevée', 'high'), L('très élevée', 'very high')];
  const ACT_COL = ['#AEB8C2', '#95B443', '#E3A92B', '#E0722C', '#C23347'];
  const actBars = l => `<span class="act" title="${esc(L('Activité incidents 90 j', 'Incident activity 90 d'))} : ${esc(ACT_LBL()[l])}">${[1, 2, 3, 4].map(i => `<span style="${i <= l ? `background:${ACT_COL[l]};height:${4 + i * 3}px` : `height:${4 + i * 3}px`}"></span>`).join('')}</span>`;
  const cityName = c => lang === 'fr' ? (c.name_fr || c.name) : c.name;
  const evTitle = e => lang === 'fr' ? (e.tf || e.t) : (e.te || e.t);
  function hospitalsIn(city) {
    const h = (PRACT[ISO] || {}).hospitals || [];
    const keys = new Set([norm(city.name), norm(city.name_fr)].concat(((city.note || {}).aliases || []).map(norm)));
    return h.filter(x => keys.has(norm(x.city))).slice(0, 4);
  }

  /* ------------------------------------------------ recommandations sûreté */
  function recommendations(iso, rows) {
    const lvl = (RISK[iso] || {}).level || 2;
    const top = rows.filter(r => r.lvl >= 3).map(r => r.key);
    const rec = [];
    const add = (title, items) => rec.push({ title, items });
    const general = {
      1: [L('Politique voyage standard ; enregistrement des déplacements (Ariane pour les ressortissants français).', 'Standard travel policy; register trips with your embassy.'), L('Sensibilisation sûreté de base avant départ.', 'Basic pre-travel security awareness.')],
      2: [L('Politique voyage standard avec enregistrement systématique (Ariane) et suivi des voyageurs.', 'Standard travel policy with systematic registration and traveller tracking.'), L('Briefing sûreté avant départ ; consignes de discrétion.', 'Pre-travel security briefing; low-profile guidance.')],
      3: [L('Validation hiérarchique des déplacements et briefing sûreté obligatoire.', 'Management approval of trips and mandatory security briefing.'), L('Journey management : itinéraires validés, horaires, points de contact.', 'Journey management: validated routes, schedules, check-ins.'), L('Hébergement dans des hôtels évalués ; transport avec chauffeur de confiance.', 'Vetted hotels only; trusted driver transport.')],
      4: [L('Déplacements limités aux besoins essentiels, validés par la direction sûreté.', 'Essential travel only, approved by the security function.'), L('Prestataire sûreté local, suivi GPS et points de contact réguliers.', 'Local security provider, GPS tracking and regular check-ins.'), L('Plan d\'évacuation et de mise à l\'abri testé ; assurance rapatriement et K&R.', 'Tested evacuation and shelter plan; repatriation and K&R insurance.')],
      5: [L('Déplacements proscrits sauf mission vitale, sur décision de la direction.', 'Travel prohibited except for vital missions, on executive decision.'), L('Escorte armée ou véhicules protégés selon les zones ; mouvements de jour uniquement.', 'Armed escort or protected vehicles depending on area; daylight movements only.'), L('Plan d\'évacuation actif, stocks de mise à l\'abri (hibernation), communications satellitaires.', 'Active evacuation plan, hibernation stocks, satellite communications.'), L('Revue quotidienne de la situation et critères de déclenchement de l\'évacuation.', 'Daily situation review and evacuation triggers.')],
    };
    add(L(`Posture générale — niveau ${lvl} (${riskName(lvl)})`, `General posture — level ${lvl} (${riskName(lvl)})`), general[lvl] || general[2]);
    const specific = {
      terrorism: [L('Éviter les lieux de rassemblement, lieux de culte et sites symboliques lors des périodes sensibles.', 'Avoid gatherings, places of worship and symbolic sites during sensitive periods.'), L('Varier itinéraires et horaires ; repérer les issues dans les lieux fréquentés.', 'Vary routes and schedules; identify exits in crowded venues.')],
      conflict: [L('Cartographier les zones interdites et zones de front ; interdire tout déplacement non validé hors des zones autorisées.', 'Map no-go zones and front lines; no unapproved movement outside permitted areas.'), L('Abri renforcé sur site, protocole alerte aérienne / tirs indirects.', 'Hardened shelter on site, air-raid / indirect fire protocol.')],
      attack: [L('Profil discret, pas de signes extérieurs de richesse ; transport sécurisé porte-à-porte.', 'Low profile, no visible wealth; secure door-to-door transport.'), L('Sensibilisation anti-enlèvement ; assurance K&R et cellule de crise identifiée.', 'Kidnap-avoidance awareness; K&R insurance and identified crisis cell.')],
      unrest: [L('Éviter les manifestations ; suivre les appels à la grève et à la mobilisation.', 'Avoid demonstrations; monitor strike and protest calls.'), L('Prévoir télétravail, stocks et itinéraires alternatifs pour les sites.', 'Plan remote work, supplies and alternative routes for sites.')],
      political: [L('Suivre le calendrier politique (élections, votes, décisions judiciaires) et anticiper les couvre-feux.', 'Track the political calendar (elections, votes, court rulings) and anticipate curfews.'), L('Maintenir des liens avec l\'ambassade et les réseaux d\'entreprises locaux.', 'Maintain links with the embassy and local business networks.')],
      crime: [L('Sécurité physique des sites (contrôle d\'accès, vidéosurveillance, gardiennage) adaptée au niveau de criminalité.', 'Site physical security (access control, CCTV, guarding) sized to crime level.'), L('Limiter les déplacements de nuit ; distributeurs dans des lieux sûrs.', 'Limit night travel; use ATMs in secure locations.')],
      cyber: [L('Appareils dédiés pour les pays à risque, VPN, chiffrement ; vigilance face à l\'hameçonnage.', 'Dedicated devices for high-risk countries, VPN, encryption; phishing vigilance.')],
      natural: [L('Plan de continuité d\'activité tenant compte des saisons à risque (cyclones, moussons, feux).', 'Business continuity plan covering risk seasons (cyclones, monsoon, fires).'), L('Consignes séisme / inondation connues du personnel ; kits d\'urgence sur site.', 'Staff trained on earthquake/flood drills; emergency kits on site.')],
      health: [L('Vérifier vaccinations et prophylaxies avant départ ; assurance médicale et évacuation sanitaire.', 'Check vaccinations and prophylaxis before travel; medical and medevac insurance.'), L('Identifier les établissements de santé de référence près des sites.', 'Identify reference medical facilities near sites.')],
    };
    top.forEach(k => { if (specific[k]) add(RISK_ROWS.find(r => r.key === k)[lang], specific[k]); });
    if (usReasons(iso).includes('detention')) add(L('Détention arbitraire', 'Wrongful detention'), [L('Évaluer le profil des voyageurs (nationalité, binationaux, fonctions sensibles) avant validation.', 'Assess traveller profile (nationality, dual nationals, sensitive roles) before approval.'), L('Appareils « propres », aucun contenu sensible ; pas de photo de sites officiels ; contacts consulaires connus.', 'Clean devices, no sensitive content; no photos of official sites; known consular contacts.')]);
    add(L('Sites et personnels permanents', 'Permanent sites and staff'), [
      L('Audit de sûreté des sites (accès, périmètre, protection des personnes) et plan de sûreté formalisé.', 'Site security audit (access, perimeter, personnel protection) and formal security plan.'),
      L('Arbre d\'alerte et exercices de gestion de crise au moins une fois par an.', 'Alert tree and crisis-management drills at least once a year.'),
      L('Veille quotidienne sur le pays et alertes automatiques dans un rayon défini autour de chaque site.', 'Daily country monitoring and automatic alerts within a defined radius around each site.')]);
    return rec;
  }

  /* ------------------------------------------------ angles business */
  function businessAngles(iso) {
    const pr = P[iso] || {}, fb = FB[iso] || {}, r = RISK[iso];
    const out = [];
    const g = pr.imf_growth || {}, years = Object.keys(g).sort();
    const nextG = years.length ? g[years[years.length - 1]] : val(pr, 'gdp_growth');
    if (nextG != null) {
      if (nextG >= 4) out.push(L(`Croissance soutenue attendue (${num(nextG)} % prévu par le FMI) : marché en expansion, besoins en infrastructures, services et biens d'équipement.`, `Strong expected growth (${num(nextG)}% IMF forecast): expanding market, demand for infrastructure, services and equipment.`));
      else if (nextG < 1) out.push(L(`Croissance faible (${num(nextG)} %) : privilégier les créneaux de productivité, d'efficacité et de restructuration.`, `Weak growth (${num(nextG)}%): focus on productivity, efficiency and restructuring niches.`));
    }
    const wb = pr.wb_projects;
    if (wb && wb.count) {
      const sectors = Object.keys(wb.sectors || {}).filter(s => s !== 'Other').slice(0, 3).join(', ');
      out.push(L(`${wb.count} projets actifs de la Banque mondiale (${money(wb.total_usd)}) : marchés publics financés par bailleurs${sectors ? `, en particulier ${sectors}` : ''}.`, `${wb.count} active World Bank projects (${money(wb.total_usd)}): donor-funded public procurement${sectors ? `, notably ${sectors}` : ''}.`));
    }
    const fdi = val(pr, 'fdi_inflows_pct_gdp');
    if (fdi != null && fdi >= 3) out.push(L(`Pays attractif pour l'investissement étranger (IDE ≈ ${num(fdi)} % du PIB).`, `Attractive for foreign investment (FDI ≈ ${num(fdi)}% of GDP).`));
    if (fb.natural_resources) out.push(L(`Filières liées aux ressources naturelles : ${fb.natural_resources.split(',').slice(0, 5).join(',')}.`, `Natural-resource value chains: ${fb.natural_resources.split(',').slice(0, 5).join(',')}.`));
    if (fb.industries) out.push(L(`Industries principales : ${fb.industries.split(',').slice(0, 6).join(',')}.`, `Main industries: ${fb.industries.split(',').slice(0, 6).join(',')}.`));
    if (r && r.level >= 3) out.push(L('Demande structurelle en services de sûreté : conseil, protection des sites et des personnes, formation, gestion de crise, veille.', 'Structural demand for security services: consulting, site and personnel protection, training, crisis management, intelligence.'));
    const rq = val(pr, 'wgi_regulation'), cc = val(pr, 'wgi_corruption');
    if (rq != null && rq < 35) out.push(L('Environnement réglementaire difficile : partenaire local fiable et due diligence approfondie indispensables.', 'Difficult regulatory environment: reliable local partner and thorough due diligence essential.'));
    if (cc != null && cc < 30) out.push(L('Risque de corruption élevé : programme de conformité (loi Sapin II, FCPA) et vérification des intermédiaires.', 'High corruption risk: compliance programme (Sapin II, FCPA) and intermediary vetting.'));
    return out;
  }

  /* ------------------------------------------------ avis des ministères */
  const MINS = () => [['MEAE (France)', 'meae', 'France'], ['FCDO (UK)', 'fcdo', L('Royaume-Uni', 'United Kingdom')], ['US State Dept', 'us', L('États-Unis', 'United States')], ['Auswärtiges Amt (DE)', 'de', L('Allemagne', 'Germany')]];
  const MIN_LBLS = () => ({ 1: L('Vigilance normale', 'Normal precautions'), 2: L('Vigilance renforcée', 'Increased caution'), 3: L('Déconseillé sauf raison impérative', 'Reconsider / essential travel only'), 4: L('Formellement déconseillé', 'Do not travel') });
  const US_REASONS = () => ({ terrorism: L('terrorisme', 'terrorism'), crime: L('criminalité', 'crime'), unrest: L('troubles civils', 'civil unrest'), kidnapping: L('enlèvements', 'kidnapping'), detention: L('détention arbitraire', 'wrongful detention'), conflict: L('conflit armé', 'armed conflict'), health: L('santé', 'health'), natural: L('catastrophes naturelles', 'natural disasters'), landmines: L('mines', 'landmines') });
  function advList(iso) {
    const advs = (RISK[iso] || {}).advisories || {};
    const MIN_LBL = MIN_LBLS();
    return MINS().map(([src, mode, who]) => {
      const a = advs[src];
      if (!a) return { src, mode, who, a: null };
      const lvl = mode === 'us' ? a.level : (a.max || a.level);
      let label = mode === 'us' ? a.label : MIN_LBL[lvl];
      if (a.parts && lvl > 1 && mode !== 'us') label += L(' (certaines zones)', ' (some areas)');
      return { src, mode, who, a, lvl, label };
    });
  }

  /* ------------------------------------------------ agenda */
  const MUSLIM = new Set('AF AL AZ BH BD BN BF TD KM DJ EG GM GN ID IR IQ JO KZ XK KW KG LB LY MY MV ML MR MA NE NG OM PK PS QA SA SN SL SO SD SY TJ TN TR TM AE UZ EH YE'.split(' '));
  function agenda(iso, days = 365) {
    const cal = (window.VS_CALENDAR || {}).events || [];
    const today = new Date().toISOString().slice(0, 10), end = new Date(Date.now() + days * 864e5).toISOString().slice(0, 10);
    return cal.filter(e => (e.e || e.d) >= today && e.d <= end && (e.iso === iso || (!e.iso && e.type === 'religious' && MUSLIM.has(iso))))
      .sort((a, b) => a.d.localeCompare(b.d));
  }
  const agType = e => ['holiday', 'election', 'religious'].includes(e.type) ? e.type : 'other';

  /* ------------------------------------------------ sections */
  const SECTIONS = [
    { id: 'synthese', icon: 'gauge', fr: 'Synthèse', en: 'Executive summary', kfr: 'L\'essentiel en une page', ken: 'Key points on one page' },
    { id: 'risques', icon: 'shield', fr: 'Évaluation des risques', en: 'Risk assessment', kfr: 'Matrice par menace, tendances et fondements', ken: 'Threat matrix, trends and basis' },
    { id: 'surete', icon: 'shield-alert', fr: 'Sûreté détaillée', en: 'Security in detail', kfr: 'Terrorisme, enlèvements, criminalité, troubles, surveillance…', ken: 'Terrorism, kidnapping, crime, unrest, surveillance…' },
    { id: 'recommandations', icon: 'clipboard-check', fr: 'Recommandations', en: 'Recommendations', kfr: 'Posture pour les voyageurs, personnels et sites', ken: 'Posture for travellers, staff and sites' },
    { id: 'villes', icon: 'building', fr: 'Villes', en: 'Cities', kfr: 'Analyse ville par ville : exposition, zones sensibles, usages', ken: 'City by city: exposure, sensitive areas, customs' },
    { id: 'incidents', icon: 'activity', fr: 'Incidents récents', en: 'Recent incidents', kfr: 'Événements détectés par Angor sur 30 jours', ken: 'Events detected by Angor over 30 days' },
    { id: 'avis', icon: 'landmark', fr: 'Avis officiels', en: 'Official advisories', kfr: 'France, Royaume-Uni, États-Unis, Allemagne', ken: 'France, UK, US, Germany' },
    { id: 'voyage', icon: 'plane', fr: 'Voyage et déplacements', en: 'Travel and getting around', kfr: 'Entrée, aéroports, route, transports', ken: 'Entry, airports, roads, transport' },
    { id: 'sante', icon: 'heart-pulse', fr: 'Santé et secours', en: 'Health and emergency', kfr: 'Numéros d\'urgence, vaccins, maladies, hôpitaux', ken: 'Emergency numbers, vaccines, diseases, hospitals' },
    { id: 'culture', icon: 'users', fr: 'Lois, usages et culture', en: 'Laws, customs and culture', kfr: 'Ce qu\'il faut savoir pour se comporter', ken: 'What to know to behave appropriately' },
    { id: 'calendrier', icon: 'calendar', fr: 'Calendrier', en: 'Calendar', kfr: 'Fêtes, élections et échéances des 12 prochains mois', ken: 'Holidays, elections and key dates for the next 12 months' },
    { id: 'economie', icon: 'briefcase', fr: 'Économie et affaires', en: 'Economy and business', kfr: 'Indicateurs, angles business, projets financés', ken: 'Indicators, business angles, funded projects' },
    { id: 'contexte', icon: 'globe', fr: 'Contexte pays', en: 'Country background', kfr: 'Géographie, institutions, société, gouvernance', ken: 'Geography, institutions, society, governance' },
    { id: 'prestataires', icon: 'radio-tower', fr: 'Communications et prestataires', en: 'Communications and providers', kfr: 'Télécoms, sûreté, assistance', ken: 'Telecoms, security, assistance' },
    { id: 'sources', icon: 'book-open-text', fr: 'Sources et méthode', en: 'Sources and method', kfr: 'D\'où viennent les informations', ken: 'Where the information comes from' },
  ];
  let excluded = new Set(store.get('vs-rep-excluded', []));
  const secNum = id => String(SECTIONS.findIndex(s => s.id === id) + 1).padStart(2, '0');
  function sec(id, body, flagTxt = '') {
    const s = SECTIONS.find(x => x.id === id);
    if (!body) return '';
    return `<section class="page${excluded.has(id) ? ' excluded' : ''}" id="${id}" data-excluded="${esc(L('Exclu du PDF', 'Excluded from PDF'))}">
      <div class="sec-head"><div class="sec-num">${secNum(id)}</div><div><h2 class="sec-title">${esc(L(s.fr, s.en))}</h2><div class="sec-kicker">${esc(L(s.kfr, s.ken))}</div></div><div class="sec-flag">${flagTxt}</div></div>
      ${body}</section>`;
  }

  function coverHtml(iso) {
    const r = RISK[iso], pr = P[iso] || {}, fb = FB[iso] || {}, b = pr.basics || {}, dt = detail() || {};
    const lvl = r ? r.level : 0;
    const f = FEATURES.find(x => x.properties.iso2 === iso);
    const cap = ((dt.cities || []).find(c => c.capital) || {});
    const facts = [[L('Capitale', 'Capital'), (lang === 'fr' ? cap.name_fr : cap.name) || b.capital || fb.capital || '—'], [L('Population', 'Population'), big(val(pr, 'population'))],
      [L('Fuseau horaire', 'Time zone'), cap.tz ? tzLabel(cap.tz) : '—'], [L('Indicatif', 'Calling code'), ((PRACT[iso] || {}).calling_code || []).map(c => c.startsWith('+') ? c : '+' + c)[0] || '—']];
    return `<section class="page cover" id="couverture">
      ${f ? `<svg class="c-map" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><path d="${shapePath(f.geometry)}"/></svg>` : ''}
      <div class="c-top"><span class="c-brand"><span class="c-mark"></span>${esc((D.settings || {}).product_name || 'Angor Intelligence')}</span><span>${esc(L('Dossier pays · sûreté & intelligence économique', 'Country file · security & business intelligence'))}</span></div>
      <div class="c-main">
        <div class="c-kicker">${esc(L('Rapport pays', 'Country report'))} · ${esc(regionOf(iso))}</div>
        <div class="c-rule"></div>
        <h1>${flag(iso, 160)}${esc(cname(iso))}</h1>
        <div class="c-sub">${esc(L('Édité le', 'Issued on'))} ${fmtLong(new Date())} · ${esc(L('données du', 'data as of'))} ${D.generated ? fmtLong(D.generated) : '—'}</div>
        <div class="c-risk">${lvlBadge(lvl)}<div><div class="rn">${esc(L('Risque global', 'Overall risk'))} : ${esc(riskName(lvl))}</div><div class="rd">${esc(riskDesc(lvl))}</div>
          <div class="c-scale">${[1, 2, 3, 4, 5].map(i => `<span class="${i === lvl ? 'on' : ''}" style="background:${RC[i]}"></span>`).join('')}</div></div></div>
      </div>
      <div>
        <div class="c-facts">${facts.map(([k, v]) => `<div class="c-fact"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join('')}</div>
        <div class="c-adv">${advList(iso).map(x => `<div><b>${esc(x.who)}</b>${x.a ? `<i style="background:${MIN_COLORS[x.lvl] || '#8A96A3'}"></i>${esc(x.label)}` : esc(L('Pas d\'avis', 'No advisory'))}</div>`).join('')}</div>
      </div>
      <div class="c-foot" style="margin-top:12mm"><span>${esc(L('Outil d\'aide à la décision fondé sur des sources ouvertes. Ne garantit pas l\'exhaustivité ; à compléter par l\'analyse d\'un professionnel de la sûreté.', 'Decision-support tool based on open sources. Not exhaustive; to be complemented by a security professional\'s analysis.'))}</span><span class="conf">${esc(L('Confidentiel · usage interne', 'Confidential · internal use'))}</span></div>
    </section>`;
  }
  function tzLabel(tz) {
    try {
      const p = new Intl.DateTimeFormat('en-US', { timeZone: tz, timeZoneName: 'shortOffset' }).formatToParts(new Date()).find(x => x.type === 'timeZoneName');
      return p ? p.value.replace('GMT', 'UTC') : tz;
    } catch (e) { return tz; }
  }
  // contour du pays en SVG (filigrane de la couverture)
  function shapePath(g) {
    const polys = g.type === 'MultiPolygon' ? g.coordinates : [g.coordinates];
    let pts = []; polys.forEach(p => { pts = pts.concat(p[0]); });
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    const k = 100 / Math.max(x1 - x0, y1 - y0 || 1);
    const ox = (100 - (x1 - x0) * k) / 2, oy = (100 - (y1 - y0) * k) / 2;
    return polys.map(p => 'M' + p[0].map(([x, y]) => `${(ox + (x - x0) * k).toFixed(1)},${(oy + (y1 - y) * k).toFixed(1)}`).join('L') + 'Z').join('');
  }

  function synthHtml(iso, rows) {
    const r = RISK[iso], st = STATS[iso] || {}, dt = detail() || {};
    const lvl = r ? r.level : 0;
    const n7 = (st['7d'] || {}).total || 0, n90 = (st['90d'] || {}).total || 0, n30 = (st['30d'] || {}).total;
    const weekly = n90 / 13;
    const trend = n90 < 3 ? 0 : n7 > weekly * 1.5 ? 1 : n7 < weekly * 0.5 ? -1 : 0;
    const severe = EVENTS.filter(e => e.country === iso && e.severity >= 3 && Date.now() - Date.parse(e.date) < 30 * 864e5).length;
    const top = rows.filter(x => x.lvl >= 3).slice(0, 4);
    const us = usReasons(iso);
    const hot = (dt.cities || []).filter(c => (c.note && c.note.level >= 4) || c.stats.level >= 3).slice(0, 4);
    const next = agenda(iso, 120).filter(e => e.type === 'election' || e.type === 'religious' || e.type === 'holiday').slice(0, 3);
    const keys = [];
    keys.push(['shield', L(`<b>Risque global ${lvl} – ${esc(riskName(lvl))}.</b> ${esc(riskDesc(lvl))}`, `<b>Overall risk ${lvl} – ${esc(riskName(lvl))}.</b> ${esc(riskDesc(lvl))}`)]);
    if (top.length) keys.push(['triangle-alert', L('Menaces principales : ', 'Main threats: ') + top.map(x => `<b>${esc(x[lang])}</b> (${x.lvl})`).join(', ') + '.']);
    if (us.length) keys.push(['landmark', L('Le Département d\'État américain cite : ', 'The US State Department cites: ') + us.map(k => esc(US_REASONS()[k] || k)).join(', ') + '.']);
    keys.push(['activity', L(`${n7} incident(s) détecté(s) sur 7 jours et ${n90} sur 90 jours${severe ? `, dont ${severe} grave(s) ou critique(s) sur 30 jours` : ''} — tendance ${trend > 0 ? 'en hausse' : trend < 0 ? 'en baisse' : 'stable'}.`, `${n7} incident(s) detected in 7 days and ${n90} in 90 days${severe ? `, including ${severe} serious or critical in 30 days` : ''} — trend ${trend > 0 ? 'rising' : trend < 0 ? 'falling' : 'stable'}.`)]);
    if (hot.length) keys.push(['building', L('Villes à suivre : ', 'Cities to watch: ') + hot.map(c => `<b>${esc(cityName(c))}</b>${c.note ? ` (${L('niveau', 'level')} ${c.note.level})` : ` (${L('activité', 'activity')} ${esc(ACT_LBL()[c.stats.level])})`}`).join(', ') + '.']);
    if (next.length) keys.push(['calendar', L('À venir : ', 'Coming up: ') + next.map(e => `${esc(lang === 'fr' ? e.t_fr : (e.t_en || e.t_fr))} (${fmtDate(e.d)})`).join(' ; ') + '.']);
    const pr = P[ISO] || {};
    const kpis = [[n7, L('incidents · 7 j', 'incidents · 7 d'), trend > 0 ? '↑' : trend < 0 ? '↓' : '→'], [n90, L('incidents · 90 j', 'incidents · 90 d'), ''],
      [severe, L('graves · 30 j', 'serious · 30 d'), ''], [val(pr, 'wgi_stability') != null ? num(val(pr, 'wgi_stability'), 0) : '—', L('stabilité politique /100', 'political stability /100'), '']];
    const note = store.get('vs-rep-note-' + iso, '');
    return sec('synthese', `
      <div class="exec">
        <div><ul class="keys">${keys.map(([i, h]) => `<li><span class="ki">${icon(i, 13)}</span><span>${h}</span></li>`).join('')}</ul>
          <div class="kpis">${kpis.map(([v, k, d]) => `<div class="kpi"><div class="v">${esc(v)} <span class="d">${d}</span></div><div class="k">${esc(k)}</div></div>`).join('')}</div></div>
        <div class="panel"><h3>${icon('landmark', 13)} ${esc(L('Avis aux voyageurs', 'Travel advisories'))}</h3>
          <div class="adv-grid">${advList(iso).map(x => `<div class="adv-row"><span class="dot" style="background:${x.a ? MIN_COLORS[x.lvl] : '#C9D1D9'}"></span><div><b>${esc(x.who)}</b>${x.a ? esc(x.label) : `<span class="hint">${esc(L('pas d\'avis publié', 'no advisory'))}</span>`}</div></div>`).join('')}</div>
          <h3>${icon('shield', 13)} ${esc(L('Profil de menace', 'Threat profile'))}</h3>
          <div class="bars">${rows.slice(0, 6).map(x => `<div class="bar" style="grid-template-columns:1fr 70px 16px"><span>${esc(x[lang])}</span><span class="meter" style="margin:0">${[1, 2, 3, 4, 5].map(i => `<span style="${i <= x.lvl ? `background:${RC[x.lvl]}` : ''}"></span>`).join('')}</span><span class="bv">${x.lvl}</span></div>`).join('')}</div>
        </div>
      </div>
      <div class="note-box"><h3 style="margin-top:0">${icon('pencil', 13)} ${esc(L('Appréciation de l\'analyste', 'Analyst assessment'))}</h3>
        <div class="ne" contenteditable="true" id="analyst-note" data-ph="${esc(L('Cliquez pour ajouter votre appréciation (imprimée dans le PDF, enregistrée sur cet appareil).', 'Click to add your assessment (printed in the PDF, saved on this device).'))}">${esc(note)}</div></div>
      <h3 class="toc-h">${icon('list', 13)} ${esc(L('Sommaire', 'Contents'))}</h3>
      <ol class="toc">${SECTIONS.filter(s => !excluded.has(s.id)).map(s => `<li><span class="n">${secNum(s.id)}</span><span>${esc(L(s.fr, s.en))}</span></li>`).join('')}</ol>`);
  }

  function risksHtml(iso, rows) {
    const trendTxt = t => t > 0 ? `<span class="trend up">↑</span>` : t < 0 ? `<span class="trend down">↓</span>` : '<span class="trend">→</span>';
    return sec('risques', `
      <p class="lead">${esc(L('Chaque menace est notée de 1 (faible) à 5 (critique). La note combine les incidents détectés par l\'outil et des indicateurs structurels : avis officiels, motifs cités par le Département d\'État, stabilité politique et taux d\'homicides (Banque mondiale), groupes armés (CIA Factbook).', 'Each threat is rated from 1 (low) to 5 (critical). The rating combines incidents detected by the tool with structural indicators: official advisories, reasons cited by the US State Department, political stability and homicide rate (World Bank), armed groups (CIA Factbook).'))}</p>
      <table class="matrix"><thead><tr><th>${esc(L('Menace', 'Threat'))}</th><th>${esc(L('Niveau', 'Level'))}</th><th class="c">${esc(L('Tend.', 'Trend'))}</th><th class="c">24 h</th><th class="c">72 h</th><th class="c">${L('7 j', '7 d')}</th><th class="c">${L('90 j', '90 d')}</th><th>${esc(L('Fondement', 'Basis'))}</th></tr></thead>
      <tbody>${rows.map(x => `<tr><td>${esc(x[lang])}</td><td class="nowrap">${lvlBadge(x.lvl)} ${esc(riskName(x.lvl))}</td><td class="c">${trendTxt(x.trend)}</td>
        <td class="c">${x.c.h24}</td><td class="c">${x.c.h72}</td><td class="c">${x.c.d7}</td><td class="c">${x.c.d90}</td><td class="small">${esc(x.basis.join(' · '))}</td></tr>`).join('')}</tbody></table>
      <h3>${icon('scale', 13)} ${esc(L('Indicateurs structurels (Banque mondiale, 0 = pire, 100 = meilleur)', 'Structural indicators (World Bank, 0 = worst, 100 = best)'))}</h3>
      ${govBars(P[iso] || {})}`);
  }
  function govBars(pr) {
    const items = [[L('Stabilité politique / absence de violence', 'Political stability / no violence'), val(pr, 'wgi_stability')], [L('État de droit', 'Rule of law'), val(pr, 'wgi_rule_of_law')],
      [L('Contrôle de la corruption', 'Control of corruption'), val(pr, 'wgi_corruption')], [L('Efficacité des pouvoirs publics', 'Government effectiveness'), val(pr, 'wgi_government')],
      [L('Qualité de la réglementation', 'Regulatory quality'), val(pr, 'wgi_regulation')], [L('Voix et responsabilité', 'Voice and accountability'), val(pr, 'wgi_voice')]];
    if (items.every(([, v]) => v == null)) return `<p class="empty">${esc(L('Indicateurs non disponibles.', 'Indicators not available.'))}</p>`;
    return `<div class="bars">${items.map(([label, v]) => `<div class="bar"><span>${esc(label)}</span><span class="track"><span class="fill" style="width:${v == null ? 0 : Math.max(2, v)}%;background:${v == null ? '#ccc' : v < 25 ? RC[5] : v < 45 ? RC[4] : v < 65 ? RC[3] : RC[1]}"></span></span><span class="bv">${v == null ? '—' : num(v, 0)}</span></div>`).join('')}</div>`;
  }

  function securityHtml(iso, rows) {
    const fc = (detail() || {}).fcdo;
    const buckets = fcdoBuckets(fc);
    const fb = FB[iso] || {};
    const us = usReasons(iso);
    const evs = EVENTS.filter(e => e.country === iso);
    const cards = THEMES.map(th => {
      const row = th.row ? rows.find(x => x.key === th.row) : null;
      const official = fcdoHtml(buckets[th.k]);
      const chips = [];
      if (row) chips.push(`<span class="chip">${esc(L('Incidents 90 j', 'Incidents 90 d'))} : ${row.c.d90}</span>`);
      (th.us || []).forEach(k => { if (us.includes(k)) chips.push(`<span class="chip bad">${icon('landmark', 11)} ${esc(L('Cité par les États-Unis', 'Cited by the US'))}</span>`); });
      if (th.k === 'terrorism' && fb.terrorist_groups) chips.push(`<span class="chip warn">${esc(L('Groupes actifs recensés', 'Active groups listed'))}</span>`);
      if (th.k === 'kidnap') { const n = evs.filter(e => /kidnap|abduct|hostage|enlev|enlèv|otage|rapt|secuestr/i.test(e.title)).length; if (n) chips.push(`<span class="chip warn">${n} ${esc(L('enlèvement(s) signalé(s) · 30 j', 'kidnapping(s) reported · 30 d'))}</span>`); }
      if (th.k === 'crime') { const h = val(P[iso] || {}, 'homicide_rate'); if (h != null) chips.push(`<span class="chip">${esc(L('Homicides', 'Homicides'))} : ${num(h)} / 100 000</span>`); }
      const lvl = th.k === 'kidnap' ? (us.includes('kidnapping') ? Math.max(4, row ? row.lvl : 0) : null) : th.k === 'detention' ? (us.includes('detention') ? 4 : null) : row ? row.lvl : null;
      let extra = '';
      if (th.k === 'terrorism' && fb.terrorist_groups) extra = `<p class="small"><b>${esc(L('Groupes présents (CIA Factbook)', 'Groups present (CIA Factbook)'))} :</b> ${tx(fb.terrorist_groups.slice(0, 700), 'en')}</p>`;
      if (!official && !extra && !chips.length && lvl == null) return '';
      if (th.k === 'other' && !official) return '';
      return `<div class="theme"><div class="theme-h"><span class="ti">${icon(th.icon, 16)}</span><div><div class="tt">${esc(L(th.fr, th.en))}</div>${row ? `<div class="ts">${esc(riskName(row.lvl))}</div>` : ''}</div>${lvl != null ? lvlBadge(lvl) : ''}</div>
        ${chips.length ? `<div class="facts-line">${chips.join('')}</div>` : ''}${extra}${official || (th.k === 'cyber' ? `<p class="small">${esc(L('Menace mondiale de fond : hameçonnage, rançongiciels, interception des communications dans les pays à risque. Appareils dédiés et VPN recommandés pour les pays sensibles.', 'Global baseline threat: phishing, ransomware, interception of communications in high-risk countries. Dedicated devices and VPN recommended for sensitive countries.'))}</p>` : '')}</div>`;
    }).filter(Boolean);
    const flagTxt = fc ? '' : L('Texte FCDO en cours de collecte', 'FCDO text being collected');
    return sec('surete', `<p class="lead">${esc(L('Pour chaque menace : le niveau Angor, les indices issus des données, puis les conseils officiels britanniques (FCDO), cités intégralement. Utilisez « Traduire » pour les afficher en français.', 'For each threat: the Angor level, data-driven indicators, then the official UK (FCDO) advice quoted in full.'))}</p>
      <div class="themes">${cards.join('')}</div>`, flagTxt);
  }

  function recoHtml(iso, rows) {
    return sec('recommandations', `${recommendations(iso, rows).map(g => `<h3>${icon('check', 13)} ${esc(g.title)}</h3><ul>${g.items.map(i => `<li>${esc(i)}</li>`).join('')}</ul>`).join('')}
      <p class="hint">${esc(L('Recommandations génériques à adapter par l\'analyste sûreté au contexte précis (zones, activité, profil des voyageurs).', 'Generic recommendations to be tailored by the security analyst (areas, activity, traveller profile).'))}</p>`);
  }

  function citiesHtml(iso) {
    const dt = detail();
    if (!dt) return sec('villes', `<p class="empty">${esc(L('Chargement des données villes…', 'Loading city data…'))}</p>`);
    const cities = dt.cities || [];
    if (!cities.length) return sec('villes', `<p class="empty">${esc(L('Pas de grande ville référencée pour ce pays.', 'No major city listed for this country.'))}</p>`);
    const fc = dt.fcdo;
    const cmp = `<table class="city-cmp"><thead><tr><th>${esc(L('Ville', 'City'))}</th><th class="r">${esc(L('Population', 'Population'))}</th><th>${esc(L('Niveau analyste', 'Analyst level'))}</th><th>${esc(L('Activité 90 j', 'Activity 90 d'))}</th><th class="c">${esc(L('Incidents', 'Incidents'))}</th><th>${esc(L('Aéroport', 'Airport'))}</th></tr></thead><tbody>
      ${cities.map(c => `<tr><td><b>${esc(cityName(c))}</b>${c.capital ? ` <span class="chip gold">${esc(L('capitale', 'capital'))}</span>` : ''}</td><td class="r">${pop(c.pop)}</td><td>${c.note ? lvlBadge(c.note.level) : '<span class="hint">—</span>'}</td><td>${actBars(c.stats.level)} <span class="small">${esc(ACT_LBL()[c.stats.level])}</span></td><td class="c">${c.stats.n90}</td><td class="small">${c.airport ? `${esc(c.airport.iata)} · ${c.airport.km} km` : '—'}</td></tr>`).join('')}</tbody></table>`;
    const cards = cities.map(c => {
      const n = c.note;
      const hosp = hospitalsIn(c);
      const cats = Object.entries(c.stats.by_cat || {}).sort((a, b) => b[1] - a[1]).slice(0, 4);
      return `<article class="city" id="ville-${esc(norm(c.name).replace(/ /g, '-'))}">
        <div class="city-h"><div><div class="city-name">${esc(cityName(c))}</div>
          <div class="city-sub">${esc([c.capital ? L('Capitale', 'Capital') : '', c.adm1, pop(c.pop), c.tz ? tzLabel(c.tz) : ''].filter(Boolean).join(' · '))}</div></div>
          <div class="city-badges">${n ? `<span class="chip" style="gap:6px">${esc(L('Niveau analyste', 'Analyst level'))} ${lvlBadge(n.level)}</span>` : ''}<span class="chip">${actBars(c.stats.level)} ${esc(L('Activité', 'Activity'))} : ${esc(ACT_LBL()[c.stats.level])}</span></div></div>
        ${n ? `<p style="margin-top:8px">${tx(n.summary, 'fr')}</p>` : ''}
        <div class="city-grid"><div>
          ${n && n.zones && n.zones.length ? `<h4>${esc(L('Zones sensibles', 'Sensitive areas'))}</h4><ul>${n.zones.map(z => `<li>${tx(z, 'fr')}</li>`).join('')}</ul>` : ''}
          ${n && n.advice && n.advice.length ? `<h4>${esc(L('Conseils', 'Advice'))}</h4><ul>${n.advice.map(z => `<li>${tx(z, 'fr')}</li>`).join('')}</ul>` : ''}
          ${n && n.customs && n.customs.length ? `<h4>${esc(L('Us et coutumes', 'Customs'))}</h4><ul>${n.customs.map(z => `<li>${tx(z, 'fr')}</li>`).join('')}</ul>` : ''}
          ${c.fcdo && c.fcdo.length ? `<h4>${esc(L('Ce qu\'en dit le FCDO', 'What the FCDO says'))}</h4><div class="official" style="margin-top:2px">${c.fcdo.map(s => `<p>${tx(s, 'en')}</p>`).join('')}<div class="src">FCDO · Open Government Licence v3.0</div></div>` : ''}
          ${!n && !(c.fcdo || []).length ? `<p class="hint">${esc(L('Pas de note d\'analyste pour cette ville. Les indicateurs ci-contre sont calculés automatiquement.', 'No analyst note for this city. Indicators alongside are computed automatically.'))}</p>` : ''}
        </div><div>
          <h4>${esc(L(`Incidents dans un rayon de ${c.radius_km} km · 90 j`, `Incidents within ${c.radius_km} km · 90 d`))}</h4>
          ${c.top && c.top.length ? `<ul class="mini-ev">${c.top.map(e => `<li><span class="dot" style="background:${SEV[e.s] || SEV[1]}"></span><span>${tx(evTitle(e), lang === 'fr' && e.tf ? 'fr' : lang === 'en' && e.te ? 'en' : 'xx')}</span><span class="w">${fmtDate(e.d)}</span></li>`).join('')}</ul>` : `<p class="hint">${esc(L('Aucun incident enregistré.', 'No incident recorded.'))}</p>`}
          ${cats.length ? `<div class="facts-line" style="margin-top:6px;display:flex;flex-wrap:wrap;gap:5px">${cats.map(([k, v]) => `<span class="chip">${icon(catIcon(k), 11)} ${esc(catName(k))} · ${v}</span>`).join('')}</div>` : ''}
          ${c.airport ? `<h4>${esc(L('Aéroport', 'Airport'))}</h4><p class="small">${esc(c.airport.name)} (${esc(c.airport.iata)}${c.airport.icao ? ' / ' + esc(c.airport.icao) : ''}) — ${c.airport.km} km ${esc(L('du centre', 'from the centre'))}</p>` : ''}
          ${hosp.length ? `<h4>${esc(L('Hôpitaux', 'Hospitals'))}</h4><ul class="small">${hosp.map(h => `<li>${esc(h.name)}${h.beds ? ` · ${num(h.beds, 0)} ${esc(L('lits', 'beds'))}` : ''}</li>`).join('')}</ul>` : ''}
        </div></div></article>`;
    }).join('');
    const withNotes = cities.some(c => c.note);
    return sec('villes', `<p class="lead">${esc(L('Les grandes villes ne présentent pas toutes le même niveau d\'exposition que le reste du pays. Pour chacune : la note de l\'analyste (quand elle existe), l\'activité des incidents détectés dans un rayon de 20 à 40 km sur 90 jours, ce qu\'en dit le FCDO, l\'aéroport et les hôpitaux.', 'Major cities do not all share the country\'s exposure. For each: the analyst note (when available), activity of incidents detected within 20–40 km over 90 days, what the FCDO says, the airport and hospitals.'))}</p>
      <div class="map-box" id="city-map"></div>
      <div class="map-legend"><span><i class="dot" style="background:${SEV[4]}"></i>${esc(L('critique', 'critical'))}</span><span><i class="dot" style="background:${SEV[3]}"></i>${esc(L('élevée', 'high'))}</span><span><i class="dot" style="background:${SEV[2]}"></i>${esc(L('modérée', 'moderate'))}</span><span><i class="dot" style="background:${SEV[1]}"></i>${esc(L('faible', 'low'))}</span><span>${esc(L('Chiffre = incidents à proximité sur 90 jours', 'Number = nearby incidents over 90 days'))}</span></div>
      ${cmp}${cards}
      ${withNotes ? `<p class="hint" style="margin-top:10px">${esc(L('Notes d\'analyste : premier jet rédigé avec assistance IA à partir de sources ouvertes (septembre 2026), à valider. Niveau analyste sur l\'échelle Angor de 1 à 5.', 'Analyst notes: first draft written with AI assistance from open sources (September 2026), to be validated. Analyst level on the Angor 1–5 scale.'))}${lang === 'en' ? ' Notes are written in French: use “Translate”.' : ''}</p>` : ''}`,
      fc ? '' : '');
  }

  function incidentsHtml(iso) {
    const recent = EVENTS.filter(e => e.country === iso).sort((a, b) => b.severity - a.severity || (b.date > a.date ? 1 : -1)).slice(0, 18);
    const title = e => lang === 'fr' ? (e.title_fr || e.title) : (e.title_en || e.title);
    return sec('incidents', recent.length ? `<table><thead><tr><th></th><th>${esc(L('Date', 'Date'))}</th><th>${esc(L('Incident', 'Incident'))}</th><th>${esc(L('Catégorie · source', 'Category · source'))}</th></tr></thead><tbody>
      ${recent.map(e => `<tr><td><span class="dot" style="background:${SEV[e.severity]};margin-top:5px"></span></td><td class="nowrap small">${fmtDate(e.date)}</td><td><b>${tx(title(e), (lang === 'fr' && e.title_fr) || (lang === 'en' && e.title_en) ? lang : (e.lang || 'xx'))}</b>${e.place ? `<br><span class="small">${esc(e.place)}</span>` : ''}</td><td class="small">${esc(catName(e.category))}<br>${esc(e.source)}${e.admiralty ? ` · <span class="mono">${esc(e.admiralty)}</span>` : ''}${(e.tags || []).includes('auto-detected') ? ` · ${esc(L('auto', 'auto'))}` : ''}</td></tr>`).join('')}</tbody></table>
      <p class="hint">${esc(L('Classés par gravité puis par date. Détections automatiques non vérifiées signalées « auto » ; cotation de l\'Amirauté (fiabilité de la source A–F, crédibilité 1–6).', 'Sorted by severity then date. Unverified automated detections flagged “auto”; Admiralty rating (source reliability A–F, credibility 1–6).'))}</p>`
      : `<p class="empty">${esc(L('Aucun incident enregistré sur les 30 derniers jours.', 'No incident recorded in the last 30 days.'))}</p>`);
  }

  function advisoriesHtml(iso) {
    const list = advList(iso);
    const r = RISK[iso];
    const a = r && r.advisories ? r.advisories['MEAE (France)'] : null;
    const uk = r && r.advisories ? r.advisories['FCDO (UK)'] : null;
    const us = r && r.advisories ? r.advisories['US State Dept'] : null;
    const maps = [a && a.map ? [a.map, 'MEAE'] : null, uk && uk.map ? [uk.map, 'FCDO'] : null].filter(Boolean);
    const fc = (detail() || {}).fcdo;
    return sec('avis', `
      <table><thead><tr><th>${esc(L('Pays émetteur', 'Issuer'))}</th><th>${esc(L('Niveau', 'Level'))}</th><th>${esc(L('Avis', 'Advice'))}</th><th>${esc(L('Mise à jour', 'Updated'))}</th><th></th></tr></thead><tbody>
      ${list.map(x => `<tr><td><b>${esc(x.who)}</b><br><span class="small">${esc(x.src)}</span></td><td>${x.a ? `<span class="lvl" style="background:${MIN_COLORS[x.lvl]}">${x.lvl}</span>` : '—'}</td><td>${x.a ? esc(x.label) : `<span class="hint">${esc(L('Pas d\'avis publié', 'No advisory'))}</span>`}${x.mode === 'us' && us && (us.reasons || []).length ? `<br><span class="small">${esc(L('Motifs', 'Reasons'))} : ${(us.reasons || []).map(k => esc(US_REASONS()[k] || k)).join(', ')}</span>` : ''}</td><td class="small nowrap">${x.a && x.a.updated ? fmtDate(x.a.updated) : ''}</td><td>${x.a && x.a.url ? `<a href="${esc(x.a.url)}">${icon('external-link', 13)}</a>` : ''}</td></tr>`).join('')}</tbody></table>
      ${a && (a.excerpt || []).length ? `<h3>${icon('landmark', 13)} ${esc(L('France — Conseils aux voyageurs (extraits « Sécurité »)', 'France — Travel advice (security excerpts)'))}</h3><blockquote class="quote">${a.excerpt.map(x => `<p>« ${tx(x, 'fr')} »</p>`).join('')}<footer>${esc(L('Extraits du site diplomatie.gouv.fr — la page officielle fait foi.', 'Excerpts from diplomatie.gouv.fr — the official page prevails.'))} <a href="${esc(a.url)}">diplomatie.gouv.fr</a></footer></blockquote>` : ''}
      ${fc && (fc.parts || {}).warnings && fc.parts.warnings.length ? `<h3>${icon('landmark', 13)} ${esc(L('Royaume-Uni — Avertissements du FCDO', 'United Kingdom — FCDO warnings'))}</h3>${fcdoHtml(fc.parts.warnings)}` : ''}
      ${maps.length ? `<h3>${icon('map', 13)} ${esc(L('Cartes officielles des zones', 'Official zone maps'))}</h3><div class="maps">${maps.map(([u, s]) => `<figure><img src="${esc(u)}" alt="${esc(s)}" referrerpolicy="no-referrer" onerror="this.parentNode.remove()"><figcaption>${esc(L('Carte officielle', 'Official map'))} ${esc(s)}</figcaption></figure>`).join('')}</div>` : ''}`);
  }

  function travelHtml(iso) {
    const dt = detail() || {};
    const fc = dt.fcdo;
    const buckets = fcdoBuckets(fc);
    const aps = dt.airports || [];
    const entry = fc && fc.parts ? (fc.parts.entry || []).filter(s => !/vaccine requirement/i.test(s.h)) : [];
    return sec('voyage', `
      <div class="cols"><div>
        <h3>${icon('plane', 13)} ${esc(L('Aéroports avec vols réguliers', 'Airports with scheduled flights'))}</h3>
        ${aps.length ? `<table><thead><tr><th>${esc(L('Aéroport', 'Airport'))}</th><th>IATA / OACI</th><th>${esc(L('Ville', 'City'))}</th></tr></thead><tbody>${aps.map(a => `<tr><td>${esc(a.name)}${a.large ? ` <span class="chip gold">${esc(L('international', 'international'))}</span>` : ''}</td><td class="mono small">${esc(a.iata)}${a.icao ? ' / ' + esc(a.icao) : ''}</td><td class="small">${esc(a.city)}</td></tr>`).join('')}</tbody></table>` : `<p class="empty">${esc(L('Données en cours de chargement.', 'Data loading.'))}</p>`}
      </div><div>
        <h3>${icon('route', 13)} ${esc(L('Sur la route', 'On the road'))}</h3>
        <dl class="kv"><dt>${esc(L('Circulation', 'Traffic'))}</dt><dd><b>${esc(dt.driving === 'left' ? L('à gauche', 'on the left') : L('à droite', 'on the right'))}</b></dd>
          <dt>${esc(L('Permis', 'Licence'))}</dt><dd>${esc(L('Permis international (IDP) recommandé en plus du permis national ; vérifier les règles locales ci-dessous.', 'International Driving Permit recommended in addition to your licence; check local rules below.'))}</dd>
          <dt>${esc(L('Location', 'Car hire'))}</dt><dd>${esc(((RISK[iso] || {}).level || 1) >= 4 ? L('Conduite personnelle déconseillée : véhicule avec chauffeur de confiance.', 'Self-drive not advised: vehicle with a trusted driver.') : L('Possible dans les grandes villes ; préférer un chauffeur pour les trajets de nuit ou hors agglomération.', 'Possible in major cities; prefer a driver at night or outside cities.'))}</dd></dl>
      </div></div>
      ${entry.length ? `<h3>${icon('file-text', 13)} ${esc(L('Formalités d\'entrée (FCDO — pour les ressortissants britanniques, à vérifier pour votre nationalité)', 'Entry requirements (FCDO — for British nationals, check for your nationality)'))}</h3>${fcdoHtml(entry)}` : ''}
      ${(buckets.transport || []).length ? `<h3>${icon('route', 13)} ${esc(L('Transports : route, taxis, avion, bateau', 'Transport: road, taxis, air, sea'))}</h3>${fcdoHtml(buckets.transport)}` : ''}
      ${(buckets.outdoor || []).length ? `<h3>${icon('mountain', 13)} ${esc(L('Activités de plein air', 'Outdoor activities'))}</h3>${fcdoHtml(buckets.outdoor)}` : ''}
      ${!fc ? `<p class="hint">${esc(L('Les conseils détaillés du FCDO (transports, formalités) s\'ajouteront automatiquement après les prochaines collectes.', 'Detailed FCDO advice (transport, entry) will be added automatically after the next collections.'))}</p>` : ''}`);
  }

  function healthHtml(iso) {
    const dt = detail() || {};
    const hc = window.VS_HEALTH || null;
    const em = dt.emergency || {};
    const x = PRACT[iso] || {};
    const SERV = { police: L('Police', 'Police'), ambulance: L('Ambulance', 'Ambulance'), fire: L('Pompiers', 'Fire'), medical: L('Urgences médicales', 'Medical'), emergency: L('Urgences', 'Emergency'), 'tourist police': L('Police touristique', 'Tourist police'), coastguard: L('Garde-côtes', 'Coastguard'), 'coast guard': L('Garde-côtes', 'Coastguard') };
    let tiles = (em.fcdo || []).map(e => [e.number, SERV[e.service] || e.service]);
    if (!tiles.length && (em.general || []).length) tiles = em.general.slice(0, 4).map(n => [n, L('Urgences', 'Emergency')]);
    if (!tiles.length && (x.emergency || []).length) tiles = x.emergency.slice(0, 4).map(n => [n, L('Urgences', 'Emergency')]);
    const h = dt.health || { risks: [], vaccines: [] };
    const dis = (h.risks || []).map(k => ({ k, d: hc && hc.diseases ? hc.diseases[k] : null })).filter(o => o.d);
    const vac = (h.vaccines || []).map(k => ({ k, v: hc && hc.vaccines ? hc.vaccines[k] : null })).filter(o => o.v);
    const hosp = (x.hospitals || []).slice().sort((a, b) => (a.city || '~').localeCompare(b.city || '~'));
    const alerts = EVENTS.filter(e => e.country === iso && e.category === 'health').slice(0, 5);
    const fc = dt.fcdo;
    const fhealth = fc && fc.parts ? (fc.parts.health || []).filter(s => !/medication|mental health/i.test(s.h)) : [];
    return sec('sante', `
      <h3>${icon('siren', 13)} ${esc(L('Numéros d\'urgence', 'Emergency numbers'))}</h3>
      ${tiles.length ? `<div class="sos">${tiles.map(([n, s]) => `<div><div class="n">${esc(n)}</div><div class="s">${esc(s)}</div></div>`).join('')}</div>` : `<p class="empty">${esc(L('Numéros en cours de collecte.', 'Numbers being collected.'))}</p>`}
      ${em.notes ? `<p class="small">${tx(em.notes, 'en')}</p>` : ''}
      <p class="hint">${esc(L('Sources : FCDO (rubrique « Getting help »), worldhotlines.org, Wikidata. Vérifier sur place (numéros régionaux possibles) et enregistrer aussi le numéro de l\'assisteur et de l\'ambassade.', 'Sources: FCDO (Getting help), worldhotlines.org, Wikidata. Check locally (regional numbers may apply) and also save your assistance provider and embassy numbers.'))}</p>
      ${vac.length ? `<h3>${icon('shield-check', 13)} ${esc(L('Vaccinations à envisager', 'Vaccinations to consider'))}</h3><ul class="vacc">${vac.map(o => `<li class="${o.k === 'yellow_fever_cert' ? 'req' : ''}">${icon(o.k === 'yellow_fever_cert' ? 'triangle-alert' : 'check', 14)}<span>${esc(o.v[lang] || o.v.fr)}</span></li>`).join('')}</ul>` : ''}
      ${h.malaria ? `<p class="small"><b>${esc(L('Paludisme', 'Malaria'))} :</b> ${esc(h.malaria === 'high' ? L('risque présent sur la majeure partie du territoire — chimioprophylaxie à discuter avec un médecin.', 'risk in most of the country — discuss preventive medication with a doctor.') : L('risque limité à certaines zones (souvent rurales ou frontalières) — avis médical selon l\'itinéraire.', 'risk limited to some areas (often rural or border) — medical advice depending on itinerary.'))}</p>` : ''}
      ${dis.length ? `<h3>${icon('biohazard', 13)} ${esc(L('Risques sanitaires courants', 'Common health risks'))}</h3><div class="dis">${dis.map(o => { const d = o.d[lang] || o.d.fr; return `<div><b>${icon(o.d.icon || 'circle-alert', 14)} ${esc(d[0])}</b><p>${esc(d[1])}</p></div>`; }).join('')}</div>` : ''}
      ${alerts.length ? `<h3>${icon('activity', 13)} ${esc(L('Alertes sanitaires récentes', 'Recent health alerts'))}</h3><ul class="mini-ev">${alerts.map(e => `<li><span class="dot" style="background:${SEV[e.severity]}"></span><span>${tx(lang === 'fr' ? (e.title_fr || e.title) : (e.title_en || e.title), (lang === 'fr' && e.title_fr) || (lang === 'en' && e.title_en) ? lang : 'en')}</span><span class="w">${fmtDate(e.date)}</span></li>`).join('')}</ul>` : ''}
      ${fhealth.length ? `<h3>${icon('heart-pulse', 13)} ${esc(L('Soins et offre médicale (FCDO)', 'Medical care (FCDO)'))}</h3>${fcdoHtml(fhealth)}` : ''}
      <h3>${icon('building', 13)} ${esc(L('Principaux établissements hospitaliers', 'Main hospitals'))}</h3>
      ${hosp.length ? `<table><thead><tr><th>${esc(L('Établissement', 'Hospital'))}</th><th>${esc(L('Ville', 'City'))}</th><th class="r">${esc(L('Lits', 'Beds'))}</th><th>${esc(L('Site', 'Website'))}</th></tr></thead><tbody>
        ${hosp.map(hh => `<tr><td><b>${esc(hh.name)}</b></td><td>${esc(hh.city)}</td><td class="r">${hh.beds ? num(hh.beds, 0) : '—'}</td><td class="small">${hh.web ? `<a href="${esc(hh.web)}">${esc(hh.web.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, ''))}</a>` : ''}</td></tr>`).join('')}</tbody></table>`
        : `<p class="empty">${esc(L('Liste en cours de constitution (mise à jour progressive depuis Wikidata).', 'List being compiled (progressive update from Wikidata).'))}</p>`}
      <p class="hint">${esc(L('Informations indicatives d\'après OMS, CDC, HCSP et TravelHealthPro. Consulter un centre de vaccinations internationales 4 à 8 semaines avant le départ. Hôpitaux classés par capacité (Wikidata) : ce n\'est pas une liste agréée, à valider avec l\'assisteur et le consulat.', 'Indicative information based on WHO, CDC, HCSP and TravelHealthPro. See a travel clinic 4 to 8 weeks before departure. Hospitals ranked by capacity (Wikidata): not an approved list, validate with your assistance provider and consulate.'))}</p>`);
  }

  const GUIDE_KEYS = [['tenue', 'Tenue vestimentaire', 'Dress code', 'shirt'], ['religion', 'Religion et pratiques', 'Religion and practices', 'landmark'],
    ['gestes', 'Gestes et attitudes à éviter', 'Gestures and behaviour to avoid', 'hand'], ['salutations', 'Salutations', 'Greetings', 'handshake'],
    ['affaires', 'Culture des affaires', 'Business culture', 'briefcase'], ['interdits', 'Interdits et sujets sensibles', 'Red lines and sensitive topics', 'ban'],
    ['voyageuses', 'Voyageuses', 'Women travellers', 'user']];
  function cultureHtml(iso) {
    const g = GUIDES[iso];
    const buckets = fcdoBuckets((detail() || {}).fcdo);
    const body = `${g ? `<div class="guide">${GUIDE_KEYS.filter(([k]) => (g[k] || []).length).map(([k, fr, en, ic]) =>
        `<div class="gcard"><h4>${icon(ic, 14)} ${esc(L(fr, en))}</h4><ul>${g[k].map(x => `<li>${tx(x, 'fr')}</li>`).join('')}</ul></div>`).join('')}</div>
        <p class="hint">${esc(GUIDES_NOTE)}</p>` : ''}
      ${(buckets.culture || []).length ? `<h3>${icon('gavel', 13)} ${esc(L('Lois et différences culturelles (FCDO)', 'Laws and cultural differences (FCDO)'))}</h3>${fcdoHtml(buckets.culture)}` : ''}`;
    return sec('culture', body.trim() ? body : `<p class="empty">${esc(L('Pas de fiche culturelle pour ce pays.', 'No cultural guide for this country.'))}</p>`);
  }

  function calendarHtml(iso) {
    if (!window.VS_CALENDAR) return sec('calendrier', `<p class="empty">${esc(L('Calendrier en cours de chargement…', 'Calendar loading…'))}</p>`);
    const items = agenda(iso, 365);
    const TYPE = { holiday: L('Jour férié', 'Public holiday'), election: L('Élection', 'Election'), religious: L('Fête religieuse', 'Religious'), other: L('Échéance', 'Key date') };
    return sec('calendrier', items.length ? `<ul class="cal">${items.map(e => `<li><div class="d"><span class="dot ag-${agType(e)}"></span> ${e.prec === 'year' ? esc(e.d.slice(0, 4)) : esc(fmtDate(e.d))}${e.e && e.e !== e.d ? `<br>→ ${esc(fmtDate(e.e))}` : ''}</div><div><div class="t">${esc(lang === 'fr' ? e.t_fr : (e.t_en || e.t_fr))} <span class="chip" style="margin-left:4px">${esc(TYPE[agType(e)])}</span></div>${(lang === 'fr' ? e.note_fr : (e.note_en || e.note_fr)) ? `<div class="x">${esc(lang === 'fr' ? e.note_fr : (e.note_en || e.note_fr))}</div>` : ''}</div></li>`).join('')}</ul>
      <p class="hint">${esc(L('Jours fériés (Nager.Date / Wikidata), élections (Wikidata) et fêtes religieuses calculées (dates indicatives ± 1-2 jours).', 'Public holidays (Nager.Date / Wikidata), elections (Wikidata) and computed religious festivals (indicative dates ± 1-2 days).'))}</p>`
      : `<p class="empty">${esc(L('Aucune échéance connue sur les 12 prochains mois.', 'No known key date in the next 12 months.'))}</p>`);
  }

  const kv = rows => `<dl class="kv">${rows.filter(([, v]) => v && v !== '—').map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join('')}</dl>`;
  function economyHtml(iso) {
    const pr = P[iso] || {}, fb = FB[iso] || {};
    const g = pr.imf_growth || {}, inf = pr.imf_inflation || {};
    const yrs = Object.keys(g).sort();
    const econ = (ECON[iso] || []).slice(0, 8);
    const angles = businessAngles(iso);
    return sec('economie', `
      <div class="kpis">${[[big(val(pr, 'population')), L('population', 'population')], [money(val(pr, 'gdp_usd')), L('PIB', 'GDP')],
        [yrs.length ? num(g[yrs[yrs.length - 2]] ?? g[yrs[0]]) + ' %' : num(val(pr, 'gdp_growth')) + ' %', L('croissance', 'growth')], [num(val(pr, 'inflation')) + ' %', L('inflation', 'inflation')]]
        .map(([v, k]) => `<div class="kpi"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join('')}</div>
      <h3>${icon('trending-up', 13)} ${esc(L('Angles business', 'Business angles'))}</h3>
      <ul>${angles.map(a => `<li>${esc(a)}</li>`).join('') || `<li>${esc(L('Données insuffisantes.', 'Insufficient data.'))}</li>`}</ul>
      <div class="cols">
        ${kv([[L('PIB par habitant', 'GDP per capita'), val(pr, 'gdp_per_capita') ? num(val(pr, 'gdp_per_capita'), 0) + ' $ (' + yr(pr, 'gdp_per_capita') + ')' : ''],
              [L('Prévisions FMI (croissance)', 'IMF growth forecast'), yrs.map(y => `${y} : ${num(g[y])} %`).join(' · ')],
              [L('Prévisions FMI (inflation)', 'IMF inflation forecast'), Object.keys(inf).sort().map(y => `${y} : ${num(inf[y])} %`).join(' · ')],
              [L('Chômage', 'Unemployment'), val(pr, 'unemployment') != null ? num(val(pr, 'unemployment')) + ' %' : ''],
              [L('IDE entrants', 'FDI inflows'), val(pr, 'fdi_inflows_pct_gdp') != null ? num(val(pr, 'fdi_inflows_pct_gdp')) + L(' % du PIB', '% of GDP') : ''],
              [L('Création d\'entreprise', 'Starting a business'), val(pr, 'days_to_start_business') != null ? `${num(val(pr, 'days_to_start_business'), 0)} ${L('jours', 'days')}` : '']])}
        ${kv([[L('Exportations', 'Exports'), tx(fb.exports_commodities, 'en')], [L('Clients', 'Export partners'), tx(fb.exports_partners, 'en')],
              [L('Fournisseurs', 'Import partners'), tx(fb.imports_partners, 'en')], [L('Sanctions', 'Sanctions'), esc({ extensive: L('Étendues (UE/États-Unis)', 'Extensive (EU/US)'), extensive_us: L('Embargo américain', 'US embargo'), sectoral: L('Sectorielles', 'Sectoral'), targeted: L('Ciblées (personnes/entités)', 'Targeted'), partially_lifted: L('Partiellement levées (2025)', 'Partially lifted (2025)') }[pr.sanctions] || '')]])}
      </div>
      ${pr.wb_projects && pr.wb_projects.top && pr.wb_projects.top.length ? `<h3>${icon('landmark', 13)} ${esc(L('Principaux projets financés par la Banque mondiale', 'Main World Bank-funded projects'))}</h3>
        <table><tbody>${pr.wb_projects.top.map(p => `<tr><td><a href="${esc(p.url)}">${esc(p.name)}</a></td><td class="small">${esc(p.sector)}</td><td class="nowrap r">${money(p.amount_usd)}</td></tr>`).join('')}</tbody></table>` : ''}
      ${econ.length ? `<h3>${icon('newspaper', 13)} ${esc(L('Actualité économique récente', 'Recent business news'))}</h3><ul class="plain">${econ.map(e => `<li style="margin:5px 0"><a href="${esc(e.url)}">${esc(e.title)}</a> <span class="small">— ${esc(e.source)}, ${fmtDate(e.date)}</span></li>`).join('')}</ul>` : ''}`);
  }

  function contextHtml(iso) {
    const pr = P[iso] || {}, fb = FB[iso] || {}, b = pr.basics || {};
    return sec('contexte', `
      ${fb.background ? `<p class="lead">${tx(fb.background, 'en')}</p>` : ''}
      <div class="cols">
        ${kv([[L('Situation', 'Location'), tx(fb.location, 'en')], [L('Superficie', 'Area'), b.area_km2 ? num(b.area_km2, 0) + ' km²' : esc(fb.area)],
              [L('Capitale', 'Capital'), esc(b.capital || fb.capital)], [L('Régime', 'Government'), tx(fb.government_type, 'en')],
              [L('Système juridique', 'Legal system'), tx(fb.legal_system, 'en')], [L('Langues', 'Languages'), esc((b.languages || []).join(', ')) || tx(fb.languages, 'en')],
              [L('Monnaie', 'Currency'), esc((b.currencies || []).join(', '))]])}
        ${kv([[L('Groupes ethniques', 'Ethnic groups'), tx(fb.ethnic_groups, 'en')], [L('Religions', 'Religions'), tx(fb.religions, 'en')],
              [L('Grandes villes', 'Major cities'), tx(fb.urban_areas, 'en')], [L('Climat', 'Climate'), tx(fb.climate, 'en')],
              [L('Aléas naturels', 'Natural hazards'), tx(fb.natural_hazards, 'en')], [L('Forces armées', 'Armed forces'), tx(fb.military, 'en')],
              [L('Réfugiés et déplacés', 'Refugees and IDPs'), tx(fb.refugees, 'en')]])}
      </div>
      <h3>${icon('scale', 13)} ${esc(L('Gouvernance', 'Governance'))}</h3>${govBars(pr)}`);
  }

  const SATPHONE = { IN: ['Thuraya et Iridium interdits sans autorisation (confiscation, poursuites).', 'Thuraya and Iridium banned without a licence (seizure, prosecution).'],
    CN: ['Usage soumis à autorisation.', 'Use subject to authorisation.'], RU: ['Déclaration / enregistrement obligatoire.', 'Registration required.'],
    KP: ['Interdits.', 'Banned.'], CU: ['Importation soumise à autorisation.', 'Import subject to authorisation.'], BD: ['Restrictions signalées.', 'Restrictions reported.'], MM: ['Restrictions signalées.', 'Restrictions reported.'] };
  const REGION_OF = p => {
    if (!p) return '';
    if (p.region === 'Western Asia') return 'Moyen-Orient';
    return { Africa: 'Afrique', Europe: 'Europe', Asia: 'Asie', 'North America': 'Amériques', 'South America': 'Amériques', Oceania: 'Océanie' }[p.continent] || '';
  };
  function providersHtml(iso) {
    const x = PRACT[iso] || {}, pr = P[iso] || {};
    const cp = COUNTRIES.find(c => c.iso2 === iso);
    const region = REGION_OF(cp);
    const lvl = (RISK[iso] || {}).level || 0;
    const svc = k => ((PROV.services || {})[k] || {})[lang] || k;
    const local = (PROV.local || {})[iso] || [];
    const provs = local.map(p => ({ ...p, local: true })).concat((PROV.providers || []).filter(p => !region || p.regions.includes(region)))
      .sort((a, b) => (b.local ? 1 : 0) - (a.local ? 1 : 0) || ['cp', 'ts', 'ev'].filter(k => b.services.includes(k)).length - ['cp', 'ts', 'ev'].filter(k => a.services.includes(k)).length).slice(0, 10);
    const pct = (k, u) => val(pr, k) != null ? `${num(val(pr, k), 0)}${u} (${yr(pr, k)})` : '';
    const sat = SATPHONE[iso];
    return sec('prestataires', `
      <div class="cols">
        ${kv([[L('Indicatif téléphonique', 'Calling code'), esc((x.calling_code || []).map(c => c.startsWith('+') ? c : '+' + c).join(', '))],
              [L('Prises électriques', 'Plug types'), esc((x.plugs || []).join(', '))], [L('Tension', 'Voltage'), (x.voltage || []).length ? esc(x.voltage.join(' / ')) + ' V' : ''],
              [L('Accès à l\'électricité', 'Access to electricity'), pct('electricity_access', ' %')], [L('Internautes', 'Internet users'), pct('internet_users', ' %')]])}
        ${kv([[L('Opérateurs mobiles', 'Mobile operators'), esc((x.operators || []).join(', '))],
              [L('Abonnements mobiles', 'Mobile subscriptions'), val(pr, 'mobile_subs') != null ? `${num(val(pr, 'mobile_subs'), 0)} ${L('pour 100 hab.', 'per 100 people')}` : ''],
              [L('Téléphone satellite', 'Satellite phone'), esc(sat ? L('⚠ Restrictions : ', '⚠ Restrictions: ') + L(sat[0], sat[1]) : (lvl >= 4 ? L('Recommandé (Iridium, Thuraya, Inmarsat) : coupures d\'Internet possibles. Vérifier la réglementation.', 'Recommended (Iridium, Thuraya, Inmarsat): internet shutdowns possible. Check regulations.') : L('Non indispensable hors zones isolées ; vérifier la réglementation.', 'Not essential outside remote areas; check regulations.')))]])}
      </div>
      <h3>${icon('shield-check', 13)} ${esc(L('Prestataires de sécurité et d\'assistance', 'Security and assistance providers'))}${region ? ` — ${esc(region)}` : ''}</h3>
      <table><thead><tr><th>${esc(L('Prestataire', 'Provider'))}</th><th>${esc(L('Services', 'Services'))}</th><th>${esc(L('Liens', 'Links'))}</th></tr></thead><tbody>
        ${provs.map(p => `<tr><td><b>${esc(p.name)}</b>${p.local ? ` <span class="tag">${esc(L('local vérifié', 'verified local'))}</span>` : ''}<br><span class="small">${esc(p.hq || '')}${p.note ? ' · ' + esc(p.note) : ''}</span></td>
          <td class="small">${(p.services || []).map(svc).map(esc).join(' · ')}</td><td class="small nowrap">${p.web ? `<a href="${esc(p.web)}">${esc(L('Site web', 'Website'))}</a>` : ''}${p.linkedin ? `<br><a href="${esc(p.linkedin)}">LinkedIn</a>` : ''}</td></tr>`).join('')}</tbody></table>
      <p class="hint">${esc(PROV.note || '')}</p>`);
  }

  function sourcesHtml() {
    const src = [L('Incidents : USGS, GDACS, NASA EONET, OMS, ECDC, NOAA, GDELT, presse locale et internationale, canaux Telegram publics (détection automatique, cotation de l\'Amirauté).', 'Incidents: USGS, GDACS, NASA EONET, WHO, ECDC, NOAA, GDELT, local and international press, public Telegram channels (automated detection, Admiralty rating).'),
      L('Avis aux voyageurs : MEAE (France), FCDO (Royaume-Uni), Département d\'État (États-Unis), Auswärtiges Amt (Allemagne).', 'Travel advisories: French MFA, FCDO (UK), US State Department, German Federal Foreign Office.'),
      L('Textes FCDO : « Contains public sector information licensed under the Open Government Licence v3.0 ».', 'FCDO texts: “Contains public sector information licensed under the Open Government Licence v3.0”.'),
      L('Villes : Natural Earth (domaine public). Aéroports : OurAirports (domaine public).', 'Cities: Natural Earth (public domain). Airports: OurAirports (public domain).'),
      L('Numéros d\'urgence : FCDO, worldhotlines.org, Wikidata. Hôpitaux, prises, opérateurs : Wikidata (CC0).', 'Emergency numbers: FCDO, worldhotlines.org, Wikidata. Hospitals, plugs, operators: Wikidata (CC0).'),
      L('Santé : listes OMS, CDC Yellow Book, HCSP, TravelHealthPro (indicatif).', 'Health: WHO, CDC Yellow Book, HCSP, TravelHealthPro lists (indicative).'),
      L('Économie et gouvernance : Banque mondiale (WDI, WGI, projets), FMI (World Economic Outlook). Contexte : CIA World Factbook (archive 2026, domaine public).', 'Economy and governance: World Bank (WDI, WGI, projects), IMF (WEO). Background: CIA World Factbook (2026 archive, public domain).'),
      L('Usages culturels et notes par ville : rédigés avec assistance IA, à valider par l\'analyste.', 'Cultural guides and city notes: written with AI assistance, to be validated by the analyst.'),
      L('Calendrier : Nager.Date, Wikidata, calcul des fêtes religieuses.', 'Calendar: Nager.Date, Wikidata, computed religious festivals.')];
    return sec('sources', `<ul class="sources-list">${src.map(s => `<li>${esc(s)}</li>`).join('')}</ul>
      <p class="hint" style="margin-top:12px">${esc(L('Ce rapport est un outil d\'aide à la décision : il ne garantit pas l\'exhaustivité des informations et doit être complété par l\'analyse d\'un professionnel de la sûreté. Les extraits d\'avis officiels sont cités tels que publiés ; la page officielle fait foi.', 'This report is a decision-support tool: it does not guarantee completeness and must be complemented by a security professional\'s analysis. Official advice is quoted as published; the official page prevails.'))}</p>`);
  }

  /* ------------------------------------------------ carte des villes (Leaflet, fond raster imprimable) */
  let cmap = null;
  function drawMap() {
    const el = $('#city-map');
    if (!el || !window.L || !detail()) return;
    if (cmap) { cmap.remove(); cmap = null; }
    const dt = detail();
    cmap = window.L.map(el, { zoomControl: false, attributionControl: true, scrollWheelZoom: false, dragging: !('ontouchstart' in window) });
    window.L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', { maxZoom: 16, attribution: 'Esri, HERE, Garmin, OpenStreetMap' }).addTo(cmap);
    const f = FEATURES.find(x => x.properties.iso2 === ISO);
    // la vue doit être fixée AVANT d'ajouter des formes vectorielles (sinon Leaflet plante : bug trouvé par le test e2e)
    const outline = f ? window.L.geoJSON(f, { style: { color: '#0E1B2C', weight: 1.4, fillColor: RC[(RISK[ISO] || {}).level || 0], fillOpacity: 0.12 } }) : null;
    const bounds = outline ? outline.getBounds() : null;
    if (bounds && bounds.isValid()) cmap.fitBounds(bounds, { padding: [16, 16], maxZoom: 7 }); else if ((dt.cities || [])[0]) cmap.setView([dt.cities[0].lat, dt.cities[0].lon], 6); else cmap.setView([20, 0], 2);
    if (outline) outline.addTo(cmap);
    const seen = new Set();
    const addEv = (lat, lon, s, title) => {
      if (lat == null) return;
      const k = lat.toFixed(2) + lon.toFixed(2) + title; if (seen.has(k)) return; seen.add(k);
      window.L.circleMarker([lat, lon], { radius: 3 + s, color: '#fff', weight: 1, fillColor: SEV[s] || SEV[1], fillOpacity: 0.9 }).bindTooltip(esc(title)).addTo(cmap);
    };
    EVENTS.filter(e => e.country === ISO).forEach(e => addEv(e.lat, e.lon, e.severity, e.title));
    const placed = [];
    (dt.cities || []).slice().sort((a, b) => b.pop - a.pop).forEach(c => {
      const lvl = c.note ? c.note.level : 0;
      const col = c.note ? RC[lvl] : ACT_COL[c.stats.level];
      const pt = cmap.latLngToContainerPoint([c.lat, c.lon]);
      // étiquette à gauche si une ville voisine occupe déjà la droite
      const left = placed.some(q => Math.abs(q.y - pt.y) < 18 && pt.x - q.x < 110 && pt.x - q.x > -20);
      placed.push(pt);
      window.L.marker([c.lat, c.lon], { icon: window.L.divIcon({ className: '', iconSize: [26, 26], html: `<div class="city-pin" style="background:${col}">${c.stats.n90}</div>` }) })
        .bindTooltip(esc(cityName(c)), { permanent: true, direction: left ? 'left' : 'right', offset: [left ? -12 : 12, 0], className: 'city-lbl' }).addTo(cmap);
    });
  }

  /* ------------------------------------------------ rendu */
  function render() {
    const iso = ISO;
    const r = RISK[iso];
    const name = cname(iso);
    document.title = `${name} – ${L('Rapport pays', 'Country report')} – ${(D.settings || {}).product_name || 'Angor Intelligence'}`;
    const rows = rateRows(iso);
    $('#report').innerHTML = [coverHtml(iso), synthHtml(iso, rows), risksHtml(iso, rows), securityHtml(iso, rows), recoHtml(iso, rows), citiesHtml(iso),
      incidentsHtml(iso), advisoriesHtml(iso), travelHtml(iso), healthHtml(iso), cultureHtml(iso), calendarHtml(iso), economyHtml(iso), contextHtml(iso),
      providersHtml(iso), sourcesHtml()].join('');
    // sommaire latéral
    $('#side').innerHTML = `<div class="s-country">${flag(iso, 40)}${esc(name)} ${r ? lvlBadge(r.level) : ''}</div>
      <nav>${SECTIONS.filter(s => $('#' + s.id)).map(s => `<a href="#${s.id}" data-sec="${s.id}" class="${excluded.has(s.id) ? 'off' : ''}"><span class="n">${secNum(s.id)}</span><span>${esc(L(s.fr, s.en))}</span></a>`).join('')}</nav>
      <div class="s-meta">${esc(L('Données du', 'Data as of'))} ${D.generated ? fmtDate(D.generated) : '—'}${detail() && detail().fcdo && detail().fcdo.updated ? `<br>FCDO : ${fmtDate(detail().fcdo.updated)}` : ''}</div>`;
    // pied de page du PDF (boîtes de marge @page, Chrome / Edge 131+)
    const foot = `${(D.settings || {}).product_name || 'Angor Intelligence'} · ${L('Rapport pays', 'Country report')} · ${name} · ${fmtDate(new Date())}`;
    $('#page-style').textContent = `@page { @bottom-left { content: "${foot.replace(/"/g, '')}"; font: 7.5pt "Instrument Sans", sans-serif; color: #6E7C8C; }
      @bottom-right { content: counter(page) " / " counter(pages); font: 7.5pt "IBM Plex Mono", monospace; color: #6E7C8C; }
      @top-right { content: "${L('CONFIDENTIEL', 'CONFIDENTIAL')}"; font: 600 7pt "IBM Plex Mono", monospace; letter-spacing: 1.5pt; color: #B08D57; } }
      @page :first { @bottom-left { content: none; } @bottom-right { content: none; } @top-right { content: none; } }`;
    const note = $('#analyst-note');
    if (note) note.addEventListener('input', () => store.set('vs-rep-note-' + iso, note.innerText.trim()));
    const trb = $('#tb-tr');
    const pending = $$('.tr[data-src]').length;
    trb.hidden = !pending && trb.getAttribute('aria-pressed') !== 'true';
    trb.querySelector('.lbl').textContent = pending ? L('Traduire', 'Translate') : L('Traduit', 'Translated');
    setTimeout(drawMap, 30);
    spy();
    if (pendingAnchor) { const el = document.getElementById(pendingAnchor); if (el) { pendingAnchor = null; setTimeout(() => el.scrollIntoView(), 60); } }
  }
  let pendingAnchor = null;
  function spy() {
    if (!('IntersectionObserver' in window)) return;
    if (spy.o) spy.o.disconnect();
    spy.o = new IntersectionObserver(ents => ents.forEach(en => {
      if (en.isIntersecting) $$('#side nav a').forEach(a => a.classList.toggle('on', a.dataset.sec === en.target.id));
    }), { rootMargin: '-30% 0px -60% 0px' });
    $$('.page[id]').forEach(p => spy.o.observe(p));
  }

  function renderSections() {
    $('#sec-pop').innerHTML = `<h4>${esc(L('Contenu du PDF', 'PDF content'))}</h4>${SECTIONS.map(s => `<label><input type="checkbox" data-sec="${s.id}"${excluded.has(s.id) ? '' : ' checked'}> ${secNum(s.id)} · ${esc(L(s.fr, s.en))}</label>`).join('')}
      <div class="row"><button class="tb-btn" id="sec-all" type="button">${esc(L('Tout', 'All'))}</button><button class="tb-btn" id="sec-travel" type="button">${esc(L('Voyageur', 'Traveller'))}</button><button class="tb-btn" id="sec-exec" type="button">${esc(L('Direction', 'Executive'))}</button></div>`;
  }
  const PRESETS = { all: [], travel: ['economie', 'contexte', 'prestataires', 'recommandations'], exec: ['surete', 'villes', 'voyage', 'sante', 'culture', 'calendrier', 'prestataires', 'sources', 'incidents'] };

  function load(iso) {
    ISO = iso;
    render();
    const done = () => { if (ISO === iso) render(); };
    if (!detail()) loadScript(`data/country/${iso}.js?v=${encodeURIComponent((D.generated || '').slice(0, 13))}`).then(done, () => { /* fiche détaillée absente : rapport sans villes */ });
    if (!window.VS_CALENDAR) loadScript('data/calendar.js').then(done, () => {});
  }
  function init() {
    const sel = $('#tb-country');
    const list = COUNTRIES.slice().sort((a, b) => a['name_' + lang].localeCompare(b['name_' + lang]));
    sel.innerHTML = list.map(c => `<option value="${c.iso2}">${esc(c['name_' + lang])}${RISK[c.iso2] ? ` (${RISK[c.iso2].level})` : ''}</option>`).join('');
    let [iso, anchor] = decodeURIComponent(location.hash.slice(1)).split('/');
    iso = (iso || 'FR').toUpperCase();
    if (!COUNTRIES.some(c => c.iso2 === iso)) iso = 'FR';
    sel.value = iso;
    $('#tb-back').innerHTML = icon('arrow-left') + `<span class="lbl">${esc(L('Carte', 'Map'))}</span>`;
    $('#tb-print').innerHTML = icon('printer') + `<span class="lbl">${esc(L('Exporter en PDF', 'Export to PDF'))}</span>`;
    $('#tb-sec').innerHTML = icon('list') + `<span class="lbl">${esc(L('Contenu', 'Content'))}</span>`;
    $('#tb-tr').innerHTML = icon('languages') + `<span class="lbl">${esc(L('Traduire', 'Translate'))}</span>`;
    $('#tb-lang').textContent = lang === 'fr' ? 'EN' : 'FR';
    document.documentElement.lang = lang;
    renderSections();
    pendingAnchor = anchor || null;
    load(iso);
  }
  $('#tb-country').addEventListener('change', ev => { location.hash = ev.target.value; });
  window.addEventListener('hashchange', () => { const iso = decodeURIComponent(location.hash.slice(1)).split('/')[0].toUpperCase(); if (iso && iso !== ISO) { $('#tb-country').value = iso; load(iso); } });
  $('#tb-print').addEventListener('click', () => { if (cmap) cmap.invalidateSize(); setTimeout(() => window.print(), 150); });
  $('#tb-tr').addEventListener('click', ev => translateAll(ev.currentTarget));
  $('#tb-lang').addEventListener('click', () => { lang = lang === 'fr' ? 'en' : 'fr'; store.set('vs-lang', lang); init(); });
  $('#tb-sec').addEventListener('click', ev => { ev.stopPropagation(); $('#sec-pop').hidden = !$('#sec-pop').hidden; });
  document.addEventListener('click', ev => { if (!ev.target.closest('#sec-pop') && !ev.target.closest('#tb-sec')) $('#sec-pop').hidden = true; });
  $('#sec-pop').addEventListener('change', ev => {
    const cb = ev.target.closest('input[data-sec]'); if (!cb) return;
    if (cb.checked) excluded.delete(cb.dataset.sec); else excluded.add(cb.dataset.sec);
    store.set('vs-rep-excluded', [...excluded]); render();
  });
  $('#sec-pop').addEventListener('click', ev => {
    const b = ev.target.closest('button'); if (!b) return;
    excluded = new Set(PRESETS[b.id.replace('sec-', '')] || []);
    store.set('vs-rep-excluded', [...excluded]); renderSections(); render();
  });
  window.addEventListener('beforeprint', () => { if (cmap) cmap.invalidateSize(); });
  init();
})();
