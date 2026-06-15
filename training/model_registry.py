#!/usr/bin/env python3
"""Signed, append-only model registry (WHITEPAPER 4.6).

Every promoted model version is hashed, signed (ed25519), and appended with its
parent, validation loss, and a changelog note — so the model's lineage is
auditable and tamper-evident. Promotion REQUIRES a passing ValidationResult;
there is no path to ship a model that didn't go through the gate.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validation_gate import ValidationResult

KEYDIR = Path(__file__).resolve().parent.parent / "governance" / "keys"
MODEL_KEY = KEYDIR / "model_ed25519_private.pem"


def _load_or_make_key() -> Ed25519PrivateKey:
    if MODEL_KEY.exists():
        return serialization.load_pem_private_key(MODEL_KEY.read_bytes(), password=None)
    KEYDIR.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    MODEL_KEY.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    MODEL_KEY.chmod(0o600)
    return key


@dataclass
class ModelVersion:
    version: int
    params: list
    parent: str | None
    val_loss: float
    note: str
    hash: str = ""
    signature: str = ""


def _canonical(v: ModelVersion) -> bytes:
    payload = {"version": v.version, "params": [round(float(x), 8) for x in v.params],
               "parent": v.parent, "val_loss": round(float(v.val_loss), 8), "note": v.note}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


class ModelRegistry:
    def __init__(self):
        self._key = _load_or_make_key()
        self._pub = self._key.public_key()
        self.versions: list[ModelVersion] = []

    @property
    def public_key_hex(self) -> str:
        return self._pub.public_bytes(serialization.Encoding.Raw,
                                      serialization.PublicFormat.Raw).hex()

    def latest(self):
        return self.versions[-1] if self.versions else None

    def latest_params(self):
        v = self.latest()
        return np.asarray(v.params, dtype=float) if v else None

    def promote(self, candidate, validation: ValidationResult, note: str = "") -> ModelVersion:
        """Append a new signed version — ONLY if validation passed."""
        if not validation.ok:
            raise PermissionError(f"validation gate rejected promotion: {validation.reason}")
        parent = self.latest().hash if self.latest() else None
        v = ModelVersion(version=len(self.versions) + 1,
                         params=[float(x) for x in np.asarray(candidate, dtype=float)],
                         parent=parent, val_loss=float(validation.candidate_loss), note=note)
        canon = _canonical(v)
        v.hash = hashlib.sha256(canon).hexdigest()
        v.signature = self._key.sign(canon).hex()
        self.versions.append(v)
        return v

    def verify(self, v: ModelVersion) -> bool:
        try:
            self._pub.verify(bytes.fromhex(v.signature), _canonical(v))
            return v.hash == hashlib.sha256(_canonical(v)).hexdigest()
        except (InvalidSignature, ValueError):
            return False

    def verify_chain(self) -> bool:
        """Signatures valid AND parent links form an unbroken append-only chain."""
        prev = None
        for v in self.versions:
            if not self.verify(v) or v.parent != prev:
                return False
            prev = v.hash
        return True
