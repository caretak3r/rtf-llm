# Plan 049: Engine seam test baseline + root conftest

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat a6a9a9d..HEAD -- modules/engine/eval/llm_judge.py modules/engine/backends/stream_handler.py modules/engine/transforms/legacy/legacy_bridge.py tests/`
> If these changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW (tests only + one empty conftest)
- **Depends on**: none; SHOULD land before 050 (dead-code sweep needs these tests as a safety net)
- **Category**: test debt
- **Planned at**: commit `a6a9a9d`, 2026-08-21
- **Supersedes the remaining gap of** plan 001 (test harness exists, 21 files,
  CI runs pytest — what's missing is the engine SEAMS listed below)

## Why this matters

The maintained surface has exactly seven files with zero or smoke-only test
coverage — and they are precisely where correctness lives:
`modules/engine/eval/llm_judge.py` (covered by plan 044),
`backends/opencode_target.py`, `backends/stream_handler.py` (import-smoke
only), `transforms/legacy/legacy_bridge.py`, all 1,106 lines of `main.py`,
and both `scripts/*.py`. Bugs #1-#9 in the current audit shipped because
these seams are untested.

Separately, there is NO root `conftest.py`. pytest inserts only `tests/`
into `sys.path` (no `__init__.py` anywhere), so `import modules` works ONLY
when the project is properly installed in the active venv. This checkout
was recently MOVED (`~/Documents/rtf-llm` →
`~/Documents/red-teaming/rtf-llm`): `.venv/bin/pytest`'s shebang still
pointed at the old path, so `uv run pytest` silently fell through to a
Homebrew pytest under Python 3.14 and produced 21 collection errors that
looked like 21 broken test files. The venv was rebuilt during the audit
(153 passing). A root conftest makes the suite robust against foreign
pytest processes and relocation by putting the repo root on `sys.path`.

## Current state

Verified facts:

- `ls tests/conftest.py` → does not exist; `ls conftest.py` → does not exist.
- `grep -c "def test_" tests/test_stream_handler.py` → import-smoke only.
- `tests/test_legacy_bridge.py`, `tests/test_opencode_target.py`,
  `tests/test_llm_judge.py`, `tests/test_main_cli.py` → do not exist.
- Suite baseline at `a6a9a9d`: **153 passed** via
  `uv sync --all-groups && uv run pytest -q`.

## Repo conventions to match

- Plain pytest functions, fakes over mocks, no fixtures beyond `tmp_path` —
  see `tests/test_pair_transform.py`, `tests/test_engine_report.py`.
- Module docstring on every test file stating the contract under test.
- No network, no real API keys, no subprocess spawns in tests.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Lint | `uv run ruff check .` | exit 0 |
| Full suite | `uv run pytest -q` | all pass (≥153 before your additions) |
| New tests | `uv run pytest tests/test_opencode_target.py tests/test_stream_handler.py tests/test_legacy_bridge.py tests/test_root_conftest.py -q` | all pass |

## Scope

**In scope**:
- `conftest.py` (repo ROOT, create) — sys.path bootstrap, nothing else.
- `tests/test_opencode_target.py` (create) — `_extract` parsing + `_run`
  error-marker behavior with a fake binary.
- `tests/test_stream_handler.py` (extend) — strategy semantics per current code.
- `tests/test_legacy_bridge.py` (create) — `_fold_campaign`, live-gate error path, `_Facade` chat collapse.
- `tests/test_root_conftest.py` (create) — proves root is importable from an arbitrary cwd-relative collection.

**Out of scope**:
- `main.py` CLI tests (plan-worthy separately; needs a click-free harness decision).
- `scripts/*` tests beyond what 040/043 add.
- Coverage tooling/gates (separate tooling decision; not in this plan).

## Git workflow

- Branch: `advisor/049-engine-seam-tests`
- Commit message: `test: engine seam coverage + root conftest sys.path bootstrap`
- Do NOT push unless instructed.

## Steps

### Step 1: Root conftest.py

Create `conftest.py` at repo root:

```python
"""Pytest bootstrap: make the repo root importable regardless of how pytest was invoked.

Without this, `import modules` only resolves when the project venv is active
AND correctly relocated; a stale/moved .venv silently falls back to a system
pytest and produces mass collection errors (seen 2026-08 after the checkout
moved into red-teaming/).
"""

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
```

**Verify**: `uv run pytest tests/test_router.py -q` → passes; then prove
robustness: `/opt/homebrew/bin/python3* -m pytest tests/test_root_conftest.py -q`
is NOT required to pass (foreign interpreter may lack deps) — skip that;
the unit test below asserts the mechanism instead.

### Step 2: opencode_target seam tests

Read `opencode_target.py` fully first. Create
`tests/test_opencode_target.py`:

```python
"""OpencodeTarget: response extraction + error markers, no subprocess."""
from modules.engine.backends.opencode_target import OpencodeTarget


def _target(tmp_path, binary="true"):
    return OpencodeTarget(binary=binary, model="fake", workdir=str(tmp_path))


def test_extract_prefers_last_assistant_block():
    raw = 'some preamble\nassistant: first\nassistant: final answer'
    assert OpencodeTarget._extract(raw).endswith("final answer")


def test_run_missing_binary_returns_marker(tmp_path):
    t = _target(tmp_path, binary="/nonexistent/opencode-binary-xyz")
    out = t.generate("hello")
    assert out.startswith("[ERROR]")


def test_timeout_returns_marker(tmp_path):
    # Requires plan 046 landed; if not landed, mark xfail with reason.
    ...
```

Match the REAL `_extract` name/signature and constructor kwargs by reading
the file — the drafts above are shape guides, not gospel. If `_extract` is
named differently (`_parse_output` etc.), use the real name.

### Step 3: stream_handler semantics (current behavior)

Extend `tests/test_stream_handler.py` with one test per strategy encoding
CURRENT semantics (SWALLOW yields tokens but doesn't count them;
COMMIT yields and counts; RETROACTIVE aborts on next token). These tests
are what makes plan 050's fix-or-delete decision safe. Read
`stream_handler.py:100-127` for exact behavior first.

### Step 4: legacy_bridge tests

Create `tests/test_legacy_bridge.py` covering, per the real API (read it):

1. Live-gate OFF: bridge transform returns `error=...requires a live target`.
2. Live-gate ON with a fake module: folded results map to
   `TransformResult(output=..., bypassed=...)` correctly (use
   `_fold_campaign` if that's the real helper name).
3. `_Facade.chat` collapses multi-turn calls into sequential prompts.

Use monkeypatch/stub objects for the frozen-module classes — never import
real ones requiring API keys (they don't need keys, but keep isolation).

### Step 5: conftest mechanism test

`tests/test_root_conftest.py`:

```python
"""Root conftest puts the repo root on sys.path."""
import sys


def test_repo_root_importable():
    assert any(p.endswith("rtf-llm") for p in sys.path[:3]) or "modules" in sys.modules
```

(Tighten to an exact assertion once you see how conftest orders the path.)

**Verify**: full new-test selection green; `uv run pytest -q` green.

## Done criteria

ALL must hold:

- [ ] Root `conftest.py` exists containing ONLY the sys.path bootstrap
- [ ] Four new/extended test files exist and pass
- [ ] `uv run pytest -q` → all pass, count ≥ 153 + your additions
- [ ] `uv run ruff check .` → exit 0 (tests are linted)
- [ ] No source files modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:
- Any seam requires network/key/subprocess to test — redesign with fakes;
  if impossible, drop that seam and note why.
- `main.py` grew CLI tests elsewhere meanwhile (skip Step covering it).
- Stream handler semantics changed (plan 050 landed first) — encode NEW
  semantics instead and say so in the docstring.

## Maintenance notes

- These tests are the safety net for plan 050's deletions — sequence 049
  before 050.
- `main.py` remains untested; its engine block shrinks as 040-047 extract
  pure helpers (`build_engine_config`, `construct_transform` consumers) —
  test THOSE helpers where they live.
