/* Angor Intelligence – annuaire des prestataires : fonctions communes à la carte (fiche pays), au rapport pays et à
   l'espace prestataire (prestataire.html). Données : window.VS_PROVIDERS (docs/data/providers.js, écrit par le robot
   à partir de config/providers.json, config/providers_directory.json et des fiches inscrites dans Supabase).
   La grille de qualité (score) est la MÊME que celle de la base (private.provider_score dans supabase/schema.sql) :
   la base fait foi, cette copie sert à montrer au prestataire, en direct, ce qu'il lui reste à compléter. */
(function () {
  'use strict';
  const TIER_ORDER = { A: 0, B: 1, C: 2, D: 3, E: 4 };
  const TIER_DEFAULT = {
    A: { fr: 'Vérifié par Angor – dossier complet', en: 'Verified by Angor – complete file', color: '#1a9850' },
    B: { fr: 'Vérifié par Angor', en: 'Verified by Angor', color: '#91cf60' },
    C: { fr: 'Inscrit – dossier complet, non vérifié', en: 'Registered – complete file, not verified', color: '#d9c84a' },
    D: { fr: 'Inscrit – dossier incomplet', en: 'Registered – incomplete file', color: '#fc8d59' },
    E: { fr: 'Non vérifié – à contacter séparément', en: 'Unverified – to be contacted separately', color: '#d73027' },
  };
  const data = () => window.VS_PROVIDERS || { categories: {}, groups: {}, tiers: TIER_DEFAULT, providers: [], registered: [], local: {} };
  const tiers = () => Object.assign({}, TIER_DEFAULT, data().tiers || {});
  const regionOf = p => {
    if (!p) return '';
    if (p.region === 'Western Asia') return 'Moyen-Orient';
    return { Africa: 'Afrique', Europe: 'Europe', Asia: 'Asie', 'North America': 'Amériques', 'South America': 'Amériques', Oceania: 'Océanie' }[p.continent] || '';
  };
  const norm = (p, extra) => Object.assign({ name: p.name, web: p.web || '', hq: p.hq || '', note: p.note || '', id: p.id || null,
    categories: p.categories || p.services || [], tier: p.tier || 'E', score: p.score || 0, source: p.source || 'angor', linkedin: p.linkedin || '' }, extra || {});
  const sort = list => list.sort((a, b) => (TIER_ORDER[a.tier] ?? 9) - (TIER_ORDER[b.tier] ?? 9) || b.score - a.score || a.name.localeCompare(b.name));

  /** Prestataires couvrant un pays : inscrits (pays déclarés), locaux repérés, internationaux de la région. */
  function forCountry(iso, countryProps) {
    const D = data(), region = regionOf(countryProps);
    const reg = (D.registered || []).filter(p => (p.countries || []).includes(iso)).map(p => norm(p, { source: 'self' }));
    const loc = ((D.local || {})[iso] || []).map(p => norm(p, { local: true }));
    const intl = (D.providers || []).filter(p => !region || (p.regions || []).includes(region)).map(p => norm(p));
    return sort(reg.concat(loc, intl));
  }
  /** {catégorie: {n, best}} – best = niveau le plus fiable disponible dans la catégorie. */
  function byCategory(list) {
    const out = {};
    for (const p of list) for (const c of p.categories) {
      const o = out[c] || (out[c] = { n: 0, best: 'E', tiers: {} });
      o.n += 1; o.tiers[p.tier] = (o.tiers[p.tier] || 0) + 1;
      if ((TIER_ORDER[p.tier] ?? 9) < (TIER_ORDER[o.best] ?? 9)) o.best = p.tier;
    }
    return out;
  }
  const catLabel = (c, lang) => ((data().categories || {})[c] || {})[lang || 'fr'] || c;
  const tierLabel = (t, lang) => (tiers()[t] || {})[lang || 'fr'] || t;
  const tierColor = t => (tiers()[t] || {}).color || '#888';
  const link = p => (p.source === 'self' && p.id ? 'prestataire.html?id=' + encodeURIComponent(p.id) : p.web);

  /* Justificatifs : envoyés en privé (compartiment « provider-docs »), visibles du prestataire et d'Angor uniquement.
     pts = points du score quand le document est envoyé, non refusé et non expiré (null = accepté mais hors score). */
  const DOC_KINDS = {
    registration: { key: 'doc_reg', fr: 'Registre du commerce / extrait d\'immatriculation (Kbis…)', en: 'Company registration extract',
      hint: 'Extrait de moins de 3 mois (Kbis, Companies House, registre local).' },
    licence: { key: 'doc_lic', fr: 'Licence ou autorisation professionnelle', en: 'Professional licence or authorisation',
      hint: 'Ex. autorisation CNAPS, certificat de transporteur aérien (AOC), licence VTC / taxi, agrément sanitaire.' },
    insurance: { key: 'doc_ins', fr: 'Attestation d\'assurance responsabilité civile professionnelle', en: 'Professional liability insurance certificate',
      hint: 'Indiquez la date de fin de validité : elle est obligatoire pour ce document.', expiry: true },
    certification: { key: 'doc_cert', fr: 'Certification / norme (ISO 9001, ISO 18788, ISO 27001, ICoCA…)', en: 'Certification / standard (ISO…)',
      hint: 'Certificat en cours de validité, avec son périmètre.' },
    cv: { key: 'doc_cv', fr: 'CV et qualifications des dirigeants ou équipes clés', en: 'CVs and qualifications of key staff',
      hint: 'Informations professionnelles uniquement (expérience, diplômes, habilitations) : sans photo, adresse personnelle, date de naissance ni n° de sécurité sociale. Informez les personnes concernées.' },
    tax: { key: null, fr: 'Attestation de régularité fiscale ou sociale (URSSAF…)', en: 'Tax / social security compliance certificate', hint: '' },
    other: { key: null, fr: 'Autre justificatif', en: 'Other document', hint: '' },
  };
  /** Un justificatif compte s'il n'est pas refusé et pas expiré ; l'attestation d'assurance doit avoir une date de fin. */
  const docActive = (d, today) => d && d.status !== 'rejected' && (d.expires_on ? d.expires_on >= today : !(DOC_KINDS[d.kind] || {}).expiry);

  /* Grille de qualité – POIDS: ident=10 desc=5 scope=5 contact=10 pricing=5 media=5 links=5 doc_reg=15 doc_lic=10 doc_ins=10 doc_cert=5 doc_cv=5 docs_ok=10 */
  const filled = v => v != null && String(v).trim() !== '';
  const arr = v => (Array.isArray(v) ? v : []);
  function score(p, docs) {
    p = p || {}; docs = docs || [];
    const c = p.contacts || {}, today = new Date().toISOString().slice(0, 10);
    const act = docs.filter(d => docActive(d, today));
    const has = k => act.some(d => d.kind === k);
    const valid = act.filter(d => d.status === 'validated');
    const items = [
      ['ident', 10, filled(p.legal_name) && filled(p.registration_no) && filled(p.hq_country), 'Raison sociale, n° d\'immatriculation et pays du siège', 'Legal name, registration number and HQ country'],
      ['desc', 5, Math.max((p.description_fr || '').length, (p.description_en || '').length) >= 200, 'Présentation d\'au moins 200 caractères', 'Description of at least 200 characters'],
      ['scope', 5, arr(p.categories).length >= 1 && arr(p.countries).length >= 1, 'Au moins une catégorie et un pays couvert', 'At least one category and one country covered'],
      ['contact', 10, filled(c.phone_247) && (filled(c.email_ops) || filled(c.email_booking)), 'Téléphone 24/7 et e-mail opérationnel', '24/7 phone and operations e-mail'],
      ['pricing', 5, arr(p.pricing).some(x => filled(x && x.price)), 'Au moins un tarif fixe publié', 'At least one fixed price published'],
      ['media', 5, arr(p.media).length >= 1, 'Au moins une photo ou vidéo', 'At least one photo or video'],
      ['links', 5, filled(p.website) || filled(p.linkedin), 'Site web ou page LinkedIn', 'Website or LinkedIn page'],
      ['doc_reg', 15, has('registration'), 'Justificatif : ' + DOC_KINDS.registration.fr, 'Document: ' + DOC_KINDS.registration.en],
      ['doc_lic', 10, has('licence'), 'Justificatif : ' + DOC_KINDS.licence.fr, 'Document: ' + DOC_KINDS.licence.en],
      ['doc_ins', 10, has('insurance'), 'Justificatif : Attestation d\'assurance RC pro en cours de validité', 'Document: valid liability insurance certificate'],
      ['doc_cert', 5, has('certification'), 'Justificatif : ' + DOC_KINDS.certification.fr, 'Document: ' + DOC_KINDS.certification.en],
      ['doc_cv', 5, has('cv'), 'Justificatif : ' + DOC_KINDS.cv.fr, 'Document: ' + DOC_KINDS.cv.en],
      ['docs_ok', 10, valid.some(d => d.kind === 'registration') && valid.length >= 2, 'Au moins 2 justificatifs validés par Angor, dont l\'immatriculation', 'At least 2 documents validated by Angor, including registration'],
    ].map(([key, pts, ok, fr, en]) => ({ key, pts, ok: !!ok, fr, en, doc: key.startsWith('doc') }));
    return { score: items.reduce((s, i) => s + (i.ok ? i.pts : 0), 0), items };
  }
  /** Conditions de soumission (immatriculation envoyée) et de vérification (immatriculation validée), comme dans la base. */
  const canSubmit = docs => (docs || []).some(d => d.kind === 'registration' && docActive(d, new Date().toISOString().slice(0, 10)));
  const canVerify = docs => (docs || []).some(d => d.kind === 'registration' && d.status === 'validated' && docActive(d, new Date().toISOString().slice(0, 10)));
  /** Même règle que la base : A/B vérifié (A si score ≥ 80), C soumis ≥ 60, D sinon. */
  const tierOf = (status, s) => (status === 'verified' ? (s >= 80 ? 'A' : 'B') : status === 'submitted' && s >= 60 ? 'C' : 'D');

  window.AngorProviders = { data, forCountry, byCategory, catLabel, tierLabel, tierColor, tiers, link, score, tierOf, regionOf, TIER_ORDER, DOC_KINDS, docActive, canSubmit, canVerify };
})();
