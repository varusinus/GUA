#!/usr/bin/env python3
"""Resilience demo: GUA's model survives nodes hitting their kill-switch.

Run:  python network/replication_demo.py

It builds a small network, stores a "model", then kills nodes one by one and
shows the model is still fully recoverable (and verified by hash) until the very
last replica is gone — and that `rebalance()` heals redundancy after a death.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replication import ReplicatedModelStore, ModelLost


def line(c="-"):
    print(c * 64)


def show(store, key):
    holders = store.replicas_alive(key)
    print(f"   alive nodes: {store.alive_nodes()}")
    print(f"   model replicas alive: {len(holders)}  -> {holders}")
    try:
        data = store.get(key)
        print(f"   GET '{key}': OK ({len(data)} bytes), integrity={store.integrity_ok(key)}")
    except ModelLost as e:
        print(f"   GET '{key}': LOST — {e}")


def main():
    line("=")
    print("GUA resilience demo — the model lives across nodes")
    line("=")

    # A 5-node network, every model replicated on 3 of them.
    store = ReplicatedModelStore(replication_factor=3)
    for i in range(1, 6):
        store.add_node(f"node{i}")

    # The "model weights" — any bytes; here a stand-in blob.
    model = b"GUA-MODEL-WEIGHTS-v1::" + bytes(range(256)) * 8
    m = store.put("gua-model", model, version=1)
    print(f"\nStored 'gua-model' v{m.version}  sha256={m.sha256[:16]}…  "
          f"size={m.size}B  on {sorted(m.replicas)}")
    print("(Replication factor 3: three nodes each hold a full copy.)\n")
    show(store, "gua-model")

    line()
    print("1) node holding a replica hits its LOCAL KILL-SWITCH (goes offline)")
    victim = sorted(m.replicas)[0]
    store.kill_node(victim)
    print(f"   -> {victim} stopped. Its own data is retained, just unreachable.")
    show(store, "gua-model")
    print("   The model is still served by the other replicas. Nothing lost.")

    line()
    print("2) self-healing: rebalance() restores redundancy on survivors")
    rep = store.rebalance("gua-model")
    print(f"   -> replicas after heal: {rep['gua-model']}")
    show(store, "gua-model")

    line()
    print("3) a node leaves PERMANENTLY (disk wiped) — still fine")
    gone = store.replicas_alive("gua-model")[0]
    store.wipe_node(gone)
    print(f"   -> {gone} wiped for good.")
    store.rebalance("gua-model")
    show(store, "gua-model")

    line()
    print("4) keep killing until only ONE replica remains")
    while len(store.replicas_alive("gua-model")) > 1:
        store.kill_node(store.replicas_alive("gua-model")[0])
    show(store, "gua-model")
    print("   Down to a single survivor — the model is STILL fully recoverable.")

    line()
    print("5) revive a stopped node — its retained copy rejoins the network")
    dead = [n for n in store._alive if not store._alive[n]]
    if dead:
        store.revive_node(dead[0])
        print(f"   -> {dead[0]} resumed.")
    show(store, "gua-model")

    line("=")
    print("Takeaway: any node (including yours) can stop anytime via its")
    print("kill-switch and the network keeps the model. It is only ever lost")
    print("if EVERY replica disappears at once — which is what replication")
    print("factor + rebalance are designed to prevent.")
    line("=")


if __name__ == "__main__":
    main()
