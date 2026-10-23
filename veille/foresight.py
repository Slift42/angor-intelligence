"""Tendances de risques (espace Anticipation, onglet « Tendances », v0.26).

Méthode d'anticipation des menaces, région par région et pays par pays : des facteurs (climat, géopolitique,
politique, société, sécurité, cyber, économie, finances, énergie, infrastructures, santé, démographie, technologies)
produisent des tendances de risques. Chaque tendance est évaluée par l'analyste :
- vraisemblance (1 à 5, échelle de probabilité inspirée de l'ICD 203 et du PHIA Probability Yardstick) ;
- impact sur l'entreprise et sur le voyageur (1 à 5) ;
- horizon (3, 12 ou 36 mois), dynamique (hausse, stable, baisse), confiance (faible, moyenne, élevée) ;
- signaux datés et sourcés, indicateurs d'alerte, scénario de rupture, implications et recommandations.

Ce module ne remplace pas l'analyste : il calcule les scores (vraisemblance × impact), contrôle la qualité des fiches
(sources existantes, au moins deux éditeurs indépendants, part limitée de sources de faible cotation, dates
cohérentes), signale les fiches à réviser (date de revue dépassée) et les surprises : incidents Angor vérifiés en
nette hausse dans le périmètre d'une tendance que l'analyste ne voyait pas monter.

Fichiers : config/foresight/method.json (échelles, familles, facteurs, indicateurs), sources.json (bibliographie),
regions/<id>.json et countries/<ISO2>.json (tendances). Sortie : docs/data/foresight.js (window.VS_FS).
Documentation : doc/FORESIGHT.md ; page publique : docs/methodologie.html.
"""
import json
import re
from datetime import datetime, timedelta, timezone

from .config import CONFIG_DIR
from .model import CATEGORIES, parse_iso
from .publish import write_js

BASE = CONFIG_DIR / "foresight"
HORIZONS = ("3m", "12m", "36m")
CONFIDENCE = ("low", "medium", "high")
AUDIENCES = ("business", "travel")
DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
HISTORY_MONTHS = 36
SKEW = timedelta(days=1)  # fuseaux horaires : une fiche datée « aujourd'hui » à Paris peut précéder minuit UTC
TEXT_KEYS = ("title", "summary")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load(base=BASE):
    """{method, sources, scopes} : scopes = régions et pays décrits (fichiers regions/ et countries/)."""
    method = _read(base / "method.json")
    sources = {k: v for k, v in _read(base / "sources.json").items() if not k.startswith("_")}
    scopes = {}
    for sub in ("regions", "countries"):
        folder = base / sub
        if folder.is_dir():
            for f in sorted(folder.glob("*.json")):
                s = _read(f)
                scopes[s["id"]] = s
    return {"method": method, "sources": sources, "scopes": scopes}


def regions(base=BASE):
    """Régions du monde {id: {fr, en, countries, bbox}} : périmètres communs aux tendances et à l'alerte précoce."""
    out = {}
    folder = base / "regions"
    for f in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        r = _read(f)
        out[r["id"]] = {"fr": r["fr"], "en": r["en"], "countries": r["countries"], "bbox": r["bbox"]}
    return out


# famille de facteurs d'une tendance → composante de l'indice d'alerte précoce par subdivision (early_warning.py)
FAMILY_COMPONENT = {"climate": "cl", "security": "co", "geopolitics": "co", "social": "so", "political": "so",
                    "infrastructure": "hz", "energy": "hz", "cyber": "hz", "health": "hz", "humanitarian": "hu"}


def _date(s):
    """Date (début de période) d'une chaîne AAAA, AAAA-MM ou AAAA-MM-JJ."""
    parts = [int(p) for p in s.split("-")]
    return datetime(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1, tzinfo=timezone.utc)


def trend_sources(t):
    """Sources citées par une tendance (signaux), sans doublon, dans l'ordre d'apparition."""
    out = []
    for s in t.get("signals") or []:
        for k in s.get("src") or []:
            if k not in out:
                out.append(k)
    return out


def validate(cfg, now=None):
    """Liste des anomalies (chaîne lisible par fiche). Vide = configuration publiable."""
    now = now or datetime.now(timezone.utc)
    m, sources, scopes = cfg["method"], cfg["sources"], cfg["scopes"]
    rules = m.get("rules") or {}
    families = m.get("families") or {}
    drivers = {d["id"]: d for d in m.get("drivers") or []}
    sectors = m.get("sectors") or {}
    rel = (m.get("scales") or {}).get("source_reliability") or {}
    err = []
    for d in drivers.values():
        if d.get("family") not in families:
            err.append(f"facteur {d['id']} : famille inconnue {d.get('family')}")
        for ind in d.get("indicators") or []:
            for k in ind.get("src") or []:
                if k not in sources:
                    err.append(f"facteur {d['id']} : source inconnue {k}")
    for k, s in sources.items():
        for f in ("t", "pub", "url", "kind", "rel"):
            if not s.get(f):
                err.append(f"source {k} : champ « {f} » manquant")
        if s.get("rel") and s["rel"] not in rel:
            err.append(f"source {k} : cotation {s['rel']} inconnue")
        if s.get("url") and not (s["url"].startswith("https://") or s["url"].endswith(".html")):
            err.append(f"source {k} : lien non sécurisé {s['url']}")
    seen = set()
    owner = {}
    for sid, sc in scopes.items():
        if sc.get("type") == "region":
            if not (isinstance(sc.get("bbox"), list) and len(sc["bbox"]) == 4):
                err.append(f"région {sid} : emprise (bbox) absente")
            for c in sc.get("countries") or []:
                if c in owner:
                    err.append(f"pays {c} rattaché à deux régions ({owner[c]}, {sid})")
                owner[c] = sid
    for sid, sc in scopes.items():
        if sc.get("type") not in ("region", "country"):
            err.append(f"périmètre {sid} : type inconnu")
        if sc.get("type") == "country":
            parent = scopes.get(sc.get("parent"))
            if not parent:
                err.append(f"pays {sid} : région parente {sc.get('parent')} absente")
            elif sid not in parent.get("countries", []):
                err.append(f"pays {sid} : absent de la liste des pays de {parent['id']}")
        for t in sc.get("trends") or []:
            tid = t.get("id", "?")
            where = f"{sid}/{tid}"
            if tid in seen:
                err.append(f"{where} : identifiant en double")
            seen.add(tid)
            if t.get("family") not in families:
                err.append(f"{where} : famille inconnue {t.get('family')}")
            for f in t.get("also") or []:
                if f not in families:
                    err.append(f"{where} : famille secondaire inconnue {f}")
            for k in TEXT_KEYS:
                if not ((t.get(k) or {}).get("fr") and (t.get(k) or {}).get("en")):
                    err.append(f"{where} : « {k} » doit exister en français et en anglais")
            for d in t.get("drivers") or []:
                if d not in drivers:
                    err.append(f"{where} : facteur inconnu {d}")
            if not t.get("drivers"):
                err.append(f"{where} : aucun facteur")
            if t.get("likelihood") not in (1, 2, 3, 4, 5):
                err.append(f"{where} : vraisemblance hors échelle")
            for a in AUDIENCES:
                if (t.get("impact") or {}).get(a) not in (1, 2, 3, 4, 5):
                    err.append(f"{where} : impact {a} hors échelle")
            if t.get("horizon") not in HORIZONS:
                err.append(f"{where} : horizon inconnu")
            if t.get("momentum") not in (-1, 0, 1):
                err.append(f"{where} : dynamique hors échelle")
            if t.get("confidence") not in CONFIDENCE:
                err.append(f"{where} : confiance inconnue")
            for s in t.get("sectors") or []:
                if s not in sectors:
                    err.append(f"{where} : secteur inconnu {s}")
            sigs = t.get("signals") or []
            if not sigs:
                err.append(f"{where} : aucun signal")
            for i, s in enumerate(sigs, 1):
                if not (s.get("fr") and s.get("en")):
                    err.append(f"{where} : signal {i} sans texte bilingue")
                if not s.get("src"):
                    err.append(f"{where} : signal {i} sans source")
                for k in s.get("src") or []:
                    if k not in sources:
                        err.append(f"{where} : signal {i}, source inconnue {k}")
                if s.get("d") is not None:
                    if not DATE_RE.match(str(s["d"])):
                        err.append(f"{where} : signal {i}, date illisible {s['d']}")
                    elif _date(s["d"]) > now + SKEW:
                        err.append(f"{where} : signal {i} daté dans le futur")
            cited = [k for k in trend_sources(t) if k in sources]
            if len(cited) < rules.get("min_sources_per_trend", 2):
                err.append(f"{where} : moins de {rules.get('min_sources_per_trend', 2)} sources")
            pubs = {sources[k]["pub"] for k in cited}
            if len(pubs) < rules.get("min_independent_publishers", 2):
                err.append(f"{where} : moins de {rules.get('min_independent_publishers', 2)} éditeurs indépendants")
            low = [k for k in cited if sources[k].get("rel") in ("D", "E", "F")]
            if cited and len(low) / len(cited) > rules.get("max_low_grade_share", 0.5):
                err.append(f"{where} : trop de sources de faible cotation ({len(low)}/{len(cited)})")
            if not t.get("watch"):
                err.append(f"{where} : aucun indicateur d'alerte")
            rev = t.get("reviewed") or sc.get("reviewed")
            if not rev or not DATE_RE.match(rev):
                err.append(f"{where} : date de revue absente")
            elif _date(rev) > now + SKEW:
                err.append(f"{where} : date de revue dans le futur")
            for c in t.get("live") or []:
                if c not in CATEGORIES:
                    err.append(f"{where} : catégorie d'incident inconnue {c}")
    ids = {t["id"] for sc in scopes.values() for t in sc.get("trends") or [] if t.get("id")}
    for sc in scopes.values():
        for t in sc.get("trends") or []:
            for link in t.get("links") or []:
                if link not in ids:
                    err.append(f"{sc['id']}/{t.get('id')} : lien vers une tendance inconnue {link}")
    return err


def level_of(score, levels):
    for lv in levels:
        if lv["min"] <= score <= lv["max"]:
            return lv["key"]
    return levels[-1]["key"] if score > levels[-1]["max"] else levels[0]["key"]


def score(t):
    """Scores 1–25 : vraisemblance × impact (entreprise, voyageur, et le plus élevé des deux)."""
    L, imp = t["likelihood"], t["impact"]
    return {"business": L * imp["business"], "travel": L * imp["travel"], "all": L * max(imp["business"], imp["travel"])}


def live_signal(t, countries, events, now, params):
    """Incidents vérifiés récents dans le périmètre et les catégories de la tendance, comparés à la période
    précédente : {n, base, ratio, dir} ; dir = 1 (hausse nette), -1 (baisse nette), 0. None sans catégorie."""
    cats = set(t.get("live") or [])
    if not cats:
        return None
    win = int(params.get("window_days", 30))
    base_days = int(params.get("baseline_days", 90))
    start_recent = now - timedelta(days=win)
    start_base = start_recent - timedelta(days=base_days)
    isos = set(countries)
    recent = base = 0
    for e in events:
        if e.get("category") not in cats or e.get("country") not in isos:
            continue
        try:
            d = parse_iso(e.get("date"))
        except (TypeError, ValueError):
            continue
        if d is None or d > now:
            continue
        if d >= start_recent:
            recent += 1
        elif d >= start_base:
            base += 1
    base_rate = base * win / base_days
    ratio = (recent + 1) / (base_rate + 1)
    mn = int(params.get("min_events", 3))
    direction = 0
    if recent >= mn and ratio >= float(params.get("up_ratio", 1.5)):
        direction = 1
    elif base_rate >= mn and ratio <= float(params.get("down_ratio", 0.6)):
        direction = -1
    return {"n": recent, "base": round(base_rate, 1), "ratio": round(ratio, 2), "dir": direction,
            "cats": sorted(cats), "days": win}


def _review_due(t, sc, now, horizons):
    rev = _date(t.get("reviewed") or sc["reviewed"])
    days = int((horizons.get(t["horizon"]) or {}).get("review_days", 60))
    return (now - rev).days > days, (rev + timedelta(days=days)).date().isoformat()


def pressure(scores, top_n=5):
    """Pression de risque 0–100 : moyenne des N scores les plus élevés, rapportée au maximum (25)."""
    top = sorted(scores, reverse=True)[:top_n]
    return round(sum(top) / len(top) * 4) if top else 0


def _ew_top(units, comp=None, n=5):
    key = (lambda u: (u["c"].get(comp, 0), u["v"])) if comp else (lambda u: u["v"])
    pool = [u for u in units if (u["c"].get(comp, 0) if comp else u["v"]) > 0]
    return [[u["id"], u["n"], u["iso"], u["v"], u["lvl"], u["c"].get(comp, 0) if comp else u["v"], u["reg"]]
            for u in sorted(pool, key=key, reverse=True)[:n]]


def _ew_summary(units):
    return {"n": len(units), "with_climate": sum(1 for u in units if u.get("ok")),
            "high": sum(1 for u in units if u["lvl"] >= 3), "top": _ew_top(units)}


def build(cfg, events, now, history=None, ew=None, ind=None):
    """Charge utile publiée : méthode, sources citées, périmètres (avec synthèse) et tendances calculées.
    ew : sortie de early_warning.build (subdivisions), pour descendre au niveau de détail le plus fin ;
    ind : indicateurs structurels par pays (indicators.py)."""
    ew_units = (ew or {}).get("units") or []
    ew_by_iso, ew_by_reg = {}, {}
    for u in ew_units:
        ew_by_iso.setdefault(u["iso"], []).append(u)
        ew_by_reg.setdefault(u["reg"], []).append(u)
    m, sources, scopes = cfg["method"], cfg["sources"], cfg["scopes"]
    scales = m["scales"]
    levels = scales["levels"]
    rules = m.get("rules") or {}
    params = m.get("live") or {}
    trends = []
    for sid, sc in scopes.items():
        countries = sc.get("countries") if sc["type"] == "region" else [sid]
        for t in sc.get("trends") or []:
            sc_ = score(t)
            due, due_on = _review_due(t, sc, now, scales["horizon"])
            live = live_signal(t, countries, events, now, params)
            flags = []
            if due:
                flags.append("review_due")
            if live and live["dir"] == 1 and t["momentum"] <= 0:
                flags.append("live_up")
            if live and live["dir"] == -1 and t["momentum"] >= 1:
                flags.append("live_down")
            hist = [[mo, (snap or {}).get(t["id"])] for mo, snap in sorted((history or {}).items())]
            item = {k: v for k, v in t.items()}
            item.update({"scope": sid, "score": sc_, "lvl": level_of(sc_["all"], levels),
                         "lvl_business": level_of(sc_["business"], levels), "lvl_travel": level_of(sc_["travel"], levels),
                         "sources": trend_sources(t), "reviewed": t.get("reviewed") or sc["reviewed"], "review_by": due_on,
                         "live": live, "flags": flags, "history": [h for h in hist if h[1] is not None][-12:]})
            item["live_cats"] = t.get("live") or []
            comp = next((FAMILY_COMPONENT[f] for f in [t["family"], *(t.get("also") or [])] if f in FAMILY_COMPONENT), None)
            if comp and ew_units:
                pool = [u for c in countries for u in ew_by_iso.get(c, [])]
                item["units"] = {"comp": comp, "top": _ew_top(pool, comp)}
            trends.append(item)
    by_scope = {}
    for t in trends:
        by_scope.setdefault(t["scope"], []).append(t)
    out_scopes = {}
    for sid, sc in scopes.items():
        if sc["type"] == "region":
            members = sc.get("countries") or []
            out_scopes[sid] = {"id": sid, "type": "region", "fr": sc["fr"], "en": sc["en"], "countries": members,
                               "bbox": sc.get("bbox"), "outlook": sc.get("outlook"), "reviewed": sc.get("reviewed"),
                               "perimeter_fr": sc.get("perimeter_fr"), "perimeter_en": sc.get("perimeter_en"),
                               "covered": [c for c in members if c in scopes],
                               **({"ew": _ew_summary(ew_by_reg.get(sid, []))} if ew_units else {})}
    # pays : décrits (fichier dédié) ou hérités de leur région (tendances régionales seules)
    for rid, reg in list(out_scopes.items()):
        for iso in reg["countries"]:
            sc = scopes.get(iso)
            out_scopes[iso] = {"id": iso, "type": "country", "parent": rid, "described": bool(sc),
                               **({"fr": sc["fr"], "en": sc["en"], "outlook": sc.get("outlook"), "reviewed": sc.get("reviewed"),
                                   "perimeter_fr": sc.get("perimeter_fr"), "perimeter_en": sc.get("perimeter_en")} if sc else {}),
                               **({"ew": _ew_summary(ew_by_iso.get(iso, []))} if ew_units else {}),
                               **({"ind": (ind or {}).get(iso)} if (ind or {}).get(iso) else {})}
    top_n = int(rules.get("pressure_top_n", 5))
    for sid, s in out_scopes.items():
        if s["type"] == "region":
            own = by_scope.get(sid, [])
            members = [t for c in s["countries"] for t in by_scope.get(c, [])]
            pool = own + members
        else:
            own = by_scope.get(sid, [])
            pool = own + by_scope.get(s["parent"], [])
        fam = {}
        for t in pool:
            fam[t["family"]] = max(fam.get(t["family"], 0), t["score"]["all"])
        lv = {}
        for t in pool:
            lv[t["lvl"]] = lv.get(t["lvl"], 0) + 1
        s["summary"] = {"pressure": pressure([t["score"]["all"] for t in pool], top_n),
                        "pressure_business": pressure([t["score"]["business"] for t in pool], top_n),
                        "pressure_travel": pressure([t["score"]["travel"] for t in pool], top_n),
                        "n": len(pool), "own": len(own), "levels": lv,
                        "families": dict(sorted(fam.items(), key=lambda kv: -kv[1])),
                        "max_lvl": max((t["lvl"] for t in pool), default=0),
                        "flags": sum(1 for t in pool if t["flags"])}
    cited = sorted({k for t in trends for k in t["sources"]} |
                   {k for d in m.get("drivers") or [] for i in d.get("indicators") or [] for k in i.get("src") or []} |
                   {k for k in sources if sources[k].get("kind") == "method"})
    return {"generated": now.replace(microsecond=0).isoformat(), "version": m.get("version"), "updated": m.get("updated"),
            "scales": scales, "rules": rules, "live_params": params, "families": m["families"], "sectors": m.get("sectors", {}),
            "drivers": m.get("drivers", []), "roadmap": m.get("roadmap", []),
            "sources": {k: sources[k] for k in cited if k in sources},
            "scopes": out_scopes, "trends": sorted(trends, key=lambda t: (-t["score"]["all"], -t["likelihood"], t["id"]))}


def public_method(cfg, payload):
    """Version publique (page methodologie.html, sans compte) : méthode, facteurs, bibliographie complète et couverture.
    Les tendances, leurs scores et leurs signaux restent dans foresight.js (données réservées aux comptes validés)."""
    m = cfg["method"]
    cov = [{"id": s["id"], "type": s["type"], "fr": s["fr"], "en": s["en"], "n": len(s.get("trends") or []),
            "reviewed": s.get("reviewed"), **({"parent": s["parent"]} if s.get("parent") else {}),
            **({"nc": len(s.get("countries") or [])} if s["type"] == "region" else {})} for s in cfg["scopes"].values()]
    return {"generated": payload["generated"], "version": m.get("version"), "updated": m.get("updated"),
            "scales": m["scales"], "rules": m.get("rules") or {}, "live_params": m.get("live") or {},
            "families": m["families"], "sectors": m.get("sectors", {}), "drivers": m.get("drivers", []),
            "roadmap": m.get("roadmap", []), "auto": m.get("auto", {}), "coverage": cov, "sources": cfg["sources"]}


def snapshot(store, payload, now):
    """Mémoire mensuelle des scores (évolution affichée sur chaque fiche, rétro-évaluation ultérieure)."""
    st = store.setdefault("state", {}).setdefault("foresight", {})
    hist = st.setdefault("history", {})
    hist[now.strftime("%Y-%m")] = {t["id"]: t["score"]["all"] for t in payload["trends"]}
    for k in sorted(hist)[:-HISTORY_MONTHS]:
        del hist[k]
    return hist


def update(store, events, log, now=None, ew=None, ind=None):
    """Appelé à chaque collecte, après l'alerte précoce : contrôle, calcul et publication (docs/data/foresight.js)."""
    now = now or datetime.now(timezone.utc)
    if not BASE.is_dir():
        return None
    cfg = load()
    errors = validate(cfg, now)
    for e in errors[:20]:
        log(f"  ⚠ tendances : {e}")
    hist = (store.get("state") or {}).get("foresight", {}).get("history") or {}
    payload = build(cfg, events, now, hist, ew, ind)
    snapshot(store, payload, now)
    payload = build(cfg, events, now, store["state"]["foresight"]["history"], ew, ind)
    payload["errors"] = len(errors)
    write_js("foresight.js", "VS_FS", payload)
    write_js("foresight_method.js", "VS_FS_METHOD", public_method(cfg, payload))
    flagged = sum(1 for t in payload["trends"] if t["flags"])
    log(f"  Tendances de risques : {len(payload['trends'])} tendance(s) sur {len(cfg['scopes'])} périmètre(s)"
        + (f", {flagged} à revoir" if flagged else "") + (f", {len(errors)} anomalie(s) de fiche" if errors else ""))
    return payload
