#!/usr/bin/env bash
# Two real nodes federate the model over TCP (Linux/macOS).
cd "$(dirname "$0")"
echo "Starting node A (seed) on 9401 and node B (joins A) on 9402..."
python3 network/node_daemon.py --id A --port 9401 --data .gua-node/A \
  --seed-text "GUA model v1 (demo seed)" --key gua-model &
A=$!
sleep 3
echo "Node B will pull the model from A. Press Ctrl+C to stop both."
trap "kill $A 2>/dev/null" EXIT
python3 network/node_daemon.py --id B --port 9402 --data .gua-node/B --peers 127.0.0.1:9401
