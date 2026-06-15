# training/  *(Phase 2 — reference implementation)*

Decentralized training: **the network improves the model**, the responsible way.
Nodes train on their own private data shards and share only model updates (not
data); the coordinator aggregates them; and every improved version must pass a
**validation gate** and be **signed** before it is promoted. This is bounded
self-improvement — no model ships without passing a check (and, for significant
changes, a human).

## What's implemented (runnable, tested)

- **`model.py`** — a small logistic-regression model (predict / loss / gradient),
  dependency-light so the pipeline is testable. The federated protocol is the
  point, not the model size; larger models train the same way (Hivemind-style).
- **`federated.py`** — `local_update` (a node's work on its shard) and two
  aggregators: `fedavg` (size-weighted mean) and `robust_median` (coordinate-wise
  median that resists a malicious node's poison update). `FederatedTrainer`
  runs rounds.
- **`validation_gate.py`** — a candidate model is rejected unless it is
  numerically sane, does not regress on a holdout set, and (for significant
  changes) is human-approved. This is the corrigibility mechanism (R5) for
  self-improvement.
- **`model_registry.py`** — versioned, **ed25519-signed**, append-only model
  store with parent links; `promote()` REFUSES any candidate that didn't pass
  the gate; `verify_chain()` proves the lineage is intact and tamper-evident.
- **`train_demo.py`** — `python training/train_demo.py` shows the model
  improving across signed versions despite a malicious node, and a regression
  being rejected by the gate.

## What's still pending

- **Real models at scale** via Hivemind/Petals (Mixture-of-Experts, swarm
  parallelism) instead of the reference logistic model.
- **Secure aggregation** (so the coordinator can't read individual updates) and
  stronger Byzantine-robust aggregators (Krum, trimmed mean).
- Wiring the training rounds onto the live `network/` transport.

See [WHITEPAPER 4.5–4.6](../WHITEPAPER.md#45-the-decentralized-traininginference-pipeline)
and [6.2 (validation gate)](../WHITEPAPER.md#62-validation-gate-for-self-modification).
