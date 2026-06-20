#!/usr/bin/env python3
"""GUA node daemon — a REAL node that federates the model across machines.

Each node:
  * listens on TCP (host:port) and serves the models it holds,
  * on startup pulls any models it is missing from its bootstrap peers,
  * periodically re-syncs (gossip), so a model spreads to every node,
  * persists everything to disk, so stopping (kill-switch) and restarting keeps
    its copy — and the network keeps the model even if this node never returns.

This is real networking over sockets across processes / machines (not a
simulation). It is not yet full internet-scale P2P: peers are reached by
IP:port and you bootstrap from a known peer. libp2p + a DHT + NAT traversal
replace explicit peers later (see docs/DISTRIBUTED_DESIGN.md). Blob transfer is
base64-in-JSON for now; chunked streaming is the next hardening for multi-GB
weights.

Protocol (4-byte length prefix + JSON, from transport.py):
  list                       -> {manifest: {key: {version, sha256, size}}}
  get {sha}                  -> {blob, key, version, b64} | {missing}
  peers {peers:[...]}        -> {peers:[...]}            (gossip)
  ping                       -> {pong, node_id, models}

CLI:
  python network/node_daemon.py --port 9075 --data .gua-node/A \
        --seed-text "GUA model v1" --key gua-model
  python network/node_daemon.py --port 9076 --data .gua-node/B --peers 127.0.0.1:9075
"""
from __future__ import annotations

import base64
import socket
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transport import send_msg, recv_msg          # noqa: E402
from blobstore import BlobStore                    # noqa: E402
from improvement import ImprovementLedger          # noqa: E402


# abuse guards for the open port
MAX_BLOB_BYTES = 48 * 1024 * 1024      # largest model blob we accept from a peer
MAX_REQS_PER_CONN = 10000              # cap requests on one connection
MAX_IMPROVEMENTS_IN = 5000             # cap improvement entries processed per sync


def parse_peers(s: str | None) -> list[tuple[str, int]]:
    out = []
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        host, _, port = part.rpartition(":")
        out.append((host or "127.0.0.1", int(port)))
    return out


class GuaNode:
    def __init__(self, node_id: str, host: str = "0.0.0.0", port: int = 9075,
                 data_dir: str | None = None, peers=None, advertise: str | None = None):
        self.node_id = node_id
        self.host = host
        self.port = port
        # The address OTHER nodes should use to reach us (our public/LAN host:port).
        # Without it, a peer we dial can't dial us back or gossip us onward — so
        # this is what lets the mesh self-assemble from a single bootstrap node.
        self.advertise: tuple[str, int] | None = None
        if advertise:
            h, _, p = advertise.rpartition(":")
            self.advertise = (h or "127.0.0.1", int(p))
        self.store = BlobStore(data_dir or f".gua-node/{port}")
        self.ledger = ImprovementLedger(self.store.root / "improvements.json")
        self.peers: set[tuple[str, int]] = set(peers or [])
        self._srv: socket.socket | None = None
        self._running = False
        self._lock = threading.Lock()

    def _advertise_list(self) -> list:
        return [[self.advertise[0], self.advertise[1]]] if self.advertise else []

    # -- server -------------------------------------------------------------
    def start(self) -> int:
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind((self.host, self.port))
        self._srv.listen(32)
        self.port = self._srv.getsockname()[1]
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        return self.port

    def _accept_loop(self) -> None:
        while self._running:
            try:
                conn, _ = self._srv.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        served = 0
        with conn:
            while self._running and served < MAX_REQS_PER_CONN:
                msg = recv_msg(conn)
                if msg is None:        # closed, oversized, or malformed frame
                    break
                served += 1
                reply = self._process(msg)
                if reply is not None:
                    try:
                        send_msg(conn, reply)
                    except (OSError, ValueError):
                        break

    def _process(self, msg: dict) -> dict | None:
        mt = msg.get("type")
        if mt == "list":
            with self._lock:
                return {"type": "manifest", "manifest": self.store.list()}
        if mt == "get":
            sha = msg.get("sha", "")
            data = self.store.get_blob(sha)
            if data is None:
                return {"type": "missing", "sha": sha}
            key, ver = "", 1
            for k, m in self.store.list().items():
                if m["sha256"] == sha:
                    key, ver = k, m["version"]
                    break
            return {"type": "blob", "sha": sha, "key": key, "version": ver,
                    "b64": base64.b64encode(data).decode()}
        if mt == "peers":
            incoming = {(h, int(p)) for h, p in (msg.get("peers") or [])}
            with self._lock:
                self.peers |= incoming
                self.peers.discard((self.host, self.port))
                if self.advertise:
                    self.peers.discard(self.advertise)
                known = [[h, p] for h, p in self.peers] + self._advertise_list()
            return {"type": "peers", "peers": known}
        if mt == "improvements":
            with self._lock:
                return {"type": "improvements", "entries": self.ledger.all()}
        if mt == "ping":
            return {"type": "pong", "node_id": self.node_id,
                    "models": len(self.store.list()),
                    "improvements": len(self.ledger.all())}
        return {"type": "error", "reason": f"unknown: {mt}"}

    # -- client / sync ------------------------------------------------------
    def sync_from(self, host: str, port: int, timeout: float = 10.0) -> int:
        """Pull every model this node is missing from one peer. Returns count."""
        pulled = 0
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
        except OSError:
            return 0
        if (host, port) != (self.host, self.port):
            with self._lock:
                self.peers.add((host, port))     # remember who we federate with
        try:
            send_msg(sock, {"type": "list"})
            resp = recv_msg(sock) or {}
            manifest = resp.get("manifest", {})
            for key, m in manifest.items():
                sha = m["sha256"]
                if self.store.has(sha):
                    continue
                if m.get("size", 0) > MAX_BLOB_BYTES:
                    continue        # refuse oversized model blobs (abuse guard)
                send_msg(sock, {"type": "get", "sha": sha})
                blob = recv_msg(sock) or {}
                if blob.get("type") == "blob":
                    try:
                        data = base64.b64decode(blob["b64"])
                    except Exception:
                        continue
                    if len(data) > MAX_BLOB_BYTES:
                        continue
                    try:
                        self.store.put_blob(sha, data, {"key": blob["key"],
                                                        "version": blob["version"]})
                        pulled += 1
                    except ValueError:
                        pass        # corrupted/tampered — skip (integrity guard)
            # federated self-improvement: pull & verify-merge signed improvements
            send_msg(sock, {"type": "improvements"})
            imp = recv_msg(sock) or {}
            if imp.get("type") == "improvements":
                entries = (imp.get("entries", []) or [])[:MAX_IMPROVEMENTS_IN]
                with self._lock:
                    self.ledger.merge(entries)   # each is signature-verified inside
            # gossip: exchange peer lists. Include OUR advertised address so the
            # peer can reach us back and gossip us onward (mesh self-assembly).
            with self._lock:
                mine = [[h, p] for h, p in self.peers] + [[host, port]] + self._advertise_list()
            send_msg(sock, {"type": "peers", "peers": mine})
            got = recv_msg(sock) or {}
            with self._lock:
                for h, p in got.get("peers", []):
                    if (h, int(p)) != (self.host, self.port):
                        self.peers.add((h, int(p)))
        finally:
            sock.close()
        return pulled

    def sync_all(self) -> int:
        total = 0
        for host, port in list(self.peers):
            total += self.sync_from(host, port)
        return total

    def ping_peers(self, timeout: float = 2.0) -> list[dict]:
        """Return the peers that actually answer right now (real live count)."""
        live = []
        for host, port in list(self.peers):
            try:
                s = socket.create_connection((host, port), timeout=timeout)
                send_msg(s, {"type": "ping"})
                r = recv_msg(s) or {}
                s.close()
                if r.get("type") == "pong":
                    live.append({"host": host, "port": port,
                                 "node_id": r.get("node_id"), "models": r.get("models")})
            except OSError:
                pass
        return live

    def run_background(self, gossip_interval: float = 15.0) -> int:
        """Start serving + gossip in background threads (for embedding in the
        chat bridge). Returns the bound port."""
        self.start()

        def _loop():
            while self._running:
                try:
                    self.sync_all()
                except Exception:
                    pass
                time.sleep(gossip_interval)

        threading.Thread(target=_loop, daemon=True).start()
        return self.port

    def serve_forever(self, gossip_interval: float = 15.0) -> None:
        self.start()
        print(f"[{self.node_id}] listening on {self.host}:{self.port}  "
              f"data={self.store.root}  peers={sorted(self.peers)}")
        try:
            while True:
                pulled = self.sync_all()
                models = list(self.store.list())
                print(f"[{self.node_id}] models={models} peers={sorted(self.peers)}"
                      + (f"  (+{pulled} pulled)" if pulled else ""))
                time.sleep(gossip_interval)
        except KeyboardInterrupt:
            print(f"\n[{self.node_id}] kill-switch: stopping. Data kept at "
                  f"{self.store.root} — the network keeps the model via other nodes.")
            self.stop()

    def stop(self) -> None:
        self._running = False
        try:
            self._srv.close()
        except (OSError, AttributeError):
            pass


def _main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Run a GUA node that federates the model.")
    ap.add_argument("--id", default=None, help="node id (default: gua-<port>)")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=9075)
    ap.add_argument("--data", default=None, help="data dir (default .gua-node/<port>)")
    ap.add_argument("--peers", default="", help="bootstrap peers host:port,host:port")
    ap.add_argument("--seed-file", default=None, help="store this file as the model")
    ap.add_argument("--seed-text", default=None, help="store this text as the model")
    ap.add_argument("--key", default="gua-model", help="logical model name to seed")
    ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--sync-once", action="store_true",
                    help="pull from peers once and exit (no server)")
    args = ap.parse_args()

    node = GuaNode(args.id or f"gua-{args.port}", host=args.host, port=args.port,
                   data_dir=args.data, peers=parse_peers(args.peers))

    if args.seed_file:
        data = Path(args.seed_file).read_bytes()
        m = node.store.put(args.key, data, args.version)
        print(f"[seed] stored {args.key} v{m['version']} "
              f"sha={m['sha256'][:16]}… size={m['size']}B from {args.seed_file}")
    elif args.seed_text is not None:
        m = node.store.put(args.key, args.seed_text.encode(), args.version)
        print(f"[seed] stored {args.key} v{m['version']} sha={m['sha256'][:16]}…")

    if args.sync_once:
        pulled = node.sync_all()
        print(f"[{node.node_id}] pulled {pulled} model(s); now holds "
              f"{list(node.store.list())}")
        return

    node.serve_forever()


if __name__ == "__main__":
    _main()
