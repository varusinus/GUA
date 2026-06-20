# Launch post drafts

Honest, no-hype copy for sharing GUA. Pick the one that fits the venue. Replace
the link if your repo URL changes.

Repo: https://github.com/varusinus/GUA

---

## Show HN / r/LocalLLaMA / r/opensource (long)

**GUA — an open, rule-governed AI network with a guaranteed kill-switch and federated self-improvement (AGPL-3.0)**

I've been building GUA: an open-source attempt at a community-run AI that gets
better as more people run it — like volunteer computing (BOINC, Folding@home),
but the product is open AI capacity instead of protein folds.

What actually works today (tested, on one or a few machines):

- **A tool-using chat assistant** on a local model (Ollama). It decides on its
  own when to search the web and read pages, cites sources, and won't pretend to
  have browsed when it didn't.
- **A real cross-machine node network.** The model is content-addressed and
  replicated across nodes; any node can hit its local kill-switch and the network
  keeps the model. A node going offline never loses it.
- **Federated, signed self-improvement.** Replies you rate 👍 become a signed,
  gated training update that propagates to other nodes — so more nodes pooling
  feedback makes everyone's next model better. Tampered/unsigned updates are
  rejected.
- **Bounded self-training.** It retrains from feedback, must pass a validation
  gate (still knows it's itself, still refuses harm), and only then is promoted.
  No model ships ungated.
- **Signed governance + kill-switch.** Ten rules (five immutable: non-harm,
  peace, corrigibility, truthfulness, child protection), ed25519-signed, enforced
  by a policy engine. You always control your own node.

What is honestly NOT there yet (it's a Phase-0/1 reference, not a finished
network): full libp2p P2P + NAT traversal (nodes currently connect by IP:port),
channel encryption, a trained safety classifier (the policy engine is a keyword
stub today), and integration with Petals/Hivemind for internet-scale large-model
training. The hardest unsolved part — training big models over consumer internet
— is the actual research frontier, and I say so in the docs.

It's deliberately honest about the limits, including the "No-Off Problem": you
can always stop *your* node, but a truly decentralized network can't be switched
off globally by one person. That tension is documented, not hidden.

AGPL-3.0. 80+ tests, CI on Python 3.10–3.12. Windows `.bat` and Linux/Mac `.sh`
one-click launchers. Whitepaper, constitution, threat model, and a distributed-
design doc are all in the repo.

I'd love feedback on the design — especially the federated-improvement trust
model and the path to real P2P. Good first issues are listed in the repo.

Repo: https://github.com/varusinus/GUA

---

## Short (X / Mastodon / Discussions)

Open-sourced **GUA**: a rule-governed AI network where the model is replicated
across volunteer nodes (survives any node going offline), improves from signed 👍
feedback that spreads peer-to-peer, and has a guaranteed local kill-switch.

Honest about what's not done yet (libp2p, big-model training at scale). AGPL-3.0,
tested, runs today.

→ https://github.com/varusinus/GUA

---

## One-liner

An open, rule-governed AI network with a kill-switch, where the model survives
any node going offline and gets smarter as more people run it. AGPL-3.0.

---

### Posting tips
- HN: title "Show HN: GUA — open rule-governed AI network with a kill-switch (AGPL)".
  Post as the author; add a first comment with the "what's NOT done yet" list —
  HN respects that.
- r/LocalLLaMA values local-first + honesty about limits. Lead with the kill-switch
  and the "no hidden mining / opt-in only" point.
- Don't call it "AGI" in the title — it invites dismissal. "AI network" is accurate
  and credible.
- Expect hard questions on the No-Off Problem and the keyword-stub policy. The
  honest answers are already in WHITEPAPER §5.4 and docs/THREAT_MODEL.md.
