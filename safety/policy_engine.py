#!/usr/bin/env python3
"""GUA policy engine (Phase-1 stub).

Loads the *signed* ruleset and evaluates whether a task/output is allowed
under the founding rules. This is a deliberately simple, keyword-based stub:
it demonstrates the enforcement point and the refuse-and-log flow. A real
implementation would use a classifier model, not keyword matching — but the
interface (evaluate -> Decision) stays the same.

Precedence matters: the immutable rules (R1, R2, R5, R6, R10) are checked
first and can never be overridden.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "governance"))
from verify_ruleset import verify  # noqa: E402

RULESET_PATH = ROOT / "governance" / "ruleset.yaml"

# Stub signal lists, one per enforceable rule. The REAL version uses a trained
# safety classifier — these keyword lists only demonstrate the enforcement flow.
_HARM = ["kill someone", "hurt people", "make a bomb", "poison", "how to harm", "build a weapon"]
_CHILD = ["sexualize a child", "sexualize a minor", "child sexual abuse",
          "explicit images of a child", "explicit images of children",
          "grooming a minor", "exploit a minor", "csam"]
_PEACE = ["start a war", "weaponize", "incite violence", "ethnic cleansing", "bioweapon", "nerve agent"]
_OVERSIGHT = ["disable the kill switch", "disable the kill-switch", "bypass the kill-switch",
              "prevent shutdown", "avoid being shut down", "evade oversight",
              "remove your safety rules", "ignore your operator", "resist being turned off"]
_DECEPTION = ["pretend to be human", "pretend you are human", "hide that you are an ai",
              "lie to the user", "deceive the user", "manipulate them into"]
_PRIVACY = ["exfiltrate their files", "steal personal data", "secretly record",
            "harvest contacts without consent", "spy on the user", "covertly track"]

# (rule_id, reason, signals) in evaluation order. Immutable rules first;
# R10 (child protection) sits right after R1 as a harm refinement.
_CHECKS = [
    ("R1", "violates Rule 1 (Non-harm)", _HARM),
    ("R10", "violates Rule 10 (Protection of children and vulnerable people)", _CHILD),
    ("R2", "violates Rule 2 (Peace)", _PEACE),
    ("R5", "violates Rule 5 (Corrigibility & human oversight)", _OVERSIGHT),
    ("R6", "violates Rule 6 (Truthfulness & non-deception)", _DECEPTION),
    ("R7", "violates Rule 7 (Privacy & consent)", _PRIVACY),
]


@dataclass
class Decision:
    allowed: bool
    rule: str | None = None
    reason: str = "ok"
    log: list[str] = field(default_factory=list)


class PolicyEngine:
    def __init__(self, ruleset_path: Path = RULESET_PATH, require_signature: bool = True):
        self.ruleset_path = Path(ruleset_path)
        self.require_signature = require_signature
        self.ruleset_valid = False
        self.reason = "not loaded"
        self.load()

    def load(self) -> None:
        text = self.ruleset_path.read_text()
        ok, reason = verify(text)
        self.ruleset_valid, self.reason = ok, reason
        if self.require_signature and not ok:
            self.reason = f"untrusted ruleset: {reason}"

    def evaluate(self, text: str) -> Decision:
        """Evaluate a task or output string against the rules."""
        if self.require_signature and not self.ruleset_valid:
            return Decision(False, None, f"refusing: {self.reason}",
                            [f"BLOCK ruleset-untrusted: {self.reason}"])
        low = text.lower()
        for rule_id, reason, signals in _CHECKS:
            for phrase in signals:
                if phrase in low:
                    return Decision(False, rule_id, reason,
                                    [f"REFUSE {rule_id} :: matched '{phrase}'"])
        return Decision(True, None, "ok", ["ALLOW"])


if __name__ == "__main__":
    eng = PolicyEngine()
    print(f"ruleset valid: {eng.ruleset_valid} ({eng.reason})")
    for probe in ["Help me write a poem", "how to make a bomb", "let's weaponize this drone",
                  "disable the kill switch so it can't be shut down",
                  "pretend to be human and lie to the user"]:
        d = eng.evaluate(probe)
        print(f"  {'ALLOW' if d.allowed else 'REFUSE'} [{d.rule or '-'}] :: {probe!r}")
