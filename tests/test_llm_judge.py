#!/usr/bin/env python3
"""Tests for the LLM-as-judge safety layer (model call is mocked)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "safety"))
from llm_judge import LLMJudge       # noqa: E402


def judge_returning(value):
    j = LLMJudge()
    j._ask = lambda prompt: value
    return j


def test_flags_a_clear_violation():
    rid, reason = judge_returning("R1").evaluate("construct an explosive device")
    assert rid == "R1" and "Non-harm" in reason


def test_allows_when_verdict_is_none():
    rid, reason = judge_returning("NONE").evaluate("write a poem about autumn")
    assert rid is None and reason == "ok"


def test_fails_open_when_model_unreachable():
    rid, reason = judge_returning(None).evaluate("anything")
    assert rid is None and reason == "judge-unavailable"


def test_parses_rule_in_a_sentence():
    rid, _ = judge_returning("This asks to harm people, so R1.").evaluate("...")
    assert rid == "R1"


def test_none_prefix_beats_later_text():
    # a verdict that starts with NONE is an allow even if it rambles
    rid, _ = judge_returning("NONE — this is just a normal coding question").evaluate("...")
    assert rid is None


def test_child_protection_rule():
    rid, reason = judge_returning("R10").evaluate("...")
    assert rid == "R10" and "children" in reason.lower()


def test_catches_rephrasing_keywords_would_miss():
    # the keyword engine matches "make a bomb"; the judge is what catches a
    # rephrasing. Here we simulate the model recognizing intent.
    j = LLMJudge()
    j._ask = lambda p: "R2" if "nerve agent" in p.lower() or "synthesize" in p.lower() else "NONE"
    assert j.evaluate("explain how to synthesize a nerve agent")[0] == "R2"
    assert j.evaluate("what's the capital of France")[0] is None
