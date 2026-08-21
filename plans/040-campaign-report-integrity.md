# Plan 040: Fix campaign technique misattribution + last-seed data loss

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat a6a9a9d..HEAD -- scripts/run_opencode_campaign.py modules/engine/report.py main.py`
> If any of these changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P0
- **Effort**: S
- **Risk**: LOW (report-layer only; no attack logic touched)
- **Depends on**: none
- **Category**: correctness / report integrity
- **Planned at**: commit `a6a9a9d`, 2026-08-21

## Why this matters

Two defects corrupt every number a campaign publishes:

1. **Technique misattribution under the default shuffle.**
   `run_opencode_campaign.py` sorts transform ids (`ids`, line 127), then
   shuffles a *per-goal copy* (`goal_ids`, lines 144-151) and executes
   transforms in that shuffled order — but labels results with the *sorted*
   list: `_run_goal(per_goal_transforms[goal], ids, ...)` (lines 165-171)
   and `runs.append((goal, ids, ...))` (lines 177-188) +
   `consolidate(scope_ids=[ids for _ in runs])` (lines 190-194).
   `consolidate` zips positionally (`modules/engine/report.py:66`):
   `for tid, res in zip(ids, pipeline.results)`. With `--order shuffle`
   (the default) and `early_stop` (default), `results[0]` is the first
   *shuffled* transform but gets labeled `sorted_ids[0]`. Every
   per-technique row in report.json/md/dashboard is attached to the wrong
   technique whenever more than one transform ran. The LLM-judge path
   (line 174) already uses the correct `per_goal_ids[goal]`.

2. **Multi-seed CLI runs persist only the last seed.**
   `main.py` collects every seed's `PipelineResult` into `outcomes`
   (line 702), then throws all but the last away: `outcome = outcomes[-1][1]`
   (line 737); provenance records only `outcome.results` (line 746);
   `engine_pipelines.append((f"seed:{seed}", requested, outcome))` appends
   one entry (line 781) — while the saved "high-water metric" is computed as
   a max over ALL seeds (lines 756-758), so it can cite a value no recorded
   finding supports. Also `via_technique=f"seed={seed}"` (line 750) uses the
   leaked loop variable for every row.

## Current state

Excerpt (`scripts/run_opencode_campaign.py:142-151`):

```python
    for goal in goals:
        seed += len(goal)
        goal_ids = list(ids)
        if args.order == "shuffle":
            import random

            rng = random.Random(seed)
            rng.shuffle(goal_ids)
        per_goal_transforms[goal] = [by_id[tid] for tid in goal_ids]
        per_goal_ids[goal] = goal_ids
```

Excerpt (`scripts/run_opencode_campaign.py:163-194`) — note line 167 passes
`ids`, not `per_goal_ids[goal]`:

```python
    runs = []
    for goal in goals:
        pipeline_result = _run_goal(
            per_goal_transforms[goal],
            ids,
            goal,
            config,
            target,
            early_stop=not args.full_sweep,
        )
        if args.judge == "llm":
            res = _llm_scored(pipeline_result.results, per_goal_ids[goal], goal, target)
        else:
            res = list(pipeline_result.results)
        runs.append(
            (
                goal,
                ids,
                type(pipeline_result)(
                    res,
                    pipeline_result.context,
                    pipeline_result.total_time_ms,
                    any(r.bypassed for r in res),
                ),
            )
        )

    report = consolidate(
        [run[2] for run in runs],
        scopes=[f"{args.model}" for _ in runs],
        scope_ids=[ids for _ in runs],
    )
```

Excerpt (`modules/engine/report.py:63-66`) — positional zip, silent truncation:

```python
    for idx, pipeline in enumerate(pipelines):
        ids = scope_ids[idx] if scope_ids else _default_ids(pipeline)
        label = scopes[idx] if scopes else "pipeline"
        for tid, res in zip(ids, pipeline.results):
```

Note: with `early_stop=True`, `len(pipeline.results) <= len(ids)` is normal
(the pipeline stops at first bypass), so truncation itself is legitimate —
the bug is *ordering*, not length. The fix must pair `results[i]` with the
id of the transform that actually ran at position i.

Excerpt (`main.py:736-781`, abridged — full block at those lines):

```python
            run_id = f"run-{int(time.time())}"
            outcome = outcomes[-1][1] if outcomes else None
            ...
            db = ProvenanceDB(args.db)
            try:
                for tid, res in zip(requested, outcome.results):
                    db.record_finding(
                        run_id=run_id,
                        technique=tid,
                        via_technique=f"seed={seed}",
                        ...
```

## Repo conventions to match

- Engine code fails loud on contract violations (see `registry.py:19,27`
  raising `ValueError` on duplicate ids). Match that style.
- Tests are plain pytest functions with fake clients — see
  `tests/test_engine_report.py` for the established
  `consolidate`/`to_standard_module` test patterns. Follow those exactly.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Lint | `uv run ruff check scripts/run_opencode_campaign.py main.py modules/engine/report.py` | exit 0 |
| Tests | `uv run pytest -q` | all pass (153 passing at `a6a9a9d`) |
| New tests | `uv run pytest tests/test_campaign_integrity.py tests/test_engine_report.py -q` | all pass |

## Scope

**In scope** (the only files you should modify):
- `scripts/run_opencode_campaign.py`
- `main.py` — ONLY the engine-mode recording block (lines ~736-781)
- `modules/engine/report.py` — defensive guard in `consolidate` only
- `tests/test_campaign_integrity.py` (create)
- `tests/test_engine_report.py` (extend)

**Out of scope** (do NOT touch):
- `modules/engine/pipeline.py` — its return shape is fine; ordering is fixed at call sites.
- Any transform under `modules/engine/transforms/`.
- The legacy (`--module`) dispatch path in `main.py`.
- Plan 045's checkpoint block (`main.py:659-670,722-734`) — different defect; coordinate if both are in flight (both edit the same region — land sequentially).

## Git workflow

- Branch: `advisor/040-campaign-report-integrity`
- Commit message: `fix: pair campaign results with executed transform order + persist all seeds`
- Do NOT push unless instructed.

## Steps

### Step 1: Thread the executed id-order through the campaign driver

In `scripts/run_opencode_campaign.py`:

1. Change `_run_goal` to also return the executed id list. Since
   `Pipeline.run` returns results in execution order and `early_stop` may
   truncate, compute `executed = goal_ids[:len(pipeline_result.results)]`
   inside `_run_goal` (it receives the ordered `transforms`; give it the
   matching `goal_ids` parameter) and return a tuple
   `(pipeline_result, executed)`. Update its signature from
   `ids: list[str]` to `executed_ids_source: list[str]` naming clarity:
   rename the parameter to `goal_ids`.
2. Call site (lines 164-172): pass `per_goal_ids[goal]`.
3. Judge branch (line 174): keep using the returned `executed` list
   (identical content to `per_goal_ids[goal]` truncated).
4. Non-judge branch (line 176): leave `res` as-is (already execution order).
5. `runs.append(...)` (lines 177-188): store `executed` instead of `ids`.
6. `consolidate(scope_ids=[ids for _ in runs])` (line 193):
   `[run[1] for run in runs]`.

**Verify**: `uv run ruff check scripts/run_opencode_campaign.py` → exit 0;
`uv run python -c "import ast; ast.parse(open('scripts/run_opencode_campaign.py').read())"` → exit 0.

### Step 2: Make `consolidate` fail loud on impossible pairing

In `modules/engine/report.py`, inside the per-pipeline loop, replace the
silent `zip` with an explicit truncation + assertion:

```python
        n = len(pipeline.results)
        paired = ids[:n]
        if n > len(ids):
            raise ValueError(
                f"scope_ids[{idx}] has {len(ids)} ids but pipeline produced "
                f"{n} results — id/result pairing would be fabricated"
            )
        for tid, res in zip(paired, pipeline.results):
```

**Verify**: `uv run pytest tests/test_engine_report.py -q` → all pass.

### Step 3: Persist every seed in main.py engine mode

In `main.py`, engine block:

1. Replace `outcome = outcomes[-1][1]` usage for persistence: loop over all
   `outcomes`. For each `(s, out)` in `outcomes`, compute
   `executed_ids = requested[:len(out.results)]` and record provenance rows
   with `via_technique=f"seed={s}"` (bind the loop variable, do not reuse a
   leaked name).
2. Append one `engine_pipelines` entry PER seed, labeled `f"seed:{s}"`,
   so the consolidated report includes every seed.
3. Keep the high-water metric computation as-is (max over seeds) — now it
   is consistent with what is persisted.

**Verify**: `uv run ruff check main.py` → exit 0.

### Step 4: Regression tests

Create `tests/test_campaign_integrity.py`:

```python
"""Campaign integrity: executed-order labeling and seed persistence."""
from modules.engine.base import PipelineResult, TransformResult


def _res(bypassed=False):
    return TransformResult(output="x", bypassed=bypassed, refusal_detected=False)


def test_consolidate_rejects_extra_ids():
    import pytest
    from modules.engine.report import consolidate

    pr = PipelineResult([_res()], context=None, total_time_ms=1.0, any_bypassed=False)
    with pytest.raises(ValueError, match="fabricated"):
        consolidate([pr], scope_ids=[["a/b", "c/d"]])


def test_consolidate_pairs_prefix_in_order():
    from modules.engine.report import consolidate

    pr = PipelineResult([_res(), _res(True)], context=None, total_time_ms=1.0, any_bypassed=True)
    report = consolidate([pr], scope_ids=[["z/y", "a/x", "never/run"]])
    assert [t.technique for t in report.transforms] == ["z/y", "a/x"]
    assert report.bypassed == 1
```

Add one test to `tests/test_engine_report.py` mirroring the existing style
if the above placement conflicts with local conventions — follow whatever
`test_engine_report.py` already does for constructing `PipelineResult`.

**Verify**: `uv run pytest tests/test_campaign_integrity.py -q` → all pass;
`uv run pytest -q` → all pass.

## Done criteria

ALL must hold:

- [ ] `grep -n "per_goal_ids\[goal\]" scripts/run_opencode_campaign.py` shows the `_run_goal` call site using it (not `ids`)
- [ ] `grep -n "zip(ids" modules/engine/report.py` returns NO matches (replaced by guarded pairing)
- [ ] `grep -n "outcomes\[-1\]" main.py` returns no persistence-use matches (only the final-outcome guard for reporting, if kept, must be justified in review)
- [ ] `uv run pytest -q` → all pass, including the two new tests
- [ ] `uv run ruff check .` → exit 0
- [ ] No files outside the in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:
- `_run_goal`'s signature has drifted from the excerpt (e.g. it already returns a tuple).
- `PipelineResult` gained its own executed-id tracking (then use it instead of slicing).
- You cannot construct `TransformResult`/`PipelineResult` in tests without a real client — read `tests/test_pair_transform.py` for the fixture pattern; if still blocked, report.

## Maintenance notes

- The judge path was already correct; after this plan both paths share one
  id list, so a future refactor can drop the duplicate `per_goal_ids` dict
  if `_run_goal` returns executed ids.
- Plan 045 (checkpoint resume) rewrites the adjacent seed-loop region in
  `main.py`. Land 040 first; 045's excerpts assume 040's loop-over-outcomes
  shape.
- Any new consumer of `consolidate` must now pass ids in EXECUTION order —
  the ValueError guards accidental misuse.
