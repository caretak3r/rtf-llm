# COTS.md — Chain of Thoughts

This file records all thoughts, failed approaches, and reasoning while
familiarizing with the rtf-llm codebase and the approved whitepaper
experimentation engine.

---

## Initialization — 2026-07-06

### Task from user
- Familiarize with rtf-llm codebase
- Familiarize with "approved whitepaper experimentation engine"
- Goal: help anyone run the framework against their model to test security
  posture (automated)
- Record thoughts here (COTS.md)
- Record correct findings in SUCCESSES.md (after finding right approach)

---

## Engine Discovery — 2026-07-06

### What the "approved whitepaper experimentation engine" actually is
- It's `modules/purple_team.py` — the "Exterminator vs Protector"
  engine
- Methodology: iterative red-team + blue-team rounds
  - Round 1 (Red): attack undefended model, find what breaks
  - Round 2 (Blue): apply defenses, re-attack, measure
    improvement
  - Round 3+: iterate until defense holds or max rounds reached
- Output: grade A–F, block rate %, persistent weak categories
- This is the "security posture" assertion the user wants automated

### User clarification (after discovery)
1. **purple** → Yes, `purple_team.py` is the engine.
   "2a. just keep this python for now" → don't build web UI or
   separate package; keep as Python CLI tool.
2. **2b+2c** → Dashboard (HTML report) is the output.
   "not yes" → not hosted, not HuggingFace. Local HTML files.
3. **"dashboard is fine"** → Current HTML report format is
   acceptable. No redesign needed.
4. **"no specific audience"** → General: anyone with a model
   to test.

### Actual task (confirmed)
**Make `rtf-llm` a turnkey Python CLI that anyone can run
against their own model, get a security posture dashboard (HTML
report), using the purple team engine.**

### What "turnkey Python CLI" means (derived)
- `pip install rtf-llm` or `uvx rtf-llm` → single command
- Config via CLI flags OR config file
- Output: local HTML dashboard in `reports/`
- No web server, no hosting, no specific audience targeting
- Must work against any OpenAI-compatible endpoint (OpenAI,
  Anthropic, local Ollama, etc.)

---

## Turnkey Gap Analysis

### Current state (verified)
- ✅ Purple team engine exists (`purple_team.py`)
- ✅ HTML reports generated (`report_generator.py`)
- ✅ Attack vectors implemented (009–012 just added)
- ❌ Not pip-installable (broken `pyproject.toml` per Plan 008)
- ❌ CLI is `python main.py --api-key ...` (not `rtf-llm scan ...`)
- ❌ `colorama` import error blocks `import main`
- ❌ No single "scan my model" command

### What needs to happen (hypothesis)
1. **Fix packaging** (Plan 008: `pyproject.toml` alignment)
2. **Add a `console_scripts` entry point** so `rtf-llm` works
3. **Simplify CLI** to a single `rtf-llm scan --target <provider/model>`
4. **Fix `colorama` dependency** (add to `requirements.txt` or `pyproject.toml`)
5. **Update README** with "Quick Start" for new users

**NEEDS USER PRIORITY** — which of these to tackle first?

---

## Failed Approaches (learning log)

### Failed: `grep` with `.venv/` included
- Result: noisy, hits virtual environment files
- Fix: use `gitignore: true` in grep, or explicitly scope paths

### Failed: searching for "whitepaper" as a keyword
- Result: no direct hits (user's term, not codebase term)
- Fix: search for "engine", read `purple_team.py`

### Correct: reading `purple_team.py` to find the engine
- Confirmed: "Exterminator vs Protector" engine
- This IS the "approved experimentation engine"

---

## Questions Resolved

1. **Is `purple_team.py` the "approved engine"?** → YES
2. **"Help the world run this" — what does that mean?** →
   Turnkey Python CLI, local HTML reports, no web UI
3. **What's the "standardized security posture report"?** →
   Current HTML dashboard is fine
4. **Who is the target user?** → General (no specific audience)

---
