# Changelog

All notable changes to GUA are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versions use [SemVer](https://semver.org/).

## [0.1.0] — unreleased (first public release)

The first publishable cut: a working assistant, a real federated node network,
gated self-improvement, signed governance, and a guaranteed local kill-switch.

### Added
- **Chat assistant** with a real local model (Ollama) and a **native tool-calling
  agent** that decides on its own when to search the web and read pages, cites
  sources, and never fabricates having browsed.
- **Signed governance**: ed25519-signed `ruleset.yaml` (R1–R10), self-healing
  signer, and a policy engine that enforces the rules and explains refusals.
- **Persistent memory** and multi-conversation history (rename, delete, switch),
  surviving restarts.
- **Real cross-machine node daemon** (`network/node_daemon.py`): content-addressed
  model blobs replicate to peers by IP:port; a node's kill-switch never loses the
  model while one replica survives; self-healing `rebalance()`.
- **Federated self-improvement** (`network/improvement.py`): 👍 feedback becomes
  a signed, gated improvement that propagates across nodes; each node trains on
  the whole network's verified examples — more nodes make GUA smarter.
- **Bounded self-training** (`training/self_train.py`): retrains from feedback,
  passes a validation gate (identity + safety), and only then promotes — no model
  ships ungated (R5).
- **Live UI**: real node count, capabilities panel (reflects features as they
  grow), self-improvement controls, kill-switch.
- **Security**: framed-message size cap, blob-size and per-connection limits on
  the open port; `docs/THREAT_MODEL.md`.
- **Cross-platform**: Windows `.bat` and Linux/macOS `.sh` launchers; CI on
  Python 3.10–3.12; `pyproject.toml`; smoke test for every UI endpoint.
- Docs: Whitepaper, Constitution, Governance, Roadmap, `DISTRIBUTED_DESIGN.md`,
  `THREAT_MODEL.md`, `RELEASE_CHECKLIST.md`.

### Known limitations (see docs/THREAT_MODEL.md)
- Policy engine is a keyword **stub**, not a trained safety classifier.
- Peers are reached by IP:port; full libp2p/DHT + NAT traversal is pending.
- Plain-TCP transport (signed where it matters; no channel encryption yet).
- Single authority key; threshold signing / key rotation is a later phase.

[0.1.0]: https://github.com/REPLACE_ME/gua/releases/tag/v0.1.0
