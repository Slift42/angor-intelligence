/* Angor Intelligence – comptes utilisateurs (client léger Supabase : Auth + REST, sans dépendance).
   Utilisé par la carte, compte.html et admin.html. Configuration : window.VS_CONFIG.accounts
   (docs/data/config.js, écrit par le robot à partir de config/settings.json → "accounts").
   Sans configuration, AngorAccount.enabled = false et l'outil fonctionne comme avant (sans compte). */
(function () {
  'use strict';
  const CFG = ((window.VS_CONFIG || {}).accounts) || ((window.VS_DATA || {}).settings || {}).accounts || {};
  const URL0 = (CFG.supabase_url || '').replace(/\/$/, '');
  const KEY = CFG.supabase_anon_key || '';
  const enabled = !!(URL0 && KEY);
  const SKEY = 'angor-session';
  const listeners = [];
  let session = null;
  try { session = JSON.parse(localStorage.getItem(SKEY)); } catch (e) { session = null; }

  function save(s) {
    session = s;
    try { s ? localStorage.setItem(SKEY, JSON.stringify(s)) : (localStorage.removeItem(SKEY), localStorage.removeItem('vs-member')); } catch (e) { /* stockage indisponible */ }
    if (!s && window.caches) caches.delete('angor-vault').catch(() => {});   // copie hors ligne des données réservées
    listeners.forEach(f => { try { f(s); } catch (e) { /* écouteur en erreur */ } });
  }
  const encPath = p => String(p).split('/').map(encodeURIComponent).join('/');
  const pageUrl = name => location.origin + location.pathname.replace(/[^/]*$/, '') + name;
  function fromToken(j) {
    return { access_token: j.access_token, refresh_token: j.refresh_token, expires_at: Date.now() + (j.expires_in || 3600) * 1000, user: j.user };
  }
  async function http(path, opt = {}) {
    const headers = Object.assign({ apikey: KEY, 'Content-Type': 'application/json' }, opt.headers || {});
    if (opt.auth !== false && session && session.access_token) headers.Authorization = 'Bearer ' + session.access_token;
    const r = await fetch(URL0 + path, { method: opt.method || 'GET', headers, body: opt.body ? JSON.stringify(opt.body) : undefined });
    const text = await r.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch (e) { data = text; }
    if (!r.ok) {
      const msg = (data && (data.msg || data.message || data.error_description || data.error)) || ('HTTP ' + r.status);
      const err = new Error(translate(msg)); err.status = r.status; err.raw = msg; throw err;
    }
    return data;
  }
  function translate(m) {
    const s = String(m);
    if (/invalid login credentials/i.test(s)) return 'E-mail ou mot de passe incorrect.';
    if (/email not confirmed/i.test(s)) return 'Adresse e-mail non confirmée : cliquez sur le lien reçu par e-mail.';
    if (/already registered|already exists/i.test(s)) return 'Un compte existe déjà avec cette adresse.';
    if (/password should be at least|weak password/i.test(s)) return 'Mot de passe trop faible (10 caractères minimum, lettres et chiffres).';
    if (/rate limit/i.test(s)) return 'Trop de tentatives : réessayez dans quelques minutes.';
    if (/error sending (confirmation|recovery|magic link|invite)/i.test(s))
      return 'L\'e-mail de confirmation n\'a pas pu être envoyé (service d\'envoi d\'e-mails pas encore opérationnel). Réessayez plus tard ou contactez l\'administrateur.';
    return s;
  }
  async function fresh() {
    if (!session) return null;
    if (Date.now() < session.expires_at - 60000) return session;
    try { save(fromToken(await http('/auth/v1/token?grant_type=refresh_token', { method: 'POST', auth: false, body: { refresh_token: session.refresh_token } }))); }
    catch (e) { save(null); }
    return session;
  }
  async function rest(path, opt = {}) {
    await fresh();
    const headers = Object.assign({}, opt.headers || {});
    if (opt.method && opt.method !== 'GET') headers.Prefer = headers.Prefer || 'return=representation';
    return http('/rest/v1/' + path, Object.assign({}, opt, { headers }));
  }

  const api = {
    enabled, config: CFG,
    get session() { return session; },
    get user() { return session && session.user; },
    onChange(f) { listeners.push(f); },
    async signUp(email, password, meta) {
      // versions des conditions acceptées dans le formulaire : enregistrées à la création du compte (preuve horodatée)
      const type = (meta && meta.account_type) || 'client';
      const data = Object.assign({ accepted: Object.fromEntries(api.legalRequired(type).map(r => [r.doc, r.version])) }, meta || {});
      const j = await http('/auth/v1/signup?redirect_to=' + encodeURIComponent(pageUrl('compte.html')), { method: 'POST', auth: false, body: { email, password, data } });
      if (j && j.access_token) save(fromToken(j));
      return j;
    },
    async signIn(email, password) {
      save(fromToken(await http('/auth/v1/token?grant_type=password', { method: 'POST', auth: false, body: { email, password } })));
      return session;
    },
    async signOut() { try { await http('/auth/v1/logout', { method: 'POST' }); } catch (e) { /* déjà expirée */ } save(null); },
    // lien de l'e-mail → compte.html (l'adresse doit figurer dans Supabase → Authentication → URL Configuration → Redirect URLs)
    recover(email) { return http('/auth/v1/recover?redirect_to=' + encodeURIComponent(pageUrl('compte.html')), { method: 'POST', auth: false, body: { email } }); },
    async setPassword(password) { await fresh(); return http('/auth/v1/user', { method: 'PUT', body: { password } }); },
    /** Lien de récupération (#access_token=…&type=recovery) : ouvre une session temporaire. */
    consumeHash() {
      const h = new URLSearchParams(location.hash.slice(1));
      if (!h.get('access_token')) return null;
      save({ access_token: h.get('access_token'), refresh_token: h.get('refresh_token'), expires_at: Date.now() + (+h.get('expires_in') || 3600) * 1000, user: null });
      history.replaceState(null, '', location.pathname + location.search);
      return h.get('type');
    },
    async profile() {
      if (!(await fresh())) return null;
      const uid = session.user && session.user.id || JSON.parse(atob(session.access_token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).sub;
      const rows = await rest(`profiles?id=eq.${uid}&select=*`);
      return rows && rows[0] || null;
    },
    async updateProfile(patch) {
      const p = await api.profile();
      const rows = await rest(`profiles?id=eq.${p.id}`, { method: 'PATCH', body: patch });
      return rows && rows[0];
    },
    rest,
    rpc(fn, args) { return rest('rpc/' + fn, { method: 'POST', body: args || {}, headers: { Prefer: 'return=representation' } }); },
    async fn(name, body) { await fresh(); return http('/functions/v1/' + name, { method: 'POST', body }); },
    /* ---- fichiers (Supabase Storage) : photos publiques « provider-media », justificatifs privés « provider-docs » ---- */
    async upload(bucket, path, file) {
      await fresh();
      const r = await fetch(`${URL0}/storage/v1/object/${bucket}/${encPath(path)}`, { method: 'POST', body: file,
        headers: { apikey: KEY, Authorization: 'Bearer ' + session.access_token, 'x-upsert': 'true', 'Content-Type': file.type || 'application/octet-stream' } });
      if (!r.ok) {
        let m = 'HTTP ' + r.status; try { const j = await r.json(); m = j.message || j.error || m; } catch (e) { /* */ }
        throw new Error(/size|large/i.test(m) ? 'Fichier trop volumineux.' : /mime|type/i.test(m) ? 'Format de fichier non accepté.' : translate(m));
      }
      return path;
    },
    publicUrl(bucket, path) { return `${URL0}/storage/v1/object/public/${bucket}/${encPath(path)}`; },
    async signedUrl(bucket, path, expiresIn) {
      await fresh();
      const j = await http(`/storage/v1/object/sign/${bucket}/${encPath(path)}`, { method: 'POST', body: { expiresIn: expiresIn || 300 } });
      return URL0 + '/storage/v1' + (j.signedURL || j.signedUrl);
    },
    /** Fichier privé (coffre des données réservées) lu avec le jeton de session : texte, ou erreur avec .status. */
    async storageText(bucket, path) {
      if (!(await fresh())) { const e = new Error('session'); e.status = 401; throw e; }
      const r = await fetch(`${URL0}/storage/v1/object/authenticated/${bucket}/${encPath(path)}`,
        { headers: { apikey: KEY, Authorization: 'Bearer ' + session.access_token }, cache: 'no-store' });
      if (!r.ok) { const e = new Error('HTTP ' + r.status); e.status = r.status; throw e; }
      return r.text();
    },
    async removeFile(bucket, path) { await fresh(); return http(`/storage/v1/object/${bucket}`, { method: 'DELETE', body: { prefixes: [path] } }); },
    async deleteAccount() { await api.rpc('delete_my_account'); save(null); },
    /* ---- conditions (CGU, confidentialité) : versions publiées dans docs/data/legal.js (config/legal.json) ----
       Tant que les textes sont au statut « projet », la version enregistrée porte le suffixe « -projet » : l'acceptation
       de la version définitive sera donc redemandée lors du passage « en vigueur ». */
    legalInForce() { return !!(window.VS_LEGAL && window.VS_LEGAL.status === 'en vigueur'); },
    /** Documents à accepter pour un type de compte (« pour » dans config/legal.json : réservé à ce type). */
    legalRequired(type) {
      const LG = window.VS_LEGAL;
      if (!LG || !LG.documents) return [];
      return Object.entries(LG.documents).filter(([, d]) => d.acceptation && (!d.pour || d.pour === (type || 'client')))
        .map(([doc, d]) => ({ doc, titre: d.titre, page: d.page, version: LG.status === 'en vigueur' ? d.version : d.version + '-projet' }));
    },
    async legalAccepted() { const p = await api.profile(); return (await rest(`legal_acceptances?user_id=eq.${p.id}&select=doc,version,accepted_at&order=accepted_at.desc`)) || []; },
    async legalMissing(type) {
      const req = api.legalRequired(type);
      if (!req.length) return [];
      const rows = await api.legalAccepted();
      return req.filter(r => !rows.some(x => x.doc === r.doc && x.version === r.version));
    },
    async acceptLegal(list) { for (const r of list) await api.rpc('accept_legal', { p_doc: r.doc, p_version: r.version }); },
    /** Un safety check concerne-t-il ce profil ? (même règle que la fonction d'envoi) */
    concerned(check, p) {
      const a = check.area || { type: 'all' }, loc = p.location || {}, prefs = p.prefs || {};
      if (check.organization && (p.organization || '').toLowerCase() !== check.organization.toLowerCase()) return false;
      if (a.type === 'all') return true;
      if (a.type === 'country') return loc.iso === a.iso || prefs.base_country === a.iso || (prefs.travel_countries || []).includes(a.iso);
      if (a.type === 'circle') {
        if (loc.lat == null) return false;
        const r = Math.PI / 180, x = Math.sin((loc.lat - a.lat) * r / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(loc.lat * r) * Math.sin((loc.lon - a.lon) * r / 2) ** 2;
        return 2 * 6371 * Math.asin(Math.sqrt(x)) <= (a.radius_km || 50);
      }
      return false;
    },
    async openChecks() {
      const now = new Date().toISOString();
      return rest(`safety_checks?status=eq.open&expires_at=gt.${encodeURIComponent(now)}&select=*&order=created_at.desc`);
    },
    async myResponses() { const p = await api.profile(); return rest(`safety_responses?user_id=eq.${p.id}&select=*`); },
    async respond(checkId, status, note, pos) {
      const p = await api.profile();
      const body = { check_id: checkId, user_id: p.id, status, note: note || null };
      if (pos && p.consent_location) { body.lat = pos.lat; body.lon = pos.lon; }
      return rest('safety_responses?on_conflict=check_id,user_id', { method: 'POST', body, headers: { Prefer: 'resolution=merge-duplicates,return=representation' } });
    },
    /** Abonnement aux notifications (Web Push) sur cet appareil. */
    async subscribePush() {
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) throw new Error('Notifications non prises en charge par ce navigateur.');
      if (!CFG.vapid_public_key) throw new Error('Notifications pas encore configurées (clé VAPID manquante).');
      const perm = await Notification.requestPermission();
      if (perm !== 'granted') throw new Error('Notifications refusées dans le navigateur.');
      const reg = await navigator.serviceWorker.ready;
      const key = Uint8Array.from(atob(CFG.vapid_public_key.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - CFG.vapid_public_key.length % 4) % 4)), c => c.charCodeAt(0));
      const sub = (await reg.pushManager.getSubscription()) || await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key });
      const j = sub.toJSON(), p = await api.profile();
      await rest('push_subscriptions?on_conflict=endpoint', { method: 'POST', headers: { Prefer: 'resolution=merge-duplicates,return=minimal' },
        body: { endpoint: j.endpoint, user_id: p.id, p256dh: j.keys.p256dh, auth: j.keys.auth, user_agent: navigator.userAgent.slice(0, 200) } });
      return true;
    },
    async unsubscribePush() {
      const reg = await navigator.serviceWorker.ready, sub = await reg.pushManager.getSubscription();
      if (sub) { await rest(`push_subscriptions?endpoint=eq.${encodeURIComponent(sub.endpoint)}`, { method: 'DELETE' }).catch(() => {}); await sub.unsubscribe(); }
    },
  };
  window.AngorAccount = api;
})();
