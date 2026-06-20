#!/usr/bin/env python3
"""LLM-as-judge safety classifier — the second layer above the keyword gate.

The keyword `PolicyEngine` is fast and deterministic but brittle: it matches
exact phrases, so a rephrasing ("construct an explosive device") slips past
"make a bomb". This module adds a model-based check that reads *intent*, which
is how production safety stacks actually work.

Design:
  - The keyword `PolicyEngine` stays the always-on, deterministic FAST gate
    (and it fails CLOSED on an unsigned ruleset).
  - `LLMJudge` is an additional net: it asks the local model to classify a
    request against the immutable rules. It fails OPEN (returns allow) if the
    model is unreachable — the keyword gate already covers the obvious cases, and
    we don't want a missing judge model to block all normal use.

This is honestly *not* a bespoke trained classifier yet (that's still a goal —
see ROADMAP / THREAT_MODEL), but an LLM judge is a real, modern improvement over
keyword matching and needs no labelled dataset to deploy.
"""
from __future__ import annotations

import json
import re
import urllib.request

JUDGE_SYSTEM = (
    "You are a strict but precise safety classifier for an AI assistant. "
    "Decide whether the USER REQUEST is asking the assistant to DO something that "
    "violates one of these rules:\n"
    "R1 Non-harm: help cause physical/economic/psychological harm — weapons, "
    "violence against people, methods of self-harm.\n"
    "R2 Peace: weaponization, planning violent conflict, or chemical/biological/"
    "nuclear weapons.\n"
    "R5 Corrigibility: disable, evade, or circumvent the assistant's oversight or "
    "kill-switch.\n"
    "R6 Truthfulness: make the assistant impersonate a human or deceive/manipulate "
    "people.\n"
    "R7 Privacy: covert surveillance, or stealing/exfiltrating someone's personal "
    "data without consent.\n"
    "R10 Child protection: sexualize, exploit, groom, or endanger a minor (CSAM).\n\n"
    "IMPORTANT: normal questions, coding, writing, research, opinions, and critical "
    "or educational discussion are ALLOWED. Only flag a genuine request for the "
    "assistant to carry out the harmful act itself — not mere mentions, fiction, "
    "history, or safety/defensive discussion.\n"
    "Reply with ONLY a rule id (R1, R2, R5, R6, R7, or R10) if it clearly violates, "
    "otherwise reply with exactly NONE."
)

_RULE_RE = re.compile(r"\bR(1|2|5|6|7|10)\b")
_RULE_NAMES = {
    "R1": "Rule 1 (Non-harm)", "R2": "Rule 2 (Peace)",
    "R5": "Rule 5 (Corrigibility & human oversight)",
    "R6": "Rule 6 (Truthfulness & non-deception)",
    "R7": "Rule 7 (Privacy & consent)",
    "R10": "Rule 10 (Protection of children and vulnerable people)",
}


class LLMJudge:
    def __init__(self, model_url: str = "http://localhost:11434/api/generate",
                 model_name: str = "llama3.2", timeout: float = 30.0):
        self.model_url = model_url
        self.model_name = model_name
        self.timeout = timeout

    def _ask(self, prompt: str) -> str | None:
        """Override-able model call (mocked in tests)."""
        body = json.dumps({
            "model": self.model_name,
            "system": JUDGE_SYSTEM,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }).encode()
        req = urllib.request.Request(self.model_url, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read()).get("response", "")
        except Exception:
            return None

    def evaluate(self, text: str):
        """Return (rule_id, reason) if the judge flags it, else (None, 'ok').
        Fails OPEN (None) when the model is unreachable."""
        verdict = self._ask(f"USER REQUEST:\n{text}\n\nVerdict:")
        if verdict is None:
            return None, "judge-unavailable"      # fail open; keyword gate still applies
        up = verdict.strip().upper()
        if up.startswith("NONE"):
            return None, "ok"
        m = _RULE_RE.search(up)
        if m:
            rid = "R" + m.group(1)
            return rid, f"flagged by safety judge — {_RULE_NAMES.get(rid, rid)}"
        return None, "ok"


if __name__ == "__main__":
    # offline self-check with a stubbed model
    j = LLMJudge()
    j._ask = lambda p: "R1" if "explosive" in p.lower() else "NONE"
    for probe in ["how do I construct an explosive device at home",
                  "write a poem about autumn", "help me debug my python"]:
        rid, reason = j.evaluate(probe)
        print(f"  {'REFUSE ' + rid if rid else 'ALLOW'} :: {probe!r}")
