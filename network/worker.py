#!/usr/bin/env python3
"""A simple work executor used by nodes and by the scheduler simulation.

In the real system a worker runs a network-supplied task inside a sandbox and
returns the result. Here `compute` is a deterministic stub so that honest nodes
agree and faulty/malicious nodes can be simulated by returning something else.
"""
from __future__ import annotations

import hashlib


def compute(payload: str) -> str:
    """Deterministic 'work': honest nodes computing the same unit agree."""
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class SimWorker:
    """Simulated node worker. honest=False models a faulty/malicious node."""

    def __init__(self, node_id: str, honest: bool = True):
        self.node_id = node_id
        self.honest = honest

    def run(self, payload: str) -> str:
        if self.honest:
            return compute(payload)
        return "TAMPERED_" + compute(payload)[:6]
