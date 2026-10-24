"""Aide en anglais (docs/help.html) générée depuis l'aide française – v0.29, run 4."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_help_en  # noqa: E402


def test_toutes_les_phrases_de_l_aide_sont_traduites():
    page, missing, _ = build_help_en.build()
    assert not missing, ("textes de docs/aide.html sans traduction : ajoutez-les dans tools/aide_en.json puis lancez "
                         "python tools/build_help_en.py\n" + "\n".join(missing[:20]))


def test_help_html_est_a_jour():
    page, _, _ = build_help_en.build()
    assert (ROOT / "docs" / "help.html").read_text(encoding="utf-8") == page, \
        "docs/help.html n'est pas à jour : lancez python tools/build_help_en.py"


def test_meme_structure_et_memes_ancres():
    fr = (ROOT / "docs" / "aide.html").read_text(encoding="utf-8")
    en = (ROOT / "docs" / "help.html").read_text(encoding="utf-8")
    assert re.findall(r'id="([^"]+)"', fr) == re.findall(r'id="([^"]+)"', en)
    assert len(re.findall(r"<[a-zA-Z][^>]*>", fr)) == len(re.findall(r"<[a-zA-Z][^>]*>", en))
    assert '<html lang="en">' in en and 'href="aide.html" hreflang="fr"' in en
    assert 'href="help.html" hreflang="en"' in fr


def test_traduction_conserve_les_espaces_et_echappe():
    page, missing, used = build_help_en.translate(
        '<!doctype html><html lang="fr"><p aria-label="Sommaire"> Bonjour  <b>A &amp; B</b>\n</p>'
        '<script>const x = "Bonjour";</script></html>', {"Sommaire": "Contents", "Bonjour": "Hello", "A & B": "A & B"})
    assert not missing
    assert '<p aria-label="Contents"> Hello  <b>A &amp; B</b>\n</p>' in page
    assert 'const x = "Bonjour"' in page                    # scripts recopiés tels quels
    assert '<html lang="en">' in page


def test_lien_d_aide_selon_la_langue():
    js = (ROOT / "docs" / "app.js").read_text(encoding="utf-8")
    assert "state.lang === 'en' ? 'help.html' : 'aide.html'" in js
    assert 'href="aide.html"' not in js
    assert "'help.html'" in (ROOT / "docs" / "sw.js").read_text(encoding="utf-8")
