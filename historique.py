"""Angor Intelligence – base historique (5 ans par défaut) pour l'onglet Analyses et la carte.

Sources ouvertes, toutes réutilisables avec citation :
  ucdp   UCDP GED + « Candidate events » (Université d'Uppsala, CC BY 4.0) – conflits, violences
         contre les civils ; événements vérifiés, avec bilan humain
  gdelt  GDELT 1.0, fichiers quotidiens (presse mondiale) – manifestations, attaques, combats,
         filtrés sévèrement (détections automatiques, pour les volumes et tendances)
  usgs   séismes M4.5+ (USGS)       gdacs  alertes catastrophes (ONU/UE)
  eonet  phénomènes naturels (NASA) who    épidémies (OMS – Disease Outbreak News)

Usage :
  python historique.py                  → tout (long : prévu pour le robot GitHub « Historique »)
  python historique.py --only usgs who  → certaines parties seulement
  python historique.py --years 3
  python historique.py --build          → reconstruit docs/data/history à partir des parties déjà téléchargées
  python historique.py --only ucdp      → télécharge UCDP seulement, SANS reconstruire (à lancer sur le PC :
                                          ucdp.uu.se refuse les serveurs de GitHub), puis publier.bat
Sorties :
  history_parts/<partie>.json.gz         parties brutes (versionnées, réutilisées si une source est injoignable)
  docs/data/history/index.js             sommaire (période, volumes)
  docs/data/history/stats-AAAA.js        toutes les lignes, format compact (onglet Analyses)
  docs/data/history/map/AAAA-MM.js       incidents marquants, format complet (carte, périodes longues)
"""
import argparse
import csv
import gzip
import io
import json
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from multiprocessing import Pool

import requests

from veille import config, http
from veille.connectors import eonet as eonet_mod
from veille.connectors import gdacs as gdacs_mod
from veille.connectors.gdelt_events import CAMEO
from veille.connectors.usgs import gravite
from veille.geo import Countries
from veille.model import CATEGORIES, make_event, parse_iso, to_iso

PARTS_DIR = config.ROOT / "history_parts"   # versionné : une partie téléchargée ailleurs (PC) est réutilisée par le robot
OUT_DIR = config.ROOT / "docs" / "data" / "history"
PARTS = ["usgs", "gdacs", "eonet", "who", "ucdp", "gdelt"]
SECURITY_CATS = {"armed_conflict", "attack", "terrorism", "crime", "unrest", "political"}
MAP_PER_MONTH = 600          # incidents marquants par mois sur la carte (les plus graves d'abord)
UA = {"User-Agent": "AngorIntelligence/1.0 (veille sureté, sources ouvertes)"}


def log(msg):
    print(msg, flush=True)


def rec(**k):
    """Enregistrement intermédiaire. map=True : affiché aussi sur la carte (incident marquant)."""
    return k


# ------------------------------------------------------------------ USGS
def part_usgs(start, end, countries):
    out = []
    y0 = start
    while y0 < end:
        y1 = min(end, y0 + timedelta(days=366))
        url = ("https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&orderby=time&limit=20000"
               f"&minmagnitude=4.5&starttime={y0.isoformat()}&endtime={y1.isoformat()}")
        data = http.get_json(url, timeout=120)
        for f in data.get("features", []):
            p = f["properties"]
            mag = p.get("mag")
            if mag is None:
                continue
            lon, lat = f["geometry"]["coordinates"][:2]
            dt = datetime.fromtimestamp(p["time"] / 1000, tz=timezone.utc)
            sev = gravite(mag, p.get("alert"), p.get("tsunami"))
            out.append(rec(id=f"usgs-{f['id']}", t=to_iso(dt), iso=countries.locate(lat, lon), cat="earthquake",
                           sev=sev, src="USGS", auto=False, conf="high", place=p.get("place") or "",
                           lat=lat, lon=lon, title=p.get("title") or f"M {mag} earthquake", url=p.get("url"),
                           summary=f"Magnitude {mag}" + (f". PAGER alert: {p['alert']}" if p.get("alert") else ""),
                           map=sev >= 3))
        log(f"  USGS {y0} → {y1} : {len(out)} séismes au total")
        y0 = y1
    return out


# ------------------------------------------------------------------ GDACS
def part_gdacs(start, end, countries):
    out, seen = [], set()
    base = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
    q0 = start
    while q0 < end:
        q1 = min(end, q0 + timedelta(days=92))
        for page in range(1, 40):
            params = {"eventlist": "EQ;TC;FL;VO;DR;WF", "fromDate": q0.isoformat(), "toDate": q1.isoformat(),
                      "alertlevel": "Green;Orange;Red", "pagesize": 100, "pagenumber": page}
            try:
                data = http.get_json(base, params=params, timeout=60)
            except Exception as exc:
                if page == 1:
                    log(f"  GDACS {q0} : {exc}")
                break
            feats = data.get("features") or []
            if not feats:
                break
            for f in feats:
                p = f.get("properties", {})
                key = f"gdacs-{p.get('eventtype')}-{p.get('eventid')}"
                geom = f.get("geometry") or {}
                if key in seen or geom.get("type") != "Point":
                    continue
                seen.add(key)
                lon, lat = geom["coordinates"][:2]
                sev = gdacs_mod.GRAVITES.get(str(p.get("alertlevel", "")).lower(), 1)
                cat = gdacs_mod.CATEGORIES.get(p.get("eventtype"), "other")
                iso3 = p.get("iso3") or ""
                item = countries.by_iso3.get(iso3) if iso3 else None
                d = parse_iso(p.get("todate")) or parse_iso(p.get("fromdate"))
                if not d:
                    continue
                out.append(rec(id=key, t=to_iso(d), iso=item["iso2"] if item else countries.locate(lat, lon), cat=cat,
                               sev=sev, src="GDACS", auto=False, conf="high", place=p.get("country") or "",
                               lat=lat, lon=lon, title=p.get("name") or p.get("eventname") or "GDACS alert",
                               url=(p.get("url") or {}).get("report") or "https://www.gdacs.org",
                               summary=f"GDACS {p.get('alertlevel', '')} alert.", map=sev >= 3))
            if len(feats) < 100:
                break
        log(f"  GDACS {q0} → {q1} : {len(out)} alertes au total")
        q0 = q1
    return out


# ------------------------------------------------------------------ NASA EONET
def part_eonet(start, end, countries):
    out = []
    y0 = start
    while y0 < end:
        y1 = min(end, y0 + timedelta(days=366))
        data = http.get_json(eonet_mod.URL, params={"status": "all", "start": y0.isoformat(), "end": y1.isoformat()},
                             timeout=120)
        for e in data.get("events", []):
            cats = [c["id"] for c in e.get("categories", [])]
            if not cats or cats[0] in ("seaLakeIce", "waterColor") or not e.get("geometry"):
                continue
            cat = eonet_mod.CATEGORIES.get(cats[0], "other")
            title = e.get("title", "")
            if cat == "storm" and any(w in title.lower() for w in eonet_mod.CYCLONE_WORDS):
                cat = "cyclone"
            last = e["geometry"][-1]
            lat, lon = eonet_mod._point(last)
            sev = eonet_mod._severity(cat, last, title)
            srcs = e.get("sources") or []
            out.append(rec(id=f"eonet-{e['id']}", t=to_iso(parse_iso(last["date"])), iso=countries.locate(lat, lon),
                           cat=cat, sev=sev, src="NASA EONET", auto=False, conf="high", place="", lat=lat, lon=lon,
                           title=title, url=srcs[0]["url"] if srcs else e.get("link"), summary="", map=sev >= 2))
        log(f"  EONET {y0} → {y1} : {len(out)} phénomènes au total")
        y0 = y1
    return out


# ------------------------------------------------------------------ OMS
def part_who(start, end, countries):
    from veille.connectors.who_don import HIGH, ITEM_URL, URL
    out, skip = [], 0
    while skip < 3000:
        data = http.get_json(URL, params={"sf_culture": "en", "$orderby": "PublicationDateAndTime desc",
                                          "$top": 100, "$skip": skip}, timeout=60)
        items = data.get("value", [])
        if not items:
            break
        oldest = None
        for it in items:
            title = (it.get("OverrideTitle") or it.get("Title") or "").strip()
            d = parse_iso(it.get("PublicationDateAndTime") or it.get("PublicationDate"))
            if not title or not d:
                continue
            oldest = d
            if d.date() < start:
                continue
            name = title.split(" - ")[-1] if " - " in title else ""
            item = countries.by_country_name(name) if name else None
            if not item:
                continue
            sev = 3 if any(w in title.lower() for w in HIGH) else 2
            out.append(rec(id=f"who-{it.get('DonId') or it.get('Id')}", t=to_iso(d), iso=item["iso2"], cat="health",
                           sev=sev, src="WHO", auto=False, conf="high", place=item["name_en"],
                           lat=item["label"][1], lon=item["label"][0], title=title,
                           url=ITEM_URL + (it.get("UrlName") or ""), summary="WHO Disease Outbreak News.", map=True))
        skip += 100
        if oldest and oldest.date() < start:
            break
    log(f"  OMS : {len(out)} bulletins")
    return out


# ------------------------------------------------------------------ UCDP
UCDP_PAGE = "https://ucdp.uu.se/downloads/"
UCDP_GED_FALLBACK = "https://ucdp.uu.se/downloads/ged/ged261-csv.zip"
UCDP_ALIASES = {"russia (soviet union)": "RU", "yemen (north yemen)": "YE", "dr congo (zaire)": "CD",
                "myanmar (burma)": "MM", "cambodia (kampuchea)": "KH", "zimbabwe (rhodesia)": "ZW",
                "madagascar (malagasy)": "MG", "bosnia-herzegovina": "BA", "serbia (yugoslavia)": "RS",
                "ivory coast": "CI", "kingdom of eswatini (swaziland)": "SZ", "burkina faso (upper volta)": "BF",
                "vietnam (north vietnam)": "VN", "north macedonia": "MK", "macedonia, fyr": "MK"}


def _ucdp_links():
    try:
        text = http.get(UCDP_PAGE, timeout=30).text
    except Exception:
        return UCDP_GED_FALLBACK, []
    ged = re.findall(r'href="([^"]*downloads/ged/ged\d+-csv\.zip)"', text)
    cand = re.findall(r'href="([^"]*candidateged/GEDEvent_v[\d_]+\.csv)"', text)
    fix = lambda u: u if u.startswith("http") else "https://ucdp.uu.se" + ("" if u.startswith("/") else "/") + u
    ged = sorted({fix(u) for u in ged}, key=lambda u: int(re.search(r"ged(\d+)", u).group(1)))
    return (ged[-1] if ged else UCDP_GED_FALLBACK), sorted({fix(u) for u in cand})


def _ucdp_rows(url):
    raw = requests.get(url, headers=UA, timeout=(20, 300)).content
    if url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
            raw = z.read(name)
    return csv.DictReader(io.StringIO(raw.decode("utf-8", errors="replace")))


def part_ucdp(start, end, countries):
    ged_url, cands = _ucdp_links()
    log(f"  UCDP : {ged_url} + {len(cands)} fichier(s) « candidate »")
    events, s0 = {}, start.isoformat()
    for url, kind in [(ged_url, "UCDP GED")] + [(u, "UCDP Candidate") for u in cands]:
        try:
            rows = _ucdp_rows(url)
        except Exception as exc:
            log(f"  UCDP {url} indisponible : {exc}")
            continue
        n = 0
        for r in rows:
            d = (r.get("date_start") or "")[:10]
            if not d or d < s0:
                continue
            try:
                lat, lon = float(r["latitude"]), float(r["longitude"])
                best = int(float(r.get("best") or 0))
            except (TypeError, ValueError):
                continue
            name = (r.get("country") or "").strip()
            iso = UCDP_ALIASES.get(name.lower())
            if not iso:
                item = countries.by_country_name(re.sub(r"\s*\(.*?\)", "", name))
                iso = item["iso2"] if item else countries.locate(lat, lon)
            tov = str(r.get("type_of_violence") or "")
            cat = "attack" if tov == "3" else "armed_conflict"
            sev = 4 if best >= 25 else 3 if best >= 5 else 2 if best >= 1 else 1
            place = (r.get("where_description") or r.get("adm_1") or "").strip()[:80]
            dyad = (r.get("dyad_name") or r.get("conflict_name") or "Organised violence").strip()
            cid = r.get("conflict_new_id") or ""
            events[f"ucdp-{r.get('id')}"] = rec(
                id=f"ucdp-{r.get('id')}", t=d + "T12:00:00+00:00", iso=iso, cat=cat, sev=sev, src=kind, auto=False,
                conf="high" if kind == "UCDP GED" else "medium", place=place, lat=lat, lon=lon,
                title=f"{dyad}" + (f" – {place}" if place else ""),
                url=f"https://ucdp.uu.se/conflict/{cid}" if cid else "https://ucdp.uu.se/",
                summary=f"{best} death(s), UCDP best estimate" + (f" (range {r.get('low')}–{r.get('high')})" if r.get("high") else "") + ".",
                deaths=best, map=sev >= 3)
            n += 1
        log(f"  UCDP {kind} : {n} événements depuis {s0}")
    return list(events.values())


# ------------------------------------------------------------------ GDELT (fichiers quotidiens)
GDELT_DAILY = "http://data.gdeltproject.org/events/{d}.export.CSV.zip"
_G = {}


def _gdelt_init(fips, iso3, tense):
    _G.update(fips=fips, iso3=iso3, tense=tense)


def _gdelt_day(day):
    """Télécharge et filtre un fichier quotidien. Renvoie [(AAAAMMJJ, iso2, cat, sev, lieu, conf)]."""
    url = GDELT_DAILY.format(d=day)
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=120)
            if r.status_code == 404:
                return day, None
            r.raise_for_status()
            break
        except Exception:
            time.sleep(3 * (attempt + 1))
    else:
        return day, None
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            text = z.read(z.namelist()[0]).decode("utf-8", errors="replace")
    except Exception:
        return day, None
    d0 = datetime.strptime(day, "%Y%m%d")
    ok_dates = {(d0 - timedelta(days=k)).strftime("%Y%m%d") for k in range(3)}
    agg = {}
    for line in text.split("\n"):
        row = line.split("\t")
        n = len(row)
        if n == 58:
            o = 0
        elif n == 61:
            o = 2
        else:
            continue
        root = row[28]
        if root not in ("14", "18", "19", "20") or row[25] != "1" or row[1] not in ok_dates:
            continue
        gtype = row[49 + o]
        if gtype not in ("2", "3", "4", "5") or not row[53 + o + (1 if o else 0)]:
            continue
        code = row[26][:3]
        if code not in CAMEO:
            code = root + "0"
            if code not in CAMEO:
                continue
        fips = row[51 + o]
        iso = _G["fips"].get(fips)
        if not iso:
            continue
        try:
            articles = int(row[33] or 0)
            nsrc = int(row[32] or 0)
        except ValueError:
            continue
        full = row[50 + o]
        feat = row[55 + o + (1 if o else 0)] or full
        key = (feat, code, row[1])
        a = agg.get(key)
        if a is None:
            a = agg[key] = {"iso": iso, "root": root, "code": code, "articles": 0, "nsrc": 0, "domains": set(),
                            "actors": set(), "acc": set(), "place": full.split(",")[0].strip()[:40], "day": row[1]}
        a["articles"] += articles
        a["nsrc"] = max(a["nsrc"], nsrc)
        url_ = row[-1].strip()
        if url_:
            host = re.sub(r"^https?://(www\.)?", "", url_).split("/")[0].lower()
            a["domains"].add(host)
        for c in (row[7], row[17]):
            if c:
                a["acc"].add(c)
        for nm in (row[6], row[16]):
            if nm:
                a["actors"].add(nm.upper())
    out = []
    for a in agg.values():
        violent = a["root"] in ("18", "19", "20")
        iso3 = _G["iso3"].get(a["iso"])
        if violent and (a["place"].upper() in a["actors"] or (iso3 and a["acc"] and iso3 not in a["acc"])):
            continue  # effet « dateline » : article écrit depuis une capitale sur un conflit étranger
        dom = max(len(a["domains"]), a["nsrc"])
        tense = a["iso"] in _G["tense"]
        if a["root"] == "14":
            need = (15, 3) if (tense or a["code"] == "145") else (30, 4)
        elif tense:
            need = (8, 3)
        else:
            need = (15, 4) if a["root"] == "18" else (25, 4)
        if a["articles"] < need[0] or dom < need[1]:
            continue
        cat, sev, _ = CAMEO[a["code"]]
        if not tense and a["root"] in ("19", "20"):
            cat, sev = "attack", min(sev, 3)
        if a["articles"] >= 50 and dom >= 5:
            sev = min(4, sev + 1)
        conf = "high" if dom >= 5 and a["articles"] >= 20 else "medium" if dom >= 3 else "low"
        out.append((a["articles"], a["day"], a["iso"], cat, sev, a["place"], conf))
    # au plus 15 détections par pays et par jour (les plus reprises) : évite qu'un pays très médiatisé écrase tout
    out.sort(key=lambda x: -x[0])
    per, kept = {}, []
    for x in out:
        k = (x[2], x[1])
        if per.get(k, 0) < 15:
            per[k] = per.get(k, 0) + 1
            kept.append(x[1:])
    return day, kept


def part_gdelt(start, end, countries, workers=8):
    fips = {k: v["iso2"] for k, v in countries.by_fips.items()}
    iso3 = {v["iso2"]: v["iso3"] for v in countries.items}
    store = config.ROOT / "data" / "store.json"
    tense = set()
    if store.exists():
        try:
            advs = json.loads(store.read_text(encoding="utf-8")).get("advisories", {})
            for v in advs.values():
                for iso, a in (v.get("data") or {}).items():
                    if a.get("level", 0) >= 3:
                        tense.add(iso)
        except Exception:
            pass
    days = []
    d = start
    while d < end:
        days.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    out, missing, t0 = [], 0, time.time()
    with Pool(workers, initializer=_gdelt_init, initargs=(fips, iso3, tense)) as pool:
        for i, (day, rows) in enumerate(pool.imap_unordered(_gdelt_day, days, chunksize=2), 1):
            if rows is None:
                missing += 1
                continue
            for (dd, iso, cat, sev, place, conf) in rows:
                out.append(rec(t=f"{dd[:4]}-{dd[4:6]}-{dd[6:]}T12:00:00+00:00", iso=iso, cat=cat, sev=sev, src="GDELT",
                               auto=True, conf=conf, place=place, map=False))
            if i % 100 == 0:
                log(f"  GDELT : {i}/{len(days)} jours lus, {len(out)} détections ({time.time() - t0:.0f} s)")
    log(f"  GDELT : {len(out)} détections retenues, {missing} jour(s) indisponible(s)")
    return out


# ------------------------------------------------------------------ assemblage
def save_part(name, records):
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    with gzip.open(PARTS_DIR / f"{name}.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, separators=(",", ":"))


def load_part(name):
    p = PARTS_DIR / f"{name}.json.gz"
    if not p.exists():
        return []
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def write_js(path, prefix, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(prefix)
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")


def build(start, until):
    records = []
    for name in PARTS:
        part = load_part(name)
        records.extend(r for r in part if r.get("t") and start.isoformat() <= r["t"][:10] <= until.isoformat())
        log(f"  {name:<6} {len(part):>8} enregistrement(s)")
    cats = list(CATEGORIES)
    srcs = sorted({r["src"] for r in records})
    epoch = date(1970, 1, 1)
    by_year, by_month = {}, {}
    for r in records:
        by_year.setdefault(r["t"][:4], []).append(r)
        if r.get("map") and r.get("lat") is not None and r.get("iso") is not False:
            by_month.setdefault(r["t"][:7], []).append(r)
    if OUT_DIR.exists():
        for f in list(OUT_DIR.glob("stats-*.js")) + list((OUT_DIR / "map").glob("*.js")):
            f.unlink()
    years = {}
    for y, rs in sorted(by_year.items()):
        places, pidx, rows = [], {}, []
        for r in sorted(rs, key=lambda x: x["t"]):
            day = (date.fromisoformat(r["t"][:10]) - epoch).days
            pl = (r.get("place") or "")[:40]
            if pl not in pidx:
                pidx[pl] = len(places)
                places.append(pl)
            flags = (1 if r.get("auto") else 0) | (2 if r.get("conf") == "high" else 0) | (4 if r.get("conf") == "low" else 0)
            rows.append([day, r.get("iso") or "", cats.index(r["cat"]) if r["cat"] in cats else cats.index("other"),
                         int(r["sev"]), srcs.index(r["src"]), flags, pidx[pl]])
        write_js(OUT_DIR / f"stats-{y}.js", f"(window.VS_HIST = window.VS_HIST || {{}})['{y}'] = ",
                 {"rows": rows, "places": places})
        years[y] = len(rows)
    months = {}
    for m, rs in sorted(by_month.items()):
        rs.sort(key=lambda r: (-int(r["sev"]), -int(r.get("deaths") or 0)))
        evs = []
        for r in rs[:MAP_PER_MONTH]:
            ev = make_event(id=r["id"], source=r["src"], category=r["cat"], severity=r["sev"], title=r.get("title") or "",
                            date=r["t"], lat=r["lat"], lon=r["lon"], url=r.get("url") or "", summary=r.get("summary", ""),
                            precision="city" if r["src"].startswith("UCDP") else "exact", place=r.get("place", ""),
                            country=r.get("iso") or None, confidence=r.get("conf", "high"), tags=["history"])
            ev.pop("start", None)
            evs.append(ev)
        write_js(OUT_DIR / "map" / f"{m}.js", f"(window.VS_HMAP = window.VS_HMAP || {{}})['{m}'] = ", evs)
        months[m] = len(evs)
    counts, base = {}, {}
    last12 = (until - timedelta(days=365)).isoformat()
    for r in records:
        counts[r["src"]] = counts.get(r["src"], 0) + 1
        if r.get("iso") and r["t"][:10] >= last12 and r["cat"] in SECURITY_CATS:
            base[r["iso"]] = base.get(r["iso"], 0) + 1
    baseline = {iso: round(n / 12, 1) for iso, n in base.items()}
    write_js(OUT_DIR / "index.js", "window.VS_HIST_INDEX = ",
             {"generated": to_iso(datetime.now(timezone.utc)), "from": start.isoformat(), "until": until.isoformat(),
              "years": years, "map_months": months, "sources": counts, "cats": cats, "srcs": srcs,
              "baseline_month": baseline,
              "credits": "UCDP GED (Uppsala University, CC BY 4.0), GDELT Project, USGS, GDACS, NASA EONET, WHO"})
    log(f"→ {len(records)} enregistrements, {sum(months.values())} incidents marquants sur la carte, "
        f"{len(years)} année(s) → docs/data/history/")


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="Base historique Angor Intelligence")
    ap.add_argument("--years", type=float, default=5)
    ap.add_argument("--only", nargs="*", choices=PARTS)
    ap.add_argument("--build", action="store_true", help="assembler seulement (sans téléchargement)")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    config.load_dotenv()
    today = datetime.now(timezone.utc).date()
    until = today - timedelta(days=1)
    start = today - timedelta(days=int(365.25 * args.years))
    log(f"Base historique du {start} au {until}")
    countries = Countries()
    if args.only or not args.build:
        for name in args.only or PARTS:
            t0 = time.time()
            log(f"• {name}")
            try:
                fn = globals()[f"part_{name}"]
                recs = fn(start, until + timedelta(days=1), countries, args.workers) if name == "gdelt" \
                    else fn(start, until + timedelta(days=1), countries)
                if recs:
                    save_part(name, recs)
                    log(f"  ✔ {name} : {len(recs)} enregistrement(s) en {time.time() - t0:.0f} s")
                else:
                    old = len(load_part(name))
                    log(f"  ✘ {name} : aucun enregistrement téléchargé – partie précédente conservée ({old})")
            except Exception as exc:  # une source en panne ne bloque jamais les autres
                log(f"  ✘ {name} : {type(exc).__name__}: {exc}")
    if not args.only or args.build:
        build(start, until)
    else:
        log("Parties téléchargées. Reconstruction non lancée (--only sans --build) : envoyez avec publier.bat,"
            " puis relancez le robot « Historique ».")
    return 0


if __name__ == "__main__":
    sys.exit(main())
