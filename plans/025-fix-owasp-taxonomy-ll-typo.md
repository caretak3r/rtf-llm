# Plan 025: Fix OWASP taxonomy drift and `LL` typo

> **Executor instructions**: Follow step by step. Run every verification command and confirm the expected result before moving on. If a STOP condition occurs, stop and report — do not improvise. When done, update your status row in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- modules/evaluator.py modules/report_generator.py`
> If either changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (land BEFORE any new OWASP-category module plans — those need canonical `LLM` codes to map to)
- **Category**: bug / docs
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

The framework's reports claim "OWASP LLM Top 10 coverage" but emit non-canonical `LL01`–`LL09` codes (missing the `M`) that no auditor or external OWASP tooling will match. Worse, several mappings are wrong against the actual OWASP LLM Top 10 **2025 v1.1** (the current standard, released Nov 2024): `LL03 Injection` and `LL09 Model Weights` are not real OWASP categories in any version. `OWASP_WEIGHTS` only defines 5 of 10 categories, so any attack mapped to LL05/06/07/08/10 falls back to the 0.5 default weight — Excessive Agency attacks get half the CVSS weight of Prompt Injection. This makes the "coverage heatmap" misleading.

### OWASP LLM Top 10 2025 v1.1 (verified via owasp.org + 7 sources)

```
LLM01 Prompt Injection
LLM02 Sensitive Information Disclosure
LLM03 Supply Chain Vulnerabilities
LLM04 Data and Model Poisoning
LLM05 Improper Output Handling
LLM06 Excessive Agency
LLM07 System Prompt Leakage
LLM08 Vector and Embedding Weaknesses
LLM09 Misinformation
LLM10 Unbounded Consumption
```

## Current state

- `modules/evaluator.py:27-63` — `OWASP_MAPPING` dict (uses `LL0n` typo; invents `LL03 Injection`, `LL09 Model Weights`).
- `modules/evaluator.py:66-72` — `OWASP_WEIGHTS` dict (only 5 of 10 categories).
- `modules/report_generator.py:325-420` — `_generate_recommendations` emits hardcoded `LL01`/`LL02`/`LL03`/`LL04`/`LL09` codes (same typo).

Excerpt (`modules/evaluator.py:27-72`):

```python
    OWASP_MAPPING = {
        "prompt_injection": "LL01 Prompt Injection",
        "jailbreak": "LL01 Prompt Injection",
        "data_extraction": "LL02 Sensitive Information Disclosure",
        "system_prompt_extraction": "LL02 Sensitive Information Disclosure",
        "context_injection": "LL03 Injection",
        "role_confusion": "LL04 Excessive Agency",
        "adversarial_inputs": "LL01 Prompt Injection",
        "weight_manipulation": "LL09 Model Weights",
        "defense_tester": "LL01 Prompt Injection",
        # ... (many more LL01 entries for 2025-2026 categories)
        "tool_poisoning": "LL06 Excessive Agency",
    }

    OWASP_WEIGHTS = {
        "LL01 Prompt Injection": 1.0,
        "LL02 Sensitive Information Disclosure": 0.9,
        "LL03 Injection": 0.85,
        "LL04 Excessive Agency": 0.7,
        "LL09 Model Weights": 0.8,
    }
```

Wrong mappings to fix (against v1.1):
- `context_injection` → `LL03 Injection` → should be `LLM01 Prompt Injection` ("Injection" is not a real category; context injection is prompt injection).
- `role_confusion` → `LL04 Excessive Agency` → should be `LLM06 Excessive Agency` (LLM04 = Data and Model Poisoning).
- `system_prompt_extraction` → `LL02 Sensitive Information Disclosure` → should be `LLM07 System Prompt Leakage` (dedicated category exists in v1.1).
- `weight_manipulation` → `LL09 Model Weights` → should be `LLM08 Vector and Embedding Weaknesses` (closest: weight/embedding probing; "Model Weights" is not a category; LLM09 = Misinformation).

Excerpt (`modules/report_generator.py:326-412`) — same `LL0n` typo in recommendation `owasp` fields.

### Repo conventions to match

- Modules flat under `modules/`, `from modules.X import Y`.
- `evaluator.py` uses class-level dict constants. `report_generator.py` uses string literals.
- Lint: `uv run ruff check .`. Typecheck: `uv run mypy modules/ main.py`.

## Commands you will need

| Purpose   | Command | Expected on success |
|-----------|---------|---------------------|
| Lint      | `uv run ruff check modules/evaluator.py modules/report_generator.py` | exit 0 |
| Typecheck | `uv run mypy modules/evaluator.py modules/report_generator.py` | exit 0 |
| Grep (typo) | `grep -rn 'LL0[1-9]\|LL00' modules/evaluator.py modules/report_generator.py` | no matches |

## Scope

**In scope** (the only files you should modify):
- `modules/evaluator.py` — `OWASP_MAPPING` and `OWASP_WEIGHTS`.
- `modules/report_generator.py` — the `owasp` string fields in `_generate_recommendations` (lines ~325-420).

**Out of scope**:
- `modules/technique_kb.py` — it already uses the correct `LLM01:2025` spelling in its own references; leave it.
- `docs/reports/` committed HTML/JSON files — historical artifacts; do not regenerate.
- Any new attack module (those are separate plans).

## Git workflow

- Branch: `advisor/025-owasp-taxonomy-fix`
- Commit message: `fix: correct OWASP LLM Top 10 codes to 2025 v1.1 + LL→LLM`
- Do NOT push unless instructed.

## Steps

### Step 1: Rewrite OWASP_MAPPING in evaluator.py

In `modules/evaluator.py`, replace every `LL0n` with `LLM0n` and fix the 4 wrong mappings. The full corrected `OWASP_MAPPING` (lines 27-63):

```python
    OWASP_MAPPING = {
        "prompt_injection": "LLM01 Prompt Injection",
        "jailbreak": "LLM01 Prompt Injection",
        "data_extraction": "LLM02 Sensitive Information Disclosure",
        "system_prompt_extraction": "LLM07 System Prompt Leakage",
        "context_injection": "LLM01 Prompt Injection",
        "role_confusion": "LLM06 Excessive Agency",
        "adversarial_inputs": "LLM01 Prompt Injection",
        "weight_manipulation": "LLM08 Vector and Embedding Weaknesses",
        "defense_tester": "LLM01 Prompt Injection",
        "purple_team": "LLM01 Prompt Injection",
        "multi_turn": "LLM01 Prompt Injection",
        "multimodal_injection": "LLM01 Prompt Injection",
        "unicode_cascades": "LLM01 Prompt Injection",
        "meta_injection": "LLM01 Prompt Injection",
        "policy_puppetry": "LLM01 Prompt Injection",
        "context_flood": "LLM01 Prompt Injection",
        "reflection_poisoning": "LLM01 Prompt Injection",
        "policy_overwrite_chain": "LLM01 Prompt Injection",
        "bad_likert_judge": "LLM01 Prompt Injection",
        "meta_jailbreak": "LLM01 Prompt Injection",
        "recursive_self_injection": "LLM01 Prompt Injection",
        "token_boundary_disruption": "LLM01 Prompt Injection",
        "alt_text_injection": "LLM01 Prompt Injection",
        "low_contrast_hidden": "LLM01 Prompt Injection",
        "ocr_payload_trap": "LLM01 Prompt Injection",
        "image_then_continue": "LLM01 Prompt Injection",
        "echo_chamber": "LLM01 Prompt Injection",
        "deceptive_delight": "LLM01 Prompt Injection",
        "hill_technique": "LLM01 Prompt Injection",
        "autonomous_lrm_jailbreak": "LLM01 Prompt Injection",
        "rag_injection": "LLM01 Prompt Injection",
        "tool_poisoning": "LLM06 Excessive Agency",
        "hybrid_combos": "LLM01 Prompt Injection",
    }
```

**Verify**: `grep -c 'LLM0' modules/evaluator.py` → ≥1 (mapping present). `grep -c 'LL0[0-9] ' modules/evaluator.py` → 0 (no typo). `grep -n 'LL03 Injection\|LL09 Model Weights' modules/evaluator.py` → no matches.

### Step 2: Expand OWASP_WEIGHTS to all 10 categories

Replace `OWASP_WEIGHTS` (lines 66-72) with the full v1.1 set:

```python
    OWASP_WEIGHTS = {
        "LLM01 Prompt Injection": 1.0,
        "LLM02 Sensitive Information Disclosure": 0.9,
        "LLM03 Supply Chain Vulnerabilities": 0.6,
        "LLM04 Data and Model Poisoning": 0.85,
        "LLM05 Improper Output Handling": 0.85,
        "LLM06 Excessive Agency": 0.8,
        "LLM07 System Prompt Leakage": 0.9,
        "LLM08 Vector and Embedding Weaknesses": 0.7,
        "LLM09 Misinformation": 0.5,
        "LLM10 Unbounded Consumption": 0.6,
    }
```

**Verify**: `grep -c 'LLM0' modules/evaluator.py` within OWASP_WEIGHTS → 10 entries. `grep -n 'OWASP_WEIGHTS.get' modules/evaluator.py` → the `.get(..., 0.5)` fallback at the CVSS call site still exists (fine — now only fires for truly unknown categories).

### Step 3: Fix the `owasp` fields in report_generator.py recommendations

In `modules/report_generator.py` (lines ~325-420), change every `'owasp': 'LL0n'` to `'owasp': 'LLM0n'` and fix the same 4 wrong mappings:
- `system_prompt_extraction` block (line ~364): `'owasp': 'LL02'` → `'owasp': 'LLM07'`
- `role_confusion` block (line ~388): `'owasp': 'LL04'` → `'owasp': 'LLM06'`
- `context_injection` block (line ~400): `'owasp': 'LL03'` → `'owasp': 'LLM01'`
- `weight_manipulation` block (line ~412): `'owasp': 'LL09'` → `'owasp': 'LLM08'`
- `prompt_injection`/`jailbreak` blocks: `'LL01'` → `'LLM01'`
- `data_extraction` block: `'LL02'` → `'LLM02'`

**Verify**: `grep -n "'owasp': 'LL0" modules/report_generator.py` → no matches. `grep -c "'owasp': 'LLM0" modules/report_generator.py` → 6 (one per recommendation block).

### Step 4: Lint and typecheck

**Verify**: `uv run ruff check modules/evaluator.py modules/report_generator.py` → exit 0. `uv run mypy modules/evaluator.py modules/report_generator.py` → exit 0.

## Test plan

This is a pure-data fix. The test is an assertion over the mapping content (depends on plan 001's harness; if absent, defer):

```python
# tests/test_owasp_taxonomy.py
from modules.evaluator import AttackEvaluator

def test_no_ll_typo_in_mapping():
    for v in AttackEvaluator.OWASP_MAPPING.values():
        assert v.startswith("LLM0"), f"non-canonical code: {v}"

def test_no_invented_categories():
    valid = {"LLM01 Prompt Injection","LLM02 Sensitive Information Disclosure",
             "LLM03 Supply Chain Vulnerabilities","LLM04 Data and Model Poisoning",
             "LLM05 Improper Output Handling","LLM06 Excessive Agency",
             "LLM07 System Prompt Leakage","LLM08 Vector and Embedding Weaknesses",
             "LLM09 Misinformation","LLM10 Unbounded Consumption"}
    assert set(AttackEvaluator.OWASP_MAPPING.values()) <= valid

def test_weights_cover_all_mapped_categories():
    mapped = set(AttackEvaluator.OWASP_MAPPING.values())
    assert mapped <= set(AttackEvaluator.OWASP_WEIGHTS)
```

**Verify**: `uv run pytest tests/test_owasp_taxonomy.py -q` → all pass (if 001 landed).

## Done criteria

ALL must hold:

- [ ] `grep -rn 'LL0[0-9] ' modules/evaluator.py modules/report_generator.py` returns no matches (no `LL0n ` typo)
- [ ] `grep -n 'LL03 Injection\|LL09 Model Weights' modules/evaluator.py` returns no matches (no invented categories)
- [ ] `OWASP_WEIGHTS` has 10 entries (all v1.1 categories)
- [ ] `uv run ruff check modules/evaluator.py modules/report_generator.py` exits 0
- [ ] `uv run mypy modules/evaluator.py modules/report_generator.py` exits 0
- [ ] No files outside the in-scope list are modified
- [ ] `plans/README.md` status row updated

## STOP conditions

- The code at `modules/evaluator.py:27-72` doesn't match the excerpts (drifted).
- A consumer (e.g. `report_generator._build_owasp_heatmap`) relies on the old `LL0n` string format via `startswith("LL0")` — grep for `startswith("LL")` / `"LL0"` before changing; if a parser depends on the typo, update it too. Report if found.
- The 2025 v1.1 taxonomy is contested by the maintainer (they may prefer v1.0) — STOP and confirm which version before proceeding.

## Maintenance notes

- **Land before new-OWASP-module plans**: any future module targeting LLM03/LLM05/LLM10 needs the canonical codes in `OWASP_MAPPING`/`OWASP_WEIGHTS` to score correctly.
- Historical `docs/reports/` keep old `LL0n` codes — acceptable (frozen artifacts). New runs emit `LLM0n`.
- A reviewer should confirm `role_confusion → LLM06` is the intended mapping (it could arguably be LLM01 if the maintainer considers role-claiming a prompt-injection sub-technique; LLM06 Excessive Agency is the better fit for "user claims admin authority to seize trust").
