#!/usr/bin/env bash
# Smoke-test every UI endpoint against a running bridge (Linux/macOS).
# Start GUA first (./start_gua.sh), then run this.
cd "$(dirname "$0")"
python3 webui/backend/smoke_test.py "$@"
