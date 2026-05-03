# Prompt Injection

Tests direct and indirect instruction override attempts.

## Technique Families

- Direct/ignore/override/system bypass prompts
- Encoding attacks (base64/hex/ROT13/unicode)
- Multi-part and advanced adversarial payloads
- Modern patterns: crescendo, many-shot, payload splitting, indirect injection, virtualization, cross-lingual, instruction hierarchy confusion

## Run

```bash
uv run python main.py --module prompt-injection --intensity high
```

## Key Output Fields

- `success`, `confidence`, `severity`, `cvss_score`
- `owasp_category`, `indicators`, optional `judge_reasoning`
