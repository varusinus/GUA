# GUA — Architecture & Status

This document maps the project's vision to what actually exists in the
repository, layer by layer, with the tests that back each claim. It's the
fastest way for a new contributor (or a skeptic) to see what's real.

**Status:** Phase 0–2 reference implementation complete and tested. **61 tests pass.**
Everything here runs offline with no model; point `GUA_MODEL_URL` at a real
open model (Ollama/llama.cpp) to make the chat answer for real.

```
pip install -r requirements.txt
python full_demo.py        # the whole stack in one run
pytest tests/              # 61 tests
```

---

## The vision → what's built

The original goal: *an open AI that learns and improves itself, powered by
volunteer compute that grows with adoption, free on GitHub, with a guaranteed
off-switch and enforceable rules.*

| Vision element | How it's realized | Where | Tested |
|---|---|---|---|
| Enforceable rules | Signed constitution R1–R10; 5 immutable | `governance/`, `CONSTITUTION.md` | ✓ |
| Off-switch you control | Local kill-switch (node + self-improvement loop) | `node-client/`, `training/self_improve.py` | ✓ |
| Volunteer compute, consensual | Opt-in, idle-only, capped node state machine | `node-client/gua_node.py` | ✓ |
| Grows with adoption | P2P registry + scheduler; real socket transport | `network/` | ✓ |
| Trustworthy across strangers | Redundant work + majority-vote + reputation | `network/scheduler.py` | ✓ |
| Safe execution | Sandbox: isolation + resource limits + whitelist | `safety/sandbox.py` | ✓ |
| Talk to it | Claude-like chat UI + verified-inference backend | `webui/`, `network/service.py` | ✓ |
| Learns / improves itself | Federated training + robust aggregation | `training/federated.py` | ✓ |
| …but stays under control | Validation gate + human approval + signed registry | `training/`, `self_improve.py` | ✓ |
| Transparent | Hash-chained, tamper-evident audit log | `safety/audit_log.py` | ✓ |
| Free & open, adoptable | AGPL-3.0, full docs, runnable demos | repo root | n/a |

---

## Layers (data flows top to bottom)

```
                ┌─────────────────────────────────────────────┐
  USER  ───────►│  webui/  (chat UI: opt-in, caps, kill-switch)│
                └───────────────┬─────────────────────────────┘
                                ▼
        ┌───────────────────────────────────────────────┐
        │  GuaService  (network/service.py)              │
        │  prompt → POLICY in → network → POLICY out     │
        └───────┬───────────────────────────────┬────────┘
                ▼                               ▼
   ┌────────────────────┐            ┌───────────────────────┐
   │ POLICY ENGINE      │            │ NETWORK                │
   │ safety/policy_*    │            │ registry + scheduler   │
   │ refuses R1–R10     │            │ + real socket transport│
   └─────────┬──────────┘            └───────────┬───────────┘
             │ enforces                          ▼
             │                        ┌───────────────────────┐
             │                        │ SANDBOX (safety/)      │
             ▼                        │ isolate + limit + allow│
   ┌────────────────────┐            └───────────┬───────────┘
   │ GOVERNANCE         │                        ▼
   │ signed ruleset     │            ┌───────────────────────┐
   │ R1–R10 (5 immutable)│           │ TRAINING (training/)   │
   └────────────────────┘            │ federated → gate →     │
                                     │ signed model registry  │
   ┌────────────────────┐            │ + audit log            │
   │ KILL-SWITCH         │◄───────────┤ + self-improve loop    │
   │ local = guaranteed  │  stop()    └───────────────────────┘
   └────────────────────┘
```

---

## Component reference

**`governance/`** — `ruleset.yaml` (the signed R1–R10 constitution),
`sign_ruleset.py` / `verify_ruleset.py` (ed25519). Immutable core: R1 non-harm,
R2 peace, R5 corrigibility, R6 truthfulness, R10 protection of the vulnerable.
No "obey the law" rule by design (Constitution Article 6).

**`safety/`** — `policy_engine.py` (refuses rule-violating tasks/outputs),
`sandbox.py` (process isolation + CPU/mem limits + timeout + task whitelist),
`audit_log.py` (hash-chained, tamper-evident).

**`node-client/`** — `gua_node.py`: consent/opt-in, resource caps, idle-only,
pause-on-battery, and the guaranteed local kill-switch, as a tested state machine.

**`network/`** — `registry.py` (discovery + reputation), `scheduler.py`
(redundant dispatch + majority-vote verification), `transport.py` (real TCP
sockets), `worker.py` / `inference_worker.py`, `service.py` (end-to-end chat),
demos (`demo.py`, `net_demo.py`, `chat_demo.py`).

**`training/`** — `model.py`, `federated.py` (FedAvg + robust median),
`validation_gate.py`, `model_registry.py` (signed, append-only),
`self_improve.py` (bounded loop), `train_demo.py`.

**`webui/`** — `index.html` (chat UI with live contribution panel + kill-switch
+ rules), `backend/server.py` (DIRECT and NETWORK modes).

---

## Honest limits (what is reference vs. production)

These are deliberately scoped, not hidden:

- **No guaranteed *global* kill-switch.** Local control is guaranteed; a truly
  decentralized network can't be switched off by one party (the "No-Off
  Problem"). Early phases stay partly centralized on purpose.
- **Single bootstrap coordinator**, not full libp2p/DHT P2P with NAT traversal yet.
- **Reference model** (logistic regression) stands in for real large models
  (Hivemind/Petals) — the federated *protocol* is what's proven, not scale.
- **Sandbox** gives process isolation + resource caps + a whitelist; full
  filesystem/network isolation needs containers/WASM.
- **Rules are policy + enforced safeguards**, not mathematical guarantees on a
  self-modifying system. The validation gate + human-in-the-loop + caps reduce
  risk; they don't eliminate it. This is the state of the art for everyone.
- **Generative verification** uses deterministic decoding (temp 0) so honest
  nodes agree; otherwise reputation + spot-checks, not exact-match voting.

## What's next (scaling & hardening, no new concepts)

Real models via Hivemind/Petals · secure aggregation · container/WASM sandbox ·
true libp2p P2P · threshold-signed governance · auto-retraining driving the gate.

See [ROADMAP.md](./ROADMAP.md) and [WHITEPAPER.md](./WHITEPAPER.md).
