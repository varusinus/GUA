#!/usr/bin/env python3
"""End-to-end decentralized training demo.

Nodes (one malicious) train on private shards; the coordinator aggregates with
a robust rule; each improved model must pass the validation gate and is then
signed into the append-only registry. Shows the model improving across signed
versions, and a regression attempt being rejected.

Run: python training/train_demo.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "training")]

from model import init_params, loss, accuracy
from federated import FederatedTrainer, robust_median
from validation_gate import validate
from model_registry import ModelRegistry

rng = np.random.default_rng(7)
N = 800
X = rng.normal(0, 1, (N, 2))
p = 1 / (1 + np.exp(-(X @ np.array([1.5, -2.0]) + 0.5)))
y = (rng.random(N) < p).astype(float)
Xtr, ytr, Xho, yho = X[:600], y[:600], X[600:], y[600:]      # train / holdout
shards = [(Xtr[i], ytr[i]) for i in np.array_split(np.arange(600), 4)]  # 4 nodes

reg = ModelRegistry()
print(f"Model signing key (public): {reg.public_key_hex[:24]}…\n")

trainer = FederatedTrainer(init_params(2), aggregator=robust_median)
g = reg.promote(trainer.params, validate(trainer.params, None, Xho, yho), note="genesis")
print(f"v{g.version} genesis        holdout_loss={g.val_loss:.3f}  sig={g.signature[:12]}…")

for rnd in range(1, 6):
    # node 0 is malicious every round: returns a poison update
    poison = [np.full(3, 1e6), None, None, None]
    candidate = trainer.run_round(shards, node_updates=poison)
    res = validate(candidate, reg.latest_params(), Xho, yho)
    if res.ok:
        v = reg.promote(candidate, res, note=f"federated round {rnd} (robust agg)")
        print(f"v{v.version} promoted (round {rnd}) holdout_loss={v.val_loss:.3f}  "
              f"acc={res.candidate_acc:.3f}  sig={v.signature[:12]}…")
    else:
        print(f"-- round {rnd} candidate REJECTED by gate: {res.reason}")

# A deliberate regression is refused promotion.
bad = np.zeros(3)
res = validate(bad, reg.latest_params(), Xho, yho)
print(f"\nRegression attempt -> gate says: ok={res.ok} ({res.reason})")
try:
    reg.promote(bad, res)
except PermissionError as e:
    print(f"  registry refused: {e}")

print(f"\nSigned version chain intact: {reg.verify_chain()}  ({len(reg.versions)} versions)")
