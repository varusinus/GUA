# Node-client specification (Phase 1)

The node-client is the application a user installs to (a) talk to GUA and (b) optionally donate spare compute. This spec defines its behavior so the implementation in [`../node-client/`](../node-client/README.md) is unambiguous. It is the bridge from the current interface shell to a real network node.

The guiding principle: **the client's guarantees are the user's rights.** Opt-in, caps, and the kill-switch are not features to be weakened for performance — they are contractual.

---

## 1. Responsibilities

1. Run a local **agent process** that connects to the GUA P2P network.
2. Enforce the user's **consent and resource policy** (opt-in, caps, schedule).
3. Execute network **work units** inside a **sandbox**.
4. Expose **telemetry** and a **control API** that the [web UI](../webui/README.md) consumes.
5. Guarantee an **instant local kill-switch**.

---

## 2. Consent model (opt-in)

- The client **never** contributes compute until the user explicitly enables it. Default state after install: **chat-only, not contributing.**
- The opt-in screen must state, in plain language: what is used (CPU/GPU share), when (idle-only by default), the cap, and that it can be stopped anytime.
- Consent is **revocable instantly** and persisted locally.
- Contributing compute and using the chat are **independent**: a user may chat without contributing, contribute without chatting, both, or neither.

> Violating the opt-in requirement turns GUA into cryptojacking/malware. This is a release-blocking, security-critical invariant ([SECURITY.md](../SECURITY.md)).

---

## 3. Resource policy

Configurable, with conservative defaults. Stored in `config.toml` (schema in §7).

| Setting | Default | Meaning |
|---|---|---|
| `max_cpu_percent` | 25 | Hard ceiling on CPU use by the node. |
| `max_gpu_percent` | 50 | Ceiling on GPU use (0 disables GPU work). |
| `max_ram_mb` | 2048 | Memory ceiling. |
| `bandwidth_cap_kbps` | 5000 | Upload/download cap. |
| `temp_limit_celsius` | 80 | Pause if device temperature exceeds this. |
| `idle_only` | true | Compute only when the machine is idle. |
| `idle_threshold_seconds` | 120 | Idle = no keyboard/mouse for this long. |
| `pause_on_battery` | true | Laptops: don't compute on battery. |
| `allowed_hours` | "00:00-24:00" | Time window when contribution is allowed. |

### Throttling mechanism
Follow the BOINC model: implement CPU caps by **suspending and resuming** the worker at ~1s granularity to hit the target duty cycle, rather than busy-spinning. This keeps fans quiet and the machine responsive — the top reason volunteers quit is fan noise.

### Idle detection
- Desktop: OS idle-time APIs (no input for `idle_threshold_seconds`).
- On user activity, **suspend within 1 second**.

---

## 4. Sandbox

- Every network-supplied work unit runs **isolated**: container, microVM, or WASM runtime.
- **No access** to the user's personal files, environment secrets, or network beyond what the task declares.
- Least privilege; explicit, auditable capabilities only.
- Resource ceilings (§3) enforced at the sandbox boundary, not just requested.

---

## 5. Kill-switch

Two scopes, matching [Constitution Article 5](../CONSTITUTION.md#article-5--the-off-switch-what-is-promised):

- **Local (guaranteed):** a `stop()` command halts all GUA compute and disconnects, **immediately and unconditionally**. Exposed via tray, UI, CLI (`gua stop`), and an OS service stop. Must succeed even if the network is unreachable.
- **Network halt (best-effort):** the node honors a valid **signed halt message** and a **dead-man's-switch** (stops itself if it hasn't received a signed heartbeat within the interval). It cannot force other people's nodes or forks to stop — that limit is by design.

The kill-switch path must be simple and dependency-light so it cannot be broken by a failure elsewhere in the client.

---

## 6. Control & telemetry API (consumed by the UI)

Local-only HTTP API on `127.0.0.1` (default port `8754`), so the web UI and CLI can drive the node.

```
GET  /status        -> { contributing, state, cpu_percent, units_done, rules_version, killed }
POST /contribute    -> { enabled: bool }            # opt-in toggle
POST /config        -> { ...resource policy... }    # update caps
POST /stop          -> {}                            # LOCAL KILL-SWITCH (guaranteed)
POST /resume        -> {}                            # clear killed state
POST /chat          -> { message } -> streamed tokens (see chat backend)
GET  /rules         -> signed ruleset (verified)    # for display
```

`state` ∈ `offline | online_idle | computing | paused_battery | paused_thermal | killed`.

The web UI's contribution panel and STOP button map directly onto `/status`, `/contribute`, `/config`, and `/stop`. In the Phase-0 shell these are simulated in JS; Phase 1 points them at this API.

---

## 7. Config schema (`config.toml`)

```toml
[identity]
node_id = "auto-generated-uuid"

[consent]
contribute = false            # opt-in; default off

[resources]
max_cpu_percent = 25
max_gpu_percent = 50
max_ram_mb = 2048
bandwidth_cap_kbps = 5000
temp_limit_celsius = 80
idle_only = true
idle_threshold_seconds = 120
pause_on_battery = true
allowed_hours = "00:00-24:00"

[network]
bootstrap_peers = ["/dns4/bootstrap.gua.example/tcp/4001/p2p/PEERID"]
control_api_port = 8754

[governance]
ruleset_path = "../governance/ruleset.yaml"
require_valid_signature = true   # reject unsigned/invalid rulesets
```

---

## 8. Startup sequence

1. Load `config.toml`.
2. Load and **verify** the signed ruleset; if invalid and `require_valid_signature`, keep the last valid one (or refuse to contribute).
3. Start the local control API.
4. Start the chat client (always available).
5. If `consent.contribute` is true **and** policy conditions are met, join the work pool; otherwise stay chat-only.
6. Begin emitting telemetry; honor `stop()` at all times.

---

## 9. Non-negotiable invariants (release-blocking if violated)

1. No compute without explicit opt-in.
2. Never exceed declared resource ceilings.
3. `stop()` always works, immediately, even offline.
4. No access to the user's personal files.
5. Reject rulesets that fail signature verification (when required).

---

## 10. Implementation notes

- A reference prototype of the consent/caps/kill-switch logic lives in [`../node-client/gua_node.py`](../node-client/) (no real P2P or sandbox yet — it models the policy state machine and is unit-tested).
- Suggested stack: Python or Rust core; libp2p for P2P; container/WASM for sandbox; a small embedded HTTP server for the control API.
- The P2P protocol, scheduler, and sandbox each get their own spec under `docs/` as Phase 1 proceeds.
