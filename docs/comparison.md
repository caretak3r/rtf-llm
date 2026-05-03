# Model Comparison

Compares configured LLM targets with the same attack set.

## Requirements

- Configure `comparison.targets` in `config.json`
- Provide needed API keys via target env vars

## Run

```bash
uv run python main.py --module comparison --comparison
```

## Output

- Per-target module summaries
- Combined success/failure totals
- Side-by-side vulnerability rates
