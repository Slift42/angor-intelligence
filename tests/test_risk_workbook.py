"""Classeur de revue de l'analyse des risques (tools/build_risk_workbook.py).

Vérifie que le générateur tourne, que les onglets attendus existent et que les réglages affichés
sont bien ceux du code (sinon l'analyste relirait des valeurs fausses).
"""
import subprocess
import sys
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

ROOT = Path(__file__).resolve().parent.parent
TABS = ["Lisez-moi", "Échelles", "Catégories", "Règles de gravité", "Note pays", "Matrice menaces", "Pulse",
        "Cotation", "Médias", "Sources", "Mots-clés", "Jeu de test", "Fiabilité & alertes", "Alerte précoce",
        "Go-no-go", "Recommandations", "Villes", "Santé", "Journal"]


@pytest.fixture(scope="module")
def workbook(tmp_path_factory):
    out = tmp_path_factory.mktemp("wb") / "revue.xlsx"
    subprocess.run([sys.executable, str(ROOT / "tools" / "build_risk_workbook.py"), str(out)], check=True,
                   capture_output=True, cwd=ROOT)
    return openpyxl.load_workbook(out)


def test_onglets(workbook):
    assert workbook.sheetnames == TABS


def test_note_pays_reprend_les_poids_du_code(workbook):
    from veille.risk import DEFAULTS
    import json
    cfg = {**DEFAULTS, **json.loads((ROOT / "config" / "risk.json").read_text(encoding="utf-8"))}
    ws = workbook["Note pays"]
    w = cfg["weights"]
    assert [ws["B7"].value, ws["B8"].value, ws["B9"].value] == [w["advisories"], w["security"], w["hazards"]]
    assert ws["B15"].value == cfg["saturation_points"]


def test_simulateurs_en_formules(workbook):
    # Les résultats doivent être des formules (recalculées par Excel), jamais des valeurs figées.
    assert str(workbook["Note pays"]["U26"].value).startswith("=")
    assert str(workbook["Go-no-go"]["B68"].value).startswith("=")
    assert str(workbook["Pulse"]["J22"].value).startswith("=")


def test_pas_d_ecrasement(tmp_path):
    out = tmp_path / "a.xlsx"
    out.write_bytes(b"annotations de l'analyste")
    subprocess.run([sys.executable, str(ROOT / "tools" / "build_risk_workbook.py"), str(out)], check=True,
                   capture_output=True, cwd=ROOT)
    assert out.read_bytes() == b"annotations de l'analyste"
    assert len(list(tmp_path.glob("a_*.xlsx"))) == 1


def test_version_anglaise(tmp_path):
    """--lang en : onglets traduits, aucun texte sans traduction, formules et listes cohérentes."""
    out = tmp_path / "en.xlsx"
    run = subprocess.run([sys.executable, str(ROOT / "tools" / "build_risk_workbook.py"), str(out), "--lang", "en"],
                         check=True, capture_output=True, cwd=ROOT, text=True)
    # Les notes de villes sont du contenu que l'analyste modifie : une note nouvelle ou corrigée peut rester en
    # français sans bloquer. Tout autre texte doit être dans tools/risk_workbook_en.json (voir --missing).
    if "sans traduction" in run.stdout:
        assert run.stdout.split(" : ", 1)[1].split("\n")[0].startswith("Villes (") and "), " not in run.stdout, run.stdout
    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames[0] == "Read me" and "Country rating" in wb.sheetnames
    assert '"keep"' in wb["Test set"]["G10"].value and '"yes"' in wb["Test set"]["G10"].value
    assert wb["Read me"]["B25"].hyperlink.location.startswith("'Scales'")
    lists = [dv.formula1 for dv in wb["Go-no-go"].data_validations.dataValidation]
    assert any("Female traveller" in (f or "") for f in lists)
