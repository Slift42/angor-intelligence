/* Angor Intelligence – moteur go/no-go guidé (partagé par la carte et le brief de mission).
   Menace (M, 1 à 5) calculée à partir des données Angor ; vulnérabilité (V, 1 à 5) à partir du questionnaire.
   Risque résiduel = M × V (1 à 25) → décision, modulée par la criticité de la mission.
   Tout est calculé dans le navigateur ; rien n'est envoyé. */
(function () {
  'use strict';
  const L = (lang, fr, en) => lang === 'fr' ? fr : en;
  const Q = [
    { id: 'crit', fr: 'Criticité de la mission', en: 'Mission criticality', opts: [
      ['vital', 'Vitale (sécurité des personnes, continuité essentielle)', 'Vital (people safety, essential continuity)'],
      ['important', 'Importante (enjeu commercial ou opérationnel fort)', 'Important (strong business or operational stake)'],
      ['defer', 'Reportable ou faisable à distance', 'Can be postponed or done remotely']] },
    { id: 'profile', fr: 'Profil du voyageur', en: 'Traveller profile', opts: [
      ['biz', 'Voyageur d\'affaires', 'Business traveller'], ['team', 'Équipe technique / chantier', 'Technical / site team'],
      ['exec', 'Dirigeant / personnalité exposée', 'Executive / high-profile'], ['woman', 'Voyageuse', 'Woman traveller'],
      ['long', 'Séjour long / expatriation', 'Long stay / expatriation']] },
    { id: 'exp', fr: 'Expérience du pays ou de zones comparables', en: 'Experience of the country or similar areas', opts: [
      ['none', 'Aucune (premier séjour)', 'None (first visit)'], ['some', 'Quelques séjours', 'A few trips'], ['high', 'Habitué', 'Seasoned']] },
    { id: 'support', fr: 'Appui sur place', en: 'Support in country', opts: [
      ['none', 'Aucun', 'None'], ['partner', 'Partenaire ou client qui accueille', 'Host partner or client'],
      ['security', 'Prestataire sûreté / accueil sécurisé', 'Security provider / secure meet-and-greet']] },
    { id: 'transport', fr: 'Transport sur place', en: 'Ground transport', opts: [
      ['driver', 'Véhicule avec chauffeur de confiance (réservé)', 'Pre-booked trusted driver'],
      ['taxi', 'Taxi officiel / VTC', 'Official taxi / ride-hailing'], ['self', 'Conduite personnelle (location)', 'Self-drive (rental)'],
      ['public', 'Transports publics', 'Public transport']] },
    { id: 'night', fr: 'Déplacements de nuit ou hors des villes', en: 'Night travel or travel outside cities', opts: [
      ['no', 'Non', 'No'], ['city', 'Oui, en ville', 'Yes, in town'], ['rural', 'Oui, hors des villes', 'Yes, outside cities']] },
    { id: 'lodging', fr: 'Hébergement', en: 'Accommodation', opts: [
      ['vetted', 'Hôtel évalué (sûreté vérifiée)', 'Vetted hotel (security checked)'], ['hotel', 'Hôtel non évalué', 'Non-vetted hotel'],
      ['private', 'Location, chez l\'habitant', 'Rental, private home']] },
    { id: 'insurance', fr: 'Assurance-assistance (médical, rapatriement)', en: 'Assistance insurance (medical, repatriation)', opts: [
      ['yes', 'Oui, numéro 24/7 connu', 'Yes, 24/7 number known'], ['no', 'Non ou à vérifier', 'No or to be checked']] },
    { id: 'comms', fr: 'Communications et suivi', en: 'Communications and tracking', opts: [
      ['full', 'Téléphone local + points de contact planifiés (+ satellite si besoin)', 'Local phone + scheduled check-ins (+ satphone if needed)'],
      ['phone', 'Téléphone seulement', 'Phone only'], ['none', 'Pas de plan', 'No plan']] },
    { id: 'training', fr: 'Préparation sûreté', en: 'Security preparation', opts: [
      ['heat', 'Formation HEAT / environnement hostile', 'HEAT / hostile-environment training'], ['brief', 'Briefing sûreté avant départ', 'Pre-departure security briefing'],
      ['none', 'Aucune', 'None']] },
  ];
  const DEFAULTS = { crit: 'important', profile: 'biz', exp: 'some', support: 'partner', transport: 'driver', night: 'no', lodging: 'vetted', insurance: 'yes', comms: 'full', training: 'brief' };

  function hav(a, b, c, d) { const R = 6371, r = Math.PI / 180, x = Math.sin((c - a) * r / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin((d - b) * r / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(x)); }

  /** Menace de la destination (1 à 5) et facteurs expliqués, à partir des données Angor. */
  function threat(opt) {
    const { iso, point, from, to, lang = 'fr' } = opt;
    const D = window.VS_DATA || {};
    const r = (D.countries || {})[iso] || {}, adv = r.advisories || {};
    const p = (D.pulse || {})[iso];
    const factors = [];
    let T = r.level || 2;
    factors.push(L(lang, `Risque pays Angor ${r.level || '?'}/5`, `Angor country risk ${r.level || '?'}/5`));
    const meae = adv['MEAE (France)'];
    if (meae) {
      const whole = meae.parts ? Math.max(1, (meae.max || meae.level) - 1) : (meae.max || meae.level);
      const m = { 1: 1, 2: 2, 3: 4, 4: 5 }[whole] || 2;
      if (m > T) T = m;
      factors.push(L(lang, `MEAE : ${meae.label}`, `French MFA: ${meae.label}`));
    }
    const us = adv['US State Dept'];
    if (us && us.level >= 4 && T < 4) { T = 4; factors.push(L(lang, 'US State Dept : Do not travel', 'US State Dept: Do not travel')); }
    if (p && p.value < 35) { T += 1; factors.push(L(lang, `Pulse très bas (${p.value}/100)`, `Very low Pulse (${p.value}/100)`)); }
    else if (p && p.d7 != null && p.d7 <= -10) { T += 1; factors.push(L(lang, `Pulse en forte baisse (${p.d7} en 7 j)`, `Pulse falling sharply (${p.d7} in 7 d)`)); }
    let near = [];
    if (point) {
      near = (D.events || []).filter(e => e.lat != null && Date.now() - Date.parse(e.date) < 7 * 864e5 && e.severity >= 3 && e.confidence !== 'low' && hav(point.lat, point.lon, e.lat, e.lon) <= 100);
      if (near.length >= 3) { T += 1; factors.push(L(lang, `${near.length} incidents graves à moins de 100 km en 7 j`, `${near.length} serious incidents within 100 km in 7 d`)); }
      else if (near.length) factors.push(L(lang, `${near.length} incident(s) grave(s) à moins de 100 km en 7 j`, `${near.length} serious incident(s) within 100 km in 7 d`));
    }
    const crises = (D.crises || []).filter(c => c.country === iso && c.status === 'active' && (c.trend === 'escalating' || c.trend === 'new') && c.max_severity >= 3);
    if (crises.length) factors.push(L(lang, `Crise en cours : ${crises[0].title}`, `Ongoing crisis: ${crises[0].title_en || crises[0].title}`));
    const cal = ((window.VS_CALENDAR || {}).events || []).filter(e => (e.iso === iso) && e.type === 'election' && e.prec !== 'year' && from && to
      && e.d >= addDays(from, -3) && e.d <= addDays(to, 3));
    if (cal.length) { if ((r.level || 0) >= 3) T += 1; factors.push(L(lang, `Élection pendant le séjour : ${cal[0].t_fr}`, `Election during the stay: ${cal[0].t_en}`)); }
    return { T: Math.max(1, Math.min(5, T)), factors, near: near.length, crises, calendar: cal };
  }
  function addDays(d, n) { const x = new Date(d + 'T12:00:00Z'); x.setUTCDate(x.getUTCDate() + n); return x.toISOString().slice(0, 10); }

  /** Vulnérabilité (1 à 5), conditions à remplir, décision. */
  function evaluate(ans, th, lang = 'fr') {
    const a = Object.assign({}, DEFAULTS, ans || {});
    const T = th.T;
    let v = 0;
    const cond = [];
    const need = (pts, fr, en) => { v += pts; cond.push(L(lang, fr, en)); };
    if (a.profile === 'exec') v += 1;
    if (a.profile === 'woman' && T >= 3) v += 0.5;
    if (a.exp === 'none') need(T >= 3 ? 1 : 0.5, 'Premier séjour : briefing approfondi et accueil par un correspondant local', 'First visit: in-depth briefing and meet-and-greet by a local contact');
    if (a.support === 'none' && T >= 3) need(1, 'Prévoir un appui sur place (partenaire, prestataire sûreté)', 'Arrange in-country support (partner, security provider)');
    if (a.transport === 'self' && T >= 3) need(1.5, 'Remplacer la conduite personnelle par un chauffeur de confiance', 'Replace self-drive with a trusted driver');
    else if (a.transport === 'public' && T >= 2) need(T >= 3 ? 1.5 : 0.5, 'Éviter les transports publics : chauffeur réservé', 'Avoid public transport: pre-booked driver');
    else if (a.transport === 'taxi' && T >= 3) need(0.5, 'Chauffeur réservé à l\'avance plutôt que taxi', 'Pre-booked driver rather than taxis');
    if (a.night === 'rural') need(T >= 3 ? 1.5 : 0.5, 'Supprimer les trajets de nuit hors des villes', 'Cancel night travel outside cities');
    else if (a.night === 'city' && T >= 3) need(0.5, 'Limiter les déplacements de nuit, toujours avec chauffeur', 'Limit night movement, always with a driver');
    if (a.lodging === 'private' && T >= 3) need(1, 'Hôtel évalué (contrôle d\'accès) plutôt que location', 'Vetted hotel (access control) rather than a rental');
    else if (a.lodging === 'hotel' && T >= 3) need(0.5, 'Faire évaluer l\'hôtel (sûreté, étages, accès)', 'Have the hotel security-vetted');
    if (a.insurance === 'no') need(1.5, 'Souscrire / vérifier l\'assurance-assistance et le rapatriement', 'Take out / check assistance and repatriation insurance');
    if (a.comms === 'none') need(1, 'Mettre en place des points de contact planifiés', 'Set up scheduled check-ins');
    else if (a.comms === 'phone' && T >= 4) need(0.5, 'Points de contact planifiés et téléphone satellite', 'Scheduled check-ins and a satellite phone');
    if (a.training === 'none' && T >= 3) need(T >= 4 ? 1.5 : 0.5, T >= 4 ? 'Formation HEAT avant départ' : 'Briefing sûreté avant départ', T >= 4 ? 'HEAT training before departure' : 'Pre-departure security briefing');
    else if (a.training === 'brief' && T >= 5) need(1, 'Formation HEAT avant départ', 'HEAT training before departure');
    const V = Math.max(1, Math.min(5, Math.round(1 + v)));
    const R = T * V;
    let code = R <= 6 ? 'go' : R <= 12 ? 'conditions' : R <= 16 ? 'escalate' : 'nogo';
    if (T >= 5 && code !== 'nogo') code = 'escalate';
    if (T >= 5 && V >= 3) code = 'nogo';
    let note = '';
    if (a.crit === 'defer' && (code === 'escalate' || code === 'nogo')) { code = 'nogo'; note = L(lang, 'Mission reportable : la reporter ou la mener à distance.', 'Mission can be postponed: postpone it or run it remotely.'); }
    if (a.crit === 'vital' && code === 'nogo' && T < 5) { code = 'escalate'; note = L(lang, 'Mission vitale : possible uniquement avec toutes les conditions et validation de la direction.', 'Vital mission: only with all conditions met and executive approval.'); }
    const LBL = { go: [L(lang, 'GO – mesures standard', 'GO – standard measures'), '#2E9E5B'],
      conditions: [L(lang, 'GO sous conditions', 'GO with conditions'), '#E3B505'],
      escalate: [L(lang, 'Escalade : décision de la direction sûreté', 'Escalate: security management decision'), '#EE7D22'],
      nogo: [L(lang, 'NO-GO', 'NO-GO'), '#D7263D'] };
    return { T, V, R, code, label: LBL[code][0], color: LBL[code][1], conditions: cond, note, answers: a };
  }

  /** Matrice 5 × 5 (SVG) : menace en abscisse, vulnérabilité en ordonnée, case courante entourée. */
  function matrix(T, V, lang = 'fr', size = 190) {
    const c = size / 6, cells = [];
    const col = r => r <= 6 ? '#2E9E5B' : r <= 12 ? '#E3B505' : r <= 16 ? '#EE7D22' : '#D7263D';
    for (let v = 1; v <= 5; v++) for (let t = 1; t <= 5; t++) {
      const x = c * t, y = c * (5 - v);
      cells.push(`<rect x="${x}" y="${y}" width="${c - 2}" height="${c - 2}" rx="3" fill="${col(t * v)}" opacity="${t === T && v === V ? 1 : 0.35}"/>`);
      if (t === T && v === V) cells.push(`<rect x="${x - 1.5}" y="${y - 1.5}" width="${c + 1}" height="${c + 1}" rx="4" fill="none" stroke="#111B27" stroke-width="2.5"/>`);
    }
    const lab = [];
    for (let i = 1; i <= 5; i++) {
      lab.push(`<text x="${c * i + c / 2 - 1}" y="${c * 5 + 14}" font-size="10" text-anchor="middle" fill="currentColor">${i}</text>`);
      lab.push(`<text x="${c - 8}" y="${c * (5 - i) + c / 2 + 3}" font-size="10" text-anchor="end" fill="currentColor">${i}</text>`);
    }
    lab.push(`<text x="${c * 3.5}" y="${c * 5 + 28}" font-size="10.5" text-anchor="middle" fill="currentColor">${L(lang, 'Menace', 'Threat')} →</text>`);
    lab.push(`<text x="10" y="${c * 2.5}" font-size="10.5" text-anchor="middle" fill="currentColor" transform="rotate(-90 10 ${c * 2.5})">${L(lang, 'Vulnérabilité', 'Vulnerability')} →</text>`);
    return `<svg class="gng-matrix" viewBox="0 0 ${size} ${c * 5 + 34}" width="${size}" role="img" aria-label="${L(lang, 'Matrice menace × vulnérabilité', 'Threat × vulnerability matrix')}">${cells.join('')}${lab.join('')}</svg>`;
  }
  const encode = a => btoa(unescape(encodeURIComponent(JSON.stringify(a)))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const decode = s => { try { return JSON.parse(decodeURIComponent(escape(atob(s.replace(/-/g, '+').replace(/_/g, '/'))))); } catch (e) { return null; } };
  window.AngorGNG = { QUESTIONS: Q, DEFAULTS, threat, evaluate, matrix, encode, decode };
})();
