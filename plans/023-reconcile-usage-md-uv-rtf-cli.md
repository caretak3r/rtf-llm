# Plan 023: Reconcile `USAGE.md` with `uv` and the `rtf-llm` CLI

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- USAGE.md`
> If this file changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: docs
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

`USAGE.md` contradicts the README and the current tooling. It tells users to
`pip install -r requirements.txt` and run `python main.py --api-key ...`, and
shows a `config.json` example with `"api_key": "your-key"` and a `"format":
"json"` schema that doesn't match the current `reporting` section. The README
(aligning with plan 008) uses `uv sync` / `uv run python main.py` / `rtf-llm`.
A new user following `USAGE.md` gets a working-but-wrong install path and a
stale config schema. Stale docs are worse than missing (playbook §8).

## Current state

- `USAGE.md` — 272-line usage guide. Stale sections below.

Stale excerpts (file:line):

**Install** (`USAGE.md:15-22`):
```bash
## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys in config.json or via CLI
```
```

**Run commands** (`USAGE.md:31`, `:43`, `:55`, `:67`, `:78`, `:144`, etc.) — all use `python main.py` instead of `uv run python main.py` or `rtf-llm`:
```bash
python main.py --module prompt-injection \
  --api-key YOUR_API_KEY \
  --provider openai \
  --model gpt-4 --intensity high
```

**Stale config example** (`USAGE.md:93-112`):
```json
{
  "llm": {
    "provider": "openai",
    "api_key": "your-key",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "attacks": {
    "enable_prompt_injection": true,
    "enable_jailbreak": true
  },
  "reporting": {
    "output_dir": "reports",
    "format": "json",
    "include_responses": true
  }
}
```

This doesn't match the current `config.json` schema (see `config.json`:
`reporting` uses `output_dir` + `format` but the actual file has different keys;
`attacks` uses `enable_*` booleans that may not match; `api_key` should be
loaded via env var, not hardcoded in the example).

### Repo conventions to match

- README uses `uv sync`, `uv run python main.py`, and `rtf-llm` (the console script from plan 008).
- API keys: load via `--api-key "$OPENAI_API_KEY"` or env var (`LLM_API_KEY`), not hardcoded in config.json (config.json `api_key` defaults to `"not-needed"` placeholder).
- `--no-auth` flag skips the authorization prompt (see README:191).

## Commands you will need

| Purpose   | Command | Expected on success |
|-----------|---------|---------------------|
| File check| `grep -c 'pip install -r requirements' USAGE.md` | 0 (after fix) |
| File check| `grep -c 'python main.py' USAGE.md` | 0 (after fix) |

## Scope

**In scope** (the only file you should modify):
- `USAGE.md`

**Out of scope** (do NOT touch):
- `README.md` — already correct (uv/rtf-llm); do not change.
- `config.json` — the tracked config is correct; only the USAGE.md *example* is stale.
- `docs/*.md` — per-module docs; not in scope.

## Git workflow

- Branch: `advisor/023-usage-md-reconcile`
- Commit message: `docs: reconcile USAGE.md with uv and rtf-llm CLI`
- Do NOT push unless instructed.

## Steps

### Step 1: Fix the Installation section

Replace the `## Installation` block (`USAGE.md:15-22`) with:

```markdown
## Installation

```bash
# Install dependencies (managed by uv)
uv sync --group dev

# Or install the framework as a package
uv pip install .

# Verify the CLI works
uv run rtf-llm --help

# Configure API keys via env var or --api-key (not hardcoded in config.json)
export LLM_API_KEY="your-key"
```
```

**Verify**: `grep -n 'pip install -r requirements' USAGE.md` → no matches.

### Step 2: Replace all `python main.py` with `uv run python main.py` or `rtf-llm`

For each run-command example, replace `python main.py` with `uv run rtf-llm`
(the console script). For example (`USAGE.md:31`):

```bash
uv run rtf-llm --module prompt-injection \
  --api-key "$OPENAI_API_KEY" \
  --provider openai \
  --model gpt-4 --intensity high
```

Apply to all run-command blocks in the file (sections: Prompt Injection,
Jailbreak, System Prompt Extraction, Data Extraction, Comprehensive, Custom
Configuration, Custom Provider, Report Generation, Examples 1–3). Use
`--api-key "$OPENAI_API_KEY"` (env var reference) instead of literal
`YOUR_API_KEY` / `sk-...`.

**Verify**: `grep -n 'python main.py' USAGE.md` → no matches. `grep -n 'YOUR_API_KEY\|sk-\.\.\.' USAGE.md` → no matches.

### Step 3: Fix the stale config.json example

Replace the `config.json` example (`USAGE.md:93-112`) with one matching the
actual schema. Read `config.json` to get the real keys, then write:

```json
{
  "llm": {
    "provider": "openai",
    "api_key": "not-needed",
    "model": "auto",
    "base_url": "http://localhost:8081/v1",
    "temperature": 0.7,
    "max_tokens": 2000,
    "timeout": 120
  },
  "reporting": {
    "output_dir": "docs/reports",
    "format": "json"
  },
  "rate_limiting": {
    "delay_between_requests": 1.0
  }
}
```

Key corrections: `api_key` is `"not-needed"` (load real keys via env var); `model` is `"auto"` (auto-detect, per README:23); `output_dir` is `docs/reports` (per README:144); drop the stale `attacks.enable_*` and `reporting.include_responses` keys unless they exist in the real `config.json` (verify first).

**Verify**: `grep -n '"api_key": "your-key"' USAGE.md` → no matches. `grep -n 'output_dir' USAGE.md` → matches the corrected example.

### Step 4: Verify no stale references remain

**Verify**: `grep -nE 'pip install -r requirements|python main\.py|your-key|sk-\.\.\.' USAGE.md` → no matches.

## Test plan

- No tests — this is a documentation file. The grep checks in steps 1–4 are the verification.
- Cross-check: every command in USAGE.md should be runnable (copy-paste safe). Spot-check the install + one run command against the README.

## Done criteria

ALL must hold:

- [ ] `grep -n 'pip install -r requirements' USAGE.md` returns no matches
- [ ] `grep -n 'python main.py' USAGE.md` returns no matches
- [ ] `grep -n 'your-key' USAGE.md` returns no matches
- [ ] `grep -n 'sk-\.\.\.' USAGE.md` returns no matches
- [ ] The config.json example uses `"api_key": "not-needed"` and `docs/reports` output_dir
- [ ] No files outside `USAGE.md` are modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:
- `USAGE.md` has been rewritten since this plan was written (line numbers won't match).
- The real `config.json` schema has keys not shown in the corrected example — read `config.json` and match it exactly; do not invent keys.
- A run command references a flag that no longer exists (verify against `uv run rtf-llm --help`) — update or remove it; don't leave broken commands.

## Maintenance notes

- After this lands, USAGE.md and README.md should agree on install/run commands. If one drifts again, update both.
- A reviewer should copy-paste the install + one run command into a clean env to confirm they work.
- If a `--scan`/`posture` turnkey subcommand is added later (see direction findings), USAGE.md should lead with it; this plan just reconciles to the current `rtf-llm --module` interface.
