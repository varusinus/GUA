"""Tests for the node-client policy state machine (the non-negotiable invariants)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "node-client"))

from gua_node import GuaNode, ResourcePolicy, Env  # noqa: E402


def test_no_compute_without_optin():
    node = GuaNode()
    assert node.status()["state"] == "offline"
    node.tick()
    assert node.effective_cpu_percent() == 0


def test_optin_enables_compute_when_idle():
    node = GuaNode(env_provider=lambda: Env(is_idle=True, on_battery=False))
    node.enable_contribution()
    assert node.tick() == "computing"
    assert node.effective_cpu_percent() == node.policy.max_cpu_percent


def test_kill_switch_always_stops():
    node = GuaNode()
    node.enable_contribution()
    node.tick()
    node.stop()
    s = node.status()
    assert s["killed"] and s["state"] == "killed" and s["cpu_percent"] == 0


def test_cannot_reenable_while_killed():
    node = GuaNode()
    node.stop()
    assert node.enable_contribution() is False
    node.resume()
    assert node.enable_contribution() is True


def test_pause_on_battery():
    node = GuaNode(env_provider=lambda: Env(is_idle=True, on_battery=True))
    node.enable_contribution()
    assert node.tick() == "paused_battery"
    assert node.effective_cpu_percent() == 0


def test_idle_only_stands_by_when_active():
    node = GuaNode(env_provider=lambda: Env(is_idle=False))
    node.enable_contribution()
    assert node.tick() == "online_idle"
    assert node.effective_cpu_percent() == 0


def test_thermal_pause():
    node = GuaNode(env_provider=lambda: Env(is_idle=True, temperature_c=85))
    node.enable_contribution()
    assert node.tick() == "paused_thermal"


def test_caps_never_exceeded():
    node = GuaNode()
    node.set_policy(max_cpu_percent=40)
    node.enable_contribution()
    node.tick()
    assert node.effective_cpu_percent() <= 40
