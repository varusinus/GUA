#!/usr/bin/env python3
"""On-disk, content-addressed blob store for a GUA node.

Each node keeps its models here. A blob is addressed by its SHA-256, so any copy
that hashes to the same value is provably identical (tamper-evident). The store
persists to disk, so a node that stops (kill-switch) and restarts keeps its data
— it rejoins the network with the model it already holds.

  data_dir/
    blobs/<sha256>        the raw bytes of each model
    manifest.json         logical name -> {version, sha256, size}
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class BlobStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.blobs_dir = self.root / "blobs"
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "manifest.json"
        self.manifests: dict[str, dict] = {}
        if self.manifest_path.exists():
            try:
                self.manifests = json.loads(self.manifest_path.read_text())
            except Exception:
                self.manifests = {}

    # -- writes -------------------------------------------------------------
    def put(self, key: str, data: bytes, version: int = 1) -> dict:
        sha = sha256_hex(data)
        (self.blobs_dir / sha).write_bytes(data)
        m = {"key": key, "version": int(version), "sha256": sha, "size": len(data)}
        self.manifests[key] = m
        self._save()
        return m

    def put_blob(self, sha: str, data: bytes, manifest: dict) -> None:
        """Store a blob received from a peer, trusting the manifest's name but
        verifying the bytes hash to the claimed sha (integrity)."""
        if sha256_hex(data) != sha:
            raise ValueError("blob hash mismatch — refusing corrupted data")
        (self.blobs_dir / sha).write_bytes(data)
        self.manifests[manifest["key"]] = {
            "key": manifest["key"], "version": int(manifest.get("version", 1)),
            "sha256": sha, "size": len(data)}
        self._save()

    # -- reads --------------------------------------------------------------
    def has(self, sha: str) -> bool:
        return (self.blobs_dir / sha).exists()

    def get_blob(self, sha: str) -> bytes | None:
        p = self.blobs_dir / sha
        return p.read_bytes() if p.exists() else None

    def get_by_key(self, key: str) -> bytes | None:
        m = self.manifests.get(key)
        return self.get_blob(m["sha256"]) if m else None

    def list(self) -> dict[str, dict]:
        return dict(self.manifests)

    def _save(self) -> None:
        self.manifest_path.write_text(json.dumps(self.manifests, indent=2))
