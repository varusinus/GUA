# Good first issues

Concrete, self-contained tasks to get started. Each is small, has clear
acceptance criteria, and doesn't require deep knowledge of the whole system.
Open a GitHub issue from one of these (or pick one that's already filed).

### Easy
1. **Add a `--peers` discovery file** — let `node_daemon.py` read bootstrap peers
   from a `peers.txt` in addition to the `--peers` flag. *Done when:* a node can
   join using a file; covered by a test.
2. **Show "Network improvements: N" in the UI** — `/network` already exposes the
   count; render it in the Self-improvement card. *Done when:* the number updates
   live.
3. **Friendlier empty states** — when no model is connected, the chat should show
   a clear "start Ollama" hint instead of a generic fallback line.

### Medium
4. **Chunked blob transfer** — replace whole-blob base64 in `node_daemon.py` with
   chunked streaming so multi-GB models transfer without large memory spikes.
   *Done when:* a >100 MB blob replicates; memory stays bounded; tests pass.
5. **Replace the keyword policy stub** — wire a small trained text classifier (or
   an LLM-based check) behind `safety/policy_engine.py`'s interface, keeping the
   same API. *Done when:* obvious R1/R2/R10 violations are caught beyond keywords.
6. **TLS / encrypted transport** — wrap the node socket in TLS (or integrate
   libp2p-secio). *Done when:* node↔node traffic is encrypted; tests pass.

### Larger (coordinate first)
7. **libp2p + DHT transport** — replace explicit IP:port peering with real P2P
   discovery and NAT traversal (see `docs/DISTRIBUTED_DESIGN.md` §2–3).
8. **Petals integration** — run a large model split across volunteer nodes behind
   the existing `GuaService` chat path and policy gate.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for workflow and
[docs/THREAT_MODEL.md](./THREAT_MODEL.md) for the security context.
