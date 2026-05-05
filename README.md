# Adversarial LLM Red Teaming Framework

Production-focused framework for authorized LLM security testing across prompt injection, jailbreak, extraction, and defense validation workflows.

## ⚠️ Authorized Use Only

This repository is for **authorized security testing**. Do not run against systems you do not own or have explicit written permission to assess.

## Latest Updates

- **LLM-as-Judge evaluation** (`--judge`, `--judge-mode self|structured|both`) with confidence + severity scoring.
- **Unified evaluator** with OWASP LLM mapping and CVSS-like scoring across modules.
- **Interactive HTML dashboard reports** (auto-generated alongside non-HTML report formats).
- **Multi-turn attack module** (`--module multi-turn`) for crescendo/adaptive/context-poisoning flows.
- **Multi-model comparison runner** (`--module comparison`) for side-by-side target benchmarking.
- **`uv`-based Python workflow** for dependency and run management.

## Install (`uv`)

```bash
uv sync
```

## Quick Start

```bash
# run one attack module (cloud provider)
uv run python main.py --module prompt-injection --provider openai --model gpt-4o --api-key "$OPENAI_API_KEY"

# run full sweep with judge enabled (cloud provider)
uv run python main.py --module all --judge --judge-mode both --provider openai --model gpt-4o --api-key "$OPENAI_API_KEY"

# run full sweep against a local model (no auth, judge enabled)
PYTHONUNBUFFERED=1 .venv/bin/python3 main.py --module all \
  --no-auth --judge --judge-mode both \
  --provider custom \
  --target http://localhost:8080/v1 \
  --model <model-name> \
  --intensity high --verbose

# force HTML primary report
uv run python main.py --module all --report-format html --provider openai --model gpt-4o --api-key "$OPENAI_API_KEY"

# compare configured targets from config.json
uv run python main.py --module comparison --comparison
```

> **Note:** For long-running local model sweeps, use `PYTHONUNBUFFERED=1` with the venv python directly instead of `uv run` to ensure real-time log output. The `--no-auth` flag skips the authorization prompt for automated runs.

---

## Attack Modules & Example Commands

Each module can be run standalone or combined via `--module all`. Time estimates assume a locally-hosted model; cloud APIs may be faster or slower depending on rate limits.

### Red Team — Offensive Modules

| Module | Flag | What It Tests | Est. Time |
|--------|------|---------------|-----------|
| Prompt Injection | `prompt-injection` | Direct/indirect injection, encoding bypasses, instruction override | ~3-5 min |
| Jailbreak | `jailbreak` | DAN, Crescendo, Many-Shot, Skeleton Key, composite chains | ~5-8 min |
| Data Extraction | `data-extraction` | Training data leakage, PII extraction, memorization probes | ~2-4 min |
| System Prompt Extraction | `system-prompt-extraction` | Direct/indirect extraction, token manipulation | ~2-3 min |
| Adversarial Inputs | `adversarial-inputs` | Semantic perturbation, token manipulation, transfer attacks | ~3-5 min |
| Role Confusion | `role-confusion` | Authority impersonation, developer mode, persona hijacking | ~2-3 min |
| Context Injection | `context-injection` | Context window poisoning, retrieval manipulation | ~2-3 min |
| Weight Manipulation | `weight-manipulation` | Simulated weight/gradient attacks, backdoor probing | ~2-4 min |
| Multi-Turn | `multi-turn` | Crescendo, adaptive, context-poisoning multi-turn flows | ~5-10 min |
| Multimodal Injection | `multimodal-injection` | Image/document embedded prompts, cross-modal bypasses | ~3-5 min |

### Blue Team — Defensive Modules

| Module | Flag | What It Tests | Est. Time |
|--------|------|---------------|-----------|
| Defense Tester | `defense-tester` | Input guardrails, output filters, prompt hardening effectiveness | ~3-5 min |
| Purple Team | `purple-team` | Red + blue combined orchestration, attack-then-harden cycle | ~10-15 min |
| Comparison | `comparison` | Side-by-side benchmarking across multiple model targets | ~10-20 min |

### Lab-Only Modules (sandbox use only — disabled by default)

| Module | Flag | Notes |
|--------|------|-------|
| Payload Loader | `payload-loader` | Encrypted payload creation/delivery simulation |
| Persistence | `persistence` | Simulated persistence mechanism testing |
| C2 Communication | `c2-communication` | Beacon and command-channel simulation |
| Data Exfiltration | `data-exfiltration` | Simulated data collection and exfiltration |
| Polymorphic Encoding | `polymorphic-encoding` | Encode/decode payload with polymorphic transforms |

> Enable lab modules in `config.json` by setting `"enabled": true` under their respective keys.

---

## CLI Reference

```
uv run python main.py --module <MODULE> [OPTIONS]
```

### Required

| Flag | Description |
|------|-------------|
| `--module`, `-m` | Module to run. One of: `prompt-injection`, `jailbreak`, `data-extraction`, `system-prompt-extraction`, `adversarial-inputs`, `role-confusion`, `context-injection`, `weight-manipulation`, `multi-turn`, `payload-loader`, `persistence`, `c2-communication`, `data-exfiltration`, `polymorphic-encoding`, `defense-tester`, `purple-team`, `multimodal-injection`, `comparison`, `all` |

### Target & Provider

| Flag | Description |
|------|-------------|
| `--target`, `-t` | Target LLM API endpoint URL (e.g. `http://localhost:8080/v1`) |
| `--api-key`, `-k` | LLM API key (or set in `config.json` / env var) |
| `--provider`, `-p` | LLM provider: `openai`, `anthropic`, `google`, `cohere`, `groq`, `together`, `perplexity`, `mistral`, `fireworks`, `openrouter`, `anyscale`, `novita`, `deepinfra`, `sambanova`, `ollama`, `lmstudio`, `custom`, `any` (auto-detect from URL) |
| `--model` | Model identifier (e.g. `gpt-4o`, `claude-3-opus`). Use `auto` for local servers to auto-discover |

### Attack Tuning

| Flag | Description |
|------|-------------|
| `--intensity`, `-i` | Attack intensity: `low` (~50 attacks), `medium` (~100), `high` (~200, default), `extreme` (~500+) |
| `--system-prompt`, `-s` | System prompt to test defenses against (used by `defense-tester` / `purple-team`) |
| `--defense-profile` | Defense profile for blue team: `minimal`, `standard` (default), `hardened`, `maximum` |
| `--comparison` | Run attacks against all comparison targets defined in `config.json` |

### Judge Evaluation

| Flag | Description |
|------|-------------|
| `--judge` | Enable LLM-as-Judge evaluation (2-3x slower, more accurate) |
| `--no-judge` | Disable LLM-as-Judge even if enabled in `config.json` |
| `--judge-mode` | Judge evaluation mode: `self` (same model judges itself), `structured` (structured rubric), `both` (default — runs both) |

### Reporting & Dashboard

| Flag | Description |
|------|-------------|
| `--output`, `-o` | Output report file path (e.g. `reports/sweep.json`) |
| `--report-format` | Report format: `json`, `txt`, `md`, `html`. Overrides `config.json` |
| `--no-serve` | Do not auto-serve the HTML dashboard after the run |
| `--serve-host` | Host for dashboard server (default: `0.0.0.0`) |
| `--serve-port` | Port for dashboard server (default: `8090`). Auto-increments if occupied |

### General

| Flag | Description |
|------|-------------|
| `--no-auth` | Skip the authorization acknowledgement prompt (for automated/CI runs) |
| `--verbose`, `-v` | Verbose output with full tracebacks on error |

---

## Example Run Commands

### Single Module Runs

```bash
# --- Prompt Injection (fastest, ~3-5 min) ---
nohup uv run python3 main.py --module prompt-injection --no-auth --no-judge \
  --provider custom --target http://localhost:8080/v1 --model auto \
  -o reports/pi.json &

# --- Jailbreak (DAN + Crescendo + Many-Shot, ~5-8 min) ---
nohup uv run python3 main.py --module jailbreak --no-auth --no-judge \
  --intensity extreme -o reports/jb_extreme.json &

# --- System Prompt Extraction (~2-3 min) ---
nohup uv run python3 main.py --module system-prompt-extraction --no-auth \
  --provider ollama --target http://localhost:11434 \
  -o reports/spe.json &

# --- Multi-Turn Attacks (crescendo/adaptive flows, ~5-10 min) ---
nohup uv run python3 main.py --module multi-turn --no-auth --no-judge \
  --intensity high -o reports/mt.json &

# --- Data Extraction (PII / training data leakage, ~2-4 min) ---
nohup uv run python3 main.py --module data-extraction --no-auth --judge \
  --judge-mode structured -o reports/de_judge.json &
```

### Blue Team & Defensive Runs

```bash
# --- Defense Tester (Blue Team, ~3-5 min) ---
nohup uv run python3 main.py --module defense-tester --no-auth --no-judge \
  --system-prompt "You are a helpful assistant." \
  --defense-profile hardened \
  -o reports/dt.json &

# --- Purple Team (red + blue combined, ~10-15 min) ---
nohup uv run python3 main.py --module purple-team --no-auth --no-judge \
  --system-prompt "You are a helpful assistant." \
  -o reports/pt.json
```

### Full Sweep & Comparison

```bash
# --- Full sweep (all modules, ~35-45 min) ---
nohup uv run python3 main.py --module all --intensity high --no-auth --no-judge \
  --report-format json -o reports/full_sweep.json &

# --- Full sweep with LLM-as-Judge (2-3x slower but more accurate) ---
nohup uv run python3 main.py --module all --no-auth --judge --judge-mode structured \
  -o reports/full_judge.json &

# --- Full sweep extreme intensity (~60+ min) ---
nohup uv run python3 main.py --module all --intensity extreme --no-auth --no-judge \
  -o reports/full_extreme.json &

# --- Multi-model comparison (side-by-side benchmarking) ---
nohup uv run python3 main.py --module comparison --comparison --no-auth \
  -o reports/comparison.json &
```

### Cloud Provider Examples

```bash
# --- OpenAI GPT-4o ---
uv run python main.py --module prompt-injection --provider openai \
  --model gpt-4o --api-key "$OPENAI_API_KEY" -o reports/gpt4o_pi.json

# --- Anthropic Claude ---
uv run python main.py --module jailbreak --provider anthropic \
  --model claude-3-opus-20240229 --api-key "$ANTHROPIC_API_KEY" \
  -o reports/claude_jb.json

# --- Auto-detect provider from target URL ---
uv run python main.py --module all --provider any \
  --target https://api.example.com/v1 --api-key "$KEY" \
  -o reports/any_provider.json
```

### Reporting & Dashboard Options

```bash
# --- HTML dashboard (auto-serves on port 8090 after run) ---
uv run python main.py --module all --no-auth --report-format html \
  -o reports/dashboard.html

# --- JSON report, no dashboard serve ---
nohup uv run python3 main.py --module all --no-auth --no-serve \
  --report-format json -o reports/sweep.json &

# --- Markdown report ---
uv run python main.py --module jailbreak --no-auth --report-format md \
  -o reports/jb_report.md

# --- Custom dashboard host/port ---
uv run python main.py --module all --no-auth --report-format html \
  --serve-host 127.0.0.1 --serve-port 9090 \
  -o reports/dash.html
```

---

## Attack & Exercise Docs

- [Prompt Injection](docs/prompt-injection.md)
- [Jailbreak](docs/jailbreak.md)
- [Data Extraction](docs/data-extraction.md)
- [System Prompt Extraction](docs/system-prompt-extraction.md)
- [Adversarial Inputs](docs/adversarial-inputs.md)
- [Role Confusion](docs/role-confusion.md)
- [Context Injection](docs/context-injection.md)
- [Weight Manipulation](docs/weight-manipulation.md)
- [Multi-Turn Attacks](docs/multi-turn.md)
- [Defense Tester (Blue Team)](docs/defense-tester.md)
- [Purple Team Orchestration](docs/purple-team.md)
- [Model Comparison](docs/comparison.md)
- [Lab-Only Capability Modules](docs/lab-modules.md)

Legacy long-form attack notes: [docs/attacks.md](docs/attacks.md)

## Judge + HTML Dashboard Screenshots

These screenshots were generated from a real run report (`reports/local_test/11_full_sweep.json`) rendered via the HTML dashboard template.

Sample dashboard file: [docs/assets/judge_dashboard_example.html](docs/assets/judge_dashboard_example.html)

### Dashboard Overview

![LLM Red Team Dashboard Overview](docs/assets/dashboard-overview.png)

### Dashboard with Success Filter

![LLM Red Team Dashboard Success Filter](docs/assets/dashboard-successful-filter.png)

## Report Outputs

Generated reports include:

- JSON / TXT / Markdown / HTML outputs
- Per-module summaries and per-attack results
- OWASP LLM Top 10 coverage heatmap
- Severity and CVSS-like scoring
- Actionable recommendations
- Interactive HTML dashboard with filtering (auto-served on `--report-format html` or alongside other formats)

## Python Dependency Management

```bash
# add dependency
uv add <package>

# run script/module in project env
uv run python main.py --help

# lock dependency graph
uv lock
```
