# Plan 021: Add `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest]` config sections

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- pyproject.toml`
> If this file changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (complementary to plan 018 which adds the pytest CI invocation)
- **Category**: dx
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

`pyproject.toml` has NO `[tool.ruff]`, `[tool.mypy]`, or `[tool.pytest]`
sections. Ruff/mypy/pytest all run on defaults. Concrete cost: `ruff check .`
with no excludes sweeps the **vendored** `prompt-inj-attacks/` subproject
(including `attack.py` with its own `aiohttp`/`ollama`/`openai` deps not in
pyproject) and the dead `new_attacks/` files — generating lint noise on code
the project doesn't own and doesn't ship. There's also no `target-version`, so
ruff doesn't consistently apply py3.10+ syntax rules, and mypy has no
per-module overrides. Plan 008 added the *tools* (ruff/mypy/pytest to dev +
the CI runner) but explicitly scoped itself to "add the tooling, not to fix
pre-existing issues." This plan adds the config that 008 deliberately deferred.

## Current state

- `pyproject.toml` — has `[project]`, `[tool.uv]`, `[project.scripts]`,
  `[dependency-groups]`, `[build-system]`, `[tool.setuptools]`,
  `[tool.setuptools.packages.find]`. No `[tool.ruff]`/`[tool.mypy]`/`[tool.pytest]`.

Excerpt (`pyproject.toml:1-12`):

```toml
[project]
name = "llm-red-team-framework"
version = "0.1.0"
description = "Adversarial LLM red teaming framework"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31.0",
    "colorama>=0.4.6",
    "cryptography>=41.0.0",
    "pycryptodome>=3.19.0",
]
```

The file ends at line 36. The config sections will be appended.

### Repo conventions to match

- `requires-python = ">=3.10"` (line 6) → ruff `target-version = "py310"`.
- CI runs `ruff check .` and `mypy modules/ main.py` — config must keep these working.
- `prompt-inj-attacks/` is vendored and should be excluded from lint/type checks.

## Commands you will need

| Purpose   | Command | Expected on success |
|-----------|---------|---------------------|
| Lint      | `uv run ruff check .` | exit 0 (or only pre-existing findings in modules/) |
| Format    | `uv run ruff format --check .` | exit 0 |
| Typecheck | `uv run mypy modules/ main.py` | exit 0 (or no new errors) |

## Scope

**In scope** (the only file you should modify):
- `pyproject.toml` — append three `[tool.*]` sections.

**Out of scope** (do NOT touch):
- `.github/workflows/quality.yml` — that's plan 018's scope (CI invocation).
- `requirements.txt` — runtime deps only; no tool config there.
- Any source code — this is config-only.
- `prompt-inj-attacks/` — excluded, not fixed. It's vendored.

## Git workflow

- Branch: `advisor/021-ruff-mypy-config`
- Commit message: `chore: add ruff/mypy/pytest config to pyproject.toml`
- Do NOT push unless instructed.

## Steps

### Step 1: Append the config sections to `pyproject.toml`

Append (after the existing `[tool.setuptools.packages.find]` block at the end):

```toml
[tool.ruff]
target-version = "py310"
line-length = 120
extend-exclude = ["prompt-inj-attacks", "docs", "build", ".venv"]

[tool.mypy]
python_version = "3.10"
ignore_missing_imports = true
exclude = ["prompt-inj-attacks/", "build/", ".venv/"]

[[tool.mypy.overrides]]
module = "modules.*"
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-q"
```

Rationale:
- `target-version = "py310"` matches `requires-python = ">=3.10"`.
- `extend-exclude` removes the vendored subproject, docs, build, and venv from ruff's default glob.
- `line-length = 120` — check the existing code's prevailing width first (see STOP conditions); if most lines are ≤100, use 100 instead. 120 is a safe default that avoids reformatting churn.
- mypy `exclude` + `ignore_missing_imports` — the vendored code has deps not in pyproject; excluding it avoids false errors.
- pytest `testpaths = ["tests"]` — matches plan 001's expected layout.

**Verify**: `grep -n 'tool.ruff\|tool.mypy\|tool.pytest' pyproject.toml` → 3 matches. `uv run ruff check .` → exit 0 OR only pre-existing findings in `modules/` (no findings in `prompt-inj-attacks/`).

### Step 2: Verify ruff no longer sweeps vendored code

**Verify**: `uv run ruff check prompt-inj-attacks/ 2>&1 | head -3` → should show the exclude taking effect (no findings, or "excluded"). Then `uv run ruff check .` → no findings originating from `prompt-inj-attacks/` paths.

### Step 3: Verify mypy and format unaffected

**Verify**: `uv run mypy modules/ main.py` → exit 0 (or same error count as before — no new errors). `uv run ruff format --check .` → exit 0 (the `line-length` change should NOT trigger reformatting if set ≥ existing max; if it does, either apply `ruff format .` or lower the setting — but do NOT reformat vendored code).

### Step 4: Check for pre-existing lint findings surfacing

The config may surface pre-existing ruff findings in `modules/` that defaults
masked. If `uv run ruff check .` now fails with findings:

**Verify**: `uv run ruff check .` → if it exits non-zero on `modules/` findings, that is EXPECTED (the config is correct; the findings are pre-existing tech debt). Do NOT fix them in this plan — record them as a follow-up. The plan's done criterion is that `prompt-inj-attacks/` is excluded and `target-version` is set, not that all pre-existing findings vanish. If you want CI to stay green, gate temporarily with `# ruff: noqa` only on the new findings OR defer this plan until a lint-cleanup pass. Report the finding count back.

## Test plan

- No unit tests — this is a config change. The verification is that ruff/mypy/pytest respect the new config.

## Done criteria

ALL must hold:

- [ ] `grep -n '\[tool.ruff\]\|\[tool.mypy\]\|\[tool.pytest' pyproject.toml` returns 3 matches
- [ ] `target-version = "py310"` present in `[tool.ruff]`
- [ ] `extend-exclude` includes `prompt-inj-attacks`
- [ ] `uv run ruff check prompt-inj-attacks/` produces no lint findings (excluded)
- [ ] `uv run mypy modules/ main.py` exits 0 or with no new errors vs. before
- [ ] No source files modified (`git status --short` shows only `pyproject.toml`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:
- The existing code's prevailing line length is much shorter than 120 (e.g. ≤88) — setting 120 could mask long-line issues; check with `uv run ruff format --check .` first and pick a value that doesn't trigger mass reformatting. Report the measured max if uncertain.
- `extend-exclude` breaks an existing ruff invocation (e.g. CI runs `ruff check prompt-inj-attacks/` explicitly — unlikely, but check `quality.yml`).
- Adding `[tool.pytest.ini_options]` causes `uv run pytest -q` to fail before plan 001 creates `tests/` (pytest may warn about a missing testpath) — if it errors rather than warning, add `--ignore-glob` or defer the pytest section until 001 lands.

## Maintenance notes

- **Complementary to plan 018**: 018 adds the pytest CI *invocation*; 021 adds the pytest *config*. Both can land independently; together they make the test gate real.
- If a lint-cleanup pass fixes the pre-existing `modules/` findings surfaced by `target-version`, remove any temporary `noqa` markers at that time.
- A reviewer should confirm `extend-exclude` covers `prompt-inj-attacks` (the vendored tree) — this is the primary value of this plan.
- If `line-length` is later changed, run `uv run ruff format .` to apply consistently across the codebase in one commit (not piecemeal).
