"""Page d'aide en anglais (docs/help.html), générée depuis l'aide française (docs/aide.html) – v0.29, run 4.

L'aide française reste la seule source : on la modifie, puis on relance ce script. Chaque texte de la page (nœud de
texte, aria-label, title, alt, placeholder) est cherché dans tools/aide_en.json (texte français, espaces normalisés →
texte anglais). Le balisage, les ancres (#apercu…) et le style sont recopiés à l'identique.

    python tools/build_help_en.py            # régénère docs/help.html
    python tools/build_help_en.py --check    # liste les textes sans traduction (code de sortie 1), sans rien écrire

Un texte nouveau ou modifié dans aide.html sans traduction fait échouer tests/test_help_en.py : ajoutez la ligne
correspondante dans tools/aide_en.json (le message d'erreur donne le texte exact à traduire).
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "aide.html"
OUT = ROOT / "docs" / "help.html"
MAP = ROOT / "tools" / "aide_en.json"
NOTICE = "<!-- Généré par tools/build_help_en.py depuis docs/aide.html : ne pas modifier à la main. -->"

_TOKEN_RE = re.compile(r"(<!--.*?-->|<[^>]+>)", re.S)
_ATTR_RE = re.compile(r'(\s(?:aria-label|title|alt|placeholder)=")([^"]*)(")')
# liens entre les deux versions de l'aide
_SWAPS = [('<html lang="fr">', '<html lang="en">'),
          ('href="aide.html', 'href="help.html'),
          ('href="help.html" hreflang="en" lang="en"', 'href="aide.html" hreflang="fr" lang="fr"')]   # dans cet ordre


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def load_map(path=MAP):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def translate(src, mapping):
    """(html anglais, textes sans traduction, clés utilisées)."""
    missing, used = [], set()

    def tr(raw, escape):
        text = norm(html.unescape(raw))
        if not text:
            return raw
        if text not in mapping:
            missing.append(text)
            return raw
        used.add(text)
        lead = raw[: len(raw) - len(raw.lstrip())]
        trail = raw[len(raw.rstrip()):]
        return lead + escape(mapping[text]) + trail

    out, skip = [], None
    for part in _TOKEN_RE.split(src):
        if not part:
            continue
        if part.startswith("<"):
            low = part.lower()
            if skip and low.startswith("</" + skip):
                skip = None
            elif not part.startswith("<!") and re.match(r"<(style|script)\b", low):
                skip = re.match(r"<(style|script)", low).group(1)
            if not part.startswith("<!") and not part.startswith("</"):
                for a, b in _SWAPS:
                    part = part.replace(a, b)
                part = _ATTR_RE.sub(lambda m: m.group(1) + tr(m.group(2), lambda t: html.escape(t, quote=True))
                                    + m.group(3), part)
            out.append(part)
        elif skip:
            out.append(part)
        else:
            out.append(tr(part, lambda t: html.escape(t, quote=False)))
    page = "".join(out)
    page = page.replace("<!doctype html>", "<!doctype html>\n" + NOTICE, 1)
    return page, list(dict.fromkeys(missing)), used


def build(src_path=SRC, map_path=MAP):
    return translate(Path(src_path).read_text(encoding="utf-8"), load_map(map_path))


def main(argv):
    page, missing, used = build()
    unused = sorted(set(load_map()) - used)
    if missing:
        print(f"{len(missing)} texte(s) de aide.html sans traduction dans tools/aide_en.json :")
        for t in missing:
            print("  " + json.dumps(t, ensure_ascii=False))
    if unused:
        print(f"{len(unused)} traduction(s) inutilisée(s) (texte supprimé ou modifié dans aide.html) :")
        for t in unused[:20]:
            print("  " + json.dumps(t, ensure_ascii=False)[:120])
    if "--check" in argv:
        return 1 if missing else 0
    if missing:
        print("docs/help.html non régénéré : complétez d'abord les traductions.")
        return 1
    OUT.write_text(page, encoding="utf-8")
    print(f"docs/help.html régénéré ({len(used)} textes traduits).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
