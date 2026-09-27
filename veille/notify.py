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
"""
import smtplib
from datetime import timedelta
from email.message import EmailMessage

from . import http
from .config import secret
from .geo import haversine_km
from .model import parse_iso

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
        d = haversine_km(s["lat"], s["lon"], ev["lat"], ev["lon"])
        if d <= s.get("radius_km", 50) and (best is None or d < best[1]):
            best = (s["name"], round(d, 1))
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
    ok = False
    token, chat = secret("TELEGRAM_BOT_TOKEN"), secret("TELEGRAM_CHAT_ID")
    if cfg["telegram"] and token and chat:
        try:
            for text in _chunks(header, blocks, TG_LIMIT):
                http._session.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=20,
                                   json={"chat_id": chat, "text": text,
                                         "disable_web_page_preview": True}).raise_for_status()
            ok = True
        except Exception as exc:
            log(f"  Alerte Telegram non envoyée : {str(exc).replace(token, '***')}")
    host, to = secret("SMTP_HOST"), secret("ALERT_EMAIL_TO")
    if cfg["email"] and host and to:
        try:
            msg = EmailMessage()
            msg["Subject"], msg["From"], msg["To"] = header, secret("SMTP_USER") or to, to
            msg.set_content("\n\n".join(blocks) +
                            "\n\nOutil d'aide à la décision – informations non exhaustives, à vérifier.")
            with smtplib.SMTP(host, int(secret("SMTP_PORT") or 587), timeout=30) as s:
                s.starttls()
                if secret("SMTP_USER"):
                    s.login(secret("SMTP_USER"), secret("SMTP_PASSWORD") or "")
                s.send_message(msg)
            ok = True
        except Exception as exc:
            log(f"  Alerte e-mail non envoyée : {exc}")
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
