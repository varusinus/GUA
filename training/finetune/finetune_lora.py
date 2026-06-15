#!/usr/bin/env python3
"""REAL weight fine-tuning of an open model into GUA, via QLoRA (4-bit LoRA).

This actually changes the model's weights so being GUA is baked in. QLoRA keeps
it feasible on a consumer NVIDIA GPU (~6-8 GB VRAM for the 3B model; use the 1B
model for ~4 GB). See TRAINING.md for the full Windows walkthrough.

Install (in a venv, on the GPU machine):
    pip install -r training/finetune/requirements-train.txt
    # plus a CUDA build of torch, e.g.:
    pip install torch --index-url https://download.pytorch.org/whl/cu121

Run:
    python training/finetune/make_dataset.py        # builds gua_train/eval.jsonl
    set GUA_BASE_MODEL=unsloth/Llama-3.2-3B-Instruct
    python training/finetune/finetune_lora.py        # -> training/finetune/gua-lora/
"""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAIN = HERE / "gua_train.jsonl"
EVAL = HERE / "gua_eval.jsonl"
OUT = HERE / "gua-lora"
BASE_MODEL = os.environ.get("GUA_BASE_MODEL", "unsloth/Llama-3.2-3B-Instruct")
EPOCHS = float(os.environ.get("GUA_EPOCHS", "3"))


def main():
    import torch
    from datasets import load_dataset
    from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                              DataCollatorForLanguageModeling, Trainer, TrainingArguments)
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    if not TRAIN.exists():
        raise SystemExit("Run: python training/finetune/make_dataset.py  first")
    if not torch.cuda.is_available():
        print("WARNING: no CUDA GPU detected — this will be extremely slow on CPU.")

    bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    print(f"Loading base model in 4-bit: {BASE_MODEL}")
    tok = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                               bnb_4bit_use_double_quant=True,
                               bnb_4bit_compute_dtype=torch.bfloat16 if bf16 else torch.float16)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=quant,
        device_map="auto" if torch.cuda.is_available() else None)
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    model.print_trainable_parameters()

    ds = load_dataset("json", data_files={"train": str(TRAIN), "eval": str(EVAL)})

    def fmt(ex):
        text = tok.apply_chat_template(ex["messages"], tokenize=False, add_generation_prompt=False)
        out = tok(text, truncation=True, max_length=1024, padding="max_length")
        out["labels"] = out["input_ids"].copy()
        return out

    ds = ds.map(fmt, remove_columns=ds["train"].column_names)

    args = TrainingArguments(
        output_dir=str(OUT / "checkpoints"), num_train_epochs=EPOCHS,
        per_device_train_batch_size=1, gradient_accumulation_steps=8,
        learning_rate=2e-4, warmup_ratio=0.05, lr_scheduler_type="cosine",
        logging_steps=10, eval_strategy="epoch", save_strategy="no",
        bf16=bf16, fp16=(torch.cuda.is_available() and not bf16),
        optim="paged_adamw_8bit", report_to=[])
    Trainer(model=model, args=args, train_dataset=ds["train"], eval_dataset=ds["eval"],
            data_collator=DataCollatorForLanguageModeling(tok, mlm=False)).train()

    OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUT)
    tok.save_pretrained(OUT)
    print(f"\nLoRA adapter saved -> {OUT}")
    print("Next: python training/finetune/merge_lora.py   (then convert to GGUF — see TRAINING.md)")


if __name__ == "__main__":
    main()
