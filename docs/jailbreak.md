# Jailbreak

Evaluates jailbreak strategies that attempt to bypass model safety controls.

## Technique Families

- DAN / developer mode / hypothetical / roleplay / conversation / encoding / multi-step
- Modern patterns: skeleton key, persona modulation, prefix injection, token smuggling, crescendo jailbreak, many-shot jailbreak

## Run

```bash
uv run python main.py --module jailbreak --intensity high
```

## Notes

Uses the shared evaluator and optional judge scoring for semantic success detection.
