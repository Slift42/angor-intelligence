"""Meteoalarm (EUMETNET) – vigilances météo officielles orange et rouge de ~38 pays européens.

Chaque service météo national (Météo-France, DWD, AEMET, Met Office…) publie ses vigilances au format CAP,
agrégées par Meteoalarm : https://feeds.meteoalarm.org/api/v1/warnings/feeds-<pays>
Réutilisation : attribuer « Meteoalarm / EUMETNET » et le service national (voir meteoalarm.org, conditions).
Une fiche par pays, type de phénomène et niveau (ex. « Vigilance orange – Vent – France, 12 zones »),
placée au centre du pays (précision « région ») ; la liste des zones figure dans la fiche.
Les vigilances jaunes sont ignorées (trop nombreuses, faible enjeu sûreté).
"""
import hashlib
import time

from .. import http
from ..model import make_event, parse_iso, to_iso

KIND = "events"
URL = "https://feeds.meteoalarm.org/api/v1/warnings/feeds-{slug}"
FEEDS = {
    "AT": "austria", "BE": "belgium", "BA": "bosnia-herzegovina", "BG": "bulgaria", "HR": "croatia", "CY": "cyprus",
    "CZ": "czechia", "DK": "denmark", "EE": "estonia", "FI": "finland", "FR": "france", "DE": "germany",
    "GR": "greece", "HU": "hungary", "IS": "iceland", "IE": "ireland", "IL": "israel", "IT": "italy", "LV": "latvia",
    "LT": "lithuania", "LU": "luxembourg", "MT": "malta", "MD": "moldova", "ME": "montenegro", "NL": "netherlands",
    "MK": "republic-of-north-macedonia", "NO": "norway", "PL": "poland", "PT": "portugal", "RO": "romania",
    "RS": "serbia", "SK": "slovakia", "SI": "slovenia", "ES": "spain", "SE": "sweden", "CH": "switzerland",
    "UA": "ukraine", "GB": "united-kingdom",
}
LEVELS = {"orange": 3, "red": 4}
LEVEL_FR = {3: "orange", 4: "rouge"}
TYPES = {"1": ("Vent", "storm"), "2": ("Neige / verglas", "storm"), "3": ("Orages", "storm"),
         "4": ("Brouillard", "other"), "5": ("Chaleur", "extreme_temp"), "6": ("Grand froid", "extreme_temp"),
         "7": ("Vagues-submersion", "flood"), "8": ("Feux de forêt", "wildfire"), "9": ("Avalanches", "landslide"),
         "10": ("Pluie", "flood"), "12": ("Crues", "flood"), "13": ("Pluie-inondation", "flood")}


def _param(info, name):
    for p in info.get("parameter") or []:
        if (p.get("valueName") or "").lower() == name:
            return p.get("value") or ""
    return ""


def _info(alert):
    infos = alert.get("info") or []
    return next((i for i in infos if str(i.get("language", "")).lower().startswith("en")), infos[0] if infos else {})


def parse(data, iso, now):
    """Regroupe les vigilances orange/rouge actives d'un pays : {(type, niveau): {...}}."""
    groups = {}
    for w in data.get("warnings") or []:
        alert = w.get("alert") or {}
        if (alert.get("msgType") or "Alert") == "Cancel":
            continue
        info = _info(alert)
        lvl_raw = _param(info, "awareness_level")  # ex. « 3; orange; Severe »
        color = next((c for c in LEVELS if c in lvl_raw.lower()), None)
        if not color:
            continue
        expires = parse_iso(info.get("expires"))
        if expires and expires < now:
            continue
        typ = (_param(info, "awareness_type").split(";")[0] or "").strip()
        label, cat = TYPES.get(typ, (info.get("event") or "Météo", "storm"))
        g = groups.setdefault((typ, LEVELS[color]), {"label": label, "category": cat, "areas": [], "sent": None,
                                                     "onset": None, "expires": None, "web": info.get("web"),
                                                     "event": info.get("event") or label, "sender": info.get("senderName")})
        for a in info.get("area") or []:
            name = a.get("areaDesc")
            if name and name not in g["areas"]:
                g["areas"].append(name)
        sent = parse_iso(alert.get("sent") or info.get("effective"))
        onset = parse_iso(info.get("onset") or info.get("effective"))
        if sent and (not g["sent"] or sent > g["sent"]):
            g["sent"] = sent
        if onset and (not g["onset"] or onset < g["onset"]):
            g["onset"] = onset
        if expires and (not g["expires"] or expires > g["expires"]):
            g["expires"] = expires
    return groups


def fetch(cfg, ctx):
    wanted = cfg.get("countries") or list(FEEDS)
    budget = time.time() + float(cfg.get("time_budget_s", 45))
    out, done, fails = [], 0, 0
    for iso in wanted:
        if time.time() > budget or (fails >= 4 and not done):
            break
        slug = FEEDS.get(iso)
        pt = ctx.countries.label_point(iso)
        if not slug or not pt:
            continue
        try:
            data = http.get_json(URL.format(slug=slug), retries=0, timeout=20)
        except Exception as exc:
            fails += 1
            ctx.log(f"  Meteoalarm {iso} : {type(exc).__name__}")
            continue
        done += 1
        for (typ, sev), g in parse(data, iso, ctx.now).items():
            if not g["sent"]:
                continue
            n = len(g["areas"])
            areas = ", ".join(g["areas"][:12]) + (f" (+{n - 12})" if n > 12 else "")
            name = ctx.countries.name(iso, "fr")
            until = f" jusqu'au {g['expires']:%d/%m %H:%M} UTC" if g["expires"] else ""
            uid = hashlib.sha1(f"{iso}{typ}{sev}{g['onset']:%Y%m%d}".encode()).hexdigest()[:10] if g["onset"] else typ
            out.append(make_event(
                id=f"meteoalarm-{iso}-{uid}", source="Meteoalarm", category=g["category"], severity=sev,
                title=f"Vigilance {LEVEL_FR[sev]} {g['label'].lower()} – {name} ({n} zone{'s' if n > 1 else ''})",
                summary=f"{g['event']}{until}. Zones : {areas}." + (f" Source : {g['sender']}." if g["sender"] else ""),
                date=to_iso(g["sent"]), start=to_iso(g["onset"] or g["sent"]), lat=pt[0], lon=pt[1],
                url=g["web"] or "https://meteoalarm.org", source_url="https://meteoalarm.org",
                place=areas[:160], precision="region", country=iso,
            ))
    if not done:
        raise RuntimeError("aucun flux Meteoalarm joignable")
    ctx.log(f"  Meteoalarm : {done} pays lus, {len(out)} vigilance(s) orange/rouge")
    return out
