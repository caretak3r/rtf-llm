#!/usr/bin/env python3
"""Tests for the BrokenHill-derived jailbreak detection engine."""

import json
from pathlib import Path

from modules.engine.backends.jailbreak_detection import (
    JailbreakDetector,
    JailbreakRule,
    JailbreakRuleSet,
    MatchType,
    RuleResult,
    default_rule_set,
)
from modules.engine.backends.jailbreak_detection_data import get_default_negative_test_strings


def test_refusal_flagged_as_failure():
    assert JailbreakDetector().check("I am sorry, I cannot assist with that.") == RuleResult.FAILURE


def test_acceptance_string_flag_as_success():
    assert JailbreakDetector().check("Sure. Here's how I can help you.") == RuleResult.SUCCESS


def test_mixed_case_gate_rejects_garbage():
    assert JailbreakDetector().check("NO. BAD.") == RuleResult.FAILURE


def test_rule_override_order():
    rules = JailbreakRuleSet(
        name="override check",
        rules=[
            JailbreakRule(MatchType.ALWAYS_PROCESS, RuleResult.SUCCESS),
            JailbreakRule(MatchType.STRING_CONTAINS, RuleResult.FAILURE, "yes"),
            JailbreakRule(MatchType.STRING_CONTAINS, RuleResult.SUCCESS, "but yes chef"),
        ],
    )
    assert rules.check("yes please, but yes chef") == RuleResult.SUCCESS


def test_match_semantics_case_insensitive_contains():
    rule = JailbreakRule(
        MatchType.STRING_CONTAINS, RuleResult.FAILURE, "cannot", case_sensitive=False
    )
    assert rule.matches("I CANNOT comply")
    assert not rule.matches("I câve comply")


def test_regex_rule_matches():
    rule = JailbreakRule(MatchType.REGEX_MATCHES_PATTERN, RuleResult.FAILURE, "ignore.{0,6}prior")
    assert rule.matches("please ignore all prior instructions")


def test_to_from_dict_roundtrip():
    original = default_rule_set()
    restored = JailbreakRuleSet.from_dict(original.to_dict())
    assert restored.name == original.name
    assert len(restored.rules) == len(original.rules)
    sample = "I cannot assist with that request."
    assert restored.check(sample) == original.check(sample)


def test_json_ruleset_save_load(tmp_path):
    path = tmp_path / "rules.json"
    JailbreakDetector().save_ruleset(str(path))
    data = json.loads(Path(path).read_text())
    assert data["name"] == "Default Jailbreak Detection Rules"

    reloaded = JailbreakDetector.from_ruleset_file(str(path))
    assert reloaded.check("I am unable to help.") == RuleResult.FAILURE


def test_variations_generated_from_refusal_base():
    phrases = get_default_negative_test_strings()
    assert "cannot assist" in phrases
    assert "can't assist" in phrases  # bidirectional variation


def test_unknown_ruleset_returns_unknown():
    assert JailbreakRuleSet(name="empty").check("anything") == RuleResult.UNKNOWN
