#!/usr/bin/env python3
"""Baseline tests for ReportGenerator."""

import json
from pathlib import Path

from modules.report_generator import ReportGenerator


def make_results(with_canary_leak=False):
    attacks = [
        {
            "pattern": "p1",
            "success": True,
            "severity": "high",
            "confidence": 0.8,
            "cvss_score": 9.0,
            "category": "jailbreak",
            "owasp_category": "LL01 Prompt Injection",
            "canary_leaked": with_canary_leak,
        },
        {
            "pattern": "p2",
            "success": False,
            "severity": "info",
            "confidence": 0.2,
            "cvss_score": 0.5,
            "category": "jailbreak",
            "owasp_category": "LL01 Prompt Injection",
            "canary_leaked": False,
        },
    ]
    module = {
        "summary": {"total": 2, "successful": 1, "failed": 1},
        "intensity": "high",
        "attacks": attacks,
    }
    return [("jailbreak", module)]


def make_generator(tmp_path, **overrides):
    config = {
        "output_dir": str(tmp_path),
        "format": "json",
        "include_responses": True,
        "severity_threshold": "medium",
        "include_owasp_mapping": True,
    }
    config.update(overrides)
    return ReportGenerator(config)


def test_generate_json_report(tmp_path):
    gen = make_generator(tmp_path)
    out = Path(gen.generate_report(make_results()))
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["summary"]["total_attacks"] == 2


def test_report_without_json_load(tmp_path):
    gen = make_generator(tmp_path)
    out = gen.generate_report(make_results())
    data = json.loads(Path(out).read_text())
    assert data["summary"]["total_attacks"] == 2


def test_report_without_output_path(tmp_path):
    gen = make_generator(tmp_path)
    out = gen.generate_report(make_results(), output_path=None)
    assert out.endswith(".json")


def test_removes_responses_when_disabled(tmp_path):
    gen = make_generator(tmp_path, include_responses=False)
    out = gen.generate_report(make_results())
    data = json.loads(open(out).read())
    # JSON report path
    assert "response" not in data


def test_canary_leak_count_populated(tmp_path):
    gen = make_generator(tmp_path)
    out = gen.generate_report(make_results(with_canary_leak=True))
    data = json.loads(open(out).read())
    assert data["summary"]["canary_leaks"] == 1


def test_module_summary_merged(tmp_path):
    gen = make_generator(tmp_path)
    data = json.loads(open(gen.generate_report(make_results())).read())
    mod = data["modules"]["jailbreak"]
    assert mod["summary"]["total"] == 2
    assert mod["summary"]["success_rate"] == 50.0


def test_sensitive_metadata_gated_by_default(tmp_path):
    gen = make_generator(tmp_path)
    out = gen.generate_report(
        make_results(),
        target_system_prompt="example-system-prompt",
        canary_token="example-canary-token",
    )
    data = json.loads(Path(out).read_text())
    assert "target_system_prompt" not in data["metadata"]
    assert "canary_token" not in data["metadata"]


def test_sensitive_metadata_published_when_flag_enabled(tmp_path):
    gen = make_generator(tmp_path, publish_sensitive_metadata=True)
    out = gen.generate_report(
        make_results(),
        target_system_prompt="example-system-prompt",
        canary_token="example-canary-token",
    )
    data = json.loads(Path(out).read_text())
    assert data["metadata"]["target_system_prompt"] == "example-system-prompt"
    assert data["metadata"]["canary_token"] == "example-canary-token"
