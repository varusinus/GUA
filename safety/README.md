# safety/  *(placeholder — grows across all phases)*

The safety and governance-enforcement components. Placeholder until implementation begins (policy-engine stub in Phase 1, full version in Phase 2+).

## What's implemented

- **`policy_engine.py`** — evaluates tasks and outputs against the signed [`ruleset.yaml`](../governance/ruleset.yaml); refuses violations of R1–R10 (immutable rules first) and logs them. Tested.
- **`sandbox.py`** — runs network work in an isolated child process with CPU/memory limits, a wall-clock timeout, and a **whitelist** so only named, pre-approved task kinds run (never arbitrary code). `SandboxWorker` plugs into the scheduler. Tested (normal, timeout, memory, crash, unknown-task).

## What's still planned
- **Validation gate** — staging + capability tests + safety tests; **no self-modification is auto-applied**; human-in-the-loop for significant changes; rollback always available.
- **Kill-switch logic** — local (guaranteed) stop; network-level signed halt (best-effort); dead-man's-switch heartbeat.
- **Audit log** — append-only record of important decisions.

This directory implements the parts of the [Constitution](../CONSTITUTION.md) and [WHITEPAPER §6](../WHITEPAPER.md#6-safety) that can be enforced in code. Its guarantees (opt-in, caps, sandbox, kill-switch) must never be weakened by any change.
