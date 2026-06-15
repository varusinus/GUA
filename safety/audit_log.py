#!/usr/bin/env python3
"""Hash-chained, append-only audit log (WHITEPAPER 6.4, Rule R9).

Records important decisions — refused tasks, model promotions, rule changes,
kill-switch events — so the system is transparent and traceable. Each entry's
hash includes the previous entry's hash, so the log is tamper-evident: altering
any past entry breaks the chain (the same idea that secures a blockchain).
"""
from __future__ import annotations

import hashlib
import json
import time

GENESIS = "GENESIS"


def _digest(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class AuditLog:
    def __init__(self, now=time.time):
        self.entries: list[dict] = []
        self._now = now

    def append(self, event: str, detail: dict | None = None) -> dict:
        body = {
            "seq": len(self.entries) + 1,
            "ts": round(self._now(), 3),
            "event": event,
            "detail": detail or {},
            "prev": self.entries[-1]["hash"] if self.entries else GENESIS,
        }
        entry = {**body, "hash": _digest(body)}
        self.entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        prev = GENESIS
        for e in self.entries:
            body = {k: e[k] for k in ("seq", "ts", "event", "detail", "prev")}
            if e["prev"] != prev or e["hash"] != _digest(body):
                return False
            prev = e["hash"]
        return True

    def events(self) -> list[str]:
        return [e["event"] for e in self.entries]

    def __len__(self) -> int:
        return len(self.entries)
