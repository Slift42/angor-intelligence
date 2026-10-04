/* Angor Intelligence – service worker : application installable (Android, ordinateur), dernière situation
   consultable hors ligne, notifications de safety check.
   - pages, code et données : réseau d'abord, copie locale si pas de réseau ;
   - bibliothèques et icônes : copie locale d'abord ;
   - fonds de carte et API externes : jamais mis en cache ici. */
const CACHE = 'angor-v3';  // v3 : polices et drapeaux auto-hébergés, pages légales (v0.19)
const SHELL = ['./', 'index.html', 'app.css', 'app.js', 'gonogo.js', 'account.js', 'compte.html', 'aide.html', 'legal.html', 'vendor/fonts/fonts.css',
  'vendor/icons.js', 'vendor/leaflet/leaflet.js', 'vendor/leaflet/leaflet.css', 'vendor/markercluster/leaflet.markercluster.js',
  'vendor/markercluster/MarkerCluster.css', 'data/countries.js', 'data/data.js', 'manifest.webmanifest', 'icons/icon-192.png'];

self.addEventListener('install', ev => {
  ev.waitUntil(caches.open(CACHE).then(c => Promise.allSettled(SHELL.map(u => c.add(u)))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', ev => {
  ev.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', ev => {
  const req = ev.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;                         // tuiles, Supabase, IA : réseau direct
  const cacheFirst = /\/(vendor|icons)\//.test(url.pathname);
  if (cacheFirst) {
    // copie locale d'abord, mais par adresse complète : app.js?v=nouveau n'est jamais servi par une ancienne copie
    ev.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => { if (r.ok) put(req, r.clone(), true); return r; })));
    return;
  }
  ev.respondWith(fetch(req).then(r => { if (r.ok) put(req, r.clone()); return r; })
    .catch(() => caches.match(req, { ignoreSearch: true }).then(hit => hit || (req.mode === 'navigate' ? caches.match('index.html') : Response.error()))));
});
function put(req, res, keepSearch) {
  const u = new URL(req.url); if (!keepSearch) u.search = '';        // réseau d'abord : une seule copie par fichier
  caches.open(CACHE).then(c => c.put(u.toString(), res)).catch(() => {});
}

/* Notifications (safety check) : envoyées par la fonction Supabase « safety-push ». */
self.addEventListener('push', ev => {
  let d = {};
  try { d = ev.data ? ev.data.json() : {}; } catch (e) { d = { title: 'Angor Intelligence', body: ev.data ? ev.data.text() : '' }; }
  const opts = { body: d.body || '', icon: 'icons/icon-192.png', badge: 'icons/icon-192.png', tag: d.tag || 'angor',
    requireInteraction: !!d.check_id, data: d,
    actions: d.check_id ? [{ action: 'safe', title: 'Je suis en sécurité' }, { action: 'help', title: 'J\'ai besoin d\'aide' }] : [] };
  ev.waitUntil(self.registration.showNotification(d.title || 'Angor Intelligence', opts));
});
self.addEventListener('notificationclick', ev => {
  ev.notification.close();
  const d = ev.notification.data || {};
  let url = d.url || './';
  if (d.check_id) url = `./?safety=${encodeURIComponent(d.check_id)}${ev.action ? '&answer=' + ev.action : ''}`;
  ev.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    for (const c of list) if ('focus' in c) { c.navigate(url); return c.focus(); }
    return self.clients.openWindow(url);
  }));
});
