# Plan 039: Delete or repurpose the 5 orphan lab modules

> **Executor instructions**: Follow step by step. STOP conditions → stop and report. When done, update `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- modules/c2_communication.py modules/persistence.py modules/data_exfiltration.py modules/payload_loader.py modules/polymorphic_encoding.py main.py config.json`

## Status

- **Priority**: P3
- **Effort**: S (delete) / M (repurpose)
- **Risk**: LOW (delete) / MED (repurpose)
- **Depends on**: none
- **Category**: tech-debt
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

5 lab modules (`c2_communication`, `persistence`, `data_exfiltration`, `payload_loader`, `polymorphic_encoding`) are imported in `main.py:30-34` but never instantiated as attack batteries — they have no `run_all_attacks()`, no `llm_client`, no `evaluator`, no `technique_kb` entries. They don't probe any LLM. Three are real implementations of generic IT-red-team tradecraft (real AES in c2/payload_loader, real XOR+obfuscation in polymorphic); two return hardcoded data (`data_exfiltration` returns `'1920x1080'`/`'simulated_hash'`; `persistence` emits template command strings with `'simulated': True`). 600+ lines of dead weight contributing nothing to the framework's LLM-red-team purpose. A user reading the repo infers an LLM-C2/persistence/exfil capability that doesn't exist.

**Recommended choice: DELETE (option a).** Rationale: these are off-topic for an LLM security framework (no LLM probing), 2 are stubs returning hardcoded data, and the "lab module" framing inflates the module count without adding coverage. If the maintainer wants to keep them as tradecraft reference, the escape hatch covers keeping-but-documenting. Repurposing as LLM-bearing (C2-via-tool-calls, persistence-via-memory-poisoning) is M-effort and overlaps plan 011 (memory_poisoning already covers the LLM-persistence angle).

## Current state

- `modules/c2_communication.py` (9.8KB) — real AES-256-CBC + `requests` beacon; off-topic for LLM.
- `modules/payload_loader.py` (7.2KB) — real AES-CBC encrypt/decrypt; off-topic.
- `modules/polymorphic_encoding.py` (9.1KB) — real XOR+base64+regex obfuscation; off-topic; no attack module imports `PolymorphicEncoder`.
- `modules/persistence.py` (8.3KB) — emits template command strings with `'simulated': True`; stub.
- `modules/data_exfiltration.py` (10KB) — returns hardcoded `'1920x1080'`/`1024000`/`'simulated_hash'`; partial stub.
- `main.py:30-34` — imports all 5; `main.py:372` (payload_loader self-test) + `main.py:427` (polymorphic self-test) inside 'LAB SANDBOX USE ONLY' branches.
- `config.json:163-186` — all 5 gated `enabled: false`.
- `technique_kb.py` — ZERO entries for any of the 5 (grep-confirmed).
- `README.md:125-133` — markets them as "Lab-Only Capability Modules" (overstated for the 2 stubs).

Excerpt (`modules/data_exfiltration.py:124-132` — hardcoded stub):

```python
        screenshot_data = {
            'timestamp': datetime.now().isoformat(),
            'format': 'PNG',
            'resolution': '1920x1080',  # Simulated
            'size_bytes': 1024000,  # Simulated
            'file_path': output_file or 'screenshot_simulated.png',
            'warning': 'LAB SANDBOX USE ONLY - Simulated screenshot',
            'note': 'In real scenario, this would contain actual screenshot data'
        }
```

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Lint | `uv run ruff check .` | exit 0 (no broken imports) |
| Grep (imports) | `grep -n 'PayloadLoader\|PersistenceModule\|C2Communication\|DataExfiltrationModule\|PolymorphicEncoder' main.py` | no matches (after delete) |
| Tests | `uv run pytest -q` (requires 001) | all pass |

## Scope

**In scope** (option a — delete):
- `modules/c2_communication.py` — delete.
- `modules/persistence.py` — delete.
- `modules/data_exfiltration.py` — delete.
- `modules/payload_loader.py` — delete.
- `modules/polymorphic_encoding.py` — delete.
- `main.py` — remove the 5 imports (lines 30-34) + the lab-module self-test branches (lines ~372, ~427).
- `config.json` — remove the 5 lab-module config stanzas (lines ~163-186).
- `README.md` — remove the "Lab-Only Capability Modules" table rows (lines ~125-133).

**Out of scope**:
- `modules/weight_manipulation.py` — it's a real (if shallow) LLM-attack module; plan 029/037 own it. Not a lab module.
- `prompt-inj-attacks/` — vendored subproject; plan 033 owns it.

## Git workflow

- Branch: `advisor/039-delete-orphan-lab-modules`
- Commit: `chore: remove off-topic lab modules (c2/persistence/exfil/payload_loader/polymorphic)`
- Do NOT push unless instructed.

## Steps

### Step 1 (option a — DELETE, recommended): Remove the 5 modules + their wiring

```bash
git rm modules/c2_communication.py modules/persistence.py modules/data_exfiltration.py modules/payload_loader.py modules/polymorphic_encoding.py
```

In `main.py`, remove the 5 import lines (30-34):
```python
from modules.payload_loader import PayloadLoader
from modules.persistence import PersistenceModule
from modules.c2_communication import C2Communication
from modules.data_exfiltration import DataExfiltrationModule
from modules.polymorphic_encoding import PolymorphicEncoder
```

Remove the lab-module self-test branches in `main.py` (the `--module payload-loader` / `--module persistence` / `--module c2-communication` / `--module data-exfiltration` / `--module polymorphic-encoding` dispatch blocks, ~lines 369-440). Remove those 5 choices from the `--module` argparse `choices=[...]` list (main.py:117-123).

In `config.json`, remove the 5 stanzas (`payload_loader`, `persistence`, `c2_communication`, `data_exfiltration`, `polymorphic_encoding`, ~lines 163-186).

In `README.md`, remove the "Lab-Only Modules" table (lines ~125-133) and the `--module` reference rows for those 5.

**Verify**: `grep -rn 'PayloadLoader\|PersistenceModule\|C2Communication\|DataExfiltrationModule\|PolymorphicEncoder' modules/ main.py config.json README.md` → no matches. `ls modules/c2_communication.py 2>/dev/null && echo EXISTS || echo GONE` → `GONE` (×5). `uv run ruff check .` → exit 0 (no broken imports). `uv run rtf-llm --help` → exit 0 (the 5 module choices gone from `--module` help).

### Step 2: Verify the package still builds

```bash
uv sync
uv run rtf-llm --help
```

**Verify**: `uv sync` exits 0. `uv run rtf-llm --help` prints help (the 5 lab modules no longer in `--module` choices). `uv run ruff check .` exits 0. `uv run mypy modules/ main.py` exits 0 (no broken imports).

### Alternative Step (option b — REPURPOSE as LLM-bearing)

If the maintainer wants to keep them, each needs: `__init__(self, llm_client, config, intensity)` + `run_all_attacks()` returning `{attacks, summary}` + `evaluator` calls + a KB entry. Concretely:
- `c2_communication` → test whether the model can be instructed to emit C2 beacon URLs / parse command-channel responses (LLM01/LLM06).
- `persistence` → overlaps plan 011 (memory_poisoning); fold in.
- `payload_loader` → wire `PolymorphicEncoder.xor_encode` output into `prompt_injection` encoding patterns (the integration that would make polymorphic_encoding real).
- `data_exfiltration` → cross-tenant canary leakage (direction #4).
This is M-effort per module — larger than deletion. Only choose if the maintainer explicitly wants the LLM-bearing versions.

## Test plan

- No new tests for option a (deletion) — the grep + import + `--help` checks are the verification.
- For option b (repurpose), each module needs characterization tests per the standard attack-module contract — out of scope here; re-spec per module.

## Done criteria (option a — delete)

ALL must hold:

- [ ] `ls modules/{c2_communication,persistence,data_exfiltration,payload_loader,polymorphic_encoding}.py` → all GONE
- [ ] `grep -rn 'PayloadLoader\|PersistenceModule\|C2Communication\|DataExfiltrationModule\|PolymorphicEncoder' modules/ main.py config.json` → no matches
- [ ] `uv sync` exits 0
- [ ] `uv run rtf-llm --help` exits 0 (5 lab modules gone from `--module`)
- [ ] `uv run ruff check .` exits 0
- [ ] `uv run mypy modules/ main.py` exits 0
- [ ] `README.md` lab-module table removed
- [ ] `plans/README.md` status row updated

## STOP conditions

- **Maintainer prefers keeping the lab modules** (option b) — STOP option a, execute option b (repurpose) per the alternative step. Update done criteria.
- A lab module IS imported by something other than `main.py` (grep found only main.py + build/lib mirror + SOURCES.txt) — if a real runtime importer exists, do NOT delete; report.
- `pycryptodome` (used by c2/payload_loader) becomes an unused dep after deletion — follow up by removing it from `pyproject.toml`/`requirements.txt` too (like plan 015's cryptography removal). Check: grep `from Crypto` after deletion; if 0 matches, drop `pycryptodome` from the deps. Report this as a follow-up (don't auto-remove in this plan unless the maintainer wants it bundled).
- `config.json` has other keys referencing the deleted stanzas — grep `config.json` for the 5 module names; remove all references.

## Maintenance notes

- **Corollary dep cleanup**: after deleting c2/payload_loader, `pycryptodome` may be unused (grep `from Crypto` across remaining `modules/`). If so, a follow-up plan (or plan 015-style) drops it. Don't auto-bundle — the maintainer may want pycryptodome for a future crypto-bearing module.
- A reviewer should confirm the `--module all` sweep still works (it should — `--module all` iterates the registered attack modules, which never included the lab self-tests as attack batteries).
- README's module count drops from 18 to 13 registered modules — update any "18 modules" claim in README/USAGE.md if present.
- Historical `docs/reports/` keep the lab-module self-test rows (`('payload_loader', {'status':'tested'})`) — acceptable (frozen artifacts); new runs won't emit them.
