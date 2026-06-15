# node-client/  *(Phase 1 — placeholder)*

The application a user installs to contribute compute. This directory is a placeholder until Phase 1.

## What will live here

- **Opt-in onboarding** — a clear consent screen (no hidden behavior).
- **Idle detection** — compute only when the PC is idle; suspend instantly on user activity.
- **Resource caps** — `max_cpu_percent` (default ≈25%), `max_gpu_percent`, `max_ram_mb`, `bandwidth_cap`, `temp_limit_celsius`, allowed hours, "never on battery".
- **Local kill-switch** — tray button + dashboard control that stops the node instantly. *This guarantee must never be weakened.*
- **Dashboard** — real-time view of usage, current task, total contribution.
- **Sandbox client** — runs network tasks isolated, with no access to personal files.

## Hard requirements (non-negotiable)

1. Never run without explicit user opt-in.
2. Never exceed declared resource caps.
3. Always honor the local stop button immediately.
4. Never access the user's personal files.

See [WHITEPAPER §4.2](../WHITEPAPER.md#42-the-node-client-what-the-user-installs) and [SECURITY.md](../SECURITY.md).
