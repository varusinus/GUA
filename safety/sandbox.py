#!/usr/bin/env python3
"""GUA execution sandbox (Phase-1 reference).

Runs a work unit in an isolated child process with CPU-time and memory limits
and a wall-clock timeout, returning a structured ok/error result. This is the
safety boundary that lets a node run network-supplied work without that work
hogging the machine or crashing the node.

Two layers of protection:
  1. WHITELIST — nodes only run *named, pre-approved* task kinds (TASK_REGISTRY),
     never arbitrary code from the wire. This is the primary control.
  2. ISOLATION — each task runs in a separate process with resource limits
     (RLIMIT_CPU, RLIMIT_AS) and a timeout; a runaway or crashing task is
     killed without taking the node down.

Honest scope: this gives process isolation + resource caps. Full filesystem and
network isolation needs OS containers / namespaces / WASM — that is the next
hardening step (documented in safety/README.md). The whitelist already prevents
arbitrary code execution, which is the most important property today.
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing as mp

try:
    import resource           # Unix-only: lets us set CPU/memory rlimits
except ImportError:           # Windows has no `resource` module
    resource = None           # -> we fall back to process isolation + timeout only


# Whitelisted, deterministic task kinds. Deterministic so honest nodes agree
# (which is what makes majority-vote verification work).
TASK_REGISTRY = {
    "sha256":    lambda s: hashlib.sha256(s.encode()).hexdigest()[:16],
    "wordcount": lambda s: str(len(s.split())),
    "upper":     lambda s: s.upper(),
    "sum_range": lambda s: str(sum(range(int(s) + 1))),
}


def make_task(task: str, task_input: str) -> str:
    """Encode a work-unit payload the sandbox can run."""
    return json.dumps({"task": task, "input": task_input})


def _set_limits(cpu_seconds: int, mem_mb: int) -> None:
    if resource is None:          # Windows: no rlimits; rely on the wall-clock timeout
        return
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    if mem_mb:
        nbytes = mem_mb * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (nbytes, nbytes))
        except (ValueError, OSError):
            pass                  # some platforms disallow RLIMIT_AS; timeout still applies


def _child(task_name, task_input, cpu_seconds, mem_mb, q) -> None:
    try:
        _set_limits(cpu_seconds, mem_mb)
        fn = TASK_REGISTRY.get(task_name)
        if fn is None:
            q.put(("err", f"unknown task: {task_name}"))
            return
        q.put(("ok", fn(task_input)))
    except MemoryError:
        q.put(("err", "memory limit exceeded"))
    except Exception as e:  # noqa: BLE001 - sandbox must capture everything
        q.put(("err", f"{type(e).__name__}: {e}"))


def _run_inprocess(task_name: str, task_input: str, wall_timeout: float) -> dict:
    """Fallback for platforms without fork (Windows): run the whitelisted task in
    a worker thread with a wall-clock timeout. No process isolation/rlimits here —
    the WHITELIST (only named, pure, deterministic tasks) is the safety control,
    and full isolation needs OS containers (documented scope)."""
    import threading
    box = {}

    def work():
        fn = TASK_REGISTRY.get(task_name)
        if fn is None:
            box["r"] = ("err", f"unknown task: {task_name}")
        else:
            try:
                box["r"] = ("ok", fn(task_input))
            except Exception as e:  # noqa: BLE001
                box["r"] = ("err", f"{type(e).__name__}: {e}")

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(wall_timeout)
    if t.is_alive():
        return {"ok": False, "error": "timeout"}
    kind, payload = box.get("r", ("err", "no result"))
    return {"ok": True, "result": payload} if kind == "ok" else {"ok": False, "error": payload}


def run_sandboxed(task_name: str, task_input: str, cpu_seconds: int = 2,
                  mem_mb: int = 256, wall_timeout: float | None = None) -> dict:
    """Run a whitelisted task in an isolated process. Returns {ok, result|error}."""
    if wall_timeout is None:
        wall_timeout = cpu_seconds + 2.0
    try:
        ctx = mp.get_context("fork")     # fast, copy-on-write (Unix)
    except ValueError:
        return _run_inprocess(task_name, task_input, wall_timeout)   # Windows path
    q = ctx.Queue()
    p = ctx.Process(target=_child, args=(task_name, task_input, cpu_seconds, mem_mb, q))
    p.start()
    try:
        kind, payload = q.get(timeout=wall_timeout)
    except Exception:
        kind, payload = "err", "timeout"
    finally:
        if p.is_alive():
            p.terminate()
        p.join(timeout=1)
    return {"ok": True, "result": payload} if kind == "ok" else {"ok": False, "error": payload}


class SandboxWorker:
    """A node worker that runs each unit inside the sandbox.

    honest=False models a malicious node that tampers with the result.
    """

    def __init__(self, node_id: str, honest: bool = True, **limits):
        self.node_id = node_id
        self.honest = honest
        self.limits = limits

    def run(self, payload: str):
        spec = json.loads(payload)
        out = run_sandboxed(spec["task"], spec["input"], **self.limits)
        res = out["result"] if out["ok"] else f"ERROR:{out['error']}"
        return res if self.honest else "TAMPERED_" + str(res)[:6]


if __name__ == "__main__":
    print(run_sandboxed("sha256", "hello"))
    print(run_sandboxed("sum_range", "100"))
    print(run_sandboxed("nope", "x"))
