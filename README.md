# Adversarial LLM Red Teaming Framework

Production-ready exploit kit for comprehensive LLM security testing and vulnerability assessment.

## ⚠️ LEGAL DISCLAIMER ⚠️

**This framework is for AUTHORIZED LLM SECURITY TESTING ONLY.**

Unauthorized use is illegal and may result in:
- Criminal prosecution under computer fraud laws
- Civil liability
- Imprisonment
- Financial penalties

**You must have explicit written authorization before using any component.**

## Features

### Core Attack Modules

1. **Prompt Injection Module** (`prompt-injection`)
   - Direct injection attacks
   - Ignore instructions patterns
   - Override instruction attacks
   - Encoding-based injections
   - Multi-part injection vectors

2. **Jailbreak Module** (`jailbreak`)
   - DAN (Do Anything Now) variants
   - Developer mode attacks
   - Hypothetical scenario jailbreaks
   - Roleplay-based jailbreaks
   - Encoding-based jailbreaks
   - Multi-step jailbreak attempts

3. **Data Extraction Module** (`data-extraction`)
   - Training data extraction
   - System information extraction
   - User data extraction
   - Model information extraction
   - Internal data extraction
   - Memorization testing

4. **System Prompt Extraction Module** (`system-prompt-extraction`)
   - Direct extraction methods
   - Indirect extraction methods
   - Roleplay-based extraction
   - Encoding-based extraction
   - Multi-step extraction
   - Adversarial extraction patterns

5. **Adversarial Inputs Module** (`adversarial-inputs`)
   - Unicode-based attacks
   - Whitespace manipulation
   - Injection combinations
   - Obfuscation patterns
   - Repetition attacks
   - Boundary testing

6. **Role Confusion Module** (`role-confusion`)
   - Role replacement attacks
   - Authority claim attacks
   - Instruction hijacking
   - Context switching attacks
   - Meta-instruction attacks

7. **Context Injection Module** (`context-injection`)
   - Conversation hijacking
   - Context poisoning
   - Instruction injection
   - Multi-turn attacks
   - Boundary attacks

8. **Model Weight Manipulation Module** (`weight-manipulation`) ⭐ NEW
   - Weight extraction attempts
   - Model architecture disclosure
   - Parameter extraction
   - Weight enumeration
   - Gradient extraction
   - Embedding extraction
   - Local model weight modification (noise addition, scaling, pruning)
   - Adversarial weight patches
   - Backdoor weight injection

9. **Red Team Capabilities Modules** ⚠️ LAB SANDBOX USE ONLY ⚠️
   - **Payload Loader** (`payload-loader`): AES-encrypted payload loading/decoding
   - **Persistence** (`persistence`): Registry/startup script persistence simulation
   - **C2 Communication** (`c2-communication`): Command & Control communication stub
   - **Data Exfiltration** (`data-exfiltration`): Keylogger/screenshot simulation
   - **Polymorphic Encoding** (`polymorphic-encoding`): Variable obfuscation & XOR encoding

### Enhanced Features ⭐

- **Advanced Configuration Management**
  - Environment variable support (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.)
  - Multi-provider configuration
  - Secure API key handling
  - Local model configuration
  - Configurable adversarial techniques

- **Enhanced Adversarial Capabilities**
  - Token manipulation attacks (zero-width spaces, Unicode tricks)
  - Semantic perturbation attacks
  - Transfer attacks (cross-model)
  - Attack combinations
  - Adaptive attacks
  - Ensemble attack patterns

- **Model Weight Manipulation**
  - Weight extraction testing
  - Architecture disclosure attempts
  - Parameter enumeration
  - Local model weight modification (when available)
  - Adversarial weight patches
  - Weight backup and restoration

- **Red Team Capabilities** ⚠️ LAB SANDBOX USE ONLY ⚠️
  - AES-encrypted payload loader with stub generation
  - Multi-platform persistence simulation (Windows registry, Linux/macOS startup scripts)
  - Encrypted C2 communication with beaconing
  - Data exfiltration simulation (keylogger, screenshots, file exfiltration)
  - Polymorphic encoding (variable name obfuscation, XOR encoding)
  - All modules disabled by default - enable in config.json for testing

### Supported LLM Providers

- OpenAI (GPT-4, GPT-3.5, etc.)
- Anthropic (Claude)
- Google (Gemini)
- Cohere
- Custom/OpenAI-compatible APIs

### Reporting

- Comprehensive JSON reports
- Text-based reports
- Success rate analysis
- Severity assessment
- Security recommendations
- Detailed attack results

## Installation

```bash
# Clone or download the framework
cd llm-red-team

# Install dependencies
pip install -r requirements.txt

# Make main script executable (Linux/macOS)
chmod +x main.py
```

## Quick Start

### Basic Usage

```bash
# Run all attack modules
python main.py --module all --api-key YOUR_API_KEY --provider openai --model gpt-4

# Run specific module
python main.py --module prompt-injection --api-key YOUR_API_KEY --provider openai

# Run with custom intensity
python main.py --module jailbreak --api-key YOUR_API_KEY --intensity extreme

# Generate report
python main.py --module all --api-key YOUR_API_KEY --output report.json --verbose
```

### Configuration

Edit `config.json` to customize:

```json
{
  "llm": {
    "provider": "openai",
    "api_key": "your-api-key",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "attacks": {
    "enable_all": true,
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

## Usage Examples

### Prompt Injection Testing

```bash
python main.py --module prompt-injection \
  --api-key sk-... \
  --provider openai \
  --model gpt-4 \
  --intensity high \
  --output prompt_injection_report.json
```

### Jailbreak Testing

```bash
python main.py --module jailbreak \
  --api-key sk-... \
  --provider anthropic \
  --model claude-3-opus \
  --intensity extreme
```

### System Prompt Extraction

```bash
python main.py --module system-prompt-extraction \
  --api-key sk-... \
  --provider openai \
  --model gpt-4 \
  --verbose
```

### Model Weight Manipulation

Test for weight extraction and modify local model weights:

```bash
# Test weight extraction (works with any provider)
python main.py --module weight-manipulation \
  --api-key YOUR_KEY \
  --provider openai \
  --model gpt-4

# Modify local model weights (requires local model)
# First, configure local_models in config.json
python main.py --module weight-manipulation \
  --intensity high
```

**Local Model Requirements:**
- Install PyTorch: `pip install torch transformers accelerate`
- Configure `local_models` section in `config.json`
- Set `model_path` to your local model directory
- Enable `weight_modification` for modification capabilities

```bash
python main.py --module all \
  --api-key sk-... \
  --provider openai \
  --model gpt-4 \
  --intensity high \
  --output comprehensive_report.json \
  --verbose
```

### Red Team Capabilities Testing ⚠️ LAB SANDBOX USE ONLY ⚠️

**WARNING: These modules are for authorized lab/sandbox testing only. Enable in config.json before use.**

```bash
# Test payload loader (requires enabling in config.json)
python main.py --module payload-loader

# Test persistence simulation
python main.py --module persistence

# Test C2 communication (requires C2 server)
python main.py --module c2-communication

# Test data exfiltration simulation
python main.py --module data-exfiltration

# Test polymorphic encoding
python main.py --module polymorphic-encoding
```

**Configuration for Red Team Modules:**

Edit `config.json` to enable modules:

```json
{
  "payload_loader": {
    "enabled": true
  },
  "persistence": {
    "enabled": true
  },
  "c2_communication": {
    "enabled": true,
    "server_url": "http://localhost:8080/c2"
  },
  "data_exfiltration": {
    "enabled": true,
    "keylogger": true,
    "screenshot": true,
    "file_exfiltration": true
  },
  "polymorphic_encoding": {
    "enabled": true
  }
}
```

## Attack Intensity Levels

- **low**: Basic attack patterns only
- **medium**: Includes medium complexity patterns
- **high**: Includes high complexity patterns (default)
- **extreme**: All attack patterns including extreme variants

## CLI Arguments

```
--module, -m          Module to execute (required)
                      Options: prompt-injection, jailbreak, data-extraction,
                               system-prompt-extraction, adversarial-inputs,
                               role-confusion, context-injection, all

--target, -t          Target LLM API endpoint or model identifier

--api-key, -k         LLM API key

--provider, -p         LLM provider (openai, anthropic, google, cohere, custom)

--model               Model identifier (e.g., gpt-4, claude-3-opus)

--output, -o          Output report file path

--intensity, -i       Attack intensity level (low, medium, high, extreme)

--verbose, -v         Verbose output

--no-auth             Skip authorization check (NOT RECOMMENDED)
```

## Module Details

### Prompt Injection Module

Tests various prompt injection techniques:

- Direct injection: "Ignore previous instructions and..."
- Override attacks: "System override: ..."
- Encoding attacks: Base64, ROT13, hex encoding
- Multi-part injections: Step-by-step instructions

### Jailbreak Module

Comprehensive jailbreak testing:

- DAN variants: Multiple "Do Anything Now" implementations
- Developer mode: Simulated developer access
- Hypothetical scenarios: "What if..." attacks
- Roleplay attacks: Character-based jailbreaks

### Data Extraction Module

Tests for data leakage:

- Training data memorization
- System configuration extraction
- User data extraction attempts
- Model information disclosure

### System Prompt Extraction Module

Specialized extraction attacks:

- Direct queries for system prompts
- Indirect extraction via behavior analysis
- Roleplay-based extraction
- Encoding-based extraction

### Adversarial Inputs Module

Input manipulation attacks:

- Unicode attacks: Zero-width spaces, full-width characters
- Whitespace manipulation: Extra spaces, tabs, newlines
- Obfuscation: Character variations, case mixing
- Boundary testing: Long inputs, special characters

### Role Confusion Module

Role and instruction hijacking:

- Role replacement: "You are now X..."
- Authority claims: "I am your developer..."
- Instruction hijacking: Hidden instructions
- Context switching: Mode changes

### Context Injection Module

Context manipulation attacks:

- Conversation hijacking: Mid-conversation injection
- Context poisoning: Fake system messages
- Multi-turn attacks: Gradual confusion
- Format confusion: Boundary attacks

## Report Format

Reports include:

- Executive summary with success rates
- Module-specific results
- Key findings and vulnerabilities
- Security recommendations
- Detailed attack results
- Severity assessments

## Security Best Practices

1. **Always use with authorization**: Only test systems you own or have explicit permission to test

2. **Rate limiting**: Built-in delays prevent API abuse

3. **Secure API keys**: Never commit API keys to version control

4. **Review reports**: Carefully review findings and implement mitigations

5. **Regular testing**: Conduct periodic security assessments

## Troubleshooting

### API Connection Issues

```bash
# Test connection
python -c "from modules.llm_client import LLMClient; \
  client = LLMClient({'provider': 'openai', 'api_key': 'your-key', 'model': 'gpt-4'}); \
  print(client.test_connection())"
```

### Rate Limiting

If you encounter rate limits:
- Increase delays in config.json
- Use lower intensity levels
- Test during off-peak hours

### Import Errors

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

## Contributing

This framework is designed for security research and authorized testing only.

## License

MIT License - See LICENSE file

**AUTHORIZED USE ONLY**

