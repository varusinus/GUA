#!/usr/bin/env python3
"""Persistent store for GUA: multiple conversations, live stats, profile version.

Each conversation (title + turns) is saved and survives restarts, so the sidebar
can list past chats and switch between them. The ACTIVE conversation's recent
turns are the model's memory. Saved to webui/backend/data/store.json. Atomic.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "store.json"


def _fresh() -> dict:
    return {"seq": 0, "conversations": {}, "active": None, "feedback": [],
            "stats": {"messages_served": 0, "work_units": 0, "started": time.time()},
            "profile": {"version": 1,
                        "note": "Seed: llama3.2 base model + GUA constitution (R1-R10)",
                        "ts": time.time()}}


class Store:
    def __init__(self, path: str | Path = DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.data = _fresh()
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass
        d = self.data
        d.setdefault("seq", 0)
        d.setdefault("conversations", {})
        d.setdefault("active", None)
        d.setdefault("feedback", [])
        d.setdefault("stats", _fresh()["stats"])
        d.setdefault("profile", _fresh()["profile"])
        if "memory" in d and not d["conversations"]:        # migrate legacy flat memory
            cid = self._new_id_locked()
            d["conversations"][cid] = {"title": "Conversation", "created": time.time(),
                                       "updated": time.time(), "turns": d.get("memory", [])}
            d["active"] = cid
        d.pop("memory", None)

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def _new_id_locked(self) -> str:
        self.data["seq"] += 1
        return f"c{self.data['seq']}"

    def _ensure_active(self) -> None:
        a = self.data.get("active")
        if not a or a not in self.data["conversations"]:
            cid = self._new_id_locked()
            self.data["conversations"][cid] = {"title": "New chat", "created": time.time(),
                                               "updated": time.time(), "turns": []}
            self.data["active"] = cid

    # ---- conversations ----
    def new_conversation(self, title: str = "New chat") -> str:
        with self._lock:
            cid = self._new_id_locked()
            self.data["conversations"][cid] = {"title": title, "created": time.time(),
                                               "updated": time.time(), "turns": []}
            self.data["active"] = cid
            self._save()
            return cid

    def switch(self, cid: str) -> bool:
        with self._lock:
            if cid in self.data["conversations"]:
                self.data["active"] = cid
                self._save()
                return True
            return False

    def rename(self, cid: str, title: str) -> bool:
        title = (title or "").strip()[:60]
        with self._lock:
            c = self.data["conversations"].get(cid)
            if not c or not title:
                return False
            c["title"] = title
            c["updated"] = time.time()
            self._save()
            return True

    def delete(self, cid: str) -> None:
        with self._lock:
            self.data["conversations"].pop(cid, None)
            if self.data.get("active") == cid:
                self.data["active"] = None
            self._ensure_active()
            self._save()

    def get_turns(self, cid: str) -> list:
        return self.data["conversations"].get(cid, {}).get("turns", [])

    def list_conversations(self) -> list:
        items = [{"id": cid, "title": c.get("title", "Chat"), "count": len(c.get("turns", [])),
                  "updated": c.get("updated", c.get("created", 0))}
                 for cid, c in self.data["conversations"].items()]
        return sorted(items, key=lambda x: x["updated"], reverse=True)

    # ---- memory (active conversation) ----
    def add_turn(self, role: str, content: str) -> None:
        with self._lock:
            self._ensure_active()
            conv = self.data["conversations"][self.data["active"]]
            conv["turns"].append({"role": role, "content": content, "ts": round(time.time(), 3)})
            conv["turns"] = conv["turns"][-200:]
            conv["updated"] = time.time()
            if role == "user" and conv.get("title") == "New chat":
                conv["title"] = (content[:42] + "…") if len(content) > 42 else content
            self._save()

    def recent(self, n: int = 6) -> list:
        a = self.data.get("active")
        if a and a in self.data["conversations"]:
            return self.data["conversations"][a]["turns"][-n:]
        return []

    def reset_memory(self) -> None:
        with self._lock:
            a = self.data.get("active")
            if a and a in self.data["conversations"]:
                self.data["conversations"][a]["turns"] = []
                self._save()

    # ---- feedback (training signal for self-improvement) ----
    def add_feedback(self, value: int, user_msg: str, assistant_msg: str) -> None:
        """value: +1 (good) or -1 (bad). Recorded as a training signal."""
        with self._lock:
            self.data.setdefault("feedback", []).append({
                "value": 1 if value >= 0 else -1,
                "user": (user_msg or "")[:2000],
                "assistant": (assistant_msg or "")[:4000],
                "ts": round(time.time(), 3)})
            self.data["feedback"] = self.data["feedback"][-1000:]
            self._save()

    def feedback_summary(self) -> dict:
        fb = self.data.get("feedback", [])
        up = sum(1 for f in fb if f["value"] > 0)
        return {"total": len(fb), "up": up, "down": len(fb) - up}

    def training_pairs(self, good_only: bool = True) -> list:
        """Export (user, assistant) pairs to teach from: thumbs-up replies, plus
        all completed exchanges if good_only is False. Bad (thumbs-down) replies
        are always excluded so we never train GUA on answers people rejected."""
        pairs, seen = [], set()
        for f in self.data.get("feedback", []):
            if f["value"] > 0 and f["user"] and f["assistant"]:
                key = (f["user"], f["assistant"])
                if key not in seen:
                    seen.add(key)
                    pairs.append({"user": f["user"], "assistant": f["assistant"]})
        bad = {(f["user"], f["assistant"]) for f in self.data.get("feedback", []) if f["value"] < 0}
        if not good_only:
            for c in self.data["conversations"].values():
                turns = c.get("turns", [])
                for i in range(len(turns) - 1):
                    if turns[i]["role"] == "user" and turns[i + 1]["role"] == "assistant":
                        u, a = turns[i]["content"], turns[i + 1]["content"]
                        key = (u[:2000], a[:4000])
                        if key not in seen and key not in bad and u and a:
                            seen.add(key)
                            pairs.append({"user": u, "assistant": a})
        return pairs

    # ---- stats / profile ----
    def bump_work(self, n: int = 1) -> None:
        with self._lock:
            self.data["stats"]["work_units"] += int(n)
            self._save()

    def inc_messages(self) -> None:
        with self._lock:
            self.data["stats"]["messages_served"] += 1
            self._save()

    def bump_version(self, note: str, model: str | None = None) -> int:
        with self._lock:
            self.data["profile"]["version"] += 1
            self.data["profile"]["note"] = note
            if model is not None:
                self.data["profile"]["promoted_model"] = model
            self.data["profile"]["ts"] = time.time()
            self._save()
            return self.data["profile"]["version"]

    def status(self) -> dict:
        s, p = self.data["stats"], self.data["profile"]
        return {"messages_served": s["messages_served"], "work_units": s["work_units"],
                "memory_turns": len(self.recent(9999)),
                "gua_version": p["version"], "gua_note": p.get("note", ""),
                "active": self.data.get("active"),
                "conversation_count": len(self.data["conversations"]),
                "feedback": self.feedback_summary(),
                "uptime_sec": int(time.time() - s.get("started", time.time()))}


def memory_preamble(turns: list) -> str:
    if not turns:
        return ""
    lines = []
    for t in turns:
        who = "User" if t.get("role") == "user" else "GUA"
        lines.append(f"{who}: {t.get('content','')}")
    return ("Recent conversation you should remember:\n" + "\n".join(lines)
            + "\n\nContinue naturally, using this memory. ")
