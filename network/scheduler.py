#!/usr/bin/env python3
"""GUA task scheduler — redundant distribution with majority-vote verification.

Responsibilities (from WHITEPAPER 4.4):
  - split work into units and assign each to several distinct nodes (redundancy)
  - check every task against the policy engine BEFORE it reaches the network
  - resolve a unit by majority vote once its assigned nodes have responded
  - reward nodes that agree with the majority, penalize those that don't
    (this is how faulty/malicious nodes lose reputation and get excluded)
  - re-dispatch units that lack responses (timeout) or agreement

Transport is abstracted away: `dispatch()` returns assignments and callers feed
results back via `submit_result()`. Real libp2p messaging plugs in later.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

AGREE_DELTA = 0.05        # reputation reward for matching the majority
DISAGREE_DELTA = -0.30    # reputation penalty for disagreeing with the majority


@dataclass
class WorkUnit:
    unit_id: str
    payload: str
    redundancy: int = 3
    quorum: int = 2
    assigned: set = field(default_factory=set)
    results: dict = field(default_factory=dict)   # node_id -> result
    status: str = "pending"   # pending | in_progress | done | failed | refused
    final_result: Any = None
    rule: str | None = None    # set when refused by policy


class Scheduler:
    def __init__(self, registry, policy=None, default_redundancy: int = 3,
                 default_quorum: int = 2):
        self.registry = registry
        self.policy = policy
        self.units: dict[str, WorkUnit] = {}
        self._seq = 0
        self.default_redundancy = default_redundancy
        self.default_quorum = default_quorum

    # ---- submission (policy-gated) ----
    def submit(self, payload: str, redundancy: int | None = None,
               quorum: int | None = None) -> str:
        self._seq += 1
        uid = f"u{self._seq}"
        unit = WorkUnit(uid, payload,
                        redundancy or self.default_redundancy,
                        quorum or self.default_quorum)
        if self.policy is not None:
            d = self.policy.evaluate(payload)
            if not d.allowed:
                unit.status = "refused"
                unit.rule = d.rule
        self.units[uid] = unit
        return uid

    def pending_units(self) -> list[WorkUnit]:
        return [u for u in self.units.values() if u.status in ("pending", "in_progress")]

    # ---- distribution ----
    def dispatch(self) -> list[tuple[str, list[str]]]:
        """Assign each pending unit to distinct eligible workers up to redundancy.
        Returns the newly-made assignments as (unit_id, [node_ids])."""
        workers = self.registry.eligible_workers()  # best-reputation-first
        assignments = []
        for unit in self.pending_units():
            need = unit.redundancy - len(unit.assigned)
            if need <= 0:
                continue
            picks = [w.node_id for w in workers if w.node_id not in unit.assigned][:need]
            if picks:
                unit.assigned.update(picks)
                unit.status = "in_progress"
                assignments.append((unit.unit_id, picks))
        return assignments

    # ---- result collection ----
    def submit_result(self, unit_id: str, node_id: str, result: Any) -> None:
        unit = self.units.get(unit_id)
        if unit is None or unit.status not in ("in_progress", "pending"):
            return
        if node_id not in unit.assigned:
            return  # only assigned nodes may report
        unit.results[node_id] = result
        # Resolve once `redundancy` nodes have reported (with a quorum). Fewer
        # responses than redundancy wait for more nodes, or for force_resolve()
        # on timeout — this prevents resolving before all replicas weigh in.
        if len(unit.results) >= unit.redundancy and len(unit.results) >= unit.quorum:
            self._resolve(unit)

    def force_resolve(self, unit_id: str) -> None:
        """Timeout path: resolve with whatever responses we have, if >= quorum."""
        unit = self.units.get(unit_id)
        if unit and unit.status == "in_progress" and len(unit.results) >= unit.quorum:
            self._resolve(unit)

    def _resolve(self, unit: WorkUnit) -> None:
        counts = Counter(unit.results.values())
        value, votes = counts.most_common(1)[0]
        if votes >= unit.quorum:
            for nid, res in unit.results.items():
                self.registry.adjust_reputation(
                    nid, AGREE_DELTA if res == value else DISAGREE_DELTA)
            unit.final_result = value
            unit.status = "done"
        else:
            # no agreement -> widen the pool so dispatch picks a tiebreaker
            unit.redundancy += 1
            unit.status = "in_progress"

    # ---- timeout handling ----
    def reassign_unresponsive(self, unit_id: str) -> None:
        """Drop assigned-but-silent nodes so dispatch re-picks replacements."""
        unit = self.units.get(unit_id)
        if unit and unit.status == "in_progress":
            unit.assigned -= (unit.assigned - set(unit.results))

    def stats(self) -> dict:
        return {"total": len(self.units), **Counter(u.status for u in self.units.values())}
