# webui/backend

A small bridge between the chat UI and a real open-weights model. The point of
this layer is GUA-specific: **every message and every model response is checked
against the rules (R1/R2)** by the [policy engine](../../safety/policy_engine.py)
before it reaches the user.

## Run

```bash
pip install -r ../../requirements.txt
python server.py          # serves http://127.0.0.1:8754
```

Then open `../index.html`. If the bridge is running, the chat uses it; if not,
the UI falls back to its built-in simulated replies. Either way the page works.

## Connect a real model

The bridge talks to any **OpenAI-compatible** `/chat/completions` endpoint:

```bash
# Example with Ollama:
ollama serve &
ollama pull llama3.1
export GUA_MODEL_URL="http://localhost:11434/v1/chat/completions"
export GUA_MODEL_NAME="llama3.1"
python server.py
```

Also works with LM Studio, llama.cpp server, vLLM, or any compatible gateway.
If the model is unreachable, the bridge returns a clearly-labelled fallback
reply instead of failing.

## Endpoints

- `GET /status` — node + ruleset + model status.
- `POST /chat` `{ "message": "..." }` — rule-checked chat. Returns `{reply, refused, rule, used_model}`.

## Why the rule check is here

This is the enforcement point from the [whitepaper](../../WHITEPAPER.md#52-policy-engine):
a refused request never reaches the model, and a rule-violating model output
never reaches the user. In Phase 1 this is a keyword stub; it upgrades to a
safety classifier without changing the interface.

## Phase 1 note

This reference bridge runs the model on a single local endpoint. The full GUA
design serves the model across the **volunteer network** (Petals-style swarm
inference); this bridge is the same `/chat` contract pointed at that network
instead of localhost.
