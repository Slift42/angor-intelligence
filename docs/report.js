/* Angor Intelligence – rapport pays imprimable (PDF via le navigateur) */
(function () {
  'use strict';
  const D = window.VS_DATA || {};
  const P = (window.VS_PROFILES || {}).countries || {};
  const FB = window.VS_FACTBOOK || {};
  const ECON = (window.VS_ECON || {}).countries || {};
  const COUNTRIES = (window.VS_COUNTRIES || { features: [] }).features.map(f => f.properties);
  const ICONS = window.VS_ICONS || {};
  const TAX = D.taxonomy || { categories: {}, risk_levels: {}, severity: {} };
  const RISK = D.countries || {};
  const STATS = D.country_stats || {};
  const EVENTS = D.events || [];
  let lang = 'fr';
  try { lang = JSON.parse(localStorage.getItem('vs-lang')) || 'fr'; } catch (e) { /* défaut */ }

  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const icon = (n, s = 16) => `<svg viewBox="0 0 24 24" width="${s}" height="${s}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[n] || ''}</svg>`;
  const L = (fr, en) => lang === 'fr' ? fr : en;
  const RISK_COLORS = { 0: '#C9D1D9', 1: '#5FA37C', 2: '#B3C75A', 3: '#F0BE4A', 4: '#EA8639', 5: '#C73E4D' };
  const SEV_COLORS = { 1: '#3F86C6', 2: '#E0A21B', 3: '#E0622B', 4: '#B0182E' };
  const riskName = l => (TAX.risk_levels[l] || {})[lang] || '—';
  const riskDesc = l => (TAX.risk_levels[l] || {})['desc_' + lang] || '';
  const catName = c => (TAX.categories[c] || {})[lang] || c;
  const cname = iso => { const p = COUNTRIES.find(c => c.iso2 === iso); return p ? p['name_' + lang] : iso; };
  const num = (v, d = 1) => v == null || isNaN(v) ? '—' : Number(v).toLocaleString(lang === 'fr' ? 'fr-FR' : 'en-GB', { maximumFractionDigits: d });
  const big = v => {
    if (v == null) return '—';
    const a = Math.abs(v);
    if (a >= 1e12) return lang === 'fr' ? num(v / 1e9, 0) + ' Md $' : num(v / 1e12, 2) + ' tn $';
    if (a >= 1e9) return num(v / 1e9, 1) + L(' Md $', ' bn $');
    if (a >= 1e6) return num(v / 1e6, 1) + L(' M', ' m');
    return num(v, 0);
  };
  const money = v => v == null ? '—' : big(v) + (Math.abs(v) < 1e9 ? ' $' : '');
  const val = (p, k) => p && p[k] ? p[k].value : null;
  const yr = (p, k) => p && p[k] ? p[k].year : '';
  const fmtDate = iso => new Date(iso).toLocaleDateString(lang === 'fr' ? 'fr-FR' : 'en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

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
  function countFor(stats, w, cats) { const s = (stats[w] || {}).by_cat || {}; return cats.reduce((n, c) => n + (s[c] || 0), 0); }
  function incidentLevel(n90) { return n90 >= 60 ? 5 : n90 >= 20 ? 4 : n90 >= 5 ? 3 : n90 >= 1 ? 2 : 1; }
  function rateRows(iso) {
    const st = STATS[iso] || {}, pr = P[iso] || {}, fb = FB[iso] || {}, r = RISK[iso];
    const maxAdv = r ? Math.max(0, ...Object.values(r.advisories || {}).map(a => a.level)) : 0;
    const stab = val(pr, 'wgi_stability'), hom = val(pr, 'homicide_rate');
    return RISK_ROWS.map(row => {
      const c = { h24: countFor(st, '24h', row.cats), h72: countFor(st, '72h', row.cats), d7: countFor(st, '7d', row.cats), d90: countFor(st, '90d', row.cats) };
      let lvl = incidentLevel(c.d90), basis = [];
      const bump = (v, why) => { if (v > lvl) { lvl = v; } if (why) basis.push(why); };
      if (row.key === 'terrorism' && fb.terrorist_groups) bump(maxAdv >= 4 ? 4 : 3, L('groupes terroristes actifs', 'active terrorist groups'));
      if (row.key === 'conflict' && maxAdv >= 4) bump(4, L('avis « ne pas se rendre »', '“do not travel” advisory'));
      if (row.key === 'political' && stab != null) bump(stab < 15 ? 5 : stab < 30 ? 4 : stab < 50 ? 3 : stab < 70 ? 2 : 1, L(`stabilité politique ${num(stab, 0)}/100`, `political stability ${num(stab, 0)}/100`));
      if (row.key === 'crime' && hom != null) bump(hom >= 20 ? 5 : hom >= 10 ? 4 : hom >= 5 ? 3 : hom >= 2 ? 2 : 1, L(`${num(hom)} homicides/100 000 hab.`, `${num(hom)} homicides per 100k`));
      if (row.key === 'natural' && fb.natural_hazards) bump(2, L('aléas naturels connus', 'known natural hazards'));
      if (row.key === 'cyber') bump(2, L('menace mondiale de fond', 'global baseline threat'));
      if (c.d90) basis.push(L(`${c.d90} incident(s) sur 90 j`, `${c.d90} incident(s) in 90 d`));
      const weekly = c.d90 / 13;
      const trend = c.d90 < 3 ? '→' : c.d7 > weekly * 1.5 ? '↑' : c.d7 < weekly * 0.5 ? '↓' : '→';
      return { ...row, lvl: Math.min(5, lvl), c, trend, basis };
    }).sort((a, b) => b.lvl - a.lvl || b.c.d90 - a.c.d90);
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
    add(L(`Posture générale (niveau ${lvl} – ${riskName(lvl)})`, `General posture (level ${lvl} – ${riskName(lvl)})`), general[lvl] || general[2]);
    const specific = {
      terrorism: [L('Éviter les lieux de rassemblement, lieux de culte et sites symboliques lors des périodes sensibles.', 'Avoid gatherings, places of worship and symbolic sites during sensitive periods.'), L('Varier itinéraires et horaires ; repérer les issues dans les lieux fréquentés.', 'Vary routes and schedules; identify exits in crowded venues.')],
      conflict: [L('Cartographier les zones interdites et zones de front ; interdire tout déplacement non validé hors des zones autorisées.', 'Map no-go zones and front lines; no unapproved movement outside permitted areas.'), L('Abri renforcé sur site, protocole alerte aérienne/tirs indirects.', 'Hardened shelter on site, air-raid / indirect fire protocol.')],
      attack: [L('Profil discret, pas de signes extérieurs de richesse ; transport sécurisé porte-à-porte.', 'Low profile, no visible wealth; secure door-to-door transport.'), L('Sensibilisation anti-enlèvement ; assurance K&R et cellule de crise identifiée.', 'Kidnap-avoidance awareness; K&R insurance and identified crisis cell.')],
      unrest: [L('Éviter les manifestations ; suivre les appels à la grève et à la mobilisation.', 'Avoid demonstrations; monitor strike and protest calls.'), L('Prévoir télétravail, stocks et itinéraires alternatifs pour les sites.', 'Plan remote work, supplies and alternative routes for sites.')],
      political: [L('Suivre le calendrier politique (élections, votes, décisions judiciaires) et anticiper les couvre-feux.', 'Track the political calendar (elections, votes, court rulings) and anticipate curfews.'), L('Maintenir des liens avec l\'ambassade et les réseaux d\'entreprises locaux.', 'Maintain links with the embassy and local business networks.')],
      crime: [L('Sécurité physique des sites (contrôle d\'accès, vidéosurveillance, gardiennage) adaptée au niveau de criminalité.', 'Site physical security (access control, CCTV, guarding) sized to crime level.'), L('Limiter les déplacements de nuit ; distributeurs dans des lieux sûrs.', 'Limit night travel; use ATMs in secure locations.')],
      cyber: [L('Appareils dédiés pour les pays à risque, VPN, chiffrement ; vigilance face à l\'hameçonnage.', 'Dedicated devices for high-risk countries, VPN, encryption; phishing vigilance.')],
      natural: [L('Plan de continuité d\'activité tenant compte des saisons à risque (cyclones, moussons, feux).', 'Business continuity plan covering risk seasons (cyclones, monsoon, fires).'), L('Consignes séisme/inondation connues du personnel ; kits d\'urgence sur site.', 'Staff trained on earthquake/flood drills; emergency kits on site.')],
      health: [L('Vérifier vaccinations et prophylaxies avant départ ; assurance médicale et évacuation sanitaire.', 'Check vaccinations and prophylaxis before travel; medical and medevac insurance.'), L('Identifier les établissements de santé de référence près des sites.', 'Identify reference medical facilities near sites.')],
    };
    top.forEach(k => { if (specific[k]) add(RISK_ROWS.find(r => r.key === k)[lang], specific[k]); });
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
      out.push(L(`${wb.count} projets actifs de la Banque mondiale (${money(wb.total_usd)}) : marchés publics financés par bailleurs${sectors ? `, en particulier ${sectors}` : ''}. Suivre les avis de passation de marchés.`,
        `${wb.count} active World Bank projects (${money(wb.total_usd)}): donor-funded public procurement${sectors ? `, notably ${sectors}` : ''}. Monitor procurement notices.`));
    }
    const fdi = val(pr, 'fdi_inflows_pct_gdp');
    if (fdi != null && fdi >= 3) out.push(L(`Pays attractif pour l'investissement étranger (IDE ≈ ${num(fdi)} % du PIB).`, `Attractive for foreign investment (FDI ≈ ${num(fdi)}% of GDP).`));
    if (fb.natural_resources) out.push(L(`Filières liées aux ressources naturelles : ${fb.natural_resources.split(',').slice(0, 5).join(',')}.`, `Natural-resource value chains: ${fb.natural_resources.split(',').slice(0, 5).join(',')}.`));
    if (fb.industries) out.push(L(`Industries principales : ${fb.industries.split(',').slice(0, 6).join(',')}.`, `Main industries: ${fb.industries.split(',').slice(0, 6).join(',')}.`));
    if (r && r.level >= 3) out.push(L('Demande structurelle en services de sûreté : conseil, protection des sites et des personnes, formation, gestion de crise, veille — votre cœur de métier.', 'Structural demand for security services: consulting, site and personnel protection, training, crisis management, intelligence — your core business.'));
    const rq = val(pr, 'wgi_regulation'), cc = val(pr, 'wgi_corruption');
    if (rq != null && rq < 35) out.push(L('Environnement réglementaire difficile : partenaire local fiable et due diligence approfondie indispensables.', 'Difficult regulatory environment: reliable local partner and thorough due diligence essential.'));
    if (cc != null && cc < 30) out.push(L('Risque de corruption élevé : programme de conformité (loi Sapin II, FCPA) et vérification des intermédiaires.', 'High corruption risk: compliance programme (Sapin II, FCPA) and intermediary vetting.'));
    return out;
  }

  /* ------------------------------------------------ rendu */
  function bars(items) {
    return `<div class="bars">${items.map(([label, v, note]) => `<div class="bar"><span class="bl">${esc(label)}</span><span class="track"><span class="fill" style="width:${v == null ? 0 : Math.max(2, v)}%;background:${v == null ? '#ccc' : v < 25 ? '#C73E4D' : v < 45 ? '#EA8639' : v < 65 ? '#F0BE4A' : '#5FA37C'}"></span></span><span class="bv">${v == null ? '—' : num(v, 0)}</span>${note ? `<span class="bn">${esc(note)}</span>` : ''}</div>`).join('')}</div>`;
  }
  const kv = rows => `<dl class="kv">${rows.filter(([, v]) => v && v !== '—').map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join('')}</dl>`;
  const lvlBadge = l => `<span class="lvl" style="background:${RISK_COLORS[l || 0]}">${l || '–'}</span>`;

  function render(iso) {
    const r = RISK[iso], pr = P[iso] || {}, fb = FB[iso] || {}, b = pr.basics || {};
    const name = cname(iso);
    document.title = `${name} – ${L('Rapport pays', 'Country report')} – ${(D.settings || {}).product_name || 'Angor Intelligence'}`;
    const rows = rateRows(iso);
    const st = STATS[iso] || {};
    const recent = EVENTS.filter(e => e.country === iso).sort((a, b2) => b2.severity - a.severity || (b2.date > a.date ? 1 : -1)).slice(0, 10);
    const econ = (ECON[iso] || []).slice(0, 8);
    const g = pr.imf_growth || {}, inf = pr.imf_inflation || {};
    const yrs = Object.keys(g).sort();
    const advs = r ? Object.entries(r.advisories || {}) : [];
    const today = new Date().toISOString();
    const sanctions = { extensive: L('Étendues (UE/États-Unis)', 'Extensive (EU/US)'), extensive_us: L('Embargo américain', 'US embargo'), sectoral: L('Sectorielles', 'Sectoral'), targeted: L('Ciblées (personnes/entités)', 'Targeted (persons/entities)'), partially_lifted: L('Partiellement levées (2025)', 'Partially lifted (2025)') }[pr.sanctions];

    $('#report').innerHTML = `
    <section class="page cover">
      <div class="brand">${esc((D.settings || {}).product_name || 'Angor Intelligence')} · ${L('Rapport pays sûreté & intelligence économique', 'Country security & business intelligence brief')}</div>
      <div class="title-row">
        <div><h1>${esc(name)}</h1><div class="sub">${esc([b.capital || fb.capital, (COUNTRIES.find(c => c.iso2 === iso) || {}).region].filter(Boolean).join(' · '))}</div></div>
        <div class="risk-box" style="border-color:${RISK_COLORS[r ? r.level : 0]}">${lvlBadge(r && r.level)}<div><div class="rn">${L('Risque global', 'Overall risk')} : ${esc(riskName(r && r.level))}</div><div class="rd">${esc(riskDesc(r && r.level))}</div></div></div>
      </div>
      <div class="meta">${L('Édité le', 'Issued')} ${fmtDate(today)} · ${L('Données collectées le', 'Data collected')} ${D.generated ? fmtDate(D.generated) : '—'}</div>
      <div class="facts">
        ${[[L('Population', 'Population'), big(val(pr, 'population'))], [L('PIB', 'GDP'), money(val(pr, 'gdp_usd'))],
           [L('Croissance', 'Growth') + (yrs.length ? ` ${yrs[yrs.length - 2] || ''}` : ''), yrs.length ? num(g[yrs[yrs.length - 2]] ?? g[yrs[0]]) + ' %' : num(val(pr, 'gdp_growth')) + ' %'],
           [L('Inflation', 'Inflation'), num(val(pr, 'inflation')) + ' %'], [L('Incidents 7 j', 'Incidents 7 d'), (st['7d'] || {}).total || 0], [L('Incidents 90 j', 'Incidents 90 d'), (st['90d'] || {}).total || 0]]
          .map(([k, v]) => `<div class="fact"><div class="fv">${esc(v)}</div><div class="fk">${esc(k)}</div></div>`).join('')}
      </div>

      <h2>${icon('globe')} 1. ${L('Informations générales', 'General information')}</h2>
      ${fb.background ? `<p class="lead">${esc(fb.background)}</p>` : ''}
      <div class="cols">
        ${kv([[L('Situation', 'Location'), esc(fb.location)], [L('Superficie', 'Area'), b.area_km2 ? num(b.area_km2, 0) + ' km²' : esc(fb.area)],
              [L('Capitale', 'Capital'), esc(b.capital || fb.capital)], [L('Régime', 'Government'), esc(fb.government_type)],
              [L('Système juridique', 'Legal system'), esc(fb.legal_system)], [L('Langues', 'Languages'), esc((b.languages || []).join(', ') || fb.languages)],
              [L('Monnaie', 'Currency'), esc((b.currencies || []).join(', '))]])}
        ${kv([[L('Groupes ethniques', 'Ethnic groups'), esc(fb.ethnic_groups)], [L('Religions', 'Religions'), esc(fb.religions)],
              [L('Grandes villes', 'Major cities'), esc(fb.urban_areas)], [L('Climat', 'Climate'), esc(fb.climate)],
              [L('Aléas naturels', 'Natural hazards'), esc(fb.natural_hazards)]])}
      </div>
    </section>

    <section class="page">
      <h2>${icon('shield')} 2. ${L('Analyse des risques sûreté', 'Security risk analysis')}</h2>
      <p class="hint">${L('Classement des risques par niveau (1 à 5) et nombre d\'incidents enregistrés par l\'outil. Le niveau combine les incidents détectés et des indicateurs structurels (avis officiels, stabilité politique, homicides, groupes armés).', 'Risks ranked by level (1 to 5) with incidents recorded by the tool. The level combines detected incidents and structural indicators (official advisories, political stability, homicides, armed groups).')}</p>
      <table class="matrix"><thead><tr><th>${L('Risque', 'Risk')}</th><th>${L('Niveau', 'Level')}</th><th>${L('Tend.', 'Trend')}</th><th>24 h</th><th>72 h</th><th>${L('7 j', '7 d')}</th><th>${L('90 j', '90 d')}</th><th>${L('Fondement', 'Basis')}</th></tr></thead>
      <tbody>${rows.map(x => `<tr><td><strong>${esc(x[lang])}</strong></td><td class="nowrap">${lvlBadge(x.lvl)} ${esc(riskName(x.lvl))}</td><td class="c">${x.trend}</td>
        <td class="c">${x.c.h24}</td><td class="c">${x.c.h72}</td><td class="c">${x.c.d7}</td><td class="c">${x.c.d90}</td><td class="small">${esc(x.basis.join(' · '))}</td></tr>`).join('')}</tbody></table>
      ${advs.length ? `<h3>${L('Avis officiels aux voyageurs', 'Official travel advisories')}</h3><ul class="plain">${advs.map(([src, a]) => `<li><strong>${esc(src)}</strong> — ${L('niveau', 'level')} ${a.level}/${a.scale || 4} : ${esc(a.label)}</li>`).join('')}</ul>` : ''}
      ${fb.terrorist_groups ? `<h3>${L('Groupes terroristes présents (Factbook)', 'Terrorist groups present (Factbook)')}</h3><p>${esc(fb.terrorist_groups)}</p>` : ''}
      <h3>${L('Incidents majeurs récents (30 j)', 'Major recent incidents (30 d)')}</h3>
      ${recent.length ? `<table class="list"><tbody>${recent.map(e => `<tr><td><span class="dot" style="background:${SEV_COLORS[e.severity]}"></span></td><td class="nowrap">${fmtDate(e.date)}</td><td><strong>${esc(e.title)}</strong>${e.headline && e.headline !== e.title ? `<br><span class="small">${esc(e.headline)}</span>` : ''}</td><td class="small">${esc(catName(e.category))}<br>${esc(e.source)}${(e.tags || []).includes('auto-detected') ? ' · auto' : ''}</td></tr>`).join('')}</tbody></table>` : `<p class="hint">${L('Aucun incident enregistré sur la période.', 'No incident recorded in the period.')}</p>`}
    </section>

    <section class="page">
      <h2>${icon('siren')} 3. ${L('Recommandations sûreté (personnels et sites)', 'Security recommendations (staff and sites)')}</h2>
      ${recommendations(iso, rows).map(g2 => `<h3>${esc(g2.title)}</h3><ul>${g2.items.map(i => `<li>${esc(i)}</li>`).join('')}</ul>`).join('')}
      <p class="hint">${L('Recommandations génériques à adapter par l\'analyste sûreté au contexte précis (zones, activité, profil des voyageurs).', 'Generic recommendations to be tailored by the security analyst (areas, activity, traveller profile).')}</p>
    </section>

    <section class="page">
      <h2>${icon('briefcase')} 4. ${L('Angles business', 'Business angles')}</h2>
      <ul>${businessAngles(iso).map(a => `<li>${esc(a)}</li>`).join('') || `<li>${L('Données insuffisantes.', 'Insufficient data.')}</li>`}</ul>
      <div class="cols">
        ${kv([[L('PIB par habitant', 'GDP per capita'), val(pr, 'gdp_per_capita') ? num(val(pr, 'gdp_per_capita'), 0) + ' $ (' + yr(pr, 'gdp_per_capita') + ')' : ''],
              [L('Prévisions FMI (croissance)', 'IMF growth forecast'), yrs.map(y => `${y} : ${num(g[y])} %`).join(' · ')],
              [L('Prévisions FMI (inflation)', 'IMF inflation forecast'), Object.keys(inf).sort().map(y => `${y} : ${num(inf[y])} %`).join(' · ')],
              [L('Chômage', 'Unemployment'), val(pr, 'unemployment') != null ? num(val(pr, 'unemployment')) + ' %' : ''],
              [L('IDE entrants', 'FDI inflows'), val(pr, 'fdi_inflows_pct_gdp') != null ? num(val(pr, 'fdi_inflows_pct_gdp')) + L(' % du PIB', '% of GDP') : ''],
              [L('Commerce extérieur', 'Trade'), val(pr, 'trade_pct_gdp') != null ? num(val(pr, 'trade_pct_gdp'), 0) + L(' % du PIB', '% of GDP') : '']])}
        ${kv([[L('Exportations', 'Exports'), esc(fb.exports_commodities)], [L('Clients', 'Export partners'), esc(fb.exports_partners)],
              [L('Fournisseurs', 'Import partners'), esc(fb.imports_partners)], [L('Agriculture', 'Agriculture'), esc(fb.agriculture)]])}
      </div>
      ${pr.wb_projects && pr.wb_projects.top && pr.wb_projects.top.length ? `<h3>${L('Principaux projets financés par la Banque mondiale', 'Main World Bank-funded projects')}</h3>
        <table class="list"><tbody>${pr.wb_projects.top.map(p => `<tr><td><a href="${esc(p.url)}">${esc(p.name)}</a></td><td class="small">${esc(p.sector)}</td><td class="nowrap r">${money(p.amount_usd)}</td></tr>`).join('')}</tbody></table>` : ''}
      ${econ.length ? `<h3>${L('Actualité économique récente', 'Recent business news')}</h3><ul class="plain">${econ.map(e => `<li><a href="${esc(e.url)}">${esc(e.title)}</a> <span class="small">— ${esc(e.source)}, ${fmtDate(e.date)}</span></li>`).join('')}</ul>` : ''}
    </section>

    <section class="page">
      <h2>${icon('scale')} 5. ${L('Spécificités du pays', 'Country specifics')}</h2>
      <h3>${L('Gouvernance (Banque mondiale, 0 = pire, 100 = meilleur)', 'Governance (World Bank, 0 = worst, 100 = best)')}</h3>
      ${bars([[L('Contrôle de la corruption', 'Control of corruption'), val(pr, 'wgi_corruption')], [L('État de droit', 'Rule of law'), val(pr, 'wgi_rule_of_law')],
              [L('Qualité de la réglementation', 'Regulatory quality'), val(pr, 'wgi_regulation')], [L('Efficacité des pouvoirs publics', 'Government effectiveness'), val(pr, 'wgi_government')],
              [L('Stabilité politique / absence de violence', 'Political stability / no violence'), val(pr, 'wgi_stability')], [L('Voix et responsabilité', 'Voice and accountability'), val(pr, 'wgi_voice')]])}
      <div class="cols">
        ${kv([[L('Société', 'Society'), multicultural(b, fb)], [L('Sanctions internationales', 'International sanctions'), sanctions ? esc(sanctions) + L(' — indicatif, à vérifier', ' — indicative, to be checked') : L('Pas de régime majeur identifié (à vérifier)', 'No major regime identified (to be checked)')],
              [L('Création d\'entreprise', 'Starting a business'), val(pr, 'days_to_start_business') != null ? `${num(val(pr, 'days_to_start_business'), 0)} ${L('jours', 'days')} (${yr(pr, 'days_to_start_business')})` : ''],
              [L('Pression fiscale totale', 'Total tax rate'), val(pr, 'total_tax_rate') != null ? `${num(val(pr, 'total_tax_rate'), 0)} % ${L('des bénéfices', 'of profits')} (${yr(pr, 'total_tax_rate')})` : ''],
              [L('Participation étrangère', 'Foreign ownership'), L('À vérifier au cas par cas : secteurs réservés, obligation d\'associé local (ex. 51 %), autorisations préalables. Sources : OCDE (indice de restrictivité des IDE), CNUCED Investment Policy Hub, ambassade et Business France.', 'To be checked case by case: restricted sectors, local-partner requirements (e.g. 51%), prior approvals. Sources: OECD FDI Restrictiveness Index, UNCTAD Investment Policy Hub, embassy trade desk.')]])}
        ${kv([[L('Forces armées', 'Armed forces'), esc(fb.military)], [L('Dépenses militaires', 'Military spending'), val(pr, 'military_pct_gdp') != null ? num(val(pr, 'military_pct_gdp')) + L(' % du PIB', '% of GDP') : esc(fb.military_spend)],
              [L('Trafics / criminalité organisée', 'Trafficking / organised crime'), esc([fb.drugs, fb.trafficking].filter(Boolean).join(' · ').slice(0, 420))],
              [L('Réfugiés et déplacés', 'Refugees and IDPs'), esc(fb.refugees)], [L('Internet', 'Internet users'), val(pr, 'internet_users') != null ? num(val(pr, 'internet_users'), 0) + ' %' : '']])}
      </div>
      <h3>${L('Sources et méthode', 'Sources and method')}</h3>
      <p class="small">${L('Incidents : USGS, GDACS, NASA EONET, OMS, GDELT et presse locale/internationale (détection automatique, non vérifiée). Avis aux voyageurs : Département d\'État américain, Gouvernement du Canada. Économie et gouvernance : Banque mondiale (WDI, WGI, projets), FMI (World Economic Outlook). Contexte : CIA World Factbook (archive 2026, domaine public), REST Countries. Ce rapport est un outil d\'aide à la décision : il ne garantit pas l\'exhaustivité des informations et doit être complété par l\'analyse d\'un professionnel de la sûreté.', 'Incidents: USGS, GDACS, NASA EONET, WHO, GDELT and local/international press (automated, unverified detection). Travel advisories: US State Department, Government of Canada. Economy and governance: World Bank (WDI, WGI, projects), IMF (World Economic Outlook). Background: CIA World Factbook (2026 archive, public domain), REST Countries. This report is a decision-support tool: it does not guarantee completeness and must be complemented by a security professional\'s analysis.')}</p>
    </section>`;
  }
  function multicultural(b, fb) {
    const langs = (b.languages || []).length;
    const pct = ((fb.ethnic_groups || '').match(/\d+(\.\d+)?%/g) || []).length;
    if (langs >= 3 || pct >= 3) return L(`Société multiculturelle / multilingue (${langs} langue(s) officielle(s) ou majeure(s)). Tenir compte des équilibres communautaires dans le recrutement et la communication.`, `Multicultural / multilingual society (${langs} official or major language(s)). Consider community balances in hiring and communication.`);
    return L('Société relativement homogène sur le plan linguistique.', 'Relatively homogeneous linguistically.');
  }

  /* ------------------------------------------------ démarrage */
  function init() {
    const sel = $('#tb-country');
    const list = COUNTRIES.slice().sort((a, b) => a['name_' + lang].localeCompare(b['name_' + lang]));
    sel.innerHTML = list.map(c => `<option value="${c.iso2}">${esc(c['name_' + lang])}${RISK[c.iso2] ? ` (${RISK[c.iso2].level})` : ''}</option>`).join('');
    let iso = decodeURIComponent(location.hash.slice(1)) || 'FR';
    if (!COUNTRIES.some(c => c.iso2 === iso)) iso = 'FR';
    sel.value = iso;
    $('#tb-back').innerHTML = icon('arrow-left') + ' ' + L('Carte', 'Map');
    $('#tb-print').innerHTML = icon('printer') + ' ' + L('Imprimer / PDF', 'Print / PDF');
    $('#tb-lang').textContent = lang === 'fr' ? 'EN' : 'FR';
    document.documentElement.lang = lang;
    render(iso);
  }
  $('#tb-country').addEventListener('change', ev => { location.hash = ev.target.value; });
  window.addEventListener('hashchange', init);
  $('#tb-print').addEventListener('click', () => window.print());
  $('#tb-lang').addEventListener('click', () => { lang = lang === 'fr' ? 'en' : 'fr'; try { localStorage.setItem('vs-lang', JSON.stringify(lang)); } catch (e) { /* */ } init(); });
  init();
})();
