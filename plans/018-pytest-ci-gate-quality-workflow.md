# Plan 018: Add pytest CI gate to the quality workflow

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- .github/workflows/quality.yml`
> If this file changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plans/001-test-baseline.md (the gate has nothing to run until 001 lands tests; land this plan together with or right after 001)
- **Category**: dx
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

`.github/workflows/quality.yml` runs `ruff check`, `ruff format --check`, and
`mypy` — but **no pytest step**. Style and type regressions are gated; behavioral
regressions are not. `pytest` is already in the `dev` dependency group, so the
tool is provisioned but never invoked in CI. Plan 001 establishes the test
harness; without this plan, those tests run only locally and are not enforced
on PRs. The safety net 001 exists to provide is unenforced.

## Current state

- `.github/workflows/quality.yml` — CI workflow. Currently untracked in git
  (working-tree new file) but matching plan 008's spec.

Excerpt (`.github/workflows/quality.yml:27-37`):

```yaml
      - name: Sync dependencies (including dev)
        run: uv sync --group dev

      - name: Ruff check
        run: uv run ruff check .

      - name: Ruff format check
        run: uv run ruff format --check .

      - name: Mypy typecheck
        run: uv run mypy modules/ main.py
```

There is no `pytest` step after the mypy step.

### Repo conventions to match

- CI uses `uv sync --group dev` then `uv run <tool>`. Match this pattern.
- Python version in CI is 3.12 (`quality.yml:20`); venv is 3.14 locally. The pytest step must work on 3.12.
- `pytest` is listed in `pyproject.toml` `[dependency-groups] dev` — no extra install needed.

## Commands you will need

| Purpose   | Command | Expected on success |
|-----------|---------|---------------------|
| Local test| `uv run pytest -q` | exit 0 (once 001 lands tests; until then, 0 collected is also OK) |
| YAML lint| (visual — no yamllint configured) | steps syntactically valid |

## Scope

**In scope** (the only file you should modify):
- `.github/workflows/quality.yml` — add one pytest step.

**Out of scope** (do NOT touch):
- `pyproject.toml` — pytest is already a dev dep; do not add `[tool.pytest]` here (that's plan 021).
- `main.py`, `modules/*` — no source changes.
- `tests/` dir — created by plan 001, not this plan.

## Git workflow

- Branch: `advisor/018-pytest-ci-gate`
- Commit message: `ci: add pytest step to quality workflow`
- Do NOT push unless instructed.

## Steps

### Step 1: Add the pytest step

In `.github/workflows/quality.yml`, after the `Mypy typecheck` step, add:

```yaml
      - name: Run tests
        run: uv run pytest -q
```

The full steps section becomes: `Sync dependencies` → `Ruff check` →
`Ruff format check` → `Mypy typecheck` → `Run tests`.

**Verify**: `grep -n 'pytest' .github/workflows/quality.yml` → 1 match (the new step). `grep -n 'Run tests' .github/workflows/quality.yml` → 1 match.

### Step 2: Validate the YAML locally

**Verify**: `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/quality.yml'))"` → exit 0 (no YAML parse error). (If `pyyaml` is not installed, skip — the step structure mirrors the existing mypy step exactly, so it is syntactically valid by construction.)

### Step 3: Confirm the step is non-breaking before 001 lands

Before plan 001 creates `tests/`, `uv run pytest -q` with no test dir exits 0
("no tests ran"). So adding this step now does NOT break CI even before tests
exist. Confirm:

**Verify**: `uv run pytest -q` locally → exit 0 (with "no tests ran" or collected tests passing).

## Test plan

- No unit test — this is a CI config change. The verification is that `uv run pytest -q` exits 0 locally and the YAML is valid.
- Once plan 001 lands tests, this gate enforces them automatically.

## Done criteria

ALL must hold:

- [ ] `grep -n 'pytest' .github/workflows/quality.yml` returns 1 match
- [ ] The new step appears after the `Mypy typecheck` step (visual / `grep -n`)
- [ ] `uv run pytest -q` exits 0 locally
- [ ] No files outside `.github/workflows/quality.yml` are modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:
- `quality.yml` has been restructured (e.g. split into multiple jobs) since this plan was written — the step placement may differ; re-derive from current YAML.
- `uv run pytest -q` exits non-zero locally even with no `tests/` dir — pytest may need a config block (plan 021); report and coordinate.
- The repo's CI uses a different test runner convention (check `git log` / other workflows) — match the established convention instead.

## Maintenance notes

- **Dependency on plan 001**: the gate is inert (0 tests) until 001 creates `tests/`. Land 001 + 018 together for the gate to be meaningful on first run.
- A reviewer should confirm the step uses `uv run pytest -q` (quiet, fast) not `pytest` directly (which would bypass the uv venv).
- If tests become slow, add `uv run pytest -q -x` (fail-fast) or split into a separate job with caching. Not needed now.
- This plan and plan 021 (pytest config) are complementary: 021 adds `[tool.pytest.ini_options]` with `testpaths`; 018 adds the CI invocation. Both can land independently.
