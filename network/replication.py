#!/usr/bin/env python3
"""Replicated, resilient model store (WHITEPAPER §4 — "GUA lives everywhere").

This answers a concrete question: if the model is spread across many volunteer
nodes, and any node can hit its **local kill-switch** at any time, how does the
network *not* lose the model?

Answer: **replication + content-addressing**.

  - The model's weights are a blob, identified by its SHA-256 (content address).
    Any copy that hashes to the same value is provably the same model — tamper
    is detectable for free.
  - Each blob is stored on R different nodes (the *replication factor*). The
    model is available as long as **at least one** of those R nodes is alive.
  - A node hitting its kill-switch only makes *its own* copy unreachable. The
    other replicas still serve the model, so the network loses nothing. Your
    machine stopping never takes the model down — that is the whole point of
    decentralization, and it is what makes the local kill-switch safe to use.
  - `rebalance()` restores the replication factor on the surviving nodes after a
    death, so redundancy heals over time (like BitTorrent re-seeding / IPFS pin).

This is a dependency-light reference of the semantics. The real system would put
libp2p + a DHT underneath (who has which blob) and stream chunks over the wire;
the availability math demonstrated here is identical. Authenticity (that a blob
is a *blessed* version) is handled by the signed `training/model_registry.py`;
this module handles *availability and integrity*.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ModelLost(LookupError):
    """Raised only when every replica of a model is gone — true data loss."""


@dataclass
class Manifest:
    """What the network knows about a stored model (not the bytes themselves)."""
    key: str                       # logical name, e.g. "gua-model"
    version: int
    sha256: str
    size: int
    replicas: set[str] = field(default_factory=set)   # node_ids meant to hold it


class ReplicatedModelStore:
    """A toy of the distributed model store. Nodes hold content-addressed blobs;
    killing nodes never loses the model while one replica survives."""

    def __init__(self, replication_factor: int = 3):
        if replication_factor < 1:
            raise ValueError("replication_factor must be >= 1")
        self.replication_factor = replication_factor
        self._alive: dict[str, bool] = {}
        self._blobs: dict[str, dict[str, bytes]] = {}     # node_id -> {sha: bytes}
        self._manifests: dict[str, Manifest] = {}         # key -> Manifest

    # -- node lifecycle -----------------------------------------------------
    def add_node(self, node_id: str) -> None:
        self._alive.setdefault(node_id, True)
        self._blobs.setdefault(node_id, {})

    def kill_node(self, node_id: str) -> None:
        """Local kill-switch: the node goes offline. Its data is RETAINED (so it
        can resume), but it is unreachable by the network while stopped."""
        if node_id in self._alive:
            self._alive[node_id] = False

    def revive_node(self, node_id: str) -> None:
        if node_id in self._alive:
            self._alive[node_id] = True

    def wipe_node(self, node_id: str) -> None:
        """Permanent departure: node leaves and its disk is gone for good.
        The network must still survive this via other replicas."""
        self._alive.pop(node_id, None)
        self._blobs.pop(node_id, None)
        for m in self._manifests.values():
            m.replicas.discard(node_id)

    def alive_nodes(self) -> list[str]:
        return sorted(n for n, up in self._alive.items() if up)

    # -- storage ------------------------------------------------------------
    def put(self, key: str, data: bytes, version: int = 1) -> Manifest:
        """Store a model blob on up to R alive nodes (least-loaded first)."""
        targets = self._pick_targets(self.replication_factor, holding=None)
        if not targets:
            raise RuntimeError("no alive nodes to store the model on")
        sha = sha256_hex(data)
        for n in targets:
            self._blobs[n][sha] = data
        m = Manifest(key=key, version=version, sha256=sha, size=len(data),
                     replicas=set(targets))
        self._manifests[key] = m
        return m

    def get(self, key: str) -> bytes:
        """Fetch the model from ANY surviving replica, verifying its hash.
        Raises ModelLost only if no replica survives anywhere."""
        m = self._manifests.get(key)
        if m is None:
            raise KeyError(key)
        for n in self.alive_nodes():
            if n in m.replicas and m.sha256 in self._blobs.get(n, {}):
                data = self._blobs[n][m.sha256]
                if sha256_hex(data) != m.sha256:
                    continue                      # corrupted copy — skip it
                return data
        raise ModelLost(f"'{key}' has no surviving replica (all holders are gone)")

    def replicas_alive(self, key: str) -> list[str]:
        """Which alive nodes currently serve this model."""
        m = self._manifests.get(key)
        if not m:
            return []
        return [n for n in self.alive_nodes()
                if n in m.replicas and m.sha256 in self._blobs.get(n, {})]

    def is_available(self, key: str) -> bool:
        return len(self.replicas_alive(key)) > 0

    def integrity_ok(self, key: str) -> bool:
        """Every surviving copy still hashes to the manifest hash (no tamper)."""
        m = self._manifests.get(key)
        if not m:
            return False
        copies = [self._blobs[n][m.sha256] for n in self.replicas_alive(key)]
        return bool(copies) and all(sha256_hex(c) == m.sha256 for c in copies)

    # -- self-healing redundancy -------------------------------------------
    def rebalance(self, key: str | None = None) -> dict:
        """Restore the replication factor on surviving nodes after deaths.
        Returns {key: new_replica_count}."""
        report = {}
        keys = [key] if key else list(self._manifests)
        for k in keys:
            m = self._manifests[k]
            holders = self.replicas_alive(k)
            if not holders:
                report[k] = 0                      # truly lost — cannot heal
                continue
            need = self.replication_factor - len(holders)
            if need > 0:
                source = self._blobs[holders[0]][m.sha256]
                for n in self._pick_targets(need, holding=m.sha256):
                    self._blobs[n][m.sha256] = source
                    m.replicas.add(n)
            report[k] = len(self.replicas_alive(k))
        return report

    # -- helpers ------------------------------------------------------------
    def _pick_targets(self, count: int, holding: str | None) -> list[str]:
        """Pick `count` alive nodes that don't already hold `holding`,
        least-loaded first (balance), then by id (deterministic)."""
        candidates = [n for n in self.alive_nodes()
                      if holding is None or holding not in self._blobs.get(n, {})]
        candidates.sort(key=lambda n: (len(self._blobs[n]), n))
        return candidates[:count]
