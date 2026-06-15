#!/usr/bin/env python3
"""Smoke-test every endpoint the UI buttons call, against a running bridge.

Start GUA first (start_gua.bat), then run:  python webui/backend/smoke_test.py
It exercises each button's backend route and prints PASS/FAIL per endpoint, so
you can confirm the whole UI is wired correctly end to end.

Maps UI control -> endpoint:
  New chat            POST /conversations/new
  Switch conversation POST /conversations/switch  + GET /conversation
  Rename (✎/dblclick) POST /conversations/rename
  Delete (🗑)          POST /conversations/delete
  Send message        POST /chat            (only with --chat; needs a model)
  👍/👎 feedback        POST /feedback
  Improve from feedback POST /self_improve
  STOP / re-enable     POST /stop, POST /resume
  (memory reset)       POST /reset
  Live stats card      GET /status
  Nodes connected      GET /network
  Capabilities card    GET /capabilities
  Active rules card    GET /rules
  Memory               GET /memory
"""
import argparse
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8754"


def call(method, path, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", action="store_true", help="also test /chat (needs a model)")
    args = ap.parse_args()

    results = []

    def check(label, method, path, body=None, ok=lambda s, d: s == 200):
        s, d = call(method, path, body)
        passed = False
        try:
            passed = ok(s, d)
        except Exception:
            passed = False
        results.append((label, passed, f"{s}"))
        return d

    check("GET /status", "GET", "/status",
          ok=lambda s, d: s == 200 and "gua_version" in d)
    check("GET /capabilities", "GET", "/capabilities",
          ok=lambda s, d: s == 200 and "capabilities" in d)
    check("GET /network", "GET", "/network",
          ok=lambda s, d: s == 200 and "nodes_connected" in d)
    check("GET /rules", "GET", "/rules", ok=lambda s, d: s == 200 and "rules" in d)
    check("GET /memory", "GET", "/memory", ok=lambda s, d: s == 200)

    new = check("POST /conversations/new", "POST", "/conversations/new", {},
                ok=lambda s, d: s == 200 and "id" in d)
    cid = (new or {}).get("id", "")
    check("GET /conversations", "GET", "/conversations",
          ok=lambda s, d: s == 200 and "list" in d)
    check("POST /conversations/rename", "POST", "/conversations/rename",
          {"id": cid, "title": "Smoke test chat"}, ok=lambda s, d: s == 200 and d.get("ok"))
    check("POST /conversations/switch", "POST", "/conversations/switch",
          {"id": cid}, ok=lambda s, d: s == 200 and d.get("ok"))
    check("GET /conversation", "GET", "/conversation?id=" + cid,
          ok=lambda s, d: s == 200 and "turns" in d)
    check("POST /feedback", "POST", "/feedback",
          {"value": 1, "user": "smoke", "assistant": "smoke reply"},
          ok=lambda s, d: s == 200 and "feedback" in d)
    check("GET /self_improve", "GET", "/self_improve",
          ok=lambda s, d: s == 200 and "good_examples" in d)
    check("POST /stop", "POST", "/stop", {}, ok=lambda s, d: s == 200 and d.get("halted"))
    check("POST /resume", "POST", "/resume", {}, ok=lambda s, d: s == 200 and not d.get("halted"))
    check("POST /conversations/delete", "POST", "/conversations/delete",
          {"id": cid}, ok=lambda s, d: s == 200)

    if args.chat:
        check("POST /chat", "POST", "/chat", {"message": "Say hello in one word."},
              ok=lambda s, d: s == 200 and "reply" in d)

    print("\nGUA UI endpoint smoke test")
    print("=" * 48)
    ok_n = 0
    for label, passed, detail in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}  ({detail})")
        ok_n += 1 if passed else 0
    print("=" * 48)
    print(f"{ok_n}/{len(results)} endpoints OK")
    sys.exit(0 if ok_n == len(results) else 1)


if __name__ == "__main__":
    main()
