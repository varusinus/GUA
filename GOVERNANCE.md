# Governance

How decisions are made in GUA, who makes them, and how the rules change. This complements the [Constitution](./CONSTITUTION.md) (the rules themselves) and the [Whitepaper](./WHITEPAPER.md) (the design).

## Guiding stance: control vs. decentralization

GUA faces a structural trade-off that shapes all governance:

> The more guaranteed control we want, the more centralized the system must be. The more decentralization and viral growth we want, the less global control any single party retains (the **"No-Off Problem"**).

Our chosen path: **start more centralized, decentralize progressively as safety matures.** Early phases keep coordination nodes and signing keys under the founding developer's control. Decentralization of authority is earned by demonstrated safety, not assumed up front.

## Current model (Phase 0–1): Benevolent founder + open input

- **Decision authority:** the founding developer (Alexandru Ciobanu) is the final decision-maker and holds the ruleset signing key.
- **Open input:** anyone may propose changes via issues and pull requests. Design discussion is public.
- **Constraint on the founder:** the founder is also bound by the Constitution. The founder **cannot** weaken Rules 1 or 2 — those are immutable for everyone, including them.

This concentrated model is intentional for the early, higher-risk phases. It is the part of the system that gives the founder the off-switch and rule-setting power they require.

## Intended evolution (Phase 2+): toward shared governance

As the project matures, authority is intended to broaden — for example a stewarding **foundation** or an elected **technical council** — with:

- Multiple signing-key holders (threshold/multisig signing of the ruleset).
- A transparent proposal → review → decision pipeline.
- Clear conflict-of-interest and succession rules (so the project survives any single person).

The immutable rules (R1, R2) remain immutable across every governance form.

## How rules change (amendment pipeline)

Mirrors [Constitution Article 4](./CONSTITUTION.md#article-4--amendment-process):

1. **Propose** — public issue/PR with rationale.
2. **Compatibility check** — automated + human review that the change does not conflict with R1/R2. *Failing this ends the proposal.*
3. **Public review window** — currently **14 days** for material changes (shorter for typo/clarity fixes).
4. **Decision** — by the current authority (Phase 0–1: the founder).
5. **Sign & version** — update and sign [`governance/ruleset.yaml`](./governance/ruleset.yaml), bump the semver, add a changelog entry.
6. **Propagate** — nodes adopt the new signed ruleset; nodes that cannot verify the signature keep the last valid one.

## Keys and signing

- The ruleset and model releases are cryptographically signed (suggested: ed25519; threshold signing once governance broadens).
- Public keys are published in the repo so anyone can verify authenticity.
- **Key compromise** is a security incident — see [SECURITY.md](./SECURITY.md).

## What is explicitly *not* promised

- A guaranteed global kill-switch. (Local control is guaranteed; global is best-effort.)
- That governance will always be fast. Safety review takes precedence over speed.

## Amending this document

Changes to GOVERNANCE.md follow the same amendment pipeline above, except they may never grant any authority the power to weaken R1 or R2.
