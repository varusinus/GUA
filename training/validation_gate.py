#!/usr/bin/env python3
"""Validation gate — bounded self-improvement (WHITEPAPER 6.2, Rule R5).

A model the network trains is NOT promoted automatically. A candidate must:
  1. be numerically sane (no NaN / Inf),
  2. not regress on a held-out set (capability check),
  3. for a significant change, be approved by a human (human-in-the-loop).

This is the concrete mechanism that keeps "self-improvement" corrigible: the
system proposes an improvement, but a check + a human decide whether it ships.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import loss, accuracy


@dataclass
class ValidationResult:
    ok: bool
    reason: str
    candidate_loss: float = float("nan")
    current_loss: float = float("nan")
    candidate_acc: float = float("nan")


def validate(candidate, current, X_holdout, y_holdout, *,
             tolerance: float = 1e-3, require_human: bool = False,
             human_approved: bool = False) -> ValidationResult:
    candidate = np.asarray(candidate, dtype=float)
    if not np.all(np.isfinite(candidate)):
        return ValidationResult(False, "candidate has non-finite values")

    cand_loss = loss(candidate, X_holdout, y_holdout)
    cur_loss = loss(current, X_holdout, y_holdout) if current is not None else float("inf")
    cand_acc = accuracy(candidate, X_holdout, y_holdout)

    if cand_loss > cur_loss + tolerance:
        return ValidationResult(False, f"regression: holdout loss {cand_loss:.4f} > {cur_loss:.4f}",
                                cand_loss, cur_loss, cand_acc)
    if require_human and not human_approved:
        return ValidationResult(False, "awaiting human approval (significant change)",
                                cand_loss, cur_loss, cand_acc)
    return ValidationResult(True, "ok", cand_loss, cur_loss, cand_acc)
