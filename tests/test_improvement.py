#!/usr/bin/env python3
"""Tests for the federated (signed, propagating) self-improvement layer."""
import sys
from pathlib import Path

NET = Path(__file__).resolve().parent.parent / "network"
sys.path.insert(0, str(NET))
from improvement import ImprovementLedger, examples_hash      # noqa: E402

EX1 = [{"user": "what is GUA?", "assistant": "An open, rule-governed AI network."}]
EX2 = [{"user": "can I turn it off?", "assistant": "Yes — the local kill-switch always works."}]


def test_publish_and_verify(tmp_path):
    led = ImprovementLedger(tmp_path / "a.json")
    d = led.publish(EX1, base_model="gua-smart", note="v1")
    assert d["version"] == 1 and d["signature"]
    assert led.verify(d)


def test_tampered_examples_rejected(tmp_path):
    led = ImprovementLedger(tmp_path / "a.json")
    d = led.publish(EX1, base_model="gua-smart")
    d["examples"] = [{"user": "x", "assistant": "malicious"}]   # tamper
    assert not led.verify(d)


def test_tampered_note_rejected(tmp_path):
    led = ImprovementLedger(tmp_path / "a.json")
    d = led.publish(EX1, base_model="gua-smart", note="orig")
    d["note"] = "changed after signing"
    assert not led.verify(d)


def test_untrusted_signer_rejected(tmp_path):
    led = ImprovementLedger(tmp_path / "a.json")
    d = led.publish(EX1, base_model="gua-smart")
    # a ledger that trusts only some other key must reject this entry
    picky = ImprovementLedger(tmp_path / "b.json", trusted_pubkeys=["00" * 32])
    assert not picky.verify(d)


def test_merge_propagates_across_nodes(tmp_path):
    node_a = ImprovementLedger(tmp_path / "a.json")
    node_b = ImprovementLedger(tmp_path / "b.json")
    a1 = node_a.publish(EX1, base_model="gua-smart", note="from A")
    # B learns A's improvement by merging A's ledger
    added = node_b.merge(node_a.all())
    assert added == 1
    assert node_b.verify(a1)
    # merging again adds nothing (idempotent)
    assert node_b.merge(node_a.all()) == 0


def test_aggregated_examples_grow_with_more_nodes(tmp_path):
    a = ImprovementLedger(tmp_path / "a.json")
    b = ImprovementLedger(tmp_path / "b.json")
    a.publish(EX1, base_model="gua-smart")
    b.publish(EX2, base_model="gua-smart")
    # one node alone has 1 example
    assert len(a.aggregated_examples()) == 1
    # after pooling both nodes' improvements, it has 2 (more nodes -> bigger set)
    a.merge(b.all())
    pool = a.aggregated_examples()
    assert len(pool) == 2
    users = {p["user"] for p in pool}
    assert users == {"what is GUA?", "can I turn it off?"}


def test_aggregated_examples_dedup(tmp_path):
    a = ImprovementLedger(tmp_path / "a.json")
    b = ImprovementLedger(tmp_path / "b.json")
    a.publish(EX1, base_model="gua-smart")
    b.publish(EX1, base_model="gua-smart")     # same example, different node
    a.merge(b.all())
    assert len(a.aggregated_examples()) == 1   # deduped


def test_chain_parent_links(tmp_path):
    led = ImprovementLedger(tmp_path / "a.json")
    d1 = led.publish(EX1, base_model="gua-smart")
    d2 = led.publish(EX2, base_model="gua-smart")
    assert d2["parent"] == d1["id"] and d2["version"] == 2
