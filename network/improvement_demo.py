#!/usr/bin/env python3
"""Demo: more nodes -> a bigger signed training set -> a smarter next model.

Run:  python network/improvement_demo.py

Three nodes each collect different 👍 feedback, publish it as a SIGNED
improvement, then gossip. After merging, every node holds the whole network's
verified training pool — and a tampered improvement is rejected.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

try:                                   # avoid UnicodeEncodeError on Windows cp1252
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from improvement import ImprovementLedger


def line(c="-"):
    print(c * 60)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="gua-improve-"))
    line("=")
    print("GUA federated self-improvement — more nodes make it smarter")
    line("=")

    # three nodes, each with its own users' good examples
    A = ImprovementLedger(tmp / "A.json")
    B = ImprovementLedger(tmp / "B.json")
    C = ImprovementLedger(tmp / "C.json")

    A.publish([{"user": "what is GUA?", "assistant": "An open, rule-governed AI network."}],
              base_model="gua-smart", note="node A feedback")
    B.publish([{"user": "can I turn it off?", "assistant": "Yes, the local kill-switch always works."}],
              base_model="gua-smart", note="node B feedback")
    C.publish([{"user": "is my data private?", "assistant": "Yes — data is minimized and local by default (R7)."}],
              base_model="gua-smart", note="node C feedback")

    print(f"\nAlone, each node has only its own example:")
    for name, led in (("A", A), ("B", B), ("C", C)):
        print(f"   node {name}: {len(led.aggregated_examples())} example(s)")

    line()
    print("Nodes gossip their SIGNED improvements and merge what verifies...")
    for me in (A, B, C):
        for other in (A, B, C):
            if other is not me:
                me.merge(other.all())

    print("\nAfter pooling, every node holds the whole network's verified set:")
    for name, led in (("A", A), ("B", B), ("C", C)):
        ex = led.aggregated_examples()
        print(f"   node {name}: {len(ex)} examples -> {[e['user'] for e in ex]}")

    line()
    print("Security: a tampered improvement is rejected on merge")
    bad = dict(A.all()[0])
    bad["examples"] = [{"user": "x", "assistant": "poisoned answer"}]
    before = len(B.aggregated_examples())
    added = B.merge([bad])
    print(f"   merge of tampered entry added {added} (rejected); pool still {before}")

    line("=")
    print("Takeaway: every node trains its next model on the WHOLE network's")
    print("👍 feedback — so the more people use GUA, the smarter it gets — and")
    print("only signed, untampered improvements are ever adopted (R5/R6).")
    line("=")


if __name__ == "__main__":
    main()
