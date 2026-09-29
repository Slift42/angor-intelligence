/* Angor Intelligence – onglet « Alerte précoce » : climat, sécurité et humanitaire par unité administrative.
   Données : docs/data/early_warning.js (window.VS_EW), écrites par le robot (veille/early_warning.py).
   Branché sur la carte par app.js : window.AngorEW.init(bridge) puis open() / close(). */
(function () {
  'use strict';
  let B = null;           // pont vers app.js : map, t, esc, icon, flagImg, countryName, openDrawer, lang(), theme()
  let layer = null, circles = null, loading = null;
  const S = { region: null, dataset: 'score', month: null, overlay: true, selected: null };
  try { Object.assign(S, JSON.parse(localStorage.getItem('vs-ew') || '{}'), { selected: null }); } catch (e) { /* stockage indisponible */ }
  const save = () => { try { localStorage.setItem('vs-ew', JSON.stringify({ region: S.region, dataset: S.dataset, overlay: S.overlay })); } catch (e) { /* idem */ } };

  const TXT = {
    fr: {
      hint: 'Croisez le climat, la sécurité et la situation humanitaire, région par région, pour repérer les zones où les risques convergent avant une dégradation. Données mensuelles.',
      region: 'Région', month: 'Mois', dataset: 'Donnée affichée', overlay: 'Superposer les incidents du mois',
      g_syn: 'Synthèse', g_clim: 'Climat et ressources', g_sec: 'Sécurité', g_hum: 'Impacts humanitaires',
      score: 'Indice de convergence des risques', rain: 'Précipitations (écart à la normale)', temp: 'Température (écart à la normale)',
      soil: 'Humidité du sol (écart à la normale)', inc: 'Incidents de sécurité', res: 'Conflits liés aux ressources',
      ipc: 'Insécurité alimentaire (IPC 3+)', idp: 'Personnes déplacées',
      top: 'Unités les plus exposées', loading: 'Chargement des données…', missing: 'Données pas encore disponibles : elles seront produites par le robot lors des prochaines collectes (quelques heures pour tout le climat).',
      levels: { 1: 'Faible', 2: 'Modéré', 3: 'Élevé', 4: 'Très élevé' },
      no_data: 'pas de donnée', dry: 'saison sèche', normal: 'normale', avg: 'moyenne', range: 'min–max des 15 années précédentes',
      comp_cl: 'Climat', comp_co: 'Sécurité', comp_hu: 'Humanitaire', drivers: 'Facteurs', method: 'Méthode',
      method_txt: 'Indice expérimental de 0 à 100 : climat (40 points : déficit ou excès de pluie sur 3 mois, chaleur anormale, sols secs), sécurité (35 : volume d’incidents sur 3 mois, hausse par rapport aux 12 mois précédents, conflits liés aux ressources), humanitaire (25 : part de la population en phase IPC 3 ou plus, déplacés). Il signale des convergences, pas des certitudes : à confronter à l’analyse.',
      dr: {
        rain_deficit: v => `Pluies à ${v} % de la normale sur 3 mois`, rain_excess: v => `Pluies à ${v} % de la normale sur 3 mois (risque d’inondation)`,
        heat: v => `Températures supérieures de ${v} °C à la normale`, soil_record: () => 'Sols plus secs que toutes les années précédentes', soil_dry: () => 'Sols plus secs que la normale',
        conflict_up: v => `Incidents en hausse de ${v} %`, conflict_new: v => `${v} incidents alors que la zone était calme`, incidents: v => `${v} incident(s) de sécurité en 3 mois`,
        resource: v => `${v} incident(s) liés aux ressources (eau, terres, bétail…)`, ipc: v => `${v} % de la population en insécurité alimentaire aiguë (IPC 3+)`,
        idp: v => `${fmtN(v)} personnes déplacées`,
      },
      ipc_src: 'IPC via HDX HAPI', idp_src: 'OIM-DTM via HDX HAPI', at: 'au', people: 'personnes', incidents12: 'Incidents sur 12 mois',
      rain_chart: 'Précipitations mensuelles (mm)', temp_chart: 'Température moyenne (°C)', soil_chart: 'Humidité du sol racinaire (0–1)',
      credits: 'Sources', see_incidents: 'Voir les incidents de la zone', score_at: 'Indice au',
    },
    en: {
      hint: 'Cross climate, security and humanitarian data, area by area, to spot where risks converge before things deteriorate. Monthly data.',
      region: 'Region', month: 'Month', dataset: 'Dataset', overlay: 'Overlay the month’s incidents',
      g_syn: 'Summary', g_clim: 'Climate & resources', g_sec: 'Security', g_hum: 'Humanitarian impacts',
      score: 'Risk convergence index', rain: 'Rainfall (anomaly)', temp: 'Temperature (anomaly)', soil: 'Soil moisture (anomaly)',
      inc: 'Security incidents', res: 'Resource-related conflict', ipc: 'Food insecurity (IPC 3+)', idp: 'Internally displaced people',
      top: 'Most exposed areas', loading: 'Loading data…', missing: 'Data not available yet: the robot will produce it over the next runs (a few hours for all climate data).',
      levels: { 1: 'Low', 2: 'Moderate', 3: 'High', 4: 'Very high' },
      no_data: 'no data', dry: 'dry season', normal: 'normal', avg: 'average', range: 'min–max over the previous 15 years',
      comp_cl: 'Climate', comp_co: 'Security', comp_hu: 'Humanitarian', drivers: 'Drivers', method: 'Method',
      method_txt: 'Experimental 0–100 index: climate (40 points: 3-month rainfall deficit or excess, abnormal heat, dry soils), security (35: 3-month incident volume, increase vs the previous 12 months, resource-related conflict), humanitarian (25: share of population in IPC phase 3+, displacement). It flags convergence, not certainty: always check against analysis.',
      dr: {
        rain_deficit: v => `Rainfall at ${v}% of normal over 3 months`, rain_excess: v => `Rainfall at ${v}% of normal over 3 months (flood risk)`,
        heat: v => `Temperatures ${v} °C above normal`, soil_record: () => 'Soils drier than in any previous year', soil_dry: () => 'Soils drier than normal',
        conflict_up: v => `Incidents up ${v}%`, conflict_new: v => `${v} incidents in a previously quiet area`, incidents: v => `${v} security incident(s) in 3 months`,
        resource: v => `${v} resource-related incident(s) (water, land, livestock…)`, ipc: v => `${v}% of the population in acute food insecurity (IPC 3+)`,
        idp: v => `${fmtN(v)} internally displaced people`,
      },
      ipc_src: 'IPC via HDX HAPI', idp_src: 'IOM-DTM via HDX HAPI', at: 'at', people: 'people', incidents12: 'Incidents over 12 months',
      rain_chart: 'Monthly rainfall (mm)', temp_chart: 'Mean temperature (°C)', soil_chart: 'Root-zone soil wetness (0–1)',
      credits: 'Sources', see_incidents: 'Show incidents in this area', score_at: 'Index as of',
    },
  };
  const tx = k => (TXT[B.lang()] || TXT.fr)[k];
  const fmtN = n => n == null ? '—' : Number(n).toLocaleString(B && B.lang() === 'en' ? 'en-GB' : 'fr-FR');
  const DATASETS = [['g_syn', ['score']], ['g_clim', ['rain', 'temp', 'soil']], ['g_sec', ['inc', 'res']], ['g_hum', ['ipc', 'idp']]];
  const LEVEL_COLORS = { 1: '#5FA37C', 2: '#E3B505', 3: '#EE7D22', 4: '#C0263B' };
  const RAIN = [[0.5, '#8C510A'], [0.75, '#D8B365'], [0.9, '#F2DDA4'], [1.1, '#EEF0EC'], [1.25, '#B7E1DA'], [1.5, '#5AB4AC'], [Infinity, '#01665E']];
  const TEMP = [[-1, '#2166AC'], [-0.3, '#92C5DE'], [0.3, '#EEF0EC'], [0.8, '#FDB863'], [1.5, '#E66101'], [Infinity, '#B2182B']];
  const SOIL = [[-0.15, '#8C510A'], [-0.07, '#D8B365'], [0.07, '#EEF0EC'], [0.15, '#A6D96A'], [Infinity, '#1A9641']];
  const INC = [[0, '#EEF0EC'], [2, '#FCD9C4'], [5, '#F9A77B'], [10, '#EE6A3B'], [20, '#C9302C'], [Infinity, '#7F0F1E']];
  const IPC = [[0.1, '#CDFACD'], [0.2, '#FAE61E'], [0.3, '#E67800'], [0.4, '#C80000'], [Infinity, '#640000']];
  const IDP = [[10000, '#EFEDF5'], [50000, '#BCBDDC'], [200000, '#9E9AC8'], [500000, '#756BB1'], [Infinity, '#54278F']];
  const pick = (scale, v) => scale.find(([lim]) => v <= lim)[1];

  function data() { return window.VS_EW; }
  function monthIdx() { const d = data(); const i = d.months.indexOf(S.month); return i < 0 ? d.months.length - 1 : i; }
  function secIdx() { const d = data(); const i = d.sec_months.indexOf(S.month); return i < 0 ? d.sec_months.length - 1 : i; }

  /** Valeur d'une unité pour la donnée affichée : {v, label, color} */
  function valueOf(u, ds) {
    const i = monthIdx(), j = secIdx();
    if (ds === 'score') return { v: u.score.v, color: LEVEL_COLORS[u.score.lvl], label: `${u.score.v}/100 · ${tx('levels')[u.score.lvl]}` };
    if (ds === 'rain') {
      const c = u.clim.P; if (!c || c.v[i] == null || c.avg[i] == null) return null;
      if (c.avg[i] < 10) return { v: 1, color: '#E6E8E4', label: `${Math.round(c.v[i])} mm · ${tx('dry')}`, dry: true };
      const r = c.v[i] / c.avg[i];
      return { v: r, color: pick(RAIN, r), label: `${Math.round(c.v[i])} mm · ${Math.round(r * 100)} % ${tx('normal')}` };
    }
    if (ds === 'temp') {
      const c = u.clim.T; if (!c || c.v[i] == null || c.avg[i] == null) return null;
      const d = c.v[i] - c.avg[i];
      return { v: d, color: pick(TEMP, d), label: `${c.v[i].toFixed(1)} °C · ${d >= 0 ? '+' : ''}${d.toFixed(1)} °C` };
    }
    if (ds === 'soil') {
      const c = u.clim.W; if (!c || c.v[i] == null || c.avg[i] == null) return null;
      const d = c.v[i] - c.avg[i];
      return { v: d, color: pick(SOIL, d), label: `${c.v[i].toFixed(2)} · ${d >= 0 ? '+' : ''}${d.toFixed(2)}` };
    }
    if (ds === 'inc' || ds === 'res') {
      const n = u.sec[ds === 'inc' ? 'all' : 'res'][j] || 0;
      return { v: n, color: pick(INC, n), label: `${n}` };
    }
    if (ds === 'ipc') { const v = u.hum.ipc3; return v == null ? null : { v, color: pick(IPC, v), label: `${Math.round(v * 100)} %` }; }
    if (ds === 'idp') { const v = u.hum.idp; return v == null ? null : { v, color: pick(IDP, v), label: fmtN(v) }; }
    return null;
  }
  function legend(ds) {
    const row = (c, l) => `<span class="k"><i class="sq" style="background:${c}"></i>${B.esc(l)}</span>`;
    if (ds === 'score') return [1, 2, 3, 4].map(l => row(LEVEL_COLORS[l], tx('levels')[l])).join('');
    if (ds === 'rain') return ['< 50 %', '50–75 %', '75–90 %', '90–110 %', '110–125 %', '125–150 %', '> 150 %'].map((l, k) => row(RAIN[k][1], l)).join('') + row('#E6E8E4', tx('dry'));
    if (ds === 'temp') return ['< −1 °C', '−1/−0,3', '±0,3', '+0,3/+0,8', '+0,8/+1,5', '> +1,5 °C'].map((l, k) => row(TEMP[k][1], l)).join('');
    if (ds === 'soil') return ['< −0,15', '−0,15/−0,07', '±0,07', '+0,07/+0,15', '> +0,15'].map((l, k) => row(SOIL[k][1], l)).join('');
    if (ds === 'inc' || ds === 'res') return ['0', '1–2', '3–5', '6–10', '11–20', '> 20'].map((l, k) => row(INC[k][1], l)).join('');
    if (ds === 'ipc') return ['< 10 %', '10–20 %', '20–30 %', '30–40 %', '> 40 %'].map((l, k) => row(IPC[k][1], l)).join('');
    if (ds === 'idp') return ['< 10 000', '10–50 000', '50–200 000', '200–500 000', '> 500 000'].map((l, k) => row(IDP[k][1], l)).join('');
    return '';
  }

  function monthLabel(ym, long) {
    const d = new Date(ym + '-15T12:00:00Z');
    return d.toLocaleDateString(B.lang() === 'en' ? 'en-GB' : 'fr-FR', long ? { month: 'long', year: 'numeric' } : { month: 'short', year: '2-digit' });
  }

  /* ------------------------------------------------------------------ couche carte */
  function drawLayer() {
    const d = data(); if (!d) return;
    const units = d.units.filter(u => u.reg === S.region);
    const dark = B.theme() === 'dark';
    const feats = units.map(u => ({ type: 'Feature', properties: { id: u.id }, geometry: { type: 'MultiPolygon', coordinates: u.g } }));
    if (layer) B.map.removeLayer(layer);
    const byId = Object.fromEntries(units.map(u => [u.id, u]));
    layer = L.geoJSON({ type: 'FeatureCollection', features: feats }, {
      pane: 'ewPane',
      style: f => {
        const u = byId[f.properties.id], val = valueOf(u, S.dataset);
        return { fillColor: val ? val.color : (dark ? '#2A3542' : '#D5DBE0'), fillOpacity: val ? 0.72 : 0.35, color: S.selected === u.id ? (dark ? '#fff' : '#111B27') : (dark ? '#0D141C' : '#FFFFFF'),
          weight: S.selected === u.id ? 2.4 : 0.8 };
      },
      onEachFeature: (f, lyr) => {
        const u = byId[f.properties.id];
        lyr.on('click', ev => { L.DomEvent.stopPropagation(ev); select(u.id); });
        lyr.on('mouseover', () => lyr.setStyle({ weight: 2 }));
        lyr.on('mouseout', () => layer && layer.resetStyle(lyr));
        lyr.bindTooltip(() => { const v = valueOf(u, S.dataset); return `<strong>${B.esc(u.n)}</strong> · ${B.esc(B.countryName(u.iso))}<br>${B.esc(tx(S.dataset))} : ${v ? B.esc(v.label) : tx('no_data')}`; },
          { sticky: true, className: 'vs-tip', direction: 'top', offset: [0, -8] });
      },
    }).addTo(B.map);
    if (circles) B.map.removeLayer(circles);
    circles = null;
    if (S.overlay && S.dataset !== 'inc') {
      const j = secIdx();
      circles = L.layerGroup(units.filter(u => u.sec.all[j]).map(u => L.circleMarker([u.c[0], u.c[1]], {
        pane: 'ewPane', radius: 4 + Math.sqrt(u.sec.all[j]) * 3, color: '#7F0F1E', weight: 1.2, fillColor: '#C9302C', fillOpacity: 0.55, interactive: false,
      }))).addTo(B.map);
    }
  }
  function fitRegion() {
    const r = data().regions[S.region]; if (!r) return;
    B.map.flyToBounds([[r.bbox[1], r.bbox[0]], [r.bbox[3], r.bbox[2]]], { padding: [30, 30], duration: 0.8 });
  }

  /* ------------------------------------------------------------------ panneau */
  function render() {
    const el = document.getElementById('ew-body'); if (!el) return;
    const d = data();
    if (!d) { el.innerHTML = `<p class="hint">${loading ? tx('loading') : tx('missing')}</p>`; return; }
    if (!d.regions[S.region]) S.region = Object.keys(d.regions)[0];
    if (!d.months.includes(S.month)) S.month = d.months[d.months.length - 1];
    const units = d.units.filter(u => u.reg === S.region);
    const ranked = units.map(u => ({ u, v: valueOf(u, S.dataset) })).filter(x => x.v && !x.v.dry)
      .sort((a, b) => (S.dataset === 'rain' ? Math.abs(1 - b.v.v) - Math.abs(1 - a.v.v) : b.v.v - a.v.v)).slice(0, 10);
    el.innerHTML = `
      <p class="hint">${tx('hint')}</p>
      <div class="ew-controls">
        <label>${tx('region')}<select id="ew-region">${Object.entries(d.regions).map(([k, r]) => `<option value="${k}"${k === S.region ? ' selected' : ''}>${B.esc(r[B.lang()] || r.fr)}</option>`).join('')}</select></label>
        <label>${tx('month')}<select id="ew-month">${d.months.slice().reverse().map(m => `<option value="${m}"${m === S.month ? ' selected' : ''}>${B.esc(monthLabel(m, true))}</option>`).join('')}</select></label>
      </div>
      <div class="ew-datasets" role="radiogroup" aria-label="${B.esc(tx('dataset'))}">
        ${DATASETS.map(([g, list]) => `<div class="ew-group"><div class="fgroup-title"><span>${tx(g)}</span></div>
          ${list.map(k => `<label class="ew-ds${k === S.dataset ? ' on' : ''}"><input type="radio" name="ew-ds" value="${k}"${k === S.dataset ? ' checked' : ''}>${B.esc(tx(k))}</label>`).join('')}</div>`).join('')}
      </div>
      <label class="switch"><input type="checkbox" id="ew-overlay"${S.overlay ? ' checked' : ''}><span>${tx('overlay')}</span></label>
      <div class="ew-legend"><div class="card-title">${B.esc(tx(S.dataset))}${S.dataset === 'score' ? ` · ${tx('score_at')} ${B.esc(monthLabel(d.months[d.months.length - 1], true))}` : S.dataset === 'ipc' || S.dataset === 'idp' ? '' : ` · ${B.esc(monthLabel(S.month, true))}`}</div><div class="row">${legend(S.dataset)}</div></div>
      <div class="d-sec"><h3>${tx('top')}</h3><ol class="ew-rank">${ranked.map(({ u, v }) => `<li data-ew="${u.id}"><span class="sw" style="background:${v.color}"></span><span class="t">${B.flagImg(u.iso)}${B.esc(u.n)}</span><span class="w">${B.esc(v.label)}</span></li>`).join('') || `<li class="empty">${tx('no_data')}</li>`}</ol></div>
      <details class="ew-method"><summary>${tx('method')}</summary><p class="hint">${tx('method_txt')}</p><p class="hint">${tx('credits')} : ${B.esc(d.credits)}</p></details>`;
    el.querySelector('#ew-region').onchange = ev => { S.region = ev.target.value; S.selected = null; save(); B.closeDrawer(); render(); drawLayer(); fitRegion(); };
    el.querySelector('#ew-month').onchange = ev => { S.month = ev.target.value; render(); drawLayer(); };
    el.querySelectorAll('input[name="ew-ds"]').forEach(r => { r.onchange = () => { S.dataset = r.value; save(); render(); drawLayer(); }; });
    el.querySelector('#ew-overlay').onchange = ev => { S.overlay = ev.target.checked; save(); drawLayer(); };
    el.querySelectorAll('[data-ew]').forEach(li => { li.onclick = () => { B.closePanelMobile(); select(li.dataset.ew, true); }; });
  }

  /* ------------------------------------------------------------------ fiche d'une unité */
  function chart(c, months, opts) {
    if (!c) return '';
    const W = 320, H = 118, P = { l: 30, r: 6, t: 8, b: 20 };
    const vals = [].concat(c.v, c.avg, c.min, c.max).filter(v => v != null);
    if (!vals.length) return '';
    let lo = Math.min(...vals), hi = Math.max(...vals);
    if (opts.zero) lo = Math.min(0, lo);
    if (hi - lo < 1e-6) hi = lo + 1;
    const x = i => P.l + (i + 0.5) * (W - P.l - P.r) / months.length;
    const y = v => P.t + (hi - v) * (H - P.t - P.b) / (hi - lo);
    const bw = (W - P.l - P.r) / months.length * 0.62;
    const band = c.min.map((m, i) => m != null ? `${x(i)},${y(c.max[i])}` : null).filter(Boolean).join(' ') + ' ' +
      c.min.map((m, i) => m != null ? `${x(i)},${y(m)}` : null).filter(Boolean).reverse().join(' ');
    const avg = c.avg.map((v, i) => v != null ? `${x(i)},${y(v)}` : null).filter(Boolean).join(' ');
    const main = opts.bars
      ? c.v.map((v, i) => v != null ? `<rect x="${x(i) - bw / 2}" y="${y(Math.max(v, lo))}" width="${bw}" height="${Math.max(0.5, y(lo) - y(Math.max(v, lo)))}" rx="1.5" fill="${opts.color}" opacity="${months[i] === S.month ? 1 : 0.72}"/>` : '').join('')
      : `<polyline points="${c.v.map((v, i) => v != null ? `${x(i)},${y(v)}` : null).filter(Boolean).join(' ')}" fill="none" stroke="${opts.color}" stroke-width="2"/>` +
        c.v.map((v, i) => v != null ? `<circle cx="${x(i)}" cy="${y(v)}" r="${months[i] === S.month ? 3.4 : 2}" fill="${opts.color}"/>` : '').join('');
    const ticks = [lo, (lo + hi) / 2, hi].map(v => `<text x="${P.l - 4}" y="${y(v) + 3}" text-anchor="end">${opts.fmt(v)}</text><line x1="${P.l}" x2="${W - P.r}" y1="${y(v)}" y2="${y(v)}" class="grid"/>`).join('');
    const lab = months.map((m, i) => i % 2 === 0 ? `<text x="${x(i)}" y="${H - 5}" text-anchor="middle">${B.esc(monthLabel(m).replace('.', ''))}</text>` : '').join('');
    return `<figure class="ew-chart"><figcaption>${B.esc(opts.title)}</figcaption>
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${B.esc(opts.title)}">${ticks}
        ${band.trim() ? `<polygon points="${band}" class="band"/>` : ''}${main}${avg ? `<polyline points="${avg}" class="avg"/>` : ''}${lab}</svg>
      <div class="ew-key"><span><i class="k-main" style="background:${opts.color}"></i>${B.esc(monthLabel(months[months.length - 1], true))}</span><span><i class="k-avg"></i>${tx('avg')}</span><span><i class="k-band"></i>${tx('range')}</span></div></figure>`;
  }
  function bars12(arr, months, color, title) {
    const W = 320, H = 96, P = { l: 22, r: 6, t: 8, b: 20 };
    const hi = Math.max(1, ...arr), x = i => P.l + (i + 0.5) * (W - P.l - P.r) / months.length, bw = (W - P.l - P.r) / months.length * 0.62;
    const y = v => P.t + (hi - v) * (H - P.t - P.b) / hi;
    return `<figure class="ew-chart"><figcaption>${B.esc(title)}</figcaption><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${B.esc(title)}">
      <text x="${P.l - 4}" y="${y(hi) + 3}" text-anchor="end">${hi}</text><line x1="${P.l}" x2="${W - P.r}" y1="${y(hi)}" y2="${y(hi)}" class="grid"/><line x1="${P.l}" x2="${W - P.r}" y1="${y(0)}" y2="${y(0)}" class="grid"/>
      ${arr.map((v, i) => `<rect x="${x(i) - bw / 2}" y="${y(v)}" width="${bw}" height="${Math.max(0.5, y(0) - y(v))}" rx="1.5" fill="${color}" opacity="${months[i] === S.month ? 1 : 0.75}"/>`).join('')}
      ${months.map((m, i) => i % 2 === 0 ? `<text x="${x(i)}" y="${H - 5}" text-anchor="middle">${B.esc(monthLabel(m).replace('.', ''))}</text>` : '').join('')}</svg></figure>`;
  }
  function select(id, fly) {
    const d = data(), u = d.units.find(x => x.id === id); if (!u) return;
    S.selected = id; drawLayer();
    if (fly) { const b = L.geoJSON({ type: 'MultiPolygon', coordinates: u.g }).getBounds(); B.map.flyToBounds(b, { padding: [60, 60], maxZoom: 7, duration: 0.7 }); }
    const sc = u.score, secM = d.sec_months.slice(-12);
    const bar = (k, v, max) => `<div class="bar"><span>${tx(k)}</span><span class="track"><span class="fill" style="width:${Math.round(v / max * 100)}%"></span></span><span class="v">${v}/${max}</span></div>`;
    const dr = sc.dr.filter(([k]) => k !== 'incidents' || !sc.dr.some(([x]) => x === 'conflict_up' || x === 'conflict_new'));
    B.openDrawer(`
      <div class="d-head"><div class="d-kicker">${B.esc(tx('score'))}</div>
        <h2 class="d-title">${B.flagImg(u.iso, 24)}${B.esc(u.n)} <span class="muted" style="font-weight:400;font-size:14px">· ${B.esc(B.countryName(u.iso))}</span></h2>
        <div class="risk-big"><span class="lvl" style="background:${LEVEL_COLORS[sc.lvl]}">${sc.v}</span><div><div class="name">${B.esc(tx('levels')[sc.lvl])}</div>
          <div class="desc">${tx('score_at')} ${B.esc(monthLabel(d.months[d.months.length - 1], true))}</div></div></div></div>
      <div class="d-sec">${bar('comp_cl', sc.cl, 40)}${bar('comp_co', sc.co, 35)}${bar('comp_hu', sc.hu, 25)}</div>
      ${dr.length ? `<div class="d-sec"><h3>${tx('drivers')}</h3><ul class="ew-drivers">${dr.map(([k, v]) => `<li>${B.esc(tx('dr')[k](v))}</li>`).join('')}</ul></div>` : ''}
      <div class="d-sec">
        ${chart(u.clim.P, d.months, { title: tx('rain_chart'), color: '#2B7BB9', bars: true, zero: true, fmt: v => Math.round(v) })}
        ${chart(u.clim.T, d.months, { title: tx('temp_chart'), color: '#E66101', fmt: v => v.toFixed(0) })}
        ${chart(u.clim.W, d.months, { title: tx('soil_chart'), color: '#5E8C31', fmt: v => v.toFixed(2) })}
        ${bars12(u.sec.all.slice(-12), secM, '#C9302C', tx('incidents12'))}
      </div>
      <div class="d-sec"><h3>${tx('g_hum')}</h3><ul class="mini-list">
        <li><span class="t">${tx('ipc')}</span><span class="w">${u.hum.ipc3 == null ? tx('no_data') : `${Math.round(u.hum.ipc3 * 100)} % · ${B.esc(u.hum.ipc_end || '')}`}</span></li>
        <li><span class="t">${tx('idp')}</span><span class="w">${u.hum.idp == null ? tx('no_data') : `${fmtN(u.hum.idp)} · ${B.esc(u.hum.idp_end || '')}`}</span></li>
      </ul><div class="hint">${tx('ipc_src')} · ${tx('idp_src')}</div></div>
      <div class="d-sec"><button class="btn" id="ew-see">${B.icon('siren')}${tx('see_incidents')}</button></div>
      <div class="d-sec"><div class="hint">${tx('method_txt')}</div></div>`, 'ew', id);
    const see = document.getElementById('ew-see');
    if (see) see.onclick = () => { const b = L.geoJSON({ type: 'MultiPolygon', coordinates: u.g }).getBounds(); B.showIncidents(b); };
    const li = document.querySelector(`#ew-body [data-ew="${id}"]`); if (li) li.classList.add('on');
  }

  /* ------------------------------------------------------------------ cycle de vie */
  function ensure() {
    if (window.VS_EW) return Promise.resolve();
    if (!loading) loading = B.loadScript('data/early_warning.js').then(() => { loading = null; });
    return loading;
  }
  const api = {
    active: false,
    init(bridge) {
      B = bridge;
      if (!B.map.getPane('ewPane')) { B.map.createPane('ewPane'); B.map.getPane('ewPane').style.zIndex = 390; }
    },
    open() {
      api.active = true; if (B.enter) B.enter(); render();
      ensure().then(() => { if (!api.active) return; render(); if (data()) { drawLayer(); fitRegion(); } });
    },
    close() {
      api.active = false; S.selected = null; if (B.leave) B.leave();
      if (layer) { B.map.removeLayer(layer); layer = null; }
      if (circles) { B.map.removeLayer(circles); circles = null; }
    },
    refresh() { if (api.active) { render(); drawLayer(); } },
    reopen(id) { if (data()) select(id); },
  };
  window.AngorEW = api;
})();
