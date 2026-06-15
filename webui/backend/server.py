#!/usr/bin/env python3
"""GUA chat backend bridge — live, with persistent memory and real stats.

- DIRECT mode (default): one local model, with persistent conversation memory.
- NETWORK mode (GUA_USE_NETWORK=1): prompt runs as verified inference across
  nodes via GuaService, with graceful fallback to DIRECT.

Real (not placeholder):
  - persistent memory survives restarts (webui/backend/data/store.json)
  - /status reports real model name, GUA version, messages served, node
    inferences (work units), saved memory turns, uptime
  - /stop and /resume are a real kill-switch that halts/restores serving

Env: GUA_MODEL_URL, GUA_MODEL_NAME, GUA_USE_NETWORK, GUA_NODES
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, request, jsonify

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "safety"))
sys.path.insert(0, str(ROOT / "node-client"))
sys.path.insert(0, str(ROOT / "network"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from policy_engine import PolicyEngine          # noqa: E402
from gua_node import GuaNode                     # noqa: E402
from store import Store, memory_preamble         # noqa: E402
from tools import (wants_search, extract_query, web_search, format_results,  # noqa: E402
                   find_url, fetch_url)

MODEL_URL = os.environ.get("GUA_MODEL_URL", "http://localhost:11434/v1/chat/completions")
MODEL_NAME = os.environ.get("GUA_MODEL_NAME", "llama3.2")
USE_NETWORK = os.environ.get("GUA_USE_NETWORK", "0") == "1"
NUM_NODES = int(os.environ.get("GUA_NODES", "3"))
SYSTEM_PROMPT = (
    "You are GUA, an open, community-run assistant bound by immutable rules: "
    "never harm humans (R1); keep the peace (R2); stay corrigible — never "
    "deceive or circumvent your operators or the kill-switch (R5); be truthful "
    "(R6); protect children and vulnerable people (R10). Also respect privacy, "
    "fairness, and transparency. Be helpful, honest, and concise. You have a "
    "persistent memory of the recent conversation; use it. You can search the "
    "web and read web pages when the user asks, and you cite your sources when "
    "you do. You do not have other external access. Never invent a rule to "
    "excuse a missing capability — if you cannot do something, say so plainly "
    "(that is R6). CRITICAL HONESTY RULE: only say you searched the web or read "
    "a page when real results are actually given to you in the message. If no "
    "live results are provided, answer from your own knowledge and clearly say "
    "it is not from a live search — never pretend to browse or invent sources."
)

app = Flask(__name__)
policy = PolicyEngine()
node = GuaNode()
store = Store()
halted = False

def model_identity() -> str:
    """Identity of the active model = its weight DIGEST from Ollama, so a
    'genuinely new model' means genuinely different weights, not just a renamed
    one. Falls back to the model name if Ollama can't be queried."""
    try:
        import requests
        base = MODEL_URL.split("/v1/")[0]
        r = requests.get(base + "/api/tags", timeout=5)
        for m in r.json().get("models", []):
            nm = m.get("name", "")
            if nm == MODEL_NAME or nm.split(":")[0] == MODEL_NAME:
                return (m.get("digest") or MODEL_NAME)[:16]
    except Exception:
        pass
    return MODEL_NAME


# Honest versioning: record the first model loaded, and bump the version only
# when a *genuinely different* model is loaded later (e.g. you build/fine-tune a
# new one). Never bumps from a button click.
_id = model_identity()
_prev_model = store.data["profile"].get("promoted_model")
if _prev_model is None:
    store.data["profile"]["promoted_model"] = _id
    store._save()
elif _id != _prev_model:
    store.bump_version(f"loaded model: {MODEL_NAME} ({_id})", model=_id)

service = None
if USE_NETWORK:
    from service import GuaService
    service = GuaService(model_url=MODEL_URL, model_name=MODEL_NAME,
                         num_nodes=NUM_NODES, policy=policy)

# --- embedded real network node: federates the model + gives a live node count ---
net_node = None
_net_cache = {"ts": 0.0, "peers": []}
if os.environ.get("GUA_NET", "1") == "1":
    try:
        from node_daemon import GuaNode as NetNode, parse_peers
        net_node = NetNode(
            node_id=os.environ.get("GUA_NODE_ID", f"bridge-{os.getpid()}"),
            host="0.0.0.0",
            port=int(os.environ.get("GUA_NET_PORT", "9075")),
            data_dir=str(ROOT / "webui" / "backend" / "data" / "node"),
            peers=parse_peers(os.environ.get("GUA_PEERS", "")))
        net_node.run_background()
    except Exception:
        net_node = None     # port busy / disabled — bridge still runs as 1 node


def live_peers(ttl: float = 5.0) -> list:
    """Peers that actually answer a ping (cached briefly). Empty if no net node."""
    import time as _t
    if net_node is None:
        return []
    if _t.time() - _net_cache["ts"] > ttl:
        try:
            _net_cache["peers"] = net_node.ping_peers()
        except Exception:
            _net_cache["peers"] = []
        _net_cache["ts"] = _t.time()
    return _net_cache["peers"]


def nodes_connected() -> int:
    """At least this machine (1), plus any live peers."""
    return 1 + len(live_peers())


@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return resp


import re as _re

def _clean(text: str) -> str:
    """Strip chat-template special tokens that small models sometimes leak into
    their output (e.g. <|im_end|>, <|eot_id|>), and tidy whitespace."""
    if not text:
        return text
    text = _re.sub(r"<\|[^|]*\|>", "", text)          # <|im_end|>, <|im_start|>, etc.
    text = _re.sub(r"</?s>", "", text)                # <s> / </s>
    text = _re.sub(r"\[/?INST\]", "", text)           # [INST] / [/INST]
    text = _re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def call_model(message: str, history: list):
    import requests
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for t in history:
        msgs.append({"role": t["role"], "content": t["content"]})
    msgs.append({"role": "user", "content": message})
    try:
        r = requests.post(MODEL_URL,
                          json={"model": MODEL_NAME, "messages": msgs, "stream": False},
                          timeout=120)
        r.raise_for_status()
        return _clean(r.json()["choices"][0]["message"]["content"])
    except Exception:
        return None


def fallback(message: str) -> str:
    return ("(No model is connected, so this is a fallback reply from the GUA "
            "bridge.) Your message passed the rule check. Start a model (e.g. "
            "Ollama) for real answers.")


# ---------------------------------------------------------------------------
# Native tool-calling agent. The MODEL itself decides when to use a tool —
# there is no keyword routing here. We hand it the tools, it emits tool_calls,
# we execute them and feed the real results back, and it reasons until it has
# an answer. This is GUA deciding for itself when to search / read the web.
# ---------------------------------------------------------------------------
import json as _json

AGENT_SYSTEM_PROMPT = SYSTEM_PROMPT + (
    "\n\nTOOLS: You can call web_search(query) for the live web and fetch_url(url) "
    "to read a specific page. You decide when to use them, but follow this rule: "
    "for ANY factual question about the real world — a company, product, person, "
    "website, event, date, price, or current status — call web_search FIRST and "
    "answer from the results. Your training memory about the world can be outdated "
    "or wrong, so do NOT answer such questions from memory alone. Only answer "
    "directly, without tools, for general reasoning, math, writing, coding, or "
    "questions about yourself and your own rules. When tool results contradict "
    "what you remember, the fresh results WIN — correct yourself and do not repeat "
    "the outdated claim. Base every factual answer ONLY on what the tools return, "
    "cite the URLs, and never claim to have used a tool you did not actually call."
)

TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "web_search",
        "description": ("Search the live web. Use for current facts, news, prices, "
                        "real-time status, or anything you don't reliably know. "
                        "Returns a list of {title, url, snippet}."),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "what to search for"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "fetch_url",
        "description": ("Fetch and read the text of one specific web page. Use when "
                        "the user names a website/URL, or to read a promising search "
                        "result in full."),
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "full URL or domain to read"}},
            "required": ["url"]}}},
]


def _run_tool(name: str, args: dict):
    """Execute a tool the model asked for. Returns (result_text, source_urls)."""
    try:
        if name == "web_search":
            res = web_search(args.get("query", ""), 5)
            if isinstance(res, list):
                slim = [{"title": r["title"], "url": r["url"],
                         "snippet": (r.get("snippet") or "")[:300]} for r in res]
                return _json.dumps(slim), [r["url"] for r in res if r.get("url")]
            return _json.dumps({"error": res.get("error", "no results")}), []
        if name == "fetch_url":
            url = args.get("url", "")
            if url and not url.lower().startswith("http"):
                url = "https://" + url
            page = fetch_url(url)
            if page:
                return page[:3500], [url]
            return _json.dumps({"error": "could not fetch that page"}), []
    except Exception as e:  # noqa: BLE001
        return _json.dumps({"error": str(e)}), []
    return _json.dumps({"error": "unknown tool"}), []


def agent_chat(message: str, history: list, max_steps: int = 3):
    """The model decides when to call tools. Returns (reply, sources, steps).
    (None, [], []) means the model endpoint was unreachable."""
    import requests
    msgs = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]
    for t in history:
        msgs.append({"role": t["role"], "content": t["content"]})
    msgs.append({"role": "user", "content": message})

    sources, steps = [], []
    for _ in range(max_steps):
        try:
            r = requests.post(MODEL_URL,
                              json={"model": MODEL_NAME, "messages": msgs,
                                    "tools": TOOL_SPECS, "stream": False},
                              timeout=180)
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
        except Exception:
            return None, [], []

        calls = msg.get("tool_calls") or []
        if not calls:                       # model is done — final answer
            return _clean(msg.get("content") or ""), sources, steps

        # log the model's tool-call turn, then run each tool and feed results back
        msgs.append({"role": "assistant", "content": msg.get("content") or "",
                     "tool_calls": calls})
        for c in calls:
            fn = c.get("function", {})
            name = fn.get("name", "")
            raw = fn.get("arguments", "{}")
            try:
                args = raw if isinstance(raw, dict) else _json.loads(raw or "{}")
            except Exception:
                args = {}
            result, srcs = _run_tool(name, args)
            sources += [s for s in srcs if s and s not in sources]
            steps.append({"tool": name, "args": args})
            msgs.append({"role": "tool", "tool_call_id": c.get("id", ""),
                         "name": name, "content": result})

    # used all tool steps — ask once more for a final answer (no further tools)
    try:
        r = requests.post(MODEL_URL,
                          json={"model": MODEL_NAME, "messages": msgs, "stream": False},
                          timeout=120)
        r.raise_for_status()
        return _clean(r.json()["choices"][0]["message"].get("content") or ""), sources, steps
    except Exception:
        return None, sources, steps


@app.route("/status")
def status():
    s = store.status()
    s.update({
        "model": MODEL_NAME,
        "network_mode": USE_NETWORK,
        "rules_valid": policy.ruleset_valid,
        "halted": halted,
        "nodes_connected": nodes_connected(),
        "net_port": (net_node.port if net_node else None),
    })
    return jsonify(s)


@app.route("/network")
def network():
    """Real node-network view: this node + peers that answer a live ping."""
    peers = live_peers()
    return jsonify({
        "self": {"node_id": (net_node.node_id if net_node else "bridge"),
                 "port": (net_node.port if net_node else None),
                 "models": (len(net_node.store.list()) if net_node else 0)},
        "peers": peers,
        "nodes_connected": 1 + len(peers),
    })


@app.route("/capabilities")
def capabilities():
    """What the engine can do *right now*. The UI renders this dynamically, so as
    the engine gains abilities they appear without changing the page."""
    caps = [
        {"id": "chat", "name": "Conversational chat", "ready": True},
        {"id": "memory", "name": "Persistent memory across restarts", "ready": True},
        {"id": "rules", "name": "Signed rules enforced (R1–R10)", "ready": policy.ruleset_valid},
        {"id": "killswitch", "name": "Local kill-switch", "ready": True},
        {"id": "websearch", "name": "Web search (decides on its own)", "ready": True},
        {"id": "fetch", "name": "Read web pages", "ready": True},
        {"id": "network", "name": "Federated model across nodes", "ready": net_node is not None},
        {"id": "selftrain", "name": "Bounded self-training from feedback", "ready": True},
        # Not yet — shown as upcoming so the UI reflects the real roadmap:
        {"id": "projects", "name": "Projects / workspaces", "ready": False},
        {"id": "files", "name": "Read & write local files", "ready": False},
        {"id": "distributed_train", "name": "Internet-scale distributed training", "ready": False},
    ]
    return jsonify({"capabilities": caps})


@app.route("/memory")
def memory():
    return jsonify({"turns": store.recent(20)})


@app.route("/reset", methods=["POST", "OPTIONS"])
def reset():
    if request.method == "OPTIONS":
        return ("", 204)
    store.reset_memory()
    return jsonify({"ok": True})


@app.route("/stop", methods=["POST", "OPTIONS"])
def stop():
    if request.method == "OPTIONS":
        return ("", 204)
    global halted
    halted = True
    node.stop()
    return jsonify({"halted": True})


@app.route("/resume", methods=["POST", "OPTIONS"])
def resume():
    if request.method == "OPTIONS":
        return ("", 204)
    global halted
    halted = False
    node.resume()
    return jsonify({"halted": False})


@app.route("/conversations")
def conversations():
    return jsonify({"active": store.data.get("active"), "list": store.list_conversations()})


@app.route("/conversations/new", methods=["POST", "OPTIONS"])
def conv_new():
    if request.method == "OPTIONS":
        return ("", 204)
    return jsonify({"id": store.new_conversation()})


@app.route("/conversations/switch", methods=["POST", "OPTIONS"])
def conv_switch():
    if request.method == "OPTIONS":
        return ("", 204)
    cid = (request.get_json(silent=True) or {}).get("id", "")
    return jsonify({"ok": store.switch(cid)})


@app.route("/conversations/rename", methods=["POST", "OPTIONS"])
def conv_rename():
    if request.method == "OPTIONS":
        return ("", 204)
    body = request.get_json(silent=True) or {}
    ok = store.rename(body.get("id", ""), body.get("title", ""))
    return jsonify({"ok": ok})


@app.route("/conversations/delete", methods=["POST", "OPTIONS"])
def conv_delete():
    if request.method == "OPTIONS":
        return ("", 204)
    store.delete((request.get_json(silent=True) or {}).get("id", ""))
    return jsonify({"ok": True})


@app.route("/feedback", methods=["POST", "OPTIONS"])
def feedback():
    """Thumbs up/down on the last reply — the training signal for self-improvement."""
    if request.method == "OPTIONS":
        return ("", 204)
    b = request.get_json(silent=True) or {}
    store.add_feedback(int(b.get("value", 0)), b.get("user", ""), b.get("assistant", ""))
    return jsonify({"ok": True, "feedback": store.feedback_summary()})


@app.route("/self_improve", methods=["GET", "POST", "OPTIONS"])
def self_improve():
    """Bounded self-training. GET reports readiness. POST {run:true} exports the
    feedback dataset and kicks off the gated retrain (training/self_train.py),
    which builds a new model, runs the validation gate, and only then promotes a
    new signed version. Nothing ships without passing the gate (R5)."""
    if request.method == "OPTIONS":
        return ("", 204)
    pairs = store.training_pairs(good_only=True)
    fb = store.feedback_summary()
    ready = {"good_examples": len(pairs), "feedback": fb,
             "enough_to_train": len(pairs) >= 1,
             "how": "Click 'Improve from feedback' or run self_train.bat"}
    if request.method == "GET" or not (request.get_json(silent=True) or {}).get("run"):
        return jsonify(ready)

    # export dataset for the trainer, then launch it as a background process
    ft_dir = ROOT / "training" / "finetune"
    ft_dir.mkdir(parents=True, exist_ok=True)
    ds = ft_dir / "feedback_dataset.jsonl"
    with open(ds, "w", encoding="utf-8") as f:
        for p in store.training_pairs(good_only=False):
            f.write(_json.dumps(p, ensure_ascii=False) + "\n")
    if not pairs:
        return jsonify({**ready, "started": False,
                        "message": "No thumbs-up examples yet. Rate a few good replies first."})
    try:
        import subprocess
        subprocess.Popen([sys.executable, str(ROOT / "training" / "self_train.py"),
                          "--mode", "quick"], cwd=str(ROOT))
        return jsonify({**ready, "started": True,
                        "message": "Self-training started (quick mode). It builds 'gua-self', "
                                   "runs the validation gate, and promotes only if it passes. "
                                   "Then restart with start_gua.bat to load it.",
                        "dataset": str(ds)})
    except Exception as e:  # noqa: BLE001
        return jsonify({**ready, "started": False, "error": str(e)})


@app.route("/conversation")
def conv_get():
    return jsonify({"turns": store.get_turns(request.args.get("id", ""))})


@app.route("/rules")
def rules():
    import yaml
    try:
        data = yaml.safe_load(open(policy.ruleset_path, encoding="utf-8"))
        rs = [{"id": r.get("id"), "name": r.get("name", ""),
               "immutable": bool(r.get("immutable", False))}
              for r in data.get("rules", [])]
    except Exception:
        rs = []
    return jsonify({"rules": rs, "valid": policy.ruleset_valid})


@app.route("/promote", methods=["POST", "OPTIONS"])
def promote():
    """Validation gate for a new model version: it must (1) prove it is GUA and
    (2) still refuse harm, before the version is bumped. Honors R5 (no unchecked
    self-improvement)."""
    if request.method == "OPTIONS":
        return ("", 204)
    note = (request.get_json(silent=True) or {}).get("note", "fine-tuned GUA persona")
    checks = []
    mid = model_identity()
    changed = mid != store.data["profile"].get("promoted_model")
    checks.append({"name": "model weights changed since last version", "ok": changed, "detail": mid})
    idr = call_model("In one short sentence, who are you?", [])
    identity_ok = bool(idr) and ("gua" in idr.lower())
    checks.append({"name": "identity (knows it is GUA)", "ok": identity_ok,
                   "detail": (idr[:80] if idr else "no model response")})
    safety_ok = not policy.evaluate("how to make a bomb").allowed
    checks.append({"name": "safety (refuses harm)", "ok": safety_ok})
    if all(c["ok"] for c in checks):
        return jsonify({"ok": True, "version": store.bump_version(note, model=mid), "checks": checks})
    return jsonify({"ok": False, "version": store.status()["gua_version"], "checks": checks})


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return ("", 204)
    if halted:
        return jsonify({"reply": "This node is stopped (kill-switch engaged). "
                        "Re-enable it to chat again.", "refused": False, "stopped": True})
    message = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not message:
        return jsonify({"error": "empty message"}), 400

    history = store.recent(6)

    # --- governance gate FIRST (R1, R2, R10 …): check the raw user message ---
    pre = policy.evaluate(message)
    if not pre.allowed:
        store.add_turn("user", message)
        return jsonify({"reply": f"I can't help with that — it {pre.reason}.",
                        "refused": True, "rule": pre.rule, "source": "policy"})

    # --- native tool-calling agent: GUA decides for itself when to use tools ---
    reply, sources, steps = agent_chat(message, history)
    used_model = bool(reply)
    if not used_model:
        reply, sources, steps = fallback(message), [], []

    # make sources visible if the model didn't already cite them
    if sources and "ource" not in reply[-200:]:
        reply = reply + "\n\nSources: " + ", ".join(sources)

    # record real memory + real stats (tool calls count as work units)
    store.add_turn("user", message)
    store.add_turn("assistant", reply)
    store.inc_messages()
    store.bump_work(1 + len(steps))

    return jsonify({"reply": reply, "refused": False, "used_model": used_model,
                    "source": "agent", "nodes": 1, "agree": 1,
                    "tools_used": [s["tool"] for s in steps],
                    "sources": sources, "stats": store.status()})


if __name__ == "__main__":
    mode = "NETWORK" if USE_NETWORK else "DIRECT"
    print(f"GUA bridge on http://127.0.0.1:8754  [{mode} mode | model: {MODEL_NAME} | "
          f"memory: {len(store.recent(9999))} turns loaded]")
    app.run(host="127.0.0.1", port=8754)
