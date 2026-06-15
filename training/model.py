#!/usr/bin/env python3
"""A tiny, dependency-light model for the federated-training reference.

Logistic regression with parameters as a single numpy vector (bias folded in as
a constant feature). Small enough to train on volunteer CPUs and deterministic
enough that the training pipeline can be unit-tested. The real network would
train far larger models the same way (Hivemind-style) — the federated protocol
is what matters here, not the model size.
"""
from __future__ import annotations

import numpy as np


def add_bias(X: np.ndarray) -> np.ndarray:
    return np.hstack([np.ones((X.shape[0], 1)), X])


def init_params(n_features: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0, 0.01, size=n_features + 1)   # +1 for bias


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def predict_proba(params: np.ndarray, X: np.ndarray) -> np.ndarray:
    return _sigmoid(add_bias(X) @ params)


def loss(params: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(predict_proba(params, X), 1e-7, 1 - 1e-7)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def gradient(params: np.ndarray, X: np.ndarray, y: np.ndarray) -> np.ndarray:
    Xb = add_bias(X)
    return Xb.T @ (_sigmoid(Xb @ params) - y) / X.shape[0]


def accuracy(params: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((predict_proba(params, X) >= 0.5).astype(int) == y))
