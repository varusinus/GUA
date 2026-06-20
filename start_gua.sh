#!/usr/bin/env bash
# GUA launcher (Linux/macOS). Windows users: use start_gua.bat
set -e
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "[!] Python 3.10+ required."; exit 1; }

echo "Checking dependencies..."
python3 -m pip install -r requirements.txt >/dev/null 2>&1 || true

echo "Signing the ruleset with your local key..."
python3 governance/sign_ruleset.py --generate-key >/dev/null 2>&1 || true
python3 governance/verify_ruleset.py >/dev/null 2>&1 || python3 governance/sign_ruleset.py >/dev/null 2>&1
if python3 governance/verify_ruleset.py >/dev/null 2>&1; then echo "Ruleset: VALID and signed."; else echo "[!] WARNING: ruleset invalid — GUA will refuse all requests."; fi

# pick the best available model (weakest-to-strongest; last match wins)
MODEL=llama3.2
for m in "gua" "gua-ft" "gua-smart" "gua-self"; do
  ollama list 2>/dev/null | grep -qi "$m" && MODEL="$m"
done
echo "Using model: $MODEL"
export GUA_MODEL_NAME="$MODEL" GUA_USE_NETWORK=1 GUA_NODES=1 GUA_LLM_JUDGE=1

echo "Stopping any previous GUA servers..."
pkill -f "http.server 8000" 2>/dev/null || true
pkill -f "webui/backend/server.py" 2>/dev/null || true
sleep 1

echo "Starting the web interface and the model bridge..."
python3 -m http.server 8000 --directory webui >/dev/null 2>&1 &
sleep 1
( xdg-open http://127.0.0.1:8000/index.html >/dev/null 2>&1 || open http://127.0.0.1:8000/index.html >/dev/null 2>&1 ) || true
echo "GUA is running with model: $MODEL"
echo "(Refresh the browser with Ctrl+Shift+R if it doesn't update. Ctrl+C to stop.)"
python3 webui/backend/server.py
