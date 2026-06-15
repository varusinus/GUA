#!/usr/bin/env python3
"""Merge the trained LoRA adapter back into the base model's weights, producing
a standalone fine-tuned model (HF format) ready to convert to GGUF for Ollama.

Run (after finetune_lora.py):
    python training/finetune/merge_lora.py     # -> training/finetune/gua-merged/
"""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADAPTER = HERE / "gua-lora"
MERGED = HERE / "gua-merged"
BASE_MODEL = os.environ.get("GUA_BASE_MODEL", "unsloth/Llama-3.2-3B-Instruct")


def main():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    if not ADAPTER.exists():
        raise SystemExit("Run finetune_lora.py first (no adapter found).")
    print(f"Loading base {BASE_MODEL} (full precision) to merge the adapter...")
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.float16, device_map="auto" if torch.cuda.is_available() else None)
    model = PeftModel.from_pretrained(base, str(ADAPTER))
    model = model.merge_and_unload()
    MERGED.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(MERGED, safe_serialization=True)
    AutoTokenizer.from_pretrained(BASE_MODEL).save_pretrained(MERGED)
    print(f"Merged model saved -> {MERGED}")
    print("Next: convert to GGUF and load into Ollama — see TRAINING.md.")


if __name__ == "__main__":
    main()
