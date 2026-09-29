/**
 * Relais IA d'angor.fr (Cloudflare Worker, offre gratuite) : « My travel buddy », avis go/no-go, synthèse du brief.
 * La carte envoie { task: "buddy" | "gonogo" | "brief", q, context, history, lang }.
 *
 * Le site est statique : il ne peut pas cacher de clé. Ce petit relais garde la clé Anthropic
 * côté serveur, n'accepte que les requêtes venant d'angor.fr, limite le nombre de questions par jour
 * (global et par visiteur) et transmet à Claude la question + le contexte Angor préparé par la carte.
 *
 * Installation (10 min) : voir GUIDE_MISE_EN_LIGNE.md, partie E.
 * Variables du Worker (Settings → Variables and Secrets) :
 *   ANTHROPIC_API_KEY  (secret)            clé Anthropic
 *   ALLOWED_ORIGINS    https://angor.fr,https://www.angor.fr
 *   DAILY_LIMIT        150   questions par jour, tous visiteurs confondus (≈ 1 $/jour maximum)
 *   USER_LIMIT         20    questions par jour et par visiteur
 *   MODEL              claude-haiku-4-5
 * Liaison KV facultative mais recommandée (Settings → Bindings → KV namespace) : nom QUOTA.
 */
const SYSTEM = `Tu es « My travel buddy », l'assistant de sûreté voyage d'Angor Intelligence (conseil aux entreprises
et voyageurs d'affaires). Réponds dans la langue de la question, de façon concrète, structurée et brève
(250 mots maximum, titres courts et puces).
Règles :
- Appuie-toi d'abord sur le CONTEXTE ANGOR fourni (avis MEAE/FCDO/US, incidents récents, fiches culturelles,
  urgences, hôpitaux, prestataires). Cite tes appuis entre crochets : [MEAE], [FCDO], [US], [Incidents Angor],
  [Fiche pays], [Wikidata], [Prestataires].
- Tu peux compléter par des connaissances générales bien établies (ex. vaccins usuels, bonnes pratiques de
  sûreté des trajets) en l'indiquant « [connaissance générale] » ; pour la santé, renvoie vers un centre de
  vaccinations internationales / médecin du voyage.
- N'invente jamais d'incident, de chiffre, de numéro, de nom de prestataire ou de contact. Si le contexte ne
  suffit pas, dis-le et indique où vérifier (MEAE, ambassade, assisteur).
- Pour un trajet : timing (jour), mode (vol intérieur / route), véhicule et chauffeur, convoi/escorte selon le
  niveau de risque, points de contact, plan B, prestataires listés dans le contexte.
- Refuse poliment toute demande illégale, d'atteinte à des personnes ou sans rapport avec le voyage et la sûreté.
- Termine par une ligne « À vérifier avant décision » si la situation est évolutive.`;

// Autres tâches demandées par la carte (même relais, même quota)
const TASKS = {
  buddy: { system: SYSTEM, max_tokens: 900 },
  gonogo: { max_tokens: 700, system: `Tu es le responsable sûreté d'Angor Intelligence. On te donne une évaluation go/no-go
déjà calculée (menace, vulnérabilité, décision, conditions) et le contexte Angor du pays. Rédige un avis motivé de
120 mots maximum, en français (ou dans la langue demandée) : décision recommandée, 2 ou 3 raisons principales tirées
du contexte (cite [MEAE], [FCDO], [US], [Incidents Angor], [Agenda]), conditions indispensables avant le départ.
Ne contredis pas la décision calculée sauf incohérence manifeste, que tu signales alors explicitement.
N'invente aucun fait. Termine par « Avis indicatif – décision finale : responsable sûreté / direction. »` },
  brief: { max_tokens: 600, system: `Tu es analyste sûreté chez Angor Intelligence. À partir du CONTEXTE ANGOR fourni,
rédige la synthèse d'un brief de mission : 4 à 6 phrases (110 mots maximum), factuelles, sans liste, sur la
situation sécuritaire de la destination et de la ville pour les dates indiquées, les points d'attention et la
posture recommandée. Cite tes appuis entre crochets. N'invente rien.` },
};

const json = (obj, status, headers) => new Response(JSON.stringify(obj), { status, headers: { ...headers, 'Content-Type': 'application/json' } });

export default {
  async fetch(req, env) {
    const origin = req.headers.get('Origin') || '';
    const allowed = (env.ALLOWED_ORIGINS || 'https://angor.fr,https://www.angor.fr').split(',').map(s => s.trim());
    const cors = { 'Access-Control-Allow-Origin': allowed.includes(origin) ? origin : allowed[0],
      'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type', Vary: 'Origin' };
    if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
    if (req.method !== 'POST' || !allowed.includes(origin)) return json({ error: 'forbidden' }, 403, cors);

    let body;
    try { body = await req.json(); } catch (e) { return json({ error: 'bad_request' }, 400, cors); }
    const task = TASKS[body.task] ? body.task : 'buddy';
    const q = String(body.q || '').slice(0, 800).trim();
    const context = String(body.context || '').slice(0, 14000);
    const history = Array.isArray(body.history) ? body.history.slice(-4)
      .filter(m => m && (m.role === 'user' || m.role === 'assistant') && m.content)
      .map(m => ({ role: m.role, content: String(m.content).slice(0, 1500) })) : [];
    if (!q) return json({ error: 'empty' }, 400, cors);

    // quotas (si la liaison KV « QUOTA » existe)
    if (env.QUOTA) {
      const day = new Date().toISOString().slice(0, 10);
      const ip = req.headers.get('CF-Connecting-IP') || 'anon';
      const g = Number(await env.QUOTA.get('g:' + day) || 0);
      const u = Number(await env.QUOTA.get('u:' + day + ':' + ip) || 0);
      if (g >= Number(env.DAILY_LIMIT || 150)) return json({ error: 'daily_quota' }, 429, cors);
      if (u >= Number(env.USER_LIMIT || 20)) return json({ error: 'user_quota' }, 429, cors);
      await env.QUOTA.put('g:' + day, String(g + 1), { expirationTtl: 172800 });
      await env.QUOTA.put('u:' + day + ':' + ip, String(u + 1), { expirationTtl: 172800 });
    }

    // l'historique doit alterner user/assistant et commencer par user
    const msgs = [];
    for (const m of history) if (!msgs.length ? m.role === 'user' : msgs[msgs.length - 1].role !== m.role) msgs.push(m);
    if (msgs.length && msgs[msgs.length - 1].role === 'user') msgs.pop();
    msgs.push({ role: 'user', content: `CONTEXTE ANGOR (données du ${new Date().toISOString().slice(0, 10)}) :\n${context || '(aucun pays reconnu)'}\n\nQUESTION : ${q}` });

    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
      body: JSON.stringify({ model: env.MODEL || 'claude-haiku-4-5', max_tokens: TASKS[task].max_tokens, system: TASKS[task].system, messages: msgs }),
    });
    if (!r.ok) return json({ error: 'upstream_' + r.status }, 502, cors);
    const data = await r.json();
    const answer = (data.content || []).filter(c => c.type === 'text').map(c => c.text).join('\n').trim();
    return json({ answer, usage: data.usage || {} }, 200, cors);
  },
};
