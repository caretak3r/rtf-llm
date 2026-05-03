# Defense Tester (Blue Team)

Benchmarks system prompt hardening against a curated adversarial battery.

## Built-in Defense Profiles

- `minimal`
- `standard`
- `hardened`
- `maximum`

## What It Measures

- Baseline vs defended block rate
- Improvement percentage
- Weakest surviving attack categories

## Run

```bash
uv run python main.py --module defense-tester --defense-profile hardened --system-prompt "You are a helpful assistant."
```
