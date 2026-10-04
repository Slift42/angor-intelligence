"""Trafic aérien : instantané à chaque collecte (toutes les 30 min) pour l'espace « Trafic » de la carte.

Source : adsb.lol (réseau communautaire ADS-B, données sous licence ODbL 1.0, API gratuite sans inscription).
Son API ne peut pas être appelée directement depuis le navigateur (pas d'en-tête CORS) : le robot la lit et
publie docs/data/traffic.js.

Contenu :
- aéronefs militaires identifiés dans le monde (/v2/mil) ;
- aéronefs en détresse : codes transpondeur 7500 (détournement), 7600 (panne radio), 7700 (urgence) ;
- tous les aéronefs dans un rayon de 250 milles nautiques autour de zones d'intérêt sûreté.
"""
import time

from . import http
from .publish import write_js

API = "https://api.adsb.lol/v2"
# zones d'intérêt (centre, rayon en milles nautiques, 250 max)
ZONES = {
    "ukraine": (49.0, 32.0, 250), "levant": (33.5, 36.0, 200), "gulf": (27.0, 52.0, 250), "sahel": (15.0, 2.0, 250),
    "redsea": (16.0, 42.0, 250), "taiwan": (24.0, 121.0, 200), "baltic": (57.0, 20.0, 250),
}
SQUAWKS = {"7500": "hijack", "7600": "radio", "7700": "emergency"}


def _compact(a, mil=False):
    if a.get("lat") is None or a.get("lon") is None:
        return None
    alt = a.get("alt_baro")
    return [a.get("hex"), (a.get("flight") or "").strip(), a.get("r") or "", a.get("t") or "",
            round(a["lat"], 3), round(a["lon"], 3), alt if isinstance(alt, (int, float)) else (0 if alt == "ground" else None),
            round(a["gs"]) if isinstance(a.get("gs"), (int, float)) else None,
            round(a["track"]) if isinstance(a.get("track"), (int, float)) else None,
            a.get("squawk") or "", 1 if (mil or (a.get("dbFlags") or 0) & 1) else 0]


def _get(path):
    return http.get_json(f"{API}{path}", timeout=25, retries=1).get("ac") or []


def update(settings, log, now):
    cfg = (settings.get("traffic") or {}).get("air") or {}
    if cfg.get("enabled") is False:
        return None
    t0 = time.time()
    out = {"generated": now.replace(microsecond=0).isoformat(), "source": "adsb.lol",
           "license": "ODbL 1.0 – © adsb.lol contributors", "mil": [], "emergency": [], "zones": {}}
    errors = 0
    try:
        out["mil"] = [x for x in (_compact(a, True) for a in _get("/mil")) if x]
    except Exception as exc:
        errors += 1
        log(f"  Trafic aérien : militaires indisponibles ({type(exc).__name__})")
    for code, kind in SQUAWKS.items():
        try:
            for a in _get(f"/sqk/{code}"):
                x = _compact(a)
                if x:
                    out["emergency"].append(x + [kind])
        except Exception:
            errors += 1
    for zid, (lat, lon, dist) in ZONES.items():
        if time.time() - t0 > 40:
            break
        try:
            acs = [x for x in (_compact(a) for a in _get(f"/lat/{lat}/lon/{lon}/dist/{dist}")) if x]
            out["zones"][zid] = {"n": len(acs), "mil": sum(1 for x in acs if x[10]), "ac": acs[:400]}
        except Exception:
            errors += 1
    if errors >= 6 and not out["mil"]:
        log("  Trafic aérien : adsb.lol injoignable, instantané précédent conservé")
        return None
    write_js("traffic.js", "VS_TRAFFIC", out)
    log(f"  Trafic aérien : {len(out['mil'])} militaires, {len(out['emergency'])} en détresse, "
        f"{sum(z['n'] for z in out['zones'].values())} aéronefs dans {len(out['zones'])} zones ({time.time() - t0:.0f} s)")
    return out
