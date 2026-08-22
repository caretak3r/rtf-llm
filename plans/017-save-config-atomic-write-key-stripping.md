# Plan 017: Harden `save_config` — atomic write + complete key stripping

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- modules/config_manager.py`
> If this file changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

`ConfigManager.save_config` has two defects. (1) It writes `config.json` with a
non-atomic truncate-then-`json.dump` — a crash or Ctrl+C mid-write leaves a
truncated/partial-JSON file; the next launch hits `JSONDecodeError` and silently
falls back to defaults, wiping every operator customization. (2) It strips only
`llm.api_key` and `providers[*].api_key`, but `JUDGE_API_KEY` is loaded into
`config['judge']['api_key']` (env-var mapping at line 155) and is **not**
stripped — a live key could be written to the tracked `config.json`. The prior
audit's clearance ("save_config strips keys") is incomplete for this key. This
finding supersedes that recorded clearance.

**Hard Rule 4 (no secret values)**: this plan references credential types and
locations only — never a value. If a `judge.api_key` was previously committed,
recommend rotation.

## Current state

- `modules/config_manager.py` — `ConfigManager` class. `save_config` at lines
  225-243. Env-var mapping at lines 148-168 (line 155: `'JUDGE_API_KEY': ('judge', 'api_key')`).
- `modules/judge_evaluator.py:53-59` — `JudgeEvaluator.__init__` reads
  `judge.mode/fallback_on_error/temperature/max_tokens` but **not**
  `judge.api_key` (it reuses the passed-in `llm_client`). So `judge.api_key`
  is dead config that `save_config` fails to strip.

Excerpt (`modules/config_manager.py:225-243`):

```python
    def save_config(self, path: str = None):
        """Save configuration to file"""
        save_path = path or self.config_path

        # Don't save API keys to file
        config_to_save = json.loads(json.dumps(self.config))

        # Remove API keys from saved config
        if 'llm' in config_to_save:
            config_to_save['llm']['api_key'] = None

        if 'providers' in config_to_save:
            for provider in config_to_save['providers']:
                config_to_save['providers'][provider]['api_key'] = None

        with open(save_path, 'w') as f:
            json.dump(config_to_save, f, indent=2)

        print(f"{Fore.GREEN}[+] Configuration saved to {save_path}{Style.RESET_ALL}")
```

Two problems: (a) `open(save_path, 'w')` truncates before `json.dump`
completes — not atomic; (b) only `llm.api_key` and `providers[*].api_key` are
nulled — `judge.api_key` (and any other `*_api_key`/`api_key` field) survives.

### Repo conventions to match

- `modules/config_manager.py` uses `json` + `os` (already imported at top of file — verify).
- Uses `colorama` `Fore`/`Style` for output (see line 243).
- Atomic-write convention: temp file in same dir + `os.replace` (atomic on POSIX/Windows).

## Commands you will need

| Purpose   | Command | Expected on success |
|-----------|---------|---------------------|
| Lint      | `uv run ruff check modules/config_manager.py` | exit 0 |
| Typecheck | `uv run mypy modules/config_manager.py` | exit 0 |
| Tests     | `uv run pytest -q` (requires plan 001) | all pass |

## Scope

**In scope** (the only files you should modify):
- `modules/config_manager.py` — `save_config` method only.
- `tests/test_config_save.py` (create — depends on plan 001).

**Out of scope** (do NOT touch):
- `modules/judge_evaluator.py` — do NOT wire `judge.api_key` into it (that's a separate decision; the fix here is to strip it, not to use it). The dead-key wiring/​removal overlaps plan 004 (dead config keys).
- `config.json` — do not modify the tracked file.
- `main.py` — `save_config` is not called from the CLI flow; do not add a caller.

## Git workflow

- Branch: `advisor/017-save-config-atomic-strip`
- Commit message: `fix: atomic save_config + strip all api_key fields`
- Do NOT push unless instructed.

## Steps

### Step 1: Rewrite save_config with atomic write + recursive key stripping

Replace the body of `save_config` (lines 225-243) with:

```python
    def save_config(self, path: str = None):
        """Save configuration to file (atomically, without credentials)."""
        save_path = path or self.config_path

        # Deep copy so we don't mutate the live config
        config_to_save = json.loads(json.dumps(self.config))

        # Recursively strip every api_key / *_api_key field
        _strip_api_keys(config_to_save)

        # Atomic write: temp file in same dir, then os.replace
        tmp_path = save_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(config_to_save, f, indent=2)
        os.replace(tmp_path, save_path)

        print(f"{Fore.GREEN}[+] Configuration saved to {save_path}{Style.RESET_ALL}")
```

Add a module-level helper function (above the class, or as a `@staticmethod`)
that recursively walks the config tree and nulls any key named `api_key` or
ending in `_api_key`:

```python
def _strip_api_keys(obj):
    """Recursively set every api_key / *_api_key field to None in-place."""
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if key == 'api_key' or key.endswith('_api_key'):
                obj[key] = None
            else:
                _strip_api_keys(obj[key])
    elif isinstance(obj, list):
        for item in obj:
            _strip_api_keys(item)
```

Verify `os` is imported at the top of `modules/config_manager.py` (it should
be; if not, add `import os`).

**Verify**: `grep -n 'os.replace' modules/config_manager.py` → 1 match. `grep -n '_strip_api_keys' modules/config_manager.py` → ≥2 matches (def + call). `uv run ruff check modules/config_manager.py` → exit 0.

### Step 2: Add regression tests

Create `tests/test_config_save.py` (depends on plan 001's harness):

```python
"""Tests for ConfigManager.save_config atomicity and key stripping."""
import json
import os
import tempfile
from modules.config_manager import ConfigManager, _strip_api_keys


def test_strip_api_keys_recursive():
    cfg = {
        'llm': {'api_key': 'secret-llm'},
        'providers': {'openai': {'api_key': 'secret-openai'}},
        'judge': {'api_key': 'secret-judge', 'mode': 'both'},
        'nested': {'deep': {'custom_api_key': 'secret-deep'}},
    }
    _strip_api_keys(cfg)
    assert cfg['llm']['api_key'] is None
    assert cfg['providers']['openai']['api_key'] is None
    assert cfg['judge']['api_key'] is None          # the bug — was not stripped
    assert cfg['judge']['mode'] == 'both'           # non-key fields preserved
    assert cfg['nested']['deep']['custom_api_key'] is None


def test_save_config_is_atomic_and_strips_keys(tmp_path):
    save_path = str(tmp_path / 'config.json')
    cm = ConfigManager.__new__(ConfigManager)
    cm.config = {
        'llm': {'api_key': 'secret-llm', 'model': 'auto'},
        'judge': {'api_key': 'secret-judge', 'mode': 'both'},
    }
    cm.config_path = save_path
    cm.save_config()
    with open(save_path) as f:
        saved = json.load(f)
    assert saved['llm']['api_key'] is None
    assert saved['judge']['api_key'] is None        # judge key stripped
    assert saved['llm']['model'] == 'auto'          # non-key preserved
    assert not os.path.exists(save_path + '.tmp')   # temp cleaned up by os.replace
```

**Verify**: `uv run pytest tests/test_config_save.py -q` → all pass. (If plan 001's harness is absent, STOP and defer tests; the code fix in step 1 can proceed.)

## Test plan

- `tests/test_config_save.py` (above) — covers recursive stripping (incl. `judge.api_key`) + atomic write (temp file cleaned up).
- Edge case: empty config, nested lists containing dicts with `api_key`.
- Verification: `uv run pytest tests/test_config_save.py -q` → all pass.

## Done criteria

ALL must hold:

- [ ] `grep -n 'os.replace' modules/config_manager.py` returns 1 match
- [ ] `grep -n '_strip_api_keys' modules/config_manager.py` returns ≥2 matches
- [ ] `uv run ruff check modules/config_manager.py` exits 0
- [ ] `uv run mypy modules/config_manager.py` exits 0
- [ ] `uv run pytest tests/test_config_save.py -q` exits 0 (if 001 landed)
- [ ] No secret values appear anywhere in the plan or test (only placeholders like `'secret-llm'`)
- [ ] No files outside the in-scope list are modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:
- `modules/config_manager.py` has drifted from the excerpt (e.g. `save_config` signature changed).
- `os` is not importable or already used differently — report.
- You find that `judge.api_key` IS read somewhere (the audit found it is not — `JudgeEvaluator.__init__` reuses the llm_client). If it is wired, do NOT strip it without also wiring it; report the contradiction.
- A previously committed `config.json` contains a real `judge.api_key` value — do NOT reproduce it; report the file:line + credential type and recommend rotation (Hard Rule 4).

## Maintenance notes

- **Supersedes the prior clearance** in `plans/README.md` ("Hardcoded secrets — save_config strips keys"). That clearance is now corrected: stripping is recursive as of this plan.
- The `judge.api_key` dead-key question (wire it into `JudgeEvaluator` vs remove the env mapping) overlaps plan 004 (dead config keys). This plan strips it defensively; plan 004 decides its fate. Coordinate so both don't conflict.
- A reviewer should confirm `os.replace` is atomic on the target platforms (it is, on POSIX and Windows ≥3.3).
- Future: if `save_config` gains a caller in `main.py` (e.g. a `--save-config` flag), the atomic write protects it automatically.
