#!/usr/bin/env python3
"""Generate an Ollama Modelfile that bakes the GUA persona + examples into a
custom model named `gua`. This is instruction-level customization (the weights
are unchanged), but it produces a real named model that knows it is GUA without
needing the system prompt injected at call time.

For true weight fine-tuning, see finetune_lora.py (needs a GPU).
Run: python training/finetune/make_modelfile.py  ->  writes Modelfile
Then: ollama create gua -f Modelfile
"""
from pathlib import Path

from make_dataset import SYSTEM, PAIRS  # noqa: E402  (same dir)

BASE = "llama3.2"
HERE = Path(__file__).resolve().parent


def build_modelfile() -> str:
    lines = [f"FROM {BASE}", "", f'SYSTEM """{SYSTEM}"""', ""]
    # few-shot examples (single-line only, so the Modelfile stays valid)
    shots = [(u, a) for (u, a) in PAIRS if "\n" not in a][:12]
    for user, assistant in shots:
        lines.append(f"MESSAGE user {user}")
        lines.append(f"MESSAGE assistant {assistant}")
    lines += ["", "PARAMETER temperature 0.6", "PARAMETER top_p 0.9"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    path = HERE / "Modelfile"
    path.write_text(build_modelfile(), encoding="utf-8")
    print(f"Wrote {path}")
    print("Next: ollama create gua -f training/finetune/Modelfile")
