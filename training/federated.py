#!/usr/bin/env python3
"""Federated training: nodes train on local shards, the coordinator aggregates.

This is the reference for Phase 2 ("the network improves the model"). Each node
runs a *local update* on its own data shard (its data never leaves the machine —
only model updates are shared, which is the privacy property R7 cares about).
The coordinator aggregates the updates into a new global model.

Two aggregators:
  - `fedavg` (size-weighted mean) — standard Federated Averaging.
  - `robust_median` (coordinate-wise median) — resists a malicious node that
    returns garbage updates, the training analogue of the scheduler's
    majority-vote defense.
"""
from __future__ import annotations

import numpy as np

from model import gradient


def local_update(params: np.ndarray, X: np.ndarray, y: np.ndarray,
                 lr: float = 0.5, epochs: int = 5) -> np.ndarray:
    """One node's work: a few gradient-descent steps on its shard."""
    w = params.copy()
    for _ in range(epochs):
        w = w - lr * gradient(w, X, y)
    return w


def fedavg(updates: list[np.ndarray], weights: list[float] | None = None) -> np.ndarray:
    M = np.vstack(updates)
    if weights is None:
        return M.mean(axis=0)
    wts = np.asarray(weights, dtype=float)
    wts = wts / wts.sum()
    return (M * wts[:, None]).sum(axis=0)


def robust_median(updates: list[np.ndarray], weights=None) -> np.ndarray:
    """Coordinate-wise median — a single malicious update can't move it far."""
    return np.median(np.vstack(updates), axis=0)


class FederatedTrainer:
    def __init__(self, params: np.ndarray, aggregator=fedavg):
        self.params = params.copy()
        self.aggregator = aggregator

    def run_round(self, shards: list[tuple[np.ndarray, np.ndarray]],
                  node_updates: list[np.ndarray] | None = None) -> np.ndarray:
        """Distribute current params, collect each node's update, aggregate.

        `node_updates`, if given, overrides the honest local update for specific
        nodes (used to inject a malicious node in tests/demos).
        """
        updates, weights = [], []
        for i, (X, y) in enumerate(shards):
            if node_updates is not None and node_updates[i] is not None:
                upd = node_updates[i]
            else:
                upd = local_update(self.params, X, y)
            updates.append(upd)
            weights.append(len(y))
        self.params = self.aggregator(updates, weights)
        return self.params
