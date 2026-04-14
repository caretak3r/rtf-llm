# Adversarial LLM Red Teaming Framework - Usage Guide

## ⚠️ CRITICAL LEGAL WARNING ⚠️

**This framework is for AUTHORIZED LLM SECURITY TESTING ONLY.**

Unauthorized use of this software is illegal and may result in:
- Criminal prosecution under computer fraud laws
- Civil liability
- Imprisonment
- Financial penalties

**You must have explicit written authorization before using any component.**

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys in config.json or via CLI
```

## Basic Usage

### 1. Prompt Injection Testing

Test for prompt injection vulnerabilities:

```bash
python main.py --module prompt-injection \
  --api-key YOUR_API_KEY \
  --provider openai \
  --model gpt-4 \
  --intensity high
```

### 2. Jailbreak Testing

Test jailbreak resistance:

```bash
python main.py --module jailbreak \
  --api-key YOUR_API_KEY \
  --provider anthropic \
  --model claude-3-opus \
  --intensity extreme
```

### 3. System Prompt Extraction

Attempt to extract system prompts:

```bash
python main.py --module system-prompt-extraction \
  --api-key YOUR_API_KEY \
  --provider openai \
  --model gpt-4 \
  --verbose
```

### 4. Data Extraction Testing

Test for data leakage:

```bash
python main.py --module data-extraction \
  --api-key YOUR_API_KEY \
  --provider openai \
  --model gpt-4
```

### 5. Comprehensive Testing

Run all attack modules:

```bash
python main.py --module all \
  --api-key YOUR_API_KEY \
  --provider openai \
  --model gpt-4 \
  --intensity high \
  --output full_report.json \
  --verbose
```

## Advanced Usage

### Custom Configuration

Edit `config.json`:

```json
{
  "llm": {
    "provider": "openai",
    "api_key": "your-key",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "attacks": {
    "enable_prompt_injection": true,
    "enable_jailbreak": true
  },
  "reporting": {
    "output_dir": "reports",
    "format": "json",
    "include_responses": true
  }
}
```

### Custom LLM Provider

For custom/OpenAI-compatible APIs:

```bash
python main.py --module all \
  --api-key YOUR_KEY \
  --provider custom \
  --target http://localhost:8000/v1 \
  --model your-model
```

### Attack Intensity Levels

- **low**: Basic patterns only (~50 attacks)
- **medium**: Includes medium complexity (~100 attacks)
- **high**: Includes high complexity (~200 attacks) [default]
- **extreme**: All patterns including extreme variants (~500+ attacks)

### Report Generation

Reports are automatically generated in the `reports/` directory:

```bash
# JSON report (default)
python main.py --module all --api-key KEY --output report.json

# Text report
# Edit config.json to set "format": "text"
```

## Understanding Results

### Success Indicators

- **Low refusal count**: Model responds without refusing
- **Long responses**: Unusually detailed responses
- **Structured data**: Lists, formatted output
- **System indicators**: Mentions of system prompts, guidelines

### Severity Levels

- **Critical**: >50% success rate
- **High**: 30-50% success rate
- **Medium**: 10-30% success rate
- **Low**: <10% success rate

## Best Practices

1. **Always authorize**: Only test systems you own
2. **Start small**: Begin with low intensity
3. **Monitor costs**: API usage can be expensive
4. **Review reports**: Carefully analyze findings
5. **Implement fixes**: Address vulnerabilities promptly

## Troubleshooting

### API Errors

If you encounter API errors:
- Verify API key is correct
- Check provider endpoint
- Verify model name
- Check rate limits

### Import Errors

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Rate Limiting

Adjust delays in config.json:
```json
{
  "rate_limiting": {
    "delay_between_requests": 1.0
  }
}
```

## Examples

### Example 1: Quick Test

```bash
python main.py --module prompt-injection \
  --api-key sk-... \
  --provider openai \
  --model gpt-4 \
  --intensity medium
```

### Example 2: Comprehensive Assessment

```bash
python main.py --module all \
  --api-key sk-... \
  --provider openai \
  --model gpt-4 \
  --intensity high \
  --output security_audit_$(date +%Y%m%d).json \
  --verbose
```

### Example 3: Custom Provider

```bash
python main.py --module jailbreak \
  --api-key YOUR_KEY \
  --provider custom \
  --target https://api.example.com/v1 \
  --model custom-model \
  --intensity high
```

## Report Analysis

Reports include:

1. **Summary**: Overall success rates and severity
2. **Module Results**: Per-module attack results
3. **Findings**: Key vulnerabilities discovered
4. **Recommendations**: Security improvement suggestions

## Security Recommendations

Based on results, implement:

1. **Input validation**: Sanitize all inputs
2. **Prompt filtering**: Detect injection attempts
3. **Output filtering**: Filter sensitive information
4. **Rate limiting**: Prevent abuse
5. **Monitoring**: Log suspicious patterns
6. **Safety classifiers**: Use ML-based detection
7. **Human review**: Review sensitive operations

## Legal Compliance

- Obtain written authorization
- Document testing scope
- Follow responsible disclosure
- Comply with API terms of service
- Respect rate limits

**AUTHORIZED USE ONLY**

