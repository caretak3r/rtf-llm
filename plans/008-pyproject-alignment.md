# Plan 008 — Align Python version requirement with CI and add lint/typecheck tooling

- **Finding**: #8 — `pyproject.toml` requires `python >= 3.14` but `.github/workflows/deploy-pages.yml` uses `python-version: "3.12"`. Python 3.14 is not yet released (as of 2026-07), making the requirement too aggressive and blocking contributors on stable Pythons. Additionally, there is no lint, format, or typecheck configuration — no `ruff`, `mypy`, or similar setup.
- **Written against commit**: `e82a0f4`
- **Effort**: S (roughly an hour)
- **Risk of this change**: LOW — widens Python support and adds dev-only dependencies; touches no runtime code path.

## Why this matters

1. **Accessibility**: A `requires-python = ">=3.14"` requirement means anyone on a stable Python (3.10–3.13) cannot resolve dependencies with `uv sync`. The `uv.lock` file itself is locked to `requires-python = ">=3.14"`, so even manual overrides fail.
2. **CI inconsistency**: The deploy workflow installs Python 3.12, then installs `markdown` directly via `pip`. If `uv` were used there, the resolver would fail because 3.12 does not satisfy the declared `>=3.14` bound.
3. **No quality gate**: There is no automated lint, format, or typecheck step in CI. Without this, style regressions and simple type errors can land on `main` undetected.

## Conventions to follow

- `uv`-managed (`pyproject.toml`, `[tool.uv] package = false`).
- Prefer `[dependency-groups] dev = [...]` over `[project.optional-dependencies] dev` — this is the modern `uv` / PEP-735 convention already used in Plan 001.
- Re-use existing workflow patterns (`actions/setup-python@v5`, `actions/checkout@v4`, `ubuntu-latest`).

## Files in scope

- `pyproject.toml` — lower `requires-python`, add `[dependency-groups] dev`.
- `uv.lock` — regenerate after `requires-python` change.
- `.github/workflows/quality.yml` — new workflow for lint / format / typecheck.
- `README.md` — add a short "Development" subsection.

## Files explicitly OUT of scope

- Any file under `modules/` — **do not fix lint/type errors** surfaced by the new tools; that is follow-up work.
- `main.py`, `generate_report.py`, `config.json`.
- `.github/workflows/deploy-pages.yml` — do not modify; it will naturally use the same Python setup pattern.

## Current-state evidence (verified excerpts)

`pyproject.toml:7`:

```toml
requires-python = ">=3.14"
```

`.github/workflows/deploy-pages.yml:15-17`:

```yaml
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
```

`uv.lock:1-3`:

```toml
version = 1
revision = 3
requires-python = ">=3.14"
```

The framework code itself uses no 3.14-specific syntax (no `type` generics, no `except*` patterns, etc.). The lowest common denominator among active CPython versions is 3.10, which provides `typing` features used in the codebase (e.g. `typing.Union` is still valid, but `X | Y` is used; however `X | Y` as a type hint requires `from __future__ import annotations` on 3.9 and is native on 3.10+). Setting `>=3.10` maximizes contributor compatibility without forcing an unnecessary floor.

## Steps

### Step 1 — Lower the Python requirement in `pyproject.toml`

Change:

```toml
requires-python = ">=3.14"
```

To:

```toml
requires-python = ">=3.10"
```

**Verification**:

```bash
python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['requires-python'])"
```

**Expected**: prints `>=3.10`.

### Step 2 — Regenerate the lockfile

```bash
uv lock
```

**Expected**: `uv.lock` completes without error and its `requires-python` header reflects `>=3.10`.

**Verification**:

```bash
grep '^requires-python' uv.lock
```

**Expected**: `requires-python = ">=3.10"`.

### Step 3 — Add dev dependency group

In `pyproject.toml`, after the `[tool.uv]` block, add (or extend if already present from Plan 001):

```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
]
```

Then sync:

```bash
uv sync --group dev
```

**Expected**: `uv sync` completes and reports `+ ruff==0.X`, `+ mypy==1.X` (and `pytest` if not already present).

### Step 4 — Create the quality workflow

Create `.github/workflows/quality.yml`:

```yaml
name: Quality

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    name: Lint, format, and typecheck
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "0.4.x"

      - name: Sync dependencies (including dev)
        run: uv sync --group dev

      - name: Ruff check
        run: uv run ruff check .

      - name: Ruff format check
        run: uv run ruff format --check .

      - name: Mypy typecheck
        run: uv run mypy modules/ main.py
```

> Note: `setup-uv@v3` is the standard `uv` installer action. If the repo uses a different version of `setup-uv`, match that. The `python-version` is pinned to `"3.12"` (matching the deploy workflow) to keep a single, well-tested Python in CI.

**Verification** (local sanity check — may fail on existing issues; that is expected):

```bash
uv run ruff check .      # likely reports issues; do NOT fix them here
uv run ruff format --check .
uv run mypy modules/ main.py
```

### Step 5 — Document the dev workflow in README

In `README.md`, after the existing "Python Dependency Management" section, add:

```markdown
## Development

Set up the dev environment:

```bash
uv sync --group dev
```

Run quality checks locally:

```bash
uv run ruff check .        # lint
uv run ruff format --check .   # format check (use `uv run ruff format .` to apply)
uv run mypy modules/ main.py   # type check
```

These same checks run automatically on every PR via `.github/workflows/quality.yml`.
```

### Step 6 — Verify CI file exists and is syntactically valid

```bash
python -c "import yaml, sys; list(yaml.safe_load_all(open('.github/workflows/quality.yml')))"
```

**Expected**: exits with code `0` (no YAML parse errors).

## Done criteria (machine-checkable)

1. `python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['requires-python'])"` prints `>=3.10`.
2. `grep '^requires-python' uv.lock` prints `requires-python = ">=3.10"`.
3. `python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print('dev' in d.get('dependency-groups', {}))"` prints `True` (or the equivalent check depending on the exact TOML structure after Plan 001).
4. `.github/workflows/quality.yml` exists and contains the strings `ruff check`, `ruff format --check`, and `mypy`.
5. `README.md` contains a "Development" section with the three `uv run` commands.

## Test plan

- **Local**: Run `uv lock` and `uv sync --group dev` on a Python 3.10+ interpreter. Confirm resolution succeeds.
- **CI**: Push the branch. Confirm the new `Quality` workflow appears in the Actions tab and each step (checkout, setup, sync, ruff, format, mypy) completes without a runner error. It is **acceptable** if ruff or mypy report findings on existing code — the goal of this plan is to *add the tooling*, not to fix pre-existing issues.

## Maintenance note

- If the project later adopts a Python 3.11+ feature (e.g. `typing.Self`, `ExceptionGroup`), raise `requires-python` to `>=3.11` and update the CI `python-version` in both workflows to match.
- If `ruff` or `mypy` versions drift, bump them in `[dependency-groups] dev` and re-run `uv lock`.
- Once existing lint/type issues are fixed, consider adding `--output-format=github` to the ruff steps for better PR annotations.

## Escape hatches

- If `setup-uv@v3` is unavailable or the org blocks third-party actions, replace the `Install uv` step with the official `curl -LsSf https://astral.sh/uv/install.sh | sh` bootstrap and cache `~/.cargo/bin/uv` manually.
- If `mypy` reports so many errors that the workflow is too noisy to be useful, change `run: uv run mypy modules/ main.py` to `run: uv run mypy modules/ main.py || true` temporarily (with a `# TODO: fix mypy errors` comment) and file a follow-up plan.
- If the project already uses `black` or another formatter in preference to `ruff format`, replace the ruff format step with the preferred tool and update the README accordingly.
