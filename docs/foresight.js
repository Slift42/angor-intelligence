/* Angor Intelligence – onglet « Tendances · alerte précoce » (espace Anticipation), v0.27 : un seul outil, trois
   niveaux de détail, sur les 17 régions du monde :
   - région et pays : tendances de risques (évaluées, sourcées) et indicateurs structurels (FMI, Banque mondiale, BCE) ;
   - subdivisions : alerte précoce (ew.js), indice de convergence par région administrative.
   Données : docs/data/foresight.js (window.VS_FS, veille/foresight.py) ; alerte précoce chargée par ew.js.
   Méthode publique : docs/methodologie.html. Branché sur la carte par app.js : window.AngorFS.init(bridge) puis open() / close(). */
(function () {
  'use strict';
  let B = null, layer = null, loading = null;
  const S = { scope: 'weu', view: 'trends', audience: 'all', horizon: 'all', family: 'all', selected: null };
  try { Object.assign(S, JSON.parse(localStorage.getItem('vs-fs') || '{}'), { selected: null }); } catch (e) { /* stockage indisponible */ }
  const save = () => { try { localStorage.setItem('vs-fs', JSON.stringify({ scope: S.scope, view: S.view, audience: S.audience, horizon: S.horizon, family: S.family })); } catch (e) { /* idem */ } };

  const TXT = {
    fr: {
      hint: 'Les risques susceptibles d’affecter vos activités et vos voyageurs, du plus large au plus fin : tendances par région et par pays (climat, géopolitique, politique, société, économie, finances, cyber…), évaluées, sourcées et assorties d’indicateurs d’alerte, puis alerte précoce par subdivision.',
      scope: 'Périmètre', region: 'région', country_own: 'fiche pays', country_inh: 'tendances régionales', audience: 'Point de vue',
      a_all: 'Global', a_business: 'Entreprise', a_travel: 'Voyageur', horizon: 'Horizon', h_all: 'Tous', family: 'Famille', f_all: 'Toutes',
      pressure: 'Pression de risque', outlook: 'Perspective', reviewed: 'Revue le', families: 'Par famille de facteurs', matrix: 'Matrice vraisemblance × impact',
      likelihood: 'Vraisemblance', impact: 'Impact', impact_business: 'Impact entreprise', impact_travel: 'Impact voyageur', trends: 'Tendances',
      inherited: 'régional', own_country: 'national', no_trend: 'Aucune tendance pour ces filtres.', method: 'Méthode, échelles et sources',
      loading: 'Chargement des tendances…', missing: 'Tendances pas encore publiées : elles seront produites lors de la prochaine collecte.',
      not_described: 'Pas encore de fiche nationale : seules les tendances régionales s’appliquent.',
      roadmap: (a, n) => `Tendances rédigées : ${a} région(s) sur ${n} ; alerte précoce et indicateurs structurels : monde entier.`,
      score: 'Score', horizon_l: 'Horizon', momentum: 'Dynamique', confidence: 'Confiance', summary: 'Synthèse', signals: 'Signaux et faits datés',
      watch: 'Indicateurs d’alerte à surveiller', rupture: 'Scénario de rupture', implications: 'Implications', for_business: 'Pour l’entreprise',
      for_travel: 'Pour le voyageur', actions: 'Recommandations', sectors: 'Secteurs les plus exposés', drivers: 'Facteurs', links: 'Tendances liées',
      sources: 'Sources', history: 'Évolution du score', live: 'Signal en temps réel (incidents vérifiés)',
      live_txt: (n, base, days) => `${n} incident(s) sur ${days} jours, contre ${base} en moyenne sur les périodes précédentes.`,
      live_dir: { 1: 'nette hausse', 0: 'pas d’écart notable', '-1': 'nette baisse' },
      flag_review_due: d => `Révision due (le ${d}) : la fiche doit être relue.`,
      flag_live_up: 'Surprise : les incidents montent alors que la tendance n’était pas jugée en hausse. À réexaminer.',
      flag_live_down: 'Les incidents reculent alors que la tendance est jugée en hausse. À réexaminer.',
      rel: 'cotation', disclaimer: 'Aide à la décision : ces évaluations reposent sur des sources ouvertes à la date de revue et ne garantissent pas l’exhaustivité.',
      see_country: 'Voir la fiche pays', scope_region: 'Région', scope_country: 'Pays', whole_region: 'Toute la région',
      view: 'Niveau de détail', v_trends: 'Région et pays', v_ew: 'Subdivisions',
      no_trends_region: 'Tendances pas encore rédigées pour cette région : l’alerte précoce par subdivision et les indicateurs structurels sont déjà disponibles.',
      ew_sum: (n, h) => `Alerte précoce : ${n} subdivision(s) suivie(s), dont ${h} à niveau élevé ou très élevé.`, see_units: 'Voir les subdivisions',
      units: 'Subdivisions les plus exposées', units_hint: 'Alerte précoce : composante de l’indice correspondant à cette tendance.',
      ind_title: 'Indicateurs structurels', ind_src: 'FMI (Perspectives de l’économie mondiale, projections), Banque mondiale (indicateurs de gouvernance), BCE (taux souverains).',
      ind: { growth: 'Croissance du PIB', inflation: 'Inflation', debt: 'Dette publique (% du PIB)', unemployment: 'Chômage', stability: 'Stabilité politique (0–100)',
        effectiveness: 'Efficacité des pouvoirs publics (0–100)', rule_of_law: 'État de droit (0–100)', corruption: 'Maîtrise de la corruption (0–100)', yield: 'Taux souverain à 10 ans', spread: 'Écart avec l’Allemagne' },
      flags: { recession: 'Récession', high_inflation: 'Inflation forte', heavy_debt: 'Dette lourde', high_unemployment: 'Chômage élevé', unstable: 'Forte instabilité politique', spread: 'Tension sur les taux' },
      region_flags: 'Signaux structurels dans la région', bp: 'pb',
    },
    en: {
      hint: 'Risks likely to affect your operations and travellers, from the broadest to the finest level: trends by region and country (climate, geopolitics, politics, society, economy, finance, cyber…), assessed, sourced and with warning indicators, then early warning by subdivision.',
      scope: 'Scope', region: 'region', country_own: 'country sheet', country_inh: 'regional trends', audience: 'Point of view',
      a_all: 'Overall', a_business: 'Business', a_travel: 'Traveller', horizon: 'Horizon', h_all: 'All', family: 'Family', f_all: 'All',
      pressure: 'Risk pressure', outlook: 'Outlook', reviewed: 'Reviewed on', families: 'By driver family', matrix: 'Likelihood × impact matrix',
      likelihood: 'Likelihood', impact: 'Impact', impact_business: 'Business impact', impact_travel: 'Traveller impact', trends: 'Trends',
      inherited: 'regional', own_country: 'national', no_trend: 'No trend for these filters.', method: 'Method, scales and sources',
      loading: 'Loading trends…', missing: 'Trends not published yet: they will be produced at the next run.',
      not_described: 'No country sheet yet: only regional trends apply.',
      roadmap: (a, n) => `Trends written: ${a} region(s) out of ${n}; early warning and structural indicators: worldwide.`,
      score: 'Score', horizon_l: 'Horizon', momentum: 'Momentum', confidence: 'Confidence', summary: 'Summary', signals: 'Dated signals and facts',
      watch: 'Warning indicators to watch', rupture: 'Breakthrough scenario', implications: 'Implications', for_business: 'For the business',
      for_travel: 'For the traveller', actions: 'Recommendations', sectors: 'Most exposed sectors', drivers: 'Drivers', links: 'Related trends',
      sources: 'Sources', history: 'Score history', live: 'Real-time signal (verified incidents)',
      live_txt: (n, base, days) => `${n} incident(s) over ${days} days, against an average of ${base} over previous periods.`,
      live_dir: { 1: 'sharp rise', 0: 'no notable change', '-1': 'sharp fall' },
      flag_review_due: d => `Review due (on ${d}): this sheet needs re-reading.`,
      flag_live_up: 'Surprise: incidents are rising although the trend was not assessed as rising. Re-examine.',
      flag_live_down: 'Incidents are falling although the trend is assessed as rising. Re-examine.',
      rel: 'grade', disclaimer: 'Decision support: these assessments rely on open sources as of the review date and do not claim to be exhaustive.',
      see_country: 'Open the country sheet', scope_region: 'Region', scope_country: 'Country', whole_region: 'Whole region',
      view: 'Level of detail', v_trends: 'Region & country', v_ew: 'Subdivisions',
      no_trends_region: 'Trends not written yet for this region: early warning by subdivision and structural indicators are already available.',
      ew_sum: (n, h) => `Early warning: ${n} subdivision(s) tracked, ${h} at high or very high level.`, see_units: 'Show subdivisions',
      units: 'Most exposed subdivisions', units_hint: 'Early warning: index component matching this trend.',
      ind_title: 'Structural indicators', ind_src: 'IMF (World Economic Outlook, projections), World Bank (governance indicators), ECB (sovereign yields).',
      ind: { growth: 'GDP growth', inflation: 'Inflation', debt: 'Public debt (% of GDP)', unemployment: 'Unemployment', stability: 'Political stability (0–100)',
        effectiveness: 'Government effectiveness (0–100)', rule_of_law: 'Rule of law (0–100)', corruption: 'Control of corruption (0–100)', yield: '10-year sovereign yield', spread: 'Spread over Germany' },
      flags: { recession: 'Recession', high_inflation: 'High inflation', heavy_debt: 'Heavy debt', high_unemployment: 'High unemployment', unstable: 'Severe political instability', spread: 'Yield stress' },
      region_flags: 'Structural signals in the region', bp: 'bp',
    },
  };
  const LG = () => (B && B.lang() === 'en' ? 'en' : 'fr');
  const tx = k => (TXT[LG()] || TXT.fr)[k];
  const loc = o => (o ? (o[LG()] || o.fr || '') : '');
  const D = () => window.VS_FS;
  const ARROW = { 1: '↗', 0: '→', '-1': '↘' };
  const EW_COLORS = { 1: '#5FA37C', 2: '#E3B505', 3: '#EE7D22', 4: '#C0263B' };

  function lvl(key) { return D().scales.levels.find(l => l.key === key) || D().scales.levels[0]; }
  function sc(t) { return S.audience === 'business' ? t.score.business : S.audience === 'travel' ? t.score.travel : t.score.all; }
  function lv(t) { return S.audience === 'business' ? t.lvl_business : S.audience === 'travel' ? t.lvl_travel : t.lvl; }
  function scopeName(s) { return s.fr ? loc(s) : B.countryName(s.id); }
  function fmtDate(d) {
    if (!d) return '';
    const p = String(d).split('-');
    const dt = new Date(Date.UTC(+p[0], p[1] ? +p[1] - 1 : 0, p[2] ? +p[2] : 1, 12));
    return dt.toLocaleDateString(LG() === 'en' ? 'en-GB' : 'fr-FR', p.length === 3 ? { day: 'numeric', month: 'short', year: 'numeric' } : p.length === 2 ? { month: 'long', year: 'numeric' } : { year: 'numeric' });
  }

  /** Tendances applicables au périmètre choisi : pays = nationales + régionales ; région = régionales + nationales des pays membres */
  function pool() {
    const d = D(), s = d.scopes[S.scope]; if (!s) return [];
    let list;
    if (s.type === 'country') list = d.trends.filter(t => t.scope === s.id).map(t => ({ t, inh: false })).concat(d.trends.filter(t => t.scope === s.parent).map(t => ({ t, inh: true })));
    else list = d.trends.filter(t => t.scope === s.id).map(t => ({ t, inh: false })).concat(d.trends.filter(t => s.countries.includes(t.scope)).map(t => ({ t, inh: false, ctry: t.scope })));
    return list.filter(({ t }) => (S.horizon === 'all' || t.horizon === S.horizon) && (S.family === 'all' || t.family === S.family || (t.also || []).includes(S.family)))
      .sort((a, b) => sc(b.t) - sc(a.t) || b.t.likelihood - a.t.likelihood);
  }

  /* ------------------------------------------------------------------ carte : pays de la région colorés par niveau maximal */
  function regionOf(s) { return s.type === 'region' ? s : D().scopes[s.parent]; }
  function drawLayer() {
    const d = D(); if (!d || !window.VS_COUNTRIES) return;
    const reg = regionOf(d.scopes[S.scope]); if (!reg) return;
    const dark = B.theme() === 'dark';
    const feats = window.VS_COUNTRIES.features.filter(f => reg.countries.includes(f.properties.iso2));
    if (layer) B.map.removeLayer(layer);
    layer = L.geoJSON({ type: 'FeatureCollection', features: feats }, {
      pane: 'fsPane',
      style: f => {
        const cs = d.scopes[f.properties.iso2], key = cs && cs.summary ? cs.summary.max_lvl : 0, on = S.scope === f.properties.iso2;
        const ewl = !key && cs && cs.ew && cs.ew.top.length ? cs.ew.top[0][4] : 0;
        return { fillColor: key ? lvl(key).color : ewl ? EW_COLORS[ewl] : (dark ? '#2A3542' : '#D5DBE0'), fillOpacity: cs && cs.described ? 0.62 : 0.32,
          color: on ? (dark ? '#fff' : '#111B27') : (dark ? '#0D141C' : '#FFFFFF'), weight: on ? 2.4 : 0.8, dashArray: cs && cs.described ? null : '3 3' };
      },
      onEachFeature: (f, lyr) => {
        const iso = f.properties.iso2, cs = d.scopes[iso];
        lyr.on('click', ev => { L.DomEvent.stopPropagation(ev); setScope(iso); });
        lyr.bindTooltip(() => `<strong>${B.esc(B.countryName(iso))}</strong><br>${cs && cs.summary && cs.summary.n ? `${B.esc(tx('pressure'))} : ${cs.summary.pressure}/100 · ${B.esc(cs.described ? tx('country_own') : tx('country_inh'))}` : ''}${cs && cs.ew && cs.ew.n ? `<br>${B.esc(tx('ew_sum')(cs.ew.n, cs.ew.high))}` : ''}`,
          { sticky: true, className: 'vs-tip', direction: 'top', offset: [0, -8] });
      },
    }).addTo(B.map);
  }
  function fit() {
    const d = D(), s = d.scopes[S.scope]; if (!s) return;
    if (s.type === 'country' && window.VS_COUNTRIES) {
      const f = window.VS_COUNTRIES.features.find(x => x.properties.iso2 === s.id);
      if (f) { const b = L.geoJSON(f).getBounds(); if (s.id === 'FR') B.map.flyToBounds([[41.2, -5.3], [51.2, 9.7]], { padding: [20, 20], duration: 0.8 }); else B.map.flyToBounds(b, { padding: [30, 30], maxZoom: 7, duration: 0.8 }); return; }
    }
    const r = regionOf(s); if (r && r.bbox) B.map.flyToBounds([[r.bbox[1], r.bbox[0]], [r.bbox[3], r.bbox[2]]], { padding: [20, 20], duration: 0.8 });
  }
  function setScope(id) { S.scope = id; S.selected = null; save(); B.closeDrawer(); render(); if (S.view === 'trends') { drawLayer(); fit(); } }
  function setView(v) {
    S.view = v; save(); B.closeDrawer();
    if (v === 'ew') { if (layer) { B.map.removeLayer(layer); layer = null; } } else if (window.AngorEW) window.AngorEW.unmount();
    render(); if (v === 'trends') { drawLayer(); fit(); }
  }
  /** Région et pays du périmètre courant (pour l'alerte précoce) */
  function ewScope() {
    const s = D().scopes[S.scope], r = regionOf(s);
    return { region: r.id, country: s.type === 'country' ? s.id : null, bbox: r.bbox };
  }
  function fmtNum(v, unit) { return v == null ? '—' : `${Number(v).toLocaleString(LG() === 'en' ? 'en-GB' : 'fr-FR', { maximumFractionDigits: 1 })}${unit || ''}`; }
  function indicators(ind) {
    if (!ind) return '';
    const yr = String(new Date().getFullYear()), I = tx('ind'), rows = [];
    for (const k of ['growth', 'inflation', 'debt', 'unemployment']) {
      const vals = (ind.imf || {})[k]; if (!vals) continue;
      const y = vals[yr] != null ? yr : Object.keys(vals).sort().pop();
      rows.push([I[k], `${fmtNum(vals[y], ' %')} <span class="muted">(${y})</span>`]);
    }
    for (const k of ['stability', 'effectiveness', 'rule_of_law', 'corruption']) {
      const v = (ind.wgi || {})[k]; if (v) rows.push([I[k], `${fmtNum(v[0])} <span class="muted">(${B.esc(v[1])})</span>`]);
    }
    if (ind.yield) rows.push([I.yield, `${fmtNum(ind.yield[0], ' %')} <span class="muted">(${B.esc(ind.yield[1])})</span>`]);
    if (ind.spread != null) rows.push([I.spread, `${fmtNum(ind.spread)} ${tx('bp')}`]);
    if (!rows.length) return '';
    return `<div class="d-sec"><h3>${tx('ind_title')}</h3>${(ind.flags || []).length ? `<div class="fs-chips">${ind.flags.map(f => `<span class="chip warn">${B.esc(tx('flags')[f] || f)}</span>`).join('')}</div>` : ''}
      <ul class="mini-list fs-ind">${rows.map(([l, v]) => `<li><span class="t">${B.esc(l)}</span><span class="w">${v}</span></li>`).join('')}</ul><p class="hint">${tx('ind_src')}</p></div>`;
  }
  function regionFlags(s) {
    const d = D(), list = s.countries.map(c => d.scopes[c]).filter(c => c && c.ind && (c.ind.flags || []).length);
    if (!list.length) return '';
    return `<div class="d-sec"><h3>${tx('region_flags')}</h3><ul class="mini-list">${list.map(c => `<li data-scope="${c.id}"><span class="t">${B.flagImg(c.id)}${B.esc(B.countryName(c.id))}</span><span class="w">${c.ind.flags.map(f => B.esc(tx('flags')[f] || f)).join(' · ')}</span></li>`).join('')}</ul></div>`;
  }

  /* ------------------------------------------------------------------ panneau */
  function matrix(items) {
    const W = 300, P = 30, C = (W - P - 6) / 5, levels = D().scales.levels;
    const imp = t => (S.audience === 'business' ? t.impact.business : S.audience === 'travel' ? t.impact.travel : Math.max(t.impact.business, t.impact.travel));
    let cells = '';
    for (let l = 1; l <= 5; l++) for (let i = 1; i <= 5; i++) {
      const key = levels.find(x => l * i >= x.min && l * i <= x.max).key;
      cells += `<rect x="${P + (i - 1) * C}" y="${(5 - l) * C}" width="${C - 2}" height="${C - 2}" rx="4" fill="${lvl(key).color}" opacity="0.22"/>`;
    }
    const groups = {};
    items.forEach(({ t }, k) => { const key = `${t.likelihood}-${imp(t)}`; (groups[key] = groups[key] || []).push([t, k + 1]); });
    const dots = Object.entries(groups).map(([key, arr]) => {
      const [l, i] = key.split('-').map(Number);
      return arr.map(([t, n], j) => {
        const per = Math.min(arr.length, 3), row = Math.floor(j / 3), col = j % 3;
        const cx = P + (i - 1) * C + (C - 2) / 2 + (col - (per - 1) / 2) * 15, cy = (5 - l) * C + (C - 2) / 2 + (row - (Math.ceil(arr.length / 3) - 1) / 2) * 15;
        return `<g class="fs-dot" data-fs="${t.id}" tabindex="0" role="button" aria-label="${B.esc(loc(t.title))}"><circle cx="${cx}" cy="${cy}" r="7" fill="${lvl(lv(t)).color}" stroke="#fff" stroke-width="1.2"/><text x="${cx}" y="${cy + 3}" text-anchor="middle">${n}</text><title>${B.esc(loc(t.title))}</title></g>`;
      }).join('');
    }).join('');
    const ax = [1, 2, 3, 4, 5].map(n => `<text x="${P + (n - 1) * C + C / 2 - 1}" y="${5 * C + 12}" text-anchor="middle" class="ax">${n}</text><text x="${P - 8}" y="${(5 - n) * C + C / 2 + 3}" text-anchor="end" class="ax">${n}</text>`).join('');
    return `<figure class="fs-matrix"><figcaption>${B.esc(tx('matrix'))}</figcaption><svg viewBox="0 0 ${W} ${5 * C + 30}" role="img" aria-label="${B.esc(tx('matrix'))}">
      ${cells}${ax}<text x="${P + 2.5 * C}" y="${5 * C + 26}" text-anchor="middle" class="lab">${B.esc(S.audience === 'business' ? tx('impact_business') : S.audience === 'travel' ? tx('impact_travel') : tx('impact'))} →</text>
      <text x="8" y="${2.5 * C}" text-anchor="middle" class="lab" transform="rotate(-90 8 ${2.5 * C})">${B.esc(tx('likelihood'))} →</text>${dots}</svg></figure>`;
  }

  function render() {
    const el = document.getElementById('fs-body'); if (!el) return;
    const d = D();
    if (!d) { el.innerHTML = `<p class="hint">${loading ? tx('loading') : tx('missing')}</p>`; return; }
    if (!d.scopes[S.scope]) S.scope = Object.keys(d.scopes).find(k => d.scopes[k].type === 'region');
    const s = d.scopes[S.scope], items = pool(), sum = s.summary || {};
    const press = S.audience === 'business' ? sum.pressure_business : S.audience === 'travel' ? sum.pressure_travel : sum.pressure;
    const pkey = press >= 80 ? 5 : press >= 60 ? 4 : press >= 40 ? 3 : press >= 20 ? 2 : 1;
    const regions = Object.values(d.scopes).filter(x => x.type === 'region').sort((a, b) => (b.summary.n - a.summary.n) || loc(a).localeCompare(loc(b)));
    const opts = regions.map(r => `<optgroup label="${B.esc(loc(r))}"><option value="${r.id}"${r.id === S.scope ? ' selected' : ''}>${B.esc(loc(r))} · ${B.esc(tx('whole_region'))}</option>` +
      r.countries.map(c => d.scopes[c]).filter(Boolean).sort((a, b) => (b.described - a.described) || B.countryName(a.id).localeCompare(B.countryName(b.id)))
        .map(c => `<option value="${c.id}"${c.id === S.scope ? ' selected' : ''}>${B.esc(B.countryName(c.id))}${c.described ? ` · ${B.esc(tx('country_own'))}` : ''}</option>`).join('') + '</optgroup>').join('');
    const famOpts = Object.entries(d.families).map(([k, f]) => `<option value="${k}"${k === S.family ? ' selected' : ''}>${B.esc(loc(f))}</option>`).join('');
    const seg = (name, vals, cur) => `<div class="fs-seg" role="radiogroup" aria-label="${B.esc(tx(name))}">${vals.map(([v, l]) => `<button type="button" data-${name}="${v}" aria-pressed="${v === cur}">${B.esc(l)}</button>`).join('')}</div>`;
    const fams = Object.entries(sum.families || {}).slice(0, 8);
    const active = Object.values(d.scopes).filter(x => x.type === 'region' && x.summary && x.summary.own > 0).length;
    const ew = s.ew;
    const head = `
      <p class="hint">${tx('hint')}</p>
      <div class="ew-controls fs-controls">
        <label>${tx('scope')}<select id="fs-scope">${opts}</select></label>
        <label>${tx('family')}<select id="fs-family"${S.view === 'ew' ? ' disabled' : ''}><option value="all">${tx('f_all')}</option>${famOpts}</select></label>
      </div>
      <div class="fs-row"><span class="fs-lab">${tx('view')}</span>${seg('view', [['trends', tx('v_trends')], ['ew', tx('v_ew')]], S.view)}</div>`;
    const bind = () => {
      el.querySelector('#fs-scope').onchange = ev => setScope(ev.target.value);
      el.querySelector('#fs-family').onchange = ev => { S.family = ev.target.value; save(); render(); };
      el.querySelectorAll('[data-view]').forEach(b => { b.onclick = () => setView(b.dataset.view); });
      el.querySelectorAll('[data-audience]').forEach(b => { b.onclick = () => { S.audience = b.dataset.audience; save(); render(); }; });
      el.querySelectorAll('[data-horizon]').forEach(b => { b.onclick = () => { S.horizon = b.dataset.horizon; save(); render(); }; });
      el.querySelectorAll('[data-fam]').forEach(b => { b.onclick = () => { S.family = S.family === b.dataset.fam ? 'all' : b.dataset.fam; save(); render(); }; });
      el.querySelectorAll('[data-scope]').forEach(b => { b.onclick = () => setScope(b.dataset.scope); });
      el.querySelectorAll('#fs-see-units').forEach(b => { b.onclick = () => setView('ew'); });
      el.querySelectorAll('[data-fs]').forEach(x => {
        const go = () => { B.closePanelMobile(); select(x.dataset.fs); };
        x.onclick = go; x.onkeydown = ev => { if (ev.key === 'Enter') go(); };
      });
    };
    if (S.view === 'ew') {
      el.innerHTML = head + `<div id="fs-ew"></div>
        <p class="hint"><a href="methodologie.html#alerte-precoce" target="_blank" rel="noopener">${B.icon('book-open-text', 14)} ${tx('method')}</a></p>`;
      bind();
      if (window.AngorEW) window.AngorEW.mount(document.getElementById('fs-ew'), ewScope());
      return;
    }
    el.innerHTML = head + `
      <div class="fs-row"><span class="fs-lab">${tx('audience')}</span>${seg('audience', [['all', tx('a_all')], ['business', tx('a_business')], ['travel', tx('a_travel')]], S.audience)}</div>
      <div class="fs-row"><span class="fs-lab">${tx('horizon')}</span>${seg('horizon', [['all', tx('h_all')], ['3m', '0–3 m'], ['12m', '3–12 m'], ['36m', '1–3 a']], S.horizon)}</div>
      <div class="fs-outlook">
        ${sum.n ? `<div class="risk-big"><span class="lvl" style="background:${lvl(pkey).color}">${press ?? '—'}</span><div><div class="name">${B.esc(tx('pressure'))} · ${B.esc(scopeName(s))}</div>
          <div class="desc">${s.reviewed ? `${tx('reviewed')} ${B.esc(fmtDate(s.reviewed))} · ` : ''}${sum.n || 0} ${B.esc(tx('trends').toLowerCase())}</div></div></div>`
          : `<div class="name"><strong>${B.esc(scopeName(s))}</strong></div><p class="hint">${tx('no_trends_region')}</p>`}
        ${sum.n && s.type === 'country' && !s.described ? `<p class="hint">${tx('not_described')}</p>` : ''}
        ${s.outlook ? `<p class="fs-text">${B.esc(loc(s.outlook))}</p>` : ''}
        ${s['perimeter_' + LG()] ? `<p class="hint">${B.esc(s['perimeter_' + LG()])}</p>` : ''}
        ${ew && ew.n ? `<p class="fs-text">${B.esc(tx('ew_sum')(ew.n, ew.high))} <button type="button" class="btn small" id="fs-see-units">${B.icon('radar', 14)} ${tx('see_units')}</button></p>` : ''}
      </div>
      ${s.type === 'country' ? indicators(s.ind) : regionFlags(s)}
      ${fams.length ? `<div class="d-sec"><h3>${tx('families')}</h3><div class="fs-fams">${fams.map(([k, v]) => `<button type="button" class="fs-fam${k === S.family ? ' on' : ''}" data-fam="${k}"><span class="t">${B.esc(loc(d.families[k]))}</span><span class="track"><span class="fill" style="width:${v / 25 * 100}%;background:${lvl(d.scales.levels.find(x => v >= x.min && v <= x.max).key).color}"></span></span><span class="v">${v}</span></button>`).join('')}</div></div>` : ''}
      ${items.length ? matrix(items) : ''}
      ${sum.n ? `<div class="d-sec"><h3>${tx('trends')}</h3><ol class="fs-list">${items.map(({ t, inh, ctry }, k) => `
        <li data-fs="${t.id}"><span class="n" style="background:${lvl(lv(t)).color}">${k + 1}</span>
          <span class="body"><span class="t">${B.esc(loc(t.title))}</span>
          <span class="meta"><span class="chip">${B.esc(loc(d.families[t.family]))}</span><span>${B.esc(t.horizon === '3m' ? '0–3 m' : t.horizon === '12m' ? '3–12 m' : '1–3 a')}</span><span title="${B.esc(tx('momentum'))}">${ARROW[t.momentum]}</span>
          ${inh ? `<span class="chip ghost">${B.esc(tx('inherited'))}</span>` : ''}${ctry ? `<span class="chip ghost">${B.flagImg(ctry)}${B.esc(tx('own_country'))}</span>` : ''}
          ${t.flags.length ? `<span class="flag" title="${B.esc(t.flags.map(f => f === 'review_due' ? tx('flag_review_due')(t.review_by) : tx('flag_' + f)).join(' '))}">${B.icon('triangle-alert', 13)}</span>` : ''}</span></span>
          <span class="w">${sc(t)}</span></li>`).join('') || `<li class="empty">${tx('no_trend')}</li>`}</ol></div>` : ''}
      <p class="hint"><a href="methodologie.html" target="_blank" rel="noopener">${B.icon('book-open-text', 14)} ${tx('method')}</a> · ${B.esc(tx('roadmap')(active, d.roadmap.length))}</p>
      <p class="hint">${tx('disclaimer')}</p>`;
    bind();
  }

  /* ------------------------------------------------------------------ fiche d'une tendance */
  function spark(hist) {
    if (!hist || hist.length < 2) return '';
    const W = 300, H = 70, P = 18, x = i => P + i * (W - 2 * P) / (hist.length - 1), y = v => H - 16 - (v / 25) * (H - 26);
    return `<figure class="ew-chart"><figcaption>${B.esc(tx('history'))}</figcaption><svg viewBox="0 0 ${W} ${H}"><polyline points="${hist.map(([, v], i) => `${x(i)},${y(v)}`).join(' ')}" fill="none" stroke="currentColor" stroke-width="2"/>
      ${hist.map(([m, v], i) => `<circle cx="${x(i)}" cy="${y(v)}" r="2.6" fill="currentColor"/><text x="${x(i)}" y="${H - 3}" text-anchor="middle">${B.esc(m.slice(2))}</text><text x="${x(i)}" y="${y(v) - 5}" text-anchor="middle">${v}</text>`).join('')}</svg></figure>`;
  }
  function srcLink(k, n) {
    const s = D().sources[k]; if (!s) return '';
    return `<a class="fs-src" href="methodologie.html#src-${B.esc(k)}" target="_blank" rel="noopener" title="${B.esc(s.pub + ' · ' + s.t)}">[${n}]</a>`;
  }
  function select(id) {
    const d = D(), t = d.trends.find(x => x.id === id); if (!t) return;
    S.selected = id;
    const sc0 = d.scopes[t.scope], sc_ = d.scales, idx = {}, nums = t.sources.map((k, i) => { idx[k] = i + 1; return k; });
    const bar = (label, v, txt) => `<div class="bar"><span>${B.esc(label)}</span><span class="track"><span class="fill" style="width:${v * 20}%"></span></span><span class="v">${v}/5</span></div>${txt ? `<div class="hint fs-scale">${B.esc(txt)}</div>` : ''}`;
    const li = arr => (arr || []).map(x => `<li>${B.esc(loc(x))}</li>`).join('');
    const live = t.live;
    B.openDrawer(`
      <div class="d-head"><div class="d-kicker">${B.esc(loc(d.families[t.family]))} · ${B.esc(scopeName(sc0))}</div>
        <h2 class="d-title">${B.esc(loc(t.title))}</h2>
        <div class="risk-big"><span class="lvl" style="background:${lvl(t.lvl).color}">${t.score.all}</span><div><div class="name">${B.esc(loc(lvl(t.lvl)))}</div>
          <div class="desc">${tx('reviewed')} ${B.esc(fmtDate(t.reviewed))} · ${B.esc(tx('a_business'))} ${t.score.business}/25 · ${B.esc(tx('a_travel'))} ${t.score.travel}/25</div></div></div></div>
      ${t.flags.length ? `<div class="d-sec fs-flags">${t.flags.map(f => `<p>${B.icon('triangle-alert', 14)} ${B.esc(f === 'review_due' ? tx('flag_review_due')(t.review_by) : tx('flag_' + f))}</p>`).join('')}</div>` : ''}
      <div class="d-sec">
        ${bar(tx('likelihood'), t.likelihood, `${loc(sc_.likelihood[t.likelihood])} (${sc_.likelihood[t.likelihood].p})`)}
        ${bar(tx('impact_business'), t.impact.business, sc_.impact_business[t.impact.business]['d_' + LG()])}
        ${bar(tx('impact_travel'), t.impact.travel, sc_.impact_travel[t.impact.travel]['d_' + LG()])}
        <ul class="mini-list"><li><span class="t">${tx('horizon_l')}</span><span class="w">${B.esc(loc(sc_.horizon[t.horizon]))}</span></li>
          <li><span class="t">${tx('momentum')}</span><span class="w">${ARROW[t.momentum]} ${B.esc(loc(sc_.momentum[String(t.momentum)]))}</span></li>
          <li><span class="t">${tx('confidence')}</span><span class="w">${B.esc(loc(sc_.confidence[t.confidence]))}</span></li></ul>
      </div>
      <div class="d-sec"><h3>${tx('summary')}</h3><p class="fs-text">${B.esc(loc(t.summary))}</p>
        <p class="hint">${tx('drivers')} : ${t.drivers.map(k => { const dr = d.drivers.find(x => x.id === k); return dr ? B.esc(loc(dr)) : ''; }).filter(Boolean).join(' · ')}</p></div>
      <div class="d-sec"><h3>${tx('signals')}</h3><ul class="fs-signals">${t.signals.map(s => `<li>${s.d ? `<span class="dt">${B.esc(fmtDate(s.d))}</span> ` : ''}${B.esc(loc(s))} ${(s.src || []).map(k => srcLink(k, idx[k])).join('')}</li>`).join('')}</ul></div>
      ${live ? `<div class="d-sec"><h3>${tx('live')}</h3><p class="fs-text">${B.esc(tx('live_txt')(live.n, live.base, live.days))} <strong>${B.esc(tx('live_dir')[String(live.dir)])}</strong></p></div>` : ''}
      <div class="d-sec"><h3>${tx('watch')}</h3><ul class="ew-drivers">${li(t.watch)}</ul></div>
      ${t.rupture ? `<div class="d-sec"><h3>${tx('rupture')}</h3><p class="fs-text">${B.esc(loc(t.rupture))}</p></div>` : ''}
      <div class="d-sec"><h3>${tx('implications')}</h3>
        <p class="fs-text"><strong>${tx('for_business')} :</strong> ${B.esc(loc(t.implications.business))}</p>
        <p class="fs-text"><strong>${tx('for_travel')} :</strong> ${B.esc(loc(t.implications.travel))}</p></div>
      <div class="d-sec"><h3>${tx('actions')}</h3><ul class="ew-drivers">${li((t.actions.business || []).concat(t.actions.travel || []))}</ul></div>
      ${t.sectors && t.sectors.length ? `<div class="d-sec"><h3>${tx('sectors')}</h3><div class="fs-chips">${t.sectors.map(k => `<span class="chip">${B.esc(loc(d.sectors[k]))}</span>`).join('')}</div></div>` : ''}
      ${t.units && t.units.top.length ? `<div class="d-sec"><h3>${tx('units')}</h3><ul class="mini-list">${t.units.top.map(u => `<li data-unit="${B.esc(u[0])}" data-ureg="${B.esc(u[6] || '')}"><span class="dot" style="background:${EW_COLORS[u[4]]}"></span><span class="t">${B.flagImg(u[2])}${B.esc(u[1])}</span><span class="w">${u[5]} · ${u[3]}/100</span></li>`).join('')}</ul><p class="hint">${tx('units_hint')}</p></div>` : ''}
      ${spark(t.history)}
      ${t.links && t.links.length ? `<div class="d-sec"><h3>${tx('links')}</h3><ul class="mini-list">${t.links.map(k => d.trends.find(x => x.id === k)).filter(Boolean).map(x => `<li data-fsl="${x.id}" class="link"><span class="t">${B.esc(loc(x.title))}</span><span class="w">${x.score.all}</span></li>`).join('')}</ul></div>` : ''}
      <div class="d-sec"><h3>${tx('sources')}</h3><ol class="fs-sources">${nums.map(k => { const s = d.sources[k]; return s ? `<li><a href="${B.esc(s.url)}" target="_blank" rel="noopener">${B.esc(s.t)}</a> — ${B.esc(s.pub)}${s.d && /^\d/.test(s.d) ? `, ${B.esc(fmtDate(s.d))}` : ''} <span class="muted">(${B.esc(tx('rel'))} ${B.esc(s.rel)})</span></li>` : ''; }).join('')}</ol>
        <p class="hint"><a href="methodologie.html" target="_blank" rel="noopener">${tx('method')}</a></p></div>`, 'fs', id);
    document.querySelectorAll('#drawer [data-fsl]').forEach(x => { x.onclick = () => select(x.dataset.fsl); });
    document.querySelectorAll('#drawer [data-unit]').forEach(x => { x.onclick = () => openUnit(x.dataset.unit, x.dataset.ureg); });
  }

  /** Descend au niveau subdivision et ouvre la fiche d'une subdivision (depuis une fiche tendance) */
  function openUnit(id, reg) {
    const s = D().scopes[S.scope];
    if (reg && regionOf(s).id !== reg) S.scope = reg;
    if (window.AngorEW) window.AngorEW.openUnit(id);
    if (S.view !== 'ew') setView('ew'); else render();
  }

  /* ------------------------------------------------------------------ cycle de vie */
  function ensure() {
    const need = [];
    if (!window.VS_FS) need.push('data/foresight.js');
    if (!need.length) return Promise.resolve();
    if (!loading) loading = Promise.all(need.map(u => B.loadScript(u))).then(() => { loading = null; });
    return loading;
  }
  const api = {
    active: false,
    init(bridge) {
      B = bridge;
      if (!B.map.getPane('fsPane')) { B.map.createPane('fsPane'); B.map.getPane('fsPane').style.zIndex = 385; }
    },
    open(view) {
      api.active = true; if (view) S.view = view; if (B.enter) B.enter(); render();
      ensure().then(() => { if (!api.active) return; render(); if (D() && S.view === 'trends') { drawLayer(); fit(); } });
    },
    close() {
      api.active = false; S.selected = null; if (B.leave) B.leave();
      if (layer) { B.map.removeLayer(layer); layer = null; }
      if (window.AngorEW) window.AngorEW.unmount();
    },
    refresh() { if (api.active) { render(); if (S.view === 'trends') drawLayer(); else if (window.AngorEW) window.AngorEW.refresh(); } },
    reopen(id) { if (D()) select(id); },
    /** Ouvre la fiche d'une tendance (depuis une fiche de subdivision) */
    openTrend(id) { ensure().then(() => { if (D()) select(id); }); },
  };
  window.AngorFS = api;
})();
