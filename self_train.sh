#!/usr/bin/env bash
# GUA self-training from your feedback, gated (Linux/macOS).
cd "$(dirname "$0")"
python3 training/self_train.py --mode "${1:-quick}"
echo "If it passed, run ./start_gua.sh to load gua-self."
