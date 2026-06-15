# Distributed GUA — how it lives everywhere, survives kill-switches, and improves with everyone's compute

This document answers a concrete set of questions: if GUA is published on GitHub
and adopted by many people, can the model be **trained from one machine yet
stored across all the nodes**, **grow as adoption grows**, **survive any node
hitting its kill-switch without losing information**, and eventually **gain the
tools and reasoning to improve — even improve itself**?

Short answer: yes, the design is coherent and every piece has real precedent. The
honest gap is between the *reference implementations* already in this repo and a
*production system running across thousands of machines* — and part of that gap
is genuine research frontier. This doc maps each goal to a concrete mechanism, a
real framework, a build order, and the hard parts.

It is deliberately honest about limits (R6). Nothing here promises a weekend build.

---

## 0. The six goals, in one table

| Goal | Mechanism | Real precedent | Status in this repo |
|------|-----------|----------------|---------------------|
| Train from my PC, model stored on the nodes | federated training + content-addressed model blobs | Hivemind, BitTorrent/IPFS | reference (`training/federated.py`, `network/replication.py`) |
| Lives everywhere, grows with adoption | replication across nodes + signed version registry | IPFS pinning, BitTorrent | reference (`replication.py`, `training/model_registry.py`) |
| A node kills its switch, no info lost | replication factor R + self-healing rebalance | RAID/quorum, IPFS re-pin | **demonstrated** (`network/replication_demo.py`, tests) |
| Improve with everyone's compute | distributed/federated training | DiLoCo, SWARM, Petals | reference (`training/`) |
| Get the tools + logic you (Claude) have | native tool-calling agent loop | OpenAI/Anthropic tool use | **working** (`webui/backend/server.py`) |
| Improve itself | validation gate + signed registry + human review | standard MLOps + governance | reference, **bounded by design** (`training/validation_gate.py`) |

---

## 1. "Lives everywhere" and "a node's kill-switch never loses the model"

This is the most important property and it is already demonstrated. Run:

```
demo_resilience.bat        (or:  python network/replication_demo.py)
```

**How it works (`network/replication.py`):**

1. **Content-addressing.** The model's weights are a blob identified by their
   SHA-256. Any copy that hashes to the same value is provably the same model;
   tampering is detectable for free.
2. **Replication factor R.** Each blob is stored on R different nodes (e.g. 3).
   The model is available while **at least one** of them is alive.
3. **The local kill-switch only stops your own node.** Your copy becomes
   unreachable; the other replicas keep serving the model. Your machine stopping
   never takes the network down — which is exactly what makes the kill-switch
   safe to press. (This also satisfies the Constitution's R5 + the "No-Off
   Problem" stance in the Whitepaper: *local* halt is guaranteed, the *network*
   does not depend on any single node.)
4. **Self-healing.** After a node dies, `rebalance()` copies the blob to another
   surviving node to restore R — like BitTorrent re-seeding or IPFS re-pinning.
5. **Honest failure mode.** The model is lost only if **every** replica
   disappears at once. Replication factor + rebalance + many nodes make that
   vanishingly unlikely; the code reports it truthfully rather than pretending.

**Authenticity vs. availability.** `replication.py` guarantees *availability and
integrity* (the bytes are there and uncorrupted). *Authenticity* — that a blob is
a blessed, gate-approved version and not a malicious fork — is handled by the
**signed** `training/model_registry.py` (ed25519, append-only, parent-linked).
Together: the registry says *which* version is canonical; replication makes that
version *durable* across the swarm.

**What production needs underneath:** a real peer-to-peer transport with a
Distributed Hash Table (DHT) so nodes can find *who holds which blob*, plus
chunked streaming of large weight files. The availability math is identical to
the demo; only the transport changes (see §2).

---

## 2. Concrete frameworks (don't reinvent these)

- **libp2p + Kademlia DHT** — peer discovery, NAT traversal, the "who has blob X"
  lookup. This replaces the single bootstrap coordinator. (Phase 1.)
- **IPFS / BitTorrent-style content distribution** — moving large weight blobs
  efficiently; content-addressing is already what `replication.py` models.
- **Petals** — run a *large* LLM split across many volunteer machines for
  **inference** (each node holds a few transformer layers). This is the fastest
  path to "a big brain runs on the network." (Phase 1→2.)
- **Hivemind** — decentralized **training** over the internet (averaging updates
  across volunteers). The protocol matches `training/federated.py`. (Phase 2.)
- **DiLoCo / SWARM-style low-communication training** — research methods that
  make training over slow home links feasible by syncing infrequently. (Phase 2,
  research-adjacent.)
- **Ollama / llama.cpp** — the local model runtime each node already uses; the
  per-node execution engine.

Rule of thumb: **inference-on-the-network first (Petals), training-on-the-network
second (Hivemind), self-improvement last (gated).** Each stage is useful alone.

---

## 3. Build order (concrete, tied to the existing ROADMAP)

**Stage A — make the swarm real (Phase 1).**
1. Swap the bootstrap coordinator for **libp2p + DHT**; keep signed messages.
2. Put `replication.py` on top of the DHT: blobs chunked, announced, fetched by
   hash; `rebalance()` driven by real "under-replicated" events.
3. Ship the node-client as a tray app: opt-in, idle-only, resource caps, the
   local kill-switch — all already specified in `docs/node-client-spec.md`.
   *Deliverable: people install a client and the model is durably distributed.*

**Stage B — a big brain runs on the network (Phase 1→2).**
4. Integrate **Petals** so a 70B-class model runs split across volunteers, behind
   the same `GuaService` chat path and the same policy gate.
   *Deliverable: GUA answers with a genuinely large model, served by the swarm.*

**Stage C — the network trains (Phase 2).**
5. Integrate **Hivemind** for federated rounds; keep the robust-median aggregator
   (resists poisoned updates) and route rounds over the live transport.
6. Every improved model goes through the **validation gate**, gets **signed** in
   the registry, then replicated. *Deliverable: collective compute improves open
   models under enforced rules.*

**Stage D — bounded self-improvement (Phase 3).**
7. Periodic auto-retraining proposes candidates; the gate + human review for
   significant changes decide promotion; the signed registry gives rollback.
   *Deliverable: GUA improves itself within controlled, reversible bounds.*

---

## 4. The hard parts (so nothing blindsides you)

- **Training big models over home internet is bandwidth-bound, not GPU-bound.**
  This is the single hardest problem. Low-communication methods (DiLoCo) help but
  it remains the research frontier. Expect slow, infrequent global updates.
- **Security is an arms race.** Malicious nodes can try to poison training
  updates or serve bad blobs. Defenses in place/planned: content-addressing
  (bad bytes fail the hash), robust-median aggregation, redundant execution +
  majority vote, node reputation, signed versions. None is a silver bullet.
- **Adoption is a precondition, not a guarantee.** "Compute grows with users"
  only works if enough people actually run nodes. The client must be trivial to
  install and visibly safe (opt-in, caps, kill-switch).
- **Scale ≠ intelligence.** The network gives you *compute and durability*. A
  genuinely capable model still requires a strong base and good training. Don't
  expect distribution alone to make GUA smart.
- **Secure aggregation / privacy.** So the coordinator can't read individual
  updates (R7). Real but adds complexity.

---

## 5. Invariants kept at every stage (non-negotiable)

- **Local kill-switch always works and never depends on the network.**
- **R1 (non-harm) and R2 (peace) stay immutable; the ruleset stays signed.**
- **No model ships without passing the validation gate** (R5: no unchecked
  self-improvement).
- **Opt-in, idle-only, resource-capped** participation — a node owner is always
  in control of their machine.
- **We stop at bounded self-improvement (Phase 3) unless safety keeps pace.**
  This is the responsible choice and it is stated in the Whitepaper and Roadmap.

---

## 6. What you can run today

- `demo_resilience.bat` — kill nodes, watch the model survive (this doc's §1).
- `python training/train_demo.py` — model improves across **signed** versions
  despite a malicious node; a regression is rejected by the gate.
- `start_gua.bat` — the live assistant with the **native tool-calling** agent
  (it decides on its own when to search/read the web) and enforced rules.

These are real, tested reference pieces. The work ahead is swapping the toy
transport/model for libp2p + Petals/Hivemind — large engineering, well-trodden
paths, and safe to do incrementally because each stage stands on its own.
