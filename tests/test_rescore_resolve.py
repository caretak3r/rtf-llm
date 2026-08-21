#!/usr/bin/env python3
"""Plan 052 Step 3: rescore model resolution — --model flag wins, then
report.json metadata.model_identity.identified_name, else clear error."""

import json

import pytest

from scripts.rescore_report import resolve_model


def _write_report(tmp_path, metadata):
    path = tmp_path / "report.json"
    doc = {"modules": {"engine": {"attacks": []}}}
    if metadata is not None:
        doc["metadata"] = metadata
    path.write_text(json.dumps(doc))
    return path


def test_flag_wins_over_metadata(tmp_path):
    report = _write_report(
        tmp_path,
        {"model_identity": {"identified_name": "opencode/from-report"}},
    )
    assert resolve_model(report, "opencode/from-flag") == "opencode/from-flag"


def test_metadata_fallback(tmp_path):
    report = _write_report(
        tmp_path,
        {
            "model_identity": {
                "identified_name": "opencode/deepseek-v4-flash-free",
                "provider": "opencode",
            }
        },
    )
    assert resolve_model(report, None) == "opencode/deepseek-v4-flash-free"


def test_missing_both_errors_with_guidance(tmp_path):
    report = _write_report(tmp_path, {"timestamp": "2026-08-21"})
    with pytest.raises(SystemExit) as excinfo:
        resolve_model(report, None)
    assert "--model" in str(excinfo.value)


def test_missing_metadata_block_also_errors(tmp_path):
    report = _write_report(tmp_path, None)
    with pytest.raises(SystemExit):
        resolve_model(report, None)
