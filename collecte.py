"""Angor Intelligence – collecte des sources et mise à jour de la carte.

Usage :
    python collecte.py              → collecte toutes les sources activées
    python collecte.py --only usgs gdacs
    python collecte.py --list       → liste les sources et leur état
    python collecte.py --profiles   → force la mise à jour des profils pays (sinon : 1 fois par semaine)
    python collecte.py --no-profiles

Ensuite, ouvrez docs/index.html dans votre navigateur.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

from veille import __version__, ai, analytics, config, enrich, notify, practical, press, profiles, publish, risk
from veille.connectors import REGISTRY, Context
from veille.dedupe import dedupe
from veille.geo import Countries, haversine_km
from veille.http import AuthMissing
from veille.model import now_iso, parse_iso, taxonomy, to_iso


def log(msg):
    print(msg, flush=True)


def id_prefix(src):
    """Préfixe des identifiants produits par une source (pour reconstruire son historique)."""
    return {"usgs": "usgs-", "gdacs": "gdacs-", "eonet": "eonet-", "gdelt_events": "gdelt-",
            "who_don": "who-", "rss": f"rss-{src['id']}-", "jsonapi": f"{src['id']}-",
            "acled": "acled-", "gnews": "gnews-"}.get(src["type"], f"{src['id']}-")


def config_signature(src):
    return hashlib.sha1(json.dumps(src, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def site_alerts(events, sites, min_severity):
    """Événements situés dans le rayon de vigilance d'un site (base des futures alertes e-mail/Telegram)."""
    hits = []
    for site in sites:
        for ev in events:
            if ev["severity"] < site.get("min_severity", min_severity) or ev.get("confidence") == "low":
                continue
            d = haversine_km(site["lat"], site["lon"], ev["lat"], ev["lon"])
            if d <= site.get("radius_km", 50):
                hits.append({"site": site["name"], "event": ev["id"], "distance_km": round(d, 1),
                             "severity": ev["severity"], "title": ev["title"]})
    return sorted(hits, key=lambda h: (-h["severity"], h["distance_km"]))


def main():
    try:  # console Windows : ne jamais planter sur un caractère spécial
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser(description="Collecte de la veille sûreté")
    parser.add_argument("--only", nargs="*", help="identifiants des sources à collecter")
    parser.add_argument("--list", action="store_true", help="lister les sources")
    parser.add_argument("--profiles", action="store_true", help="forcer la mise à jour des profils pays")
    parser.add_argument("--no-profiles", action="store_true", help="ne pas mettre à jour les profils pays")
    args = parser.parse_args()

    config.load_dotenv()
    sources = config.load_json("sources.json")["sources"]
    settings = config.load_json("settings.json", {})
    # vos vrais sites vont dans config/sites.local.json (jamais envoyé sur GitHub)
    sites = (config.load_json("sites.local.json") or config.load_json("sites.json", {"sites": []}))["sites"]
    if os.environ.get("SITES_JSON"):  # en ligne : vrais sites fournis par un Secret GitHub, jamais publiés
        sites = json.loads(os.environ["SITES_JSON"]).get("sites", [])

    if args.list:
        for s in sources:
            flag = "ON " if s.get("enabled") else "off"
            log(f"[{flag}] {s['id']:<22} {s['type']:<15} {s.get('name', '')}")
        return 0

    now = datetime.now(timezone.utc)
    countries = Countries()
    store = publish.load_store()
    product = settings.get("product_name", "Angor Intelligence")
    log(f"{product} {__version__} – collecte du {now:%d/%m/%Y %H:%M} UTC")

    new_events = []
    ctx = Context(countries, store["state"], log, now)
    ctx.advisories = {v["name"]: v["data"] for v in store["advisories"].values()}
    for src in sources:
        if not src.get("enabled") or (args.only and src["id"] not in args.only):
            continue
        module = REGISTRY.get(src["type"])
        # Réglages modifiés depuis la dernière collecte → on reconstruit l'historique de cette source
        sigs = store["state"].setdefault("config_signatures", {})
        sig = config_signature(src)
        prefix = id_prefix(src)
        if sigs.get(src["id"]) != sig and any(k.startswith(prefix) for k in store["events"]):
            log(f"  {src['id']} : réglages modifiés, historique reconstruit")
            ctx.purge.append(prefix)
            if src["type"] == "gdelt_events":
                store["state"].pop("gdelt_last", None)
        sigs[src["id"]] = sig
        status = store["status"].get(src["id"], {})
        # une source qui échoue 3 fois de suite est mise en pause 24 h (ménage le PC et les serveurs)
        if status.get("fail_streak", 0) >= 3 and status.get("last_attempt") and \
                (now - parse_iso(status["last_attempt"])).total_seconds() < 86400:
            status["paused"] = True
            store["status"][src["id"]] = status
            log(f"… {src['id']:<22} en pause (3 échecs consécutifs) – nouvel essai d'ici 24 h")
            continue
        status["paused"] = False
        status.update({"id": src["id"], "name": src.get("name", src["id"]), "type": src["type"],
                       "kind": getattr(module, "KIND", "?"), "license": src.get("license", ""),
                       "last_attempt": now_iso()})
        t0 = time.time()
        try:
            if module is None:
                raise ValueError(f"type de connecteur inconnu : {src['type']}")
            before = len(ctx.news) + len(ctx.press) + len(ctx.econ)
            result = module.fetch(src, ctx)
            if module.KIND == "advisories":
                store["advisories"][src["id"]] = {"name": src.get("name", src["id"]), "data": result,
                                                  "updated": now_iso()}
                ctx.advisories[src.get("name", src["id"])] = result
                count = len(result)
            else:
                new_events.extend(result)
                count = len(result) + len(ctx.news) + len(ctx.press) + len(ctx.econ) - before
            status.update({"ok": True, "count": count, "error": None, "last_success": now_iso(), "fail_streak": 0})
            log(f"✔ {src['id']:<22} {count:>5} élément(s)  ({time.time() - t0:.1f} s)")
        except AuthMissing as exc:
            status.update({"ok": False, "count": 0, "error": f"Identifiants manquants : {exc}"})
            log(f"– {src['id']:<22} ignorée : identifiants manquants ({exc})")
        except Exception as exc:  # une source en panne ne bloque jamais les autres
            status.update({"ok": False, "count": 0, "error": f"{type(exc).__name__}: {exc}"[:300],
                           "fail_streak": status.get("fail_streak", 0) + 1})
            log(f"✘ {src['id']:<22} ERREUR : {type(exc).__name__}: {exc}")
        status["duration_s"] = round(time.time() - t0, 1)
        store["status"][src["id"]] = status

    enabled_ids = {s["id"] for s in sources if s.get("enabled")}
    store["status"] = {k: v for k, v in store["status"].items() if k in enabled_ids}
    store["advisories"] = {k: v for k, v in store["advisories"].items() if k in enabled_ids}

    # Presse (flux RSS + Google News) : classement, géolocalisation, veille économique
    ai_results = ai.analyze(ctx.press, store, settings, log, now)
    press_events, press_news, econ = press.build(ctx.press, ctx.econ, countries, log, now, ai_results)
    new_events.extend(press_events)

    for prefix in ctx.purge:
        store["events"] = {k: v for k, v in store["events"].items() if not k.startswith(prefix)}
    publish.merge(store, new_events, ctx.news + press_news, now, settings.get("retention_days", 95),
                  new_econ=econ)
    enrich.add_headlines(list(store["events"].values()), store["headlines"], log,
                         max_fetch=settings.get("headline_fetch_per_run", 150))
    all_events = dedupe(list(store["events"].values()))
    all_events.sort(key=lambda e: e["date"], reverse=True)
    # 30 derniers jours dans data.js (chargement rapide) ; au-delà, archives mensuelles chargées à la demande
    map_limit = to_iso(now - timedelta(days=settings.get("map_days", 30)))
    events = [e for e in all_events if e["date"] >= map_limit]
    archives = publish.write_archives([e for e in all_events if e["date"] < map_limit])

    if not args.no_profiles and (args.profiles or profiles.is_stale(now)):
        try:
            profiles.build(countries, log, now)
        except Exception as exc:
            log(f"✘ profils pays : {type(exc).__name__}: {exc}")

    if not args.no_profiles:
        try:
            practical.update(countries, store, log, per_run=settings.get("practical_per_run", 25))
        except Exception as exc:
            log(f"✘ infos pratiques : {type(exc).__name__}: {exc}")

    advisories = {v["name"]: v["data"] for v in store["advisories"].values()}
    country_risk = risk.compute(all_events, advisories, now, config.load_json("risk.json", {}))
    alerts = site_alerts(events, sites, settings.get("site_alert_min_severity", 2))

    # En ligne (GitHub Pages), la localisation de vos sites ne doit jamais être publiée.
    public = os.environ.get("VS_PUBLIC") == "1" or not settings.get("publish_sites", True)
    payload = {
        "generated": now_iso(), "version": __version__, "taxonomy": taxonomy(),
        "events": events, "countries": country_risk,
        "news": sorted(store["news"].values(), key=lambda n: n["date"], reverse=True),
        "status": list(store["status"].values()),
        "sites": [] if public else sites, "site_alerts": [] if public else alerts,
        "settings": {"product_name": product, "default_lang": settings.get("default_lang", "fr"),
                     "buddy_url": settings.get("buddy_url", "")},
        "country_stats": analytics.country_stats(all_events, now), "archives": archives,
        "analytics": analytics.global_series(all_events, now),
    }
    notify.send(events, sites, store, settings, log, now)
    publish.write_outputs(payload)
    econ_by_country = {}
    for e in sorted(store["econ"].values(), key=lambda x: x["date"], reverse=True):
        econ_by_country.setdefault(e["country"], []).append(e)
    publish.write_js("econ.js", "VS_ECON", {"generated": now_iso(), "countries": econ_by_country})
    publish.write_cities()
    publish.save_store(store)

    log(f"→ {len(events)} événements publiés, {len(country_risk)} pays notés, "
        f"{len(payload['news'])} articles dans le fil, {len(alerts)} alerte(s) près de vos sites.")
    for a in alerts[:5]:
        log(f"   ⚠ {a['site']} : {a['title']} à {a['distance_km']} km (gravité {a['severity']})")
    log("Ouvrez docs/index.html dans votre navigateur.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
