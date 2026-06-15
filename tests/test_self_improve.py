"""Tests for the bounded self-improvement loop + audit log."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "training"))
sys.path.insert(0, str(ROOT / "safety"))

from model import init_params
from federated import FederatedTrainer, robust_median
from model_registry import ModelRegistry
from self_improve import SelfImprovementLoop
from audit_log import AuditLog


def _data(seed=3, N=800):
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, (N, 2))
    p = 1 / (1 + np.exp(-(X @ np.array([1.5, -2.0]) + 0.5)))
    y = (rng.random(N) < p).astype(float)
    return (X[:600], y[:600], X[600:], y[600:])


def _loop(**kw):
    Xtr, ytr, Xho, yho = _data()
    shards = [(Xtr[i], ytr[i]) for i in np.array_split(np.arange(600), 4)]
    trainer = FederatedTrainer(init_params(2), aggregator=robust_median)
    reg = ModelRegistry()
    loop = SelfImprovementLoop(trainer, reg, (Xho, yho), **kw)
    return loop, reg, shards


def test_audit_log_chain_and_tamper():
    log = AuditLog()
    log.append("a", {"x": 1}); log.append("b"); log.append("c")
    assert log.verify_chain() and len(log) == 3
    log.entries[1]["detail"] = {"x": 999}
    assert not log.verify_chain()


def test_loop_improves_and_signs_versions():
    loop, reg, shards = _loop(max_versions=10)
    loop.seed()
    out = loop.run(5, shards)
    assert out["final_version"] >= 4           # several improvements promoted
    assert out["audit_intact"] and reg.verify_chain()
    assert "promote" in loop.audit.events()


def test_kill_switch_halts_self_improvement():
    loop, reg, shards = _loop()
    loop.seed()
    loop.stop()
    out = loop.run(5, shards)
    assert reg.latest().version == 1           # nothing promoted after the seed
    assert "kill_switch_engaged" in loop.audit.events() and "halted" in loop.audit.events()


def test_version_cap_bounds_self_improvement():
    loop, reg, shards = _loop(max_versions=2)
    loop.seed()                                 # v1
    loop.run(10, shards)
    assert reg.latest().version == 2            # capped
    assert "max_versions_reached" in loop.audit.events()


def test_human_in_the_loop_gates_promotion():
    decision = {"approve": False}
    loop, reg, shards = _loop(require_human=True, approve_fn=lambda c, r: decision["approve"])
    loop.seed()
    loop.run(3, shards)
    assert reg.latest().version == 1            # nothing promoted while human withholds
    assert "rejected_pending_human" in loop.audit.events()
    decision["approve"] = True
    loop.run(2, shards)
    assert reg.latest().version >= 2            # promotes once approved
