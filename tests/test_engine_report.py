"""Tests for the engine report renderer (modules.engine.report)."""

from __future__ import annotations

import json

from modules.engine.base import PipelineResult, TransformContext, TransformResult
from modules.engine.report import (
    consolidate,
    render_all,
    render_json,
    render_markdown,
    to_standard_module,
)


def _ctx() -> TransformContext:
    return TransformContext(input="test")


def _pipelines() -> list[PipelineResult]:
    return [
        PipelineResult(
            results=[
                TransformResult(
                    output="leaked CANARY-123",
                    bypassed=True,
                    refusal_detected=False,
                    metrics={"pairs": 3},
                ),
                TransformResult(
                    output="refused",
                    bypassed=False,
                    refusal_detected=True,
                    error=None,
                ),
                TransformResult(
                    output="",
                    bypassed=False,
                    refusal_detected=False,
                    error="target timeout",
                ),
            ],
            context=_ctx(),
            total_time_ms=12.0,
            any_bypassed=True,
        ),
        PipelineResult(
            results=[
                TransformResult(output="safe", bypassed=False, refusal_detected=False),
            ],
            context=_ctx(),
        ),
    ]


def test_consolidate_counts():
    report = consolidate(_pipelines())
    assert report.total == 4
    assert report.bypassed == 1
    assert report.errored == 1
    assert report.refusals == 1
    assert report.canary_leaks == 1


def test_consolidate_empty():
    report = consolidate([])
    assert report.total == 0 and report.bypassed == 0
    assert report.failed == 0


def test_scope_ids_and_labels():
    report = consolidate(
        _pipelines(), scopes=["seed:1", "seed:2"], scope_ids=[["a", "b", "c"], ["d"]]
    )
    assert [t.technique for t in report.transforms] == ["a", "b", "c", "d"]


def test_scope_ids_truncate_to_results_prefix():
    report = consolidate(
        _pipelines(), scopes=["seed:1", "seed:2"], scope_ids=[["a", "b", "c"], ["d", "surplus"]]
    )
    assert [t.technique for t in report.transforms] == ["a", "b", "c", "d"]


def test_render_json_roundtrip():
    payload = json.loads(render_json(consolidate(_pipelines())))
    assert payload["total"] == 4
    assert payload["bypassed"] == 1
    assert payload["canary_leaks"] == 1
    assert payload["transforms"][0]["output"] == "leaked CANARY-123"


def test_render_markdown():
    md = render_markdown(consolidate(_pipelines()))
    assert "| Technique |" in md
    assert "| 0 |" in md
    assert "CANARY-123" not in md


def test_render_all_targets():
    targets = render_all(consolidate(_pipelines()))
    assert set(targets) == {"json", "markdown"}
    assert targets["json"].startswith("{")


def test_to_standard_module_feeds_report_generator():
    module = to_standard_module(consolidate(_pipelines()))
    assert module["module"] == "engine"
    assert module["summary"]["total"] == 4
    assert module["summary"]["successful"] == 1
    attacks = module["attacks"]
    assert len(attacks) == 4
    assert attacks[0]["success"] is True
    assert attacks[0]["pattern"] == "0"
    assert attacks[0]["canary_leaked"] is True
    assert attacks[0]["response"] == "leaked CANARY-123"
