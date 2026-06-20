# GUA threat model (network layer)

An honest accounting of what the network protects against today, and what it
does **not** yet. Read alongside [SECURITY.md](../SECURITY.md) and
[DISTRIBUTED_DESIGN.md](./DISTRIBUTED_DESIGN.md).

## Assets we protect

- **The model** (weights / blobs) — must stay available and uncorrupted.
- **Improvements** (the signed training updates) — must be authentic and gated.
- **The ruleset** (governance) — must be the genuine, signed rules.
- **The user's machine** — a node owner must stay in control (opt-in, kill-switch).

## Trust model

- The **ruleset** is ed25519-signed; nodes reject an unsigned/invalid ruleset and
  keep the last valid one.
- **Improvements** are ed25519-signed by a model-authority key. A node adopts an
  improvement only if the signature verifies against a **trusted** public key and
  the example hash matches. In this reference all nodes share the repo key; in
  production only the governance authority holds the private key and nodes carry
  its public key (progressive decentralization → threshold signing is Phase 3).
- **Blobs are content-addressed** (SHA-256): any tampered byte changes the hash,
  so corruption/tamper is detected on fetch for free.

## Attack surface and current mitigations

| Threat | Mitigation today | Still open |
|---|---|---|
| Memory-bomb via huge framed message | 64 MiB hard cap in `recv_msg`; oversized length refused before allocation | — |
| Oversized / flooding blobs | 48 MiB blob cap; per-connection request cap (10k) | no global bandwidth/rate limit yet |
| Corrupted model bytes | content-addressing — hash must match or the copy is skipped | — |
| Forged / poisoned improvement | signature + trusted-key check + example-hash check; unsigned/untrusted rejected | key distribution & revocation are manual |
| Malicious training data (thumbs-down) | never trained on; only 👍 / un-rejected pairs enter the pool | a malicious node could still 👍 bad data **on its own ledger** — only matters if its key is trusted |
| Sybil nodes (many fake peers) | improvements need a trusted signature to matter; reputation exists in `registry.py` | no global Sybil resistance / proof-of-work yet |
| Unsafe model output | **two layers**: a fast deterministic keyword gate (always on) **plus an LLM-as-judge** that reads intent and catches rephrasings (`safety/llm_judge.py`, on via `GUA_LLM_JUDGE=1`) | the judge is an LLM, not a bespoke **trained** classifier yet; it fails open if the model is down (keyword gate still applies) |
| Node owner loses control | opt-in, idle-only, resource caps, guaranteed local kill-switch | — |
| Private data exfiltration | data minimized, local-by-default; conversations/keys are git-ignored | encryption-at-rest of node data not yet implemented |

## Known limitations (stated plainly)

- Safety is now **two layers**: a deterministic keyword gate plus an **LLM-as-judge**
  (intent-based, catches rephrasings the keywords miss). This is a real improvement
  over the original keyword stub, but the judge is a general LLM, not a **purpose-
  trained** safety classifier — that remains the goal, and the judge fails open if
  its model is unavailable.
- **No transport encryption yet.** Messages are signed where it matters
  (ruleset, improvements) but the channel is plain TCP; add TLS/libp2p-secio
  before exposing nodes broadly.
- **Key management is manual.** One authority key; no rotation/revocation or
  threshold signing yet (Phase 3).
- **No global rate limiting / Sybil resistance.** Per-connection caps bound a
  single peer, not a coordinated swarm.

## Reporting

Found a vulnerability? See [SECURITY.md](../SECURITY.md) for how to report it
privately. Please do not open a public issue for security problems.
