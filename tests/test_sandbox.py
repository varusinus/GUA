"""Tests for the execution sandbox."""
import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "safety"))

import sandbox  # noqa: E402

# RLIMIT-based CPU/memory enforcement only exists on Unix (the `resource` module).
# On Windows the sandbox falls back to whitelist + wall-clock timeout, so the
# rlimit-specific tests don't apply there.
needs_rlimit = pytest.mark.skipif(
    sandbox.resource is None,
    reason="resource rlimits unavailable on this platform (e.g. Windows)")


def test_normal_task_returns_correct_result():
    out = sandbox.run_sandboxed("sha256", "hello")
    assert out["ok"] and out["result"] == hashlib.sha256(b"hello").hexdigest()[:16]


def test_sum_range_task():
    out = sandbox.run_sandboxed("sum_range", "100")
    assert out["ok"] and out["result"] == "5050"


def test_unknown_task_errors():
    out = sandbox.run_sandboxed("does-not-exist", "x")
    assert not out["ok"] and "unknown task" in out["error"]


def test_crashing_task_is_captured():
    sandbox.TASK_REGISTRY["boom"] = lambda s: 1 / 0
    out = sandbox.run_sandboxed("boom", "x")
    assert not out["ok"] and "ZeroDivision" in out["error"]


@needs_rlimit
def test_cpu_timeout_is_killed():
    sandbox.TASK_REGISTRY["spin"] = lambda s: _spin()
    out = sandbox.run_sandboxed("spin", "x", cpu_seconds=1, wall_timeout=3)
    assert not out["ok"]   # killed by CPU limit / timeout, not a normal result


def _spin():
    while True:
        pass


@needs_rlimit
def test_memory_limit_enforced():
    sandbox.TASK_REGISTRY["hog"] = lambda s: bytearray(600 * 1024 * 1024)
    out = sandbox.run_sandboxed("hog", "x", mem_mb=256, wall_timeout=5)
    assert not out["ok"]   # exceeds the address-space limit


def test_sandbox_backed_scheduler_resolves():
    """A unit is computed inside real sandboxes on 3 nodes, then majority-voted."""
    sys.path.insert(0, str(ROOT / "network"))
    from registry import NodeRegistry
    from scheduler import Scheduler
    from sandbox import SandboxWorker, make_task, run_sandboxed

    reg = NodeRegistry()
    for nid in ("s1", "s2", "s3"):
        reg.register(nid)
    sch = Scheduler(reg, default_redundancy=3, default_quorum=2)
    workers = {nid: SandboxWorker(nid, honest=(nid != "s3")) for nid in ("s1", "s2", "s3")}
    uid = sch.submit(make_task("sha256", "hello"))
    for unit_id, picks in sch.dispatch():
        for nid in picks:
            sch.submit_result(unit_id, nid, workers[nid].run(sch.units[unit_id].payload))
    unit = sch.units[uid]
    expected = run_sandboxed("sha256", "hello")["result"]
    assert unit.status == "done" and unit.final_result == expected
    assert reg.get("s3").reputation < reg.get("s1").reputation
