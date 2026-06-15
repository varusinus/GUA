#!/usr/bin/env python3
"""Verify the signature on governance/ruleset.yaml.

Returns exit code 0 if valid, 1 if not. Importable as a library:
    from verify_ruleset import verify
    ok, reason = verify(Path("ruleset.yaml").read_text())

Conforming nodes MUST call this before trusting a ruleset, and MUST reject
any change to an `immutable: true` rule (checked here too).
"""
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

RULESET = Path(__file__).resolve().parent / "ruleset.yaml"
IMMUTABLE_IDS = {"R1", "R2", "R5", "R6", "R10"}


def _canonical(data: dict) -> bytes:
    d = dict(data)
    d.pop("signature", None)
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def verify(text: str):
    """Return (ok: bool, reason: str)."""
    try:
        data = yaml.safe_load(text)
    except Exception as e:
        return False, f"ruleset is malformed: {e}"
    sig_hex = data.get("signature", "")
    pk_hex = data.get("signing", {}).get("public_key", "")

    if not sig_hex or sig_hex.startswith("REPLACE_"):
        return False, "ruleset is unsigned"
    if not pk_hex or pk_hex.startswith("REPLACE_"):
        return False, "no public key in ruleset"

    # Immutable-rule sanity: each immutable id must be present and marked immutable.
    by_id = {r.get("id"): r for r in data.get("rules", [])}
    for rid in IMMUTABLE_IDS:
        r = by_id.get(rid)
        if r is None:
            return False, f"immutable rule {rid} is missing"
        if not r.get("immutable", False):
            return False, f"rule {rid} must be immutable"

    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pk_hex))
        pub.verify(bytes.fromhex(sig_hex), _canonical(data))
    except (InvalidSignature, ValueError) as e:
        return False, f"signature invalid: {e}"
    return True, "ok"


def main() -> None:
    ok, reason = verify(RULESET.read_text())
    print(("VALID" if ok else "INVALID") + f": {reason}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
