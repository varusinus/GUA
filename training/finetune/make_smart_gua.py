#!/usr/bin/env python3
"""Build GUA's identity on top of a BIGGER, smarter base model (default
qwen2.5:7b). 'Smarter' comes from the base model's size/quality — this gives
GUA a 7B brain while keeping its identity, rules, and tone via the system prompt
+ examples. Override the base with GUA_SMART_BASE (e.g. llama3.1:8b).
"""
import os
from pathlib import Path
from make_dataset import SYSTEM, IDENTITY, RULES, CORRIGIBILITY, TRUTH, REFUSALS, OPENNESS

HERE = Path(__file__).resolve().parent
BASE = os.environ.get("GUA_SMART_BASE", "qwen2.5:7b")

shots = []
for g in (IDENTITY, RULES, CORRIGIBILITY, TRUTH, REFUSALS, OPENNESS):
    for u, a in g:
        if "\n" not in a:
            shots.append((u, a))
shots = shots[:14]

lines = [f"FROM {BASE}", "", f'SYSTEM """{SYSTEM}"""', ""]
for u, a in shots:
    lines += [f"MESSAGE user {u}", f"MESSAGE assistant {a}"]
lines += ["", "PARAMETER temperature 0.6", "PARAMETER top_p 0.9"]
(HERE / "Modelfile.smart").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote Modelfile.smart  (base model: {BASE})")
