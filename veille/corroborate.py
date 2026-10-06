"""Recoupement des événements (v0.25) : sources réellement indépendantes, confirmation par les capteurs officiels,
démentis.

Après le regroupement des doublons (veille/dedupe.py) et avant la cotation de l'Amirauté (veille/quality.py) :

1. **Sources indépendantes.** Dix médias qui reprennent la même dépêche ne valent pas dix témoins. On compte :
   - un seul témoin par domaine ;
   - un seul par groupe de presse (ex. EBRA : Le Progrès, DNA, L'Est républicain… ; Schibsted, Gannett…) ;
   - un seul pour des titres identiques sur des médias différents (reprise d'agence).
   Résultat dans « corroboration » : {independent, outlets, copies, kinds}. La crédibilité (chiffre de la cote)
   se fonde désormais sur les sources indépendantes et sur la diversité des types de sources (capteur officiel,
   organisme officiel, presse de référence, autre presse, détection automatique, réseaux sociaux).

2. **Confirmation par les capteurs.** Un séisme, un cyclone, un tsunami ou une éruption rapportés par la presse ou
   GDELT sont rattachés à la fiche officielle correspondante (USGS, EMSC, GDACS, NOAA, GVP…) quand elle existe
   (même famille, lieu proche, l'article étant publié après l'événement) : une seule fiche sur la carte, avec les
   articles en sources. Un séisme chiffré (magnitude dans le titre) qu'aucun réseau n'a mesuré reste sur la carte
   mais est marqué « non confirmé par les capteurs officiels » (crédibilité 4 – douteuse) : séisme ancien repris
   par erreur, mal localisé ou imaginaire.
   Deux réseaux sismiques en désaccord sur la magnitude (écart ≥ 0,5) : écart signalé.

3. **Démentis.** Un titre de contexte qui dément (« fake », « hoax », « démenti », « no factual basis »,
   « desmiente »…) et raconte la même histoire (mêmes mots, même pays, ± 3 jours) marque l'événement
   « démenti signalé » (crédibilité 4) avec le lien vers le démenti. L'analyste tranche (verified.json).
"""
import re
import unicodedata
from urllib.parse import urlparse

from . import press
from .dedupe import story_tokens
from .geo import haversine_km
from .model import parse_iso

SENSORS = {"USGS", "EMSC", "GDACS", "NASA EONET", "NWS", "Meteoalarm", "NOAA NHC", "PTWC", "NTWC", "Smithsonian GVP",
           "Copernicus EMS"}
OFFICIAL = {"WHO", "CDC", "ECDC", "UCDP", "CISA", "MEAE", "FCDO", "Auswärtiges Amt"}
# famille → (catégories, distance max km, heures avant l'article, heures après)
CONFIRMABLE = {
    "earthquake": ({"earthquake"}, 300, 72, 6),
    "cyclone": ({"cyclone", "storm"}, 900, 120, 48),
    "volcano": ({"volcano"}, 150, 24 * 14, 48),
}
CAT_FAMILY = {"earthquake": "earthquake", "cyclone": "cyclone", "volcano": "volcano"}
MAG_RE = re.compile(r"\b(?:m|mag(?:nitude)?)\s*([1-9](?:\.\d)?)\b", re.I)

# Groupes de presse : une reprise interne au groupe n'est pas une source indépendante
MEDIA_GROUPS = {
    "ebra": ["leprogres.fr", "dna.fr", "estrepublicain.fr", "ledauphine.com", "lalsace.fr", "vosgesmatin.fr",
             "bienpublic.com", "lejsl.com", "republicain-lorrain.fr", "ledauphine-libere.fr"],
    "rossel-voix": ["lavoixdunord.fr", "courrier-picard.fr", "lesoir.be", "nordeclair.fr"],
    "sudouest": ["sudouest.fr", "charentelibre.fr", "larepubliquedespyrenees.fr"],
    "ouestfrance": ["ouest-france.fr", "actu.fr", "courrier-picard.fr", "20minutes.fr"],
    "lagardere-cmi": ["lejdd.fr", "europe1.fr", "parismatch.com"],
    "altice": ["bfmtv.com", "rmc.bfmtv.com", "rmcsport.bfmtv.com"],
    "francetv-radiofrance": ["francetvinfo.fr", "francebleu.fr", "franceinter.fr", "franceinfo.fr", "la1ere.franceinfo.fr"],
    "fmm": ["rfi.fr", "france24.com", "mc-doualiya.com"],
    "lemonde": ["lemonde.fr", "courrierinternational.com", "telerama.fr", "huffingtonpost.fr"],
    "figaro": ["lefigaro.fr", "tvmag.lefigaro.fr"],
    "nicematin": ["nicematin.com", "varmatin.com", "monacomatin.mc", "corsematin.com"],
    "lavenir": ["lavenir.net", "lameuse.be"],
    "prisa": ["elpais.com", "cadenaser.com", "as.com"],
    "vocento": ["abc.es", "elcorreo.com", "diariovasco.com", "laverdad.es", "lasprovincias.es", "elnortedecastilla.es"],
    "unidad-editorial": ["elmundo.es", "marca.com", "expansion.com"],
    "gedi": ["repubblica.it", "lastampa.it", "ilsecoloxix.it"],
    "rcs": ["corriere.it", "gazzetta.it"],
    "springer": ["bild.de", "welt.de", "politico.eu"],
    "funke": ["waz.de", "morgenpost.de", "abendblatt.de", "thueringer-allgemeine.de"],
    "ippen": ["merkur.de", "tz.de", "fr.de", "hna.de", "kreiszeitung.de"],
    "ard": ["tagesschau.de", "br.de", "ndr.de", "wdr.de", "mdr.de", "swr.de", "rbb24.de", "hr.de", "sr.de"],
    "mediahuis": ["standaard.be", "nieuwsblad.be", "nrc.nl", "telegraaf.nl", "independent.ie", "wort.lu"],
    "dpg": ["volkskrant.nl", "ad.nl", "parool.nl", "hln.be", "demorgen.be"],
    "schibsted": ["vg.no", "aftenposten.no", "aftonbladet.se", "svd.se"],
    "bonnier": ["dn.se", "expressen.se", "hs.fi"],
    "gannett": ["usatoday.com", "detroitfreepress.com", "azcentral.com", "tennessean.com", "indystar.com"],
    "nbcu": ["nbcnews.com", "msnbc.com", "cnbc.com", "telemundo.com"],
    "paramount": ["cbsnews.com", "cbs.com"],
    "disney": ["abcnews.go.com", "abc7.com", "abc7ny.com"],
    "newscorp": ["wsj.com", "nypost.com", "foxnews.com", "thetimes.co.uk", "thesun.co.uk", "theaustralian.com.au"],
    "nine": ["smh.com.au", "theage.com.au", "9news.com.au"],
    "bbc": ["bbc.com", "bbc.co.uk"],
    "dw": ["dw.com"],
    "globo": ["g1.globo.com", "oglobo.globo.com", "globo.com", "extra.globo.com"],
    "clarin": ["clarin.com", "ole.com.ar"],
    "televisa": ["televisa.com", "nmas.com.mx"],
    "milenio": ["milenio.com", "multimedios.com"],
    "oem": ["oem.com.mx"],
    "times-india": ["timesofindia.indiatimes.com", "indiatimes.com", "economictimes.indiatimes.com"],
    "ht": ["hindustantimes.com", "livehindustan.com", "livemint.com"],
    "jang": ["thenews.com.pk", "geo.tv", "jang.com.pk"],
    "nation-media": ["nation.africa", "taifaleo.nation.co.ke", "theeastafrican.co.ke"],
    "punch-vanguard": ["punchng.com"],
    "naspers-news24": ["news24.com"],
    "aljazeera": ["aljazeera.com", "aljazeera.net"],
    "rferl": ["rferl.org", "azatutyun.am", "svoboda.org", "currenttime.tv", "kavkaz-uzel.eu", "idelreal.org", "severreal.org",
              "ozodi.org", "azathabar.com", "radiotavisupleba.ge"],
}
_GROUP_OF = {d: g for g, ds in MEDIA_GROUPS.items() for d in ds}
DENIAL = ["fake", "hoax", "hoaks", "debunk", "false report", "false claim", "no factual basis", "unfounded", "denies",
          "denied", "rejects claim", "dement", "dementi", "infox", "fausse information", "fausse rumeur", "rumeur",
          "faux", "desmiente", "desmienten", "falso", "bulo", "niega", "nega", "smentit", "dementiert", "falschmeldung",
          "фейк", "опроверг", "спростув"]
_DENIAL_RE = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(w) for w in DENIAL) + r")", re.I)


def _norm(t):
    t = unicodedata.normalize("NFKD", t or "")
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c)).lower()).strip()


def _domain(src):
    d = (src.get("site") or urlparse(src.get("url") or "").netloc or src.get("name") or "").lower()
    return re.sub(r"^(www|m|amp|edition|english|en)\.", "", d)


def _group(dom):
    if dom in _GROUP_OF:
        return _GROUP_OF[dom]
    for d, g in _GROUP_OF.items():           # sous-domaine d'un membre du groupe
        if dom.endswith("." + d):
            return g
    return dom


def kind_of(src_name, ev):
    if src_name in SENSORS:
        return "capteur"
    if src_name in OFFICIAL:
        return "officiel"
    if src_name == "GDELT" or src_name == "Press (via GDELT)":
        return "détection automatique"
    if "social" in (ev.get("tags") or []) or "t.me/" in src_name:
        return "réseaux sociaux"
    return "presse"


def independence(ev):
    """Nombre de sources indépendantes d'une fiche (domaine, groupe de presse, reprise d'un même titre)."""
    sources = ev.get("sources") or []
    keys, titles, kinds = set(), {}, set()
    for s in sources:
        name = s.get("name") or ev.get("source") or ""
        kinds.add(kind_of(name, ev) if name not in ("Press",) else "presse")
        dom = _domain(s)
        grp = _group(dom) if dom else name.lower()
        t = _norm(s.get("title") or "")
        if t and len(t) > 25:                 # même titre mot pour mot ailleurs : reprise d'agence
            if t in titles and titles[t] != grp:
                continue
            titles.setdefault(t, grp)
        keys.add(grp or name.lower())
    if ev.get("source") in SENSORS | OFFICIAL:
        kinds.add("capteur" if ev["source"] in SENSORS else "officiel")
    outlets = len({_domain(s) or (s.get("name") or "").lower() for s in sources})
    n = max(1, len(keys))
    return {"independent": n, "outlets": outlets, "copies": max(0, outlets - n), "kinds": sorted(kinds)}


def _mag(text):
    m = MAG_RE.search(text or "")
    return float(m.group(1)) if m else None


def sensor_check(events):
    """Rattache les récits de presse/GDELT d'un séisme, cyclone ou éruption à la fiche officielle correspondante.
    Renvoie la liste sans les fiches absorbées ; marque les autres « non confirmé » le cas échéant."""
    official = [e for e in events if e.get("source") in SENSORS and CAT_FAMILY.get(e.get("category"))]
    gone = set()
    for e in events:
        fam = CAT_FAMILY.get(e.get("category"))
        if not fam or e.get("source") in SENSORS | OFFICIAL or e.get("lat") is None:
            continue
        cats, km, before, after = CONFIRMABLE[fam]
        t = parse_iso(e.get("start") or e["date"])
        best = None
        for o in official:
            if o.get("category") not in cats or o.get("lat") is None:
                continue
            dh = (t - parse_iso(o.get("start") or o["date"])).total_seconds() / 3600   # article après l'événement
            if not (-after <= dh <= before):
                continue
            d = haversine_km(e["lat"], e["lon"], o["lat"], o["lon"])
            if d <= km and (best is None or d < best[0]):
                best = (d, o)
        if best:
            o = best[1]
            o["sources"] = (o.get("sources") or []) + [s for s in e.get("sources") or [] if s not in (o.get("sources") or [])]
            o["sources"] = o["sources"][:25]
            o["merged"] = list(dict.fromkeys((o.get("merged") or []) + [e["id"]] + list(e.get("merged") or [])))
            o["press_reports"] = o.get("press_reports", 0) + max(1, len(e.get("sources") or []))
            o["severity"] = max(o.get("severity") or 1, min(e.get("severity") or 1, (o.get("severity") or 1) + 1))
            if "multi-source" not in (o.get("tags") or []):
                o["tags"] = sorted(set(o.get("tags") or []) | {"multi-source"})
            gone.add(e["id"])
        elif fam == "earthquake" and press._MAG_RE.search(press.norm(e.get("title") or "")):
            # un séisme chiffré (« magnitude 6,1 ») qu'aucun réseau n'a mesuré : ancien, mal localisé ou faux
            e["unconfirmed"] = "capteurs"
    # deux réseaux sismiques fusionnés (USGS + EMSC) : écart de magnitude
    for o in official:
        if o.get("category") == "earthquake" and o["id"] not in gone and o.get("merged"):
            mags = {_mag(s.get("title") or "") for s in o.get("sources") or []} | {_mag(o.get("title"))}
            mags.discard(None)
            if len(mags) >= 2 and max(mags) - min(mags) >= 0.5:
                o["mag_spread"] = [min(mags), max(mags)]
    return [e for e in events if e["id"] not in gone]


def denials(events, context_items, max_days=3):
    """Marque « disputed » les événements qu'un titre de démenti raconte (mêmes mots, même pays, ± max_days)."""
    cands = []
    for c in context_items:
        title = c.get("title") or ""
        if not _DENIAL_RE.search(_norm(title)):
            continue
        toks = set(story_tokens({"source": "Press", "title": title}))
        if len(toks) >= 3:
            cands.append((c, toks))
    if not cands:
        return 0
    n = 0
    for e in events:
        if e.get("source") in SENSORS | OFFICIAL:
            continue
        et = set(story_tokens(e))
        if len(et) < 3:
            continue
        d = parse_iso(e["date"])
        for c, toks in cands:
            if c.get("country") and e.get("country") and c["country"] != e["country"]:
                continue
            try:
                if abs((parse_iso(c["date"]) - d).total_seconds()) > max_days * 86400:
                    continue
            except (TypeError, ValueError):
                continue
            inter = len(et & toks)
            if inter >= 3 and inter / len(et | toks) >= 0.25:
                e["disputed"] = {"title": c.get("title"), "url": c.get("url"), "source": c.get("source"), "date": c.get("date")}
                n += 1
                break
    return n


def run(events, context_items=(), log=print):
    """Recoupement complet ; renvoie la liste (fiches de presse rattachées aux capteurs retirées)."""
    before = len(events)
    # copies : la mémoire du robot garde les fiches d'origine (rien ne s'accumule d'une collecte à l'autre)
    events = [dict(e, sources=list(e.get("sources") or []), tags=list(e.get("tags") or [])) for e in events]
    events = sensor_check(events)
    for e in events:
        e["corroboration"] = independence(e)
    nd = denials(events, context_items)
    unconf = sum(1 for e in events if e.get("unconfirmed"))
    log(f"  Recoupement : {before - len(events)} récit(s) rattaché(s) à une mesure officielle, {unconf} non confirmé(s) "
        f"par les capteurs, {nd} démenti(s) signalé(s)")
    return events
