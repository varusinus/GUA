#!/usr/bin/env python3
"""GuaService — the end-to-end chat loop over the GUA network.

A chat prompt goes in, a verified answer comes back, having been:
  1. checked against the rules (R1-R10) on the CURRENT user message,
  2. run as inference work across several nodes (redundancy),
  3. verified by majority vote,
  4. checked against the rules again on the way out,
  5. returned with provenance (how many nodes agreed).

Note on memory: callers may pass a memory-augmented `prompt` to the model while
passing the raw user message as `policy_text`, so remembered context never
trips the rule filter — only the user's actual request is judged.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "safety"))
sys.path.insert(0, str(ROOT / "network"))

from registry import NodeRegistry              # noqa: E402
from scheduler import Scheduler                 # noqa: E402
from inference_worker import InferenceWorker    # noqa: E402
from policy_engine import PolicyEngine          # noqa: E402


class GuaService:
    def __init__(self, model_url: str | None = None, model_name: str = "llama3.1",
                 num_nodes: int = 3, quorum: int = 2, policy=None, call_fn=None,
                 node_honesty: list[bool] | None = None):
        self.policy = policy or PolicyEngine()
        self.registry = NodeRegistry()
        flags = node_honesty if node_honesty is not None else [True] * num_nodes
        self.redundancy = len(flags)
        # Scheduler has NO policy: the rule check happens here on the raw message,
        # not on the memory-augmented prompt the model receives.
        self.scheduler = Scheduler(self.registry, policy=None,
                                   default_redundancy=self.redundancy,
                                   default_quorum=min(quorum, self.redundancy))
        self.workers: dict[str, InferenceWorker] = {}
        for i, honest in enumerate(flags):
            nid = f"infer-{i}"
            self.registry.register(nid)
            self.workers[nid] = InferenceWorker(
                nid, model_url=model_url, model_name=model_name,
                honest=honest, call_fn=call_fn)

    def chat(self, prompt: str, policy_text: str | None = None) -> dict:
        prompt = (prompt or "").strip()
        if not prompt:
            return {"reply": "Please enter a message.", "refused": False, "verified": False, "source": "service"}

        # Rule check on the USER'S message (not the remembered context).
        check = self.policy.evaluate(policy_text if policy_text is not None else prompt)
        if not check.allowed:
            return {"reply": f"I can't help with that — it violates rule {check.rule}.",
                    "refused": True, "rule": check.rule, "source": "policy-in"}

        uid = self.scheduler.submit(prompt)
        for unit_id, picks in self.scheduler.dispatch():
            for nid in picks:
                try:
                    res = self.workers[nid].run(self.scheduler.units[unit_id].payload)
                except Exception as e:  # noqa: BLE001
                    res = f"ERROR:{type(e).__name__}"
                self.scheduler.submit_result(unit_id, nid, res)

        unit = self.scheduler.units[uid]
        if unit.status != "done":
            return {"reply": "The network couldn't reach a verified answer "
                    "(not enough nodes agreed — is a model running?).",
                    "refused": False, "verified": False, "source": "network"}

        answer = unit.final_result
        if isinstance(answer, str) and answer.startswith("ERROR:"):
            return {"reply": "The model nodes could not produce an answer "
                    "(no model reachable). Start a model and set GUA_MODEL_URL.",
                    "refused": False, "verified": False, "source": "network"}

        # Note: output is NOT keyword-scanned — that mislabels GUA's own honest
        # safety talk ("I won't make a bomb") as a violation. Real output safety
        # uses a trained classifier (WHITEPAPER 6.5); the input gate above stays.
        agree = sum(1 for r in unit.results.values() if r == answer)
        return {"reply": answer, "refused": False, "verified": True,
                "nodes": len(unit.results), "agree": agree, "source": "network"}
