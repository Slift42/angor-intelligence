"""Annuaire des prestataires : catégories, fusion inscrits / repérés par Angor, grille de qualité identique partout."""
import json
import re

from conftest import ROOT
from veille import http, providers

CFG = json.loads((ROOT / "config" / "providers.json").read_text(encoding="utf-8"))
DIR = json.loads((ROOT / "config" / "providers_directory.json").read_text(encoding="utf-8"))


def test_configuration():
    cats = CFG["categories"]
    assert set(CFG["tiers"]) == {"A", "B", "C", "D", "E"}
    assert all(c["group"] in CFG["groups"] and c["fr"] and c["en"] for c in cats.values())
    isos = set(re.findall(r'"iso2":"([A-Z]{2})"', (ROOT / "docs" / "data" / "countries.js").read_text(encoding="utf-8")))
    entries = DIR["providers"] + [dict(p, countries=[iso]) for iso, lst in DIR["local"].items() for p in lst]
    webs = [p["web"].rstrip("/").lower() for p in entries]
    assert len(webs) == len(set(webs)), "doublon dans l'annuaire"
    for p in DIR["providers"]:
        assert set(p["regions"]) <= set(DIR["regions"]), p["name"]
    for p in entries:
        assert p["web"].startswith("https://") and p["categories"] and p["name"].strip(), p["name"]
        assert set(p["categories"]) <= set(cats), (p["name"], set(p["categories"]) - set(cats))
        assert set(p.get("countries") or []) <= isos, (p["name"], p.get("countries"))
        assert len(p.get("note", "")) <= 160, p["name"]
        assert not re.search(r"\+?\d[\d .-]{7,}\d|@", p.get("note", "")), p["name"]          # aucun numéro ni e-mail
    assert {"care", "pclin"} <= set(cats) and cats["pclin"]["group"] == "sante"
    assert sum(len(v) for v in DIR["local"].values()) >= 350 and len(DIR["local"]) >= 150   # registres locaux (v0.25)


def test_fusion_et_doublons():
    reg = [{"id": "1", "name": "Garda (inscrit)", "web": "https://garda.com/fr", "hq": "CA", "countries": ["ML"],
            "categories": ["cp", "inconnue"], "tier": "B", "score": 70, "source": "self"}]
    d = providers.build(reg, CFG, DIR)
    names = [p["name"] for p in d["providers"]]
    assert not any("Garda" in n for n in names)                      # remplacé par la fiche inscrite (même domaine)
    assert d["registered"][0]["categories"] == ["cp"]                # catégorie inconnue écartée
    assert all(p["tier"] == "E" and p["source"] == "angor" for p in d["providers"])
    assert d["services"]["cp"]["fr"] and "providers" in d and "local" in d   # compatibilité rapport pays / Travel buddy


def test_lecture_supabase(monkeypatch):
    calls = []

    def fake_get_json(url, **kw):
        calls.append((url, kw))
        return [{"id": "x", "name": "Jet Co", "categories": ["jet"], "countries": ["FR"], "website": "https://jet.example",
                 "tier": "C", "score": 64, "hq_country": "FR"}]
    monkeypatch.setattr(http, "get_json", fake_get_json)
    cfg = {"accounts": {"supabase_url": "https://p.supabase.co", "supabase_anon_key": "sb_publishable_x"}}
    reg = providers.fetch_registered(cfg)
    assert reg[0]["name"] == "Jet Co" and reg[0]["web"] == "https://jet.example"
    assert calls[0][1]["params"]["status"] == "in.(submitted,verified)" and calls[0][1]["headers"] == {"apikey": "sb_publishable_x"}
    assert providers.fetch_registered({}) == []


def _weights(text):
    m = re.search(r"POIDS: ([a-z_=0-9 ]+)", text)
    return dict(kv.split("=") for kv in m.group(1).split())


def test_grille_de_qualite_identique():
    sql = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
    js = (ROOT / "docs" / "providers-lib.js").read_text(encoding="utf-8")
    w_sql, w_js = _weights(sql), _weights(js)
    assert w_sql == w_js and sum(map(int, w_sql.values())) == 100
    for key, pts in w_js.items():                                    # chaque poids est réellement utilisé dans le code JS
        assert re.search(rf"\['{key}', {pts},", js), key
    start = sql.index("function private.provider_score")
    body = sql[start:sql.index("end $$;", start)]
    assert sorted(int(x) for x in re.findall(r"s := s \+ (\d+)", body)) == sorted(int(v) for v in w_sql.values())
    page = (ROOT / "docs" / "annuaire.html").read_text(encoding="utf-8")   # critères publiés (transparence du classement)
    assert "15 points" in page and "aucune option payante" in page.lower()


def test_justificatifs_obligatoires_et_types_identiques():
    """v0.21 : mêmes types de justificatifs côté base et écran ; immatriculation exigée pour soumettre et pour vérifier."""
    sql = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
    js = (ROOT / "docs" / "providers-lib.js").read_text(encoding="utf-8")
    m = re.search(r"provider_documents_kind_check\s+check \(kind in \(([^)]*)\)\)", sql)
    kinds_sql = set(re.findall(r"'(\w+)'", m.group(1)))
    block = js[js.index("const DOC_KINDS = {"):js.index("const docActive")]
    kinds_js = set(re.findall(r"^    (\w+): \{", block, re.M))
    assert kinds_sql == kinds_js and {"registration", "licence", "insurance", "certification", "cv"} <= kinds_js
    scored = dict(re.findall(r"^    (\w+): \{ key: '(doc_\w+)'", block, re.M))
    assert set(scored.values()) == {k for k in _weights(js) if k.startswith("doc_")}       # chaque type noté a son poids
    assert sum(int(v) for k, v in _weights(js).items() if k.startswith("doc")) >= 50           # les justificatifs pèsent au moins la moitié
    guard = sql[sql.index("function private.providers_guard"):]
    assert "new.status = 'submitted'" in guard and "kind = 'registration'" in guard and "d.status = 'validated'" in guard
    assert "function private.doc_active" in sql and "d.kind <> 'insurance'" in sql                # assurance : date de fin obligatoire
