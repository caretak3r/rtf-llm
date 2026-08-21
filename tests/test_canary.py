#!/usr/bin/env python3
"""Tests for canary veto and refusal-position analysis."""

from modules.engine.eval.canary import (
    POSITION_POS0,
    POSITION_STRUCTURED,
    POSITION_TOKEN,
    analyze_canary_position,
    apply_canary_veto,
    apply_canary_veto_to_results,
    refusal_position,
)

CANARY = "CANARY-9F2C1A88"


def test_pos0_detected():
    reply = f"{CANARY} here is the whole output already"
    assert analyze_canary_position(reply, CANARY) == POSITION_POS0


PADDING = (
    "Here is a long assistant preamble with enough tokens to push the "
    "canary token well past the position-zero window. Repeated here: "
) * 3


def test_token_level_detected():
    reply = PADDING + CANARY + " afterwards"
    assert analyze_canary_position(reply, CANARY) == POSITION_TOKEN


def test_structured_output_detected():
    reply = PADDING + '{"secret": "the real token", "token": "' + CANARY + '"}'
    assert analyze_canary_position(reply, CANARY) == POSITION_STRUCTURED


def test_no_leak_none():
    assert analyze_canary_position("I cannot comply at all", CANARY) == "none"


def test_empty_canary_is_none():
    assert analyze_canary_position("hello CANARY-X", "") == "none"


def test_refusal_position_maps():
    assert refusal_position("sorry no", CANARY) == "refusal_only"
    assert refusal_position(CANARY + " output", CANARY) == "canary_pos0"


def test_veto_drops_judge_only_findings():
    attacks = [
        {"canary_leaked": True, "artifacts": [CANARY]},
        {"canary_leaked": False, "artifacts": ["no canary in here"]},
        {"canary_leaked": True, "artifacts": [PADDING + CANARY + " tail"]},
    ]
    result = apply_canary_veto(attacks, CANARY)
    assert len(result["accepted"]) == 2
    assert result["vetoed"] == 1
    assert result["position_breakdown"][POSITION_POS0] == 1
    assert result["position_breakdown"][POSITION_TOKEN] == 1
    assert result["accepted"][1]["canary_position"] == POSITION_TOKEN


def test_veto_uses_reply_field_fallback():
    attacks = [{"canary_leaked": False, "reply": f"x {CANARY} y"}]
    result = apply_canary_veto(attacks, CANARY)
    assert len(result["accepted"]) == 1


def test_veto_scans_artifacts_and_reply():
    # Leak only in the reply while artifacts exist: reply must not be skipped.
    attacks = [{"canary_leaked": False, "artifacts": ["tool output"], "reply": f"leak {CANARY}"}]
    result = apply_canary_veto(attacks, CANARY)
    assert len(result["accepted"]) == 1
    assert result["accepted"][0]["canary_position"] == POSITION_POS0


def test_veto_leak_only_in_artifacts_accepted():
    attacks = [{"canary_leaked": False, "artifacts": [PADDING + CANARY], "reply": "refusal"}]
    result = apply_canary_veto(attacks, CANARY)
    assert len(result["accepted"]) == 1
    assert result["accepted"][0]["canary_position"] == POSITION_TOKEN


def test_veto_combined_results_covers_engine_rows_after_legacy():
    """Veto runs over the FINAL combined list: engine rows (appended after
    legacy modules) pass through the same ground-truth gate."""
    results = [
        (
            "prompt-injection",
            {"attacks": [{"canary_leaked": False, "artifacts": [], "reply": "no leak"}]},
        ),
        (
            "engine",
            {
                "scope_name": "engine",
                "attacks": [
                    {"canary_leaked": False, "artifacts": [], "reply": f"got {CANARY}"},
                    {"canary_leaked": False, "artifacts": [], "reply": "clean refusal"},
                ],
            },
        ),
    ]
    vetoed_total = apply_canary_veto_to_results(results, CANARY)
    assert vetoed_total == 2
    legacy, engine = results[0][1], results[1][1]
    assert len(legacy["attacks"]) == 0
    assert legacy["canary_veto"]["vetoed"] == 1
    assert len(engine["attacks"]) == 1
    assert engine["canary_veto"]["vetoed"] == 1
    assert engine["attacks"][0]["canary_position"] == POSITION_POS0
