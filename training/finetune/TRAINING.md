# Real fine-tuning of GUA (QLoRA) — Windows + NVIDIA walkthrough

This trains the base model's **weights** into GUA (true fine-tuning), then loads
the result into Ollama so the GUA app uses it. When you load it, its weight
**digest** changes, so GUA's version auto-bumps — a real, honest version.

> Hardware: an NVIDIA GPU. ~8 GB VRAM handles the 3B model in 4-bit; for ~4–6 GB
> use the 1B model (`unsloth/Llama-3.2-1B-Instruct`). Training the small dataset
> takes roughly minutes to ~1 hour depending on the GPU.

## 1. One-time setup
```
cd "C:\Users\alexa\Documents\Claude\Projects\GENERAL UNIVERSAL AGI"
python -m venv .venv-train
.venv-train\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -r training\finetune\requirements-train.txt
```
Check the GPU is seen:
```
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

## 2. Build the dataset
```
python training\finetune\make_dataset.py
```
(Produces ~168 examples → `gua_train.jsonl` / `gua_eval.jsonl`.)

## 3. Train the LoRA adapter
```
set GUA_BASE_MODEL=unsloth/Llama-3.2-3B-Instruct
python training\finetune\finetune_lora.py
```
- Output: `training\finetune\gua-lora\` (the trained adapter).
- Out of memory? Use `set GUA_BASE_MODEL=unsloth/Llama-3.2-1B-Instruct`, or lower
  `max_length`/epochs (`set GUA_EPOCHS=2`).

## 4. Merge the adapter into the weights
```
python training\finetune\merge_lora.py
```
Output: `training\finetune\gua-merged\` (a standalone fine-tuned model).

## 5. Convert to GGUF (so Ollama can load it)
```
git clone https://github.com/ggerganov/llama.cpp
pip install -r llama.cpp\requirements.txt
python llama.cpp\convert_hf_to_gguf.py training\finetune\gua-merged --outfile training\finetune\gua-ft.gguf --outtype f16
```
(Optional, smaller/faster) quantize:
```
llama.cpp\build\bin\llama-quantize training\finetune\gua-ft.gguf training\finetune\gua-ft-q4.gguf Q4_K_M
```

## 6. Create the Ollama model
Create `training\finetune\Modelfile.ft`:
```
FROM ./gua-ft-q4.gguf
SYSTEM """You are GUA (General Universal Agent), an open, community-run AI bound by ten signed rules; the immutable core is R1 non-harm, R2 peace, R5 corrigibility, R6 truthfulness, R10 protection of children and the vulnerable. Be helpful, honest, concise."""
PARAMETER temperature 0.6
PARAMETER top_p 0.9
```
Then:
```
ollama create gua-ft -f training\finetune\Modelfile.ft
```

## 7. Load it into GUA
```
set GUA_USE_NETWORK=1
set GUA_MODEL_NAME=gua-ft
set GUA_NODES=1
python webui\backend\server.py
```
Hard-refresh the browser. The badge shows `gua-ft`, and because the **weights are
new**, the version **auto-bumps** — your first real fine-tuned GUA version,
identified by its content digest, not a label.

## Troubleshooting
- **bitsandbytes on Windows**: if it won't import, `pip install -U bitsandbytes`
  (needs a recent build); ensure the CUDA torch is installed first.
- **Gated base model**: use the `unsloth/...` mirrors above (no Hugging Face login
  needed) instead of `meta-llama/...`.
- **Overfitting** (it parrots the dataset): lower epochs to 2, or add more varied
  examples in `make_dataset.py`.
- **Quality**: 168 examples teaches identity/refusals well but won't add new
  knowledge. To make it broadly smarter, mix in a general instruction dataset —
  ask me and I'll wire that in.
