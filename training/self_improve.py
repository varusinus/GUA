#!/usr/bin/env python3
"""Bounded self-improvement loop (Phase 3, Rule R5).

This is "the system improves itself" — made safe. Each cycle:
  1. the network trains a candidate (a federated round),
  2. the validation gate checks it (sane + no regression on holdout),
  3. for significant changes, a human must approve,
  4. only then is it signed into the model registry,
  5. every decision is written to the audit log.

Hard limits keep it corrigible: a `stop()` kill-switch halts further
self-improvement immediately, and a version cap bounds how far it can go on its
own. There is no path for the loop to promote a model that skipped the gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))   # training/
sys.path.insert(0, str(ROOT / "safety"))

from validation_gate import validate
from audit_log import AuditLog


class SelfImprovementLoop:
    def __init__(self, trainer, registry, holdout, *, audit=None, max_versions: int = 10,
                 require_human: bool = False, approve_fn=None, tolerance: float = 1e-3):
        self.trainer = trainer
        self.registry = registry
        self.Xho, self.yho = holdout
        self.audit = audit or AuditLog()
        self.max_versions = max_versions
        self.require_human = require_human
        self.approve_fn = approve_fn or (lambda cand, res: False)
        self.tolerance = tolerance
        self.stopped = False

    def stop(self) -> None:
        """Kill-switch: no further self-improvement is allowed."""
        self.stopped = True
        self.audit.append("kill_switch_engaged")

    def seed(self):
        res = validate(self.trainer.params, None, self.Xho, self.yho, tolerance=self.tolerance)
        v = self.registry.promote(self.trainer.params, res, note="genesis")
        self.audit.append("promote", {"version": v.version, "val_loss": round(v.val_loss, 4), "note": "genesis"})
        return v

    def run(self, cycles: int, shards, node_updates_fn=None) -> dict:
        promoted = []
        for c in range(1, cycles + 1):
            if self.stopped:
                self.audit.append("halted", {"before_cycle": c})
                break
            if len(self.registry.versions) >= self.max_versions:
                self.audit.append("max_versions_reached", {"cap": self.max_versions})
                break

            updates = node_updates_fn(c) if node_updates_fn else None
            candidate = self.trainer.run_round(shards, node_updates=updates)
            res = validate(candidate, self.registry.latest_params(), self.Xho, self.yho,
                           tolerance=self.tolerance)
            if not res.ok:
                self.audit.append("rejected_by_gate", {"cycle": c, "reason": res.reason})
                continue
            if self.require_human and not bool(self.approve_fn(candidate, res)):
                self.audit.append("rejected_pending_human", {"cycle": c})
                continue

            v = self.registry.promote(candidate, res, note=f"self-improve cycle {c}")
            self.audit.append("promote", {"version": v.version, "val_loss": round(v.val_loss, 4),
                                          "acc": round(res.candidate_acc, 4), "cycle": c})
            promoted.append(v.version)

        return {"promoted": promoted, "final_version": self.registry.latest().version,
                "stopped": self.stopped, "audit_intact": self.audit.verify_chain()}
