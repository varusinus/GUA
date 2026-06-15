#!/usr/bin/env python3
"""GUA node-client reference prototype (Phase-1, policy state machine only).

This models the *consent / resource / kill-switch* logic from
docs/node-client-spec.md. It deliberately contains NO real P2P, sandbox, or
compute — those come later. What it does encode, and what is unit-tested, are
the non-negotiable invariants:

  1. No compute without explicit opt-in.
  2. Never exceed declared resource ceilings.
  3. stop() always works, immediately.
  4. Honors idle-only and pause-on-battery.

Environment signals (idle, on-battery, temperature) are injected so the logic
is testable without real hardware.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ResourcePolicy:
    max_cpu_percent: int = 25
    max_gpu_percent: int = 50
    max_ram_mb: int = 2048
    temp_limit_celsius: int = 80
    idle_only: bool = True
    pause_on_battery: bool = True


@dataclass
class Env:
    """Injected environment signals (real client reads these from the OS)."""
    is_idle: bool = True
    on_battery: bool = False
    temperature_c: int = 50


class GuaNode:
    STATES = {
        "offline", "online_idle", "computing",
        "paused_battery", "paused_thermal", "killed",
    }

    def __init__(self, policy: ResourcePolicy | None = None,
                 env_provider: Callable[[], Env] | None = None):
        self.policy = policy or ResourcePolicy()
        self._env_provider = env_provider or (lambda: Env())
        self.contributing = False     # opt-in flag; default OFF
        self.killed = False
        self.state = "offline"
        self.units_done = 0
        self.log: list[str] = []

    # ---- consent (opt-in) ----
    def enable_contribution(self) -> bool:
        if self.killed:
            self.log.append("enable refused: node is killed")
            return False
        self.contributing = True
        self.log.append("contribution ENABLED (opt-in)")
        self._recompute()
        return True

    def disable_contribution(self) -> None:
        self.contributing = False
        self.log.append("contribution DISABLED")
        self._recompute()

    # ---- kill-switch (always works) ----
    def stop(self) -> None:
        """Guaranteed local kill-switch. Halts everything, immediately."""
        self.killed = True
        self.contributing = False
        self.state = "killed"
        self.log.append("KILL-SWITCH engaged")

    def resume(self) -> None:
        self.killed = False
        self.state = "offline"
        self.log.append("kill-switch cleared")
        self._recompute()

    # ---- caps ----
    def set_policy(self, **kw) -> None:
        for k, v in kw.items():
            if not hasattr(self.policy, k):
                raise KeyError(f"unknown policy field: {k}")
            setattr(self.policy, k, v)
        self.log.append(f"policy updated: {kw}")
        self._recompute()

    def effective_cpu_percent(self) -> int:
        """CPU the node may use right now (0 unless actually computing)."""
        return self.policy.max_cpu_percent if self.state == "computing" else 0

    # ---- core state machine ----
    def tick(self) -> str:
        self._recompute()
        if self.state == "computing":
            self.units_done += 1
        return self.state

    def _recompute(self) -> None:
        if self.killed:
            self.state = "killed"
            return
        if not self.contributing:
            self.state = "offline"
            return
        env = self._env_provider()
        if self.policy.pause_on_battery and env.on_battery:
            self.state = "paused_battery"
            return
        if env.temperature_c >= self.policy.temp_limit_celsius:
            self.state = "paused_thermal"
            return
        if self.policy.idle_only and not env.is_idle:
            self.state = "online_idle"   # connected, standing by, not computing
            return
        self.state = "computing"

    def status(self) -> dict:
        return {
            "contributing": self.contributing,
            "killed": self.killed,
            "state": self.state,
            "cpu_percent": self.effective_cpu_percent(),
            "units_done": self.units_done,
        }


if __name__ == "__main__":
    node = GuaNode()
    print("fresh:", node.status())            # offline, not contributing
    node.enable_contribution()
    print("opted in (idle):", node.tick())     # computing
    node.stop()
    print("after kill:", node.status())        # killed, cpu 0
    print("enable while killed:", node.enable_contribution())  # False
