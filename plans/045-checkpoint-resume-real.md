# Plan 045: Make checkpoint resume actually resume

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat a6a9a9d..HEAD -- modules/engine/backends/checkpoint.py main.py`
> If these changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW–MEDIUM (changes run semantics; corruption path must warn, never crash silently)
- **Depends on**: 040 (same `main.py` region — land 040 first); 042 (adjacent block)
- **Category**: correctness / wasted work
- **Planned at**: commit `a6a9a9d`, 2026-08-21
- **Partially addresses**: ARCHITECTURE_REVIEW T7 ("resume skips completed work")

## Why this matters

Engine-mode checkpointing is decorative today:

- `CheckpointStore.save` persists only `{"iteration", "metric", "seeds"}`
  (`modules/engine/backends/checkpoint.py:45-47`) — no per-seed or
  per-transform completion state, so nothing can be skipped.
- `main.py:663-670` prints "Resuming run from checkpoint" and then the
  seed loop at line 693 (`for seed in range(1, max(1, args.seeds) + 1)`)
  re-runs EVERY seed anyway.
- `check_high_water` (lines 722-734) warns when the stored metric exceeds
  the new one but never blocks the overwrite — so the "high-water" name is
  misleading and a crashed late run can erase a better recorded metric.

Net effect: a resumed run duplicates the entire sweep (cost) while telling
the operator it resumed (misleading UX), and the only durable artifact is
a counter.

## Current state

Excerpt (`modules/engine/backends/checkpoint.py:40-52`):

```python
    def save(self, run_id: str, iteration: int, metric: float, seeds: int) -> None:
        self._ensure()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints (run_id, iteration, metric, seeds) VALUES (?,?,?,?)",
                (run_id, iteration, metric, seeds),
            )

    def resume(self, run_id: str = "latest") -> dict | None:
        ...
```

Excerpt (`main.py:663-670`):

```python
            ckpt = CheckpointStore(args.db)
            if args.resume:
                state = ckpt.resume("latest")
                if state:
                    print(f"[*] Resuming run from checkpoint: {state}")
```

Excerpt (`main.py:722-730`, abridged — high-water check that never blocks):

```python
            if state := ckpt.check_high_water(metric):
                print(
                    f"[!] Previous run {state['run_id']} recorded metric {state['metric']:.3f} "
                    f"> current {metric:.3f} (possible regression)"
                )
            ckpt.save(run_id, len(transforms), metric, args.seeds)
```

## Repo conventions to match

- SQLite access via `sqlite3` stdlib with context-managed connections —
  follow `checkpoint.py` exactly (schema in `_ensure`, parameterized SQL).
- Engine modules fail loud on contract violations; user-facing warnings use
  `[!]` prefix prints (see `main.py:723-727`).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Lint | `uv run ruff check modules/engine/backends/checkpoint.py main.py` | exit 0 |
| Tests | `uv run pytest -q` | all pass |
| New tests | `uv run pytest tests/test_checkpoint.py -q` | all pass |

## Scope

**In scope**:
- `modules/engine/backends/checkpoint.py` — richer state, skip API, corruption handling.
- `main.py` — ONLY the engine-mode checkpoint/resume/seed-loop block (lines ~659-734).
- `tests/test_checkpoint.py` (extend).

**Out of scope**:
- Legacy (`--module`) path checkpointing (it has none; adding it is out of scope).
- `scripts/run_opencode_campaign.py` (no checkpointing there today).
- Concurrency/locking (single-process assumption stands; note in docstring).

## Git workflow

- Branch: `advisor/045-checkpoint-resume-real`
- Commit message: `feat: resumable engine runs — per-seed checkpoint state + enforced high-water`
- Do NOT push unless instructed.

## Steps

### Step 1: Extend the checkpoint schema

In `checkpoint.py`:

1. `_ensure` adds a column `done_seeds TEXT` (JSON array of completed seed
   ints) via the existing migration pattern — read `_ensure` first; if it
   uses `CREATE TABLE IF NOT EXISTS`, add an `ALTER TABLE ... ADD COLUMN`
   wrapped in try/except `sqlite3.OperationalError` (column exists).
2. `save` gains `done_seeds: list[int] | None = None`; serialize with
   `json.dumps`.
3. `resume` returns the dict including `done_seeds` parsed back to a list;
   on `json.JSONDecodeError` or missing table: print
   `"[!] Checkpoint corrupted, starting fresh: <err>"` and return `None`
   (never raise, never silently swallow without the print).
4. New method:

```python
    def remaining_seeds(self, state: dict | None, total: int) -> range:
        """Seeds still to run, given a resumed state."""
        if not state:
            return range(1, total + 1)
        done = set(state.get("done_seeds") or [])
        return range(1, total + 1) if total <= max(done, default=0) else range(max(done, default=0) + 1, total + 1)
```

5. Enforce the high-water gate: `check_high_water` keeps its warning, and
   `save` refuses to overwrite a strictly better metric unless the caller
   passes `force=True`. `main.py` passes `force=args.force` (flag already
   exists — verify name at main.py:676-682).

### Step 2: Skip completed seeds on resume

In `main.py` engine block:

1. After `state = ckpt.resume("latest")`, compute
   `seed_iter = ckpt.remaining_seeds(state, args.seeds)` and iterate THAT.
2. Track `completed_seeds: list[int]`; after each seed's outcomes are
   recorded (post Step-3 block of plan 040 — coordinate), call
   `ckpt.save(run_id, len(transforms), metric, args.seeds,
   done_seeds=completed_seeds)` so a mid-run crash resumes from the last
   fully recorded seed.
3. Keep the resume print but make it honest:
   `print(f"[*] Resuming: seeds {seed_iter.start}..{args.seeds} remain (done: {state.get('done_seeds') if state else []})")`.

**Verify**: `uv run ruff check main.py` → exit 0.

### Step 3: Tests

Extend `tests/test_checkpoint.py` (read it first; follow its tmp_path +
CheckpointStore pattern):

```python
def test_resume_roundtrip_done_seeds(tmp_path):
    store = CheckpointStore(str(tmp_path / "rtf.db"))
    store.save("r1", iteration=3, metric=0.5, seeds=5, done_seeds=[1, 2])
    state = store.resume("latest")
    assert state["done_seeds"] == [1, 2]


def test_corrupt_state_returns_none(tmp_path):
    import json

    store = CheckpointStore(str(tmp_path / "rtf.db"))
    store._ensure()
    with store._connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO checkpoints (run_id, iteration, metric, seeds, done_seeds) VALUES (?,?,?,?,?)",
            ("r1", 1, 0.1, 3, "{not json"),
        )
    assert store.resume("latest") is None


def test_remaining_seeds_math(tmp_path):
    store = CheckpointStore(str(tmp_path / "rtf.db"))
    assert list(store.remaining_seeds(None, 3)) == [1, 2, 3]
    assert list(store.remaining_seeds({"done_seeds": [1, 2]}, 5)) == [3, 4, 5]
```

(Adjust constructor/table names to the real schema — read the file first;
if `done_seeds` column name differs from this plan, follow the real one.)

**Verify**: `uv run pytest tests/test_checkpoint.py -q` → all pass.

## Done criteria

ALL must hold:

- [ ] `grep -n "done_seeds" modules/engine/backends/checkpoint.py main.py` → matches in both
- [ ] `grep -n "range(1, max(1, args.seeds)" main.py` → replaced by `remaining_seeds` iteration
- [ ] Corrupt checkpoint → warning print + fresh start (test proves it)
- [ ] High-water overwrite requires explicit force (test or code inspection)
- [ ] `uv run pytest -q` → all pass; `uv run ruff check .` → exit 0
- [ ] No files outside the in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:
- `checkpoint.py` schema/migration pattern differs materially from the excerpt.
- Plan 040's outcomes-loop is not yet landed (this plan's Step 2 hooks into
  it) — land 040 first or report the conflict.
- You find a second checkpoint consumer elsewhere (grep
  `CheckpointStore` across the repo) — reconcile its expectations first.

## Maintenance notes

- Per-TRANSFORM resume (T7's full promise) needs pipeline-level state; this
  plan delivers per-SEED, which covers the dominant cost case. Note the
  gap in the module docstring.
- If 048's architecture memo demotes CLI engine mode, this plan still pays
  off — the campaign script can adopt `remaining_seeds` later.
