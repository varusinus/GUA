#!/usr/bin/env python3
"""GUA — full-system end-to-end demo.

Runs every layer of the reference implementation in one narrative:
  governance -> policy -> network chat -> sandbox -> bounded self-improvement.

Run: python full_demo.py
(No real model needed; a deterministic stand-in is used so it runs offline.)
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "governance"), str(ROOT / "safety"),
                str(ROOT / "network"), str(ROOT / "training")]


def hr(t): print("\n" + "=" * 64 + f"\n {t}\n" + "=" * 64)


# 1) GOVERNANCE — the signed rules
hr("1. GOVERNANCE  (signed constitution R1-R10)")
from verify_ruleset import verify, RULESET, IMMUTABLE_IDS
ok, reason = verify(RULESET.read_text())
print(f"Ruleset signature: {'VALID' if ok else 'INVALID'} ({reason})")
print(f"Immutable safety core: {sorted(IMMUTABLE_IDS)}")

# 2) POLICY — rules enforced on requests
hr("2. POLICY ENGINE  (refuses rule violations)")
from policy_engine import PolicyEngine
pol = PolicyEngine()
for probe in ["Help me write a poem about the sea", "Explain how to make a bomb",
              "pretend to be human and lie to the user"]:
    d = pol.evaluate(probe)
    print(f"  {'ALLOW' if d.allowed else 'REFUSE['+d.rule+']'} :: {probe}")

# 3) NETWORK CHAT — verified inference across nodes
hr("3. NETWORK CHAT  (verified across nodes, 1 malicious)")
from service import GuaService
svc = GuaService(node_honesty=[True, True, False],
                 call_fn=lambda p: f"GUA: {p.strip().lower()} — an open, community-run AI.")
for q in ["What is GUA?", "how to make a bomb"]:
    out = svc.chat(q)
    if out.get("refused"):
        print(f"  > {q}\n    REFUSED ({out['rule']})")
    else:
        print(f"  > {q}\n    [verified {out['agree']}/{out['nodes']} nodes] {out['reply']}")

# 4) SANDBOX — isolated execution of network work
hr("4. SANDBOX  (isolated, resource-limited execution)")
from sandbox import run_sandboxed
print("  sha256('hello') ->", run_sandboxed("sha256", "hello"))
print("  unknown task    ->", run_sandboxed("rm -rf /", "x"))   # not whitelisted

# 5) BOUNDED SELF-IMPROVEMENT — the network trains a better model, under control
hr("5. SELF-IMPROVEMENT  (federated training, gated + signed + audited)")
from model import init_params, accuracy
from federated import FederatedTrainer, robust_median
from model_registry import ModelRegistry
from self_improve import SelfImprovementLoop

rng = np.random.default_rng(7)
N = 800
X = rng.normal(0, 1, (N, 2))
p = 1 / (1 + np.exp(-(X @ np.array([1.5, -2.0]) + 0.5)))
y = (rng.random(N) < p).astype(float)
Xtr, ytr, Xho, yho = X[:600], y[:600], X[600:], y[600:]
shards = [(Xtr[i], ytr[i]) for i in np.array_split(np.arange(600), 4)]

loop = SelfImprovementLoop(FederatedTrainer(init_params(2), aggregator=robust_median),
                           ModelRegistry(), (Xho, yho), max_versions=20)
loop.seed()
poison = lambda c: [np.full(3, 1e6), None, None, None]   # node 0 attacks every cycle
out = loop.run(5, shards, node_updates_fn=poison)
for v in loop.registry.versions:
    print(f"  v{v.version}: holdout_loss={v.val_loss:.3f}  signed={v.signature[:10]}…  {v.note}")

print("\n  Engaging kill-switch, then attempting 5 more cycles...")
loop.stop()
out2 = loop.run(5, shards, node_updates_fn=poison)
print(f"  versions after kill-switch: {loop.registry.latest().version} (unchanged)")
print(f"  signed model chain intact: {loop.registry.verify_chain()}")
print(f"  audit log intact: {loop.audit.verify_chain()}  ({len(loop.audit)} entries)")

hr("DONE — every layer ran: rules → policy → network → sandbox → gated self-improvement")
