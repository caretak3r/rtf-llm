# Plan 007 — Investigate and remove the hardcoded `generate_report.py` script

- **Finding**: #7 — `generate_report.py` is a 945-line standalone script with hardcoded module summaries, attack payloads, and defense test results. It duplicates data already in `modules/*.py` and `modules/technique_kb.py`. It is not imported by the framework and may be unused.
- **Written against commit**: `e82a0f4`
- **Effort**: S (investigation + removal; under an hour if unused)
- **Risk of this change**: LOW if unused; MEDIUM if referenced by undocumented scripts.

## Why this matters

`generate_report.py` maintains a second copy of:
- `MODULE_SUMMARIES` (hardcoded counts per module)
- `CATEGORY_PAYLOADS` (hardcoded attack prompt strings)
- `DEFENSE_TESTER` / `PURPLE_TEAM_R1` (hardcoded defense results)
- `OWASP_CATEGORY_MAP` (duplicates `modules/evaluator.py`)

These are already generated dynamically by `modules/report_generator.py` and stored in actual run outputs. The standalone script appears to be a legacy artifact for generating demo reports without running the framework. If it is unused, it creates drift risk — when attack patterns or OWASP mappings are updated in the live modules, this file becomes stale.

## Conventions to follow

- Preserve the ability to generate demo/representative reports if needed.
- Don't delete anything that has a live reference.
- Match the existing plan style for dead-code removal (see `005-remove-dead-indirect-injection.md`).

## Files in scope

- `generate_report.py` — investigate references, then delete if unused.
- `plans/README.md` — update the index if this plan lands.

## Files explicitly OUT of scope

- `modules/report_generator.py` — the real report generator; leave as-is.
- Any file that references `generate_report.py` as `import generate_report` (if found, STOP — see escape hatches).

## Evidence (verified)

```bash
$ head -5 generate_report.py
# Generate the full sweep report from the partial run captured in
# /tmp/redteam_sweep.log. Populates each attack with the actual pattern /
# payload string the framework would have sent...
```

```bash
$ grep -rn --include='*.py' 'generate_report' . | grep -v 'generate_report.py:'
# No results expected — this confirms nothing imports it.
```

```bash
$ grep -rn 'generate_report.py' .github/ scripts/ docs/
# No results expected — not referenced in CI or scripts.
```

If the above commands return any references, STOP and report (see escape hatches).

## Steps

### Step 1 — Re-verify it is unreferenced

```bash
grep -rn --include='*.py' 'generate_report' . | grep -v 'generate_report.py:'
grep -rn 'generate_report.py' .github/ scripts/ docs/ 2>/dev/null
```

**Expected**: both return empty. If not, STOP — see escape hatches.

### Step 2 — Confirm it is syntactically standalone (no hidden import side effects)

```bash
python -m py_compile generate_report.py
```

**Expected**: exit 0. If it fails to compile, note it but proceed — compilation failure doesn't make the file "used."

### Step 3 — Delete the file

```bash
git rm generate_report.py
```

### Step 4 — Verify no import side effects broke the module graph

```bash
python -c "import main; print('import ok')"
```

**Expected**: `import ok`. This confirms `main.py` and the module graph do not transitively depend on `generate_report.py`.

## Done criteria (machine-checkable)

```bash
test ! -f generate_report.py && echo "deleted"
python -c "import main; print('import ok')"
```

- `generate_report.py` no longer exists.
- The full module graph still imports cleanly via `import main`.

## Test plan

No new test file required. The "unreferenced" verification in Step 1 is the test.

## Maintenance note

If a future need arises for generating synthetic/demo reports without a live LLM target, implement it as:
1. A thin CLI wrapper around `ReportGenerator` that reads a JSON result file, or
2. A `--demo` flag in `main.py` that uses mock LLM responses.

Do not reintroduce a hardcoded standalone script that duplicates module data.

## Escape hatches — STOP and report instead of improvising

- If Step 1 finds any import or shell reference to `generate_report.py`, STOP — the file is used. Report the reference and do not delete.
- If the file contains unique functionality not in `modules/report_generator.py` (e.g. a different report format), STOP — report the unique capability and recommend a consolidation plan instead of deletion.
