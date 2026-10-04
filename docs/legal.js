/* Angor Intelligence – pages légales : remplit les textes à partir de window.VS_LEGAL (docs/data/legal.js, écrit par le
   robot depuis config/legal.json). Chaque page porte <body data-doc="cgu|cgv|…">.
   - <span data-v="editeur.siren"></span> : valeur du champ, ou « [à compléter : SIREN] » si vide ;
   - <div data-list="sous_traitants"></div> : tableau (hebergeurs, sous_traitants, tiers_techniques, offres, sources, credits, documents) ;
   - <div data-if="beta_gratuite"> : affiché seulement si la valeur est vraie ;
   - bandeau « Projet » tant que status ≠ « en vigueur », version et date du document, sommaire, navigation. */
(function () {
  'use strict';
  try { const th = JSON.parse(localStorage.getItem('vs-theme')); if (th) document.documentElement.dataset.theme = th; } catch (e) { /* */ }
  const L = window.VS_LEGAL || { status: 'projet', documents: {}, missing: [] };
  const DOC = document.body.dataset.doc || '';
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LABELS = { 'editeur.nom': "nom de l'éditeur", 'editeur.adresse': 'adresse', 'editeur.siren': 'SIREN', 'editeur.immatriculation': 'immatriculation',
    'editeur.email': 'e-mail de contact', 'editeur.telephone': 'téléphone', 'editeur.directeur_publication': 'directeur de la publication',
    'editeur.contact_donnees': 'contact données personnelles', 'mediateur.nom': 'médiateur de la consommation', 'mediateur.site': 'site du médiateur',
    'mediateur.adresse': 'adresse du médiateur', tribunal: 'tribunal compétent' };
  const DEFAULT_DOCS = { mentions: ['Mentions légales', 'mentions-legales.html'], cgu: ["Conditions générales d'utilisation", 'cgu.html'],
    cgv: ['Conditions générales de vente', 'cgv.html'], confidentialite: ['Politique de confidentialité et cookies', 'confidentialite.html'],
    dpa: ['Accord de sous-traitance des données', 'sous-traitance.html'], licences: ['Sources, crédits et licences', 'licences.html'] };
  const docs = Object.keys(DEFAULT_DOCS).map(k => Object.assign({ key: k, titre: DEFAULT_DOCS[k][0], page: DEFAULT_DOCS[k][1] }, (L.documents || {})[k] || {}));
  const get = path => path.split('.').reduce((o, k) => (o && typeof o === 'object' ? o[k] : undefined), L);
  const todo = label => `<mark class="todo">[à compléter : ${esc(label)}]</mark>`;
  const dateFr = d => { try { return new Date(d + 'T12:00:00').toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }); } catch (e) { return d || ''; } };
  const link = (url, text) => url ? (/^https?:\/\//.test(url) ? `<a href="${esc(url)}" rel="noopener" target="_blank">${esc(text || url)}</a>` : esc(text || url)) : '';
  const cell = (label, html) => `<td data-l="${esc(label)}">${html || '—'}</td>`;
  const table = (heads, rows) => `<table class="t resp"><thead><tr>${heads.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${r.map((c, i) => cell(heads[i], c)).join('')}</tr>`).join('')}</tbody></table>`;

  const LISTS = {
    hebergeurs: () => table(['Rôle', 'Prestataire', 'Adresse', 'Contact', 'Localisation des données'],
      (L.hebergeurs || []).map(h => [esc(h.role), `<strong>${esc(h.nom)}</strong>`, esc(h.adresse), /@/.test(h.contact || '') ? esc(h.contact) : link(h.contact), esc(h.localisation)])),
    sous_traitants: () => table(['Prestataire', 'Service', 'Données concernées', 'Localisation', 'Garanties'],
      (L.sous_traitants || []).map(s => [`<strong>${esc(s.nom)}</strong>`, esc(s.service), esc(s.donnees), esc(s.localisation), esc(s.garanties)])),
    tiers_techniques: () => table(['Service', 'Usage', 'Données transmises par votre navigateur'],
      (L.tiers_techniques || []).map(s => [`<strong>${esc(s.nom)}</strong>`, esc(s.usage), esc(s.donnees)])),
    offres: () => table(['Offre', 'Contenu', 'Prix'], (L.offres || []).map(o => [`<strong>${esc(o.nom)}</strong>`, esc(o.contenu), esc(o.prix)])),
    sources: () => table(['Source', 'Licence ou conditions'], (L.sources || []).map(s => [esc(s.nom), esc(s.licence)])),
    credits: () => table(['Élément', 'Licence', 'Mention'], (L.credits || []).map(c => [link(c.url, c.nom) || esc(c.nom), esc(c.licence), esc(c.mention)])),
    documents: () => `<div class="cards">${docs.map(d => `<a href="${esc(d.page)}"><strong>${esc(d.titre)}</strong><span>${d.version ? `Version ${esc(d.version)} du ${esc(dateFr(d.date))}` : ''}</span></a>`).join('')}</div>`,
  };

  function fill() {
    document.querySelectorAll('[data-v]').forEach(el => {
      const p = el.dataset.v, v = get(p);
      if (v != null && String(v).trim()) el.innerHTML = el.dataset.link === 'mail' ? `<a href="mailto:${esc(v)}">${esc(v)}</a>` : el.dataset.link === 'url' ? link(v) : esc(v);
      else el.innerHTML = todo(el.dataset.label || LABELS[p] || p);
    });
    document.querySelectorAll('[data-list]').forEach(el => { const f = LISTS[el.dataset.list]; if (f) el.innerHTML = f(); });
    document.querySelectorAll('[data-if]').forEach(el => { el.hidden = !get(el.dataset.if); });
    document.querySelectorAll('[data-ifnot]').forEach(el => { el.hidden = !!get(el.dataset.ifnot); });
  }

  function frame() {
    const art = $('article'), h1 = art.querySelector('h1'), d = docs.find(x => x.key === DOC);
    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.innerHTML = d && d.version ? `Version ${esc(d.version)} – en date du ${esc(dateFr(d.date))}` : '';
    h1.after(meta);
    if (L.status !== 'en vigueur') {
      const b = document.createElement('div');
      b.className = 'draft';
      b.innerHTML = '<strong>Projet – document non contractuel.</strong> Ce texte est en cours de finalisation'
        + (L.missing && L.missing.length ? ` (informations à compléter : ${esc(L.missing.join(', '))})` : '') + '. Il n\'engage pas encore l\'éditeur.';
      meta.after(b);
    }
    const hs = Array.from(art.querySelectorAll('h2'));
    hs.forEach((h, i) => { if (!h.id) h.id = 's' + (i + 1); });
    if (hs.length > 3) {
      const toc = document.createElement('nav');
      toc.className = 'toc no-print-x';
      toc.innerHTML = hs.map(h => `<a href="#${h.id}">${esc(h.textContent)}</a>`).join('');
      (art.querySelector('.draft') || meta).after(toc);
    }
    $('#side').innerHTML = `<h4>Informations légales</h4><ul>${docs.map(x => `<li><a href="${esc(x.page)}"${x.key === DOC ? ' aria-current="page"' : ''}>${esc(x.titre)}</a></li>`).join('')}
      <li><a href="legal.html"${DOC === 'index' ? ' aria-current="page"' : ''}>Tous les documents</a></li></ul>
      <h4>Aller plus loin</h4><ul><li><a href="aide.html">Aide</a></li><li><a href="compte.html">Mon compte</a></li><li><a href="index.html">Carte</a></li></ul>`;
    const ed = (L.editeur || {});
    $('#foot').innerHTML = `${esc(ed.nom_commercial || 'Angor Intelligence')}${ed.nom ? ' – ' + esc(ed.nom) : ''} · Outil d'aide à la décision : informations non exhaustives, à vérifier. · `
      + docs.map(x => `<a href="${esc(x.page)}">${esc(x.titre)}</a>`).join(' · ');
    const pr = $('#print');
    if (pr) pr.addEventListener('click', () => window.print());
  }

  fill();
  frame();
})();
