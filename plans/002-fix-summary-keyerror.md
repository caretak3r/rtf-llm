# Plan 002 — Fix `KeyError: 'attacks'` crash in the end-of-run summary

- **Finding**: #2 — `main.py`'s final summary block indexes `r['attacks']` directly. Some
  result payloads (comparison; enabled lab modules) have no `'attacks'` key, so the run
  crashes at the very end even though the report was already written.
- **Written against commit**: `e82a0f4`
- **Effort**: S (a couple hours with the test)
- **Risk of this change**: LOW — defensive `.get` swap and safe accumulation; no behavior
  change for the common `--module all` path.

## Why this matters

At `main.py:469-473` the summary is computed with subscripting:

```python
total_attacks = sum(len(r['attacks']) for _, r in results)
successful = sum(sum(1 for a in r['attacks'] if a.get('success', False))
                for _, r in results)
canary_leaks = sum(sum(1 for a in r['attacks'] if a.get('canary_leaked', False))
                   for _, r in results)
```

Two code paths append a result dict that has **no `'attacks'` key**:

1. **Comparison** (`main.py:444-452`): when invoked with `--module comparison` or the
   `--comparison` flag, it calls `runner.run_comparison()` and appends
   `('comparison', comp_result)`. `ComparisonRunner.run_comparison` returns a dict with keys
   `module`, `targets`, `combined_summary` — **no `attacks`** (see `modules/comparison.py:64-73`).
2. **Lab modules** when enabled (`main.py:369-441`): e.g. payload-loader appends
   `('payload_loader', {'status': 'tested', 'encryption': 'success'})` — no `attacks`.
   These are disabled by default in `config.json`, so this path is latent, but it is real
   the moment an operator enables a lab module.

The report itself is generated earlier (`main.py:457`) and `ReportGenerator` already guards
every access with `.get('attacks', [])` (e.g. `report_generator.py:250`), so **only the
summary print crashes**. The exception is caught by the outer `except Exception` at
`main.py:506`, which prints `[!] Error: 'attacks'` and exits 1 — a confusing failure after a
successful run.

## Reproduction (before the fix)

```bash
# No live model needed — comparison with zero configured targets still returns the
# no-'attacks' shape and triggers the crash path.
python main.py --module comparison --no-auth --no-serve 2>&1 | tail -5
```
**Expected before fix**: the run prints the report path, then `[!] Error: 'attacks'`,
exit code 1.

> If the executor's environment can't run `main.py` end-to-end (no reachable model for the
> identity probe at `main.py:259`), rely on the unit test in the Test plan instead, which
> reproduces the exact summing logic in isolation.

## Conventions to follow

- The codebase already uses `dict.get('attacks', [])` defensively in `report_generator.py`
  — match that idiom exactly.

## Files in scope

- `main.py` — only the summary block at lines 469-480.
- `tests/test_summary_counts.py` (new; only if plan 001 has landed / `tests/` exists).

## Files explicitly OUT of scope

- `modules/comparison.py` and the lab modules — do **not** change what they return. The fix
  belongs in the aggregation, which must tolerate heterogeneous result shapes.
- `modules/report_generator.py` — already correct; leave it.

## The change

Replace the three subscript expressions in `main.py:469-473` so they read attacks
defensively, and make the "successful"/"canary" counts fall back to a module's `summary`
when it has no per-attack list (so comparison totals still show up in the printed summary).

Current (`main.py:469-480`):

```python
        total_attacks = sum(len(r['attacks']) for _, r in results)
        successful = sum(sum(1 for a in r['attacks'] if a.get('success', False)) 
                        for _, r in results)
        canary_leaks = sum(sum(1 for a in r['attacks'] if a.get('canary_leaked', False))
                           for _, r in results)
        print(f"\n{Fore.YELLOW}[*] Summary:{Style.RESET_ALL}")
        print(f"  Total attacks: {total_attacks}")
        print(f"  Successful: {Fore.RED}{successful}{Style.RESET_ALL}")
        print(f"  Failed: {Fore.GREEN}{total_attacks - successful}{Style.RESET_ALL}")
```

Replace with:

```python
        def _module_counts(r):
            attacks = r.get('attacks') or []
            if attacks:
                total = len(attacks)
                succ = sum(1 for a in attacks if a.get('success', False))
                canary = sum(1 for a in attacks if a.get('canary_leaked', False))
                return total, succ, canary
            # Fall back to a summary block (comparison / lab-module shapes).
            summary = r.get('summary', {})
            total = summary.get('total', 0)
            succ = summary.get('successful', 0)
            return total, succ, 0

        counts = [_module_counts(r) for _, r in results]
        total_attacks = sum(c[0] for c in counts)
        successful = sum(c[1] for c in counts)
        canary_leaks = sum(c[2] for c in counts)
        print(f"\n{Fore.YELLOW}[*] Summary:{Style.RESET_ALL}")
        print(f"  Total attacks: {total_attacks}")
        print(f"  Successful: {Fore.RED}{successful}{Style.RESET_ALL}")
        print(f"  Failed: {Fore.GREEN}{total_attacks - successful}{Style.RESET_ALL}")
```

Leave the following `if getattr(llm_client, 'canary_token', None):` block that prints
`canary_leaks` unchanged — it already reads the `canary_leaks` variable you just computed.

> This mirrors `ReportGenerator._module_counts` (`report_generator.py:248-260`) deliberately.
> Do not import that method here (it's a staticmethod on a class main.py doesn't otherwise
> need for this); a small local helper keeps the summary block self-contained.

## Done criteria (machine-checkable)

```bash
python -m py_compile main.py                      # exit 0
grep -n "r\['attacks'\]" main.py || echo "no raw subscripts remain"   # prints the echo line
python main.py --module comparison --no-auth --no-serve 2>&1 | grep -c "Error: 'attacks'"  # -> 0
```
- No occurrence of `r['attacks']` (raw subscript) remains in `main.py`.
- The comparison invocation completes without the `Error: 'attacks'` line and exits 0
  (it may still print "No comparison targets defined" — that's expected and fine).

## Test plan

Only if `tests/` exists (plan 001 landed). Add `tests/test_summary_counts.py` that exercises
the exact summing logic against the three real result shapes:

```python
# Mirrors the fixed aggregation in main.py so a regression re-introduces a failure here.
def module_counts(r):
    attacks = r.get('attacks') or []
    if attacks:
        total = len(attacks)
        succ = sum(1 for a in attacks if a.get('success', False))
        canary = sum(1 for a in attacks if a.get('canary_leaked', False))
        return total, succ, canary
    summary = r.get('summary', {})
    return summary.get('total', 0), summary.get('successful', 0), 0


def test_attack_shaped_result():
    r = {'attacks': [{'success': True, 'canary_leaked': True},
                     {'success': False}]}
    assert module_counts(r) == (2, 1, 1)


def test_comparison_shaped_result_no_attacks_key():
    r = {'module': 'comparison',
         'combined_summary': {'total_attacks': 5},
         'summary': {'total': 5, 'successful': 2}}
    # No 'attacks' key -> must not raise; falls back to summary.
    assert module_counts(r) == (5, 2, 0)


def test_lab_module_shaped_result():
    r = {'status': 'tested', 'encryption': 'success'}  # payload_loader shape
    assert module_counts(r) == (0, 0, 0)
```

If plan 001 has **not** landed, skip the test file (do not create `tests/` alone here) and
rely on the `Done criteria` reproduction command instead. Note that in your final report.

## Maintenance note

The real root cause is that `results` holds heterogeneous shapes (some modules return
per-attack lists, comparison returns nested per-target data, lab modules return status
dicts). Finding #5 (`BaseAttackModule`) and finding #6 (unified registry) would normalize
this. Until then, any new code that iterates `results` must use `.get('attacks', [])`, never
subscripting.

## Escape hatches — STOP and report instead of improvising

- If you discover the summary block has already been refactored (line numbers moved / no raw
  subscript present), STOP — the finding may be stale for this commit. Report what you found.
- If running `main.py` requires network access the executor doesn't have, do not stub out the
  model identity probe — just skip the live reproduction and verify via the unit test +
  `py_compile` + the `grep` check.
