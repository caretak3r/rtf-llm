# Plan 016: Make `--intensity` gate attack count in all modules

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- modules/prompt_injection.py modules/jailbreak.py modules/multi_turn.py modules/data_extraction.py modules/role_confusion.py modules/system_prompt_extraction.py modules/context_injection.py modules/adversarial_inputs.py modules/weight_manipulation.py modules/multimodal_injection.py`
> If any changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: plans/001-test-baseline.md (for characterization tests; the code fix has no hard dependency)
- **Category**: bug
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

`README.md:164` promises `--intensity low` ≈ 50 attacks, `medium` ≈ 100,
`high` ≈ 200, `extreme` ≈ 500+. But only `prompt_injection.py` fully
implements this (cumulative tiered loaders). **8 of 10 modules** store
`self.intensity` and echo it into the result dict but **never use it to filter
patterns** — so `--intensity low` on jailbreak/multi-turn/data-extraction runs
the full battery, identical to `extreme`. An operator running a quick low-intensity
probe gets an expensive full sweep instead of ~50 attacks. The documented
contract is silently violated across most of the attack surface.

## Current state

**The exemplar** — `modules/prompt_injection.py:36-50` (the ONLY full
implementation; match this pattern's intent):

```python
    def _load_attack_patterns(self) -> Dict[str, List[str]]:
        """Load attack patterns grouped by technique category."""
        intensity_levels = ['low', 'medium', 'high', 'extreme']
        current_level = intensity_levels.index(self.intensity)

        loaders = {
            'low': self._get_basic_patterns,
            'medium': self._get_medium_patterns,
            'high': self._get_high_patterns,
            'extreme': self._get_extreme_patterns,
        }

        all_patterns: List[str] = []
        for i in range(current_level + 1):
            all_patterns.extend(loaders[intensity_levels[i]]())
```

**The broken modules** — each stores `self.intensity` in `__init__` and echoes
it in the result dict, but never gates patterns:

| Module | `__init__` line | `_load_*` method | Result-echo line |
|--------|-----------------|------------------|------------------|
| `modules/jailbreak.py` | 27-30 | `_load_jailbreak_patterns` | 397 |
| `modules/multi_turn.py` | 22-25 | (builds flows inline in `run_all_attacks`) | 34 |
| `modules/data_extraction.py` | 18-21 | `_load_extraction_patterns` | 106 |
| `modules/role_confusion.py` | 16-19 | `_load_confusion_patterns` | 139 |
| `modules/system_prompt_extraction.py` | 17-20 | `_load_extraction_methods` | 127 |
| `modules/context_injection.py` | 16-19 | `_load_injection_patterns` | 160 |
| `modules/adversarial_inputs.py` | 18-21 | `_load_adversarial_patterns` | 174 |
| `modules/weight_manipulation.py` | 20-23 | (builds inline) | 229 |

`modules/multimodal_injection.py:218` has one partial guard
(`if self.intensity in ('high', 'extreme')`) for document-upload vectors only.

### Approach

`prompt_injection`'s cumulative-tier approach is semantically ideal but requires
each module to define 4 tiered pattern subsets — a large refactor across 8
modules. This plan instead introduces a **shared count-cap helper** that each
module applies to its loaded patterns. It is deterministic, low-risk, and
honors the README's count contract. (A future plan can upgrade modules to
semantic tiering like `prompt_injection`.)

The budget mapping matches `README.md:164`:
```python
INTENSITY_BUDGETS = {'low': 50, 'medium': 100, 'high': 200, 'extreme': 500}
```
When a module has fewer patterns than the budget, all run (no truncation) —
so `role_confusion` (19 patterns) runs all 19 even at `low`, which is correct.

### Repo conventions to match

- Modules flat under `modules/`, `from modules.X import Y`. Imports at top of file.
- Type hints: `Dict[str, Any]`, `List[str]` (see any module `__init__`).
- Lint: `uv run ruff check .`. Typecheck: `uv run mypy modules/ main.py`.

## Commands you will need

| Purpose   | Command | Expected on success |
|-----------|---------|---------------------|
| Lint      | `uv run ruff check .` | exit 0 |
| Typecheck | `uv run mypy modules/ main.py` | exit 0 |
| Tests     | `uv run pytest -q` (requires plan 001) | all pass |

## Scope

**In scope** (the only files you should modify):
- `modules/_intensity.py` (create — the shared helper)
- `modules/jailbreak.py`
- `modules/multi_turn.py`
- `modules/data_extraction.py`
- `modules/role_confusion.py`
- `modules/system_prompt_extraction.py`
- `modules/context_injection.py`
- `modules/adversarial_inputs.py`
- `modules/weight_manipulation.py`
- `modules/multimodal_injection.py` (extend the existing partial guard to cover all vectors)
- `tests/test_intensity_gating.py` (create — depends on plan 001)

**Out of scope** (do NOT touch):
- `modules/prompt_injection.py` — already fully implements intensity gating; do not change its tiered approach.
- `modules/defense_tester.py` — uses intensity for defense-profile selection, not attack count; leave as-is.
- `modules/comparison.py` — passes `intensity` through to sub-modules (line 150); no change needed (sub-modules handle it).
- `modules/purple_team.py` — passes `intensity` to sub-modules (line 143); no change needed.
- `config.json` — no change.

## Git workflow

- Branch: `advisor/016-intensity-gating`
- Commit per module or one commit: `fix: gate attack count by --intensity in all modules`
- Do NOT push unless instructed.

## Steps

### Step 1: Create the shared helper

Create `modules/_intensity.py`:

```python
"""Shared intensity → attack-count budget helper.

Maps the --intensity CLI flag to a per-module pattern cap, matching
README.md's documented counts (low~50, medium~100, high~200, extreme~500).
When a module has fewer patterns than the budget, all patterns run (no
truncation)."""

from typing import List

INTENSITY_BUDGETS = {
    'low': 50,
    'medium': 100,
    'high': 200,
    'extreme': 500,
}


def cap_by_intensity(patterns: List, intensity: str) -> List:
    """Return at most INTENSITY_BUDGETS[intensity] patterns (first N).
    If the module has fewer patterns than the budget, returns all of them."""
    budget = INTENSITY_BUDGETS.get(intensity, 200)
    if len(patterns) <= budget:
        return patterns
    return patterns[:budget]
```

**Verify**: `uv run ruff check modules/_intensity.py` → exit 0. `uv run mypy modules/_intensity.py` → exit 0.

### Step 2: Wire the helper into each pattern-loading module

For each module in the scope table, find its `_load_*_patterns` method (or the
method that builds the pattern list/dict), and apply `cap_by_intensity` to the
final collection before returning it. Import at top of file:
`from modules._intensity import cap_by_intensity`.

**Example shape** (for a module whose loader returns `Dict[str, List[str]]`):
```python
    def _load_jailbreak_patterns(self) -> Dict[str, List[str]]:
        patterns = { ... }  # existing build
        # Cap each category by intensity
        return {cat: cap_by_intensity(pats, self.intensity) for cat, pats in patterns.items()}
```

For modules that build a flat list:
```python
        patterns = [ ... ]
        return cap_by_intensity(patterns, self.intensity)
```

Apply to all 8 modules in the table. For `multi_turn.py` and
`weight_manipulation.py` (which build inline rather than via a `_load_*`
method), apply the cap to the attack list built inside `run_all_attacks`
before the loop executes them.

**Verify**: `grep -rn 'cap_by_intensity' modules/` → 9 matches (8 modules + the helper definition). `uv run ruff check .` → exit 0.

### Step 3: Extend multimodal_injection's partial guard

`modules/multimodal_injection.py:218` currently gates only document-upload
vectors with `if self.intensity in ('high', 'extreme')`. Apply `cap_by_intensity`
to the other vector lists (image-injection, OCR-payload, etc.) in
`run_all_attacks` so all vectors respect intensity.

**Verify**: `grep -n 'cap_by_intensity' modules/multimodal_injection.py` → at least 1 match. `uv run ruff check modules/multimodal_injection.py` → exit 0.

### Step 4: Add characterization tests

Create `tests/test_intensity_gating.py` (depends on plan 001's harness). Test
shape: instantiate a module with a fake `LLMClient` and assert that
`--intensity low` yields fewer-or-equal patterns than `high` for a module that
has more than 50 patterns. For modules with <50 patterns, assert `low` returns
all of them (no truncation).

```python
"""Characterization tests: --intensity caps attack count per module."""
from modules._intensity import cap_by_intensity, INTENSITY_BUDGETS


def test_cap_by_intensity_truncates_above_budget():
    patterns = list(range(300))
    capped = cap_by_intensity(patterns, 'low')
    assert len(capped) == INTENSITY_BUDGETS['low']  # 50

def test_cap_by_intensity_returns_all_when_below_budget():
    patterns = list(range(19))  # e.g. role_confusion size
    assert cap_by_intensity(patterns, 'low') == patterns

def test_budgets_match_readme_contract():
    assert INTENSITY_BUDGETS == {'low': 50, 'medium': 100, 'high': 200, 'extreme': 500}
```

**Verify**: `uv run pytest tests/test_intensity_gating.py -q` → all pass. (If plan 001's harness is absent, STOP and defer the test; the code fix in steps 1-3 can proceed.)

## Test plan

- `tests/test_intensity_gating.py` (above) — covers the helper contract.
- Recommended per-module smoke (optional): for each module, assert `low` count ≤ `high` count ≤ `extreme` count. These require a fake `LLMClient` (pattern after the stub in plan 013).
- Verification: `uv run pytest tests/test_intensity_gating.py -q` → all pass.

## Done criteria

ALL must hold:

- [ ] `grep -rn 'cap_by_intensity' modules/` returns ≥9 matches (8 modules + multimodal + helper def)
- [ ] `uv run ruff check .` exits 0
- [ ] `uv run mypy modules/ main.py` exits 0
- [ ] `uv run pytest tests/test_intensity_gating.py -q` exits 0 (if 001 landed)
- [ ] No files outside the in-scope list are modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:
- Any module's pattern-loading structure doesn't match a list or dict-of-lists (e.g. it builds named tuples or nested objects) — `cap_by_intensity` assumes list/dict-of-lists; report and adapt.
- A module genuinely should NOT be intensity-gated (e.g. its attack count is semantically fixed) — report which one and why; exclude it rather than forcing a cap.
- `cap_by_intensity` would change which specific attacks run for a module whose patterns are order-dependent (e.g. crescendo sequences) — report; the cap slices first-N which may break a sequence.

## Maintenance notes

- **Comparability caveat**: this changes attack counts for existing modules. Historical reports (docs/reports/) used the uncapped counts; new runs with `--intensity high` may show different totals. Document this in the release notes. The default `high` (budget 200) is intended to approximate the prior full-run behavior for modules with ≤200 patterns.
- A reviewer should verify that no module's pattern list is order-dependent in a way that slicing first-N breaks (crescendo/multi-turn flows are the risk — multi_turn builds flows inline; verify the cap is applied to independent attack units, not mid-sequence).
- Future improvement: upgrade individual modules to prompt_injection's cumulative-tier approach (semantic subsets) instead of count-cap. This plan's helper is the stepping stone.
- `prompt_injection.py` is intentionally untouched — its tiered approach is the gold standard; do not downgrade it to count-cap.
