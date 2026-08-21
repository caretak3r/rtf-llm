# Plan 052: Small hardening bundle — mitm TLS guard, registry warning, rescore dehardcode

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat a6a9a9d..HEAD -- modules/engine/backends/mitm_proxy.py modules/engine/registry.py scripts/rescore_report.py`
> If these changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: 044 lands FIRST (rescore imports `majority_vote` from its new home)
- **Category**: security-hygiene / robustness
- **Planned at**: commit `a6a9a9d`, 2026-08-21

## Why this matters

Three small defects found during audit:

1. **mitm_proxy downgrades HTTPS upstreams to cleartext**
   (`backends/mitm_proxy.py`): the proxy forwards captured requests to the
   configured upstream over plain HTTP regardless of scheme, so tokens
   sent through the proxy traverse the network unencrypted.
2. **Registry swallows broken transforms** (`registry.py` `_walk_package`):
   an ImportError inside any transform module silently drops it from the
   registry — a typo removes an attack technique with zero diagnostics.
3. **rescore_report.py hardcodes operator specifics**: absolute workdir
   `/Users/rohit/Documents/red-teaming/rtf-llm/opencode_campaign` and model
   id are baked into constants (line ~36), plus a duplicated `continue`
   guard at lines 46-49 (the dedup part is already handled by plan 044's
   majority_vote refactor — this plan finishes the dehardcoding).

## Current state

Read these before editing (exact lines may have shifted):

- `mitm_proxy.py`: find where the outbound request scheme/host is chosen —
  grep `http://` in that file.
- `registry.py:_walk_package`: the bare `except ImportError: continue`.
- `rescore_report.py:30-40`: constants block with the hardcoded paths/model;
  line ~60: where the model name is used for judge construction.

## Repo conventions to match

- Engine prints/warnings use `[!]`; hard failures raise or return
  `[ERROR]` markers (see `opencode_target.py`).
- Scripts take argparse flags; defaults derive from inputs when possible
  (see `run_opencode_campaign.py`'s flag style).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Lint | `uv run ruff check .` | exit 0 |
| Tests | `uv run pytest -q` | all pass |

## Scope

**In scope**: `modules/engine/backends/mitm_proxy.py`,
`modules/engine/registry.py`, `scripts/rescore_report.py`, plus their test
files.

**Out of scope**: dashboard serving (plans 003/024), canary logic (043/044),
proxy protocol features.

## Git workflow

- Branch: `advisor/052-small-hardening`
- Three commits:
  - `fix: refuse cleartext mitm upstreams unless explicitly allowed`
  - `fix: warn on registry transform import failures`
  - `refactor: dehardcode rescore script inputs`

## Steps

### Step 1: mitm upstream TLS guard

In `mitm_proxy.py`, wherever the upstream URL is resolved: if the original
request was https and the resolved upstream would be http, raise (or return
a 502 with a clear body — match how the proxy reports upstream errors)
UNLESS constructor/config flag `allow_insecure_upstream=True`. Add the flag
with default False and a docstring note explaining why.

**Verify**: read the file end-to-end after editing; confirm no remaining
unconditional `http://` upgrade path.

### Step 2: Registry import warning

In `_walk_package`, before `continue` on ImportError:

```python
            except ImportError as exc:
                print(f"[!] registry skipped {mod_name}: {exc}")
                continue
```

Extend the registry test with a broken sibling module case asserting the
warning text and that valid siblings still register.

### Step 3: rescore dehardcode

Replace the constants with argparse flags:

```python
    parser.add_argument("--workdir", default=None, help="campaign output dir (default: ./opencode_campaign)")
    parser.add_argument("--model", default=None, help="model id; default: taken from report.json metadata")
```

Resolution order: flag → report.json metadata field (read the report JSON
to find the real metadata key holding the model, e.g.
`report["metadata"]["model"]` — verify the key) → error out with a clear
message if neither exists. Remove both hardcoded constants.

**Verify**:
`uv run python scripts/rescore_report.py --help` shows both flags; running
against the existing local `opencode_campaign/report.json` (READ-ONLY,
never committed anywhere new) resolves the model from metadata.

### Step 4: Tests

- Registry warning test per Step 2 (tmp_path package fixture, follow
  `tests/test_engine.py` patterns).
- Rescore: unit-test the resolution helper (extract
  `resolve_model(report_path, flag_value)` pure function) — flag wins,
  metadata fallback, missing-both raises.

## Done criteria

ALL must hold:

- [ ] `grep -n "allow_insecure_upstream" modules/engine/backends/mitm_proxy.py` → present, default False
- [ ] `grep -n "registry skipped" modules/engine/registry.py` → 1 match
- [ ] `grep -rn "/Users/rohit" scripts/rescore_report.py` → NO matches
- [ ] `uv run pytest -q` → all pass; `uv run ruff check .` → exit 0
- [ ] No files outside the in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:
- mitm_proxy has no active callers (then Step 1 still lands — it is a
  landmine defusal — but note the module may belong in plan 050's sweep).
- report.json lacks a usable model metadata key (extend the flag-default
  error message instead of guessing).
- 044 has not landed (rescore still has its inline vote loop) — do the
  dehardcode WITHOUT touching the vote loop, and say so.

## Maintenance notes

- If ADR-001 later deletes mitm_proxy entirely, Step 1 dies happily — it is
  cheap insurance either way.
- The rescore script remains a manual recovery tool; long-term it should be
  absorbed into the scoring spine (see plan 044 notes).
