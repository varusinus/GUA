# Contributing to GUA

Thank you for considering a contribution. GUA is in **Phase 0 (Foundation)** — there is no runnable network yet, so right now the most valuable work is on the *design, governance, and clarity* of the project.

## Before anything else: the rules

Every contribution must be compatible with the [Constitution](./CONSTITUTION.md). In particular, nothing may weaken **Rule 1 (Non-harm)** or **Rule 2 (Peace)** — these are immutable. Contributions that enable harm, weaponization, hidden/non-consensual compute use, or that bypass the safety controls will be rejected.

## High-value contributions right now (Phase 0)

- **Review the [Whitepaper](./WHITEPAPER.md)** and open issues where the design is weak, unclear, or unrealistic. Honest critique is welcome — especially on the safety and "No-Off Problem" sections.
- **Review the [Constitution](./CONSTITUTION.md) and [ruleset.yaml](./governance/ruleset.yaml).** Are the rules clear? Is the immutability mechanism sound?
- **Help spec the Phase 1 node-client** (see [`node-client/README.md`](./node-client/README.md)): the opt-in flow, resource-cap defaults, idle detection, the local kill-switch, the dashboard.
- **Threat modeling** — how could this be abused? How do we defend? File issues.
- **Documentation & translation** — clarity matters for adoption. (Project language is English; translations are welcome as additional files.)

## How to contribute

1. **Open an issue first** for anything non-trivial, so we can discuss direction before you invest time.
2. **Fork** the repo and create a branch (`feature/short-description`).
3. Make your change. Keep it focused; one logical change per pull request.
4. For design/governance changes, follow the [amendment pipeline](./GOVERNANCE.md#how-rules-change-amendment-pipeline).
5. **Open a pull request** with a clear description of *what* and *why*.

## Code (from Phase 1 onward)

When code lands, contributions should:
- include tests where it makes sense,
- run in the sandbox model (no component should need access to a user's personal files),
- never weaken the opt-in, resource-cap, or kill-switch guarantees,
- be documented.

A `STYLE.md` and CI will be added when the first code arrives.

## Licensing of contributions

By contributing, you agree your contribution is licensed under the project's [AGPL-3.0](./LICENSE). Don't submit code you don't have the right to license.

## Conduct

All participation is governed by the [Code of Conduct](./CODE_OF_CONDUCT.md). Be respectful; assume good faith.

## Security

Do **not** report security vulnerabilities in public issues — see [SECURITY.md](./SECURITY.md).
