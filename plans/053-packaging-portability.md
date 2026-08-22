# Plan 053: Packaging portability — console script beyond repo root

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat a6a9a9d..HEAD -- pyproject.toml modules/config_manager.py main.py`
> If these changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW–MEDIUM (touches config resolution used by every entry point)
- **Depends on**: none directly; coordinate with 008 (DONE — packaging alignment) findings; plan 005 must land FIRST if the wheel-content item below triggers
- **Category**: packaging / DX
- **Planned at**: commit `a6a9a9d`, 2026-08-21

## Why this matters

The console script declared in `pyproject.toml`
(`rtf-llm = "main:main"`, `[tool.setuptools] py-modules = ["main"]`) only
works when CWD == repo root: `main.py` and `modules/config_manager.py`
resolve `config.json` and data paths relative to CWD. From any other
directory, `rtf-llm --help` works but any real run fails to find
`config.json` (or silently runs with defaults). The uv editable install
masks this locally; the wheel install exposes it.

Secondary packaging nits verified during audit:

- `packages.find` `include = ["modules*", "modules.engine*", ...]` lists
  every subpackage individually — `["modules*"]` suffices and stops
  drifting as packages are added.
- `modules/indirect_injection.py` ships in the wheel despite being
  ruff-excluded dead code (plan 005 deletes it — dependency noted).

## Current state

Verify each claim before acting (line numbers shift):

1. `grep -n "config.json" main.py modules/config_manager.py` — note every
   CWD-relative load site.
2. `grep -n "packages" pyproject.toml` — read the full
   `[tool.setuptools.packages.find]` include list.
3. Reproduce: `cd /tmp && uv run --project /Users/rohit/Documents/red-teaming/rtf-llm python -c "from main import main" `
   then actually exercise a config load from a foreign cwd with
   `ConfigManager()` and observe which file it picks (add a temporary
   print if needed — REMOVE it after).

## Repo conventions to match

- Config precedence today: explicit `--config` flag > `./config.json` >
  defaults. Preserve exactly that order; only ADD a final package-anchor
  fallback for DEFAULT assets (never for user config).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Lint | `uv run ruff check .` | exit 0 |
| Tests | `uv run pytest -q` | all pass |
| Wheel smoke | see Step 3 | `rtf-llm --version`/`--list-transforms` OK from `/tmp` |

## Scope

**In scope**:
- `modules/config_manager.py` — anchored default-config resolution.
- `main.py` — only the config-path resolution call sites it owns.
- `pyproject.toml` — packages.find simplification (+ optional
  `[tool.uv] package = true` verification).
- `tests/test_config_paths.py` (create).

**Out of scope**:
- Deleting `indirect_injection.py` (plan 005's job; this plan only notes
  the wheel consequence).
- Data-file bundling strategy beyond config.json defaults.
- Console-script rename/relocation.

## Git workflow

- Branch: `advisor/053-packaging-portability`
- Commit message: `fix: resolve default config relative to package, not cwd`
- Do NOT push unless instructed.

## Steps

### Step 1: Anchor default config to the package

In `config_manager.py`, add near the top:

```python
_PACKAGE_ROOT = Path(__file__).resolve().parent


def _default_config_path() -> Path:
    """Ship-with defaults, valid from any cwd."""
    candidate = _PACKAGE_ROOT / "config.json"
    return candidate if candidate.exists() else _PACKAGE_ROOT.parent / "config.json"
```

(Choose the anchor matching where config.json actually lives relative to
`modules/` in the installed layout — repo root today. If the wheel should
ship a copy INSIDE the package later, that is a follow-up; document the
chosen anchor in the function docstring.)

Update the ConfigManager resolution chain: explicit flag → `./config.json`
(CWD, unchanged user behavior) → `_default_config_path()` → built-in
DEFAULT_CONFIG dict.

**Verify**: from `/tmp`:
`uv run --project <repo> python -c "from modules.config_manager import _default_config_path; print(_default_config_path())"` → prints the repo-root config.json.

### Step 2: Simplify packages.find

In `pyproject.toml`, collapse the include list to `include = ["modules*"]`.
Confirm `modules.engine.*`, `modules.engine.transforms.*` etc. still ship:
build once and inspect (Step 3 covers this via the smoke install).

### Step 3: Wheel smoke test (the real acceptance)

```bash
uv build
python3 -m venv /tmp/rtf-wheel-test && /tmp/rtf-wheel-test/bin/pip install dist/*.whl
cd /tmp && /tmp/rtf-wheel-test/bin/rtf-llm --list-transforms
```

Expected: exits 0 and lists transforms (no config.json required for that
path). Also confirm `ls /tmp/rtf-wheel-test/lib/*/site-packages/modules/engine | head`
shows engine subpackages present.

Clean up `/tmp/rtf-wheel-test` afterwards.

### Step 4: Tests

Create `tests/test_config_paths.py`:

```python
"""Default-config anchoring is cwd-independent."""
import os


def test_default_path_absolute_and_exists():
    from modules.config_manager import _default_config_path

    p = _default_config_path()
    assert p.is_absolute()
    assert p.exists()


def test_cwd_does_not_change_resolution(tmp_path, monkeypatch):
    from modules.config_manager import ConfigManager

    monkeypatch.chdir(tmp_path)
    cm = ConfigManager()
    assert cm.config.get("engine") is not None or cm.config  # loaded SOMETHING deterministically
```

(Tighten the second assertion to the real observable — e.g. compare
resolved source path attribute if ConfigManager exposes one; read the class
first.)

**Verify**: new tests green from repo root AND via
`cd tests && uv run pytest test_config_paths.py -q` style invocation if
supported; full suite green.

## Done criteria

ALL must hold:

- [ ] Wheel installed at `/tmp`, `rtf-llm --list-transforms` works from `/tmp`
- [ ] `grep -n "_default_config_path" modules/config_manager.py` → present and used in the resolution chain
- [ ] `pyproject.toml` include collapsed to `["modules*"]`
- [ ] New tests pass; `uv run pytest -q` → all pass; `uv run ruff check .` → exit 0
- [ ] No files outside the in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:
- ConfigManager resolution chain differs structurally from the assumed
  flag > cwd > defaults order.
- The wheel smoke reveals modules MISSING from the distribution beyond
  known-dead ones — packaging bug bigger than this plan; report scope.
- `uv build` fails for unrelated reasons (report, don't fight the build).

## Maintenance notes

- After this lands, CI could gain a wheel-smoke job (two commands) — propose
  separately, do not add here.
- If plan 005 deletes `indirect_injection.py` first, the wheel gets cleaner
  automatically; re-run Step 3 to confirm.
