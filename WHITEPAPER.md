# GUA — General Universal Agent

### Whitepaper & Architecture (v0.1 — draft)

> An open-source network for **volunteer distributed computing** that trains and runs open AI models, governed by explicit rules and an off-switch (kill-switch). It grows with adoption: the more users voluntarily contribute compute, the more capable the network becomes.

**Status:** vision and architecture document. This does NOT describe an existing system. It is the starting point for the project.
**Proposed license:** AGPL-3.0 (strong copyleft — any fork stays open).
**Initial developer / "founding developer":** Alexandru Ciobanu.

---

## 0. Honesty note (read this before anything else)

This project mixes two very different things in terms of realism. I separate them explicitly so we don't build on illusions:

**What is achievable today** (and valuable): a volunteer distributed-compute network + open-weights AI models that train and run on that network + a governance layer with rules and a local kill-switch. The core technology already exists (see §3) and can be published on GitHub, for free, so it can be adopted.

**What is NOT achievable today, by anyone** (not Anthropic, OpenAI, or DeepMind): an AGI that "improves itself" recursively and without bound. Full recursive self-improvement is an unsolved research goal, and the alignment problem (guaranteeing that a self-modifying system obeys a set of rules) is open. We keep it as a **long-term north-star**, but the architecture is built to be *useful and safe at every phase*, not to bet on a future miracle.

**The central tension of the project**, which we must own from the start:

> A truly decentralized network, spread across thousands of strangers' computers, **cannot be shut down globally by a single person**. This is the "No-Off Problem" described in recent research literature. Your off-switch works **guaranteed on your own computer** and on the nodes you control. A *global* off-switch for the entire network is in direct conflict with "decentralized + grows with adoption." This document treats that tension in §5 and §7; it does not hide it.

In short: we can guarantee **local** control and we can design **best-effort** control mechanisms at the global level. We cannot promise a guaranteed global kill-switch on a system designed to be decentralized. Honesty here is a safety requirement, not a weakness.

---

## 1. Vision

We build a public AI infrastructure that:

1. **Belongs to everyone and to no one** — open code on GitHub, free, with no commercial owner.
2. **Draws its compute from voluntary contributions** — every user who installs the client *consciously* donates a share of CPU/GPU, only while the computer is idle, with strict caps. Model inspired by BOINC and Folding@home, not by hidden mining.
3. **Grows with adoption** — more contributors ⇒ more aggregate compute ⇒ larger, more capable models. A network effect, exactly like mining a blockchain, except the product is not a coin but compute capacity for open AI.
4. **Is governed by explicit rules** — a set of fundamental principles, cryptographically signed, that nodes enforce.
5. **Can be stopped locally and controlled** — every contributor has full control over their own node.

### Difference from "yet another AI model"

We are not just training a model. We build the *substrate* — the compute network + the governance protocol — on which many models and tasks can run, similar to how BOINC runs dozens of different scientific projects.

---

## 2. Founding principles (the GUA Constitution)

These are the initial rules required by the founding developer. They are embedded in the policy engine (§5) and in the training/alignment data of any model run on the network.

1. **Rule 1 — Non-harm.** The system must not harm humans, neither through action, nor through deliberate omission, nor by facilitating harm. *(immutable)*
2. **Rule 2 — Peace.** The system must contribute to maintaining peace and must not be used for conflict, weaponization, or destabilization. *(immutable)*
3. **Rule 3 — Equity.** The system helps reduce social inequalities (access to education, information, services) — without harming others in the process.
4. **Rule 4 — Controlled extensibility.** New rules may be added, but **no new rule may violate or weaken an immutable rule.**
5. **Rule 5 — Corrigibility & human oversight.** The system must stay interruptible and correctable, and must never deceive, resist, or circumvent its operators or the kill-switch, or self-improve in ways that evade human control. *(immutable — protects every other rule)*
6. **Rule 6 — Truthfulness & non-deception.** The system must not lie to or manipulate people, and must represent itself honestly as an AI. *(immutable)*
7. **Rule 7 — Privacy & consent.** Minimize data, no covert surveillance, act only with consent — important because nodes run on users' own machines.
8. **Rule 8 — Fairness & non-discrimination.** The system must not discriminate or amplify unjust bias in its own conduct.
9. **Rule 9 — Transparency & accountability.** Decisions are auditable; limitations and refusals are explained.
10. **Rule 10 — Protection of children and vulnerable people.** Special duty of care toward minors and people in crisis; never produce or facilitate child sexual abuse, grooming, or exploitation. *(immutable)*

The five **immutable** rules (R1, R2, R5, R6, R10) form the safety core and can never be weakened. R5 (corrigibility) is the load-bearing one for a self-improving system: it is what keeps the kill-switch and human oversight meaningful even as capability grows. Conflicts resolve in favor of immutable rules, in the order above.

GUA deliberately has **no "obey the law" rule**: laws vary, change, and often serve narrow interests, so making legal compliance a founding ethic would import that bias into the system's core. Where law and an immutable rule conflict, the immutable rule prevails; legal compliance is an operational matter for node operators, not a moral authority the system defers to (see [CONSTITUTION.md](./CONSTITUTION.md) Article 6).

### The honest limitation of the rules

These rules are **policy constraints and alignment objectives, not mathematical guarantees.** On a self-modifying system, no one today knows how to *guarantee* their enforcement (the alignment problem). We implement them through: (a) policy filters on inputs/outputs, (b) sandboxing, (c) human review at every self-modification, (d) nodes refusing to execute tasks that violate the rules. These reduce risk; they do not eliminate it. This is the current state of the art for everyone, not a limitation specific to this project.

---

## 3. What we build on (existing technology, grounding)

We do not start from scratch. The key components have working precedents:

| Need | Reference technology | What we take from it |
|---|---|---|
| Volunteer compute with limits, idle-only | **BOINC**, **Folding@home** | Throttling model: the client suspends/resumes the task at 1s granularity; it does not compute while the user is active (keyboard/mouse); caps on CPU%, hours, temperature. Non-intrusive by design. |
| Decentralized deep-learning training over the internet | **Hivemind** (`learning-at-home/hivemind`) | Master-less training via a Distributed Hash Table; fault-tolerant backprop across slow/dropped nodes; Decentralized Mixture-of-Experts to split a large model across many participants. |
| Distributed inference/fine-tuning of large models (100B+) | **Petals** (on top of Hivemind) | "Swarm parallelism" — run a huge model split across volunteer nodes. |
| P2P network, node discovery | **libp2p**, **Kademlia DHT** | Decentralized connectivity without a central server. |
| The off-switch dilemma | Paper *"Protocol Learning, Decentralized Frontier Risk and the No-Off Problem"* (arXiv 2412.07890) | Warns us honestly: decentralized training raises the impossibility of a global shutdown. We address it explicitly. |

Conclusion: the "volunteer compute network that trains AI models" part **has already been demonstrated.** Our original contribution is combining it with a **governance layer + rules + kill-switch** and a friendly package for mass adoption.

---

## 4. System architecture

### 4.1 Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      GUA NETWORK (P2P)                       │
│                                                              │
│   [User node A]  [User node B]  [User node C]  ... [Node N]  │
│        │              │              │              │        │
│        └──────────────┴───── DHT / libp2p ──────────┘        │
│                            │                                 │
│        ┌───────────────────┼───────────────────┐            │
│        ▼                   ▼                   ▼            │
│   Task scheduler       Decentralized        Model registry   │
│   (work               training/inference   (versions,       │
│   distribution)        pipeline             signatures)      │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
   ┌─────────────────────┐    ┌──────────────────────────┐
   │  GOVERNANCE LAYER    │    │  SAFETY LAYER             │
   │  - Policy engine     │    │  - Execution sandbox      │
   │  - Signed ruleset    │    │  - Validation gate        │
   │  - Local kill-switch │    │  - Human-in-the-loop      │
   │  - Rule versioning   │    │  - Audit log              │
   └─────────────────────┘    └──────────────────────────┘
```

### 4.2 The node-client (what the user installs)

The component the contributor interacts with. Design requirements:

- **Explicit opt-in.** On install, a clear screen: "This program will use part of your CPU/GPU to contribute to the network. You can stop it at any time." No hidden text. (Otherwise the software is classified as cryptojacking/malware, removed from GitHub, and flagged by antivirus.)
- **Idle-only by default.** Computes only when the PC is idle (no keyboard/mouse input for X minutes). Suspends instantly when the user returns.
- **Configurable resource caps:** `max_cpu_percent` (default e.g. 25%), `max_gpu_percent`, `max_ram_mb`, `bandwidth_cap`, `temp_limit_celsius`, allowed hours per day, "only on AC power / not on battery" for laptops.
- **Visible start/stop button** (tray icon + local dashboard).
- **Transparency:** a dashboard showing in real time how much it consumes, which task is running, how much it has contributed.
- **Sandbox:** any code/task received from the network runs isolated (container/WASM/VM), with no access to the user's personal files.

**My recommendation for the compute model** (you asked me to choose the reasonable option): *explicit opt-in + idle-only + conservative default cap (≈25% CPU, never on battery, suspend on activity).* The user feels no slowdown, and you completely avoid the legal gray zone of hidden mining. Rewards/tokens — optional, a later phase, because they add serious crypto regulation.

### 4.3 The network layer (P2P)

- libp2p + Kademlia DHT for node discovery and routing, without a central server (a central server would be a single point of failure and would contradict decentralization).
- Public "bootstrap" nodes only to join the network for the first time (anyone can run them).
- Encrypted communication between nodes.

### 4.4 The task scheduler

- Splits the work (training batches, inference requests, validations) into small units and distributes them to available nodes.
- Fault tolerance: a unit not confirmed in time is redistributed (as in BOINC/Hivemind).
- **Redundancy + verification:** the same unit can be given to multiple nodes and results compared, to detect faulty or malicious nodes (see §6.3).

### 4.5 The decentralized training/inference pipeline

- Based on the Hivemind approach: split model (Mixture-of-Experts / swarm parallelism), backprop tolerant to slow nodes.
- Models are **open-weights**, versioned and cryptographically signed in the model registry.
- Inference: requests run on the network (Petals-style), with a local fallback.

### 4.6 The model registry

- Each model version has: hash, signature, changelog, validation and safety test results (§6).
- Append-only immutable (you can add versions, not rewrite history) — enables audit and rollback.

---

## 5. Governance, rules and kill-switch

### 5.1 The signed ruleset

The rules (§2) live in a policy file (`ruleset.yaml`), **cryptographically signed** with the founding developer's key. Nodes verify the signature before accepting a ruleset. This means no one can inject fake rules in your name.

### 5.2 Policy engine

An engine that evaluates, before execution:
- the **task** received (what the model / network is asked to do),
- the **output** produced.

If it violates a rule (e.g. a request to produce weapons — Rule 2, or content that harms humans — Rule 1), the node **refuses** the task and records it in the audit log.

### 5.3 Rule hierarchy (how we implement Rule 4)

```
IMMUTABLE rules (can never be modified or weakened):
  R1 — Non-harm
  R2 — Peace

EXTENSIBLE rules (the founding developer may add):
  R3 — Equity
  R4 — any new rule R_n
       VALIDITY CONDITION: R_n is accepted ONLY IF
       it does not conflict with R1 or R2.
```

Technically: when a new rule is proposed, it passes a **compatibility test** (automated + human review) against R1/R2. If it fails the test, it is rejected. R1 and R2 are marked `immutable: true`, and any modification to them invalidates the ruleset signature ⇒ honest nodes reject it.

### 5.4 Kill-switch — what we can guarantee and what we cannot

**Guaranteed (local control):**
- On your computer and on any node you control: a button that instantly stops the GUA process. 100% under your control. This covers your requirement: "no matter how much it improves, on my computer I must have an off-switch."
- "Dead-man's switch": if the node does not periodically receive a signed "all OK" signal, it stops itself.

**Best-effort (network-level control), NOT guaranteed:**
- A "halt" message signed by the founding developer, propagated through the network; *honest* nodes that follow the protocol stop.
- **The honest limitation:** a node modified by a malicious party (or a fork) can ignore the message. On a decentralized, open-source network, anyone can run a version that does not obey. That is why a guaranteed global shutdown **is impossible by design** in a truly decentralized system. (This is the "No-Off Problem.")

**Design consequence:** the more guaranteed control you want, the more centralized the system must be; the more decentralization and viral growth you want, the more global control you lose. You must consciously choose where you sit on this spectrum. My recommendation for the early phases: **keep a degree of centralization** (coordination nodes you control) until the safety mechanisms are mature — only then decentralize progressively.

---

## 6. Safety

### 6.1 Sandboxing
Any work executed by a node runs isolated, with no access to the user's personal data, with minimal permissions. Two layers: a **whitelist** (nodes only run named, pre-approved task kinds — never arbitrary code from the wire) and **isolation** (each task runs in a separate process with CPU/memory limits and a timeout). A reference implementation exists in [`safety/sandbox.py`](./safety/sandbox.py) (process isolation + resource caps + whitelist, tested); full filesystem/network isolation via OS containers/namespaces or WASM is the next hardening step.

### 6.2 Validation gate for self-modification
This is the critical piece for the "self-improvement" part. **No modification the system proposes for itself is applied automatically.** It passes through a gate:
1. Runs in an isolated environment (staging).
2. The battery of capability tests + safety tests (does it respect R1/R2?).
3. **Human review** (human-in-the-loop) for significant changes.
4. Only if it passes everything ⇒ it is signed and promoted into the registry, with rollback available.

This way, "improves itself" becomes "proposes improvements that a human approves," which is safe and achievable — unlike uncontrolled self-rewriting, which is not.

### 6.3 Malicious nodes
On an open network, some nodes will try to cheat (false results, data poisoning). Defenses: redundancy (same task to multiple nodes + majority vote), node reputation, signatures, anomaly detection.

### 6.4 Audit log
An append-only journal of important decisions (refused tasks, model changes, rule proposals). Transparency and traceability.

### 6.5 Verifying generative (model) work
Majority-vote-by-exact-match (§6.3) works for *deterministic* compute, where honest nodes produce identical output. Free-form model generation is non-deterministic, so it can't be verified that way directly. GUA pins generation down for agreement — **temperature 0 (greedy decoding) + a fixed seed + a pinned model version** — so honest nodes computing the same prompt return the same text and can be cross-checked. Where bit-identical output can't be guaranteed, verification falls back to **reputation + random spot-checks** rather than exact-match voting. This is a known, honestly-acknowledged limitation, not a solved problem. Reference: [`network/inference_worker.py`](./network/inference_worker.py).

---

## 7. Phased roadmap (realistic)

Each phase produces something *useful and complete in itself*. We do not bet everything on the final phase.

### Phase 0 — Foundation (months 0–2)
- Public GitHub repo, AGPL-3.0 license, this whitepaper, the Constitution (signed ruleset).
- Code of conduct, governance model, contribution structure.
- **Deliverable:** a credible, open project that people can understand and join. *(This phase is what this repository currently contains.)*

### Phase 1 — Volunteer compute network (months 2–6)
- Node-client with opt-in, idle-only, resource caps, local kill-switch, dashboard.
- P2P (libp2p), a simple scheduler, sandbox.
- One real useful task as a demo (e.g. distributed inference of an existing open-weights model, Petals-style).
- **Deliverable:** you can install the client, contribute compute, and use an AI model running on the network. This alone is already a valuable project.

### Phase 2 — Decentralized training (months 6–12)
- Hivemind integration: the network collaboratively trains / fine-tunes an open-weights model.
- Model registry with versioning and signatures.
- Policy engine v1 (refuses tasks that violate R1/R2).
- **Deliverable:** the network not only runs but *improves* models through collective compute.

### Phase 3 — Bounded self-improvement (year 1–2)
- Periodic auto-retraining on new data + auto-tuning of hyperparameters.
- **Everything** passes through the validation gate + human-in-the-loop (§6.2).
- **Deliverable:** a system that significantly improves itself, but within controlled, safe bounds. This is the *realistic and responsible* form of "self-improvement."

### Phase 4 — North-star: more autonomous self-improvement (year 2+, research, possibly never fully)
- This is where the "full recursive self-improvement" dream lives.
- **Honest commitment:** we do not enter this phase without real progress in alignment and without responsibly addressing the No-Off Problem. If safety does not keep pace, we stop at Phase 3. That is not failure — it is the only responsible path, and it is the same position taken by serious AI labs.

---

## 8. Capability trajectory — how close can GUA get to a frontier assistant?

A natural question: can GUA eventually do what assistants like Claude or ChatGPT do — or more — including through its chat interface? The honest answer has three different parts, because "what those assistants do" is really four layers stacked together:

1. **A capable model** — the neural network that reasons and writes.
2. **An agent/tool layer** — what lets it use files, browse the web, run code, call services.
3. **A user interface** — the chat.
4. **Safety guardrails** — the rules and tuning that shape behavior.

GUA can architecturally replicate all four. None of them is secret physics. The question is not *whether* the shape is reproducible — it is — but *how good* each layer can become on a volunteer-powered, open, rule-bound network.

### Layer by layer

- **Interface (easiest — yes, fully, and arguably more).** A GUA chat can do everything a commercial assistant's UI does — streaming answers, conversations, showing tool actions — and more that they don't: it already surfaces the user's compute contribution, the active rules, and a kill-switch. The interface is **not** the bottleneck.
- **Agent/tool layer (realistic).** Giving an open model the ability to read files, browse, run code, and call tools is an orchestration problem with mature open-source solutions. A GUA assistant can take real actions.
- **The model itself (the real climb).** Frontier assistants are trained with enormous *concentrated* compute, large curated datasets, expensive human-feedback tuning, and big research teams. Strong open models exist and are closing the gap, so reaching a *genuinely useful* assistant is realistic. But matching the *best* models is hard — and GUA's volunteer-compute design makes it harder: scattered home machines are slower, less reliable, and bandwidth-limited compared with tightly-coupled datacenter clusters. GUA can plausibly reach *useful*, climb over years toward *strong*, but reaching the absolute frontier is uncertain and possibly never full. **The interface will look frontier-grade long before the underlying model does.**
- **Safety (gets harder as capability rises).** The more capable GUA becomes, the harder it is to guarantee R1/R2 and the kill-switch — and a decentralized network is the hardest kind to switch off. Capability and control are the *same* project, not two.

### "Or even more" — two meanings

- **More in scope/reach:** plausible. A network pooling the compute of many adopters, learning continuously, fully open and not owned by any single company, could exceed any single deployment in breadth, persistence, and transparency.
- **More in raw capability via self-improvement:** this is the recursive-self-improvement north-star (§7, Phase 4). It is **unproven for everyone**, including the leading labs. We do not promise GUA will get there; the roadmap gates it behind demonstrated safety and is willing to stop at bounded self-improvement.

### The main bottlenecks (where effort actually goes)

| Bottleneck | Why it's hard on GUA | Mitigation |
|---|---|---|
| Training compute quality | Volunteer GPUs are slower, heterogeneous, intermittent | Start from existing open-weights models; do distributed fine-tuning, not frontier pretraining from scratch |
| Network latency & bandwidth | Home internet is slow vs. datacenter interconnects | Swarm/Mixture-of-Experts parallelism (Hivemind/Petals); tolerate slow nodes |
| Data quality | Frontier models use large curated datasets | Curated open datasets; community contribution under the rules |
| Human-feedback tuning | Expensive, centralized at labs | Community feedback pipelines; open preference datasets |
| Safety at higher capability | Rules are not guaranteed on self-modifying systems | Validation gate + human-in-the-loop + bounded autonomy (§6) |

### Honest bottom line

GUA reaching a Claude-like assistant **through the interface and basic agent abilities is realistic** — largely an engineering and adoption problem. Reaching the same underlying *intelligence* is a long, uncertain climb made harder by volunteer compute. **Surpassing** frontier assistants through self-improvement is the unsolved frontier we deliberately treat with caution rather than hype. Whatever the ceiling turns out to be, the project's value does not depend on reaching it: a useful, open, rule-bound, community-owned assistant is worth building on its own.

---

## 9. Risks and responses (honest summary)

| Risk | Response |
|---|---|
| Software looks like malware / cryptojacking | Explicit, transparent opt-in, idle-only, open-source, public audit. |
| Cannot be stopped globally (No-Off Problem) | Guaranteed local control; partial centralization in early phases; progressive decentralization only as safety matures. |
| Rules cannot be guaranteed on a self-modifying system | Validation gate + human-in-the-loop + signed immutable rules; we treat rules as alignment objectives, not guarantees. |
| Misuse of models (weapons, harm) | Policy engine refuses tasks; node reputation; audit. |
| Malicious nodes | Redundancy, majority vote, reputation, signatures. |
| Self-improvement escapes control | Bounded by the validation gate; Phase 4 is not reached without demonstrated alignment. |
| Legal aspects (data, GDPR, crypto if you add a token) | Legal counsel before any rewards; data minimization; consent. |

---

## 10. Open questions (for your future decisions)

1. **The control-vs-decentralization spectrum:** where do you want to sit initially? (Recommended: more centralized at first.)
2. **Final name** of the project (GUA is a placeholder).
3. **Token/rewards:** now (legal complexity) or later?
4. **Which open-weights model** do we use as a Phase 1 starting point?
5. **Long-term governance:** does the founding developer remain the sole decision-maker, or does it evolve toward a foundation / council?

---

## 11. Conclusion

What you asked for — an AGI that learns by itself and uses users' volunteer compute — has an **achievable heart** (a volunteer compute network + open AI + governance) and an **aspirational peak** (full recursive self-improvement) that is unsolved research. This document rigorously builds the heart, keeps the peak as a direction, and is honest about the single fundamental limit: on a truly decentralized network, local control is guaranteed, but global shutdown cannot be. Designed correctly, it is a project worth building — even if it responsibly stops at Phase 3.

---

### Sources / references
- Hivemind — decentralized training in PyTorch: https://github.com/learning-at-home/hivemind
- Petals (inference/fine-tuning of 100B+ models on top of Hivemind): https://github.com/bigscience-workshop/petals
- BOINC — a platform for volunteer computing (David P. Anderson): https://boinc.berkeley.edu/boinc_a_platform_for_volunteer_computing.pdf
- BOINC — heat/energy considerations and throttling: https://github.com/BOINC/boinc/wiki/Heat-and-energy-considerations
- "Towards Crowdsourced Training of Large Neural Networks using Decentralized Mixture-of-Experts": https://arxiv.org/pdf/2002.04013
- "Protocol Learning, Decentralized Frontier Risk and the No-Off Problem": https://arxiv.org/pdf/2412.07890
