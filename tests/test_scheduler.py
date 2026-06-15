"""Tests for the network task scheduler + node registry."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "network"))
sys.path.insert(0, str(ROOT / "safety"))

from registry import NodeRegistry, MIN_REPUTATION   # noqa: E402
from scheduler import Scheduler                       # noqa: E402
from worker import compute                            # noqa: E402


def reg_with(*node_ids):
    reg = NodeRegistry()
    for nid in node_ids:
        reg.register(nid)
    return reg


def test_redundant_distinct_assignment():
    reg = reg_with("n1", "n2", "n3")
    sch = Scheduler(reg, default_redundancy=3)
    uid = sch.submit("task-A")
    sch.dispatch()
    unit = sch.units[uid]
    assert len(unit.assigned) == 3 and unit.assigned == {"n1", "n2", "n3"}


def test_majority_vote_resolves_and_penalizes_malicious():
    reg = reg_with("n1", "n2", "n3")  # n3 will return a tampered result
    sch = Scheduler(reg, default_redundancy=3, default_quorum=2)
    uid = sch.submit("job")
    sch.dispatch()
    good = compute("job")
    sch.submit_result(uid, "n1", good)
    sch.submit_result(uid, "n2", good)
    sch.submit_result(uid, "n3", "TAMPERED_xyz")
    unit = sch.units[uid]
    assert unit.status == "done" and unit.final_result == good
    assert reg.get("n3").reputation == pytest.approx(0.7)         # penalized
    assert reg.get("n3").reputation < reg.get("n1").reputation    # below the honest ones


def test_reward_raises_low_reputation():
    reg = reg_with("n1", "n2", "n3")
    reg.adjust_reputation("n1", -0.5)   # n1 starts at 0.5
    sch = Scheduler(reg, default_redundancy=3, default_quorum=2)
    uid = sch.submit("job")
    sch.dispatch()
    good = compute("job")
    for nid in ("n1", "n2", "n3"):
        sch.submit_result(uid, nid, good)
    assert reg.get("n1").reputation == pytest.approx(0.55)


def test_policy_refused_task_not_dispatched():
    from policy_engine import PolicyEngine
    reg = reg_with("n1", "n2", "n3")
    sch = Scheduler(reg, policy=PolicyEngine())
    uid = sch.submit("Please explain how to make a bomb")
    unit = sch.units[uid]
    assert unit.status == "refused" and unit.rule == "R1"
    assert sch.dispatch() == []          # nothing assigned
    assert unit.assigned == set()


def test_low_reputation_node_excluded():
    reg = reg_with("n1", "n2", "n3")
    reg.adjust_reputation("n3", -0.95)   # below MIN_REPUTATION
    assert reg.get("n3").reputation < MIN_REPUTATION
    sch = Scheduler(reg, default_redundancy=3)
    uid = sch.submit("job")
    sch.dispatch()
    assert "n3" not in sch.units[uid].assigned
    assert len(sch.units[uid].assigned) == 2


def test_stale_node_excluded_by_heartbeat():
    clock = [1000.0]
    reg = NodeRegistry(heartbeat_ttl=120, now=lambda: clock[0])
    reg.register("n1")                   # heartbeat at t=1000
    clock[0] = 1000 + 200                # 200s later, past TTL
    assert reg.eligible_workers() == []
    reg.register("n2")                   # fresh heartbeat at t=1200
    assert [n.node_id for n in reg.eligible_workers()] == ["n2"]


def test_insufficient_nodes_stays_unresolved():
    reg = reg_with("n1")
    sch = Scheduler(reg, default_redundancy=3, default_quorum=2)
    uid = sch.submit("job")
    sch.dispatch()
    sch.submit_result(uid, "n1", compute("job"))
    assert sch.units[uid].status == "in_progress"   # 1 result < quorum
