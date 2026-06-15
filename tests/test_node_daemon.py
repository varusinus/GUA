#!/usr/bin/env python3
"""Tests for the real cross-machine GUA node daemon (over actual TCP sockets)."""
import sys
from pathlib import Path

import pytest

NET = Path(__file__).resolve().parent.parent / "network"
sys.path.insert(0, str(NET))
from node_daemon import GuaNode, parse_peers      # noqa: E402
from blobstore import BlobStore, sha256_hex       # noqa: E402

HOST = "127.0.0.1"
MODEL = b"GUA-MODEL-WEIGHTS::" + bytes(range(256)) * 4


def _node(tmp, name, peers=None):
    n = GuaNode(name, host=HOST, port=0, data_dir=str(tmp / name), peers=peers)
    n.start()                                     # binds an ephemeral port
    return n


def test_parse_peers():
    assert parse_peers("1.2.3.4:9000, 5.6.7.8:9001") == [("1.2.3.4", 9000), ("5.6.7.8", 9001)]
    assert parse_peers("") == []


def test_two_nodes_federate_over_tcp(tmp_path):
    a = _node(tmp_path, "A")
    a.store.put("gua-model", MODEL, version=1)
    b = _node(tmp_path, "B")
    try:
        pulled = b.sync_from(HOST, a.port)        # B pulls the model from A
        assert pulled == 1
        assert b.store.get_by_key("gua-model") == MODEL
        assert (HOST, a.port) in b.peers          # B remembers its peer
    finally:
        a.stop(); b.stop()


def test_model_survives_seed_node_stop(tmp_path):
    a = _node(tmp_path, "A")
    a.store.put("gua-model", MODEL)
    b = _node(tmp_path, "B")
    b.sync_from(HOST, a.port)
    a.stop()                                      # seed node hits kill-switch
    # the model lives on B, and a brand-new node C can still get it from B
    c = _node(tmp_path, "C")
    try:
        pulled = c.sync_from(HOST, b.port)
        assert pulled == 1
        assert c.store.get_by_key("gua-model") == MODEL
    finally:
        b.stop(); c.stop()


def test_already_have_it_pulls_nothing(tmp_path):
    a = _node(tmp_path, "A")
    a.store.put("gua-model", MODEL)
    b = _node(tmp_path, "B")
    try:
        assert b.sync_from(HOST, a.port) == 1
        assert b.sync_from(HOST, a.port) == 0     # second sync: nothing new
    finally:
        a.stop(); b.stop()


def test_persistence_across_restart(tmp_path):
    d = tmp_path / "persist"
    s1 = BlobStore(str(d))
    s1.put("gua-model", MODEL, version=2)
    s2 = BlobStore(str(d))                        # "restart": same data dir
    assert s2.get_by_key("gua-model") == MODEL
    assert s2.list()["gua-model"]["version"] == 2


def test_integrity_rejects_tampered_blob(tmp_path):
    s = BlobStore(str(tmp_path / "intg"))
    good_sha = sha256_hex(MODEL)
    with pytest.raises(ValueError):
        s.put_blob(good_sha, MODEL + b"tampered", {"key": "gua-model", "version": 1})


def test_improvements_propagate_over_tcp(tmp_path):
    a = _node(tmp_path, "A")
    a.ledger.publish([{"user": "what is GUA?", "assistant": "An open AI network."}],
                     base_model="gua-smart", note="A")
    b = _node(tmp_path, "B")
    try:
        b.sync_from(HOST, a.port)                       # B pulls A's signed improvement
        assert len(b.ledger.all()) == 1
        assert len(b.ledger.aggregated_examples()) == 1
        assert b.ledger.aggregated_examples()[0]["user"] == "what is GUA?"
    finally:
        a.stop(); b.stop()


def test_ping_reports_model_count(tmp_path):
    import socket
    from transport import send_msg, recv_msg
    a = _node(tmp_path, "A")
    a.store.put("gua-model", MODEL)
    try:
        sock = socket.create_connection((HOST, a.port), timeout=5)
        send_msg(sock, {"type": "ping"})
        pong = recv_msg(sock)
        sock.close()
        assert pong["type"] == "pong" and pong["models"] == 1
    finally:
        a.stop()
