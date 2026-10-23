/* Angor Intelligence – alerte précoce par subdivision (niveau administratif 1), niveau de détail le plus fin des
   tendances de risques (v0.27). Affichée dans l'onglet « Tendances » (foresight.js) quand on choisit le niveau
   « Subdivisions » ; monde entier, mêmes régions que les tendances.
   Données : docs/data/early_warning.js (window.VS_EW : index, mois, validation) et docs/data/early_warning/<région>.js
   (window.VS_EW_R[région] : subdivisions), écrites par le robot (veille/early_warning.py).
   API : window.AngorEW.init(bridge), mount(élément, {region, country}), unmount(), reopen(id), refresh(). */
(function () {
  'use strict';
  let B = null;           // pont vers app.js : map, t, esc, icon, flagImg, countryName, openDrawer, lang(), theme()
  let layer = null, circles = null, loading = {}, host = null;
  const S = { region: null, country: null, dataset: 'score', month: null, overlay: true, selected: null };
  try { Object.assign(S, JSON.parse(localStorage.getItem('vs-ew') || '{}'), { selected: null, region: null, country: null }); } catch (e) { /* stockage indisponible */ }
  const save = () => { try { localStorage.setItem('vs-ew', JSON.stringify({ dataset: S.dataset, overlay: S.overlay })); } catch (e) { /* idem */ } };

  const TXT = {
    fr: {
      hint: 'Niveau de détail le plus fin : chaque subdivision (région, État, province) croise le climat, les incidents vérifiés par famille de facteurs et, là où elle existe, la situation humanitaire, pour repérer les zones où les risques convergent avant une dégradation. Données mensuelles.',
      month: 'Mois', dataset: 'Donnée affichée', overlay: 'Superposer les incidents du mois',
      g_syn: 'Synthèse', g_clim: 'Climat et environnement', g_sec: 'Terrorisme, conflits et criminalité', g_soc: 'Société, aléas et infrastructures', g_hum: 'Crises humanitaires',
      score: 'Indice de convergence des risques', rain: 'Précipitations (écart à la normale)', temp: 'Température (écart à la normale)',
      soil: 'Humidité du sol (écart à la normale)', inc: 'Incidents de sécurité', res: 'Conflits liés aux ressources',
      so: 'Troubles civils et crises politiques', hz: 'Aléas, pannes, cyber et épidémies',
      ipc: 'Insécurité alimentaire (IPC 3+)', idp: 'Personnes déplacées',
      top: 'Subdivisions les plus exposées', loading: 'Chargement des subdivisions…',
      missing: 'Subdivisions pas encore disponibles pour ce périmètre : le robot charge les limites et le climat région après région (couverture mondiale en deux à trois jours).',
      pending: n => `${n} pays en cours de chargement dans cette région.`, no_clim: 'climat en cours de chargement',
      levels: { 1: 'Faible', 2: 'Modéré', 3: 'Élevé', 4: 'Très élevé' },
      no_data: 'pas de donnée', dry: 'saison sèche', normal: 'normale', avg: 'moyenne', range: 'min–max des 15 années précédentes',
      drivers: 'Facteurs', method: 'Méthode de l’indice', hum_na: 'sans objet (aucune crise humanitaire suivie)',
      method_txt: 'Indice de 0 à 100, cinq composantes reprenant les familles de facteurs des tendances : climat et environnement (30 points : pluie sur 3 mois, chaleur anormale, sols secs), terrorisme, conflits et criminalité (30 : volume d’incidents sur 3 mois, hausse par rapport aux 12 mois précédents, conflits liés aux ressources), société et politique (15 : troubles civils et crises politiques), aléas, infrastructures et santé (10 : catastrophes, pannes, cyberattaques, épidémies de gravité 2 et plus), crises humanitaires (15 : IPC 3+, déplacés). Sans donnée humanitaire, l’indice est ramené sur 100. Il signale des convergences, pas des certitudes : à confronter aux tendances et à l’analyse.',
      dr: {
        rain_deficit: v => `Pluies à ${v} % de la normale sur 3 mois`, rain_excess: v => `Pluies à ${v} % de la normale sur 3 mois (risque d’inondation)`,
        heat: v => `Températures supérieures de ${v} °C à la normale`, soil_record: () => 'Sols plus secs que toutes les années précédentes', soil_dry: () => 'Sols plus secs que la normale',
        conflict_up: v => `Incidents de sécurité en hausse de ${v} %`, conflict_new: v => `${v} incidents de sécurité alors que la zone était calme`, incidents: v => `${v} incident(s) de sécurité en 3 mois`,
        resource: v => `${v} incident(s) liés aux ressources (eau, terres, bétail…)`, unrest_up: v => `Troubles civils et politiques en hausse (${v} en 3 mois)`,
        unrest: v => `${v} trouble(s) civil(s) ou politique(s) en 3 mois`, political: v => `${v} crise(s) politique(s) en 3 mois`,
        haz: v => `${v} catastrophe(s) naturelle(s) notable(s) en 3 mois`, infra: v => `${v} panne(s) ou cyberattaque(s) notable(s) en 3 mois`, health: v => `${v} alerte(s) sanitaire(s) en 3 mois`,
        ipc: v => `${v} % de la population en insécurité alimentaire aiguë (IPC 3+)`, idp: v => `${fmtN(v)} personnes déplacées`,
      },
      ipc_src: 'IPC via HDX HAPI', idp_src: 'OIM-DTM via HDX HAPI', incidents12: 'Incidents de sécurité sur 12 mois', so12: 'Troubles civils et politiques sur 12 mois', hz12: 'Aléas, pannes et épidémies sur 12 mois',
      rain_chart: 'Précipitations mensuelles (mm)', temp_chart: 'Température moyenne (°C)', soil_chart: 'Humidité du sol racinaire (0–1)',
      credits: 'Sources', see_incidents: 'Voir les incidents de la zone', score_at: 'Indice au', trends: 'Tendances qui s’appliquent ici', comp: 'Composantes',
      val_title: 'Validation sur les crises passées', val_level: 'Niveau de l’indice', val_n: 'Subdivisions × mois', val_rate: 'Aggravation dans les 3 mois',
      val_txt: (a, b, h, base) => `De ${a} à ${b}, l’indice a été recalculé chaque mois avec les seules données disponibles à ce moment (climat et incidents ; l’humanitaire n’a pas d’historique), pour les subdivisions ayant connu au moins un incident. Aggravation = incidents de sécurité au moins 1,5 fois plus nombreux dans les ${h} mois suivants (taux moyen : ${base}). Un indice utile montre un taux qui monte avec le niveau.`,
    },
    en: {
      hint: 'Finest level of detail: each subdivision (region, state, province) combines climate, verified incidents by driver family and, where available, the humanitarian situation, to spot where risks converge before things deteriorate. Monthly data.',
      month: 'Month', dataset: 'Dataset', overlay: 'Overlay the month’s incidents',
      g_syn: 'Summary', g_clim: 'Climate & environment', g_sec: 'Terrorism, conflict & crime', g_soc: 'Society, hazards & infrastructure', g_hum: 'Humanitarian crises',
      score: 'Risk convergence index', rain: 'Rainfall (anomaly)', temp: 'Temperature (anomaly)', soil: 'Soil moisture (anomaly)',
      inc: 'Security incidents', res: 'Resource-related conflict', so: 'Civil unrest & political crises', hz: 'Hazards, outages, cyber & epidemics',
      ipc: 'Food insecurity (IPC 3+)', idp: 'Internally displaced people',
      top: 'Most exposed subdivisions', loading: 'Loading subdivisions…',
      missing: 'Subdivisions not available yet for this scope: the robot loads boundaries and climate region by region (global coverage within two to three days).',
      pending: n => `${n} country(ies) still loading in this region.`, no_clim: 'climate data loading',
      levels: { 1: 'Low', 2: 'Moderate', 3: 'High', 4: 'Very high' },
      no_data: 'no data', dry: 'dry season', normal: 'normal', avg: 'average', range: 'min–max over the previous 15 years',
      drivers: 'Drivers', method: 'Index method', hum_na: 'not applicable (no humanitarian crisis tracked)',
      method_txt: '0–100 index with five components matching the trend driver families: climate & environment (30 points: 3-month rainfall, abnormal heat, dry soils), terrorism, conflict & crime (30: 3-month incident volume, increase vs the previous 12 months, resource-related conflict), society & politics (15: civil unrest and political crises), hazards, infrastructure & health (10: disasters, outages, cyberattacks, epidemics of severity 2+), humanitarian crises (15: IPC 3+, displacement). Without humanitarian data the index is rescaled to 100. It flags convergence, not certainty: check against the trends and analysis.',
      dr: {
        rain_deficit: v => `Rainfall at ${v}% of normal over 3 months`, rain_excess: v => `Rainfall at ${v}% of normal over 3 months (flood risk)`,
        heat: v => `Temperatures ${v} °C above normal`, soil_record: () => 'Soils drier than in any previous year', soil_dry: () => 'Soils drier than normal',
        conflict_up: v => `Security incidents up ${v}%`, conflict_new: v => `${v} security incidents in a previously quiet area`, incidents: v => `${v} security incident(s) in 3 months`,
        resource: v => `${v} resource-related incident(s) (water, land, livestock…)`, unrest_up: v => `Civil and political unrest rising (${v} in 3 months)`,
        unrest: v => `${v} civil or political unrest event(s) in 3 months`, political: v => `${v} political crisis event(s) in 3 months`,
        haz: v => `${v} notable natural disaster(s) in 3 months`, infra: v => `${v} notable outage(s) or cyberattack(s) in 3 months`, health: v => `${v} health alert(s) in 3 months`,
        ipc: v => `${v}% of the population in acute food insecurity (IPC 3+)`, idp: v => `${fmtN(v)} internally displaced people`,
      },
      ipc_src: 'IPC via HDX HAPI', idp_src: 'IOM-DTM via HDX HAPI', incidents12: 'Security incidents over 12 months', so12: 'Civil & political unrest over 12 months', hz12: 'Hazards, outages & epidemics over 12 months',
      rain_chart: 'Monthly rainfall (mm)', temp_chart: 'Mean temperature (°C)', soil_chart: 'Root-zone soil wetness (0–1)',
      credits: 'Sources', see_incidents: 'Show incidents in this area', score_at: 'Index as of', trends: 'Trends that apply here', comp: 'Components',
      val_title: 'Back-test on past crises', val_level: 'Index level', val_n: 'Subdivisions × months', val_rate: 'Escalation within 3 months',
      val_txt: (a, b, h, base) => `From ${a} to ${b}, the index was recomputed each month using only the data available at the time (climate and incidents; humanitarian data has no history), for subdivisions with at least one incident. Escalation = at least 1.5 times more security incidents over the next ${h} months (average rate: ${base}). A useful index shows a rate rising with the level.`,
    },
  };
  const tx = k => (TXT[B.lang()] || TXT.fr)[k];
  const fmtN = n => n == null ? '—' : Number(n).toLocaleString(B && B.lang() === 'en' ? 'en-GB' : 'fr-FR');
  const DATASETS = [['g_syn', ['score']], ['g_clim', ['rain', 'temp', 'soil']], ['g_sec', ['inc', 'res']], ['g_soc', ['so', 'hz']], ['g_hum', ['ipc', 'idp']]];
  const LEVEL_COLORS = { 1: '#5FA37C', 2: '#E3B505', 3: '#EE7D22', 4: '#C0263B' };
  const RAIN = [[0.5, '#8C510A'], [0.75, '#D8B365'], [0.9, '#F2DDA4'], [1.1, '#EEF0EC'], [1.25, '#B7E1DA'], [1.5, '#5AB4AC'], [Infinity, '#01665E']];
  const TEMP = [[-1, '#2166AC'], [-0.3, '#92C5DE'], [0.3, '#EEF0EC'], [0.8, '#FDB863'], [1.5, '#E66101'], [Infinity, '#B2182B']];
  const SOIL = [[-0.15, '#8C510A'], [-0.07, '#D8B365'], [0.07, '#EEF0EC'], [0.15, '#A6D96A'], [Infinity, '#1A9641']];
  const INC = [[0, '#EEF0EC'], [2, '#FCD9C4'], [5, '#F9A77B'], [10, '#EE6A3B'], [20, '#C9302C'], [Infinity, '#7F0F1E']];
  const IPC = [[0.1, '#CDFACD'], [0.2, '#FAE61E'], [0.3, '#E67800'], [0.4, '#C80000'], [Infinity, '#640000']];
  const IDP = [[10000, '#EFEDF5'], [50000, '#BCBDDC'], [200000, '#9E9AC8'], [500000, '#756BB1'], [Infinity, '#54278F']];
  const pick = (scale, v) => scale.find(([lim]) => v <= lim)[1];
  const SERIES = { inc: 'all', res: 'res', so: 'so', hz: 'hz' };

  function index() { return window.VS_EW; }
  function regionData() { return (window.VS_EW_R || {})[S.region]; }
  function units() { const r = regionData(); return r ? r.units.filter(u => !S.country || u.iso === S.country) : []; }
  function monthIdx() { const d = index(); const i = d.months.indexOf(S.month); return i < 0 ? d.months.length - 1 : i; }
  function secIdx() { const d = index(); const i = d.sec_months.indexOf(S.month); return i < 0 ? d.sec_months.length - 1 : i; }

  /** Valeur d'une subdivision pour la donnée affichée : {v, label, color} */
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
    if (SERIES[ds]) { const n = (u.sec[SERIES[ds]] || [])[j] || 0; return { v: n, color: pick(INC, n), label: `${n}` }; }
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
    if (SERIES[ds]) return ['0', '1–2', '3–5', '6–10', '11–20', '> 20'].map((l, k) => row(INC[k][1], l)).join('');
    if (ds === 'ipc') return ['< 10 %', '10–20 %', '20–30 %', '30–40 %', '> 40 %'].map((l, k) => row(IPC[k][1], l)).join('');
    if (ds === 'idp') return ['< 10 000', '10–50 000', '50–200 000', '200–500 000', '> 500 000'].map((l, k) => row(IDP[k][1], l)).join('');
    return '';
  }
  function monthLabel(ym, long) {
    const d = new Date(ym + '-15T12:00:00Z');
    return d.toLocaleDateString(B.lang() === 'en' ? 'en-GB' : 'fr-FR', long ? { month: 'long', year: 'numeric' } : { month: 'short', year: '2-digit' });
  }

  /* ------------------------------------------------------------------ couche carte */
  function clearLayer() {
    if (layer) { B.map.removeLayer(layer); layer = null; }
    if (circles) { B.map.removeLayer(circles); circles = null; }
  }
  function drawLayer() {
    clearLayer();
    if (!host || !index() || !regionData()) return;
    const us = units(), dark = B.theme() === 'dark';
    const byId = Object.fromEntries(us.map(u => [u.id, u]));
    const feats = us.map(u => ({ type: 'Feature', properties: { id: u.id }, geometry: { type: 'MultiPolygon', coordinates: u.g } }));
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
    if (S.overlay && !SERIES[S.dataset]) {
      const j = secIdx();
      circles = L.layerGroup(us.filter(u => u.sec.all[j]).map(u => L.circleMarker([u.c[0], u.c[1]], {
        pane: 'ewPane', radius: 4 + Math.sqrt(u.sec.all[j]) * 3, color: '#7F0F1E', weight: 1.2, fillColor: '#C9302C', fillOpacity: 0.55, interactive: false,
      }))).addTo(B.map);
    }
  }

  /* ------------------------------------------------------------------ panneau */
  function render() {
    const el = host; if (!el) return;
    const d = index();
    if (!d || !regionData()) {
      const ri = d && d.regions[S.region];
      el.innerHTML = `<p class="hint">${loading[S.region] ? tx('loading') : tx('missing')}</p>${ri && ri.pending && ri.pending.length ? `<p class="hint">${tx('pending')(ri.pending.length)}</p>` : ''}`;
      return;
    }
    if (!d.months.includes(S.month)) S.month = d.months[d.months.length - 1];
    const us = units(), ri = d.regions[S.region] || {};
    if (!us.length) { el.innerHTML = `<p class="hint">${tx('missing')}</p>`; return; }
    const ranked = us.map(u => ({ u, v: valueOf(u, S.dataset) })).filter(x => x.v && !x.v.dry)
      .sort((a, b) => (S.dataset === 'rain' ? Math.abs(1 - b.v.v) - Math.abs(1 - a.v.v) : b.v.v - a.v.v)).slice(0, 10);
    const pend = (ri.pending || []).filter(c => !S.country || c === S.country);
    el.innerHTML = `
      <p class="hint">${tx('hint')}</p>
      <div class="ew-controls">
        <label>${tx('month')}<select id="ew-month">${d.months.slice().reverse().map(m => `<option value="${m}"${m === S.month ? ' selected' : ''}>${B.esc(monthLabel(m, true))}</option>`).join('')}</select></label>
      </div>
      <div class="ew-datasets" role="radiogroup" aria-label="${B.esc(tx('dataset'))}">
        ${DATASETS.map(([g, list]) => `<div class="ew-group"><div class="fgroup-title"><span>${tx(g)}</span></div>
          ${list.map(k => `<label class="ew-ds${k === S.dataset ? ' on' : ''}"><input type="radio" name="ew-ds" value="${k}"${k === S.dataset ? ' checked' : ''}>${B.esc(tx(k))}</label>`).join('')}</div>`).join('')}
      </div>
      <label class="switch"><input type="checkbox" id="ew-overlay"${S.overlay ? ' checked' : ''}><span>${tx('overlay')}</span></label>
      <div class="ew-legend"><div class="card-title">${B.esc(tx(S.dataset))}${S.dataset === 'score' ? ` · ${tx('score_at')} ${B.esc(monthLabel(d.months[d.months.length - 1], true))}` : S.dataset === 'ipc' || S.dataset === 'idp' ? '' : ` · ${B.esc(monthLabel(S.month, true))}`}</div><div class="row">${legend(S.dataset)}</div></div>
      ${pend.length ? `<p class="hint">${tx('pending')(pend.length)}</p>` : ''}
      <div class="d-sec"><h3>${tx('top')}</h3><ol class="ew-rank">${ranked.map(({ u, v }) => `<li data-ew="${u.id}"><span class="sw" style="background:${v.color}"></span><span class="t">${B.flagImg(u.iso)}${B.esc(u.n)}</span><span class="w">${B.esc(v.label)}</span></li>`).join('') || `<li class="empty">${tx('no_data')}</li>`}</ol></div>
      <details class="ew-method"><summary>${tx('method')}</summary><p class="hint">${tx('method_txt')}</p>${validation(d)}<p class="hint">${tx('credits')} : ${B.esc(d.credits)}</p></details>`;
    el.querySelector('#ew-month').onchange = ev => { S.month = ev.target.value; render(); drawLayer(); };
    el.querySelectorAll('input[name="ew-ds"]').forEach(r => { r.onchange = () => { S.dataset = r.value; save(); render(); drawLayer(); }; });
    el.querySelector('#ew-overlay').onchange = ev => { S.overlay = ev.target.checked; save(); drawLayer(); };
    el.querySelectorAll('[data-ew]').forEach(li => { li.onclick = () => { B.closePanelMobile(); select(li.dataset.ew, true); }; });
  }

  function validation(d) {
    const v = d.validation; if (!v || !v.by_level) return '';
    const pct = x => x == null ? '—' : `${Math.round(x * 1000) / 10} %`;
    const rows = [1, 2, 3, 4].map(l => { const b = v.by_level[l] || {}; return `<tr><td><i class="sq" style="background:${LEVEL_COLORS[l]}"></i> ${B.esc(tx('levels')[l])}</td><td>${fmtN(b.n || 0)}</td><td><strong>${pct(b.rate)}</strong></td></tr>`; }).join('');
    return `<div class="ew-valid"><div class="card-title">${B.esc(tx('val_title'))}</div><p class="hint">${B.esc(tx('val_txt')(monthLabel(v.period[0], true), monthLabel(v.period[1], true), v.horizon_months, pct(v.base_rate)))}</p>
      <table class="ew-vt"><thead><tr><th>${B.esc(tx('val_level'))}</th><th>${B.esc(tx('val_n'))}</th><th>${B.esc(tx('val_rate'))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  /* ------------------------------------------------------------------ fiche d'une subdivision */
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
    if (!arr || !arr.some(Boolean)) return '';
    const W = 320, H = 96, P = { l: 22, r: 6, t: 8, b: 20 };
    const hi = Math.max(1, ...arr), x = i => P.l + (i + 0.5) * (W - P.l - P.r) / months.length, bw = (W - P.l - P.r) / months.length * 0.62;
    const y = v => P.t + (hi - v) * (H - P.t - P.b) / hi;
    return `<figure class="ew-chart"><figcaption>${B.esc(title)}</figcaption><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${B.esc(title)}">
      <text x="${P.l - 4}" y="${y(hi) + 3}" text-anchor="end">${hi}</text><line x1="${P.l}" x2="${W - P.r}" y1="${y(hi)}" y2="${y(hi)}" class="grid"/><line x1="${P.l}" x2="${W - P.r}" y1="${y(0)}" y2="${y(0)}" class="grid"/>
      ${arr.map((v, i) => `<rect x="${x(i) - bw / 2}" y="${y(v)}" width="${bw}" height="${Math.max(0.5, y(0) - y(v))}" rx="1.5" fill="${color}" opacity="${months[i] === S.month ? 1 : 0.75}"/>`).join('')}
      ${months.map((m, i) => i % 2 === 0 ? `<text x="${x(i)}" y="${H - 5}" text-anchor="middle">${B.esc(monthLabel(m).replace('.', ''))}</text>` : '').join('')}</svg></figure>`;
  }
  /** Tendances (window.VS_FS) qui s'appliquent à une subdivision : celles de son pays et de sa région */
  function trendsFor(u) {
    const fs = window.VS_FS; if (!fs) return [];
    const cs = fs.scopes[u.iso], parent = cs ? cs.parent : S.region;
    const comp = { climate: 'cl', security: 'co', geopolitics: 'co', social: 'so', political: 'so', infrastructure: 'hz', energy: 'hz', cyber: 'hz', health: 'hz', humanitarian: 'hu' };
    return fs.trends.filter(t => t.scope === u.iso || t.scope === parent || t.scope === S.region)
      .map(t => ({ t, c: [t.family, ...(t.also || [])].map(f => comp[f]).find(Boolean) }))
      .sort((a, b) => ((b.c && u.score.c[b.c]) ? 1 : 0) - ((a.c && u.score.c[a.c]) ? 1 : 0) || b.t.score.all - a.t.score.all).slice(0, 8);
  }
  function select(id, fly) {
    const r = regionData(); const u = r && r.units.find(x => x.id === id); if (!u) return;
    S.selected = id; drawLayer();
    if (fly) { const b = L.geoJSON({ type: 'MultiPolygon', coordinates: u.g }).getBounds(); B.map.flyToBounds(b, { padding: [60, 60], maxZoom: 7, duration: 0.7 }); }
    const d = index(), sc = u.score, secM = d.sec_months.slice(-12), comps = d.components || {};
    const bar = k => {
      const max = (comps[k] || {}).max || 0, v = sc.c[k] || 0, name = (comps[k] || {})[B.lang()] || (comps[k] || {}).fr || k;
      if (k === 'hu' && !sc.hum) return `<div class="bar"><span>${B.esc(name)}</span><span class="hint">${tx('hum_na')}</span><span></span></div>`;
      return `<div class="bar"><span>${B.esc(name)}</span><span class="track"><span class="fill" style="width:${max ? Math.round(v / max * 100) : 0}%"></span></span><span class="v">${v}/${max}</span></div>`;
    };
    const dr = sc.dr.filter(([k]) => k !== 'incidents' || !sc.dr.some(([x]) => x === 'conflict_up' || x === 'conflict_new'));
    const tr = trendsFor(u);
    const charts = chart(u.clim.P, d.months, { title: tx('rain_chart'), color: '#2B7BB9', bars: true, zero: true, fmt: v => Math.round(v) }) +
      chart(u.clim.T, d.months, { title: tx('temp_chart'), color: '#E66101', fmt: v => v.toFixed(0) }) +
      chart(u.clim.W, d.months, { title: tx('soil_chart'), color: '#5E8C31', fmt: v => v.toFixed(2) }) +
      bars12(u.sec.all.slice(-12), secM, '#C9302C', tx('incidents12')) + bars12((u.sec.so || []).slice(-12), secM, '#D9480F', tx('so12')) +
      bars12((u.sec.hz || []).slice(-12), secM, '#495057', tx('hz12'));
    B.openDrawer(`
      <div class="d-head"><div class="d-kicker">${B.esc(tx('score'))}</div>
        <h2 class="d-title">${B.flagImg(u.iso, 24)}${B.esc(u.n)} <span class="muted" style="font-weight:400;font-size:14px">· ${B.esc(B.countryName(u.iso))}</span></h2>
        <div class="risk-big"><span class="lvl" style="background:${LEVEL_COLORS[sc.lvl]}">${sc.v}</span><div><div class="name">${B.esc(tx('levels')[sc.lvl])}</div>
          <div class="desc">${tx('score_at')} ${B.esc(monthLabel(d.months[d.months.length - 1], true))}${u.ok ? '' : ` · ${tx('no_clim')}`}</div></div></div></div>
      <div class="d-sec"><h3>${tx('comp')}</h3>${['cl', 'co', 'so', 'hz', 'hu'].map(bar).join('')}</div>
      ${dr.length ? `<div class="d-sec"><h3>${tx('drivers')}</h3><ul class="ew-drivers">${dr.map(([k, v]) => tx('dr')[k] ? `<li>${B.esc(tx('dr')[k](v))}</li>` : '').join('')}</ul></div>` : ''}
      ${tr.length ? `<div class="d-sec"><h3>${tx('trends')}</h3><ul class="mini-list">${tr.map(({ t }) => `<li data-fst="${t.id}"><span class="t">${B.esc((t.title || {})[B.lang()] || t.title.fr)}</span><span class="w">${t.score.all}</span></li>`).join('')}</ul></div>` : ''}
      ${charts ? `<div class="d-sec">${charts}</div>` : ''}
      ${sc.hum ? `<div class="d-sec"><h3>${tx('g_hum')}</h3><ul class="mini-list">
        <li><span class="t">${tx('ipc')}</span><span class="w">${u.hum.ipc3 == null ? tx('no_data') : `${Math.round(u.hum.ipc3 * 100)} % · ${B.esc(u.hum.ipc_end || '')}`}</span></li>
        <li><span class="t">${tx('idp')}</span><span class="w">${u.hum.idp == null ? tx('no_data') : `${fmtN(u.hum.idp)} · ${B.esc(u.hum.idp_end || '')}`}</span></li>
      </ul><div class="hint">${tx('ipc_src')} · ${tx('idp_src')}</div></div>` : ''}
      <div class="d-sec"><button class="btn" id="ew-see">${B.icon('siren')}${tx('see_incidents')}</button></div>
      <div class="d-sec"><div class="hint">${tx('method_txt')}</div></div>`, 'ew', id);
    const see = document.getElementById('ew-see');
    if (see) see.onclick = () => { const b = L.geoJSON({ type: 'MultiPolygon', coordinates: u.g }).getBounds(); B.showIncidents(b); };
    document.querySelectorAll('#drawer [data-fst]').forEach(x => { x.onclick = () => { if (window.AngorFS) window.AngorFS.openTrend(x.dataset.fst); }; });
    const li = document.querySelector(`[data-ew="${id}"]`); if (li) li.classList.add('on');
  }

  /* ------------------------------------------------------------------ cycle de vie */
  function ensure(rid) {
    const jobs = [];
    if (!window.VS_EW) jobs.push(loading.index || (loading.index = B.loadScript('data/early_warning.js').then(() => { loading.index = null; })));
    if (rid && !(window.VS_EW_R || {})[rid]) jobs.push(loading[rid] || (loading[rid] = B.loadScript(`data/early_warning/${rid}.js`).then(() => { loading[rid] = null; })));
    return Promise.all(jobs);
  }
  function fit() {
    if (S.country && window.VS_COUNTRIES) {
      const f = window.VS_COUNTRIES.features.find(x => x.properties.iso2 === S.country);
      const us = units();
      if (us.length) { const g = L.geoJSON({ type: 'FeatureCollection', features: us.map(u => ({ type: 'Feature', geometry: { type: 'MultiPolygon', coordinates: u.g } })) }); B.map.flyToBounds(g.getBounds(), { padding: [30, 30], maxZoom: 7, duration: 0.8 }); return; }
      if (f) { B.map.flyToBounds(L.geoJSON(f).getBounds(), { padding: [30, 30], maxZoom: 7, duration: 0.8 }); return; }
    }
    const bb = (index() && index().regions[S.region] || {}).bbox || S.bbox;
    if (bb) B.map.flyToBounds([[bb[1], bb[0]], [bb[3], bb[2]]], { padding: [20, 20], duration: 0.8 });
  }
  let pendingSelect = null;
  const api = {
    get active() { return !!host; },
    init(bridge) {
      B = bridge;
      if (!B.map.getPane('ewPane')) { B.map.createPane('ewPane'); B.map.getPane('ewPane').style.zIndex = 390; }
    },
    /** Affiche l'alerte précoce d'une région (ou d'un pays de cette région) dans l'élément donné */
    mount(el, opts) {
      const changed = S.region !== opts.region || S.country !== (opts.country || null);
      host = el; S.region = opts.region; S.country = opts.country || null; S.bbox = opts.bbox;
      render();
      ensure(S.region).then(() => {
        if (host !== el) return;
        render(); drawLayer(); if (changed || !pendingSelect) fit();
        if (pendingSelect) { const id = pendingSelect; pendingSelect = null; select(id, true); }
      });
    },
    unmount() { host = null; S.selected = null; clearLayer(); },
    refresh() { if (host) { render(); drawLayer(); } },
    reopen(id) { if (regionData()) select(id); },
    /** Ouvre la fiche d'une subdivision après chargement (appelé depuis une fiche tendance) */
    openUnit(id) { if (regionData() && regionData().units.some(u => u.id === id)) select(id, true); else pendingSelect = id; },
  };
  window.AngorEW = api;
})();
