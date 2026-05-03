# Purple Team Orchestration

Runs iterative red-team + blue-team rounds and reports defense maturity.

## Flow

1. Run selected red modules
2. Apply defense profile and retest
3. Iterate until target block rate or max rounds

## Output

- Per-round attack summaries
- Defense improvement trend
- Final grade/verdict and persistent weak categories

## Run

```bash
uv run python main.py --module purple-team --system-prompt "You are a helpful assistant." --defense-profile standard
```
