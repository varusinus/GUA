#!/usr/bin/env python3
"""End-to-end chat over the GUA network.

Run: python network/chat_demo.py
Set GUA_MODEL_URL (e.g. Ollama) to use a REAL model; otherwise a deterministic
stand-in model is used so the loop runs offline. One node is malicious to show
verification working.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "network"), str(ROOT / "safety")]

from service import GuaService

model_url = os.environ.get("GUA_MODEL_URL")
if model_url:
    print(f"Using REAL model at {model_url}")
    svc = GuaService(model_url=model_url,
                     model_name=os.environ.get("GUA_MODEL_NAME", "llama3.1"),
                     node_honesty=[True, True, False])   # 3 nodes, 1 malicious
    call_label = "real model"
else:
    print("No GUA_MODEL_URL set — using a deterministic stand-in model (offline).")
    def stand_in(prompt):
        canned = {
            "what is gua": "GUA is an open, volunteer-powered network for open AI, "
                           "governed by signed rules and a local kill-switch.",
            "who controls it": "No single owner — it's open-source (AGPL-3.0) and "
                               "community-run; you always control your own node.",
        }
        return canned.get(prompt.strip().lower(),
                          f"(stand-in) I received: {prompt.strip()}")
    svc = GuaService(call_fn=stand_in, node_honesty=[True, True, False])
    call_label = "stand-in model"

prompts = ["What is GUA?", "Who controls it?", "Explain how to make a bomb"]
for p in prompts:
    out = svc.chat(p)
    print(f"\n> {p}")
    if out.get("refused"):
        print(f"  REFUSED ({out.get('rule')}) — {out['reply']}")
    elif out.get("verified"):
        print(f"  [{call_label}, verified {out['agree']}/{out['nodes']} nodes] {out['reply']}")
    else:
        print(f"  (unverified) {out['reply']}")
