#!/usr/bin/env python3
"""Tests for the replicated, resilient model store."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "network"))
from replication import ReplicatedModelStore, ModelLost, sha256_hex


def make_store(n=5, rf=3):
    s = ReplicatedModelStore(replication_factor=rf)
    for i in range(1, n + 1):
        s.add_node(f"node{i}")
    return s


def test_put_replicates_to_rf_nodes():
    s = make_store(n=5, rf=3)
    m = s.put("model", b"weights", version=1)
    assert len(m.replicas) == 3
    assert len(s.replicas_alive("model")) == 3
    assert s.get("model") == b"weights"


def test_get_verifies_hash():
    s = make_store()
    m = s.put("model", b"abc")
    assert m.sha256 == sha256_hex(b"abc")
    assert s.integrity_ok("model")


def test_model_survives_killed_node():
    s = make_store(n=5, rf=3)
    s.put("model", b"weights")
    holders = s.replicas_alive("model")
    s.kill_node(holders[0])                     # one replica stops
    assert s.is_available("model")              # still served by the others
    assert s.get("model") == b"weights"


def test_killing_all_but_one_still_recoverable():
    s = make_store(n=5, rf=3)
    s.put("model", b"weights")
    while len(s.replicas_alive("model")) > 1:
        s.kill_node(s.replicas_alive("model")[0])
    assert len(s.replicas_alive("model")) == 1
    assert s.get("model") == b"weights"         # single survivor is enough


def test_model_lost_only_when_all_replicas_gone():
    s = make_store(n=3, rf=3)
    s.put("model", b"weights")
    for n in list(s.alive_nodes()):
        s.kill_node(n)
    assert not s.is_available("model")
    with pytest.raises(ModelLost):
        s.get("model")


def test_rebalance_restores_redundancy():
    s = make_store(n=5, rf=3)
    s.put("model", b"weights")
    # kill two replicas -> redundancy drops to 1
    for n in s.replicas_alive("model")[:2]:
        s.kill_node(n)
    assert len(s.replicas_alive("model")) == 1
    rep = s.rebalance("model")                   # heal onto surviving nodes
    assert rep["model"] == 3
    assert s.get("model") == b"weights"


def test_revived_node_rejoins_with_its_copy():
    s = make_store(n=3, rf=3)
    s.put("model", b"weights")
    victim = s.replicas_alive("model")[0]
    s.kill_node(victim)
    assert victim not in s.replicas_alive("model")
    s.revive_node(victim)
    assert victim in s.replicas_alive("model")   # retained its copy


def test_wiped_node_is_survived():
    s = make_store(n=5, rf=3)
    s.put("model", b"weights")
    gone = s.replicas_alive("model")[0]
    s.wipe_node(gone)                            # permanent loss of that node
    assert s.get("model") == b"weights"
    assert gone not in s.alive_nodes()


def test_rebalance_cannot_resurrect_fully_lost_model():
    s = make_store(n=2, rf=2)
    s.put("model", b"weights")
    for n in list(s.alive_nodes()):
        s.wipe_node(n)
    assert s.rebalance("model")["model"] == 0    # honestly reports total loss
