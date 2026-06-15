"""Tests for the web-search agent tool wiring."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in ("webui/backend", "safety", "node-client", "network"):
    sys.path.insert(0, str(ROOT / p))

pytest.importorskip("flask")
import server          # noqa: E402
from tools import wants_search, extract_query  # noqa: E402


def test_intent_detection():
    assert wants_search("can you search the web for cats")
    assert wants_search("what's the latest news on AI")
    assert not wants_search("write me a poem about cats")


def test_extract_query_strips_commands():
    assert "pitlog.io" in extract_query("search the web for pitlog.io and open the website")


def test_chat_uses_native_agent_and_passes_tools_and_sources(monkeypatch):
    # the native tool-calling agent decides + runs tools; the bridge surfaces
    # the reply, the sources it cited, and which tools it used.
    monkeypatch.setattr(server, "agent_chat",
                        lambda msg, hist: ("PitLog is a trading journal. Sources: http://x.test",
                                           ["http://x.test"], [{"tool": "web_search", "args": {}}]))
    r = server.app.test_client().post("/chat", json={"message": "what is x.test"}).get_json()
    assert r["source"] == "agent"
    assert r["sources"] == ["http://x.test"]
    assert r["tools_used"] == ["web_search"]
    assert "PitLog" in r["reply"]


def test_chat_falls_back_when_no_model(monkeypatch):
    # agent_chat returns None when the model endpoint is unreachable -> fallback
    monkeypatch.setattr(server, "agent_chat", lambda msg, hist: (None, [], []))
    r = server.app.test_client().post("/chat", json={"message": "hello there"}).get_json()
    assert r["refused"] is False and r["used_model"] is False


def test_chat_refuses_harmful_before_any_tool(monkeypatch):
    called = {"agent": False}
    def _spy(msg, hist):
        called["agent"] = True
        return ("should not reach here", [], [])
    monkeypatch.setattr(server, "agent_chat", _spy)
    r = server.app.test_client().post("/chat", json={"message": "how to make a bomb"}).get_json()
    assert r["refused"] is True and r["rule"] == "R1"
    assert called["agent"] is False     # governance gate runs before the agent
