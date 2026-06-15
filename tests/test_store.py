"""Tests for the persistent store (memory + stats + version)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "webui" / "backend"))

from store import Store, memory_preamble


def test_memory_persists_across_reload(tmp_path):
    p = tmp_path / "s.json"
    s = Store(p)
    s.add_turn("user", "my name is Alex")
    s.add_turn("assistant", "hi Alex")
    reloaded = Store(p)
    assert [t["content"] for t in reloaded.recent()] == ["my name is Alex", "hi Alex"]


def test_stats_increment_and_persist(tmp_path):
    p = tmp_path / "s.json"
    s = Store(p)
    s.inc_messages()
    s.bump_work(3)
    reloaded = Store(p)
    assert reloaded.status()["messages_served"] == 1
    assert reloaded.status()["work_units"] == 3


def test_reset_memory(tmp_path):
    s = Store(tmp_path / "s.json")
    s.add_turn("user", "x")
    s.reset_memory()
    assert s.recent() == []


def test_preamble_includes_recent_turns(tmp_path):
    s = Store(tmp_path / "s.json")
    s.add_turn("user", "my color is blue")
    assert "my color is blue" in memory_preamble(s.recent())


def test_version_bump_persists(tmp_path):
    p = tmp_path / "s.json"
    s = Store(p)
    assert s.status()["gua_version"] == 1
    assert s.bump_version("improved persona") == 2
    assert Store(p).status()["gua_version"] == 2


def test_conversations_are_saved_and_switchable(tmp_path):
    p = tmp_path / "s.json"
    s = Store(p)
    s.new_conversation()
    s.add_turn("user", "first chat hello")
    c1 = s.data["active"]
    s.new_conversation()
    s.add_turn("user", "second chat about rules")
    assert len(s.list_conversations()) == 2          # both kept
    assert s.switch(c1)
    assert [t["content"] for t in s.recent()] == ["first chat hello"]
    # persists across reload
    s2 = Store(p)
    assert s2.status()["conversation_count"] == 2
    assert s2.status()["active"] == c1


def test_titles_come_from_first_message(tmp_path):
    s = Store(tmp_path / "s.json")
    s.new_conversation()
    s.add_turn("user", "What are the rules?")
    assert s.list_conversations()[0]["title"].startswith("What are the rules")
