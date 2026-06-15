#!/usr/bin/env bash
# Resilience demo: kill nodes, the model survives (Linux/macOS).
cd "$(dirname "$0")"
python3 network/replication_demo.py
