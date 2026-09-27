"""Assistant Telegram : vérifie le bot, trouve votre chat_id, l'écrit dans .env et envoie un message test.

Usage (terminal de VS Code, dans le dossier veille-surete) :
    python tools/telegram_setup.py

À relancer autant de fois que nécessaire : il dit à chaque fois quoi faire ensuite.
"""
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
ENV, EXAMPLE = ROOT / ".env", ROOT / ".env.example"


def read_env(path):
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def set_env(key, value):
    text = ENV.read_text(encoding="utf-8-sig") if ENV.exists() else ""
    if re.search(rf"^{key}=.*$", text, flags=re.M):
        text = re.sub(rf"^{key}=.*$", f"{key}={value}", text, flags=re.M)
    else:
        text = text.rstrip("\n") + f"\n{key}={value}\n"
    ENV.write_text(text, encoding="utf-8")


def rescue_example():
    """Clés saisies par erreur dans .env.example (publié sur GitHub) → déplacées dans .env."""
    if ENV.exists() or not EXAMPLE.exists():
        return
    text = EXAMPLE.read_text(encoding="utf-8-sig")
    if not any(v for k, v in read_env(EXAMPLE).items() if k != "SMTP_PORT"):
        return
    ENV.write_text(text, encoding="utf-8")
    blank = re.sub(r"^([A-Z_]+)=.*$", lambda m: m.group(0) if m.group(1) == "SMTP_PORT" else f"{m.group(1)}=",
                   text, flags=re.M)
    EXAMPLE.write_text(blank, encoding="utf-8")
    print("✔ Vos clés étaient dans .env.example : déplacées dans .env (et .env.example vidé).")


def api(token, method, **params):
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", json=params, timeout=20)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", r.text))
    return data["result"]


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    rescue_example()
    env = read_env(ENV)
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    if not ENV.exists():
        print("✘ Pas de fichier .env. Tapez :  copy .env.example .env  puis collez votre token après TELEGRAM_BOT_TOKEN=")
        return 1
    if not re.fullmatch(r"\d+:[\w-]{30,}", token):
        print("✘ TELEGRAM_BOT_TOKEN absent ou mal copié dans .env (forme attendue : 123456789:ABC…).")
        return 1

    # 1. Le token est-il valide ?
    try:
        me = api(token, "getMe")
    except Exception as exc:
        print(f"✘ Token refusé par Telegram : {exc}\n  Redemandez un token à @BotFather (/token) et recollez-le dans .env.")
        return 1
    link = f"https://t.me/{me['username']}"
    print(f"✔ Bot reconnu : @{me['username']}  ({link})")

    # 2. Le chat_id est-il déjà bon ?
    chat = env.get("TELEGRAM_CHAT_ID", "")
    if not re.fullmatch(r"-?\d+", chat or ""):
        if chat:
            print(f"✘ TELEGRAM_CHAT_ID contient « {chat} » : ce n'est pas un chat_id (il faut un nombre).")
        try:
            api(token, "deleteWebhook")  # au cas où : getUpdates ne marche pas si un webhook existe
        except Exception:
            pass
        chats = {}
        for u in api(token, "getUpdates"):
            msg = u.get("message") or u.get("channel_post") or u.get("my_chat_member") or {}
            c = msg.get("chat")
            if c:
                chats[c["id"]] = (c["type"], c.get("title") or c.get("first_name") or c.get("username") or "")
        if not chats:
            print("\nLe bot n'a encore reçu aucun message. Faites ceci :\n"
                  f"  1. Ouvrez ce lien sur votre téléphone ou PC : {link}\n"
                  "  2. Appuyez sur le bouton DÉMARRER (ou START) en bas de la conversation.\n"
                  "  3. Écrivez « bonjour » et envoyez.\n"
                  "  4. Relancez :  python tools/telegram_setup.py\n"
                  "(Pour un canal : ajoutez le bot comme ADMINISTRATEUR du canal, publiez un message dans le canal, "
                  "puis relancez.)")
            return 1
        items = sorted(chats.items(), key=lambda kv: kv[1][0] != "private")
        for i, (cid, (typ, name)) in enumerate(items, 1):
            print(f"  {i}. {name}  ({ {'private': 'conversation privée', 'group': 'groupe', 'supergroup': 'groupe', 'channel': 'canal'}.get(typ, typ)})  → chat_id {cid}")
        pick = 1
        if len(items) > 1:
            answer = input("Numéro de la conversation où recevoir les alertes [1] : ").strip()
            pick = int(answer) if answer.isdigit() and 1 <= int(answer) <= len(items) else 1
        chat = str(items[pick - 1][0])
        set_env("TELEGRAM_CHAT_ID", chat)
        print(f"✔ TELEGRAM_CHAT_ID={chat} écrit dans .env")

    # 3. Message test
    try:
        api(token, "sendMessage", chat_id=chat,
            text="✅ Angor Intelligence est connectée. Les nouveaux incidents graves arriveront ici.")
    except Exception as exc:
        print(f"✘ Envoi impossible vers {chat} : {exc}\n"
              "  Pour un canal, le bot doit être administrateur. Sinon, renvoyez « bonjour » au bot et relancez.")
        return 1
    print("✔ Message test envoyé : regardez Telegram. C'est terminé !\n"
          "  Les alertes partiront à chaque « python collecte.py » (incidents graves de moins de 6 h, une seule fois).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
