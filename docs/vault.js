/* Angor Intelligence – chargement des données (v0.22).
   En ligne, les données détaillées (incidents complets, fil, notes de risque, alerte précoce, rapports, fiches pays…) ne
   sont plus publiées sur le site : le robot les dépose dans le compartiment privé « angor-data » de Supabase
   (veille/vault.py), que la base ne laisse lire qu'aux comptes validés. Ce fichier :
   - décide du mode : « member » (compte validé : données du coffre), « pending » (compte en attente), « guest » (visiteur :
     carte allégée data/guest.js, ou page verrouillée), « local » (comptes non configurés ou usage sur le PC : fichiers de
     docs/data comme avant) ;
   - charge les fichiers demandés par la page (attribut data-need), puis lance le code de la page (AngorVault.ready) ;
   - sert les chargements différés (AngorVault.script) : rapports, fiches pays, archives, alerte précoce…
   Une copie des données réservées est gardée sur l'appareil (cache « angor-vault ») pour la consultation hors ligne ;
   elle est effacée à la déconnexion (account.js). */
(function () {
  'use strict';
  const me = document.currentScript;
  const CFG = window.VS_CONFIG || {};
  const A = window.AngorAccount;
  const BUCKET = CFG.vault && CFG.vault.bucket;
  const active = !!(BUCKET && A && A.enabled);
  // même liste que veille/vault.py (PUBLIC, PUBLIC_DIRS)
  const PUBLIC = new Set(['config.js', 'countries.js', 'legal.js', 'providers.js', 'cities.js', 'factbook.js', 'guides.js', 'guest.js']);
  const MISSING = { 'data.js': 'VS_DATA_MISSING', 'profiles.js': 'VS_PROFILES_MISSING', 'econ.js': 'VS_ECON_MISSING' };
  const need = ((me && me.dataset.need) || '').split(/\s+/).filter(Boolean);
  const guestFile = me && me.dataset.guest;
  const done = new Set();
  const queue = [];
  let started = false;

  const relOf = src => { const m = String(src).match(/(?:^|\/)data\/([^?#]+)/); return m ? m[1] : null; };
  const isPrivate = rel => !!rel && !PUBLIC.has(rel) && !rel.startsWith('history/');
  const runText = text => { (0, eval)(text); };   // fichier « window.VS_X = {...}; » exécuté dans la portée globale
  function tag(src) {
    return new Promise((ok, ko) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = ko; document.head.appendChild(s); });
  }
  async function cacheGet(rel) {
    try { const c = await caches.open('angor-vault'); const r = await c.match('/vault/' + rel); return r ? r.text() : null; } catch (e) { return null; }
  }
  function cachePut(rel, text) {
    try { caches.open('angor-vault').then(c => c.put('/vault/' + rel, new Response(text))).catch(() => {}); } catch (e) { /* stockage indisponible */ }
  }
  /** Texte d'un fichier réservé : coffre Supabase, ou copie locale si le réseau manque. */
  async function privText(rel) {
    try {
      const text = await A.storageText(BUCKET, rel);
      cachePut(rel, text);
      return text;
    } catch (e) {
      if (!e.status) { const c = await cacheGet(rel); if (c != null) { api.offline = true; return c; } }
      throw e;
    }
  }
  async function loadPrivate(rel) { runText(await privText(rel)); done.add(rel); }

  const api = {
    active, mode: active ? 'guest' : 'local', offline: false, error: null,
    /** Lance fn quand les données de la page sont prêtes (une seule fois). */
    ready(fn) { if (started) fn(); else queue.push(fn); },
    loaded(src) { return done.has(relOf(src)); },
    /** Chargement différé d'un fichier de données (public : balise script ; réservé : coffre, comptes validés). */
    script(src) {
      const rel = relOf(src);
      if (!active || !isPrivate(rel)) return tag(src);
      if (api.mode !== 'member') return Promise.reject(new Error('reserved'));
      if (done.has(rel)) return Promise.resolve();
      return loadPrivate(rel);
    },
    /** Texte brut d'un fichier de données (contrôle de fraîcheur du bouton Actualiser). */
    text(src) {
      const rel = relOf(src);
      if (active && isPrivate(rel)) return api.mode === 'member' ? A.storageText(BUCKET, rel) : Promise.reject(new Error('reserved'));
      return fetch(src + (src.includes('?') ? '&' : '?') + 't=' + Date.now(), { cache: 'no-store' }).then(r => r.text());
    },
    /** Page réservée (rapport, brief) ouverte sans compte validé : invitation à se connecter. */
    lock(pending) {
      const box = document.createElement('div');
      box.className = 'vault-lock';
      box.setAttribute('style', 'position:fixed;inset:0;z-index:99999;display:grid;place-items:center;padding:16px;background:rgba(13,24,40,.55);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);font:15px/1.5 Inter,system-ui,sans-serif');
      box.innerHTML = `<div style="max-width:420px;width:100%;background:#fff;color:#13263D;border-radius:16px;padding:24px;box-shadow:0 20px 60px rgba(0,0,0,.35)">
        <div style="font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#5E6B78">Angor Intelligence</div>
        <h2 style="margin:6px 0 8px;font-size:20px">${pending ? 'Compte en attente de validation' : 'Réservé aux comptes validés'}</h2>
        <p style="margin:0 0 16px;color:#3A4A5B">${pending ? 'Votre compte doit être validé par un administrateur avant d\'accéder aux rapports et aux analyses.'
          : 'Les rapports pays, briefs et analyses détaillées sont accessibles aux comptes validés. Connectez-vous ou créez un compte.'}</p>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><a href="compte.html" style="background:#13263D;color:#fff;padding:9px 14px;border-radius:9px;text-decoration:none;font-weight:600">${pending ? 'Mon compte' : 'Se connecter'}</a>
        ${pending ? '' : '<a href="compte.html?mode=signup" style="border:1px solid #CBD5E1;color:#13263D;padding:9px 14px;border-radius:9px;text-decoration:none;font-weight:600">Créer un compte</a>'}
        <a href="index.html" style="color:#13263D;padding:9px 6px;font-weight:600">Carte</a></div></div>`;
      document.body.appendChild(box);
    },
  };
  window.AngorVault = api;

  async function boot() {
    if (!active) {   // comptes non configurés ou fichiers locaux : comme avant
      await Promise.all(need.map(f => tag('data/' + f).then(() => done.add(f), () => { if (MISSING[f]) window[MISSING[f]] = true; })));
      return;
    }
    await Promise.all(need.filter(f => !isPrivate(f)).map(f => tag('data/' + f).then(() => done.add(f), () => {})));
    const priv = need.filter(isPrivate);
    if (A.session && priv.length) {
      try {
        await loadPrivate(priv[0]);          // le premier fichier tranche : la base ne le donne qu'à un compte validé
        api.mode = 'member';
      } catch (e) {
        // refus (400/403/404) : compte pas encore validé, ou données pas encore publiées par le robot
        let p = null;
        try { p = await A.profile(); } catch (x) { p = null; }
        if (p && (p.status === 'approved' || p.role === 'admin')) { api.mode = 'member'; api.error = 'unpublished'; if (MISSING[priv[0]]) window[MISSING[priv[0]]] = true; }
        else api.mode = p ? 'pending' : 'guest';
      }
      if (api.mode === 'member') {
        await Promise.all(priv.slice(1).map(f => loadPrivate(f).catch(() => { if (MISSING[f]) window[MISSING[f]] = true; })));
      }
    } else if (A.session && !priv.length) {
      api.mode = 'member';
    }
    if (api.mode !== 'member') {
      if (guestFile) await tag('data/' + guestFile).catch(() => { window.VS_DATA_MISSING = true; });
      else { started = true; api.lock(api.mode === 'pending'); return; }   // page réservée : le code de la page ne démarre pas
    }
  }
  function go() { started = true; queue.splice(0).forEach(fn => { try { fn(); } catch (e) { setTimeout(() => { throw e; }); } }); }
  boot().then(() => { if (!document.querySelector('.vault-lock')) go(); }, () => go());
})();
