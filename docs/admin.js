/* Angor Intelligence – administration : validation des comptes, rôles, safety checks. */
(function () {
  'use strict';
  const A = window.AngorAccount;
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  try { const th = JSON.parse(localStorage.getItem('vs-theme')); if (th) document.documentElement.dataset.theme = th; } catch (e) { /* */ }
  const COUNTRIES = ((window.VS_COUNTRIES || {}).features || []).map(f => f.properties).sort((a, b) => a.name_fr.localeCompare(b.name_fr));
  const cname = iso => (COUNTRIES.find(c => c.iso2 === iso) || {}).name_fr || iso || '';
  const CITIES = ((window.VS_CITIES || {}).cities || []);
  const fmt = d => d ? new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—';
  const main = $('#main');
  const Q = new URLSearchParams(location.search);
  let me = null, users = [], checks = [], responses = [], tab = Q.get('tab') || (Q.get('check_title') ? 'checks' : 'users'), filter = 'pending', timer = null;

  function msg(el, text, kind) { if (el) el.innerHTML = text ? `<div class="msg ${kind || 'err'}">${esc(text)}</div>` : ''; }
  const STATUS = { pending: 'en attente', approved: 'validé', rejected: 'refusé', suspended: 'suspendu' };

  async function load() {
    [users, checks, responses] = await Promise.all([
      A.rest('profiles?select=*&order=created_at.desc'),
      A.rest('safety_checks?select=*&order=created_at.desc&limit=50'),
      A.rest('safety_responses?select=*')]);
  }
  function render() {
    const pending = users.filter(u => u.status === 'pending').length;
    main.innerHTML = `<div class="tabs" role="tablist"><button data-tab="users" aria-selected="${tab === 'users'}">Utilisateurs${pending ? `<span class="badge">${pending}</span>` : ''}</button>
      <button data-tab="checks" aria-selected="${tab === 'checks'}">Safety checks${checks.some(c => c.status === 'open') ? `<span class="badge">${checks.filter(c => c.status === 'open').length}</span>` : ''}</button></div>
      <div id="body"></div>`;
    main.querySelector('.tabs').addEventListener('click', ev => { const b = ev.target.closest('[data-tab]'); if (b) { tab = b.dataset.tab; render(); } });
    tab === 'users' ? renderUsers() : renderChecks();
  }

  /* ------------------------------------------------ utilisateurs */
  function renderUsers() {
    const q = ($('#q') || {}).value || '';
    const list = users.filter(u => (filter === 'all' || (filter === 'closed' ? ['rejected', 'suspended'].includes(u.status) : u.status === filter))
      && (!q || (u.full_name + ' ' + u.email + ' ' + u.organization).toLowerCase().includes(q.toLowerCase())));
    $('#body').innerHTML = `<div class="card"><div class="row" style="justify-content:space-between">
        <div class="seg" id="flt">${[['pending', 'En attente'], ['approved', 'Validés'], ['closed', 'Refusés / suspendus'], ['all', 'Tous']].map(([k, l]) => `<button data-f="${k}" aria-pressed="${filter === k}">${l} (${k === 'all' ? users.length : users.filter(u => k === 'closed' ? ['rejected', 'suspended'].includes(u.status) : u.status === k).length})</button>`).join('')}</div>
        <input class="i" id="q" placeholder="Rechercher (nom, e-mail, organisation)" value="${esc(q)}" style="max-width:300px"></div>
      <div id="m-users"></div>
      ${list.length ? `<table class="t resp"><thead><tr><th>Utilisateur</th><th>Organisation</th><th>Inscription</th><th>Statut</th><th>Actions</th></tr></thead><tbody>
      ${list.map(u => `<tr><td><strong>${esc(u.full_name || '—')}</strong><br><span class="hint">${esc(u.email)}${u.job_title ? ' · ' + esc(u.job_title) : ''}${u.phone ? ' · ' + esc(u.phone) : ''}</span></td>
        <td>${esc(u.organization || '—')}</td><td class="hint">${fmt(u.created_at)}</td>
        <td><span class="pill ${u.status}">${STATUS[u.status]}</span> ${u.role === 'admin' ? '<span class="pill admin">admin</span>' : ''}</td>
        <td><div class="row">${actions(u)}</div></td></tr>`).join('')}</tbody></table>` : '<p class="hint">Aucun utilisateur dans cette liste.</p>'}</div>`;
    $('#flt').addEventListener('click', ev => { const b = ev.target.closest('[data-f]'); if (b) { filter = b.dataset.f; renderUsers(); } });
    $('#q').addEventListener('input', () => { const pos = $('#q').selectionStart; renderUsers(); $('#q').focus(); $('#q').setSelectionRange(pos, pos); });
    $('#body').onclick = async ev => {
      const b = ev.target.closest('[data-act]'); if (!b) return;
      b.disabled = true;
      try {
        const [status, role] = b.dataset.act.split(':');
        await A.rpc('admin_set_status', { p_user: b.dataset.u, p_status: status, p_role: role || null });
        await load(); render();
      } catch (e) { msg($('#m-users'), e.message); b.disabled = false; }
    };
  }
  function actions(u) {
    const b = (act, label, cls) => `<button class="btn small ${cls || ''}" data-act="${act}" data-u="${u.id}">${label}</button>`;
    if (u.id === me.id) return '<span class="hint">vous</span>';
    if (u.status === 'pending') return b('approved', 'Valider', 'ok') + b('rejected', 'Refuser', 'bad');
    if (u.status === 'approved') return (u.role === 'admin' ? b('approved:user', 'Retirer admin') : b('approved:admin', 'Nommer admin')) + b('suspended', 'Suspendre', 'bad');
    return b('approved', 'Réactiver', 'ok');
  }

  /* ------------------------------------------------ safety checks */
  function areaLabel(a) {
    if (!a || a.type === 'all') return 'Tous les utilisateurs';
    if (a.type === 'country') return 'Pays : ' + cname(a.iso);
    return `${a.radius_km} km autour de ${a.label || (a.lat + ', ' + a.lon)}`;
  }
  function targetsOf(c) { return users.filter(u => u.status === 'approved' && A.concerned(c, u)); }
  function renderChecks() {
    const pre = { title: Q.get('check_title') || '', lat: Q.get('lat'), lon: Q.get('lon'), iso: Q.get('iso') || '', place: Q.get('place') || '' };
    $('#body').innerHTML = `<form class="card" id="f-check"><h2>Nouveau safety check</h2><div id="m-check"></div>
        <label class="f">Titre<input class="i" name="title" required maxlength="120" value="${esc(pre.title)}" placeholder="Ex. Attaque à Bamako – êtes-vous en sécurité ?"></label>
        <label class="f">Message<textarea class="i" name="message" maxlength="500" placeholder="Consignes : restez à l'abri, évitez le centre-ville…"></textarea></label>
        <div class="seg" id="area-type"><button type="button" data-a="all" aria-pressed="${!pre.lat && !pre.iso}">Tous</button><button type="button" data-a="country" aria-pressed="${!!pre.iso && !pre.lat}">Un pays</button><button type="button" data-a="circle" aria-pressed="${!!pre.lat}">Autour d'un lieu</button></div>
        <div class="grid2">
          <label class="f" data-for="country">Pays<select class="i" name="iso">${COUNTRIES.map(c => `<option value="${c.iso2}"${c.iso2 === pre.iso ? ' selected' : ''}>${esc(c.name_fr)}</option>`).join('')}</select></label>
          <label class="f" data-for="circle">Ville ou lieu<input class="i" name="place" list="cities" value="${esc(pre.place)}" placeholder="Ex. Bamako"><datalist id="cities">${CITIES.slice(0, 1500).map(c => `<option value="${esc(c[0])} (${c[1]})">`).join('')}</datalist></label>
          <label class="f" data-for="circle">Rayon (km)<input class="i" name="radius" type="number" min="1" max="2000" value="50"></label>
          <label class="f">Organisation (facultatif)<input class="i" name="organization" placeholder="Toutes"></label>
          <label class="f">Valable pendant<select class="i" name="hours"><option value="6">6 h</option><option value="12">12 h</option><option value="24" selected>24 h</option><option value="48">48 h</option><option value="72">72 h</option></select></label>
        </div>
        <p class="hint" id="preview"></p>
        <button class="btn primary" type="submit">Envoyer le safety check</button>
        <p class="hint">Les utilisateurs concernés reçoivent une notification (s'ils l'ont activée) et un bandeau à l'ouverture de l'application. Ciblage : pays de résidence ou déplacements déclarés, ou dernière position partagée.</p></form>
      <div class="card"><h2>Safety checks récents</h2><div id="m-list"></div><div id="checks-list">${listHtml()}</div></div>`;
    const f = $('#f-check');
    let areaType = pre.lat ? 'circle' : pre.iso ? 'country' : 'all';
    const coords = () => {
      if (pre.lat && f.place.value === pre.place) return { lat: +pre.lat, lon: +pre.lon, label: pre.place };
      const m = f.place.value.match(/^(.*?)\s*(?:\(([A-Z]{2})\))?$/), name = (m[1] || '').trim().toLowerCase(), iso = m[2];
      const c = CITIES.find(x => x[0].toLowerCase() === name && (!iso || x[1] === iso)) || CITIES.find(x => x[0].toLowerCase().startsWith(name) && name);
      return c ? { lat: c[2], lon: c[3], label: c[0] } : null;
    };
    const area = () => {
      if (areaType === 'country') return { type: 'country', iso: f.iso.value };
      if (areaType === 'circle') { const c = coords(); return c ? { type: 'circle', lat: c.lat, lon: c.lon, radius_km: +f.radius.value || 50, label: c.label } : null; }
      return { type: 'all' };
    };
    const refresh = () => {
      f.querySelectorAll('[data-for]').forEach(el => { el.hidden = el.dataset.for !== areaType; });
      $('#area-type').querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.a === areaType)));
      const a = area();
      $('#preview').textContent = a ? `${targetsOf({ area: a, organization: f.organization.value.trim() || null }).length} utilisateur(s) validé(s) concerné(s) à ce jour.` : 'Lieu non reconnu : choisissez une ville de la liste.';
    };
    $('#area-type').addEventListener('click', ev => { const b = ev.target.closest('[data-a]'); if (b) { areaType = b.dataset.a; refresh(); } });
    f.addEventListener('input', refresh); refresh();
    f.addEventListener('submit', async ev => {
      ev.preventDefault();
      const a = area(); if (!a) { msg($('#m-check'), 'Lieu non reconnu.'); return; }
      const btn = f.querySelector('button[type=submit]'); btn.disabled = true;
      try {
        const rows = await A.rest('safety_checks', { method: 'POST', body: { created_by: me.id, title: f.title.value.trim(), message: f.message.value.trim() || null, area: a,
          organization: f.organization.value.trim() || null, event_id: Q.get('event') || null, expires_at: new Date(Date.now() + (+f.hours.value) * 3600e3).toISOString() } });
        let note = '';
        try { const r = await A.fn('safety-push', { check_id: rows[0].id }); note = ` Notifications : ${r.sent || 0} appareil(s) sur ${r.targets || 0} utilisateur(s) concerné(s).`; }
        catch (e) { note = ' Notifications non envoyées (fonction « safety-push » pas encore déployée) : les utilisateurs verront le safety check à l\'ouverture de l\'application.'; }
        await load(); render(); msg($('#m-list'), 'Safety check envoyé.' + note, 'ok');
      } catch (e) { msg($('#m-check'), e.message); btn.disabled = false; }
    });
    $('#body').addEventListener('click', async ev => {
      const b = ev.target.closest('[data-close],[data-resend]'); if (!b) return;
      b.disabled = true;
      try {
        if (b.dataset.close) await A.rest(`safety_checks?id=eq.${b.dataset.close}`, { method: 'PATCH', body: { status: 'closed' } });
        if (b.dataset.resend) { const r = await A.fn('safety-push', { check_id: b.dataset.resend }); msg($('#m-list'), `Relance : ${r.sent || 0} appareil(s).`, 'ok'); }
        await load(); render();
      } catch (e) { msg($('#m-list'), e.message); b.disabled = false; }
    });
  }
  const listHtml = () => checks.length ? checks.map(checkCard).join('') : '<p class="hint">Aucun safety check.</p>';
  function checkCard(c) {
    const t = targetsOf(c), resp = responses.filter(r => r.check_id === c.id), byU = Object.fromEntries(resp.map(r => [r.user_id, r]));
    const n = k => resp.filter(r => r.status === k).length;
    const noAns = t.filter(u => !byU[u.id]);
    const open = c.status === 'open' && new Date(c.expires_at) > new Date();
    const L = { safe: ['En sécurité', 'approved'], help: ['Besoin d\'aide', 'rejected'], not_concerned: ['Pas concerné', ''] };
    const rows = t.map(u => ({ u, r: byU[u.id] })).concat(resp.filter(r => !t.some(u => u.id === r.user_id)).map(r => ({ u: users.find(x => x.id === r.user_id) || { full_name: '?' }, r })))
      .sort((a, b) => (a.r ? (a.r.status === 'help' ? 0 : 2) : 1) - (b.r ? (b.r.status === 'help' ? 0 : 2) : 1));
    return `<div class="check-card"><div class="h"><strong>${esc(c.title)}</strong><span><span class="pill ${open ? 'pending' : ''}">${open ? 'en cours' : 'clôturé'}</span></span></div>
      <div class="hint">${esc(areaLabel(c.area))}${c.organization ? ' · ' + esc(c.organization) : ''} · envoyé le ${fmt(c.created_at)} · jusqu'au ${fmt(c.expires_at)}</div>
      ${c.message ? `<p>${esc(c.message)}</p>` : ''}
      <div class="stats" style="margin:8px 0"><div class="stat"><div class="n">${t.length}</div><div class="l">concernés</div></div>
        <div class="stat"><div class="n" style="color:var(--ok)">${n('safe')}</div><div class="l">en sécurité</div></div>
        <div class="stat"><div class="n" style="color:var(--bad)">${n('help')}</div><div class="l">besoin d'aide</div></div>
        <div class="stat"><div class="n">${noAns.length}</div><div class="l">sans réponse</div></div></div>
      ${rows.length ? `<details${n('help') ? ' open' : ''}><summary>Détail par personne</summary><table class="t resp"><tbody>${rows.map(({ u, r }) => `<tr><td><strong>${esc(u.full_name || u.email)}</strong><br><span class="hint">${esc(u.organization || '')}${u.phone ? ' · <a href="tel:' + esc(u.phone) + '">' + esc(u.phone) + '</a>' : ''}</span></td>
        <td>${r ? `<span class="pill ${L[r.status][1]}">${L[r.status][0]}</span><br><span class="hint">${fmt(r.updated_at || r.created_at)}${r.lat != null ? ` · <a href="index.html?m=${r.lat},${r.lon},11" target="_blank">position</a>` : ''}</span>${r.note ? '<br>' + esc(r.note) : ''}` : '<span class="hint">sans réponse</span>'}</td></tr>`).join('')}</tbody></table></details>` : ''}
      ${open ? `<div class="row" style="margin-top:8px"><button class="btn small" data-resend="${c.id}">Relancer les notifications</button><button class="btn small" data-close="${c.id}">Clôturer</button></div>` : ''}</div>`;
  }

  /* ------------------------------------------------ démarrage */
  async function start() {
    if (!A || !A.enabled) { main.innerHTML = '<div class="card"><h2>Comptes pas encore activés</h2><p>Voir le guide de mise en ligne, partie H.</p></div>'; return; }
    if (!A.session) { location.href = 'compte.html'; return; }
    try { me = await A.profile(); } catch (e) { me = null; }
    if (!me || me.role !== 'admin' || me.status !== 'approved') { main.innerHTML = '<div class="card"><h2>Accès réservé</h2><p>Cette page est réservée aux administrateurs validés.</p><a class="btn" href="compte.html">Mon compte</a></div>'; return; }
    try { await load(); render(); } catch (e) { main.innerHTML = `<div class="card"><div class="msg err">${esc(e.message)}</div></div>`; return; }
    clearInterval(timer);
    // suivi en direct des réponses : seule la liste est rafraîchie (le formulaire en cours n'est pas effacé)
    timer = setInterval(async () => { if (tab === 'checks' && $('#checks-list')) { try { await load(); $('#checks-list').innerHTML = listHtml(); } catch (e) { /* réseau */ } } }, 30000);
  }
  start();
})();
