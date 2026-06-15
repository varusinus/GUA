<div align="center">

# GUA — General Universal Agent

**An open, volunteer-powered compute network for open AI — governed by explicit rules and a kill-switch.**

*The more people contribute compute, the more capable it becomes. Like mining a blockchain — except the product is open AI capacity, not a coin.*

[Whitepaper](./WHITEPAPER.md) · [Architecture & Status](./ARCHITECTURE.md) · [Constitution](./CONSTITUTION.md) · [Governance](./GOVERNANCE.md) · [Roadmap](./ROADMAP.md) · [Security](./SECURITY.md) · [Contributing](./CONTRIBUTING.md)

License: **AGPL-3.0** · Status: **Phase 0 — Foundation** · Language: **English**

</div>

---

## What is this?

GUA is a project to build a **public, open-source AI infrastructure** that draws its computing power from people who *voluntarily and consciously* donate a slice of their CPU/GPU — only while their computer is idle, with strict resource caps. The network runs and trains **open-weights AI models**, and is governed by a small set of explicit, signed rules plus a guaranteed local off-switch.

It is inspired by proven projects — [BOINC](https://boinc.berkeley.edu/) and [Folding@home](https://foldingathome.org/) for volunteer compute, [Hivemind](https://github.com/learning-at-home/hivemind) and [Petals](https://github.com/bigscience-workshop/petals) for decentralized training and inference — combined with a governance and safety layer that is the project's original contribution.

## What this is **not** (read this)

- **Not hidden mining.** Compute is used only after **explicit opt-in**, transparently, idle-only. Anything else would be cryptojacking — we reject it by design.
- **Not a magic self-improving AGI (yet).** Full recursive self-improvement is an unsolved research problem for *everyone*. We build the achievable parts first and keep that goal as a long-term north-star, behind strict safety gates. See [WHITEPAPER §0](./WHITEPAPER.md#0-honesty-note-read-this-before-anything-else).
- **Not globally un-killable on your machine.** You always control your own node. But note the honest limit: a *truly* decentralized network cannot be shut down globally by one person (the "No-Off Problem"). We address this openly in the [Governance](./GOVERNANCE.md) and [Whitepaper §5.4](./WHITEPAPER.md#54-kill-switch--what-we-can-guarantee-and-what-we-cannot).

## The rules (Constitution)

The network is governed by founding principles. Five are **immutable** (the safety core):

1. **Non-harm** — the system must not harm humans. *(immutable)*
2. **Peace** — the system must contribute to peace and must not be weaponized. *(immutable)*
3. **Equity** — the system helps reduce social inequalities, without harming others.
4. **Controlled extensibility** — new rules may be added, but **none may weaken an immutable rule.**
5. **Corrigibility & human oversight** — stay interruptible; never evade operators or the kill-switch. *(immutable)*
6. **Truthfulness & non-deception** — don't lie to or manipulate people; be honest about being an AI. *(immutable)*
7. **Privacy & consent** — minimize data, no covert surveillance, consent first.
8. **Fairness & non-discrimination** — no discrimination or bias amplification in the system's conduct.
9. **Transparency & accountability** — auditable decisions; explained refusals.
10. **Protection of children & vulnerable people** — special duty of care; never facilitate child exploitation. *(immutable)*

> GUA has **no "obey the law" rule** by design — laws vary and often serve narrow interests; where law conflicts with an immutable rule, the rule prevails. See [CONSTITUTION.md](./CONSTITUTION.md) Article 6.

Full text and amendment process: [CONSTITUTION.md](./CONSTITUTION.md) · machine-readable: [`governance/ruleset.yaml`](./governance/ruleset.yaml).

## How it works (high level)

```
You install the node-client  ──►  it joins a P2P network (libp2p/DHT)
        │                                   │
        │ idle-only, capped, opt-in         ▼
        ▼                          a scheduler hands it small work units
  a tray button + dashboard                 │
  to start/stop & see usage                 ▼
        │                       training / inference on open-weights models
        ▼                                   │
  100% local kill-switch  ◄──  governed by a signed ruleset + safety sandbox
```

Architecture details: [WHITEPAPER §4](./WHITEPAPER.md#4-system-architecture).

## Quickstart — run it now

Requires **Python 3.10+**. For the chat assistant you also need [Ollama](https://ollama.com) with a model pulled (e.g. `ollama pull qwen2.5:7b`).

```bash
git clone <your-repo-url> gua && cd gua
pip install -r requirements.txt
python governance/sign_ruleset.py --generate-key   # your signing key + signs the ruleset
```

**Talk to GUA (real model + tools + rules).** On Windows, double-click **`start_gua.bat`**. It signs/verifies the ruleset, picks the best local model, and opens the chat UI. GUA answers from a real model, **decides on its own when to search/read the web** (native tool-calling), cites sources, enforces the signed rules, and has a working local **kill-switch**. *(Build the smarter 7B brain once with `make_smart_gua.bat`.)*

**See the network keep the model alive when a node dies.** Double-click **`demo_network.bat`** — it starts two real nodes over TCP: node A seeds the model, node B joins and pulls it. Close A's window (its kill-switch) and B keeps serving the model. (`network/replication_demo.py` shows the same property in one process.)

**Join across machines.** On each computer: `run_node.bat HOST:PORT` to join an existing node (the host must open/forward the TCP port). The model replicates to every node that joins; any node can stop anytime without the network losing it. See [`docs/DISTRIBUTED_DESIGN.md`](./docs/DISTRIBUTED_DESIGN.md).

**Run the tests.** `python -m pytest -q` (CI runs the same on Python 3.10–3.12).

The chat UI is [`webui/index.html`](./webui/index.html); it carries the network's guarantees — an explicit opt-in compute toggle, a CPU cap you set, and a guaranteed local **kill-switch**. See [`webui/README.md`](./webui/README.md). Publishing? See [`RELEASE_CHECKLIST.md`](./RELEASE_CHECKLIST.md).

## Roadmap at a glance

| Phase | What | Status |
|---|---|---|
| **0** | Foundation: whitepaper, constitution, governance, license | ◀ **you are here** |
| 1 | Volunteer compute network + node-client + distributed inference demo | planned |
| 2 | Decentralized training (Hivemind) + model registry + policy engine | planned |
| 3 | Bounded self-improvement behind a validation gate (human-in-the-loop) | planned |
| 4 | North-star: more autonomous self-improvement — only if alignment keeps pace | research |

Full roadmap: [ROADMAP.md](./ROADMAP.md).

## Repository layout

```
.
├── README.md                  ← you are here
├── WHITEPAPER.md              ← vision + architecture + honest limits
├── CONSTITUTION.md            ← the rules, in human-readable form
├── GOVERNANCE.md              ← who decides what, and how rules change
├── ROADMAP.md                 ← phased plan
├── SECURITY.md                ← reporting vulnerabilities + safety model
├── CONTRIBUTING.md            ← how to contribute
├── CODE_OF_CONDUCT.md         ← community standards
├── LICENSE                    ← AGPL-3.0
├── governance/
│   ├── ruleset.yaml           ← machine-readable, signed ruleset
│   ├── sign_ruleset.py        ← ed25519 signing (founding key)
│   └── verify_ruleset.py      ← signature + immutability verification
├── webui/
│   ├── index.html             ← Claude-like chat interface (runnable)
│   └── backend/server.py      ← rule-checked chat bridge to an open model
├── safety/
│   └── policy_engine.py       ← enforces R1/R2 on tasks & outputs
├── node-client/
│   └── gua_node.py            ← consent/caps/kill-switch state machine (tested)
├── network/                   ← (Phase 1) P2P, scheduler, discovery
├── training/                  ← (Phase 2) decentralized training pipeline
├── tests/                     ← pytest suite (governance, policy, node, backend)
└── docs/
    └── node-client-spec.md    ← detailed Phase 1 client spec
```

> `network/` and `training/` (Phase 1–2) currently contain placeholder `README.md` files describing what will live there.

## Run the code (Phase 0 reference implementation)

The governance, safety, and node-client logic already run and are tested:

```bash
pip install -r requirements.txt

# See the WHOLE system run in one narrative (rules → policy → network → sandbox → self-improvement)
python full_demo.py

# Sign the ruleset with a fresh founding key, then verify it
python governance/sign_ruleset.py --generate-key
python governance/verify_ruleset.py          # -> VALID: ok

# Run the test suite (governance, policy, node, backend, scheduler)
pytest tests/

# Watch a swarm simulation (in-process, then over real TCP sockets)
python network/demo.py
python network/net_demo.py

# End-to-end chat over the network (offline stand-in model, or set GUA_MODEL_URL for a real one)
python network/chat_demo.py

# Start the chat bridge, then open webui/index.html
python webui/backend/server.py                 # DIRECT mode (one local model)
GUA_USE_NETWORK=1 python webui/backend/server.py   # NETWORK mode (verified across nodes)
```

What's real today: cryptographically **signed rules (R1–R10)**, a **policy
engine** that refuses violations on tasks and outputs, a **node state machine**
enforcing opt-in + caps + kill-switch, a **node registry + scheduler** with
reputation, redundant execution and majority-vote verification, a **real socket
transport** (nodes connect over TCP), an **execution sandbox** (process
isolation + resource limits + whitelist), and an **end-to-end chat service**
that runs a prompt as verified inference across nodes (`GuaService`) — wired
into the web UI and backend, with **persistent memory** (survives restarts),
**real live stats** (messages served, node inferences, model + version shown in
the UI), and a **real kill-switch** wired from the UI to the backend. Point
`GUA_MODEL_URL` at Ollama/llama.cpp for real answers.

**Windows one-click:** double-click `start_gua.bat` — it installs deps, signs the
ruleset, starts the bridge + web UI, and opens the browser. (Have Ollama running
with `ollama pull llama3.2` first.)

What's still pending: full libp2p P2P (vs. the single bootstrap coordinator),
container/WASM sandbox hardening, and real large-model fine-tuning.

## Status & how to help

This is **Phase 0** — the foundation. There is no runnable network yet; the goal right now is a clear, credible, well-governed project that people can understand and join.

The most useful contributions today: review the [whitepaper](./WHITEPAPER.md) and [constitution](./CONSTITUTION.md), open issues on the design, and help shape the Phase 1 node-client spec. See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

[AGPL-3.0](./LICENSE). Strong copyleft: anyone may use, modify, and redistribute, but derivative works — including network-served ones — must remain open under the same license. This keeps GUA a commons.
