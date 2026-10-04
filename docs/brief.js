/* Angor Intelligence – brief de mission (voyage d'affaires), imprimable en PDF.
   Tout est calculé dans le navigateur à partir des données publiées : rien n'est envoyé, rien n'est stocké en ligne.
   Sert de trace « duty of care » : date d'édition, sources consultées, recommandation et visas de validation. */
(function () {
  'use strict';
  const D = window.VS_DATA || {};
  const P = (window.VS_PROFILES || {}).countries || {};
  const GUIDES = (window.VS_GUIDES || {}).countries || {};
  const PRACT = (window.VS_PRACTICAL || {}).countries || {};
  const PROV = window.VS_PROVIDERS || { providers: [], services: {}, local: {} };
  const CITIES = ((window.VS_CITIES || {}).cities || []);
  const COUNTRIES = (window.VS_COUNTRIES || { features: [] }).features.map(f => f.properties);
  const ICONS = window.VS_ICONS || {};
  const TAX = D.taxonomy || { categories: {}, risk_levels: {}, severity: {} };
  const RISK = D.countries || {};
  const PULSE = D.pulse || {};
  const EVENTS = D.events || [];
  let lang = 'fr';
  try { lang = JSON.parse(localStorage.getItem('vs-lang')) || 'fr'; } catch (e) { /* défaut */ }

  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const icon = (n, s = 16) => `<svg viewBox="0 0 24 24" width="${s}" height="${s}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[n] || ''}</svg>`;
  const L = (fr, en) => lang === 'fr' ? fr : en;
  const norm = s => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[’']/g, ' ').trim();
  const flag = (iso, w = 40) => iso && iso.length === 2 ? `<img class="flag" src="vendor/flags/${iso.toLowerCase()}.svg" alt="" onerror="this.remove()">` : '';
  const RISK_COLORS = { 0: '#C9D1D9', 1: '#5FA37C', 2: '#B3C75A', 3: '#F0BE4A', 4: '#EA8639', 5: '#C73E4D' };
  const SEV_COLORS = { 1: '#3F86C6', 2: '#E0A21B', 3: '#E0622B', 4: '#B0182E' };
  const MIN_COLORS = { 1: '#2E9E5B', 2: '#E3B505', 3: '#EE7D22', 4: '#D7263D' };
  const pulseColor = v => v < 25 ? '#9E1B32' : v < 45 ? '#E0592A' : v < 65 ? '#E3B505' : v < 80 ? '#8DBF4E' : '#2E9E5B';
  const riskName = l => (TAX.risk_levels[l] || {})[lang] || '—';
  const sevName = s => (TAX.severity[s] || {})[lang] || s;
  const catName = c => (TAX.categories[c] || {})[lang] || c;
  const cname = iso => { const p = COUNTRIES.find(c => c.iso2 === iso); return p ? p['name_' + lang] : iso; };
  const fmtDate = d => d ? new Date(d.length === 10 ? d + 'T12:00:00' : d).toLocaleDateString(lang === 'fr' ? 'fr-FR' : 'en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) : '—';
  const fmtShort = d => new Date(d).toLocaleDateString(lang === 'fr' ? 'fr-FR' : 'en-GB', { day: '2-digit', month: '2-digit' });
  const hav = (a, b, c, d) => { const R = 6371, r = Math.PI / 180, x = Math.sin((c - a) * r / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin((d - b) * r / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(x)); };

  const T = {
    country: ['Pays', 'Country'], city: ['Ville principale', 'Main city'], from: ['Départ', 'Departure'], to: ['Retour', 'Return'],
    profile: ['Profil', 'Profile'], pax: ['Voyageurs', 'Travellers'], purpose: ['Objet de la mission', 'Purpose of the mission'],
    lodging: ['Hébergement prévu', 'Planned accommodation'], issuer: ['Émis par (service, société)', 'Issued by (department, company)'],
    privacy: ['Les champs restent dans ce navigateur : rien n\'est envoyé. N\'indiquez pas de données personnelles sensibles ; les noms se renseignent à la main sur le document imprimé.',
      'Fields stay in this browser: nothing is sent. Do not enter sensitive personal data; names are handwritten on the printed document.'],
  };
  const PROFILES = {
    biz: ['Voyageur d\'affaires', 'Business traveller'], team: ['Équipe technique / chantier', 'Technical / site team'],
    exec: ['Dirigeant / personnalité exposée', 'Executive / high-profile'], woman: ['Voyageuse', 'Woman traveller'],
    first: ['Premier séjour dans le pays', 'First visit to the country'], long: ['Séjour long / expatriation', 'Long stay / expatriation'],
  };

  /* ------------------------------------------------ calculs */
  function cityPoint(iso, city) {
    if (!city) return null;
    const k = norm(city);
    const c = CITIES.find(x => x[1] === iso && norm(x[0]) === k) || CITIES.find(x => x[1] === iso && norm(x[0]).startsWith(k));
    if (c) return { name: c[0], lat: c[2], lon: c[3] };
    const e = EVENTS.find(x => x.country === iso && norm(x.place).startsWith(k) && x.precision !== 'country');
    return e ? { name: city, lat: e.lat, lon: e.lon } : null;
  }
  function advOf(r, src) { return r && r.advisories ? r.advisories[src] || null : null; }
  /** Recommandation indicative : Go / Go sous conditions / Déconseillé / Non (sauf mission vitale). */
  function decision(iso, near, r) {
    const lvl = r ? r.level : 0;
    const meae = advOf(r, 'MEAE (France)'), fc = advOf(r, 'FCDO (UK)'), us = advOf(r, 'US State Dept');
    const mw = meae ? (meae.parts ? meae.level : meae.max || meae.level) : 0;   // niveau du pays entier
    const mx = meae ? (meae.max || meae.level) : 0;
    const severeNear = near.filter(e => e.severity >= 3 && Date.now() - Date.parse(e.date) < 7 * 864e5).length;
    const why = [];
    let code = 'go';
    if (lvl >= 5 || mw >= 4 || (us && us.level >= 4 && !(meae && meae.parts))) {
      code = 'nogo';
      if (lvl >= 5) why.push(L('risque pays Extrême (5/5)', 'Extreme country risk (5/5)'));
      if (mw >= 4) why.push(L('MEAE : formellement déconseillé', 'French MFA: advise against all travel'));
      if (us && us.level >= 4) why.push(L('US State Dept : Do not travel', 'US State Dept: Do not travel'));
    } else if (lvl >= 4 || mw >= 3 || severeNear >= 3) {
      code = 'restricted';
      if (lvl >= 4) why.push(L('risque pays Élevé (4/5)', 'High country risk (4/5)'));
      if (mw >= 3) why.push(L('MEAE : déconseillé sauf raison impérative', 'French MFA: advise against all but essential travel'));
      if (severeNear >= 3) why.push(L(`${severeNear} incidents graves à proximité en 7 jours`, `${severeNear} serious incidents nearby in 7 days`));
    } else if (lvl >= 3 || mx >= 2 || severeNear >= 1 || (fc && /avoid/i.test(fc.label || ''))) {
      code = 'conditions';
      if (lvl >= 3) why.push(L('risque pays Modéré (3/5)', 'Moderate country risk (3/5)'));
      if (mx >= 3) why.push(L('certaines zones déconseillées par le MEAE', 'some areas advised against by the French MFA'));
      else if (mx >= 2) why.push(L('MEAE : vigilance renforcée', 'French MFA: increased vigilance'));
      if (severeNear) why.push(L(`${severeNear} incident(s) grave(s) à proximité en 7 jours`, `${severeNear} serious incident(s) nearby in 7 days`));
      if (fc && /avoid/i.test(fc.label || '')) why.push(L('FCDO : zones déconseillées', 'FCDO: areas advised against'));
    } else why.push(L('pas de restriction officielle ni d\'incident grave récent à proximité', 'no official restriction nor recent serious incident nearby'));
    const label = { go: L('Mission possible – mesures standard', 'Go – standard measures'), conditions: L('Mission possible sous conditions', 'Go with conditions'),
      restricted: L('Déconseillée sauf raison impérative – validation de la direction', 'Advised against unless essential – executive approval'),
      nogo: L('Non – sauf mission vitale, sur décision de la direction', 'No-go – vital missions only, on executive decision') }[code];
    const color = { go: '#2E9E5B', conditions: '#E3B505', restricted: '#EE7D22', nogo: '#D7263D' }[code];
    return { code, label, color, why };
  }
  function measures(lvl, profile, cats, days) {
    const out = [];
    const add = (title, items) => out.push({ title, items: items.filter(Boolean) });
    const checkin = lvl >= 4 ? L('à chaque mouvement (départ / arrivée) et au minimum matin et soir', 'at every movement (departure / arrival) and at least morning and evening')
      : lvl >= 3 ? L('deux fois par jour (matin et soir)', 'twice a day (morning and evening)') : L('une fois par jour, et à l\'arrivée', 'once a day, and on arrival');
    add(L('Avant le départ', 'Before departure'), [
      L('Validation du déplacement par le manager' + (lvl >= 3 ? ' et par la fonction sûreté' : ''), 'Trip approved by the manager' + (lvl >= 3 ? ' and by the security function' : '')),
      L('Inscription sur Fil d\'Ariane (ressortissants français) : pastel.diplomatie.gouv.fr/fildariane', 'Register with your embassy (French nationals: Fil d\'Ariane)'),
      L('Assurance et assistance (rapatriement, frais médicaux) vérifiées ; numéro de l\'assisteur enregistré', 'Insurance and assistance (repatriation, medical) checked; assistance number saved'),
      L('Vaccins et traitements vérifiés auprès d\'un centre de vaccinations internationales (4 à 6 semaines avant)', 'Vaccines and prophylaxis checked with a travel clinic (4–6 weeks before)'),
      L('Copies des documents (passeport, visa, assurance) stockées hors du bagage', 'Copies of documents (passport, visa, insurance) stored separately'),
      L('Itinéraire, hébergement et contacts communiqués à l\'employeur ; briefing sûreté reçu', 'Itinerary, accommodation and contacts shared with the employer; security briefing received'),
      lvl >= 4 || profile === 'exec' ? L('Téléphone et ordinateur dédiés (« vierges »), chiffrement, pas de données sensibles embarquées', 'Dedicated clean phone and laptop, encryption, no sensitive data carried') : '',
    ]);
    add(L('Sur place', 'In country'), [
      L(`Points de contact : ${checkin}`, `Check-ins: ${checkin}`),
      lvl >= 3 ? L('Transport avec chauffeur de confiance réservé à l\'avance ; pas de taxi hélé dans la rue', 'Pre-booked trusted driver; no street-hailed taxis') : L('Taxis officiels ou VTC ; éviter les transports informels la nuit', 'Official taxis or ride-hailing; avoid informal transport at night'),
      lvl >= 4 ? L('Prestataire sûreté local, itinéraires validés, déplacements de jour uniquement, suivi GPS', 'Local security provider, validated routes, daylight movement only, GPS tracking') : '',
      lvl >= 3 ? L('Hôtel évalué (contrôle d\'accès, étages 2 à 6), chambre non attribuée au nom de la société', 'Vetted hotel (access control, floors 2–6), room not booked under company name') : '',
      L('Profil discret : pas de signes extérieurs de richesse ni de logo, discrétion sur l\'objet de la mission', 'Low profile: no visible wealth or logos, discretion about the mission'),
      L('Éviter manifestations et rassemblements ; suivre les alertes Angor et les consignes de l\'ambassade', 'Avoid demonstrations and gatherings; follow Angor alerts and embassy guidance'),
    ]);
    const spec = {
      terrorism: L('Terrorisme : éviter lieux symboliques et de culte aux heures d\'affluence ; repérer les issues', 'Terrorism: avoid symbolic sites and places of worship at peak times; locate exits'),
      attack: L('Attaques / enlèvements : varier trajets et horaires ; assurance K&R et cellule de crise identifiée', 'Attacks / kidnapping: vary routes and times; K&R insurance and crisis cell identified'),
      armed_conflict: L('Conflit : respecter strictement les zones autorisées ; abri identifié ; plan d\'évacuation', 'Conflict: stay strictly within permitted areas; identified shelter; evacuation plan'),
      unrest: L('Troubles : suivre les appels à manifester ; itinéraires de contournement ; stock d\'eau et de vivres', 'Unrest: monitor protest calls; alternative routes; water and food supplies'),
      crime: L('Criminalité : pas de déplacement à pied de nuit ; distributeurs dans des lieux sûrs ; portefeuille de délestage', 'Crime: no walking at night; ATMs in secure places; decoy wallet'),
      political: L('Crise politique : anticiper couvre-feux et coupures d\'Internet ; moyen de communication de secours', 'Political crisis: anticipate curfews and internet shutdowns; backup communications'),
      health: L('Épidémie en cours : mesures de prévention spécifiques, avis médical avant départ', 'Ongoing outbreak: specific prevention, medical advice before departure'),
      flood: L('Inondations : vérifier les itinéraires routiers le jour même', 'Floods: check road routes on the day'),
      cyclone: L('Cyclone : suivre les bulletins officiels ; prévoir un report du déplacement', 'Cyclone: follow official bulletins; plan to postpone'),
      earthquake: L('Séisme : consignes connues (se protéger sous un meuble solide, sortir après la secousse)', 'Earthquake: know the drill (take cover, evacuate after shaking)'),
    };
    const extra = cats.map(c => spec[c]).filter(Boolean);
    if (extra.length) add(L('Menaces constatées récemment', 'Recently observed threats'), extra);
    const prof = {
      exec: [L('Réservations au nom d\'un assistant ; pas de publication des déplacements sur les réseaux sociaux', 'Bookings under an assistant\'s name; no social-media posting of movements'),
        lvl >= 3 ? L('Protection rapprochée à évaluer ; accueil à l\'aéroport par un chauffeur identifié (code convenu)', 'Assess close protection; airport pick-up by identified driver (agreed code)') : ''],
      woman: [L('Consulter la rubrique « Voyageuses » ci-dessous ; tenue adaptée aux usages locaux', 'See the "Women travellers" section below; dress to local customs'),
        L('Éviter de voyager seule de nuit ; privilégier les hôtels avec étage réservé ou sécurité renforcée', 'Avoid travelling alone at night; prefer hotels with secured floors')],
      team: [L('Chef d\'équipe désigné pour les points de contact ; liste des personnels et contacts à jour', 'Team leader designated for check-ins; up-to-date staff and contact list'),
        L('Sûreté du site : contrôle d\'accès, point de rassemblement, trousse de secours', 'Site security: access control, assembly point, first-aid kit')],
      first: [L('Briefing culturel et sûreté renforcé ; accueil par un correspondant local', 'Extended cultural and security briefing; met by a local contact')],
      long: [L('Enregistrement consulaire, plan de sécurité du logement, contacts d\'urgence locaux', 'Consular registration, home security plan, local emergency contacts'),
        L('Revue mensuelle de la situation ; critères d\'alerte et d\'évacuation connus', 'Monthly situation review; alert and evacuation triggers known')],
    }[profile];
    if (prof) add(L('Selon le profil', 'For this profile'), prof);
    if (days > 14) add(L('Séjour long', 'Long stay'), [L('Point de situation hebdomadaire avec l\'employeur', 'Weekly situation update with the employer')]);
    return out;
  }

  /* ------------------------------------------------ rendu */
  function read() {
    return { iso: $('#f-country').value, city: $('#f-city').value.trim(), from: $('#f-from').value, to: $('#f-to').value,
      profile: $('#f-profile').value, pax: Math.max(1, +$('#f-pax').value || 1), purpose: $('#f-purpose').value.trim(),
      lodging: $('#f-lodging').value.trim(), issuer: $('#f-issuer').value.trim() };
  }
  function refId(f) {
    let h = 0; const s = JSON.stringify(f) + (D.generated || '');
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return `ANG-${f.iso}-${(f.from || '').replace(/-/g, '')}-${h.toString(36).slice(-4).toUpperCase()}`;
  }
  function render() {
    const f = read();
    const iso = f.iso, r = RISK[iso], pr = P[iso] || {}, g = GUIDES[iso] || {}, x = PRACT[iso] || {};
    const name = cname(iso);
    const pt = cityPoint(iso, f.city);
    const radius = 100;
    const since30 = Date.now() - 30 * 864e5;
    const inCountry = EVENTS.filter(e => e.country === iso && Date.parse(e.date) >= since30);
    const near = pt ? EVENTS.filter(e => e.lat != null && hav(pt.lat, pt.lon, e.lat, e.lon) <= radius && Date.parse(e.date) >= since30)
      .map(e => ({ ...e, _d: hav(pt.lat, pt.lon, e.lat, e.lon) })) : [];
    const focus = (pt ? near : inCountry).filter(e => e.confidence !== 'low' || e.verified).sort((a, b) => b.severity - a.severity || (b.date > a.date ? 1 : -1));
    let dec = decision(iso, pt ? near : [], r);  // sans ville : avis officiels et niveau pays seulement
    // évaluation go/no-go guidée transmise par le Travel buddy (paramètre g) : elle prime sur la règle simple
    const G = window.AngorGNG, gAns = G && GNG_ANS;
    let gng = null;
    if (gAns) {
      const th = G.threat({ iso, point: pt, from: f.from, to: f.to, lang });
      gng = { th, res: G.evaluate(gAns, th, lang) };
      dec = { code: { go: 'go', conditions: 'conditions', escalate: 'restricted', nogo: 'nogo' }[gng.res.code], label: gng.res.label, color: gng.res.color,
        why: [L(`go/no-go guidé : menace ${gng.res.T}/5 × vulnérabilité ${gng.res.V}/5`, `guided go/no-go: threat ${gng.res.T}/5 × vulnerability ${gng.res.V}/5`)] };
    }
    const CAL = ((window.VS_CALENDAR || {}).events || []);
    const MUSLIM = new Set('AF AL AZ BH BD BN BF TD KM DJ EG GM GN ID IR IQ JO KZ XK KW KG LB LY MY MV ML MR MA NE NG OM PK PS QA SA SN SL SO SD SY TJ TN TR TM AE UZ EH YE'.split(' '));
    const addD = (d, n) => { const x = new Date(d + 'T12:00:00Z'); x.setUTCDate(x.getUTCDate() + n); return x.toISOString().slice(0, 10); };
    const during = f.from ? CAL.filter(e => (e.iso === iso || (!e.iso && e.type === 'religious' && MUSLIM.has(iso)) || (!e.iso && e.src === 'Angor'))
      && e.prec !== 'year' && (e.e || e.d) >= addD(f.from, -2) && e.d <= addD(f.to, 2)) : [];
    const crises = (D.crises || []).filter(c => c.country === iso && (c.status === 'active' || Date.now() - Date.parse(c.last) < 10 * 864e5)).slice(0, 4);
    const TYPE = { holiday: L('Jour férié', 'Public holiday'), election: L('Élection', 'Election'), religious: L('Fête religieuse', 'Religious festival'), strike: L('Grève', 'Strike'), summit: L('Sommet', 'Summit'), anniversary: L('Anniversaire sensible', 'Sensitive anniversary'), other: L('Échéance', 'Event') };
    const TREND = { escalating: L('escalade', 'escalating'), new: L('nouvelle', 'new'), stable: L('stable', 'stable'), declining: L('décrue', 'declining') };
    const days = f.from && f.to ? Math.max(1, Math.round((Date.parse(f.to) - Date.parse(f.from)) / 864e5) + 1) : 0;
    const cats = [...new Set(focus.filter(e => e.severity >= 2).map(e => e.category))];
    const meas = measures(r ? r.level : 2, f.profile, cats, days);
    const meae = advOf(r, 'MEAE (France)'), fc = advOf(r, 'FCDO (UK)'), us = advOf(r, 'US State Dept');
    const p = PULSE[iso];
    const now = new Date();
    const ref = refId(f);
    document.title = `${L('Brief de mission', 'Mission brief')} – ${name}${f.city ? ' (' + f.city + ')' : ''} – Angor Intelligence`;
    $('#tb-title').textContent = ref;
    const hosp = (x.hospitals || []).filter(h => !pt || !f.city || norm(h.city).includes(norm(pt.name)) || norm(pt.name).includes(norm(h.city)));
    const hospitals = (hosp.length ? hosp : (x.hospitals || [])).slice(0, 5);
    const region = (c => !c ? '' : c.region === 'Western Asia' ? 'Moyen-Orient' : { Africa: 'Afrique', Europe: 'Europe', Asia: 'Asie', 'North America': 'Amériques', 'South America': 'Amériques', Oceania: 'Océanie' }[c.continent] || '')(COUNTRIES.find(c => c.iso2 === iso));
    const provs = ((PROV.local || {})[iso] || []).concat((PROV.providers || []).filter(pv => !region || (pv.regions || []).includes(region))).slice(0, 5);
    const advRow = (src, a, lvl, lab) => a ? `<tr><td><strong>${esc(src)}</strong></td><td><span class="dot" style="background:${MIN_COLORS[lvl] || '#9AA5B1'}"></span> ${esc(lab)}</td><td class="small">${a.url ? `<a href="${esc(a.url)}">${esc(a.url.replace(/^https?:\/\/(www\.)?/, '').slice(0, 48))}</a>` : ''}</td></tr>` : '';
    const sources = [
      meae && meae.url ? ['MEAE – Conseils aux voyageurs', meae.url] : null, fc && fc.url ? ['FCDO – Foreign travel advice', fc.url] : null,
      us && us.url ? ['US State Department – Travel advisory', us.url] : null,
      [L('Angor Intelligence – incidents géolocalisés (presse, GDELT, USGS, GDACS, OMS, services météo…)', 'Angor Intelligence – geolocated incidents (press, GDELT, USGS, GDACS, WHO, weather services…)'), location.origin + location.pathname.replace(/brief\.html$/, '') + `?c=${iso}`],
      (x.hospitals || []).length ? ['Wikidata – ' + L('établissements de santé, urgences', 'hospitals, emergency numbers'), 'https://www.wikidata.org'] : null,
      during.length ? [L('Agenda Angor – Nager.Date (jours fériés), Wikidata (élections), calendrier hégirien', 'Angor agenda – Nager.Date (holidays), Wikidata (elections), Hijri calendar'), 'https://date.nager.at'] : null,
      gng ? [L('Questionnaire go/no-go guidé (réponses du demandeur)', 'Guided go/no-go questionnaire (requester\'s answers)'), ''] : null,
      g && Object.keys(g).length ? [L('Fiche culturelle Angor (rédaction assistée par IA, relue)', 'Angor cultural sheet (AI-assisted, reviewed)'), ''] : null,
    ].filter(Boolean);

    $('#report').innerHTML = `
    <section class="page cover brief">
      <div class="brief-head"><div class="brand">Angor Intelligence · ${L('Brief de mission', 'Mission brief')}</div><div class="ref mono">${esc(ref)}</div></div>
      <div class="title-row">
        <div><h1>${flag(iso, 80)}${esc(name)}${f.city ? ` <span class="city">· ${esc(f.city)}</span>` : ''}</h1>
          <div class="sub">${f.from ? `${fmtDate(f.from)} → ${fmtDate(f.to)} · ${days} ${L('jour(s)', 'day(s)')}` : L('Dates à préciser', 'Dates to be confirmed')} · ${esc(L(...PROFILES[f.profile]))} · ${f.pax} ${L('voyageur(s)', 'traveller(s)')}</div></div>
        <div class="decision" style="border-color:${dec.color}"><div class="dl" style="background:${dec.color}">${icon(dec.code === 'go' ? 'check' : dec.code === 'nogo' ? 'circle-x' : 'circle-alert', 22)}</div>
          <div><div class="dn">${esc(dec.label)}</div><div class="dd">${esc(dec.why.join(' · '))}</div></div></div>
      </div>
      <div class="meta">${L('Émis le', 'Issued')} ${now.toLocaleString(lang === 'fr' ? 'fr-FR' : 'en-GB', { dateStyle: 'long', timeStyle: 'short' })} (${now.toISOString().slice(0, 16).replace('T', ' ')} UTC)
        · ${L('Données Angor du', 'Angor data as of')} ${D.generated ? fmtDate(D.generated) + ' ' + D.generated.slice(11, 16) + ' UTC' : '—'}${f.issuer ? ' · ' + L('Émis par', 'Issued by') + ' ' + esc(f.issuer) : ''}</div>
      ${f.purpose || f.lodging ? `<div class="kv2">${f.purpose ? `<div><span>${L('Objet', 'Purpose')}</span>${esc(f.purpose)}</div>` : ''}${f.lodging ? `<div><span>${L('Hébergement', 'Accommodation')}</span>${esc(f.lodging)}</div>` : ''}</div>` : ''}
      <div class="facts">
        <div class="fact"><div class="fv"><span class="lvl" style="background:${RISK_COLORS[r ? r.level : 0]}">${r ? r.level : '–'}</span></div><div class="fk">${L('Risque pays', 'Country risk')} · ${esc(riskName(r && r.level))}</div></div>
        <div class="fact"><div class="fv">${p ? `<span class="lvl round" style="background:${pulseColor(p.value)}">${p.value}</span>${p.d7 != null ? ` <span class="small">${p.d7 > 0 ? '+' : ''}${p.d7} / 7 ${L('j', 'd')}</span>` : ''}` : '—'}</div><div class="fk">Pulse (${L('stabilité', 'stability')} 0–100)</div></div>
        <div class="fact"><div class="fv">${inCountry.length}</div><div class="fk">${L('Incidents 30 j (pays)', 'Incidents 30 d (country)')}</div></div>
        <div class="fact"><div class="fv">${pt ? near.length : '—'}</div><div class="fk">${pt ? L(`À moins de ${radius} km de ${pt.name}`, `Within ${radius} km of ${pt.name}`) : L('Ville non reconnue', 'City not recognised')}</div></div>
        <div class="fact"><div class="fv">${inCountry.filter(e => e.severity >= 3).length}</div><div class="fk">${L('Graves / critiques 30 j', 'High / critical 30 d')}</div></div>
        <div class="fact"><div class="fv">${esc((x.emergency || []).slice(0, 2).join(' · ') || '—')}</div><div class="fk">${L('Urgences', 'Emergency')}</div></div>
      </div>
      <h2>${icon('shield', 18)} 1. ${L('Avis officiels', 'Official advice')}</h2>
      <table class="list"><tbody>
        ${advRow('MEAE (France)', meae, meae && (meae.max || meae.level), meae && meae.label)}
        ${advRow('FCDO (UK)', fc, fc && (fc.max || fc.level), fc && fc.label)}
        ${advRow('US State Dept', us, us && us.level, us && us.label)}
      </tbody></table>
      ${meae && (meae.excerpt || []).length ? `<blockquote class="quote">${meae.excerpt.slice(0, 4).map(q => `<p>« ${esc(q)} »</p>`).join('')}<footer>${L('Extraits MEAE – la page officielle fait foi.', 'French MFA excerpts – the official page prevails.')}</footer></blockquote>` : ''}
      ${gng ? `<h2>${icon('clipboard-check', 18)} ${L('Évaluation go / no-go guidée', 'Guided go / no-go assessment')}</h2>
        <div class="gng-brief">${G.matrix(gng.res.T, gng.res.V, lang, 170)}
          <div><p><strong>${esc(gng.res.label)}</strong> — ${L('menace', 'threat')} ${gng.res.T}/5 × ${L('vulnérabilité', 'vulnerability')} ${gng.res.V}/5 = ${gng.res.R}/25</p>
          ${gng.res.note ? `<p class="small"><strong>${esc(gng.res.note)}</strong></p>` : ''}
          <p class="small"><strong>${L('Facteurs de menace', 'Threat factors')} :</strong> ${esc(gng.th.factors.join(' · '))}</p>
          <p class="small"><strong>${L('Conditions à remplir', 'Conditions to meet')} :</strong></p>
          ${gng.res.conditions.length ? `<ul class="check">${gng.res.conditions.map(c => `<li><span class="box"></span>${esc(c)}</li>`).join('')}</ul>` : `<p class="small">${L('Aucune condition supplémentaire.', 'No additional condition.')}</p>`}</div></div>
        <table class="list small"><tbody>${G.QUESTIONS.map(q => { const o = q.opts.find(x => x[0] === gng.res.answers[q.id]) || q.opts[0]; return `<tr><td>${esc(lang === 'fr' ? q.fr : q.en)}</td><td><strong>${esc(lang === 'fr' ? o[1] : o[2])}</strong></td></tr>`; }).join('')}</tbody></table>` : ''}
      ${window._briefAi ? `<h2>${icon('file-text', 18)} ${L('Synthèse', 'Summary')}</h2><div class="ai-synth"><p>${esc(window._briefAi).replace(/\n+/g, '</p><p>')}</p><p class="hint">${L('Rédigée par IA à partir des données du brief – à relire.', 'AI-written from the brief data – to be reviewed.')}</p></div>` : ''}
      ${p && (p.drivers || []).length ? `<p class="small"><strong>Pulse – ${L('causes', 'drivers')} :</strong> ${esc(p.drivers.map(d => d.type === 'category' ? L('hausse ', 'rise ') + catName(d.category).toLowerCase() : `${d.source} ${d.from} → ${d.to}`).join(' · '))}</p>` : ''}
    </section>

    <section class="page">
      ${during.length ? `<h2>${icon('calendar', 18)} ${L('Pendant votre séjour', 'During your stay')}</h2>
        <table class="list"><tbody>${during.map(e => `<tr><td class="nowrap">${fmtShort(e.d)}${e.e && e.e !== e.d ? ' → ' + fmtShort(e.e) : ''}</td><td class="nowrap small">${esc(TYPE[e.type] || TYPE.other)}</td><td>${esc(lang === 'fr' ? e.t_fr : e.t_en || e.t_fr)}${e.type === 'religious' ? ` <span class="small">(${L('date indicative', 'indicative date')})</span>` : ''}${e.prec === 'month' ? ` <span class="small">(${L('date à préciser', 'date tbc')})</span>` : ''}</td></tr>`).join('')}</tbody></table>
        <p class="hint">${L('Jours fériés, élections et fêtes : fermetures d\'administrations, rassemblements, contrôles renforcés, transports perturbés.', 'Holidays, elections and festivals: closures, gatherings, reinforced checks, disrupted transport.')}</p>` : ''}
      <h2>${icon('siren', 18)} 2. ${L('Situation sécuritaire', 'Security situation')} ${pt ? `– ${esc(pt.name)} (${radius} km)` : `– ${esc(name)}`}, 30 ${L('jours', 'days')}</h2>
      ${crises.length ? `<p class="small"><strong>${L('Chronologies de crise', 'Crisis timelines')} :</strong></p><ul class="small">${crises.map(c => `<li><strong>${esc(lang === 'fr' ? c.title : c.title_en || c.title)}</strong> — ${c.n} incidents, ${TREND[c.trend] || ''}${c.status !== 'active' ? L(' (apaisée)', ' (calmed)') : ''}. ${esc(lang === 'fr' ? c.summary_fr : c.summary_en)}</li>`).join('')}</ul>` : ''}
      ${focus.length ? `<table class="list"><thead><tr><th>${L('Date', 'Date')}</th><th>${L('Gravité', 'Severity')}</th><th>${L('Incident', 'Incident')}</th><th>${L('Lieu', 'Place')}</th><th title="${L('Cotation de l\'Amirauté', 'Admiralty rating')}">${L('Cot.', 'Rating')}</th></tr></thead><tbody>
        ${focus.slice(0, 14).map(e => `<tr><td class="nowrap">${fmtShort(e.date)}</td><td class="nowrap"><span class="dot" style="background:${SEV_COLORS[e.severity]}"></span> ${esc(sevName(e.severity))}</td>
          <td>${esc(e.title)}${e.verified ? ` <span class="tag">✔ ${L('Vérifié Angor', 'Angor verified')}</span>` : ''}<br><span class="small">${esc(catName(e.category))}${e._d != null ? ` · ${Math.round(e._d)} km` : ''}</span></td><td class="small">${esc(e.place || '')}</td><td class="mono small">${esc(e.admiralty || '')}</td></tr>`).join('')}</tbody></table>
        <p class="hint">${L('Incidents de confiance moyenne ou haute. Cotation de l\'Amirauté : lettre = fiabilité de la source (A à F), chiffre = crédibilité de l\'information (1 à 6).', 'Medium or high confidence incidents. Admiralty rating: letter = source reliability (A–F), digit = information credibility (1–6).')}</p>`
        : `<p>${L('Aucun incident fiable recensé sur la période dans cette zone.', 'No reliable incident recorded in this area over the period.')}</p><p class="hint">${L('L\'absence d\'incident dans nos sources ne garantit pas l\'absence de risque.', 'No incident in our sources does not mean no risk.')}</p>`}

      <h2>${icon('clipboard-check', 18)} 3. ${L('Mesures de sûreté', 'Security measures')}</h2>
      <div class="measures">${meas.map(m => `<div class="mcard"><h3>${esc(m.title)}</h3><ul class="check">${m.items.map(i => `<li><span class="box"></span>${esc(i)}</li>`).join('')}</ul></div>`).join('')}</div>
    </section>

    <section class="page">
      <h2>${icon('heart-pulse', 18)} 4. ${L('Santé, urgences et appuis', 'Health, emergency and support')}</h2>
      ${meae && (meae.health || []).length ? `<blockquote class="quote">${meae.health.slice(0, 4).map(q => `<p>« ${esc(q)} »</p>`).join('')}<footer>${L('MEAE – rubrique Santé.', 'French MFA – health section.')}</footer></blockquote>` : `<p class="small">${L('Vaccins et prévention : consulter un centre de vaccinations internationales.', 'Vaccines and prevention: consult a travel clinic.')}</p>`}
      <div class="cols">
        <dl class="kv"><dt>${L('Urgences', 'Emergency')}</dt><dd>${esc((x.emergency || []).join(' · ') || '—')}</dd>
          <dt>${L('Indicatif', 'Calling code')}</dt><dd>${esc((x.calling_code || []).map(c => c.startsWith('+') ? c : '+' + c).join(', ') || '—')}</dd>
          <dt>${L('Prises / tension', 'Plugs / voltage')}</dt><dd>${esc((x.plugs || []).join(', ') || '—')}${(x.voltage || []).length ? ' · ' + esc(x.voltage.join('/')) + ' V' : ''}</dd>
          <dt>${L('Opérateurs', 'Operators')}</dt><dd>${esc((x.operators || []).slice(0, 4).join(', ') || '—')}</dd></dl>
        <dl class="kv"><dt>${L('Ambassade / consulat', 'Embassy / consulate')}</dt><dd class="fill-line"></dd>
          <dt>${L('Assisteur (24/7)', 'Assistance (24/7)')}</dt><dd class="fill-line"></dd>
          <dt>${L('Contact local', 'Local contact')}</dt><dd class="fill-line"></dd>
          <dt>${L('Cellule de crise', 'Crisis cell')}</dt><dd class="fill-line"></dd></dl>
      </div>
      ${hospitals.length ? `<h3>${L('Établissements de santé', 'Hospitals')}${hosp.length && pt ? ' – ' + esc(pt.name) : ''}</h3><table class="list"><tbody>${hospitals.map(h => `<tr><td><strong>${esc(h.name)}</strong></td><td class="small">${esc(h.city || '')}</td><td class="small">${h.web ? `<a href="${esc(h.web)}">${esc(h.web.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, ''))}</a>` : ''}</td></tr>`).join('')}</tbody></table>
        <p class="hint">${L('Wikidata, liste non agréée : à valider avec l\'assisteur.', 'Wikidata, not an approved list: validate with your assistance provider.')}</p>` : ''}
      ${(r && r.level >= 3) || f.profile === 'exec' ? `<h3>${L('Prestataires de sécurité et d\'assistance', 'Security and assistance providers')}</h3><p class="small">${provs.map(pv => `<strong>${esc(pv.name)}</strong>${pv.web ? ` (${esc(pv.web.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, ''))})` : ''}`).join(' · ')}</p>` : ''}
      ${(g.tenue || g.interdits || g.voyageuses) ? `<h2>${icon('users', 18)} 5. ${L('Usages à respecter', 'Customs to respect')}</h2>
        <div class="measures">${[['tenue', L('Tenue', 'Dress')], ['interdits', L('Interdits et sujets sensibles', 'Red lines')], ['affaires', L('Affaires', 'Business')], ...(f.profile === 'woman' ? [['voyageuses', L('Voyageuses', 'Women travellers')]] : [])]
          .filter(([k]) => (g[k] || []).length).map(([k, lab]) => `<div class="mcard"><h3>${esc(lab)}</h3><ul>${g[k].slice(0, 4).map(i => `<li>${esc(i)}</li>`).join('')}</ul></div>`).join('')}</div>` : ''}
    </section>

    <section class="page trace">
      <h2>${icon('file-text', 18)} 6. ${L('Traçabilité et validation (duty of care)', 'Traceability and sign-off (duty of care)')}</h2>
      <p>${L(`Ce brief a été établi le ${now.toLocaleDateString('fr-FR')} à ${now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })} pour une mission à destination de ${name}${f.city ? ` (${f.city})` : ''}. Il résume l'information disponible à cette date et la recommandation qui en découle. Il doit être relu avant le départ si la situation évolue (alerte Angor, changement d'avis officiel).`,
        `This brief was produced on ${now.toLocaleDateString('en-GB')} at ${now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} for a mission to ${name}${f.city ? ` (${f.city})` : ''}. It summarises the information available at that date and the resulting recommendation. Review it before departure if the situation changes (Angor alert, change of official advice).`)}</p>
      <h3>${L('Sources consultées', 'Sources consulted')}</h3>
      <ol class="small sources">${sources.map(([n, u]) => `<li>${esc(n)}${u ? ` – <a href="${esc(u)}">${esc(u.replace(/^https?:\/\//, ''))}</a>` : ''}</li>`).join('')}</ol>
      <div class="signs">
        ${[L('Voyageur – a pris connaissance du brief', 'Traveller – has read the brief'), L('Manager – valide le déplacement', 'Manager – approves the trip'), L('Responsable sûreté – avis', 'Security manager – opinion')]
          .map(s => `<div class="sign"><div class="st">${esc(s)}</div><div class="sl">${L('Nom', 'Name')} :</div><div class="sl">${L('Date', 'Date')} :</div><div class="sl">${L('Signature', 'Signature')} :</div></div>`).join('')}
      </div>
      <p class="hint">${L('Outil d\'aide à la décision : informations issues de sources ouvertes, non exhaustives, à vérifier. La recommandation est indicative et ne remplace pas l\'appréciation de la fonction sûreté ni les consignes officielles. Référence', 'Decision-support tool: open-source information, not exhaustive, to be verified. The recommendation is indicative and does not replace the security function\'s judgement or official guidance. Reference')} ${esc(ref)}.</p>
    </section>`;
  }

  /* ------------------------------------------------ formulaire */
  function fillForm() {
    $$('[data-l]').forEach(el => { el.textContent = L(...T[el.dataset.l]); });
    $('#tb-back').innerHTML = icon('arrow-left') + ' ' + L('Carte', 'Map');
    $('#tb-print').innerHTML = icon('printer') + ' ' + L('Imprimer / PDF', 'Print / PDF');
    $('#tb-lang').textContent = lang === 'fr' ? 'EN' : 'FR';
    document.documentElement.lang = lang;
    const sel = $('#f-country'), cur = sel.value;
    sel.innerHTML = COUNTRIES.slice().sort((a, b) => a['name_' + lang].localeCompare(b['name_' + lang]))
      .map(c => `<option value="${c.iso2}">${esc(c['name_' + lang])}${RISK[c.iso2] ? ` (${RISK[c.iso2].level})` : ''}</option>`).join('');
    if (cur) sel.value = cur;
    const ps = $('#f-profile'), pcur = ps.value;
    ps.innerHTML = Object.entries(PROFILES).map(([k, v]) => `<option value="${k}">${esc(L(...v))}</option>`).join('');
    if (pcur) ps.value = pcur;
  }
  function cityList() {
    const iso = $('#f-country').value;
    $('#city-list').innerHTML = CITIES.filter(c => c[1] === iso).slice(0, 60).map(c => `<option value="${esc(c[0])}">`).join('');
  }
  const GNG_ANS = (q => q && window.AngorGNG ? window.AngorGNG.decode(q) : null)(new URLSearchParams(location.search).get('g'));
  function saveState() {
    const f = read();
    try { localStorage.setItem('vs-brief', JSON.stringify({ profile: f.profile, issuer: f.issuer })); } catch (e) { /* */ }
    const q = new URLSearchParams({ c: f.iso });
    ['city', 'from', 'to', 'profile'].forEach(k => { if (f[k]) q.set(k === 'profile' ? 'p' : k, f[k]); });
    if (f.pax > 1) q.set('pax', f.pax);
    const g0 = new URLSearchParams(location.search).get('g'); if (g0) q.set('g', g0);
    history.replaceState(null, '', '?' + q.toString());
  }
  function init() {
    fillForm();
    const q = new URLSearchParams(location.search);
    const [hIso, hCity] = decodeURIComponent(location.hash.slice(1)).split('|');
    let saved = {};
    try { saved = JSON.parse(localStorage.getItem('vs-brief')) || {}; } catch (e) { /* */ }
    const iso = (q.get('c') || hIso || 'FR').toUpperCase();
    $('#f-country').value = COUNTRIES.some(c => c.iso2 === iso) ? iso : 'FR';
    $('#f-city').value = q.get('city') || hCity || '';
    const d0 = new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10), d1 = new Date(Date.now() + 11 * 864e5).toISOString().slice(0, 10);
    $('#f-from').value = q.get('from') || d0; $('#f-to').value = q.get('to') || d1;
    $('#f-profile').value = PROFILES[q.get('p')] ? q.get('p') : (PROFILES[saved.profile] ? saved.profile : 'biz');
    $('#f-pax').value = q.get('pax') || 1;
    $('#f-issuer').value = saved.issuer || '';
    if (location.hash) history.replaceState(null, '', location.pathname + location.search);
    cityList(); render(); saveState();
    const ai = (D.settings || {}).ai_url || (D.settings || {}).buddy_url;
    if (ai) {
      const b = document.createElement('button'); b.className = 'tb-btn'; b.id = 'tb-ai'; b.textContent = L('Synthèse IA', 'AI summary');
      $('#tb-print').before(b);
      b.addEventListener('click', async () => {
        const f = read(); b.disabled = true; b.textContent = L('Rédaction…', 'Writing…');
        const text = $('#report').innerText.slice(0, 12000);
        try {
          const r = await fetch(ai, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task: 'brief', lang,
            q: L(`Synthèse du brief : ${cname(f.iso)}${f.city ? ' (' + f.city + ')' : ''}, du ${f.from} au ${f.to}, profil ${f.profile}.`, `Brief summary: ${cname(f.iso)}${f.city ? ' (' + f.city + ')' : ''}, ${f.from} to ${f.to}, profile ${f.profile}.`), context: text }) });
          const j = await r.json(); if (!r.ok || !j.answer) throw new Error(j.error || r.status);
          window._briefAi = j.answer; render();
          b.textContent = L('Synthèse IA', 'AI summary');
        } catch (e) { b.textContent = L('IA indisponible', 'AI unavailable'); }
        b.disabled = false;
      });
    }
  }
  $('#brief-form').addEventListener('input', ev => { if (ev.target.id === 'f-country') { $('#f-city').value = ''; cityList(); } render(); saveState(); });
  $('#brief-form').addEventListener('submit', ev => ev.preventDefault());
  $('#tb-print').addEventListener('click', () => window.print());
  $('#tb-lang').addEventListener('click', () => { lang = lang === 'fr' ? 'en' : 'fr'; try { localStorage.setItem('vs-lang', JSON.stringify(lang)); } catch (e) { /* */ } fillForm(); render(); });
  init();
})();
