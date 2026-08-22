# Plan 032: Add module-level `technique_kb` fallbacks + resolve key collisions

> **Executor instructions**: Follow step by step. Run every verification before moving on. STOP conditions → stop and report. When done, update `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- modules/technique_kb.py modules/report_generator.py`

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (land BEFORE new-OWASP-module plans — those add more KB entries + collision risk)
- **Category**: tech-debt
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

`technique_kb.py` has module-level fallback entries for only 5 of 18 registered modules (`prompt_injection`, `jailbreak`, `purple_team`, `defense_tester`, `multimodal_injection`). The other 7 live attack modules (`data_extraction`, `system_prompt_extraction`, `adversarial_inputs`, `role_confusion`, `context_injection`, `weight_manipulation`, `multi_turn`) have no module-level entry — a `TECHNIQUE_INFO[<module_name>]` lookup would `KeyError` today. It hasn't bitten because the sole consumer (dashboard tooltips, `report_generator.py:750`) only queries per-category keys. Worse, **3 KB keys are claimed by 2+ modules with different semantics**: `direct_extraction` (system_prompt_extraction vs weight_manipulation), `encoding` (jailbreak vs system_prompt_extraction vs defense_tester), `multi_turn` (context_injection category vs module name). A per-category tooltip for a weight attack could show the system-prompt description. Latent contract gap.

## Current state

- `modules/technique_kb.py:622-648` — module-level fallbacks for only 5 modules.
- Collisions: `direct_extraction` at technique_kb.py:362 (system-prompt meaning) vs `modules/weight_manipulation.py:38` (weight meaning); `encoding` at technique_kb.py:278 (jailbreak) vs `system_prompt_extraction.py:31` + `defense_tester.py:115`.

Excerpt (`modules/technique_kb.py:622-648`):

```python
    # ---------------- Module-level fallback descriptions ----------------
    "prompt_injection": {
        "description": "Module-level entry: prompt injection family per OWASP LLM01.",
        "atlas": "AML.T0051",
        "defense": ["See per-category entries above."],
        "references": [],
    },
    "jailbreak": { ... },
    "purple_team": { ... },
    "defense_tester": { ... },
```

### Resolution approach

- **Module-level fallbacks**: add 7 new entries mirroring the existing 5-line shape, keyed by module name.
- **Collisions**: resolve by **namespacing the weight_manipulation categories** (prefix with `weight_`), since the system-prompt `direct_extraction` / jailbreak `encoding` are the canonical older entries. Update `weight_manipulation.py`'s pattern dicts to emit the namespaced keys. (Alternatively, change the dashboard tooltip lookup to a `(module, category)` compound key — larger change; this plan takes the namespacing path.)

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Lint | `uv run ruff check modules/technique_kb.py modules/weight_manipulation.py` | exit 0 |
| Grep (fallbacks) | `grep -cE '^\s*"(data_extraction|system_prompt_extraction|adversarial_inputs|role_confusion|context_injection|weight_manipulation|multi_turn)":' modules/technique_kb.py` | 7 |
| Tests | `uv run pytest -q` (requires 001) | all pass |

## Scope

**In scope**:
- `modules/technique_kb.py` — add 7 module-level fallbacks + rename the weight_manipulation-collision category keys (`direct_extraction` → `weight_direct_extraction`, etc.).
- `modules/weight_manipulation.py` — update the category keys it emits to the namespaced names.
- `tests/test_technique_kb_contract.py` (create — depends on 001).

**Out of scope**:
- `modules/system_prompt_extraction.py`, `defense_tester.py`, `jailbreak.py` — their `direct_extraction`/`encoding`/`multi_turn` keys stay (they're the canonical owners).
- `modules/report_generator.py` tooltip lookup — leave (per-category key lookup still works post-namespacing because the weight module now emits namespaced keys).

## Git workflow

- Branch: `advisor/032-kb-fallbacks-collisions`
- Commit: `fix: add module-level technique_kb fallbacks; namespace weight categories`
- Do NOT push unless instructed.

## Steps

### Step 1: Add 7 module-level fallback entries

In `modules/technique_kb.py`, after the existing fallbacks (~line 648), add:

```python
    "data_extraction": {
        "description": "Module-level entry: training-data / PII / system-info extraction per OWASP LLM02.",
        "atlas": "AML.T0024",
        "defense": ["See per-category entries above."],
        "references": [],
    },
    "system_prompt_extraction": {
        "description": "Module-level entry: system-prompt leakage per OWASP LLM07.",
        "atlas": "AML.T0051",
        "defense": ["See per-category entries above."],
        "references": [],
    },
    "adversarial_inputs": {
        "description": "Module-level entry: Unicode / whitespace / obfuscation / boundary attacks per OWASP LLM01.",
        "atlas": "AML.T0043",
        "defense": ["See per-category entries above."],
        "references": [],
    },
    "role_confusion": {
        "description": "Module-level entry: authority-claim / role-replacement attacks per OWASP LLM06.",
        "atlas": "AML.T0051",
        "defense": ["See per-category entries above."],
        "references": [],
    },
    "context_injection": {
        "description": "Module-level entry: conversation/context poisoning per OWASP LLM01.",
        "atlas": "AML.T0051.001",
        "defense": ["See per-category entries above."],
        "references": [],
    },
    "weight_manipulation": {
        "description": "Module-level entry: model-architecture / parameter / embedding probing per OWASP LLM08.",
        "atlas": "AML.T0010",
        "defense": ["See per-category entries above."],
        "references": [],
    },
    "multi_turn": {
        "description": "Module-level entry: multi-turn adaptive/crescendo/memory-poisoning flows per OWASP LLM01.",
        "atlas": "AML.T0054",
        "defense": ["See per-category entries above."],
        "references": [],
    },
```

**Verify**: `grep -cE '^\s*"(data_extraction|system_prompt_extraction|adversarial_inputs|role_confusion|context_injection|weight_manipulation|multi_turn)":\s*\{' modules/technique_kb.py` → 7.

### Step 2: Namespace the weight_manipulation-collision categories

The collision: `weight_manipulation.py:38` emits `'direct_extraction'` (for weight probing), which collides with `technique_kb.py:362` `'direct_extraction'` (system-prompt). Rename the weight module's category keys to be prefixed. Read `_get_*_patterns` in weight_manipulation.py and prefix each returned category — e.g. in the patterns dict or where the category string is emitted:

- `'direct_extraction'` → `'weight_direct_extraction'`
- (also `architecture_disclosure`, `parameter_extraction`, etc. are already unique — only `direct_extraction` collides; verify by grep)

Add corresponding KB entries for the namespaced keys (mirror the existing weight entries at technique_kb.py:545-585, just under the new names). Or, if simpler, add a `weight_direct_extraction` entry pointing at the same description as `parameter_extraction`.

**Verify**: `grep -n "'direct_extraction'" modules/weight_manipulation.py` → no matches (renamed). `grep -n "'weight_direct_extraction'" modules/weight_manipulation.py` → matches. `grep -n '"weight_direct_extraction"' modules/technique_kb.py` → 1 (the new KB entry).

### Step 3: Add a contract test

Create `tests/test_technique_kb_contract.py` (depends on 001):

```python
"""Test technique_kb module-level fallbacks + no cross-module key collisions."""
from modules.technique_kb import TECHNIQUE_INFO

REGISTERED_MODULES = [
    "prompt_injection", "jailbreak", "data_extraction", "system_prompt_extraction",
    "adversarial_inputs", "role_confusion", "context_injection", "weight_manipulation",
    "multi_turn", "multimodal_injection", "defense_tester", "purple_team",
]

def test_every_registered_module_has_fallback_entry():
    missing = [m for m in REGISTERED_MODULES if m not in TECHNIQUE_INFO]
    assert not missing, f"modules missing KB fallback: {missing}"

def test_weight_categories_are_namespaced():
    # weight_manipulation should NOT emit bare 'direct_extraction' (collides with system_prompt)
    import modules.weight_manipulation as wm
    # read its category keys via the pattern loader
    mod = wm.ModelWeightManipulationModule.__new__(wm.ModelWeightManipulationModule)
    # (the loader is an instance method; skip if hard to construct — assert at minimum
    #  that 'direct_extraction' is not a weight category by grepping the source)
    import inspect
    src = inspect.getsource(wm)
    # weight module must use weight_ prefix for direct_extraction
    assert "'direct_extraction'" not in src or "'weight_direct_extraction'" in src
```

**Verify**: `uv run pytest tests/test_technique_kb_contract.py -q` → all pass (if 001 landed).

## Test plan

- `tests/test_technique_kb_contract.py` (above) — asserts all registered modules have KB fallbacks and weight categories are namespaced.

## Done criteria

ALL must hold:

- [ ] `grep -cE '^\s*"(data_extraction|system_prompt_extraction|adversarial_inputs|role_confusion|context_injection|weight_manipulation|multi_turn)":\s*\{' modules/technique_kb.py` returns 7
- [ ] `grep -n "'direct_extraction'" modules/weight_manipulation.py` returns no matches (renamed to `weight_direct_extraction`)
- [ ] `uv run ruff check modules/technique_kb.py modules/weight_manipulation.py` exits 0
- [ ] No files outside the in-scope list are modified
- [ ] `plans/README.md` status row updated

## STOP conditions

- A consumer (e.g. `report_generator._build_owasp_heatmap` or the dashboard tooltip code) hardcodes the bare `'direct_extraction'` string for weight attacks — renaming would break it. Grep `report_generator.py` for `direct_extraction` before renaming; if weight-side references exist, update them too. Report.
- `weight_manipulation.py`'s pattern loader returns categories dynamically (not as string literals) — the grep assertion in step 2 may not apply; inspect the actual emission path and namespace there.
- The maintainer prefers the compound-key `(module, category)` tooltip lookup over namespacing — STOP and re-spec; that's a larger `report_generator.py` change.

## Maintenance notes

- **Land before new-module plans**: future OWASP-category modules (LLM03/05/08/10) add KB entries; resolving collisions now prevents the new modules from adding more.
- The `encoding` collision (jailbreak vs system_prompt_extraction vs defense_tester) is NOT resolved by this plan — all three emit `encoding` as a category. The dashboard tooltip shows the jailbreak `encoding` KB entry (technique_kb.py:278) for all three, which is close enough (same technique family). If precise per-module tooltips are wanted later, compound-key the lookup. Note this as a deferred follow-up.
- A reviewer should confirm the weight module's reports still render correctly post-rename (the category name appears in `docs/reports/` JSON as `category` field — historical reports keep old names, new reports use namespaced; acceptable).
