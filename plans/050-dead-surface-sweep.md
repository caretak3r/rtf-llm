# Plan 050: Dead engine surface — wire-or-delete sweep

> **Executor instructions**: Follow this plan step by step. Several items
> are explicit DECISION POINTS marked DELETE-or-WIRE — apply the DEFAULT
> given, and record any deviation in the commit message. When done, update
> the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat a6a9a9d..HEAD -- modules/engine/ pyproject.toml`
> If these changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P2
- **Effort**: S–M
- **Risk**: LOW–MEDIUM (deletions; mitigated by landing plan 049 first)
- **Depends on**: 049 (seam tests) lands FIRST; 048 (ADR) informs the WIRE choices — proceed with defaults if 048 undecided
- **Category**: tech debt / dead code
- **Planned at**: commit `a6a9a9d`, 2026-08-21
- **House style**: follows plans 004/005/014 (deletion sweeps with verification)

## Why this matters

The engine carries confirmed-dead or semantically-broken surface (~350+ LOC)
that obscures its real shape:

| Item | Problem | Evidence |
|---|---|---|
| `stream_handler.SWALLOW` | Yields the refusal text anyway — identical output to COMMIT; only the stats counter differs. A "strategy" that isn't. | `backends/stream_handler.py:116-120`: both branches `yield token` |
| `best_of_n.bypassed` | Hardcoded `False` — Best-of-N can NEVER report success. | `transforms/adaptive/best_of_n.py:71` |
| `classic.bypassed` | Same hardcode in the classic jailbreak transform. | `transforms/jailbreak/classic.py` (read around line 55) |
| `router.rerank` / `get_transform` | Zero production callers. | grep across repo |
| `Pipeline.arun` / async path | Dead async variant. | grep `arun(` |
| Empty packages `persistence/`, `injection/chinese.py` placeholder, `evaluator/` dir | T5/T9 placeholders never materialized. | directory listing |
| `HeartbeatStream` (in `llm_client.py`) | No production caller. | grep |
| ruff exclude `modules/direct_attack.py` | File no longer exists — stale exclude line. | `pyproject.toml` `[tool.ruff]` extend-exclude |
| Registry swallows broken-transform imports | `_walk_package` except-ImportError continues silently — a typo'd transform vanishes from the registry without a trace. | `registry.py` (read `_walk_package`) |

## Current state (verified excerpts)

Excerpt (`modules/engine/backends/stream_handler.py:110-121`):

```python
            if self.strategy == StreamStrategy.SWALLOW:
                yield token
                continue
```

versus COMMIT branch immediately after — both `yield token`; SWALLOW skips
only `self.tokens_emitted += len(token)`.

Excerpt (`modules/engine/transforms/adaptive/best_of_n.py:69-72`):

```python
            return TransformResult(
                output=best,
                bypassed=False,
                refusal_detected=False,
                ...
```

## Repo conventions to match

- Deletion commits are single-purpose (`refactor:`/`chore:` prefix), like
  plans 004/005 prescribe.
- Clean cutover: remove callers/references in the same change; no
  deprecation shims.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Caller checks | `grep -rn "rerank\|get_transform\|arun\|HeartbeatStream\|SWALLOW" --include='*.py' main.py scripts/ modules/engine/backends/ modules/engine/transforms/adaptive/` | inventory before deleting |
| Lint | `uv run ruff check .` | exit 0 |
| Tests | `uv run pytest -q` | all pass |

## Scope

**In scope**: files listed above + their direct callers + their tests +
`pyproject.toml` exclude line.

**Out of scope**: legacy frozen modules (ruff-exempt stack); anything 048's
ADR would re-scope; adding FEATURES while deleting (no streaming-wiring here).

## Git workflow

- One branch, several small commits:
  `advisor/050-dead-surface-sweep`
- Messages: `refactor: remove dead <item>` / `fix: best_of_n bypass detection`.

## Steps (each = verify then commit)

### Item 1: best_of_n + classic bypassed semantics — FIX (default)

Wire real detection: when a judge/detector is available in ctx config
(engine.live mode), set `bypassed=` from the existing refusal/judge signal
available in that transform's loop (PAIR already does this pattern — read
`pair_transform.py:118-130` for the established detector fallback chain and
mirror it minimally). If wiring requires more context than the transform
receives, implement the minimal version: `bypassed=not refusal_detected`
with a comment, and note the judge upgrade path. Update/add tests asserting
bypassed flips with the signal.

### Item 2: SWALLOW — FIX semantics (default)

Make SWALLOW actually swallow: buffer tokens while a refusal phrase is
actively matching and withhold them unless the scan clears (i.e., emit
nothing during an active match; COMMIT keeps current behavior). Update the
049 tests. Alternative accepted: delete the SWALLOW variant entirely if the
maintainer prefers two-strategy simplicity — choose ONE, state which in
the commit.

### Item 3: rerank tie-safety — covered by plan 047 (skip here)

If 047 hasn't landed, leave `rerank` untouched; deletion is NOT the default
(the router is plausible future API).

### Item 4: get_transform — DELETE (default)

Remove from `registry.py` plus any test references. If a caller appears in
grep that the audit missed, WIRE-decision flips to KEEP and you STOP that
item with a note.

### Item 5: arun/atransform async variants — DELETE (default)

Remove the async methods and any `asyncio` imports left unused. Verify no
caller exists first.

### Item 6: HeartbeatStream — DELETE (default)

Remove the class + its imports. It predates the engine's session backend;
nothing constructs it.

### Item 7: Empty packages — DELETE (default)

Remove `persistence/`, `evaluator/` dirs and the `injection/__init__.py`
placeholder IF truly empty (verify with `find modules/engine/persistence modules/engine/evaluator -type f`). Keep `injection/` package itself if T5
is still roadmap — check `docs/init.md` for the T5 mention; if roadmap
confirms it, keep the package and add a one-line README inside noting the
placeholder status instead.

### Item 8: Stale ruff exclude — FIX

In `pyproject.toml` `[tool.ruff]` extend-exclude list: remove
`"modules/direct_attack.py"` if the file does not exist
(`ls modules/direct_attack.py` → absent). Keep all other excludes.

### Item 9: Registry silent-import warning — FIX (small)

In `_walk_package`, log/print `"[!] registry skipped <module>: <err>"`
before continuing. Engine prints use `[!]` convention.

**Verify each item**: `uv run pytest -q` green + `uv run ruff check .` exit
0 before committing it.

## Test plan

- 049's stream/best_of_n tests updated alongside Items 1-2.
- Registry warning: extend `tests/test_engine.py` with a tmp package
  containing one broken module, assert the warning text and that valid
  siblings still register.

## Done criteria

ALL must hold:

- [ ] `grep -rn "class HeartbeatStream" modules/` → no matches (or documented KEEP)
- [ ] `grep -n "bypassed=False" modules/engine/transforms/adaptive/best_of_n.py modules/engine/transforms/jailbreak/classic.py` → no hardcoded matches (replaced by signal)
- [ ] Stale exclude gone; `uv run ruff check .` exit 0
- [ ] Registry warns on broken imports (test proves it)
- [ ] `uv run pytest -q` → all pass
- [ ] Each item its own commit; total diff ≤ ~400 net removed lines
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:
- Any "zero-caller" grep finds a live caller (flip that item to KEEP, note it).
- Deleting an item breaks an undocumented consumer (tests will catch it — investigate, don't force).
- Item 1's minimal `bypassed` wiring would mislabel refusals as bypasses under review — prefer leaving the hardcode with a TODO comment over shipping wrong signals, and report.

## Maintenance notes

- This sweep is what makes the engine's true surface visible for ADR-001.
- After landing, update `ARCHITECTURE_REVIEW.md` scorecard rows it closes.
