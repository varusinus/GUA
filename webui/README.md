# webui/

A Claude-like chat interface for talking to GUA, with the network's guarantees built directly into the UI.

## Run it

Open `index.html` in any browser. No build step, no dependencies — a single self-contained file.

## What's in it

- **Chat** — message thread + composer, like a normal AI chat app.
- **Your contribution panel** — an explicit **opt-in** toggle, a live CPU-usage meter, a configurable **max CPU cap** (default 25%), "pause on battery", and a work-units counter. Compute is *never* used unless the user opts in.
- **Local kill-switch** — a prominent red **STOP THIS NODE** button that halts the node instantly. This embodies the guaranteed local off-switch from the [Constitution](../CONSTITUTION.md#article-5--the-off-switch-what-is-promised).
- **Active rules** — R1/R2 shown as immutable, R3/R4 listed, so the user always sees what governs the agent.

## Status: Phase-0 interface shell

Replies are **simulated locally** — no AI model is connected yet, and the contribution meter is a visual simulation. This is intentional for Phase 0: it lets us design and test the *user-facing contract* (opt-in, caps, kill-switch, visible rules) before the network exists.

## Connecting a backend (Phase 1+)

The UI is written so the simulation can be swapped for the real network:

- **Chat:** replace `generateReply(text)` in `index.html` with a call to the GUA inference endpoint (an open-weights model served over the volunteer network, Petals-style). Stream tokens into the message element instead of returning a string.
- **Contribution:** replace the `runLoop()` simulation with real telemetry from the local node-client ([`../node-client/`](../node-client/README.md)) — actual CPU usage, current work unit, units completed.
- **Kill-switch:** wire `killSwitch()` to the node-client's real stop command (process halt), not just the UI state.
- **Rules:** load the signed [`../governance/ruleset.yaml`](../governance/ruleset.yaml) and render rules dynamically, verifying the signature before display.

## Design intent

The interface is not a skin on top of the rules — it *is* one of the places the rules are made real and visible: consent before compute, caps the user sets, a stop button that always works, and the governing rules shown in plain sight.
