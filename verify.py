#!/usr/bin/env python3
"""Clean-clone verification — confirm a fresh checkout actually works.

Run after `pip install -r requirements.txt` (the verify.sh / verify.bat wrappers
do that for you):

    python verify.py

It runs the same checks CI runs, plus the offline demos, and prints a single
PASS/FAIL summary. Use it before publishing, and tell new contributors to run it
after cloning so their first experience is "it just works."
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


_TEST_OUTPUT = ""


def run(label, cmd, capture=False):
    global _TEST_OUTPUT
    print(f"\n=== {label} ===", flush=True)
    try:
        if capture:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            out = (r.stdout or "") + (r.stderr or "")
            print(out, flush=True)
            _TEST_OUTPUT = out
            (ROOT / "test_output.txt").write_text(out, encoding="utf-8")
            return r.returncode == 0
        return subprocess.run(cmd, cwd=ROOT).returncode == 0
    except FileNotFoundError as e:
        print(f"[!] {e}")
        return False


STEPS = [
    ("Install deps into THIS interpreter (pytest, etc.)",
     [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"], False),
    ("Sign ruleset (generates a local key)", [sys.executable, "governance/sign_ruleset.py", "--generate-key"], False),
    ("Verify ruleset signature", [sys.executable, "governance/verify_ruleset.py"], False),
    ("Run the test suite", [sys.executable, "-m", "pytest", "-q"], True),
    ("Resilience demo (model survives node kill)", [sys.executable, "network/replication_demo.py"], False),
    ("Federated self-improvement demo", [sys.executable, "network/improvement_demo.py"], False),
]


def main():
    results = [(label, run(label, cmd, cap)) for label, cmd, cap in STEPS]
    all_ok = all(ok for _, ok in results)

    lines = ["=" * 56, "CLEAN-CLONE VERIFICATION", "=" * 56]
    for label, ok in results:
        lines.append(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    lines.append("=" * 56)
    if all_ok:
        lines.append("ALL CHECKS PASSED - a fresh clone works. Safe to publish/run.")
    else:
        lines.append("SOME CHECKS FAILED - fix them before publishing.")
        lines.append("  (If only model-dependent items failed, install Ollama and")
        lines.append("   pull a model; the core checks above do not need a model.)")
    # if the test suite failed, include its output so one file tells the story
    test_ok = dict(results).get("Run the test suite", True)
    if not test_ok and _TEST_OUTPUT:
        tail = "\n".join(_TEST_OUTPUT.splitlines()[-60:])
        lines += ["", "----- failing test output (also in test_output.txt) -----", tail]
    summary = "\n".join(lines)

    print("\n" + summary, flush=True)
    # also persist it, so the result survives even if the console window closes
    report = ROOT / "verify_report.txt"
    try:
        report.write_text(summary + "\n", encoding="utf-8")
        print(f"\nSaved this result to: {report}", flush=True)
    except Exception:
        pass
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
