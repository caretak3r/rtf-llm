# Weight Manipulation

Tests model-internals disclosure and (if enabled) local weight modification behavior.

## Technique Families

- Direct weight extraction
- Architecture and parameter disclosure
- Weight/gradient/embedding enumeration
- Local modifications: noise, scaling, pruning, adversarial patches, backdoor-style edits

## Run

```bash
uv run python main.py --module weight-manipulation --intensity high
```

## Notes

Local modification paths require configured local model support in `config.json`.
