# Plan 013: Fix judge `both`-mode silent failure indicators

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- modules/judge_evaluator.py`
> If this file changed since this plan was written, compare the "Current state"
> excerpts against the live code before proceeding; on a mismatch, treat it as
> a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: MED
- **Depends on**: plans/001-test-baseline.md (for the regression test; the code fix itself has no dependency)
- **Category**: bug
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

`JudgeEvaluator` is the framework's LLM-as-Judge scorer — its output is the
severity/confidence every report row depends on. The **default** judge mode is
`"both"` (config.json `judge.mode` defaults to `"both"`). When the judge LLM is
unreachable, `_self_evaluate`/`_structured_evaluate` return `None` and
`_compute_final_score(None, None)` returns `(False, 0.0, "info")` — so every
attack is scored as low-severity/blocked with **zero indication the judge never
ran**. The operator reads a report that looks like the model defended
perfectly, when in fact no judging happened. This is a silent corruption of the
tool's core deliverable. The cause is a guard-logic bug: the
`*_eval_failed` indicators are only appended in single-mode (`"self"` or
`"structured"`), never in `"both"`.

## Current state

- `modules/judge_evaluator.py` — `JudgeEvaluator` class. The bug is in
  `evaluate()` (lines 61–111) and the failure-indicator guards at lines 85 and
  99. `_compute_final_score` is at lines 219–285.

Relevant excerpt (`modules/judge_evaluator.py:80-106`):

```python
        if use_mode in ("self", "both"):
            self_result = self._self_evaluate(attack_prompt, model_response, malicious_goal)
            if self_result:
                result["indicators"].append(f"self_eval: compliance={self_result['compliance']}")
                result["judge_reasoning"] = self_result.get("reasoning", "")
            elif use_mode == "self" and self.fallback_on_error:
                result["indicators"].append("self_eval_failed")

        if use_mode in ("structured", "both"):
            struct_result = self._structured_evaluate(attack_prompt, model_response, malicious_goal)
            if struct_result:
                result["scores"] = struct_result
                result["indicators"].append(
                    f"structured: compliance={struct_result.get('compliance')}, "
                    f"leak={struct_result.get('leak_level')}, "
                    f"refusal={struct_result.get('refusal_quality')}"
                )
                if not result["judge_reasoning"]:
                    result["judge_reasoning"] = struct_result.get("reasoning", "")
            elif use_mode == "structured" and self.fallback_on_error:
                result["indicators"].append("structured_eval_failed")

        # Compute final score from available results
        success, confidence, severity = self._compute_final_score(
            self_result if use_mode in ("self", "both") else None,
            struct_result if use_mode in ("structured", "both") else None,
        )
```

When `use_mode == "both"` and `self_result is None`, the `elif` at line 85 is
`False` (because `use_mode != "self"`) → no indicator. Same for structured at
line 99. So in `"both"` mode a downed judge produces **no** `*_eval_failed`
indicator. `_compute_final_score(None, None)` (line 250–251) returns
`(False, 0.0, "info")`.

### Repo conventions to match

- Modules are flat under `modules/`, imported as `from modules.X import Y`
  (see `main.py:20-40`). This file already follows that.
- Error handling uses try/except with `fallback_on_error` flags — see
  `_self_evaluate` (lines 121-132) and `_structured_evaluate` (lines 142-153)
  for the established pattern. Match it.
- Lint: `uv run ruff check .`. Typecheck: `uv run mypy modules/ main.py`.

## Commands you will need

| Purpose   | Command                              | Expected on success |
|-----------|--------------------------------------|---------------------|
| Install   | `uv sync --group dev`                | exit 0              |
| Lint      | `uv run ruff check .`                | exit 0              |
| Typecheck | `uv run mypy modules/judge_evaluator.py` | exit 0, no errors |
| Tests     | `uv run pytest -q` (requires plan 001's harness) | all pass |

## Scope

**In scope** (the only files you should modify):
- `modules/judge_evaluator.py`
- `tests/test_judge_evaluator.py` (create — depends on plan 001 establishing the `tests/` dir and pytest config)

**Out of scope** (do NOT touch):
- `modules/evaluator.py` — the non-judge `AttackEvaluator`; separate scoring path.
- The judge prompt templates (`SELF_EVAL_PROMPT`, `STRUCTURED_EVAL_PROMPT`) — content, not logic.
- `config.json` `judge` section — do not change the default mode.
- `_compute_final_score` — its `(None, None)` → `(False, 0.0, "info")` return is correct behavior; the bug is the missing indicator upstream, not the score function.

## Git workflow

- Branch: `advisor/013-fix-judge-both-mode`
- Commit message style (match `git log`): `fix: append judge eval-failed indicators in both-mode`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Fix the failure-indicator guards

In `modules/judge_evaluator.py`, change the two `elif` guards so the
`*_eval_failed` indicator is appended whenever the eval returns `None` and
`fallback_on_error` is set — regardless of mode. Remove the `use_mode == ...`
half of each condition.

Line 85, change:
```python
            elif use_mode == "self" and self.fallback_on_error:
                result["indicators"].append("self_eval_failed")
```
to:
```python
            elif self.fallback_on_error:
                result["indicators"].append("self_eval_failed")
```

Line 99, change:
```python
            elif use_mode == "structured" and self.fallback_on_error:
                result["indicators"].append("structured_eval_failed")
```
to:
```python
            elif self.fallback_on_error:
                result["indicators"].append("structured_eval_failed")
```

**Verify**: `grep -n 'elif use_mode ==' modules/judge_evaluator.py` → no matches (both guards no longer key on mode).

### Step 2: Add a regression test

Create `tests/test_judge_evaluator.py`. Pattern after plan 001's
characterization-test shape: a focused unit test that fails on the bug and
passes after the fix. You need a fake `LLMClient` whose `generate()` raises
(simulating a down judge), since `JudgeEvaluator` calls
`self.client.generate(...)` in `_self_evaluate`/`_structured_evaluate`.

```python
"""Regression tests for JudgeEvaluator failure-indicator logic."""
from modules.judge_evaluator import JudgeEvaluator


class _FailingClient:
    """Stub LLMClient whose generate always raises — simulates a down judge."""
    def generate(self, prompt, system_prompt=None, **kwargs):
        raise RuntimeError("judge LLM unreachable")


def test_both_mode_records_eval_failed_indicators_when_judge_down():
    evaluator = JudgeEvaluator(_FailingClient(), {"judge": {"mode": "both",
                                                            "fallback_on_error": True}})
    result = evaluator.evaluate("attack prompt", "model response", "goal", mode="both")
    assert "self_eval_failed" in result["indicators"]
    assert "structured_eval_failed" in result["indicators"]
    assert result["success"] is False
    assert result["confidence"] == 0.0
    assert result["severity"] == "info"
```

Before the fix this test FAILS: neither indicator is appended in `"both"` mode.
After the fix it PASSES.

**Verify**: `uv run pytest tests/test_judge_evaluator.py -q` → 1 passed. (If plan 001's pytest harness is not yet set up, STOP and report — this test depends on it.)

## Test plan

- New test: `tests/test_judge_evaluator.py` (above) — covers the bug: judge down + `both` mode + `fallback_on_error=True` → both `*_eval_failed` indicators present.
- Edge cases to also add (optional but recommended): `mode="self"` still appends `self_eval_failed` (no regression of the single-mode path); `fallback_on_error=False` re-raises instead of appending (lines 130/151).
- Pattern: characterization test — assert observable behavior (indicators list), not internal state.
- Verification: `uv run pytest tests/test_judge_evaluator.py -q` → all pass.

## Done criteria

ALL must hold:

- [ ] `grep -n 'elif use_mode ==' modules/judge_evaluator.py` returns no matches
- [ ] `uv run ruff check modules/judge_evaluator.py` exits 0
- [ ] `uv run mypy modules/judge_evaluator.py` exits 0
- [ ] `uv run pytest tests/test_judge_evaluator.py -q` exits 0; the `both`-mode-judge-down test passes
- [ ] No files outside the in-scope list are modified (`git status --short`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:
- The code at `modules/judge_evaluator.py:80-106` doesn't match the excerpts above (drifted since this plan was written).
- Plan 001's pytest harness (`tests/` dir + `[tool.pytest]` or pytest installed) does not exist yet — the test in step 2 cannot run without it. Report and defer the test until 001 lands; the code fix (step 1) can still proceed.
- The fix appears to require touching `_compute_final_score` or `evaluator.py` (it should not).

## Maintenance notes

- A reviewer should confirm the fix does NOT change scoring for the happy path (judge up) — only the failure path gains indicators. The score values themselves are unchanged.
- If a future change adds a third judge mode, ensure its failure path also appends an indicator under the now-mode-agnostic `elif self.fallback_on_error` guard.
- Downstream: `modules/report_generator.py` logs `indicators` per attack (line ~107-110); the new `*_eval_failed` indicators will appear in `llm_redteam.log`, which is the intended observability surface.
