# Roadmap

GUA is built in phases. **Each phase produces something useful and complete in itself** — we do not bet everything on the final phase. Timelines are indicative.

For the reasoning behind each phase, see the [Whitepaper §7](./WHITEPAPER.md#7-phased-roadmap-realistic).

---

## Phase 0 — Foundation ◀ *current*

**Goal:** a credible, open, well-governed project people can understand and join.

- [x] Whitepaper (vision + architecture + honest limits)
- [x] Constitution + machine-readable `ruleset.yaml`
- [x] Governance, Security, Contributing, Code of Conduct
- [x] License (AGPL-3.0)
- [x] Repository skeleton
- [x] Claude-like chat interface shell (`webui/index.html`) with opt-in, caps, and local kill-switch
- [x] ed25519 signing/verification tooling; `ruleset.yaml` signed (regenerate your own key before publishing)
- [x] Reference policy engine (`safety/`) enforcing R1/R2, with tests
- [x] Node-client state machine (`node-client/`) for consent/caps/kill-switch, with tests
- [x] Chat backend bridge (`webui/backend/`) that rule-checks every message, with tests
- [x] Detailed node-client spec (`docs/node-client-spec.md`)
- [ ] Replace the keyword policy stub with a real safety classifier
- [ ] Publish the repo publicly on GitHub (after pasting full AGPL text into LICENSE)
- [ ] Open the first design-review issues

**Deliverable:** this repository — docs **and** a tested reference implementation of the governance/safety/consent core.

---

## Phase 1 — Volunteer compute network (months ~2–6)

**Goal:** people can install a client, contribute idle compute safely, and use an AI model running on the network.

- [ ] Node-client: explicit opt-in flow, idle detection, resource caps, **local kill-switch**, tray app + dashboard
- [~] Node registry: discovery, heartbeats/TTL, reputation, eligible-worker selection (`network/registry.py`, tested) — libp2p transport still pending
- [x] Task scheduler: redundant execution, majority-vote verification, malicious-node exclusion, policy-gated submission (`network/scheduler.py`, tested + `network/demo.py`)
- [x] Real socket transport: nodes connect over TCP across processes/machines (`network/transport.py`, tested + `network/net_demo.py`)
- [x] Replicated resilient model store: model blobs content-addressed + replicated across nodes, self-healing `rebalance()`, a node's kill-switch never loses the model (`network/replication.py`, tested + `network/replication_demo.py` / `demo_resilience.bat`). See [`docs/DISTRIBUTED_DESIGN.md`](./docs/DISTRIBUTED_DESIGN.md).
- [ ] Full P2P transport (libp2p / Kademlia DHT, NAT traversal) + public bootstrap nodes + encrypted signed messages
- [x] Execution sandbox: process isolation + CPU/memory limits + timeout + task whitelist (`safety/sandbox.py`, tested) — container/WASM hardening still to come
- [x] Inference-as-work + honest generative-verification design (`network/inference_worker.py`, tested); deterministic decoding so honest nodes agree
- [x] Policy-engine: refuses R1–R10 violations on tasks and outputs (`safety/policy_engine.py`, tested)
- [x] End-to-end chat over the network: `GuaService` runs a prompt as verified inference across nodes; backend NETWORK mode + UI provenance (`network/service.py`, `network/chat_demo.py`, tested). Point `GUA_MODEL_URL` at a real model (Ollama/llama.cpp) to replace the stand-in.
- [ ] Container/WASM hardening for full filesystem & network isolation
- [ ] Swap the single bootstrap coordinator for true libp2p P2P

**Deliverable:** a working, safe volunteer-compute network with a real demo. Valuable on its own.

---

## Phase 2 — Decentralized training (months ~6–12)

**Goal:** the network *improves* models, not just runs them.

- [x] Federated training: nodes train on private shards, coordinator aggregates (`training/federated.py`, tested) — share updates, not data (R7)
- [x] Robust aggregation that resists malicious updates (coordinate-wise median), the training analogue of vote-verification (`training/federated.py`, tested)
- [x] Model registry: versioning, hashes, **ed25519 signatures**, parent-linked append-only history with `verify_chain()` (`training/model_registry.py`, tested)
- [x] Policy engine (tasks **and** outputs checked against R1–R10)
- [x] Node reputation + majority-vote verification (`network/`, tested)
- [~] Hivemind/Petals integration for real large models (reference uses a small model; protocol is the same) — pending
- [ ] Secure aggregation + stronger Byzantine-robust aggregators (Krum, trimmed mean); wire rounds onto live transport

**Deliverable:** collective compute that trains open models under enforced rules — demonstrated in `training/train_demo.py` (model improves across signed versions despite a malicious node).

---

## Phase 3 — Bounded self-improvement (year ~1–2)

**Goal:** the *realistic, responsible* form of "self-improvement."

- [x] **Validation gate**: candidate must be sane + not regress on holdout before promotion (`training/validation_gate.py`, tested)
- [x] **Human-in-the-loop** approval gate for significant changes; signed registry gives rollback via version history (`training/`, tested)
- [x] **Real fine-tuning pipeline** (`training/finetune/`): a GUA dataset, an Ollama custom-model path (runs today), a real LoRA weight-training script (GPU), and a gated `/promote` that bumps the version only after identity + safety checks (tested)
- [ ] Periodic auto-retraining on new data + auto-tuning of hyperparameters (driving the gate automatically)
- [ ] Begin progressive decentralization of governance (threshold signing)

**Deliverable:** a system that meaningfully improves itself within controlled, safe bounds.

---

## Phase 4 — North-star: more autonomous self-improvement (year 2+, research)

**Goal:** the long-term "recursive self-improvement" ambition.

- [ ] *Precondition:* demonstrated progress on alignment and on responsibly addressing the No-Off Problem.
- [ ] Only proceed if safety keeps pace.

**Honest commitment:** if safety does not keep pace, **we stop at Phase 3.** That is the responsible choice, and the same position taken by serious AI labs. This phase is research, possibly never fully reached — and that is acceptable.

---

## Cross-cutting (every phase)

- Keep the opt-in, idle-only, resource-cap, and local kill-switch guarantees intact.
- Keep R1 and R2 immutable.
- Prefer safety over speed.
