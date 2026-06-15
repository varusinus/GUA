#!/usr/bin/env python3
"""GUA node registry — peer discovery and reputation (Phase-1 reference).

This models the *discovery and trust* layer: who is on the network, are they
alive (heartbeats), and how much do we trust their results (reputation). The
real transport (libp2p / Kademlia DHT) plugs in underneath later — this module
encodes the semantics the scheduler relies on, and it is fully unit-tested.

The clock is injectable so heartbeat-expiry behavior is deterministic in tests.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

DEFAULT_REPUTATION = 1.0
MIN_REPUTATION = 0.2      # below this, a node is excluded from receiving work
HEARTBEAT_TTL = 120       # seconds; a node silent longer than this is excluded


@dataclass
class Node:
    node_id: str
    reputation: float = DEFAULT_REPUTATION
    last_heartbeat: float = 0.0
    contributing: bool = True   # mirrors the node-client opt-in state


class NodeRegistry:
    def __init__(self, heartbeat_ttl: float = HEARTBEAT_TTL,
                 now: Callable[[], float] = time.time):
        self._nodes: dict[str, Node] = {}
        self.heartbeat_ttl = heartbeat_ttl
        self._now = now

    def register(self, node_id: str, contributing: bool = True) -> Node:
        n = self._nodes.get(node_id)
        if n is None:
            n = Node(node_id, last_heartbeat=self._now(), contributing=contributing)
            self._nodes[node_id] = n
        else:
            n.contributing = contributing
            n.last_heartbeat = self._now()
        return n

    def heartbeat(self, node_id: str) -> None:
        n = self._nodes.get(node_id)
        if n:
            n.last_heartbeat = self._now()

    def set_contributing(self, node_id: str, contributing: bool) -> None:
        n = self._nodes.get(node_id)
        if n:
            n.contributing = contributing

    def adjust_reputation(self, node_id: str, delta: float) -> None:
        n = self._nodes.get(node_id)
        if n:
            n.reputation = max(0.0, min(1.0, n.reputation + delta))

    def eligible_workers(self) -> list[Node]:
        """Alive, opted-in, sufficiently-trusted nodes, best reputation first."""
        t = self._now()
        alive = [
            n for n in self._nodes.values()
            if n.contributing
            and n.reputation >= MIN_REPUTATION
            and (t - n.last_heartbeat) <= self.heartbeat_ttl
        ]
        return sorted(alive, key=lambda n: n.reputation, reverse=True)

    def get(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def all(self) -> list[Node]:
        return list(self._nodes.values())
