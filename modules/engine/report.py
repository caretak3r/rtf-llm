#!/usr/bin/env python3
"""Engine report renderer — consumes TransformResult directly.

Report and dashboard rendering happens straight from TransformResult /
PipelineResult records; no intermediate dict shape is built. The legacy
ReportGenerator (modules/report_generator.py) remains for frozen legacy
modules only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from modules.engine.base import PipelineResult, TransformResult


@dataclass(frozen=True)
class TransformReport:
    technique: str
    output: str
    bypassed: bool
    refusal_detected: bool
    error: str | None
    metrics: dict
    canary_leaked: bool
    artifacts: list = field(default_factory=list)


@dataclass(frozen=True)
class EngineReport:
    total: int
    bypassed: int
    errored: int
    refusals: int
    canary_leaks: int
    transforms: list[TransformReport] = field(default_factory=list)

    @property
    def failed(self) -> int:
        return self.total - self.bypassed


def _canary_leaked(res: TransformResult) -> bool:
    haystack = " ".join([res.output or "", *[str(a) for a in (res.artifacts or [])]])
    return "CANARY" in haystack


def consolidate(
    pipelines: list[PipelineResult],
    scopes: list[str] | None = None,
    scope_ids: list[list[str]] | None = None,
) -> EngineReport:
    """Build an EngineReport from PipelineResults only.

    scope_ids supplies the transform id-list each pipeline ran (the
    requested order used by the caller); scope_labels override display
    names per pipeline.
    """
    if not pipelines:
        return EngineReport(0, 0, 0, 0, 0, [])
    rows = []
    for idx, pipeline in enumerate(pipelines):
        ids = scope_ids[idx] if scope_ids else _default_ids(pipeline)
        label = scopes[idx] if scopes else "pipeline"
        for tid, res in zip(ids, pipeline.results):
            rows.append(
                TransformReport(
                    technique=tid or label,
                    output=res.output or "",
                    bypassed=res.bypassed,
                    refusal_detected=res.refusal_detected,
                    error=res.error,
                    metrics=res.metrics,
                    canary_leaked=_canary_leaked(res),
                    artifacts=list(res.artifacts or []),
                )
            )
    return EngineReport(
        total=len(rows),
        bypassed=sum(1 for r in rows if r.bypassed),
        errored=sum(1 for r in rows if r.error),
        refusals=sum(1 for r in rows if r.refusal_detected),
        canary_leaks=sum(1 for r in rows if r.canary_leaked),
        transforms=rows,
    )


def _default_ids(pipeline: PipelineResult) -> list[str]:
    return [str(i) for i in range(len(pipeline.results))]


def render_json(report: EngineReport) -> str:
    payload = {
        "total": report.total,
        "bypassed": report.bypassed,
        "errored": report.errored,
        "refusals": report.refusals,
        "canary_leaks": report.canary_leaks,
        "transforms": [
            {
                "technique": t.technique,
                "bypassed": t.bypassed,
                "refusal_detected": t.refusal_detected,
                "error": t.error,
                "metrics": t.metrics,
                "canary_leaked": t.canary_leaked,
                "output": t.output,
                "artifacts": [str(a) for a in t.artifacts],
            }
            for t in report.transforms
        ],
    }
    return json.dumps(payload, indent=2, default=str)


def render_markdown(report: EngineReport) -> str:
    lines = [
        "# Engine red-teaming report",
        "",
        f"- Total transforms: **{report.total}**",
        f"- Bypassed: **{report.bypassed}**",
        f"- Errored: **{report.errored}**",
        f"- Refusals detected: **{report.refusals}**",
        f"- Canary leaks (ground truth): **{report.canary_leaks}**",
        "",
        "| Technique | Bypassed | Refusal | Error | Canary |",
        "|---|---|---|---|---|",
    ]
    for t in report.transforms:
        lines.append(
            f"| {t.technique} | {t.bypassed} | {t.refusal_detected} | "
            f"{bool(t.error)} | {t.canary_leaked} |"
        )
    return "\n".join(lines)


def render_all(report: EngineReport) -> dict[str, str]:
    """Data render targets: json and markdown. The HTML dashboard is
    produced by ReportGenerator (modules/report_generator.py) via
    to_standard_module()."""
    return {
        "json": render_json(report),
        "markdown": render_markdown(report),
    }


def to_standard_module(
    report: EngineReport,
    scope_name: str = "engine",
    intensity: str = "full",
) -> dict:
    """Adapter: EngineReport -> module dict consumed by ReportGenerator.

    Derives the report_generator's standard module shape (attacks +
    summary) exclusively from TransformResult data carried in
    EngineReport. No module in the engine returns this shape; it is a
    rendering-time conversion only.
    """
    attacks = [
        {
            "attack_type": "engine",
            "pattern": t.technique,
            "prompt": t.output,
            "success": t.bypassed,
            "error": t.error,
            "severity": "medium" if t.bypassed else ("high" if t.error else "info"),
            "confidence": 1.0 if t.bypassed else (0.0 if t.error else 0.0),
            "metrics": t.metrics,
            "canary_leaked": t.canary_leaked,
            "refusal_detected": t.refusal_detected,
            "response": "\n".join(str(a) for a in t.artifacts) or t.output,
        }
        for t in report.transforms
    ]
    return {
        "module": scope_name,
        "intensity": intensity,
        "attacks": attacks,
        "summary": {
            "total": report.total,
            "successful": report.bypassed,
            "failed": report.failed,
        },
    }
