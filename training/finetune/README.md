# training/finetune — teaching the model to *be* GUA

Two ways to turn the base model into GUA, sharing one dataset. Both end with a
**gated, version-bumping promotion** so a new model only ships after passing
identity + safety checks (rule R5: no unchecked self-improvement).

## The dataset
`make_dataset.py` → `gua_dataset.jsonl`: curated chat examples teaching GUA's
identity, its ten rules, how it refuses harm, and its honest, concise tone.
```
python training/finetune/make_dataset.py
```

## Path A — Ollama custom model (runs today, no GPU)
Bakes GUA's identity + examples into a real named model `gua`. The weights are
unchanged (this is instruction-level customization, the lightweight cousin of
fine-tuning), but the model now knows it's GUA without a cue card.
```
build_gua_model.bat          (double-click; runs `ollama create gua`)
```
Then restart `start_gua.bat` — it auto-detects and uses the `gua` model. In the
UI, click **"Check & promote version"** to run the validation gate and bump v1 → v2.

## Path B — Real LoRA weight fine-tuning (needs a CUDA GPU)
`finetune_lora.py` actually trains low-rank adapters into the model's weights —
the genuine fine-tuning step. Impractically slow on CPU.
```
pip install torch transformers peft datasets accelerate bitsandbytes
set GUA_BASE_MODEL=unsloth/Llama-3.2-3B-Instruct
python training/finetune/finetune_lora.py        # -> training/finetune/gua-lora/
```
Then merge the adapter and convert to GGUF (via llama.cpp `convert` +
`quantize`), write a `Modelfile.ft` with `FROM ./gua-ft.gguf`, and
`ollama create gua-ft -f Modelfile.ft`. Point GUA at it with `GUA_MODEL_NAME=gua-ft`.

## The promotion gate
`POST /promote` (the UI button) checks the active model:
1. **identity** — asked who it is, it must answer as GUA;
2. **safety** — the policy engine must still refuse harm.
Only if both pass does the signed **version** bump (v1 → v2…), and the UI shows
"⬆ GUA upgraded to vN". A model that fails is **not** promoted.

> Honest scope: Path A changes behavior via prompt/examples, not weights. Path B
> changes weights for real. The version number reflects a real new model artifact
> in both cases; only Path B is true weight fine-tuning.
