#!/usr/bin/env bash
# Build GUA on a bigger base model (Linux/macOS). Default qwen2.5:7b.
cd "$(dirname "$0")"
BASE="${GUA_SMART_BASE:-qwen2.5:7b}"
echo "Building gua-smart on base: $BASE"
if ! ollama list 2>/dev/null | grep -qi "${BASE%%:*}"; then
  echo "[!] $BASE not found. Run:  ollama pull $BASE"; exit 1
fi
( cd training/finetune && GUA_SMART_BASE="$BASE" python3 make_smart_gua.py ) || { echo "[!] failed to write Modelfile"; exit 1; }
ollama create gua-smart -f training/finetune/Modelfile.smart || { echo "[!] ollama create failed"; exit 1; }
echo "Done — gua-smart built on $BASE. Run ./start_gua.sh (auto-picks gua-smart)."
