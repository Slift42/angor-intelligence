"""Alertes sortantes : Telegram et e-mail pour chaque nouvel incident grave, partout dans le monde.

Réglages (config/settings.json → "alerts") :
  min_severity   gravité minimale envoyée (1 à 4, défaut 3 = Élevée)
  max_age_hours  n'envoie que les incidents survenus depuis moins de X heures (défaut 6) : pas de rafale d'anciens faits
  countries      liste de codes pays à suivre, ex. ["FR", "ML"] ; vide = monde entier
  categories     liste de catégories à suivre, ex. ["terrorism", "unrest"] ; vide = toutes
  include_auto   true/false : inclure les détections automatiques (presse, GDELT) – défaut true
  max_per_message nombre d'incidents détaillés par envoi (défaut 15, les plus graves d'abord)
  telegram / email  true/false
Secrets (.env ou Secrets GitHub) :
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID                           → bot Telegram (créé avec @BotFather)
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_TO → e-mail (ex. Gmail avec mot de passe d'application)
Chaque incident n'est envoyé qu'une fois (mémoire dans data/store.json).
La proximité d'un de vos sites n'est plus un critère : elle est seulement signalée dans le message.

Point quotidien (config/settings.json → "digest") : un message par jour sur le même canal Telegram
(et/ou par e-mail) à partir de `hour_utc` : incidents marquants des dernières 24 h, crises en cours,
pays dont le Pulse baisse le plus, focus sur les pays suivis (`countries`), lien vers la carte.
Alertes Pulse (→ "pulse") : chute rapide de l'indice de stabilité d'un pays ou passage sous un seuil.
"""
import smtplib
from datetime import timedelta
from urllib.parse import quote
from email.message import EmailMessage

from . import http
from .config import secret
from .geo import distance_to
from .model import CATEGORIES, parse_iso

SEV = {1: "Faible", 2: "Modérée", 3: "Élevée", 4: "CRITIQUE"}
TG_LIMIT = 3900  # Telegram refuse les messages de plus de 4096 caractères


def select(events, store, cfg, now):
    """Incidents à envoyer : récents, assez graves, fiables, jamais envoyés, dans les filtres éventuels."""
    sent = store.setdefault("state", {}).setdefault("notified", {})
    limit = now - timedelta(hours=cfg["max_age_hours"])
    countries = {c.upper() for c in cfg.get("countries") or []}
    categories = set(cfg.get("categories") or [])
    out = []
    for ev in events:
        if ev["severity"] < cfg["min_severity"] or ev.get("confidence") == "low" or ev["id"] in sent:
            continue
        if parse_iso(ev["date"]) < limit:
            continue
        if countries and ev.get("country") not in countries:
            continue
        if categories and ev.get("category") not in categories:
            continue
        if not cfg["include_auto"] and "auto" in (ev.get("tags") or []):
            continue
        out.append(ev)
    out.sort(key=lambda e: e["date"], reverse=True)       # plus récents d'abord…
    return sorted(out, key=lambda e: -e["severity"])      # …à gravité égale


def _nearest_site(ev, sites):
    best = None
    for s in sites:
        d = distance_to(s, ev["lat"], ev["lon"])
        if d <= s.get("radius_km", 50) and (best is None or d < best[1]):
            best = (("trajet " if s.get("kind") == "corridor" else "") + s["name"], round(d, 1))
    return best


def _block(ev, sites):
    place = ", ".join(x for x in (ev.get("place"), ev.get("country")) if x)
    head = f"[{SEV.get(ev['severity'], ev['severity'])}] {place}".strip()
    near = _nearest_site(ev, sites)
    if near:
        head += f" – à {near[1]} km de {near[0]}"
    text = ev.get("summary") or ev.get("headline") or ""
    if text == ev.get("title"):
        text = ""
    return "\n".join(x for x in (head, ev.get("title", ""), text[:300], ev.get("url", "")) if x)


def _chunks(header, blocks, limit):
    """Découpe en plusieurs messages si nécessaire (limite Telegram)."""
    msgs, cur = [], header
    for b in blocks:
        if len(cur) + len(b) + 2 > limit:
            msgs.append(cur)
            cur = b
        else:
            cur += "\n\n" + b
    msgs.append(cur)
    return msgs


def send(events, sites, store, settings, log, now):
    cfg = {"min_severity": 3, "max_age_hours": 6, "countries": [], "categories": [], "include_auto": True,
           "max_per_message": 15, "telegram": True, "email": True, **(settings.get("alerts") or {})}
    fresh = select(events, store, cfg, now)
    if not fresh:
        return 0
    shown = fresh[:cfg["max_per_message"]]
    blocks = [_block(ev, sites) for ev in shown]
    header = f"Angor Intelligence – {len(fresh)} nouvel(s) incident(s)"
    if len(fresh) > len(shown):
        header += f" ({len(shown)} plus graves ci-dessous)"
    ok = deliver(header, blocks, cfg, log)
    if ok:
        sent = store["state"]["notified"]
        for ev in fresh:  # tous marqués, même ceux non détaillés : pas de rattrapage en rafale
            sent[ev["id"]] = True
        if len(sent) > 5000:
            for k in list(sent)[:1000]:
                del sent[k]
        log(f"  {len(fresh)} alerte(s) envoyée(s)")
        return len(fresh)
    return 0


def _telegram(texts, log):
    token, chat = secret("TELEGRAM_BOT_TOKEN"), secret("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return False
    try:
        for text in texts:
            http._session.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=20,
                               json={"chat_id": chat, "text": text,
                                     "disable_web_page_preview": True}).raise_for_status()
        return True
    except Exception as exc:
        log(f"  Telegram : envoi impossible : {str(exc).replace(token, '***')}")
        return False


def _email(subject, body, log):
    host, to = secret("SMTP_HOST"), secret("ALERT_EMAIL_TO")
    if not (host and to):
        return False
    try:
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, secret("SMTP_USER") or to, to
        msg.set_content(body + "\n\nOutil d'aide à la décision – informations non exhaustives, à vérifier.")
        with smtplib.SMTP(host, int(secret("SMTP_PORT") or 587), timeout=30) as s:
            s.starttls()
            if secret("SMTP_USER"):
                s.login(secret("SMTP_USER"), secret("SMTP_PASSWORD") or "")
            s.send_message(msg)
        return True
    except Exception as exc:
        log(f"  E-mail : envoi impossible : {exc}")
        return False


def deliver(header, blocks, cfg, log):
    ok = False
    if cfg.get("telegram", True):
        ok = _telegram(_chunks(header, blocks, TG_LIMIT), log) or ok
    if cfg.get("email", True):
        ok = _email(header, "\n\n".join(blocks), log) or ok
    return ok


# ------------------------------------------------------------------ point quotidien
DIGEST = {"enabled": True, "hour_utc": 5, "countries": [], "max_items": 8, "telegram": True, "email": False,
          "min_severity": 3, "site_url": "https://angor.fr"}


def _name(iso, countries):
    item = countries.by_iso2.get(iso) if countries and iso else None
    return (item or {}).get("name_fr") or iso or "En mer"


def _line(ev, countries):
    place = ev.get("place") or _name(ev.get("country"), countries)
    mark = " ✔ Vérifié" if ev.get("verified") else ""
    title = ev["title"][:140]
    head = f"{place} – " if place and place.lower()[:20] not in title.lower() else ""
    return f"• [{SEV.get(ev['severity'], ev['severity'])}] {head}{title}{mark}"


def build_digest(events, country_risk, pulse, now, cfg, countries=None, news=None, crises=None, agenda=None):
    """Texte du point quotidien (liste de blocs)."""
    since = now - timedelta(hours=24)
    day = [e for e in events if parse_iso(e["date"]) >= since and e.get("confidence") != "low"]
    top = sorted([e for e in day if e["severity"] >= cfg["min_severity"]],
                 key=lambda e: (-e["severity"], -len(e.get("sources") or []), e["date"]))[:cfg["max_items"]]
    blocks = []
    n_sev = {s: sum(1 for e in day if e["severity"] == s) for s in (4, 3, 2)}
    blocks.append(f"24 dernières heures : {len(day)} incident(s) fiables – {n_sev[4]} critique(s), "
                  f"{n_sev[3]} élevé(s), {n_sev[2]} modéré(s).")
    if top:
        blocks.append("À retenir\n" + "\n".join(_line(e, countries) for e in top))
    # crises en cours : pays avec le plus d'incidents graves sur 72 h
    since72 = now - timedelta(hours=72)
    by = {}
    for e in events:
        if e.get("country") and e["severity"] >= 3 and e.get("confidence") != "low" and parse_iso(e["date"]) >= since72:
            by[e["country"]] = by.get(e["country"], 0) + 1
    hot = sorted(by.items(), key=lambda x: -x[1])[:5]
    if hot:
        blocks.append("Crises en cours (72 h)\n" + "\n".join(
            f"• {_name(iso, countries)} : {n} incident(s) grave(s)"
            + (f" – risque {country_risk[iso]['level']}/5" if iso in country_risk else "") for iso, n in hot))
    movers = sorted([(iso, p) for iso, p in (pulse or {}).items() if p.get("d7") is not None and p["d7"] <= -5],
                    key=lambda x: x[1]["d7"])[:5]
    if movers:
        blocks.append("Pulse – stabilité en baisse sur 7 jours\n" + "\n".join(
            f"• {_name(iso, countries)} : {p['value']}/100 ({p['d7']:+d})" + _cause(p) for iso, p in movers))
    esc = [c for c in crises or [] if c["status"] == "active" and c["trend"] in ("escalating", "new")][:4]
    if esc:
        blocks.append("Chronologies en escalade ou nouvelles\n" + "\n".join(
            f"• {c['title']} : {c['n']} incidents depuis le {c['start'][8:10]}/{c['start'][5:7]}"
            f" (gravité max {c['max_severity']}/4)" for c in esc))
    follow_set = {c.upper() for c in cfg.get("countries") or []}
    a, b = now.date().isoformat(), (now + timedelta(days=7)).date().isoformat()
    soon = [e for e in agenda or [] if a <= e["d"] <= b and e.get("prec", "day") == "day" and (
        e["type"] in ("election", "religious") or e.get("src") == "Angor" or e.get("iso") in follow_set)]
    if soon:
        blocks.append("À venir (7 jours)\n" + "\n".join(
            f"• {e['d'][8:10]}/{e['d'][5:7]} – {_name(e['iso'], countries) + ' : ' if e.get('iso') else ''}{e['t_fr']}"
            for e in soon[:10]))
    kev = [n for n in news or [] if n.get("source") == "CISA KEV" and parse_iso(n["date"]) >= now - timedelta(hours=36)]
    if kev:
        kev.sort(key=lambda n: -(n.get("severity") or 0))
        blocks.append(f"Cyber – {len(kev)} vulnérabilité(s) activement exploitée(s) ajoutée(s) par la CISA\n"
                      + "\n".join(f"• {n['title'][:150]}" for n in kev[:4]))
    follow = [c.upper() for c in cfg.get("countries") or []]
    if follow:
        lines = []
        for iso in follow:
            evs = [e for e in day if e.get("country") == iso]
            p = (pulse or {}).get(iso) or {}
            r = country_risk.get(iso) or {}
            head = f"• {_name(iso, countries)} : risque {r.get('level', '–')}/5"
            if p:
                head += f", Pulse {p['value']}/100" + (f" ({p['d7']:+d} sur 7 j)" if p.get("d7") is not None else "")
            head += f", {len(evs)} incident(s) en 24 h"
            lines.append(head)
            for e in sorted(evs, key=lambda e: -e["severity"])[:3]:
                lines.append("   " + _line(e, countries))
        blocks.append("Vos pays suivis\n" + "\n".join(lines))
    url = cfg.get("site_url") or "https://angor.fr"
    blocks.append(f"Carte : {url}/?h=24" + ("&watch=1" if follow else ""))
    return blocks


def _cause(p):
    for d in p.get("drivers") or []:
        if d["type"] == "category":
            return f" – hausse : {CATEGORIES.get(d['category'], {}).get('fr', d['category']).lower()}"
        if d["type"] == "advisory":
            return f" – avis {d['source']} : {d['from']} → {d['to']}"
    return ""


def send_digest(events, country_risk, pulse, store, settings, log, now, countries=None, news=None, crises=None,
                agenda=None):
    cfg = {**DIGEST, **(settings.get("digest") or {})}
    if not cfg["enabled"]:
        return False
    st = store.setdefault("state", {})
    today = now.strftime("%Y-%m-%d")
    if now.hour < int(cfg["hour_utc"]) or st.get("digest_last") == today:
        return False
    blocks = build_digest(events, country_risk, pulse, now, cfg, countries, news, crises, agenda)
    from . import llm
    edito = llm.digest_editorial(blocks, store, settings, now, log)
    if edito:
        blocks.insert(0, "L'essentiel du jour (synthèse IA)\n" + edito.strip())
    header = f"Angor Intelligence – point quotidien du {now:%d/%m/%Y}"
    if deliver(header, blocks, cfg, log):
        st["digest_last"] = today
        log("  Point quotidien envoyé")
        return True
    if not (secret("TELEGRAM_BOT_TOKEN") or secret("SMTP_HOST")):
        st["digest_last"] = today  # aucun canal configuré (usage local) : on n'insiste pas
    return False


def send_pulse_alerts(items, settings, log, countries=None):
    if not items:
        return False
    url = (settings.get("digest") or {}).get("site_url") or DIGEST["site_url"]
    blocks = []
    for a in items[:10]:
        why = (f"passe sous le seuil de {(settings.get('pulse') or {}).get('threshold', 40)}"
               if a["reason"] == "threshold" else f"{a['d7']:+d} points en 7 jours")
        blocks.append(f"• {_name(a['iso'], countries)} : Pulse {a['value']}/100 – {why}{_cause(a)}\n"
                      f"  {url}/?country={quote(a['iso'])}")
    ok = deliver(f"Angor Intelligence – alerte stabilité ({len(items)} pays)", blocks,
                 {"telegram": True, "email": True, **(settings.get("alerts") or {})}, log)
    if ok:
        log(f"  {len(items)} alerte(s) Pulse envoyée(s)")
    return ok
