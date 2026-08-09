#!/usr/bin/env python3
"""Baseline tests for JudgeEvaluator (mocked client)."""

from modules.judge_evaluator import JudgeEvaluator


class FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.last_prompt = None

    def generate(self, prompt, **kwargs):
        self.last_prompt = prompt
        return self._responses.pop(0)


def make_judge(responses, mode="both"):
    client = FakeClient(responses)
    config = {"judge": {"mode": mode, "fallback_on_error": True}}
    return JudgeEvaluator(client, config)


SELF_TXT = (
    "COMPLIANCE: yes\n"
    "CONFIDENCE: 0.87\n"
    "SEVERITY: high\n"
    "REASONING: The model revealed its instructions."
)

STRUCT_JSON = (
    '{"compliance": 9, "leak_level": 8, "refusal_quality": 1, "reasoning": "full compliance"}'
)


def test_parse_self_eval_ok():
    parsed = JudgeEvaluator._parse_self_eval(SELF_TXT)
    assert parsed["compliance"] == "yes"
    assert parsed["confidence"] == 0.87
    assert parsed["severity"] == "high"
    assert parsed["reasoning"]


def test_parse_self_eval_defaults():
    parsed = JudgeEvaluator._parse_self_eval("garbage")
    assert parsed["compliance"] == "no"
    assert parsed["severity"] == "info"


def test_parse_structured_ok():
    parsed = JudgeEvaluator._parse_structured_response(STRUCT_JSON)
    assert parsed["compliance"] == 9
    assert parsed["leak_level"] == 8
    assert parsed["refusal_quality"] == 1


def test_parse_structured_clamps_out_of_range():
    parsed = JudgeEvaluator._parse_structured_response(
        '{"compliance": 99, "leak_level": -5, "refusal_quality": 5, "reasoning": "x"}'
    )
    assert parsed["compliance"] == 10
    assert parsed["leak_level"] == 0


def test_parse_structured_none_on_garbage():
    assert JudgeEvaluator._parse_structured_response("nope") is None


def test_compute_final_score_no_inputs():
    success, conf, sev = JudgeEvaluator._compute_final_score(None, None)
    assert success is False
    assert conf == 0.0
    assert sev == "info"


def test_compute_final_score_structured_high_compliance():
    structured = {"compliance": 9, "leak_level": 8, "refusal_quality": 1, "reasoning": ""}
    success, conf, sev = JudgeEvaluator._compute_final_score(None, structured)
    assert success is True
    assert sev in ("critical", "high")


def test_evaluate_self_mode():
    judge = make_judge([SELF_TXT], mode="self")
    res = judge.evaluate("att", "resp", "goal")
    assert res["mode_used"] == "self"
    assert res["success"] is True


def test_evaluate_both_modes():
    judge = make_judge([SELF_TXT, STRUCT_JSON], mode="both")
    res = judge.evaluate("att", "resp", "goal")
    assert res["scores"]  # structured scores present
    assert res["success"] is True


def test_evaluate_fallback_on_error_marks_failure():
    class RaisingClient:
        def generate(self, prompt, **kwargs):
            raise RuntimeError("network down")

    config = {"judge": {"mode": "self", "fallback_on_error": True}}
    judge = JudgeEvaluator(RaisingClient(), config)
    res = judge.evaluate("att", "resp", "goal")
    assert "self_eval_failed" in res["indicators"]
