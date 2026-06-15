#!/usr/bin/env python3
"""Sign governance/ruleset.yaml with the founding ed25519 key.

The signature covers a canonical JSON serialization of the ruleset's semantic
content with the `signature` field emptied (and `public_key` set to the real
key). Comments and formatting in the YAML are preserved: only the two relevant
lines are rewritten in place.

Usage:
    python sign_ruleset.py --generate-key   # first time: create the keypair
    python sign_ruleset.py                   # sign (or re-sign) the ruleset

The private key is written to governance/keys/ (which is git-ignored).
Keep it secret — whoever holds it controls the ruleset signature.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

HERE = Path(__file__).resolve().parent
RULESET = HERE / "ruleset.yaml"
KEYDIR = HERE / "keys"
PRIV = KEYDIR / "founding_ed25519_private.pem"


def canonical_payload(text: str) -> bytes:
    """Canonical bytes that get signed: YAML -> dict, drop `signature`, sorted JSON."""
    data = yaml.safe_load(text)
    data.pop("signature", None)
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def load_or_make_key(generate: bool) -> Ed25519PrivateKey:
    if PRIV.exists():
        return serialization.load_pem_private_key(PRIV.read_bytes(), password=None)
    if not generate:
        sys.exit(f"No private key at {PRIV}. Run with --generate-key first.")
    KEYDIR.mkdir(exist_ok=True)
    key = Ed25519PrivateKey.generate()
    PRIV.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    PRIV.chmod(0o600)
    print(f"Generated new founding key -> {PRIV}")
    return key


def pub_hex(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return raw.hex()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate-key", action="store_true")
    args = ap.parse_args()

    key = load_or_make_key(args.generate_key)
    pk = pub_hex(key)

    text = RULESET.read_text()
    # 0) self-heal: if the top-level `signature:` line was lost (e.g. a truncated
    #    write), insert a placeholder so step 3 has something to fill. Without
    #    this the signer would silently no-op and leave the ruleset unsigned.
    if not re.search(r'(?m)^signature:\s*', text):
        if not text.endswith("\n"):
            text += "\n"
        text += '\nsignature: "REPLACE_WITH_SIGNATURE"\n'
    # 1) put the real public key in, so it is part of the signed content
    text = re.sub(r'(public_key:\s*).*', rf'\1"{pk}"', text, count=1)
    # 2) sign the canonical payload (signature field emptied)
    sig = key.sign(canonical_payload(text)).hex()
    # 3) write the signature back
    text = re.sub(r'(?m)^(signature:\s*).*$', rf'\1"{sig}"', text, count=1)

    RULESET.write_text(text)
    print(f"Signed {RULESET.name}")
    print(f"  public_key: {pk}")
    print(f"  signature:  {sig[:32]}…")


if __name__ == "__main__":
    main()
