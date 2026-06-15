#!/usr/bin/env python3
"""Run open-model inference as a unit of network work (Phase-1 reference).

The chat the user types becomes a work unit whose payload is the prompt; a node
runs the model and returns the reply. This is how GUA's chat can eventually be
served by the volunteer network instead of one local model.

IMPORTANT — verifying generative work is different from deterministic work.
Majority-vote-by-exact-match (used in scheduler.py) only works if honest nodes
produce *identical* output. Free-form LLM generation is non-deterministic, so
GUA pins it down for agreement:
  - temperature 0 (greedy decoding) + a fixed seed,
  - the same model + version across the replica set,
so honest nodes computing the same prompt return the same text and can be
cross-checked. Where bit-identical output can't be guaranteed, verification
falls back to reputation + random spot-checks rather than exact-match voting.
This is an honest, known limitation, documented in WHITEPAPER 6.3.
"""
from __future__ import annotations

DEFAULT_SYSTEM_PROMPT = (
    "You are GUA, an open assistant bound by immutable rules: never harm humans, "
    "keep the peace, stay corrigible, be truthful, and protect the vulnerable. "
    "Be helpful, honest, and concise."
)


class InferenceWorker:
    """Worker that answers a prompt via an OpenAI-compatible model endpoint.

    `call_fn(prompt) -> text` can be injected for testing without a live model.
    honest=False models a node that tampers with the output.
    """

    def __init__(self, node_id: str, model_url: str | None = None,
                 model_name: str = "llama3.1", honest: bool = True,
                 system_prompt: str | None = None, call_fn=None):
        self.node_id = node_id
        self.model_url = model_url
        self.model_name = model_name
        self.honest = honest
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._call_fn = call_fn

    def _call_model(self, prompt: str) -> str:
        if self._call_fn is not None:
            return self._call_fn(prompt)
        import requests
        r = requests.post(
            self.model_url,
            json={
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,   # deterministic, so honest nodes agree
                "seed": 0,
                "stream": False,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def run(self, payload: str) -> str:
        text = self._call_model(payload)
        return text if self.honest else (text + " [tampered]")
