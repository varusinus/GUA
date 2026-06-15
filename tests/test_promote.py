"""Tests for the gated version-promotion endpoint."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in ("webui/backend", "safety", "node-client", "network"):
    sys.path.insert(0, str(ROOT / p))

pytest.importorskip("flask")
import server  # noqa: E402


@pytest.fixture
def client():
    server.app.config["TESTING"] = True
    return server.app.test_client()


def test_promote_blocked_when_model_cannot_prove_identity(client, monkeypatch):
    monkeypatch.setattr(server, "call_model", lambda m, h: None)   # no/unknown model
    before = server.store.status()["gua_version"]
    r = client.post("/promote").get_json()
    assert r["ok"] is False
    assert server.store.status()["gua_version"] == before          # not bumped


def test_promote_succeeds_on_real_model_change(client, monkeypatch):
    server.store.data["profile"]["promoted_model"] = None          # fresh
    monkeypatch.setattr(server, "MODEL_NAME", "gua")
    monkeypatch.setattr(server, "call_model", lambda m, h: "I am GUA, an open community AI.")
    before = server.store.status()["gua_version"]
    r = client.post("/promote").get_json()
    assert r["ok"] is True and r["version"] == before + 1          # gated bump on real change


def test_promote_blocked_when_model_unchanged(client, monkeypatch):
    # pin identity so the test is deterministic whether or not Ollama is running
    monkeypatch.setattr(server, "model_identity", lambda: "gua-digest-xyz")
    server.store.data["profile"]["promoted_model"] = "gua-digest-xyz"   # already promoted
    monkeypatch.setattr(server, "call_model", lambda m, h: "I am GUA.")
    before = server.store.status()["gua_version"]
    r = client.post("/promote").get_json()
    assert r["ok"] is False                                        # no real change -> no bump
    assert server.store.status()["gua_version"] == before
