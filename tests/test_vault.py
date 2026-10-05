"""Coffre des données réservées (v0.22) : rien de réservé ne reste sur le site public, envoi des seuls fichiers modifiés,
carte des visiteurs allégée."""
from datetime import datetime, timedelta, timezone

import pytest

from veille import vault

SETTINGS = {"accounts": {"supabase_url": "https://p.supabase.co/", "supabase_anon_key": "sb_publishable_x"}}


class FakeResp:
    def __init__(self, code=200):
        self.status_code = code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, data=None, headers=None, timeout=None):
        self.calls.append((url, headers))
        return FakeResp()


@pytest.fixture
def site(tmp_path, monkeypatch):
    out, keep = tmp_path / "docs" / "data", tmp_path / "data" / "private"
    for rel in ("data.js", "events.geojson", "country/FR.js", "archive/2026-08.js", "profiles.js",
                "config.js", "countries.js", "legal.js", "providers.js", "guest.js", "history/index.js", "guides.js"):
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text("window.X = 1;", encoding="utf-8")
    monkeypatch.setattr(vault, "OUT", out)
    monkeypatch.setattr(vault, "KEEP", keep)
    monkeypatch.setattr(vault, "MANIFEST", tmp_path / "data" / "vault_manifest.json")
    monkeypatch.setenv("VS_PUBLIC", "1")
    return out, keep


def test_tri_public_reserve():
    assert vault.is_public("config.js") and vault.is_public("history/map/2025-01.js") and vault.is_public("guest.js")
    assert not vault.is_public("data.js") and not vault.is_public("country/FR.js") and not vault.is_public("early_warning.js")


def test_inactif_hors_ligne(site, monkeypatch):
    monkeypatch.delenv("VS_PUBLIC")
    assert vault.publish_private(SETTINGS) is None and (site[0] / "data.js").exists()      # PC : rien ne bouge
    monkeypatch.setenv("VS_PUBLIC", "1")
    assert not vault.enabled({"accounts": {}})                                              # comptes non configurés


def test_envoi_puis_retrait_du_site(site, monkeypatch):
    out, keep = site
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "sb_secret_test")
    s = FakeSession()
    r = vault.publish_private(SETTINGS, log=lambda m: None, session=s)
    sent = sorted(u.split("/angor-data/")[1] for u, _ in s.calls)
    assert sent == ["archive/2026-08.js", "country/FR.js", "data.js", "events.geojson", "profiles.js"]
    assert s.calls[0][0].startswith("https://p.supabase.co/storage/v1/object/angor-data/")
    assert s.calls[0][1]["apikey"] == "sb_secret_test" and s.calls[0][1]["x-upsert"] == "true"
    assert r == {"files": 5, "uploaded": 5, "failed": 0, "key": True}
    left = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert left == ["config.js", "countries.js", "guest.js", "guides.js", "history/index.js", "legal.js", "providers.js"]
    assert (keep / "data.js").exists() and not (out / "country").exists()
    # collecte suivante : profils remis en place, fichiers identiques non renvoyés
    vault.restore()
    assert (out / "profiles.js").exists()
    (out / "data.js").write_text("window.X = 2;", encoding="utf-8")
    s2 = FakeSession()
    vault.publish_private(SETTINGS, log=lambda m: None, session=s2)
    assert [u.split("/angor-data/")[1] for u, _ in s2.calls] == ["data.js"]


def test_fermeture_par_defaut_sans_cle(site, monkeypatch):
    out, _ = site
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    logs = []
    r = vault.publish_private(SETTINGS, log=logs.append, session=FakeSession())
    assert r["uploaded"] == 0 and not r["key"] and "SUPABASE_SERVICE_KEY" in logs[0]
    assert not (out / "data.js").exists() and not (out / "events.geojson").exists()   # jamais publiés en clair


def test_carte_des_visiteurs():
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    ev = [{"id": "a", "date": (now - timedelta(days=1)).isoformat(), "severity": 3, "category": "attack", "lat": 1, "lon": 2,
           "title": "T", "summary": "résumé réservé", "sources": [{"url": "https://x"}], "url": "https://x"},
          {"id": "b", "date": (now - timedelta(days=12)).isoformat(), "severity": 4, "category": "attack", "lat": 1, "lon": 2, "title": "old"}]
    g = vault.guest_payload({"events": ev, "taxonomy": {"categories": {}}, "countries": {"FR": {"level": 2}},
                             "news": [1], "settings": {"product_name": "Angor", "buddy_url": "https://secret"}}, now)
    assert [e["id"] for e in g["events"]] == ["a"] and g["guest"] is True
    assert "summary" not in g["events"][0] and "sources" not in g["events"][0] and "url" not in g["events"][0]
    assert g["countries"] == {} and g["news"] == [] and g["settings"] == {"product_name": "Angor"}


def test_compartiment_reserve_aux_comptes_valides():
    from conftest import ROOT
    sql = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
    assert f"('{vault.BUCKET}', '{vault.BUCKET}', false," in sql                        # compartiment privé
    pol = sql[sql.index("create policy angor_data_read"):]
    pol = pol[:pol.index("$p$")]
    assert "to authenticated" in pol and "private.is_approved()" in pol and "for select" in pol
