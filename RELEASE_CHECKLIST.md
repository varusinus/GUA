# Release checklist — before publishing GUA on GitHub

A short, honest list. Most of the repo is ready; these are the few steps that
need a human (mainly secrets and the license text).

## 1. License — paste the full AGPL-3.0 text (manual, ~1 min)

`LICENSE` currently holds only the copyright notice. Replace its contents with
the complete, verbatim text from the official source (do **not** retype by hand):

  https://www.gnu.org/licenses/agpl-3.0.txt

Open that URL, copy everything, and paste it into `LICENSE` (keep the
"GUA — Copyright (C) 2026 Alexandru Ciobanu" notice at the top if you like).

## 2. Keys — generate fresh signing keys, never commit private keys

`governance/keys/` is git-ignored. Before first publish, generate your own keys
so you control the canonical ruleset and model signatures:

```
python governance/sign_ruleset.py --generate-key   # founding key + signs ruleset
```

- The **private** keys stay on your machine (already in `.gitignore`).
- The **public** key is embedded in `governance/ruleset.yaml` (committed) so
  anyone can verify the ruleset.
- If a private key ever leaks, rotate it and re-sign.

## 3. Fill in repo URLs

Replace `REPLACE_ME` in `pyproject.toml` (`[project.urls]`) with your GitHub
org/repo once it exists.

## 4. Sanity check locally

```
pip install -r requirements.txt
python governance/sign_ruleset.py --generate-key
python -m pytest -q            # full suite should pass
python network/replication_demo.py     # resilience demo
```

## 5. Push and let CI run

`.github/workflows/ci.yml` signs the ruleset with a throwaway key and runs the
test suite on Python 3.10–3.12 for every push and PR.

## 6. Nice-to-have before announcing

- Add a couple of screenshots/GIFs of the chat UI and the network demo to the
  README (a picture of the kill-switch + live federation sells the idea).
- Open the first design-review issues (see ROADMAP Phase 0).
- Double-check `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md` reflect
  how you want contributions handled.

---

That's it. After step 1–3 the repository is genuinely publishable: documented,
tested, with a working assistant, a real federated node daemon, signed
governance, and a guaranteed local kill-switch.
