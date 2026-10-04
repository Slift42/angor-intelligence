/* Angor Intelligence – espace prestataire (prestataire.html).
   - sans paramètre : le prestataire connecté remplit sa fiche d'identification et de services (score de qualité en direct,
     justificatifs privés, photos, tarifs, garanties), la soumet à l'annuaire, consulte les demandes et avis reçus ;
   - ?id=<fiche> : fiche publique d'un prestataire pour les comptes validés (contacts, tarifs, garanties, avis, demande
     de devis) ; l'administrateur y trouve aussi les boutons de vérification.
   Données : Supabase (tables providers, provider_documents, provider_reviews, provider_requests ; voir supabase/schema.sql).
   Grille de qualité et niveaux : docs/providers-lib.js (la base recalcule et fait foi). */
(function () {
  'use strict';
  const A = window.AngorAccount, AP = window.AngorProviders;
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  try { const th = JSON.parse(localStorage.getItem('vs-theme')); if (th) document.documentElement.dataset.theme = th; } catch (e) { /* */ }
  const COUNTRIES = ((window.VS_COUNTRIES || {}).features || []).map(f => f.properties).sort((a, b) => a.name_fr.localeCompare(b.name_fr));
  const cname = iso => (COUNTRIES.find(c => c.iso2 === iso) || {}).name_fr || iso;
  const countryOpts = (sel, empty) => (empty ? `<option value="">${esc(empty)}</option>` : '') + COUNTRIES.map(c => `<option value="${c.iso2}"${c.iso2 === sel ? ' selected' : ''}>${esc(c.name_fr)}</option>`).join('');
  const CATS = (AP && AP.data().categories) || {}, GROUPS = (AP && AP.data().groups) || {};
  const main = $('#main');
  const ID = new URLSearchParams(location.search).get('id');
  const STATUS = { draft: ['Brouillon – invisible', 'pending'], submitted: ['Publiée dans l\'annuaire', 'approved'], verified: ['Vérifiée par Angor', 'approved'], suspended: ['Suspendue', 'suspended'] };
  const DOC_KINDS = (AP && AP.DOC_KINDS) || {};
  const docLabel = k => (DOC_KINDS[k] || {}).fr || k;
  const UNITS = ['heure', 'demi-journée', 'jour', 'nuit', 'trajet', 'personne', 'forfait'];
  const CURRENCIES = ['EUR', 'USD', 'GBP', 'CHF', 'AED', 'XOF', 'XAF', 'autre'];
  const fmtDate = d => d ? new Date(d).toLocaleDateString('fr-FR') : '';
  let me = null, P = null, docs = [], reviews = [], requests = [];

  function msg(el, text, kind) { if (el) el.innerHTML = text ? `<div class="msg ${kind || 'err'}">${esc(text)}</div>` : ''; }
  const tierBadge = (tier, score) => `<span class="pv-badge" style="--pv:${AP.tierColor(tier)}"><span class="pv-dot"></span>${esc(AP.tierLabel(tier, 'fr'))}${score != null ? ` · ${score}/100` : ''}</span>`;

  /* ------------------------------------------------ éditeur de lignes (tarifs, agréments, liens, vidéos) */
  const ROWS = {
    pricing: [['category', 'Service', 'select-cat'], ['label', 'Prestation', 'text'], ['price', 'Prix', 'text'], ['currency', 'Devise', CURRENCIES], ['unit', 'Unité', UNITS], ['conditions', 'Conditions', 'text']],
    licences: [['name', 'Agrément (ex. CNAPS)', 'text'], ['number', 'Numéro', 'text'], ['authority', 'Autorité', 'text'], ['expiry', 'Expire le', 'date']],
    certifications: [['name', 'Certification (ex. ISO 18788)', 'text'], ['issuer', 'Organisme', 'text'], ['expiry', 'Expire le', 'date']],
    links: [['label', 'Libellé', 'text'], ['url', 'Adresse (https://…)', 'text']],
    videos: [['url', 'Lien vidéo (YouTube, Vimeo…)', 'text'], ['caption', 'Légende', 'text']],
  };
  function cell(key, f, v, cats) {
    const [k, label, type] = f;
    if (type === 'select-cat') return `<select class="i" data-k="${k}" aria-label="${esc(label)}"><option value=""></option>${(cats.length ? cats : Object.keys(CATS)).map(c => `<option value="${c}"${c === v ? ' selected' : ''}>${esc(AP.catLabel(c))}</option>`).join('')}</select>`;
    if (Array.isArray(type)) return `<select class="i" data-k="${k}" aria-label="${esc(label)}">${type.map(o => `<option${o === v ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
    return `<input class="i" data-k="${k}" type="${type}" value="${esc(v || '')}" placeholder="${esc(label)}" aria-label="${esc(label)}">`;
  }
  function rowsHtml(key, rows, cats) {
    const f = ROWS[key];
    const tr = r => `<tr>${f.map(x => `<td>${cell(key, x, (r || {})[x[0]], cats || [])}</td>`).join('')}<td><button type="button" class="btn small" data-del-row title="Retirer">×</button></td></tr>`;
    return `<div class="rows" data-rows="${key}"><table class="t rows-t"><thead><tr>${f.map(x => `<th>${esc(x[1])}</th>`).join('')}<th></th></tr></thead>
      <tbody>${(rows || []).map(tr).join('')}</tbody></table><button type="button" class="btn small" data-add-row="${key}">+ Ajouter une ligne</button></div>`;
  }
  function readRows(key) {
    const box = main.querySelector(`[data-rows="${key}"]`); if (!box) return [];
    return [...box.querySelectorAll('tbody tr')].map(tr => Object.fromEntries([...tr.querySelectorAll('[data-k]')].map(i => [i.dataset.k, i.value.trim()])))
      .filter(r => Object.entries(r).some(([k, v]) => v && !['currency', 'unit'].includes(k)));
  }

  /* ------------------------------------------------ accès */
  async function start() {
    if (!A || !A.enabled || !AP) {
      main.innerHTML = '<div class="card"><h2>Espace prestataire pas encore activé</h2><p>Les comptes ne sont pas encore ouverts sur cette installation.</p><a class="btn" href="index.html">Retour à la carte</a></div>';
      return;
    }
    if (!A.session) {
      main.innerHTML = ID ? `<div class="card"><h2>Fiche prestataire</h2><p>Les coordonnées, tarifs, garanties et avis des prestataires sont réservés aux comptes validés.</p>
          <a class="btn primary" href="compte.html">Se connecter</a></div>`
        : `<div class="card"><h2>Espace prestataire</h2><p>Jets privés, sécurité, sûreté, assistance médicale, chauffeurs, taxis, meet &amp; greet… Référencez gratuitement vos services auprès des voyageurs et des entreprises clientes d'Angor.</p>
          <ul><li>Inscription et référencement <strong>gratuits</strong>, sans option payante.</li><li>Classement fondé uniquement sur la <strong>qualité et la vérification</strong> de votre fiche.</li>
          <li>Demandes de devis et avis de clients validés.</li></ul>
          <div class="row"><a class="btn primary" href="compte.html?type=provider">Créer un compte prestataire</a><a class="btn" href="compte.html">J'ai déjà un compte</a><a class="btn" href="annuaire.html">Conditions de l'annuaire</a></div></div>`;
      return;
    }
    try { me = await A.profile(); } catch (e) { me = null; }
    if (!me) { location.href = 'compte.html'; return; }
    if (ID) return renderView(ID);
    if (me.account_type !== 'provider' && me.role !== 'admin') {
      main.innerHTML = `<div class="card"><h2>Espace réservé aux prestataires</h2><p>Votre compte est un compte client. Pour consulter les prestataires, ouvrez la fiche d'un pays sur la carte (rubrique « prestataires de services disponibles »).</p><a class="btn" href="index.html">Carte</a></div>`;
      return;
    }
    await loadMine();
    if (!P) return renderCreate();
    renderEditor();
  }
  async function loadMine() {
    const rows = await A.rest(`providers?owner_id=eq.${me.id}&select=*`);
    P = (rows || [])[0] || null;
    if (!P) return;
    [docs, reviews, requests] = await Promise.all([
      A.rest(`provider_documents?provider_id=eq.${P.id}&select=*&order=uploaded_at.desc`).catch(() => []),
      A.rest(`provider_reviews?provider_id=eq.${P.id}&select=*&order=created_at.desc`).catch(() => []),
      A.rest(`provider_requests?provider_id=eq.${P.id}&select=*&order=created_at.desc`).catch(() => [])]);
  }
  function renderCreate() {
    $('#brand').textContent = 'Mon espace prestataire';
    main.innerHTML = `<div class="card"><h2>Créer ma fiche prestataire</h2><div id="m"></div>
      <p>Votre fiche reste un <strong>brouillon invisible</strong> tant que vous ne la soumettez pas à l'annuaire. Vous pourrez la compléter à votre rythme.</p>
      <form id="f-new" class="row"><input class="i" name="name" required minlength="2" maxlength="120" placeholder="Nom commercial" value="${esc(me.organization || '')}" style="max-width:360px">
      <button class="btn primary" type="submit">Créer la fiche</button></form></div>`;
    $('#f-new').addEventListener('submit', async ev => {
      ev.preventDefault();
      try { await A.rest('providers', { method: 'POST', body: { owner_id: me.id, name: new FormData(ev.target).get('name').trim() } }); await loadMine(); renderEditor(); }
      catch (e) { msg($('#m'), e.message); }
    });
  }

  /* ------------------------------------------------ éditeur de la fiche */
  function gather() {
    const f = $('#f-fiche'), d = Object.fromEntries(new FormData(f).entries());
    const g = { insurer: d.insurer.trim(), insurance_amount: d.insurance_amount.trim(), insurance_expiry: d.insurance_expiry,
      licences: readRows('licences'), certifications: readRows('certifications') };
    const photos = (P.media || []).filter(m => m.type === 'photo');
    return {
      name: d.name.trim(), legal_name: d.legal_name.trim(), registration_no: d.registration_no.trim(), hq_country: d.hq_country || null,
      founded: d.founded ? +d.founded : null, website: d.website.trim(), linkedin: d.linkedin.trim(), links: readRows('links'),
      description_fr: d.description_fr.trim(), description_en: d.description_en.trim(),
      categories: [...f.querySelectorAll('input[name="cat"]:checked')].map(i => i.value), countries: state.countries.slice(), cities: d.cities.trim(),
      contacts: { phone_247: d.phone_247.trim(), email_ops: d.email_ops.trim(), email_booking: d.email_booking.trim(), phone_booking: d.phone_booking.trim(),
        languages: d.languages.split(',').map(x => x.trim()).filter(Boolean), response_time: d.response_time.trim() },
      pricing: readRows('pricing'), guarantees: g,
      media: photos.concat(readRows('videos').map(v => ({ type: 'video', url: v.url, caption: v.caption }))),
      public_listing: !!d.public_listing,
    };
  }
  const state = { countries: [] };
  function scorePanel() {
    const cur = Object.assign({}, P, gather());
    const sc = AP.score(cur, docs), tier = AP.tierOf(P.status, sc.score);
    $('#score').innerHTML = `<div class="row" style="justify-content:space-between"><div><div class="pv-score">${sc.score}<small>/100</small></div>
        <div>${tierBadge(tier)}</div></div><span class="pill ${STATUS[P.status][1]}">${esc(STATUS[P.status][0])}</span></div>
      ${[['Fiche', sc.items.filter(i => !i.doc)], ['Justificatifs', sc.items.filter(i => i.doc)]].map(([h, its]) => `<h3 class="pv-ck-h">${h}<span>${its.reduce((a, i) => a + (i.ok ? i.pts : 0), 0)} / ${its.reduce((a, i) => a + i.pts, 0)}</span></h3>
      <ul class="pv-check">${its.map(i => `<li class="${i.ok ? 'ok' : ''}"><span>${i.ok ? '✓' : '○'}</span>${esc(i.fr.replace(/^Justificatif : /, ''))}<b>+${i.pts}</b></li>`).join('')}</ul>`).join('')}
      ${AP.canSubmit(docs) ? '' : '<div class="msg warn">Pour soumettre la fiche à l\'annuaire, envoyez d\'abord votre <strong>extrait d\'immatriculation</strong> (rubrique 8).</div>'}
      <p class="hint">Votre place dans l'annuaire dépend uniquement de ce score et de la vérification par Angor (aucune option payante). Score indicatif : il est recalculé par Angor à l'enregistrement.</p>`;
  }
  const TODAY = new Date().toISOString().slice(0, 10);
  function scoreItem(key) { return AP.score(Object.assign({}, P), docs).items.find(i => i.key === key); }
  /** État d'un type de justificatif : [classe, libellé] – le meilleur document du type l'emporte. */
  function docState(kind) {
    const list = docs.filter(d => d.kind === kind);
    if (list.some(d => d.status === 'validated' && AP.docActive(d, TODAY))) return ['approved', 'validé'];
    if (list.some(d => AP.docActive(d, TODAY))) return ['pending', 'envoyé – en attente'];
    if (list.some(d => d.status === 'rejected')) return ['rejected', 'refusé – à renvoyer'];
    if (list.length) return ['rejected', kind === 'insurance' ? 'expirée / sans date' : 'expiré'];
    return ['missing', 'manquant'];
  }
  function renderEditor() {
    $('#brand').textContent = 'Mon espace prestataire';
    state.countries = (P.countries || []).slice();
    const c = P.contacts || {}, g = P.guarantees || {};
    const groups = Object.keys(GROUPS).map(gk => `<fieldset class="pv-group"><legend>${esc(GROUPS[gk].fr)}</legend>${Object.entries(CATS).filter(([, v]) => v.group === gk)
      .map(([k, v]) => `<label class="switch"><input type="checkbox" name="cat" value="${k}"${(P.categories || []).includes(k) ? ' checked' : ''}><span>${esc(v.fr)}</span></label>`).join('')}</fieldset>`).join('');
    const photos = (P.media || []).filter(m => m.type === 'photo'), videos = (P.media || []).filter(m => m.type === 'video');
    main.classList.add('wide');
    main.innerHTML = `
    <div class="pv-layout"><div class="pv-main">
    <div class="card"><div class="row" style="justify-content:space-between"><h2 style="margin:0">${esc(P.name)}</h2>
      <div class="row"><a class="btn small" href="prestataire.html?id=${esc(P.id)}" target="_blank">Voir ma fiche publique</a></div></div>
      <p class="hint">Remplissez les rubriques puis <strong>Enregistrer</strong>. Les informations suivies de 🔒 ne sont visibles que des clients connectés et validés ; vos justificatifs ne sont visibles que d'Angor.</p></div>
    <form id="f-fiche">
    <div class="card"><h2>1. Identité</h2><div class="grid2">
      <label class="f">Nom commercial<input class="i" name="name" required value="${esc(P.name)}"></label>
      <label class="f">Raison sociale<input class="i" name="legal_name" value="${esc(P.legal_name || '')}"></label>
      <label class="f">N° d'immatriculation (SIREN, Companies House…)<input class="i" name="registration_no" value="${esc(P.registration_no || '')}"></label>
      <label class="f">Pays du siège<select class="i" name="hq_country">${countryOpts(P.hq_country, '—')}</select></label>
      <label class="f">Année de création<input class="i" name="founded" type="number" min="1800" max="2100" value="${esc(P.founded || '')}"></label>
      <label class="f">Site web<input class="i" name="website" type="url" placeholder="https://" value="${esc(P.website || '')}"></label>
      <label class="f">Page LinkedIn<input class="i" name="linkedin" type="url" placeholder="https://www.linkedin.com/company/…" value="${esc(P.linkedin || '')}"></label></div>
      <h3>Autres liens (réseaux, presse, références)</h3>${rowsHtml('links', P.links)}</div>
    <div class="card"><h2>2. Services et zones couvertes</h2><p class="hint">Cochez toutes les lignes de services que vous proposez.</p>${groups}
      <h3>Pays couverts</h3><div class="chips" id="countries"></div>
      <div class="row" style="margin-top:8px"><select class="i" id="add-country" style="max-width:320px">${countryOpts('', 'Ajouter un pays…')}</select></div>
      <label class="f">Villes et bases opérationnelles<input class="i" name="cities" value="${esc(P.cities || '')}" placeholder="Bamako, Abidjan, Dakar…"></label></div>
    <div class="card"><h2>3. Présentation</h2>
      <label class="f">Présentation en français <span class="hint" data-count="description_fr"></span><textarea class="i" name="description_fr" rows="6" maxlength="4000">${esc(P.description_fr || '')}</textarea></label>
      <label class="f">Presentation in English <span class="hint" data-count="description_en"></span><textarea class="i" name="description_en" rows="6" maxlength="4000">${esc(P.description_en || '')}</textarea></label></div>
    <div class="card"><h2>4. Points de contact 🔒</h2><p class="hint">Privilégiez des coordonnées de service (salle opérationnelle, réservation) plutôt que des coordonnées personnelles.</p><div class="grid2">
      <label class="f">Téléphone 24/7<input class="i" name="phone_247" type="tel" value="${esc(c.phone_247 || '')}"></label>
      <label class="f">E-mail opérationnel<input class="i" name="email_ops" type="email" value="${esc(c.email_ops || '')}"></label>
      <label class="f">Téléphone réservation<input class="i" name="phone_booking" type="tel" value="${esc(c.phone_booking || '')}"></label>
      <label class="f">E-mail réservation / devis<input class="i" name="email_booking" type="email" value="${esc(c.email_booking || '')}"></label>
      <label class="f">Langues parlées (séparées par des virgules)<input class="i" name="languages" value="${esc((c.languages || []).join(', '))}"></label>
      <label class="f">Délai de réponse habituel<input class="i" name="response_time" value="${esc(c.response_time || '')}" placeholder="ex. moins de 2 h"></label></div></div>
    <div class="card"><h2>5. Tarifs fixes 🔒</h2><p class="hint">Prix indicatifs publics (hors taxes ou TTC : précisez dans « Conditions »). Les devis sur mesure passent par les demandes.</p>${rowsHtml('pricing', P.pricing, P.categories || [])}</div>
    <div class="card"><h2>6. Garanties 🔒</h2><div class="grid2">
      <label class="f">Assureur responsabilité civile professionnelle<input class="i" name="insurer" value="${esc(g.insurer || '')}"></label>
      <label class="f">Montant garanti<input class="i" name="insurance_amount" value="${esc(g.insurance_amount || '')}" placeholder="ex. 5 M€ par sinistre"></label>
      <label class="f">Valable jusqu'au<input class="i" name="insurance_expiry" type="date" value="${esc(g.insurance_expiry || '')}"></label></div>
      <h3>Agréments et autorisations d'exercer</h3>${rowsHtml('licences', g.licences)}
      <h3>Certifications et adhésions (ISO 18788, ISO 9001, ICoCA, PSC.1…)</h3>${rowsHtml('certifications', g.certifications)}</div>
    <div class="card"><h2>7. Photos et vidéos</h2><div id="m-media"></div>
      <div class="pv-gallery">${photos.map(m => `<figure><img src="${esc(A.publicUrl('provider-media', m.path))}" alt="" loading="lazy"><button type="button" class="btn small bad" data-del-photo="${esc(m.path)}">Retirer</button></figure>`).join('') || '<p class="hint">Aucune photo.</p>'}</div>
      <div class="row"><input type="file" id="photo-file" accept="image/jpeg,image/png,image/webp"><button type="button" class="btn" id="photo-up">Ajouter la photo</button><span class="hint">JPEG, PNG ou WebP, 5 Mo maximum.</span></div>
      <h3>Vidéos (liens)</h3>${rowsHtml('videos', videos)}</div>
    <div class="card"><h2>Visibilité</h2><label class="switch"><input type="checkbox" name="public_listing"${P.public_listing !== false ? ' checked' : ''}><span>Apparaître dans l'annuaire (fiches pays de la carte, rapports pays) une fois la fiche soumise</span></label></div>
    </form>
    <div class="card" id="docs"><h2>8. Justificatifs <span class="hint">– 55 points sur 100, visibles d'Angor seulement</span></h2><div id="m-docs"></div>
      <p class="hint">Les justificatifs pèsent davantage que tout le reste de la fiche : sans eux, le score plafonne à 45/100 (niveau D). L'extrait
        d'immatriculation est <strong>obligatoire</strong> pour soumettre la fiche, et sa validation par Angor pour être « vérifié » (niveaux A et B).
        Un document refusé ou expiré ne compte plus. PDF, JPEG ou PNG, 10 Mo maximum.</p>
      <table class="t resp pv-doclist"><thead><tr><th>Justificatif</th><th>Points</th><th>État</th><th></th></tr></thead><tbody>
      ${Object.entries(DOC_KINDS).filter(([, v]) => v.key).map(([k, v]) => { const it = scoreItem(v.key), st = docState(k);
        return `<tr class="${st[0]}"><td data-l="Justificatif"><strong>${esc(v.fr)}</strong>${k === 'registration' ? ' <span class="pill pending">obligatoire</span>' : ''}${v.hint ? `<br><span class="hint">${esc(v.hint)}</span>` : ''}</td>
          <td data-l="Points">+${it ? it.pts : 0}</td><td data-l="État"><span class="pill ${st[0]}">${esc(st[1])}</span></td>
          <td><button type="button" class="btn small" data-add-doc="${k}">${st[0] === 'missing' || st[0] === 'rejected' ? 'Ajouter' : '+ Autre'}</button></td></tr>`; }).join('')}
      <tr><td data-l="Justificatif"><strong>Validation par Angor</strong><br><span class="hint">Au moins 2 justificatifs validés, dont l'immatriculation.</span></td><td data-l="Points">+${(scoreItem('docs_ok') || {}).pts || 0}</td>
        <td data-l="État"><span class="pill ${(scoreItem('docs_ok') || {}).ok ? 'approved' : 'missing'}">${(scoreItem('docs_ok') || {}).ok ? 'acquis' : 'en attente'}</span></td><td></td></tr></tbody></table>
      ${docs.length ? `<h3>Documents envoyés</h3><table class="t resp"><thead><tr><th>Document</th><th>Expire le</th><th>Statut</th><th></th></tr></thead><tbody>${docs.map(d => `<tr><td data-l="Document">${esc(docLabel(d.kind))}${d.label ? ' – ' + esc(d.label) : ''}<br><span class="hint">envoyé le ${fmtDate(d.uploaded_at)}</span></td>
        <td data-l="Expire le">${fmtDate(d.expires_on) || '–'}${AP.docActive(d, TODAY) || d.status === 'rejected' ? '' : ' <span class="pill rejected">expiré / sans date</span>'}</td><td data-l="Statut"><span class="pill ${d.status === 'validated' ? 'approved' : d.status === 'rejected' ? 'rejected' : 'pending'}">${{ pending: 'en attente', validated: 'validé', rejected: 'refusé' }[d.status]}</span>${d.note ? `<br><span class="hint">${esc(d.note)}</span>` : ''}</td>
        <td><div class="row"><button class="btn small" data-open-doc="${esc(d.path)}">Voir</button><button class="btn small bad" data-del-doc="${esc(d.id)}" data-path="${esc(d.path)}">Supprimer</button></div></td></tr>`).join('')}</tbody></table>` : ''}
      <h3>Envoyer un justificatif</h3>
      <form id="f-doc" class="grid2"><label class="f">Type<select class="i" name="kind">${Object.entries(DOC_KINDS).map(([k, v]) => `<option value="${k}">${esc(v.fr)}</option>`).join('')}</select></label>
        <label class="f">Libellé (facultatif)<input class="i" name="label" placeholder="ex. Kbis du 02/10/2026, ISO 18788"></label>
        <label class="f"><span id="doc-exp-l">Date de fin de validité (si applicable)</span><input class="i" name="expires_on" type="date"></label>
        <label class="f">Fichier<input class="i" name="file" type="file" accept="application/pdf,image/jpeg,image/png" required></label>
        <p class="hint full" id="doc-hint"></p>
        <div><button class="btn primary" type="submit">Envoyer le justificatif</button></div></form></div>
    ${requestsCard()}${reviewsCard()}
    </div><aside class="pv-side"><div class="card pv-sticky"><h2>Qualité de la fiche</h2><div id="score"></div><div id="m-save"></div>
      <div class="row"><button class="btn primary" id="save">Enregistrer</button>
      ${P.status === 'draft' ? `<button class="btn ok" id="submit"${AP.canSubmit(docs) ? '' : ' disabled title="Extrait d\'immatriculation requis"'}>Soumettre à l'annuaire</button>` : P.status === 'submitted' ? '<button class="btn" id="unsubmit">Repasser en brouillon</button>' : ''}</div>
      <p class="hint">${P.status === 'verified' ? `Vérifiée par Angor le ${fmtDate(P.verified_at)}.` : P.status === 'suspended' ? 'Fiche suspendue : contactez Angor.' : 'Une fois soumise, la fiche apparaît dans l\'annuaire ; Angor la vérifie ensuite à partir de vos justificatifs.'}</p></div></aside></div>`;
    drawCountries(); counters(); scorePanel(); bindEditor();
  }
  function drawCountries() {
    $('#countries').innerHTML = state.countries.map(iso => `<span class="chip">${esc(cname(iso))}<button type="button" data-rm-country="${iso}" aria-label="Retirer">×</button></span>`).join('') || '<span class="hint">Aucun pays.</span>';
  }
  function counters() { main.querySelectorAll('[data-count]').forEach(el => { const t = main.querySelector(`[name="${el.dataset.count}"]`); el.textContent = `(${t.value.trim().length} caractères)`; }); }
  function requestsCard() {
    if (!requests.length) return '<div class="card"><h2>Demandes reçues</h2><p class="hint">Aucune demande pour l\'instant. Les clients validés peuvent vous écrire depuis votre fiche.</p></div>';
    return `<div class="card"><h2>Demandes reçues <span class="badge">${requests.filter(r => r.status === 'new').length || ''}</span></h2>${requests.map(r => `<div class="check-card"><div class="h"><strong>${esc(r.requester_label || 'Client')}</strong><span class="hint">${fmtDate(r.created_at)}</span></div>
      <p class="hint">${r.category ? esc(AP.catLabel(r.category)) : ''}${r.country ? ' · ' + esc(cname(r.country)) : ''}${r.period ? ' · ' + esc(r.period) : ''}</p><p>${esc(r.message)}</p>
      <label class="f">Statut<select class="i" data-req="${esc(r.id)}" style="max-width:220px">${[['new', 'nouvelle'], ['read', 'lue'], ['answered', 'répondue'], ['closed', 'close']].map(([k, l]) => `<option value="${k}"${r.status === k ? ' selected' : ''}>${l}</option>`).join('')}</select></label></div>`).join('')}</div>`;
  }
  function reviewsCard() {
    if (!reviews.length) return '<div class="card"><h2>Avis reçus</h2><p class="hint">Aucun avis pour l\'instant.</p></div>';
    return `<div class="card"><h2>Avis reçus</h2>${reviews.map(r => `<div class="check-card"><div class="h"><strong>${'★'.repeat(r.rating)}${'☆'.repeat(5 - r.rating)} ${esc(r.title || '')}</strong><span class="hint">${esc(r.author_label || '')} · ${fmtDate(r.created_at)}${r.status === 'hidden' ? ' · masqué par Angor' : ''}</span></div>
      <p>${esc(r.comment)}</p><label class="f">Votre réponse publique<textarea class="i" rows="2" maxlength="2000" data-reply="${esc(r.id)}">${esc(r.provider_reply || '')}</textarea></label>
      <button type="button" class="btn small" data-send-reply="${esc(r.id)}">Publier la réponse</button></div>`).join('')}</div>`;
  }
  let timer = null;
  function bindEditor() {
    if (!bindEditor.done) { bindEditor.done = true; bindEditorOnce(); }
    $('#add-country').addEventListener('change', ev => { const v = ev.target.value; if (v && !state.countries.includes(v)) state.countries.push(v); ev.target.value = ''; drawCountries(); scorePanel(); });
    bindButtons();
  }
  /* écouteurs délégués : posés une seule fois sur <main>, ils servent à chaque nouvel affichage de l'éditeur */
  function bindEditorOnce() {
    main.addEventListener('input', () => { if (!$('#score')) return; counters(); clearTimeout(timer); timer = setTimeout(scorePanel, 250); });
    main.addEventListener('change', () => { if (!$('#score')) return; clearTimeout(timer); timer = setTimeout(scorePanel, 100); });
    main.addEventListener('click', async ev => {
      const add = ev.target.closest('[data-add-row]'), del = ev.target.closest('[data-del-row]'), rm = ev.target.closest('[data-rm-country]');
      if (add) { const key = add.dataset.addRow, tb = main.querySelector(`[data-rows="${key}"] tbody`);
        tb.insertAdjacentHTML('beforeend', rowsHtml(key, [{}], key === 'pricing' ? [...main.querySelectorAll('input[name="cat"]:checked')].map(i => i.value) : []).match(/<tbody>([\s\S]*)<\/tbody>/)[1]); return; }
      if (del) { del.closest('tr').remove(); scorePanel(); return; }
      if (rm) { state.countries = state.countries.filter(x => x !== rm.dataset.rmCountry); drawCountries(); scorePanel(); return; }
      if (!P) return;
      const od = ev.target.closest('[data-open-doc]');
      if (od) { try { window.open(await A.signedUrl('provider-docs', od.dataset.openDoc, 120), '_blank', 'noopener'); } catch (e) { msg($('#m-docs'), e.message); } return; }
      const dd = ev.target.closest('[data-del-doc]');
      if (dd) { try { await A.removeFile('provider-docs', dd.dataset.path).catch(() => {}); await A.rest(`provider_documents?id=eq.${dd.dataset.delDoc}`, { method: 'DELETE' }); await reload(); } catch (e) { msg($('#m-docs'), e.message); } return; }
      const dp = ev.target.closest('[data-del-photo]');
      if (dp) { try { await A.removeFile('provider-media', dp.dataset.delPhoto).catch(() => {}); P.media = (P.media || []).filter(m => m.path !== dp.dataset.delPhoto); await save(); } catch (e) { msg($('#m-media'), e.message); } return; }
      const sr = ev.target.closest('[data-send-reply]');
      if (sr) { try { await A.rest(`provider_reviews?id=eq.${sr.dataset.sendReply}`, { method: 'PATCH', body: { provider_reply: main.querySelector(`[data-reply="${sr.dataset.sendReply}"]`).value.trim() || null } }); sr.textContent = 'Réponse publiée ✓'; } catch (e) { alertBox(e.message); } }
    });
    main.addEventListener('change', async ev => {
      const rq = ev.target.closest('[data-req]');
      if (rq) { try { await A.rest(`provider_requests?id=eq.${rq.dataset.req}`, { method: 'PATCH', body: { status: rq.value } }); } catch (e) { alertBox(e.message); } }
    });
  }
  function bindButtons() {
    $('#save').addEventListener('click', () => save().then(() => msg($('#m-save'), 'Fiche enregistrée.', 'ok')).catch(e => msg($('#m-save'), e.message)));
    const sub = $('#submit'), uns = $('#unsubmit');
    if (sub) sub.addEventListener('click', () => save({ status: 'submitted' }).then(() => msg($('#m-save'), 'Fiche publiée dans l\'annuaire. Angor la vérifiera à partir de vos justificatifs.', 'ok')).catch(e => msg($('#m-save'), e.message)));
    if (uns) uns.addEventListener('click', () => save({ status: 'draft' }).catch(e => msg($('#m-save'), e.message)));
    $('#photo-up').addEventListener('click', async () => {
      const f = $('#photo-file').files[0]; if (!f) return;
      if (f.size > 5 * 1048576) { msg($('#m-media'), 'Photo trop lourde (5 Mo maximum).'); return; }
      try { const path = `${P.id}/${Date.now()}-${f.name.replace(/[^\w.-]+/g, '_')}`; await A.upload('provider-media', path, f);
        P.media = (P.media || []).concat([{ type: 'photo', path }]); await save(); } catch (e) { msg($('#m-media'), e.message); }
    });
    const fd = $('#f-doc'), kindSel = fd.querySelector('[name="kind"]');
    const kindHint = () => { const k = DOC_KINDS[kindSel.value] || {};
      $('#doc-hint').textContent = k.hint || ''; fd.querySelector('[name="expires_on"]').required = !!k.expiry;
      $('#doc-exp-l').textContent = k.expiry ? 'Date de fin de validité (obligatoire)' : 'Date de fin de validité (si applicable)'; };
    kindSel.addEventListener('change', kindHint); kindHint();
    main.querySelectorAll('[data-add-doc]').forEach(b => b.addEventListener('click', () => {
      kindSel.value = b.dataset.addDoc; kindHint(); fd.scrollIntoView({ behavior: 'smooth', block: 'center' }); fd.querySelector('[name="file"]').focus({ preventScroll: true }); }));
    fd.addEventListener('submit', async ev => {
      ev.preventDefault();
      const d = new FormData(ev.target), f = d.get('file');
      if (!f || !f.size) return;
      if (f.size > 10 * 1048576) { msg($('#m-docs'), 'Fichier trop lourd (10 Mo maximum).'); return; }
      if (!/\.(pdf|jpe?g|png)$/i.test(f.name)) { msg($('#m-docs'), 'Format accepté : PDF, JPEG ou PNG.'); return; }
      if (d.get('expires_on') && d.get('expires_on') < TODAY) { msg($('#m-docs'), 'Ce document est déjà expiré : envoyez une version à jour.'); return; }
      try { const path = `${P.id}/docs/${Date.now()}-${f.name.replace(/[^\w.-]+/g, '_')}`; await A.upload('provider-docs', path, f);
        await A.rest('provider_documents', { method: 'POST', body: { provider_id: P.id, kind: d.get('kind'), label: d.get('label').trim() || null, expires_on: d.get('expires_on') || null, path } });
        await reload(); } catch (e) { msg($('#m-docs'), e.message); }
    });
  }
  function alertBox(text) { msg($('#m-save'), text); }
  async function save(extra) {
    const body = Object.assign(gather(), extra || {});
    const keepPhotos = (P.media || []).filter(m => m.type === 'photo');
    body.media = keepPhotos.concat(body.media.filter(m => m.type === 'video'));
    const rows = await A.rest(`providers?id=eq.${P.id}`, { method: 'PATCH', body });
    P = (rows || [])[0] || P;
    await reload();
  }
  async function reload() { const y = window.scrollY; await loadMine(); renderEditor(); window.scrollTo(0, y); }

  /* ------------------------------------------------ fiche publique (clients validés, administrateur) */
  async function renderView(id) {
    let p = null;
    try { p = ((await A.rest(`providers?id=eq.${encodeURIComponent(id)}&select=*`)) || [])[0]; } catch (e) { p = null; }
    if (!p) { main.innerHTML = '<div class="card"><h2>Fiche indisponible</h2><p>Cette fiche n\'existe pas, n\'est pas encore publiée, ou elle est réservée aux comptes validés.</p><a class="btn" href="compte.html">Mon compte</a></div>'; return; }
    const rv = await A.rest(`provider_reviews?provider_id=eq.${p.id}&select=*&order=created_at.desc`).catch(() => []);
    const pub = rv.filter(r => r.status === 'published');
    const avg = pub.length ? (pub.reduce((s, r) => s + r.rating, 0) / pub.length) : 0;
    const c = p.contacts || {}, g = p.guarantees || {}, admin = me.role === 'admin', mine = p.owner_id === me.id;
    const canAct = me.account_type === 'client' && me.status === 'approved' && !mine;
    const already = rv.some(r => r.author_id === me.id);
    const photos = (p.media || []).filter(m => m.type === 'photo'), videos = (p.media || []).filter(m => m.type === 'video');
    const lic = (g.licences || []).concat(g.certifications || []);
    $('#brand').textContent = p.name;
    document.title = p.name + ' – Angor Intelligence';
    main.innerHTML = `
    <div class="card"><div class="row" style="justify-content:space-between;align-items:flex-start"><div><h2 style="margin:0 0 6px">${esc(p.name)}</h2>
      ${tierBadge(p.tier, p.score)} ${p.status !== 'verified' && p.status !== 'submitted' ? `<span class="pill ${STATUS[p.status][1]}">${esc(STATUS[p.status][0])}</span>` : ''}
      <p class="hint">${esc(p.legal_name || '')}${p.registration_no ? ' · n° ' + esc(p.registration_no) : ''}${p.hq_country ? ' · siège : ' + esc(cname(p.hq_country)) : ''}${p.founded ? ' · depuis ' + esc(p.founded) : ''}</p></div>
      ${pub.length ? `<div class="pv-avg"><b>${avg.toFixed(1)}</b>/5<br><span class="hint">${pub.length} avis</span></div>` : ''}</div>
      <div class="chips" style="margin-top:8px">${(p.categories || []).map(k => `<span class="chip">${esc(AP.catLabel(k))}</span>`).join('')}</div>
      <p class="hint" style="margin-top:8px">Pays couverts : ${(p.countries || []).map(cname).map(esc).join(', ') || '—'}${p.cities ? ' · ' + esc(p.cities) : ''}</p>
      ${admin ? `<div class="row" style="margin-top:10px"><span class="hint">Administration :</span>${['verified', 'submitted', 'suspended'].filter(s => s !== p.status).map(s => `<button class="btn small ${s === 'verified' ? 'ok' : s === 'suspended' ? 'bad' : ''}" data-admin-status="${s}">${{ verified: 'Vérifier', submitted: 'Remettre « soumise »', suspended: 'Suspendre' }[s]}</button>`).join('')}<a class="btn small" href="admin.html?tab=providers">Justificatifs</a></div><div id="m-admin"></div>` : ''}
      ${mine ? '<div class="row" style="margin-top:10px"><a class="btn small" href="prestataire.html">Modifier ma fiche</a></div>' : ''}</div>
    ${p.description_fr || p.description_en ? `<div class="card"><h2>Présentation</h2><p style="white-space:pre-line">${esc(p.description_fr || p.description_en)}</p>${p.description_fr && p.description_en ? `<details><summary>English</summary><p style="white-space:pre-line">${esc(p.description_en)}</p></details>` : ''}</div>` : ''}
    ${photos.length || videos.length ? `<div class="card"><h2>Photos et vidéos</h2><div class="pv-gallery">${photos.map(m => `<figure><a href="${esc(A.publicUrl('provider-media', m.path))}" target="_blank" rel="noopener"><img src="${esc(A.publicUrl('provider-media', m.path))}" alt="" loading="lazy"></a></figure>`).join('')}</div>
      ${videos.length ? `<ul>${videos.map(v => `<li><a href="${esc(v.url)}" target="_blank" rel="noopener">${esc(v.caption || v.url)}</a> ↗</li>`).join('')}</ul>` : ''}</div>` : ''}
    <div class="card"><h2>Contacts</h2><div class="grid2">
      ${[['Téléphone 24/7', c.phone_247, 'tel'], ['E-mail opérationnel', c.email_ops, 'mail'], ['Réservation', c.phone_booking, 'tel'], ['E-mail réservation / devis', c.email_booking, 'mail']].filter(x => x[1])
        .map(([l, v, k]) => `<div><div class="hint">${l}</div><a href="${k === 'tel' ? 'tel:' + esc(v.replace(/\s/g, '')) : 'mailto:' + esc(v)}">${esc(v)}</a></div>`).join('') || '<p class="hint">Non renseigné.</p>'}</div>
      <p class="hint">${(c.languages || []).length ? 'Langues : ' + esc(c.languages.join(', ')) : ''}${c.response_time ? ' · Délai de réponse : ' + esc(c.response_time) : ''}</p>
      <div class="row">${p.website ? `<a class="btn small" href="${esc(p.website)}" target="_blank" rel="noopener">Site web ↗</a>` : ''}${p.linkedin ? `<a class="btn small" href="${esc(p.linkedin)}" target="_blank" rel="noopener">LinkedIn ↗</a>` : ''}${(p.links || []).map(l => `<a class="btn small" href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label || 'Lien')} ↗</a>`).join('')}</div></div>
    ${(p.pricing || []).length ? `<div class="card"><h2>Tarifs fixes</h2><table class="t resp"><thead><tr><th>Prestation</th><th>Prix</th><th>Conditions</th></tr></thead><tbody>${p.pricing.map(r => `<tr><td>${esc(r.label || '')}${r.category ? `<br><span class="hint">${esc(AP.catLabel(r.category))}</span>` : ''}</td><td><strong>${esc(r.price || '')} ${esc(r.currency || '')}</strong>${r.unit ? ` / ${esc(r.unit)}` : ''}</td><td>${esc(r.conditions || '')}</td></tr>`).join('')}</tbody></table></div>` : ''}
    <div class="card"><h2>Garanties</h2><ul>
      ${g.insurer ? `<li>Assurance RC professionnelle : ${esc(g.insurer)}${g.insurance_amount ? ' – ' + esc(g.insurance_amount) : ''}${g.insurance_expiry ? ` (valable jusqu'au ${fmtDate(g.insurance_expiry)})` : ''}</li>` : ''}
      ${lic.map(l => `<li>${esc(l.name || '')}${l.number ? ' n° ' + esc(l.number) : ''}${l.authority || l.issuer ? ' – ' + esc(l.authority || l.issuer) : ''}${l.expiry ? ` (jusqu'au ${fmtDate(l.expiry)})` : ''}</li>`).join('')}
      ${!g.insurer && !lic.length ? '<li class="hint">Non renseigné.</li>' : ''}</ul>
      <p class="hint">${p.tier === 'A' || p.tier === 'B' ? 'Justificatifs contrôlés par Angor.' : 'Informations déclarées par le prestataire, non encore vérifiées par Angor.'}</p></div>
    ${canAct ? quoteForm(p) : ''}
    <div class="card"><h2>Avis ${pub.length ? `(${pub.length})` : ''}</h2>
      ${pub.map(r => `<div class="check-card"><div class="h"><strong>${'★'.repeat(r.rating)}${'☆'.repeat(5 - r.rating)} ${esc(r.title || '')}</strong><span class="hint">${esc(r.author_label || '')} · publié le ${fmtDate(r.created_at)}${r.service_date ? ' · prestation du ' + fmtDate(r.service_date) : ''}</span></div>
        <p>${esc(r.comment)}</p>${r.provider_reply ? `<div class="msg info"><strong>Réponse du prestataire</strong> (${fmtDate(r.reply_at)}) : ${esc(r.provider_reply)}</div>` : ''}
        ${admin ? `<button class="btn small" data-hide-review="${esc(r.id)}">Masquer</button>` : ''}</div>`).join('') || '<p class="hint">Aucun avis pour l\'instant.</p>'}
      ${canAct && !already ? reviewForm() : ''}
      <p class="hint">Avis déposés sans contrepartie par des clients validés d'Angor, publiés avec le nom de leur organisation et contrôlés a posteriori ; ils n'influent pas sur le classement. <a href="annuaire.html#avis">Règles de publication</a> · signaler un avis : voir les mentions légales.</p></div>`;
    bindView(p);
  }
  function quoteForm(p) {
    return `<form class="card" id="f-quote"><h2>Demander un devis / contacter</h2><div id="m-quote"></div><div class="grid2">
      <label class="f">Service<select class="i" name="category"><option value=""></option>${(p.categories || []).map(k => `<option value="${k}">${esc(AP.catLabel(k))}</option>`).join('')}</select></label>
      <label class="f">Pays<select class="i" name="country"><option value=""></option>${(p.countries || []).map(i => `<option value="${i}">${esc(cname(i))}</option>`).join('')}</select></label>
      <label class="f">Dates ou période<input class="i" name="period" maxlength="200" placeholder="ex. du 12 au 15 novembre"></label></div>
      <label class="f">Votre demande<textarea class="i" name="message" rows="4" minlength="10" maxlength="3000" required></textarea></label>
      <p class="hint">Votre nom, votre organisation et votre adresse e-mail seront transmis au prestataire pour qu'il vous réponde. Angor n'est pas partie au contrat que vous conclurez avec lui.</p>
      <button class="btn primary" type="submit">Envoyer la demande</button></form>`;
  }
  function reviewForm() {
    return `<form id="f-review" class="check-card"><h3>Laisser un avis</h3><div id="m-review"></div><div class="grid2">
      <label class="f">Note<select class="i" name="rating">${[5, 4, 3, 2, 1].map(n => `<option value="${n}">${'★'.repeat(n)}${'☆'.repeat(5 - n)} (${n}/5)</option>`).join('')}</select></label>
      <label class="f">Date de la prestation<input class="i" name="service_date" type="date"></label></div>
      <label class="f">Titre<input class="i" name="title" maxlength="120"></label>
      <label class="f">Commentaire<textarea class="i" name="comment" rows="3" minlength="10" maxlength="2000" required></textarea></label>
      <label class="switch"><input type="checkbox" required><span>Je certifie avoir eu recours à ce prestataire et n'avoir reçu aucune contrepartie pour cet avis.</span></label>
      <button class="btn" type="submit">Publier l'avis</button></form>`;
  }
  let VIEW = null;
  function bindView(p) {
    VIEW = p;
    if (!bindView.done) { bindView.done = true; bindViewOnce(); }
    bindViewForms(p);
  }
  function bindViewOnce() {
    main.addEventListener('click', async ev => {
      const p = VIEW; if (!p) return;
      const as = ev.target.closest('[data-admin-status]');
      if (as) { try { await A.rest(`providers?id=eq.${p.id}`, { method: 'PATCH', body: { status: as.dataset.adminStatus } }); renderView(p.id); } catch (e) { msg($('#m-admin'), e.message); } return; }
      const hr = ev.target.closest('[data-hide-review]');
      if (hr) { try { await A.rest(`provider_reviews?id=eq.${hr.dataset.hideReview}`, { method: 'PATCH', body: { status: 'hidden' } }); renderView(p.id); } catch (e) { msg($('#m-admin'), e.message); } }
    });
  }
  function bindViewForms(p) {
    const q = $('#f-quote');
    if (q) q.addEventListener('submit', async ev => {
      ev.preventDefault();
      const d = Object.fromEntries(new FormData(q).entries());
      try { await A.rest('provider_requests', { method: 'POST', body: { provider_id: p.id, category: d.category || null, country: d.country || null, period: d.period.trim() || null, message: d.message.trim() } });
        q.reset(); msg($('#m-quote'), 'Demande envoyée : le prestataire la voit dans son espace et vous répondra directement.', 'ok'); } catch (e) { msg($('#m-quote'), e.message); }
    });
    const r = $('#f-review');
    if (r) r.addEventListener('submit', async ev => {
      ev.preventDefault();
      const d = Object.fromEntries(new FormData(r).entries());
      try { await A.rest('provider_reviews', { method: 'POST', body: { provider_id: p.id, rating: +d.rating, title: d.title.trim() || null, comment: d.comment.trim(), service_date: d.service_date || null } });
        renderView(p.id); } catch (e) { msg($('#m-review'), e.message); }
    });
  }

  start();
})();
