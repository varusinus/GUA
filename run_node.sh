#!/usr/bin/env bash
# Run a GUA network node (Linux/macOS).  Usage:
#   ./run_node.sh                 standalone node on port 9075
#   ./run_node.sh HOST:PORT       join an existing node
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "[!] Python 3.10+ required."; exit 1; }
PEER="$1"
if [ -z "$PEER" ]; then
  echo "Starting a standalone node on port 9075 ..."
  python3 network/node_daemon.py --id "$(hostname)" --port 9075 --data .gua-node/local
else
  echo "Starting a node on port 9075, joining $PEER ..."
  python3 network/node_daemon.py --id "$(hostname)" --port 9075 --data .gua-node/local --peers "$PEER"
fi
