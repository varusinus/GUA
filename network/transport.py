#!/usr/bin/env python3
"""GUA real socket transport (Phase-1).

Turns the in-process scheduler into something that runs across real OS
processes / machines over TCP. A `Coordinator` hosts the registry + scheduler
and acts as a bootstrap endpoint; `NodeAgent`s connect over sockets to
register, pull work, and return results.

Message protocol: 4-byte big-endian length prefix + JSON body.
Message types: register, heartbeat, pull, result.

This is real networking (sockets, separate processes/threads). It is NOT yet
full internet-scale P2P — libp2p/Kademlia DHT and NAT traversal replace the
single bootstrap Coordinator later. The scheduler/registry semantics are
unchanged; only the transport is new.
"""
from __future__ import annotations

import json
import socket
import struct
import threading


# ----------------------------- framing -----------------------------
# Hard cap on a single framed message. A peer on an open port could otherwise
# claim a huge length and force us to allocate it — a trivial memory-bomb / DoS.
# 64 MiB comfortably covers a base64'd model chunk while bounding the damage.
MAX_MSG_BYTES = 64 * 1024 * 1024


def send_msg(sock: socket.socket, obj: dict) -> None:
    data = json.dumps(obj).encode()
    if len(data) > MAX_MSG_BYTES:
        raise ValueError(f"message too large to send: {len(data)} bytes")
    sock.sendall(struct.pack(">I", len(data)) + data)


def _recvn(sock: socket.socket, n: int) -> bytes | None:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(min(n - len(buf), 1 << 20))   # read in <=1 MiB slices
        if not chunk:
            return None
        buf += chunk
    return buf


def recv_msg(sock: socket.socket, max_bytes: int = MAX_MSG_BYTES) -> dict | None:
    hdr = _recvn(sock, 4)
    if not hdr:
        return None
    (n,) = struct.unpack(">I", hdr)
    if n > max_bytes:           # refuse an oversized claim before allocating it
        return None
    body = _recvn(sock, n)
    if body is None:
        return None
    try:
        return json.loads(body.decode())
    except (ValueError, UnicodeDecodeError):
        return None             # malformed frame — drop it, don't crash the node


# --------------------------- coordinator ---------------------------
class Coordinator:
    """Hosts the scheduler/registry and serves nodes over TCP."""

    def __init__(self, scheduler, host: str = "127.0.0.1", port: int = 0):
        self.scheduler = scheduler
        self.registry = scheduler.registry
        self.host = host
        self.port = port
        self._lock = threading.Lock()
        self._srv: socket.socket | None = None
        self._running = False

    def start(self) -> int:
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind((self.host, self.port))
        self._srv.listen(32)
        self.port = self._srv.getsockname()[1]
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        return self.port

    def submit(self, payload: str, **kw) -> str:
        with self._lock:
            return self.scheduler.submit(payload, **kw)

    def _accept_loop(self) -> None:
        while self._running:
            try:
                conn, _ = self._srv.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        with conn:
            while self._running:
                msg = recv_msg(conn)
                if msg is None:
                    break
                reply = self._process(msg)
                if reply is not None:
                    try:
                        send_msg(conn, reply)
                    except OSError:
                        break

    def _process(self, msg: dict) -> dict | None:
        mt = msg.get("type")
        with self._lock:
            if mt == "register":
                self.registry.register(msg["node_id"])
                return {"type": "registered"}
            if mt == "heartbeat":
                self.registry.heartbeat(msg["node_id"])
                return {"type": "ok"}
            if mt == "pull":
                nid = msg["node_id"]
                self.registry.heartbeat(nid)
                self.scheduler.dispatch()
                for u in self.scheduler.pending_units():
                    if nid in u.assigned and nid not in u.results:
                        return {"type": "work", "unit_id": u.unit_id, "payload": u.payload}
                return {"type": "idle"}
            if mt == "result":
                self.scheduler.submit_result(msg["unit_id"], msg["node_id"], msg["result"])
                return {"type": "ack"}
        return {"type": "error", "reason": f"unknown: {mt}"}

    def stop(self) -> None:
        self._running = False
        try:
            self._srv.close()
        except OSError:
            pass


# ----------------------------- node agent -----------------------------
class NodeAgent:
    """A node that connects to a Coordinator over TCP and does work."""

    def __init__(self, node_id: str, host: str, port: int, worker):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.worker = worker      # object with .run(payload) -> result
        self.sock: socket.socket | None = None
        self.completed = 0

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port))
        send_msg(self.sock, {"type": "register", "node_id": self.node_id})
        recv_msg(self.sock)

    def _pull_once(self) -> bool:
        send_msg(self.sock, {"type": "pull", "node_id": self.node_id})
        msg = recv_msg(self.sock)
        if not msg or msg.get("type") != "work":
            return False
        result = self.worker.run(msg["payload"])
        send_msg(self.sock, {"type": "result", "unit_id": msg["unit_id"],
                             "node_id": self.node_id, "result": result})
        recv_msg(self.sock)  # ack
        self.completed += 1
        return True

    def run(self, max_pulls: int = 50, idle_wait: float = 0.02) -> None:
        import time
        self.connect()
        did = False
        for _ in range(max_pulls):
            if self._pull_once():
                did = True
            elif did:
                break
            else:
                time.sleep(idle_wait)
        self.close()

    def close(self) -> None:
        try:
            self.sock.close()
        except (OSError, AttributeError):
            pass
