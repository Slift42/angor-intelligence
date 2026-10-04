"""Pages légales (config/legal.json → docs/data/legal.js), entretien des comptes, absence de traceurs tiers."""
import json
import re

from conftest import ROOT
from veille import accounts, http, legal

LEGAL = json.loads((ROOT / "config" / "legal.json").read_text(encoding="utf-8"))
PAGES = sorted((ROOT / "docs").glob("*.html"))
LEGAL_PAGES = [ROOT / "docs" / f"{n}.html" for n in
               ("legal", "mentions-legales", "cgu", "cgv", "confidentialite", "sous-traitance", "licences", "annuaire")]


def test_build_signale_les_champs_vides_et_nettoie():
    data = legal.build(LEGAL, sources=[{"id": "a", "name": "Zeta", "license": "CC BY"},
                                       {"id": "b", "name": "alpha", "license": "x", "enabled": False}])
    assert "SIREN" in data["missing"] and "médiateur de la consommation" in data["missing"]
    assert not any(k.startswith("_") for k in data) and not any(k.startswith("_") for k in data["editeur"])
    assert [s["nom"] for s in data["sources"]] == ["Zeta"]                     # sources désactivées exclues
    assert all(s["nom"] and s.get("actif", True) for s in data["sous_traitants"])  # prestataires inactifs masqués
    full = json.loads(json.dumps(LEGAL))
    for path in legal.REQUIRED:
        d = full
        *parents, last = path.split(".")
        for p in parents:
            d = d[p]
        d[last] = "x"
    assert legal.build(full, sources=[])["missing"] == []


def test_configuration_coherente():
    assert LEGAL["status"] in ("projet", "en vigueur")
    for key, doc in LEGAL["documents"].items():
        assert (ROOT / "docs" / doc["page"]).exists(), doc["page"]
        assert re.fullmatch(r"\d+\.\d+", doc["version"]) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", doc["date"])
    assert {k for k, d in LEGAL["documents"].items() if d.get("acceptation")} <= {"cgu", "confidentialite", "cgv", "dpa", "annuaire"}


def test_pages_legales_references_valides():
    data = legal.build(LEGAL, sources=[])
    known_lists = {"hebergeurs", "sous_traitants", "tiers_techniques", "offres", "sources", "credits", "documents"}
    for page in LEGAL_PAGES:
        html = page.read_text(encoding="utf-8")
        assert 'src="data/legal.js"' in html and "legal.js?v=" in html, page.name
        for path in re.findall(r'data-v="([\w.]+)"', html):
            d = data
            for part in path.split("."):
                assert isinstance(d, dict) and part in d, f"{page.name} : champ inconnu {path}"
                d = d[part]
        assert set(re.findall(r'data-list="(\w+)"', html)) <= known_lists, page.name
        for flag in re.findall(r'data-if(?:not)?="(\w+)"', html):
            assert flag in data, f"{page.name} : {flag}"


def test_aucun_appel_a_google_fonts_ni_flagcdn():
    for f in PAGES + sorted((ROOT / "docs").glob("*.js")) + sorted((ROOT / "docs").glob("*.css")):
        text = f.read_text(encoding="utf-8")
        assert "fonts.googleapis.com" not in text and "flagcdn.com" not in text, f.name
    assert (ROOT / "docs" / "vendor" / "fonts" / "fonts.css").exists()
    assert (ROOT / "docs" / "vendor" / "flags" / "fr.svg").exists()


def test_lien_vers_les_informations_legales_partout():
    for name in ("compte.html", "admin.html", "aide.html"):
        assert "legal.html" in (ROOT / "docs" / name).read_text(encoding="utf-8"), name
    assert "legal.html" in (ROOT / "docs" / "app.js").read_text(encoding="utf-8")


def test_signe_de_vie_supabase(monkeypatch):
    assert accounts.ping({}, log=lambda m: None) is None                     # comptes non configurés : rien
    calls, logs = [], []

    def fake_post(url, body, headers=None, **kw):
        calls.append((url, headers))
        return "2026-10-04T12:00:00+00:00"
    monkeypatch.setattr(http, "post_json", fake_post)
    cfg = {"accounts": {"supabase_url": "https://x.supabase.co/", "supabase_anon_key": "sb_publishable_abc"}}
    assert accounts.ping(cfg, log=logs.append)
    assert calls[0][0] == "https://x.supabase.co/rest/v1/rpc/ping"
    assert calls[0][1] == {"apikey": "sb_publishable_abc"}                     # nouvelle clé : pas d'en-tête Bearer
    cfg["accounts"]["supabase_anon_key"] = "eyJabc"
    accounts.ping(cfg, log=logs.append)
    assert calls[1][1]["Authorization"] == "Bearer eyJabc"

    def boom(*a, **k):
        raise RuntimeError("404")
    monkeypatch.setattr(http, "post_json", boom)
    assert accounts.ping(cfg, log=logs.append) is None and "injoignable" in logs[-1]   # jamais d'exception


def test_schema_supabase_durci():
    """Recommandations du conseiller de sécurité Supabase (fonctions à privilèges)."""
    sql = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
    for fn in re.findall(r"create or replace function ([\w.]+)\(", sql):
        block = sql[sql.index(f"create or replace function {fn}("):]
        assert "set search_path" in block[:block.index(" as $$")], f"{fn} : search_path non fixé"
    for fn in ("admin_set_status", "delete_my_account", "accept_legal", "handle_new_user"):
        assert re.search(rf"revoke execute on function public\.{fn}\([^)]*\) from public, anon", sql), fn
    assert "create or replace function private.housekeeping()" in sql and "drop function if exists public.housekeeping()" in sql
    assert "public.is_admin()" not in "".join(l for l in sql.splitlines() if l.startswith("create policy"))
