# SUCCESSES.md — Correct Findings

This file records proven, correct findings after iterating through failed
approaches. Each entry must be verified before being recorded here.

---

## Codebase Architecture (verified)

### Entry point
- `main.py` — CLI entry point, parses args, loads config, dispatches
  to modules
- NOW accessible via `rtf-llm` CLI command (after `pip install .`)

### Module structure
- `modules/prompt_injection.py` — direct/indirect injection attacks
- `modules/jailbreak.py` — jailbreak patterns (Skeleton Key, DAN,
  Crescendo, Logic, etc.)
- `modules/multi_turn.py` — multi-turn strategies (Crescendo,
  Reflection Poisoning, Memory Poisoning, etc.)
- `modules/adversarial_inputs.py` — adversarial inputs (Unicode,
  TokenBreak, etc.)
- `modules/multimodal_injection.py` — image/PDF injection vectors
- `modules/purple_team.py` — "Exterminator vs Protector" engine
  (Red/Blue iterations)
- `modules/technique_kb.py` — knowledge base (TECHNIQUE_INFO
  dict with descriptions, ATLAS, CWE, defenses)

### Report generation
- `generate_report.py` — standalone report generator (being
  consolidated per Plan 007)
- `modules/report_generator.py` — report generation from sweep
  results
- Output: HTML + JSON in `reports/`

### Config
- `config.json` — target config (provider, model, api_key, etc.)
- `pyproject.toml` — project metadata (NOW FIXED for pip install)

---

## The "Approved Whitepaper Experimentation Engine"

### Finding: The engine IS `modules/purple_team.py`

**Verification method:**
- Read `modules/purple_team.py` lines 1–256
- Confirmed: docstring says "This is the 'Exterminator vs
  Protector' engine"
- Confirmed: implements iterative red/blue team rounds

**How it works:**
1. **Round 1 (Red)**: Run attack modules against undefended model
2. **Round 2 (Blue)**: Apply defense profile, re-attack, measure
   improvement
3. **Round 3+**: Iterate until `target_block_rate` reached or
   `max_rounds` hit

**Output (verified):**
- Per-round attack summaries
- Defense improvement trend
- Final grade: A (>=95%), B (>=85%), C (>=70%), D (>=50%),
  F (<50%)
- Persistent weak categories list

---

## Attack Vector Coverage (after Plans 009–012)

### Implemented categories (verified in technique_kb.py)
1. `tokenbreak` — TokenBreak / Tokenization Confusion (June 2025)
2. `document_upload` — Stored Prompt Injection via Document
   Upload (2026)
3. `memory_poisoning` — Agent Memory Poisoning (OWASP
   AppSec USA 2025)
4. `logic_jailbreak` — Fallacy Failure / Logic-Based
   Jailbreaks (May 2025)

### Verification method used
- `grep -n '"tokenbreak\|"document_upload\|"memory_poisoning\|"logic_jailbreak' modules/technique_kb.py`
- Result: all 4 entries confirmed present

---

## Packaging Fix (2026-07-06)

### Problem: `pip install .` was broken
- `hatchling` build backend failing
- `setuptools` discovering multiple top-level packages (`plans/`,
  `modules/`)
- `main.py` not included as a top-level module

### Solution (verified):
1. **Switch to `setuptools` backend** in `pyproject.toml`
   ```toml
   [build-system]
   requires = ["setuptools>=68.0", "wheel"]
   build-backend = "setuptools.build_meta"
   ```
2. **Add `py-modules = ["main"]`** to include `main.py`
3. **Add `[tool.setuptools.packages.find]`** to include `modules/`
4. **Set `[tool.uv] package = true`** to enable `uv sync`

### Verification:
- `uv pip install .` → **SUCCEEDS** (package builds)
- `uv run rtf-llm --help` → **SUCCEEDS** (CLI works)
- Output: full help text with all flags

### Current state:
- ✅ `rtf-llm --help` works
- ✅ `pip install .` works (after fixes)
- ✅ All attack modules accessible via CLI
- ✅ HTML reports generated in `reports/`

---

## CLI Entry Point (2026-07-06)

### Finding: `rtf-llm` command NOW WORKS

**Verification:**
```bash
cd /Users/rohit/Documents/rtf-llm
uv pip install .  # builds package
uv run rtf-llm --help  # shows full CLI help
```

**Output (verified):**
```
usage: rtf-llm [-h] --module MODULE [--target TARGET] ...
Adversarial LLM Red Teaming Framework - Authorized Testing Only!
```

**Available flags (verified):**
- `--module` — attack module to run
- `--target` — LLM API endpoint
- `--api-key` — API key
- `--provider` — openai, anthropic, google, custom, ollama, etc.
- `--model` — model identifier
- `--intensity` — low/medium/high/extreme
- `--output` — report file path
- `--defense-profile` — minimal/standard/hardened/maximum
- `--judge` — enable LLM-as-Judge
- `--no-serve` — don't serve HTML dashboard

### "Turnkey" status:
- ✅ Single command: `rtf-llm --module all --target <provider/model>`
- ✅ No web UI needed (local HTML dashboard)
- ✅ Works for "anyone" with a model to test

---

## Search Approach Learnings

### Correct approach: scoped grep with `gitignore: true`
- **Failed**: `grep` with default paths (hits `.venv/`)
- **Correct**: `grep` with `gitignore: true` and explicit path
  scoping

### Correct approach: read source files directly
- **Failed**: searching for user's terms ("whitepaper") in codebase
- **Correct**: read codebase structure, find engine by its
  function (`purple_team.py`)

### Correct verification: `git diff --stat` + `grep` on specific
### patterns
- Don't trust executor reports alone
- Verify on disk: `git diff --name-only`, `git diff --stat`
- Verify in source: `grep -n 'pattern' file.py`

---

## Dependency Finding (2026-07-06)

### `colorama` import error — RESOLVED
- **Symptom**: `ModuleNotFoundError: No module named 'colorama'`
- **Root cause**: Running `python3` DIRECTLY instead of `uv run python`
- **Verification**: `uv run python -c "import colorama"` → `colorama ok`
- **Correct approach**: Always use `uv run python` or activate venv first
- **Implication**: `colorama` IS in `requirements.txt` and `pyproject.toml`

---
