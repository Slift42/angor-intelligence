/* Angor Intelligence – page « Mon compte » : inscription, connexion, validation, préférences, safety checks. */
(function () {
  'use strict';
  const A = window.AngorAccount;
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const ls = { get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* */ } } };
  try { const th = ls.get('vs-theme'); if (th) document.documentElement.dataset.theme = th; } catch (e) { /* */ }
  const COUNTRIES = ((window.VS_COUNTRIES || {}).features || []).map(f => f.properties).sort((a, b) => a.name_fr.localeCompare(b.name_fr));
  const cname = iso => (COUNTRIES.find(c => c.iso2 === iso) || {}).name_fr || iso;
  const countryOpts = (sel, empty) => (empty ? `<option value="">${esc(empty)}</option>` : '') + COUNTRIES.map(c => `<option value="${c.iso2}"${c.iso2 === sel ? ' selected' : ''}>${esc(c.name_fr)}</option>`).join('');
  const main = $('#main');
  let P = null;          // profil
  let mode = 'login';

  function msg(el, text, kind) { el.innerHTML = text ? `<div class="msg ${kind || 'err'}">${esc(text)}</div>` : ''; }

  /* ------------------------------------------------ non configuré / déconnecté */
  function renderDisabled() {
    main.innerHTML = `<div class="card"><h2>Comptes pas encore activés</h2><p>Cette installation d'Angor Intelligence fonctionne sans compte : la carte, les alertes et le Travel buddy restent accessibles librement.</p>
      <p class="hint">Administrateur : activez les comptes en suivant le guide de mise en ligne, partie H (Supabase, gratuit).</p><a class="btn primary" href="index.html">Retour à la carte</a></div>`;
  }
  function renderAuth(info) {
    main.innerHTML = `<div class="card"><div class="seg" role="group">
        <button data-mode="login" aria-pressed="${mode === 'login'}">Connexion</button><button data-mode="signup" aria-pressed="${mode === 'signup'}">Créer un compte</button>
        <button data-mode="recover" aria-pressed="${mode === 'recover'}">Mot de passe oublié</button></div>
      <div id="m">${info ? `<div class="msg ok">${esc(info)}</div>` : ''}</div>
      <form id="f" autocomplete="on">${mode === 'signup' ? `
        <div class="grid2"><label class="f">Nom et prénom<input class="i" name="full_name" required autocomplete="name"></label>
        <label class="f">Organisation<input class="i" name="organization" required autocomplete="organization"></label></div>` : ''}
        <label class="f">Adresse e-mail<input class="i" name="email" type="email" required autocomplete="email"></label>
        ${mode !== 'recover' ? `<label class="f">Mot de passe<input class="i" name="password" type="password" required minlength="${mode === 'signup' ? 10 : 1}" autocomplete="${mode === 'signup' ? 'new-password' : 'current-password'}"></label>` : ''}
        ${mode === 'signup' ? `<label class="f">Confirmer le mot de passe<input class="i" name="password2" type="password" required minlength="10" autocomplete="new-password"></label>
          <label class="switch"><input type="checkbox" name="consent" required><span>J'accepte les <a href="cgu.html" target="_blank">conditions générales d'utilisation</a> et j'ai pris connaissance de la <a href="confidentialite.html" target="_blank">politique de confidentialité</a>.</span></label>
          <p class="hint">Données conservées : nom, organisation, e-mail, pour gérer votre accès. Votre position n'est partagée que si vous l'activez.</p>` : ''}
        <div class="row"><button class="btn primary" type="submit">${{ login: 'Se connecter', signup: 'Créer mon compte', recover: 'Recevoir un lien' }[mode]}</button></div>
        ${mode === 'signup' ? '<p class="hint">Chaque compte est validé par un administrateur avant d\'accéder aux fonctions réservées (sites, safety checks, préférences synchronisées).</p>' : ''}
      </form></div>`;
    main.querySelector('.seg').addEventListener('click', ev => { const b = ev.target.closest('[data-mode]'); if (b) { mode = b.dataset.mode; renderAuth(); } });
    $('#f').addEventListener('submit', async ev => {
      ev.preventDefault();
      const d = Object.fromEntries(new FormData(ev.target).entries()), m = $('#m'), btn = ev.target.querySelector('button[type=submit]');
      btn.disabled = true;
      try {
        if (mode === 'login') { await A.signIn(d.email.trim(), d.password); return start(); }
        if (mode === 'recover') { await A.recover(d.email.trim()); msg(m, 'Si un compte existe, un lien de réinitialisation vient de vous être envoyé.', 'ok'); return; }
        if (d.password !== d.password2) throw new Error('Les deux mots de passe ne correspondent pas.');
        if (!/[a-z]/i.test(d.password) || !/\d/.test(d.password)) throw new Error('Le mot de passe doit contenir des lettres et des chiffres (10 caractères minimum).');
        const r = await A.signUp(d.email.trim(), d.password, { full_name: d.full_name.trim(), organization: d.organization.trim() });
        if (A.session) return start();
        mode = 'login';
        renderAuth(r && r.id || (r && r.user) ? 'Compte créé. Confirmez votre adresse avec le lien reçu par e-mail, puis connectez-vous : un administrateur validera ensuite votre accès.' : 'Compte créé.');
      } catch (e) { msg(m, e.message); } finally { btn.disabled = false; }
    });
  }
  function renderNewPassword() {
    main.innerHTML = `<div class="card"><h2>Nouveau mot de passe</h2><div id="m"></div><form id="f"><label class="f">Nouveau mot de passe<input class="i" name="p" type="password" minlength="10" required autocomplete="new-password"></label>
      <button class="btn primary" type="submit">Enregistrer</button></form></div>`;
    $('#f').addEventListener('submit', async ev => {
      ev.preventDefault();
      try { await A.setPassword(new FormData(ev.target).get('p')); await A.signOut(); mode = 'login'; renderAuth('Mot de passe modifié : connectez-vous.'); }
      catch (e) { msg($('#m'), e.message); }
    });
  }
  function renderStatus() {
    const t = { pending: ['En attente de validation', 'Votre compte a bien été créé. Un administrateur doit le valider avant que vous puissiez utiliser les fonctions réservées. Vous recevrez l\'accès dès sa validation : revenez sur cette page ou rechargez l\'application.'],
      rejected: ['Demande refusée', 'Votre demande d\'accès n\'a pas été acceptée. Contactez l\'administrateur de la plateforme si vous pensez qu\'il s\'agit d\'une erreur.'],
      suspended: ['Compte suspendu', 'Votre accès est suspendu. Contactez l\'administrateur de la plateforme.'] }[P.status];
    main.innerHTML = `<div class="card"><h2>${esc(t[0])} <span class="pill ${P.status}">${esc(P.status)}</span></h2><p>${esc(t[1])}</p>
      <p class="hint">${esc(P.full_name || '')} · ${esc(P.organization || '')} · ${esc(P.email)}</p>
      <div class="row"><button class="btn" id="reload">Vérifier à nouveau</button><button class="btn" id="out">Se déconnecter</button><a class="btn" href="index.html">Carte</a></div></div>`;
    $('#reload').addEventListener('click', start);
    $('#out').addEventListener('click', async () => { await A.signOut(); start(); });
  }

  /* ------------------------------------------------ compte validé */
  function chips(list, attr) { return (list || []).map(iso => `<span class="chip">${esc(cname(iso))}<button data-${attr}="${iso}" aria-label="Retirer">×</button></span>`).join('') || '<span class="hint">Aucun</span>'; }
  async function renderApproved() {
    const prefs = P.prefs || {};
    const watch = Array.from(new Set([...(prefs.watch || []), ...ls.get('vs-watch', [])]));
    const locSites = ls.get('vs-sites', []), locCor = ls.get('vs-corridors', []);
    const pushOn = 'Notification' in window && Notification.permission === 'granted' && prefs.push !== false && prefs.push_enabled;
    $('#admin-link').hidden = P.role !== 'admin';
    main.innerHTML = `
    <div class="card"><div class="row" style="justify-content:space-between"><div><h2 style="margin:0">${esc(P.full_name || P.email)}</h2>
      <div class="hint">${esc(P.email)} · ${esc(P.organization || '')}</div></div><div><span class="pill approved">compte validé</span> ${P.role === 'admin' ? '<span class="pill admin">administrateur</span>' : ''}</div></div></div>
    <div class="card" id="checks"><h2>Safety checks</h2><div id="checks-body" class="hint">Chargement…</div></div>
    <form class="card" id="f-profile"><h2>Profil</h2><div id="m-profile"></div><div class="grid2">
      <label class="f">Nom et prénom<input class="i" name="full_name" value="${esc(P.full_name || '')}"></label>
      <label class="f">Organisation<input class="i" name="organization" value="${esc(P.organization || '')}"></label>
      <label class="f">Fonction<input class="i" name="job_title" value="${esc(P.job_title || '')}"></label>
      <label class="f">Téléphone (facultatif, joint en cas d'urgence)<input class="i" name="phone" type="tel" value="${esc(P.phone || '')}"></label></div>
      <button class="btn primary" type="submit">Enregistrer le profil</button></form>
    <form class="card" id="f-prefs"><h2>Préférences</h2><div id="m-prefs"></div><div class="grid2">
      <label class="f">Langue<select class="i" name="lang"><option value="fr">Français</option><option value="en">English</option></select></label>
      <label class="f">Thème<select class="i" name="theme"><option value="">Automatique</option><option value="light">Clair</option><option value="dark">Sombre</option></select></label>
      <label class="f">Période affichée par défaut<select class="i" name="hours"><option value="24">24 h</option><option value="72">72 h</option><option value="168">7 jours</option><option value="720">30 jours</option></select></label>
      <label class="f">Fond de carte<select class="i" name="basemap"><option value="detail">Détaillé</option><option value="bright">Contrasté</option><option value="clean">Épuré</option><option value="satellite">Satellite</option></select></label>
      <label class="f">Pays de résidence ou d'affectation<select class="i" name="base_country">${countryOpts(prefs.base_country, '—')}</select></label>
      <label class="f">Gravité minimale de mes alertes<select class="i" name="alert_min_severity"><option value="2">Modérée et plus</option><option value="3">Élevée et plus</option><option value="4">Critique uniquement</option></select></label></div>
      <h3>Pays suivis</h3><div class="chips" id="watch">${chips(watch, 'w')}</div>
      <div class="row" style="margin-top:8px"><select class="i" id="add-watch" style="max-width:320px">${countryOpts('', 'Ajouter un pays…')}</select></div>
      <h3>Déplacements prévus (pays)</h3><div class="chips" id="travel">${chips(prefs.travel_countries, 't')}</div>
      <div class="row" style="margin-top:8px"><select class="i" id="add-travel" style="max-width:320px">${countryOpts('', 'Ajouter un pays…')}</select></div>
      <label class="switch"><input type="checkbox" name="digest" ${prefs.digest !== false ? 'checked' : ''}><span>Recevoir le point quotidien</span></label>
      <button class="btn primary" type="submit">Enregistrer les préférences</button>
      <p class="hint">Vos préférences s'appliquent sur tous vos appareils (téléphone, ordinateur) à la prochaine ouverture de la carte.</p></form>
    <div class="card"><h2>Notifications et position</h2><div id="m-dev"></div>
      <label class="switch"><input type="checkbox" id="push" ${pushOn ? 'checked' : ''}><span>Notifications sur cet appareil (safety checks, alertes graves)</span></label>
      <label class="switch"><input type="checkbox" id="consent" ${P.consent_location ? 'checked' : ''}><span>Partager ma position pour les safety checks (mise à jour quand j'ouvre l'application)</span></label>
      <div class="row"><button class="btn" id="locate" ${P.consent_location ? '' : 'disabled'}>Mettre à jour ma position</button>
      <span class="hint" id="loc-info">${P.location ? `Dernière position : ${esc(cname(P.location.iso) || '')} · ${esc(new Date(P.location.at).toLocaleString('fr-FR'))}` : 'Aucune position enregistrée.'}</span></div></div>
    <div class="card"><h2>Mes sites et trajets</h2><div id="m-sites"></div>
      <p>Compte : <strong>${(P.sites || []).length}</strong> site(s), <strong>${(P.corridors || []).length}</strong> trajet(s) · Ce navigateur : <strong>${locSites.length}</strong> site(s), <strong>${locCor.length}</strong> trajet(s)</p>
      <div class="row"><button class="btn" id="push-sites">Enregistrer ceux de ce navigateur dans mon compte</button><button class="btn" id="pull-sites">Charger ceux de mon compte ici</button></div></div>
    <div class="card"><h2>Sécurité</h2><div id="m-sec"></div>
      <form id="f-pwd" class="row"><input class="i" name="p" type="password" minlength="10" placeholder="Nouveau mot de passe (10 caractères min.)" style="max-width:320px" autocomplete="new-password"><button class="btn" type="submit">Changer le mot de passe</button></form>
      <div class="row" style="margin-top:12px"><button class="btn" id="out">Se déconnecter</button></div>
      <h3>Conditions acceptées</h3><p class="hint" id="legal-acc">…</p>
      <h3>Supprimer mon compte</h3><p class="hint">Suppression définitive de votre compte, de vos préférences, sites et réponses aux safety checks.</p>
      <div class="row"><input class="i" id="del-confirm" placeholder="Tapez SUPPRIMER" style="max-width:220px"><button class="btn bad" id="del">Supprimer définitivement</button></div></div>`;
    const fp = $('#f-prefs');
    fp.lang.value = prefs.lang || ls.get('vs-lang', 'fr'); fp.theme.value = prefs.theme || '';
    fp.hours.value = String(prefs.hours || ls.get('vs-hours', 72)); fp.basemap.value = prefs.basemap || ls.get('vs-basemap', 'detail');
    fp.alert_min_severity.value = String(prefs.alert_min_severity || 3);
    let watchList = watch.slice(), travel = (prefs.travel_countries || []).slice();
    const redrawChips = () => { $('#watch').innerHTML = chips(watchList, 'w'); $('#travel').innerHTML = chips(travel, 't'); };
    $('#add-watch').addEventListener('change', ev => { if (ev.target.value && !watchList.includes(ev.target.value)) watchList.push(ev.target.value); ev.target.value = ''; redrawChips(); });
    $('#add-travel').addEventListener('change', ev => { if (ev.target.value && !travel.includes(ev.target.value)) travel.push(ev.target.value); ev.target.value = ''; redrawChips(); });
    fp.addEventListener('click', ev => {
      const w = ev.target.closest('[data-w]'), t = ev.target.closest('[data-t]');
      if (w) { ev.preventDefault(); watchList = watchList.filter(x => x !== w.dataset.w); redrawChips(); }
      if (t) { ev.preventDefault(); travel = travel.filter(x => x !== t.dataset.t); redrawChips(); }
    });
    fp.addEventListener('submit', async ev => {
      ev.preventDefault();
      const d = Object.fromEntries(new FormData(fp).entries());
      const np = Object.assign({}, prefs, { lang: d.lang, theme: d.theme || null, hours: +d.hours, basemap: d.basemap, base_country: d.base_country || null,
        alert_min_severity: +d.alert_min_severity, digest: !!d.digest, watch: watchList, travel_countries: travel });
      try {
        P = await A.updateProfile({ prefs: np }); Object.assign(prefs, np);
        ls.set('vs-lang', np.lang); ls.set('vs-hours', np.hours); ls.set('vs-basemap', np.basemap); ls.set('vs-watch', watchList);
        if (np.theme) { ls.set('vs-theme', np.theme); document.documentElement.dataset.theme = np.theme; }
        msg($('#m-prefs'), 'Préférences enregistrées.', 'ok');
      } catch (e) { msg($('#m-prefs'), e.message); }
    });
    $('#f-profile').addEventListener('submit', async ev => {
      ev.preventDefault();
      const d = Object.fromEntries(new FormData(ev.target).entries());
      try { P = await A.updateProfile({ full_name: d.full_name.trim(), organization: d.organization.trim(), job_title: d.job_title.trim(), phone: d.phone.trim() || null }); msg($('#m-profile'), 'Profil enregistré.', 'ok'); }
      catch (e) { msg($('#m-profile'), e.message); }
    });
    $('#push').addEventListener('change', async ev => {
      try {
        if (ev.target.checked) { await A.subscribePush(); P = await A.updateProfile({ prefs: Object.assign({}, P.prefs, { push_enabled: true }) }); msg($('#m-dev'), 'Notifications activées sur cet appareil.', 'ok'); }
        else { await A.unsubscribePush(); msg($('#m-dev'), 'Notifications désactivées sur cet appareil.', 'info'); }
      } catch (e) { ev.target.checked = false; msg($('#m-dev'), e.message); }
    });
    $('#consent').addEventListener('change', async ev => {
      try { P = await A.updateProfile({ consent_location: ev.target.checked, location: ev.target.checked ? P.location : null }); $('#locate').disabled = !ev.target.checked;
        msg($('#m-dev'), ev.target.checked ? 'Partage de position activé.' : 'Partage désactivé et position effacée.', 'ok'); }
      catch (e) { msg($('#m-dev'), e.message); }
    });
    $('#locate').addEventListener('click', () => locate().then(l => { $('#loc-info').textContent = `Position enregistrée : ${cname(l.iso) || '—'}`; }).catch(e => msg($('#m-dev'), e.message)));
    $('#push-sites').addEventListener('click', async () => {
      const key = s => (s.name || '') + '|' + (s.lat || (s.points || [[0]])[0][0]);
      const merge = (a, b) => { const seen = new Set(a.map(key)); return a.concat(b.filter(x => !seen.has(key(x)))); };
      try { P = await A.updateProfile({ sites: merge(P.sites || [], ls.get('vs-sites', [])), corridors: merge(P.corridors || [], ls.get('vs-corridors', [])) }); renderApproved(); }
      catch (e) { msg($('#m-sites'), e.message); }
    });
    $('#pull-sites').addEventListener('click', () => { ls.set('vs-sites', P.sites || []); ls.set('vs-corridors', P.corridors || []); msg($('#m-sites'), 'Sites et trajets chargés sur ce navigateur.', 'ok'); });
    $('#f-pwd').addEventListener('submit', async ev => {
      ev.preventDefault();
      try { await A.setPassword(new FormData(ev.target).get('p')); ev.target.reset(); msg($('#m-sec'), 'Mot de passe modifié.', 'ok'); } catch (e) { msg($('#m-sec'), e.message); }
    });
    $('#out').addEventListener('click', async () => { await A.signOut(); start(); });
    $('#del').addEventListener('click', async () => {
      if ($('#del-confirm').value.trim().toUpperCase() !== 'SUPPRIMER') { msg($('#m-sec'), 'Tapez SUPPRIMER pour confirmer.'); return; }
      try { await A.deleteAccount(); mode = 'login'; renderAuth('Votre compte et vos données ont été supprimés.'); } catch (e) { msg($('#m-sec'), e.message); }
    });
    renderChecks();
    A.legalAccepted().then(rows => {
      const names = { cgu: 'CGU', confidentialite: 'Politique de confidentialité', cgv: 'CGV', dpa: 'Accord de sous-traitance' };
      $('#legal-acc').innerHTML = rows.length ? rows.map(r => `${esc(names[r.doc] || r.doc)} ${esc(r.version)} – ${esc(new Date(r.accepted_at).toLocaleString('fr-FR'))}`).join('<br>')
        + ' · <a href="legal.html">Informations légales</a>' : 'Aucune acceptation enregistrée. <a href="legal.html">Informations légales</a>';
    }).catch(() => { $('#legal-acc').innerHTML = '<a href="legal.html">Informations légales</a>'; });
  }

  /* ------------------------------------------------ position (volontaire) */
  function isoAt(lat, lon) {
    const inRing = (x, y, r) => { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { if (((r[i][1] > y) !== (r[j][1] > y)) && (x < (r[j][0] - r[i][0]) * (y - r[i][1]) / (r[j][1] - r[i][1]) + r[i][0])) c = !c; } return c; };
    for (const f of (window.VS_COUNTRIES || {}).features || []) {
      const g = f.geometry; if (!g) continue;
      const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
      if (polys.some(p => inRing(lon, lat, p[0]))) return f.properties.iso2;
    }
    return null;
  }
  function locate() {
    return new Promise((ok, ko) => {
      if (!navigator.geolocation) return ko(new Error('Géolocalisation indisponible.'));
      navigator.geolocation.getCurrentPosition(async pos => {
        const l = { lat: +pos.coords.latitude.toFixed(3), lon: +pos.coords.longitude.toFixed(3), iso: isoAt(pos.coords.latitude, pos.coords.longitude), at: new Date().toISOString() };
        try { P = await A.updateProfile({ location: l }); ok(l); } catch (e) { ko(e); }
      }, () => ko(new Error('Position refusée ou indisponible.')), { enableHighAccuracy: false, timeout: 15000, maximumAge: 600000 });
    });
  }

  /* ------------------------------------------------ safety checks */
  async function renderChecks() {
    const el = $('#checks-body');
    try {
      const [checks, resp] = await Promise.all([A.openChecks(), A.myResponses()]);
      const mine = (checks || []).filter(c => A.concerned(c, P));
      const byId = Object.fromEntries((resp || []).map(r => [r.check_id, r]));
      const L = { safe: 'En sécurité', help: 'Besoin d\'aide', not_concerned: 'Pas concerné' };
      el.classList.remove('hint');
      el.innerHTML = mine.length ? mine.map(c => `<div class="check-card"><div class="h"><strong>${esc(c.title)}</strong><span class="hint">${esc(new Date(c.created_at).toLocaleString('fr-FR'))}</span></div>
        ${c.message ? `<p>${esc(c.message)}</p>` : ''}
        ${byId[c.id] ? `<p>Votre réponse : <strong>${esc(L[byId[c.id].status])}</strong></p>` : ''}
        <div class="row"><button class="btn ok" data-r="safe" data-c="${c.id}">Je suis en sécurité</button><button class="btn bad" data-r="help" data-c="${c.id}">J'ai besoin d'aide</button>
        <button class="btn small" data-r="not_concerned" data-c="${c.id}">Pas concerné</button></div></div>`).join('')
        : '<p class="hint">Aucun safety check en cours pour vous.</p>';
      el.onclick = async ev => {
        const b = ev.target.closest('[data-r]'); if (!b) return;
        b.disabled = true;
        let pos = null;
        if (P.consent_location) { try { const l = await locate(); pos = l; } catch (e) { /* sans position */ } }
        try { await A.respond(b.dataset.c, b.dataset.r, null, pos); renderChecks(); } catch (e) { alertMsg(e.message); }
      };
    } catch (e) { el.textContent = 'Safety checks indisponibles : ' + e.message; }
  }
  function alertMsg(t) { const d = document.createElement('div'); d.className = 'msg err'; d.textContent = t; $('#checks-body').prepend(d); }

  /* ------------------------------------------------ démarrage */
  async function start() {
    if (!A || !A.enabled) return renderDisabled();
    const type = A.consumeHash();
    if (type === 'recovery') return renderNewPassword();
    if (!A.session) return renderAuth(type === 'signup' ? 'Adresse confirmée : connectez-vous.' : '');
    try { P = await A.profile(); } catch (e) { P = null; }
    if (!P) { await A.signOut(); return renderAuth(); }
    if (A.legalInForce()) {
      let missing = [];
      try { missing = await A.legalMissing(); } catch (e) { missing = []; }   // table absente : schéma pas encore mis à jour
      if (missing.length) return renderAccept(missing);
    }
    if (P.status !== 'approved') return renderStatus();
    renderApproved();
  }

  /* ------------------------------------------------ nouvelle version des conditions */
  function renderAccept(missing) {
    main.innerHTML = `<div class="card"><h2>Nos conditions évoluent</h2>
      <p>Pour continuer à utiliser votre compte, merci de prendre connaissance des documents suivants :</p>
      <ul>${missing.map(r => `<li><a href="${esc(r.page)}" target="_blank">${esc(r.titre)}</a> (version ${esc(r.version)})</li>`).join('')}</ul>
      <div id="m"></div>
      <label class="switch"><input type="checkbox" id="ok-legal"><span>J'ai lu et j'accepte ces documents.</span></label>
      <div class="row"><button class="btn primary" id="accept" disabled>Accepter et continuer</button><button class="btn" id="out">Se déconnecter</button></div>
      <p class="hint">Si vous ne les acceptez pas, vous pouvez demander la suppression de votre compte à l'adresse indiquée dans les mentions légales.</p></div>`;
    $('#ok-legal').addEventListener('change', ev => { $('#accept').disabled = !ev.target.checked; });
    $('#accept').addEventListener('click', async () => {
      try { await A.acceptLegal(missing); start(); } catch (e) { msg($('#m'), e.message); }
    });
    $('#out').addEventListener('click', async () => { await A.signOut(); start(); });
  }
  start();
})();
