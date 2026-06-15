#!/usr/bin/env python3
"""Federated self-improvement — "more nodes make GUA smarter", safely.

The mechanism (bandwidth-light and honest):

  1. Every node collects the replies its users marked good (👍). That small,
     curated set of (prompt, answer) examples is the training signal.
  2. A node that retrains and PASSES THE VALIDATION GATE publishes a signed
     "improvement": the version number, its parent, the base model, and the
     example set — ed25519-signed so its provenance is provable.
  3. Improvements propagate across the network. A node ADOPTS one only after it
     verifies the signature and the example hash. Tampered or unsigned
     improvements are rejected.
  4. Each node can aggregate the verified example sets from the whole network —
     so the more nodes contribute good feedback, the larger and better the shared
     training set, and the smarter every node's next model. That is the
     "compute/▒data grows with adoption" property, made concrete.

Why ship the *examples* and not the multi-GB weights? Because the curated data is
tiny and lets every node REBUILD the improvement locally (via self_train) — which
works over consumer internet. The full weights can still replicate via
`replication.py` / the node daemon when bandwidth allows.

Trust model (reference): all nodes here share the repo's model key, so signatures
verify everywhere. In production only the governance authority holds the PRIVATE
key; nodes carry its PUBLIC key and verify against it. Progressive
decentralization (threshold signing) is the Phase-3 step — see ROADMAP.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

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
    try:
        MODEL_KEY.chmod(0o600)
    except OSError:
        pass
    return key


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def examples_hash(examples: list) -> str:
    norm = [{"user": e["user"], "assistant": e["assistant"]} for e in examples]
    return _sha(_canon(norm))


@dataclass
class Improvement:
    version: int
    parent: str | None            # hash of the parent improvement (chain)
    base_model: str
    note: str
    created: float
    examples: list                # [{"user","assistant"}]
    examples_hash: str = ""
    pubkey: str = ""
    signature: str = ""

    def signed_payload(self) -> dict:
        return {"version": self.version, "parent": self.parent,
                "base_model": self.base_model, "note": self.note,
                "created": round(self.created, 3), "examples_hash": self.examples_hash}

    def hash(self) -> str:
        return _sha(_canon(self.signed_payload()))

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["id"] = self.hash()
        return d

    @staticmethod
    def from_dict(d: dict) -> "Improvement":
        return Improvement(
            version=d["version"], parent=d.get("parent"), base_model=d.get("base_model", ""),
            note=d.get("note", ""), created=d.get("created", 0.0),
            examples=d.get("examples", []), examples_hash=d.get("examples_hash", ""),
            pubkey=d.get("pubkey", ""), signature=d.get("signature", ""))


class ImprovementLedger:
    """Append-only, signed history of model improvements that propagates across
    the network. Nodes verify every entry before trusting it."""

    def __init__(self, path: str | Path, trusted_pubkeys: list[str] | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._key = _load_or_make_key()
        self.pubkey_hex = self._key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        # which signer(s) we trust; default trusts our own key (reference mode)
        self.trusted = set(trusted_pubkeys or [self.pubkey_hex])
        self.entries: list[dict] = []
        if self.path.exists():
            try:
                self.entries = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.entries = []

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.entries, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def latest(self) -> dict | None:
        return self.entries[-1] if self.entries else None

    def publish(self, examples: list, base_model: str, note: str = "") -> dict:
        """Create, sign, and append a new improvement (call AFTER the gate passes)."""
        clean = [{"user": e["user"], "assistant": e["assistant"]}
                 for e in examples if e.get("user") and e.get("assistant")]
        parent = self.latest()["id"] if self.latest() else None
        imp = Improvement(
            version=(self.latest()["version"] + 1 if self.latest() else 1),
            parent=parent, base_model=base_model, note=note,
            created=time.time(), examples=clean)
        imp.examples_hash = examples_hash(clean)
        imp.pubkey = self.pubkey_hex
        imp.signature = self._key.sign(_canon(imp.signed_payload())).hex()
        d = imp.to_dict()
        self.entries.append(d)
        self._save()
        return d

    def verify(self, d: dict) -> bool:
        """Signature valid, signer trusted, example hash intact."""
        try:
            imp = Improvement.from_dict(d)
            if imp.pubkey not in self.trusted:
                return False
            if examples_hash(imp.examples) != imp.examples_hash:
                return False
            pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(imp.pubkey))
            pub.verify(bytes.fromhex(imp.signature), _canon(imp.signed_payload()))
            return d.get("id") == imp.hash()
        except (InvalidSignature, ValueError, KeyError):
            return False

    def merge(self, incoming: list[dict]) -> int:
        """Add verified improvements we don't already have. Returns count added."""
        have = {e.get("id") for e in self.entries}
        added = 0
        for d in sorted(incoming, key=lambda x: x.get("version", 0)):
            if d.get("id") in have:
                continue
            if self.verify(d):
                self.entries.append(d)
                have.add(d.get("id"))
                added += 1
        if added:
            self.entries.sort(key=lambda x: x.get("version", 0))
            self._save()
        return added

    def all(self) -> list[dict]:
        return list(self.entries)

    def aggregated_examples(self) -> list:
        """The pooled training set from ALL verified improvements (deduped).
        Grows as more nodes contribute — this is what makes the network smarter."""
        pool, seen = [], set()
        for d in self.entries:
            if not self.verify(d):
                continue
            for e in d.get("examples", []):
                k = (e.get("user", ""), e.get("assistant", ""))
                if k[0] and k[1] and k not in seen:
                    seen.add(k)
                    pool.append({"user": e["user"], "assistant": e["assistant"]})
        return pool
