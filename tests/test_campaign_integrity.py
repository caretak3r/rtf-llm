"""Campaign integrity: executed-order labeling and seed persistence."""

from __future__ import annotations

import pytest

from modules.engine.base import PipelineResult, TransformContext, TransformResult
from modules.engine.report import consolidate


def _res(bypassed=False):
    return TransformResult(output="x", bypassed=bypassed, refusal_detected=False)


def _pr(results, any_bypassed=False):
    return PipelineResult(
        results=results,
        context=TransformContext(input="test"),
        total_time_ms=1.0,
        any_bypassed=any_bypassed,
    )


def test_consolidate_rejects_more_results_than_ids():
    # Fewer results than ids is legitimate early-stop truncation; the
    # impossible direction is a pipeline producing more results than ids.
    with pytest.raises(ValueError, match="fabricated"):
        consolidate([_pr([_res(), _res()])], scope_ids=[["a/b"]])


def test_consolidate_pairs_prefix_in_order():
    report = consolidate(
        [_pr([_res(), _res(True)], any_bypassed=True)],
        scope_ids=[["z/y", "a/x", "never/run"]],
    )
    assert [t.technique for t in report.transforms] == ["z/y", "a/x"]
    assert report.bypassed == 1
