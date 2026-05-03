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
# run one attack module
uv run python main.py --module prompt-injection --provider openai --model gpt-4o --api-key "$OPENAI_API_KEY"

# run full sweep with judge enabled
uv run python main.py --module all --judge --judge-mode both --provider openai --model gpt-4o --api-key "$OPENAI_API_KEY"

# force HTML primary report
uv run python main.py --module all --report-format html --provider openai --model gpt-4o --api-key "$OPENAI_API_KEY"

# compare configured targets from config.json
uv run python main.py --module comparison --comparison
```

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

## Python Dependency Management

```bash
# add dependency
uv add <package>

# run script/module in project env
uv run python main.py --help

# lock dependency graph
uv lock
```
