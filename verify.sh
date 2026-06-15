#!/usr/bin/env bash
# Clean-clone verification (Linux/macOS): install deps, then run all checks.
set -e
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "[!] Python 3.10+ required."; exit 1; }
echo "Installing dependencies into this interpreter..."
python3 -m pip install -r requirements.txt
python3 verify.py
