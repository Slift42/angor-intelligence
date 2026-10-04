"""Configuration commune des tests (pytest).

Les tests n'utilisent jamais le réseau : tout appel à veille.http est bloqué par la fixture `no_network`,
active par défaut. Un test qui a besoin d'une réponse distante la simule avec monkeypatch.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from veille import geo, http, model  # noqa: E402

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise RuntimeError("Accès réseau interdit pendant les tests : simulez la réponse avec monkeypatch.")
    monkeypatch.setattr(http, "get", blocked)
    monkeypatch.setattr(http, "get_json", blocked)
    monkeypatch.setattr(http, "post_json", blocked)


@pytest.fixture(scope="session")
def countries():
    return geo.Countries()


def make(id="e1", source="Press", category="attack", severity=3, title="Gunmen attack army post near Bamako",
         date="2026-09-30T10:00:00+00:00", lat=12.65, lon=-8.0, country="ML", tags=None, **kw):
    """Événement standard minimal pour les tests."""
    e = model.make_event(id=id, source=source, category=category, severity=severity, title=title, date=date,
                         lat=lat, lon=lon, url=f"https://example.org/{id}", country=country, tags=tags or [], **kw)
    return e
