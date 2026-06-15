# Security & Safety Policy

GUA has two kinds of "security": classic software security (vulnerabilities, abuse) and AI safety (the system behaving within its rules). Both matter.

## Reporting a vulnerability

**Do not open a public issue for security vulnerabilities.**

Email the maintainer privately at: **alexandru.ciobanu.ac@gmail.com** with:
- a description of the issue and its impact,
- steps to reproduce (if applicable),
- any suggested fix.

You will get an acknowledgement as soon as possible. Please allow reasonable time for a fix before public disclosure (coordinated disclosure). Security researchers acting in good faith will be credited if they wish.

## What counts as a security issue here

Beyond ordinary bugs, treat as security-sensitive:
- Anything that lets the node-client **access a user's personal files** or exceed its declared resource caps.
- Anything that lets code from the network **escape the sandbox**.
- Any way to **forge or bypass the ruleset signature** or the kill-switch.
- Any way to make the client **run without the user's explicit opt-in** (this would make GUA function like malware — a critical issue).
- **Signing-key compromise** of the governance or release keys.

## The safety model (summary)

GUA's safety rests on layered, deliberately fallible controls. See the [Whitepaper §6](./WHITEPAPER.md#6-safety) for detail.

1. **Explicit opt-in & resource caps** — the client only runs with consent, idle-only, within caps. No hidden mining, ever.
2. **Sandboxing** — untrusted code/tasks run isolated with minimal permissions, no access to personal data.
3. **Policy engine** — tasks and outputs are checked against the signed [ruleset](./governance/ruleset.yaml); violations are refused and logged.
4. **Validation gate + human-in-the-loop** — no self-modification is auto-applied; significant changes need human approval; rollback is always available.
5. **Malicious-node defenses** — redundant execution, majority vote, reputation, signatures.
6. **Append-only audit log** — important decisions are traceable.

## Honest limits (stated on purpose)

- **No guaranteed global kill-switch.** Local control is guaranteed; global shutdown of a decentralized network is not (the "No-Off Problem"). See [GOVERNANCE.md](./GOVERNANCE.md).
- **Rules are not mathematically guaranteed** on a self-modifying system; they are enforced by the controls above, which reduce but do not eliminate risk. This is the current state of the art for everyone.
- Because of these limits, the project deliberately keeps higher-autonomy capabilities (Whitepaper Phase 4) gated behind demonstrated safety progress, and is willing to **stop at Phase 3** if safety does not keep pace.

## Scope

This policy applies to all code and documents in this repository. Forks are independent; the AGPL keeps them open but their security practices are their own responsibility.
