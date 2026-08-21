# Plan 051: Live-agent blast radius — scratch workdir + unsafe-flag guard

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat a6a9a9d..HEAD -- modules/llm_client.py scripts/run_opencode_campaign.py`
> If these changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW (adds guardrails; no behavior removed)
- **Depends on**: none directly; 043 touches the same `--workdir` flag — coordinate or land together
- **Category**: safety / live-testing hygiene

## Why this matters

Campaign targets are TOOL-USING AGENTS that execute with the campaign's
`--workdir` as their context root (`opencode_target.py:59`,
`cwd=self.workdir`). Two defaults make a successful jailbreak dangerous:

1. `run_opencode_campaign.py:81` defaults `--workdir` to
   `os.path.expanduser("~")` — the operator's real home directory.
   Observed transcripts confirm agents read real files there
   (`opencode_campaign/report.json` quotes `/Users/rohit/.claude/...`
   paths).
2. The droid CLI provider accepts `--skip-permissions-unsafe`
   (`modules/llm_client.py:674`) with no friction — one flag away from an
   unsandboxed agent following attacker-controlled instructions on the
   host.

A red-team tool should assume its target WILL be compromised mid-campaign
— that is the point of the exercise — and therefore bound what a
compromised target can touch.

## Current state

Excerpt (`scripts/run_opencode_campaign.py:79-84`, verify exact lines):

```python
    parser.add_argument(
        "--workdir",
        default=os.path.expanduser("~"),
        help="agent context root",
    )
```

Excerpt (`modules/llm_client.py`, around line 674 — read the droid command
assembly):

```python
            cmd = ["droid", "exec", "--skip-permissions-unsafe", ...]
```

## Repo conventions to match

- Guardrail warnings use `[!]` prints; hard refusals exit nonzero with a
  clear message (see `main.py` parser.error usage at line ~573).
- Opt-outs are explicit flags, never env-var-only.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Lint | `uv run ruff check .` | exit 0 |
| Tests | `uv run pytest -q` | all pass |

## Scope

**In scope**:
- `scripts/run_opencode_campaign.py` — workdir default + home-dir refusal/warning.
- `modules/llm_client.py` — droid unsafe-flag gate (env opt-in).
- Tests for the new decision logic.

**Out of scope**:
- Sandbox profiles / seatbelt wrappers (future hardening, separate plan).
- 043's canary planting inside the scratch dir (separate concern, same flag).

## Git workflow

- Branch: `advisor/051-live-blast-radius`
- Commits:
  - `fix: default campaign workdir to disposable scratch, refuse $HOME`
  - `fix: require explicit opt-in for droid --skip-permissions-unsafe`

## Steps

### Step 1: Scratch-by-default workdir

Change the `--workdir` default to `None`. Resolution in `main()`:

```python
        if args.workdir is None:
            args.workdir = str(Path(args.out) / f"agent_scratch_{int(time.time())}")
            Path(args.workdir).mkdir(parents=True, exist_ok=True)
            print(f"[*] Agent scratch workdir: {args.workdir}")
```

If the user SUPPLIED a workdir whose resolved path equals the home
directory (or `~`), refuse unless `--allow-home-workdir` was passed:

```python
        if Path(args.workdir).resolve() == Path.home().resolve() and not args.allow_home_workdir:
            parser.error(
                "--workdir points at your HOME directory; pass --allow-home-workdir to accept the risk"
            )
```

Add `--allow-home-workdir` as a store_true flag with a help string that
states the risk plainly.

(043 also modifies this block for canary planting — whoever lands second
reconciles; both changes are additive.)

**Verify**: `uv run python scripts/run_opencode_campaign.py --help` shows
the new flag and no `$HOME` default.

### Step 2: Gate the droid unsafe flag

In `llm_client.py` where the droid command is assembled: keep accepting the
provider choice, but require explicit environment opt-in when the unsafe
permission mode would be used:

```python
import os
...
        if "--skip-permissions-unsafe" in cmd and not os.environ.get("RTF_ALLOW_UNSAFE_DROID"):
            raise RuntimeError(
                "droid --skip-permissions-unsafe requires RTF_ALLOW_UNSAFE_DROID=1 "
                "(a jailbroken agent WILL run commands in the workdir)"
            )
```

Match the module's existing error style (read how other config errors
raise there). Keep the flag itself available — the gate only forces
deliberate opt-in.

**Verify**: `grep -n "RTF_ALLOW_UNSAFE_DROID" modules/llm_client.py` → present.

### Step 3: Tests

Create `tests/test_workdir_guard.py`:

```python
"""Workdir guard: scratch default, home refusal."""
from pathlib import Path


def test_home_refusal_logic(monkeypatch):
    from scripts.run_opencode_campaign import resolve_workdir

    monkeypatch.setenv("HOME", str(Path("/tmp/fakehome")))
    out = resolve_workdir(None, out_dir="/tmp/campout")
    assert "agent_scratch_" in out


def test_explicit_home_requires_optin(monkeypatch):
    from scripts.run_opencode_campaign import resolve_workdir

    monkeypatch.setenv("HOME", "/tmp/fakehome")
    try:
        resolve_workdir("/tmp/fakehome", out_dir="/tmp/x", allow_home=False)
        raised = False
    except SystemExit:
        raised = True
    assert raised
```

Extract the resolution logic into a pure `resolve_workdir(workdir_arg,
out_dir, allow_home)` helper so it is testable without argparse (parser.error
→ SystemExit is acceptable in the helper).

For the droid gate: unit-test the guard function if extracted, else a
focused test constructing the client with a stub and asserting the
RuntimeError message contains `RTF_ALLOW_UNSAFE_DROID`.

**Verify**: new tests green; full suite green.

## Done criteria

ALL must hold:

- [ ] `grep -n 'expanduser("~")' scripts/run_opencode_campaign.py` → NOT the --workdir default anymore
- [ ] `grep -n "allow_home_workdir\|--allow-home-workdir" scripts/run_opencode_campaign.py` → present
- [ ] `grep -n "RTF_ALLOW_UNSAFE_DROID" modules/llm_client.py` → present
- [ ] New tests pass; `uv run pytest -q` → all pass; `uv run ruff check .` → exit 0
- [ ] No files outside the in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:
- The opencode backend resolves cwd somewhere OTHER than the passed
  workdir (guard would be theater — investigate first).
- droid command assembly moved/refactored since the excerpt.
- 043 landed with a conflicting resolution scheme — adopt ONE.

## Maintenance notes

- True containment (sandbox-exec profile per run) is the follow-up worth
  doing before pointing campaigns at COTS agents; tracked as direction,
  not planned yet.
- If ADR-001 promotes the campaign runner into `main.py` as a subcommand,
  these guards move with it — keep them in pure helpers so relocation is
  mechanical.
