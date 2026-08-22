# Plan 041: Triage public Pages exposure of transcripts and operator paths

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat a6a9a9d..HEAD -- .gitignore modules/report_generator.py scripts/build_pages_index.py`
> If these changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P0
- **Effort**: S–M
- **Risk**: MEDIUM (changes what the public site contains — maintainer-visible)
- **Depends on**: none (maintainer decision required in Step 4)
- **Category**: security / data exposure
- **Planned at**: commit `a6a9a9d`, 2026-08-21
- **Supersedes**: run-1 unplanned backlog item "auto-publish of engagement output"

## Why this matters

The repo is private, but the Pages site is **public**: `gh api
repos/caretak3r/rtf-llm/pages` returns `{"html_url":
"http://silent.engineer/rtf-llm/", "public": true, "status": "built"}`.
`.github/workflows/deploy-pages.yml` triggers on every push to `main`
(lines 3-5) and deploys the `_site` artifact (lines 39-42, 52-54), which
`scripts/build_pages_index.py` builds by recursively collecting EVERY
`*.html` under `docs/reports/` (`collect_reports`, line 269:
`reports_dir.rglob("*.html")`) and copying them into the site
(`mirror_reports`, lines 300-306).

Currently published, git-tracked (verified via `git ls-files`):

- 40 files under `docs/reports/` — full sweep transcripts with model
  responses (`include_responses: true` in `config.json` reporting block).
- `opencode_campaign/{dashboard.html,report.json,report.md}` — campaign
  transcripts whose model responses quote absolute operator paths
  (`/Users/rohit/.claude/CLAUDE.md`, `/Users/rohit/Documents/red-teaming/...`)
  and describe the operator's agent environment.

Additionally, `modules/report_generator.py:167-170` embeds
`target_system_prompt` and `canary_token` into report metadata and renders
them into the HTML dashboard (lines ~931-959). The day a real client system
prompt is tested, it auto-publishes.

This plan stops NEW exposure. Whether to scrub history / take down already-
published content is the maintainer's call (Step 4) — the executor must NOT
rewrite history or touch the Pages deployment.

**Hard Rule 4**: never reproduce secret values or private file contents in
commits, tests, or this plan's outputs. Reference by path only.

## Current state

Excerpt (`.gitignore:251-258`) — reports and campaign outputs are NOT ignored:

```
# GitHub Pages local build output
_site/

# Beads / Dolt files (added by bd init)
.dolt/
*.db
.beads-credential-key
.beads/proxieddb/
```

(`*.db` already ignores `rtf.db`.)

Excerpt (`modules/report_generator.py:167-170`):

```python
        if target_system_prompt:
            report_data["metadata"]["target_system_prompt"] = target_system_prompt
        if canary_token:
            report_data["metadata"]["canary_token"] = canary_token
```

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Lint | `uv run ruff check .` | exit 0 |
| Tests | `uv run pytest -q` | all pass |
| Track check | `git ls-files docs/reports opencode_campaign \| wc -l` | 0 after Step 1 |

## Scope

**In scope**:
- `.gitignore` — add report/campaign output patterns.
- `git rm --cached` (untrack, KEEP working-tree files) for the artifacts listed above.
- `modules/report_generator.py` — gate sensitive metadata behind a config flag.
- `config.json` — add the new reporting key with a safe default.
- `README.md` — one short "what gets published" note in the Pages section.

**Out of scope** (do NOT touch):
- Git history (no `filter-repo`/`rebase`/force-push). Maintainer decision only.
- `.github/workflows/deploy-pages.yml` and `scripts/build_pages_index.py` logic — once sources are untracked, the mirror publishes only what remains.
- `docs/` markdown documentation pages (intended public content).

## Git workflow

- Branch: `advisor/041-pages-exposure-triage`
- Commit message: `fix: stop publishing raw transcripts + operator paths to public Pages`
- Do NOT push unless instructed.

## Steps

### Step 1: Untrack generated transcripts (keep files on disk)

```bash
git rm -r --cached docs/reports
git rm --cached opencode_campaign/dashboard.html opencode_campaign/report.json opencode_campaign/report.md
```

Add to `.gitignore` (append near the Pages section):

```
# Run artifacts — local only, never published
docs/reports/
opencode_campaign/
```

**Verify**: `git ls-files docs/reports opencode_campaign | wc -l` → `0`.
`ls docs/reports | head -1` → files still on disk.

### Step 2: Gate sensitive metadata in reports

In `modules/report_generator.py`, change lines 167-170 to respect a
reporting config flag (default OFF):

```python
        publish_meta = bool(
            (self.config or {}).get("reporting", {}).get("publish_sensitive_metadata", False)
        )
        if target_system_prompt and publish_meta:
            report_data["metadata"]["target_system_prompt"] = target_system_prompt
        if canary_token and publish_meta:
            report_data["metadata"]["canary_token"] = canary_token
```

Check how the class stores its config first (`self.config` vs another
attribute — read the `__init__` around line 140 and match the real attribute
name; adjust the snippet accordingly).

In `config.json` `reporting` block add:

```json
        "publish_sensitive_metadata": false,
```

**Verify**: `uv run pytest tests/test_report_generator.py -q` → all pass. If
a test asserts metadata presence, update it to set the flag in the test
config first (follow the file's existing fixture style).

### Step 3: Document what the site publishes

In `README.md`, GitHub Pages section, add one sentence:
"Only committed `docs/*.md` pages are published; run reports and campaign
outputs stay local (gitignored). Enable `reporting.publish_sensitive_metadata`
only if you intentionally want system prompts/canaries in public reports."

**Verify**: `grep -n "publish_sensitive_metadata" README.md` → 1 match.

### Step 4: MAINTAINER DECISION — record, do not execute

Append to `plans/README.md` reconciliation notes: "041 landed; already-
published history (prior commits containing docs/reports + opencode_campaign
transcripts, and the live Pages deployment built from them) requires a
maintainer decision: history rewrite + Pages redeploy, or accept exposure of
already-public content." The executor stops here.

## Test plan

- Extend `tests/test_report_generator.py`: with flag unset (default), report
  dict contains NEITHER `target_system_prompt` NOR `canary_token`; with flag
  true, both appear. Use synthetic values (`"example-system-prompt"`) — never real ones.

## Done criteria

ALL must hold:

- [ ] `git ls-files docs/reports opencode_campaign | wc -l` → 0
- [ ] `grep -n "docs/reports/" .gitignore` and `grep -n "opencode_campaign/" .gitignore` → 1 match each
- [ ] `grep -n "publish_sensitive_metadata" modules/report_generator.py config.json` → matches in both
- [ ] `uv run pytest -q` → all pass
- [ ] `uv run ruff check .` → exit 0
- [ ] No history rewrite performed; working-tree artifacts still present
- [ ] `plans/README.md` status row + Step-4 note updated

## STOP conditions

Stop and report back if:
- `git rm --cached` would touch files outside the listed paths.
- `report_generator.py` metadata block has drifted (different keys or location).
- Any test or doc asks you to embed a real system prompt or canary value.
- The Pages site turns out to be private at execution time (re-run
  `gh api repos/:owner/:repo/pages --jq '.public'`): still land the
  gitignore/metadata parts, but note the severity change in the status row.

## Maintenance notes

- Plan 024 (restrict dashboard serve surface) and 003 (localhost bind)
  address the LAN side of the same data; land independently.
- Plan 043 (campaign canary) re-introduces a canary token into campaign
  runs — it must set `publish_sensitive_metadata` explicitly or route the
  canary through a non-published channel. Coordinate.
- If the maintainer later wants public example reports, add a curated
  `docs/reports-public/` allowlist to `build_pages_index.py` — not a blanket mirror.
