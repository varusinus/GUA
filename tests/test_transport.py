"""Tests for the real-socket transport: a job resolves over the wire."""
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "network"))
sys.path.insert(0, str(ROOT / "safety"))

from registry import NodeRegistry              # noqa: E402
from scheduler import Scheduler                 # noqa: E402
from worker import SimWorker, compute           # noqa: E402
from transport import Coordinator, NodeAgent    # noqa: E402


def _run_swarm(honest_flags):
    reg = NodeRegistry()
    sch = Scheduler(reg, default_redundancy=len(honest_flags), default_quorum=2)
    coord = Coordinator(sch)
    port = coord.start()
    uid = coord.submit("net-job")
    agents = [NodeAgent(f"n{i}", "127.0.0.1", port, SimWorker(f"n{i}", honest=h))
              for i, h in enumerate(honest_flags)]
    threads = [threading.Thread(target=a.run) for a in agents]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    coord.stop()
    return reg, sch, uid


def test_job_resolves_over_real_sockets():
    reg, sch, uid = _run_swarm([True, True, True])
    unit = sch.units[uid]
    assert unit.status == "done"
    assert unit.final_result == compute("net-job")


def test_malicious_node_penalized_over_the_wire():
    reg, sch, uid = _run_swarm([True, True, False])  # n2 malicious
    unit = sch.units[uid]
    assert unit.status == "done"
    assert unit.final_result == compute("net-job")          # honest majority wins
    assert reg.get("n2").reputation < reg.get("n0").reputation


def test_nodes_actually_registered_via_socket():
    reg, sch, uid = _run_swarm([True, True, True])
    assert {n.node_id for n in reg.all()} == {"n0", "n1", "n2"}
