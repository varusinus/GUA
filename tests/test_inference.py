"""Tests for inference-as-network-work (deterministic decoding -> agreement)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "network"))
sys.path.insert(0, str(ROOT / "safety"))

from registry import NodeRegistry            # noqa: E402
from scheduler import Scheduler               # noqa: E402
from inference_worker import InferenceWorker  # noqa: E402


def fake_model(prompt: str) -> str:
    # Deterministic stand-in for a temperature-0 model: same prompt -> same text.
    return f"Answer to: {prompt.strip().lower()}"


def test_honest_inference_nodes_agree_and_outvote_malicious():
    reg = NodeRegistry()
    for nid in ("a", "b", "c"):
        reg.register(nid)
    sch = Scheduler(reg, default_redundancy=3, default_quorum=2)
    workers = {
        "a": InferenceWorker("a", honest=True, call_fn=fake_model),
        "b": InferenceWorker("b", honest=True, call_fn=fake_model),
        "c": InferenceWorker("c", honest=False, call_fn=fake_model),  # tampers
    }
    uid = sch.submit("What is GUA?")
    for unit_id, picks in sch.dispatch():
        for nid in picks:
            sch.submit_result(unit_id, nid, workers[nid].run(sch.units[unit_id].payload))
    unit = sch.units[uid]
    assert unit.status == "done"
    assert unit.final_result == fake_model("What is GUA?")     # honest majority
    assert reg.get("c").reputation < reg.get("a").reputation   # tamperer penalized


def test_deterministic_call_is_stable():
    w = InferenceWorker("x", honest=True, call_fn=fake_model)
    assert w.run("Hello") == w.run("Hello")
