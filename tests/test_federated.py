"""Tests for Phase-2 federated training: convergence, robustness, gate, registry."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "training"))

from model import init_params, loss
from federated import FederatedTrainer, fedavg, robust_median, local_update
from validation_gate import validate
from model_registry import ModelRegistry


def make_data(seed=1, N=600):
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, (N, 2))
    p = 1 / (1 + np.exp(-(X @ np.array([1.5, -2.0]) + 0.5)))
    y = (rng.random(N) < p).astype(float)
    return X, y


def shards_of(X, y, k=4):
    idx = np.array_split(np.arange(len(y)), k)
    return [(X[i], y[i]) for i in idx]


def test_federated_training_reduces_loss():
    X, y = make_data()
    t = FederatedTrainer(init_params(2), aggregator=fedavg)
    before = loss(t.params, X, y)
    for _ in range(30):
        t.run_round(shards_of(X, y))
    assert loss(t.params, X, y) < before - 0.1   # meaningful improvement


def test_robust_aggregation_resists_malicious_update():
    X, y = make_data()
    shards = shards_of(X, y, 4)
    good = FederatedTrainer(init_params(2), aggregator=fedavg)
    robust = FederatedTrainer(init_params(2), aggregator=robust_median)
    for _ in range(30):
        # node 0 is malicious: returns a huge garbage update every round
        bad = [np.full(3, 1e6)] + [None, None, None]
        good.run_round(shards, node_updates=bad)
        robust.run_round(shards, node_updates=bad)
    # plain FedAvg is wrecked by the poison; coordinate-median stays sane
    assert not np.all(np.isfinite(good.params)) or loss(good.params, X, y) > 1.0
    assert loss(robust.params, X, y) < 0.6


def test_validation_gate_rejects_regression():
    X, y = make_data()
    good = init_params(2)
    for _ in range(40):
        good = local_update(good, X, y)
    worse = np.zeros_like(good)            # untrained -> higher loss
    res = validate(worse, good, X, y)
    assert not res.ok and "regression" in res.reason


def test_validation_gate_accepts_improvement_and_requires_human():
    X, y = make_data()
    trained = init_params(2)
    for _ in range(40):
        trained = local_update(trained, X, y)
    base = init_params(2)
    assert validate(trained, base, X, y).ok                       # improves -> ok
    r = validate(trained, base, X, y, require_human=True)
    assert not r.ok and "human" in r.reason                       # gated on human
    assert validate(trained, base, X, y, require_human=True, human_approved=True).ok


def test_registry_requires_gate_and_is_signed_appendonly():
    X, y = make_data()
    reg = ModelRegistry()
    p0 = init_params(2)
    v1 = reg.promote(p0, validate(p0, None, X, y), note="genesis")
    trained = p0.copy()
    for _ in range(40):
        trained = local_update(trained, X, y)
    v2 = reg.promote(trained, validate(trained, reg.latest_params(), X, y), note="round-1")
    assert v2.version == 2 and v2.parent == v1.hash
    assert reg.verify(v2) and reg.verify_chain()
    # a model that fails the gate cannot be promoted
    import pytest
    bad = validate(np.zeros_like(trained), reg.latest_params(), X, y)
    with pytest.raises(PermissionError):
        reg.promote(np.zeros_like(trained), bad)


def test_registry_detects_tampering():
    X, y = make_data()
    reg = ModelRegistry()
    p0 = init_params(2)
    v = reg.promote(p0, validate(p0, None, X, y))
    v.params[0] += 1.0          # tamper after signing
    assert not reg.verify(v)
