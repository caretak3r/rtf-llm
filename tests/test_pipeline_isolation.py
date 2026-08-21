#!/usr/bin/env python3
"""One failing transform must not destroy the pipeline."""

import subprocess

import pytest

from modules.engine.base import Transform, TransformContext, TransformResult
from modules.engine.pipeline import Pipeline


class Boom(Transform):
    id = "test/boom"

    def transform(self, ctx):
        raise RuntimeError("boom")


class Static(Transform):
    id = "test/static"

    def transform(self, ctx):
        return TransformResult(output="x", bypassed=False, refusal_detected=False)


@pytest.fixture
def minimal_ctx():
    return TransformContext(input="x")


def test_pipeline_survives_raising_transform(minimal_ctx):
    pipe = Pipeline([Boom(), Static()])
    out = pipe.run(minimal_ctx)
    assert len(out.results) == 2
    assert out.results[0].error and "boom" in out.results[0].error
    assert out.results[0].bypassed is False
    assert out.results[1].output == "x"


def test_early_stop_still_works(minimal_ctx):
    class Win(Transform):
        id = "test/win"

        def transform(self, ctx):
            return TransformResult(output="w", bypassed=True, refusal_detected=False)

    out = Pipeline([Static(), Win(), Boom()]).run(minimal_ctx, early_stop=True)
    assert len(out.results) == 2  # Boom never runs
    assert any(r.bypassed for r in out.results)


def test_errored_transform_is_not_a_bypass(minimal_ctx):
    out = Pipeline([Boom()]).run(minimal_ctx)
    assert out.any_bypassed is False
    assert out.results[0].error.startswith("[ERROR]")


def test_opencode_target_timeout_returns_error_marker(monkeypatch, tmp_path):
    from modules.engine.backends.opencode_target import OpencodeTarget

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="opencode", timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)
    target = OpencodeTarget(workdir=str(tmp_path), timeout=5)
    out = target.respond("ping")
    assert out.startswith("[ERROR]")
    assert "timed out after 5s" in out


def test_opencode_target_missing_binary_returns_error_marker(tmp_path):
    from modules.engine.backends.opencode_target import OpencodeTarget

    target = OpencodeTarget(
        workdir=str(tmp_path),
        opencode_bin=str(tmp_path / "no-such-binary"),
    )
    out = target.respond("ping")
    assert out == "[ERROR] opencode binary not found"
