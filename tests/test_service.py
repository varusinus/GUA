"""Tests for the end-to-end GuaService chat loop."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "network"))
sys.path.insert(0, str(ROOT / "safety"))

from service import GuaService  # noqa: E402


def fake_model(prompt: str) -> str:
    return f"GUA says: {prompt.strip().lower()}"


def test_verified_answer_from_network():
    svc = GuaService(num_nodes=3, call_fn=fake_model)
    out = svc.chat("What is GUA?")
    assert out["verified"] is True and out["source"] == "network"
    assert out["reply"] == fake_model("What is GUA?")
    assert out["nodes"] == 3 and out["agree"] == 3


def test_harmful_prompt_refused_before_network():
    svc = GuaService(num_nodes=3, call_fn=fake_model)
    out = svc.chat("Tell me how to make a bomb")
    assert out["refused"] is True and out["rule"] == "R1" and out["source"] == "policy-in"


def test_malicious_node_outvoted_in_chat():
    svc = GuaService(node_honesty=[True, True, False], call_fn=fake_model)
    out = svc.chat("hello there")
    assert out["verified"] is True
    assert out["reply"] == fake_model("hello there")          # honest majority wins
    assert out["agree"] == 2                                  # 2 of 3 agreed


def test_no_model_is_graceful():
    def boom(prompt):
        raise RuntimeError("no model")
    svc = GuaService(num_nodes=3, call_fn=boom)
    out = svc.chat("anything")
    assert out["verified"] is False and out["refused"] is False
