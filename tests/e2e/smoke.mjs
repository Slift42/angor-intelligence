// Test de fumée du site : chaque page se charge sans erreur JavaScript, sur ordinateur et sur mobile,
// et les parcours principaux répondent (espaces, période, fiche pays, analyses, trafic, rapport pays).
// Usage (depuis la racine du dépôt) :
//   cd tests/e2e && npm install && npx playwright install chromium && npm test
// Le site est servi depuis docs/ par un petit serveur local lancé ici ; aucune donnée n'est requise
// (sans docs/data/data.js, les pages doivent afficher leur état « vide » sans planter).
import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const DOCS = normalize(process.env.DOCS_DIR || join(fileURLToPath(import.meta.url), '../../../docs'));
const TYPES = { '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.webmanifest': 'application/manifest+json', '.geojson': 'application/json' };
const server = createServer(async (req, res) => {
  const path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const file = normalize(join(DOCS, path === '/' ? 'index.html' : path));
  if (!file.startsWith(DOCS)) { res.writeHead(403); return res.end(); }
  try { const body = await readFile(file); res.writeHead(200, { 'content-type': TYPES[extname(file)] || 'application/octet-stream' }); res.end(body); }
  catch { res.writeHead(404); res.end(); }
}).listen(0);
const BASE = `http://localhost:${server.address().port}`;

const failures = [];
const check = (ok, msg) => { if (!ok) failures.push(msg); console.log(`${ok ? '✓' : '✗'} ${msg}`); };
const browser = await chromium.launch();

async function page(url, viewport, steps = async () => {}) {
  const p = await browser.newPage({ viewport });
  const errors = [];
  p.on('pageerror', e => errors.push(e.message));
  await p.route(/^https?:\/\/(?!localhost)/, r => r.abort());   // pas d'Internet : tuiles, polices, API
  await p.goto(BASE + url, { waitUntil: 'load' });
  await p.waitForTimeout(800);
  try { await steps(p); } catch (e) { errors.push('parcours : ' + e.message); }
  const width = await p.evaluate(() => document.documentElement.scrollWidth);
  await p.close();
  return { errors, width };
}

for (const [name, viewport] of [['ordinateur', { width: 1400, height: 900 }], ['mobile', { width: 390, height: 800 }]]) {
  const desktop = viewport.width > 860;
  let r = await page('/index.html', viewport, async p => {
    // sans collecte (docs/data/data.js absent), la carte affiche un état vide : seul le chargement est testé
    if (!desktop || !(await p.evaluate(() => !!window.VS_DATA))) return;
    for (const sp of ['veille', 'pays', 'sites', 'anticipation', 'trafic']) await p.click(`.tabs button[data-space="${sp}"]`);
    await p.click('#period-btn'); await p.click('#period-menu button[data-h="168"]');
    await p.click('.tabs button[data-space="veille"]');
    await p.click('#btn-analytics'); await p.click('#af-group-btn');
  });
  check(!r.errors.length, `carte (${name}) sans erreur ${r.errors.join(' | ')}`);
  check(r.width <= viewport.width, `carte (${name}) sans défilement horizontal (${r.width}px)`);
  for (const url of ['/report.html#FR', '/report.html#ML/villes', '/brief.html#FR', '/aide.html', '/compte.html']) {
    r = await page(url, viewport);
    check(!r.errors.length, `${url} (${name}) sans erreur ${r.errors.join(' | ')}`);
  }
  // pages légales : sans erreur, sans défilement horizontal, champs à compléter signalés plutôt que vides
  for (const url of ['/legal.html', '/mentions-legales.html', '/cgu.html', '/cgv.html', '/confidentialite.html', '/sous-traitance.html', '/licences.html']) {
    let empty = 0;
    r = await page(url, viewport, async p => { empty = await p.evaluate(() => [...document.querySelectorAll('[data-v]')].filter(e => !e.textContent.trim()).length); });
    check(!r.errors.length && !empty && r.width <= viewport.width, `${url} (${name}) ${r.errors.join(' | ')}${empty ? ` ${empty} champ(s) vide(s)` : ''}${r.width > viewport.width ? ` largeur ${r.width}px` : ''}`);
  }
}
await browser.close();
server.close();
if (failures.length) { console.error(`\n${failures.length} échec(s)`); process.exit(1); }
console.log('\nTout est vert.');
