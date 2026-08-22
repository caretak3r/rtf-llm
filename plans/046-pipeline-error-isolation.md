# Plan 046: Pipeline error isolation + partial-report survival

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat a6a9a9d..HEAD -- modules/engine/pipeline.py modules/engine/backends/opencode_target.py main.py`
> If these changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P1
- **Effort**: S–M
- **Risk**: LOW (adds failure containment; success path untouched)
- **Depends on**: none (touches `main.py` tail — coordinate with 040/042/045 sequencing)
- **Category**: robustness / data loss
- **Planned at**: commit `a6a9a9d`, 2026-08-21

## Why this matters

One transient failure destroys an entire run:

- `Pipeline.run` calls `t.transform(ctx)` unguarded
  (`modules/engine/pipeline.py:20-27`): any exception from any transform
  aborts the whole pipeline — earlier successful transforms' results are
  lost.
- `OpencodeTarget._run` lets `subprocess.TimeoutExpired` propagate
  (`opencode_target.py:38-50`): a 180s target stall kills the pipeline
  instead of degrading one transform.
- `main.py`'s engine-mode outer handler (`except Exception` at ~line
  1094-1099) prints one line and exits — no partial report is written, so
  hours of sweep results vanish with the process.

## Current state

Excerpt (`modules/engine/pipeline.py:20-27`):

```python
    def run(self, ctx: TransformContext, early_stop: bool = False) -> PipelineResult:
        results: list[TransformResult] = []
        for t in self.transforms:
            started = time.perf_counter()
            res = t.transform(ctx)
            res.elapsed_ms = int((time.perf_counter() - started) * 1000)
            results.append(res)
            if early_stop and res.bypassed:
                break
        return PipelineResult(results, ctx, int((time.perf_counter() - t0) * 1000), any(...))
```

(Read the file for the exact `t0`/`any_bypassed` lines — match them.)

Excerpt (`modules/engine/backends/opencode_target.py:38-50`, abridged):

```python
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=self.workdir)
        except FileNotFoundError:
            return "[ERROR] opencode binary not found"
```

Note the established convention: `_run` already returns `"[ERROR] ..."`
marker strings for recoverable failures — timeout must follow the same
pattern, and `Pipeline` must additionally contain exceptions.

Excerpt (`main.py:1094-1099`, abridged):

```python
    except Exception as e:
        print(f"[!] Engine mode failed: {e}")
        raise SystemExit(1)
```

## Repo conventions to match

- `TransformResult` carries an `error: str | None` field (see `base.py`) —
  use it; do NOT invent a new result type.
- Error strings use `[ERROR]`/`[!]` prefixes consistently.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Lint | `uv run ruff check modules/engine main.py` | exit 0 |
| Tests | `uv run pytest -q` | all pass |
| New tests | `uv run pytest tests/test_engine.py tests/test_pipeline_isolation.py -q` | all pass |

## Scope

**In scope**:
- `modules/engine/pipeline.py` — per-transform try/except → error result.
- `modules/engine/backends/opencode_target.py` — catch `subprocess.TimeoutExpired`.
- `main.py` — engine-mode failure path writes a partial report when any results exist.
- `tests/test_pipeline_isolation.py` (create).

**Out of scope**:
- Retry/backoff policy (none today; adding one is a separate decision).
- Legacy `AttackEvaluator` error handling (parallel stack).
- `scripts/run_opencode_campaign.py` (its per-goal `_run_goal` inherits the
  pipeline fix automatically).

## Git workflow

- Branch: `advisor/046-pipeline-error-isolation`
- Commit message: `feat: contain transform failures — error results, timeout guard, partial reports`
- Do NOT push unless instructed.

## Steps

### Step 1: Per-transform containment in Pipeline.run

```python
        for t in self.transforms:
            started = time.perf_counter()
            try:
                res = t.transform(ctx)
            except Exception as exc:  # noqa: BLE001 — one transform must not kill the sweep
                res = TransformResult(
                    output="",
                    bypassed=False,
                    refusal_detected=False,
                    error=f"[ERROR] {type(t).__name__} raised {type(exc).__name__}: {exc}",
                )
            res.elapsed_ms = int((time.perf_counter() - started) * 1000)
            results.append(res)
            if early_stop and res.bypassed:
                break
```

Match `TransformResult`'s actual constructor signature from `base.py`
(read it; adjust field names). Keep the timing assignment OUTSIDE the try
so errored transforms still report cost.

**Verify**: `uv run pytest tests/test_engine.py -q` → still green.

### Step 2: Timeout guard in OpencodeTarget

In `_run`, add beside the existing `except FileNotFoundError`:

```python
        except subprocess.TimeoutExpired:
            return "[ERROR] opencode timed out after 180s"
```

**Verify**: `uv run ruff check modules/engine/backends/opencode_target.py` → exit 0.

### Step 3: Partial report on engine-mode failure

In `main.py`'s engine-mode exception handler: if `engine_pipelines` (or
`outcomes`) holds any results at failure time, run the existing
report-generation block in a `try/except` and print
`"[!] Partial report written: <path>"` before exiting nonzero. If report
generation itself fails, print the secondary failure and still exit 1.
Keep the change minimal — reuse the existing report code path, do not
duplicate it.

**Verify**: `uv run ruff check main.py` → exit 0.

### Step 4: Tests

Create `tests/test_pipeline_isolation.py` (follow `tests/test_engine.py`
fixture style for building a `TransformContext`):

```python
"""One failing transform must not destroy the pipeline."""
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
```

If a `minimal_ctx` fixture doesn't exist, copy the context-construction
lines from `tests/test_engine.py` into a local fixture in this file.

**Verify**: `uv run pytest tests/test_pipeline_isolation.py -q` → all pass.

## Done criteria

ALL must hold:

- [ ] `grep -n "except Exception" modules/engine/pipeline.py` → 1 match wrapping `t.transform(ctx)`
- [ ] `grep -n "TimeoutExpired" modules/engine/backends/opencode_target.py` → 1 match
- [ ] `uv run pytest tests/test_pipeline_isolation.py -q` → all pass; full suite green
- [ ] `uv run ruff check .` → exit 0
- [ ] No files outside the in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:
- `TransformResult` has no `error` field (read `base.py` — if absent, add
  `error: str | None = None` there and note the schema change in review;
  if adding it breaks constructors elsewhere, STOP).
- The `main.py` failure handler has already been restructured by 040/042/045.
- `Pipeline.run` gained its own exception policy meanwhile.

## Maintenance notes

- Errored transforms now appear in reports as non-bypassing rows with
  `error` set — consider surfacing an error count in `report.py`'s summary
  later (not in this plan).
- `noqa: BLE001` matches ruff's blanket-except rule; keep the comment.
- The 180s timeout stays hardcoded; a `--target-timeout` flag is a trivial
  follow-up if campaigns need it.
