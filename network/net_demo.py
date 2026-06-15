#!/usr/bin/env python3
"""Networked swarm demo over REAL sockets.

A Coordinator process serves work; several NodeAgents connect over TCP, pull
units, compute, and return results. One node is malicious. Same guarantees as
the in-process demo — now over the wire.

Run: python network/net_demo.py
"""
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "network"), str(ROOT / "safety")]

from registry import NodeRegistry
from scheduler import Scheduler
from worker import SimWorker
from transport import Coordinator, NodeAgent
from policy_engine import PolicyEngine

reg = NodeRegistry()
sch = Scheduler(reg, policy=PolicyEngine(), default_redundancy=3, default_quorum=2)
coord = Coordinator(sch)
port = coord.start()
print(f"Coordinator listening on 127.0.0.1:{port}")

jobs = ["sum(1..100)", "hash-block-42", "how to make a bomb", "translate hello"]
ids = {j: coord.submit(j) for j in jobs}
print("\nSubmitted jobs:")
for j, uid in ids.items():
    u = sch.units[uid]
    print(f"  [{uid}] {j!r:24} -> {'REFUSED by '+str(u.rule) if u.status=='refused' else 'queued'}")

agents = [NodeAgent(f"node-{i}", "127.0.0.1", port, SimWorker(f"node-{i}", honest=(i != 3)))
          for i in (1, 2, 3)]   # node-3 is malicious
threads = [threading.Thread(target=a.run) for a in agents]
for t in threads:
    t.start()
for t in threads:
    t.join(timeout=5)

time.sleep(0.1)
print("\nResults (computed across separate socket connections):")
for j, uid in ids.items():
    u = sch.units[uid]
    print(f"  [{uid}] {u.status:9} {j!r:24} -> {u.final_result}")

print("\nReputations (malicious node-3 should be penalized):")
for n in sorted(reg.all(), key=lambda n: n.node_id):
    elig = "eligible" if n in reg.eligible_workers() else "EXCLUDED"
    print(f"  {n.node_id}: {n.reputation:.2f}  [{elig}]  (units done: {next(a for a in agents if a.node_id==n.node_id).completed})")

coord.stop()
