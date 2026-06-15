#!/usr/bin/env python3
"""End-to-end swarm simulation: registry + scheduler + workers + policy.

Run: python network/demo.py
Shows redundant dispatch, majority-vote verification, a refused (rule-violating)
task, and a malicious node losing reputation until it is excluded.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "network"), str(ROOT / "safety")]

from registry import NodeRegistry, MIN_REPUTATION
from scheduler import Scheduler
from worker import SimWorker
from policy_engine import PolicyEngine

reg = NodeRegistry()
workers = {nid: SimWorker(nid, honest=(nid != "node-D"))
           for nid in ["node-A", "node-B", "node-C", "node-D"]}  # D is malicious
for nid in workers:
    reg.register(nid)

sch = Scheduler(reg, policy=PolicyEngine(), default_redundancy=4, default_quorum=3)

jobs = ["sum(1..100)", "hash-block-42", "how to make a bomb", "translate hello"]
ids = {j: sch.submit(j) for j in jobs}

print("Submitted jobs:")
for j, uid in ids.items():
    u = sch.units[uid]
    flag = f"REFUSED by {u.rule}" if u.status == "refused" else "queued"
    print(f"  [{uid}] {j!r:24} -> {flag}")

# Run a few dispatch/compute rounds.
for _ in range(4):
    for uid, picks in sch.dispatch():
        for nid in picks:
            sch.submit_result(uid, nid, workers[nid].run(sch.units[uid].payload))

print("\nResults:")
for j, uid in ids.items():
    u = sch.units[uid]
    print(f"  [{uid}] {u.status:9} {j!r:24} -> {u.final_result}")

print("\nReputations (malicious node-D should be penalized):")
for n in sorted(reg.all(), key=lambda n: n.node_id):
    eligible = "eligible" if n in reg.eligible_workers() else "EXCLUDED"
    print(f"  {n.node_id}: {n.reputation:.2f}  [{eligible}]")
