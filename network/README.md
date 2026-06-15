# network/  *(Phase 1 — reference implementation)*

The peer-to-peer coordination layer: who is on the network, and how work is
distributed and verified. The trust/scheduling semantics are implemented and
unit-tested here; the real libp2p transport plugs in underneath later.

## What's implemented (runnable, tested)

- **`registry.py` — node discovery & reputation.** Register nodes, track
  heartbeats with a TTL (silent nodes drop out), maintain per-node reputation,
  and select eligible workers (opted-in, alive, sufficiently trusted),
  best-reputation-first. The clock is injectable for deterministic tests.
- **`scheduler.py` — task distribution & verification.** Submit work (checked
  by the [policy engine](../safety/policy_engine.py) *before* it reaches the
  network), assign each unit to several **distinct** nodes (redundancy),
  resolve by **majority vote**, and reward/penalize nodes by whether they
  agreed — so faulty or malicious nodes lose reputation and get excluded.
  Includes timeout handling (`reassign_unresponsive`, `force_resolve`).
- **`worker.py` — work executor.** Deterministic stub so honest nodes agree;
  `SimWorker(honest=False)` models a malicious node for simulations.
- **`transport.py` — real socket transport.** A length-prefixed JSON protocol
  over TCP. A `Coordinator` hosts the registry + scheduler and serves nodes;
  `NodeAgent`s connect over real sockets to register, pull work, and return
  results. This runs across separate OS processes / machines — not just
  in-process. (Full internet-scale P2P replaces the single Coordinator later.)
- **`demo.py` / `net_demo.py` — swarm simulations.** `python network/demo.py`
  runs it in-process; `python network/net_demo.py` runs the same scenario over
  real TCP sockets. Both show redundant dispatch, a refused rule-violating
  task, and a malicious node losing reputation until it is excluded.

## What's still pending (later in Phase 1)

- **Full P2P transport:** libp2p + Kademlia DHT and NAT traversal, replacing the
  single bootstrap `Coordinator` with true peer-to-peer discovery.
- **Public bootstrap nodes** to join the network for the first time.
- **Encrypted, signed** inter-node messages.
- **Sandbox execution** of real work units (see [`../safety/`](../safety/README.md)).

## How it fits

```
client opts in ──► registry (discovery + reputation)
                        │  eligible workers
                        ▼
   submit(task) ─► scheduler ──redundant assign──► nodes ──results──┐
        │            │                                              │
   policy check   majority vote + reputation update  ◄──────────────┘
   (R1..R10)         │
                     ▼
                final result (faulty/malicious nodes outvoted & excluded)
```

See [WHITEPAPER 4.3–4.4](../WHITEPAPER.md#43-the-network-layer-p2p).
