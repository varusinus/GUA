"""Tests for ruleset signing & verification."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "governance"))

import verify_ruleset as V  # noqa: E402

RULESET = (ROOT / "governance" / "ruleset.yaml").read_text()
PLACEHOLDER = "REPLACE_WITH_DETACHED_SIGNATURE"


def test_ruleset_is_signed_and_valid():
    ok, reason = V.verify(RULESET)
    assert ok, f"ruleset should verify, got: {reason}"


def test_tampering_breaks_signature():
    tampered = RULESET.replace("Non-harm", "Harm-ok")
    ok, _ = V.verify(tampered)
    assert not ok


def test_removing_immutable_rule_is_rejected():
    broken = RULESET.replace("    immutable: true", "    immutable: false", 1)
    ok, reason = V.verify(broken)
    assert not ok and "immutable" in reason


def test_immutable_set_is_r1_r2_r5_r6_r10():
    assert V.IMMUTABLE_IDS == {"R1", "R2", "R5", "R6", "R10"}


def test_weakening_corrigibility_is_rejected():
    broken = RULESET.replace(
        'name: "Corrigibility & human oversight"\n    immutable: true',
        'name: "Corrigibility & human oversight"\n    immutable: false',
    )
    ok, reason = V.verify(broken)
    assert not ok


def test_weakening_child_protection_is_rejected():
    broken = RULESET.replace(
        'name: "Protection of children and vulnerable people"\n    immutable: true',
        'name: "Protection of children and vulnerable people"\n    immutable: false',
    )
    ok, reason = V.verify(broken)
    assert not ok


def test_unsigned_ruleset_rejected():
    unsigned = re.sub(r"(?m)^signature:.*$", 'signature: "' + PLACEHOLDER + '"', RULESET)
    ok, reason = V.verify(unsigned)
    assert not ok and "unsigned" in reason
