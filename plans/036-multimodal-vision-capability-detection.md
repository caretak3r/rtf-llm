# Plan 036: Make multimodal vision check detect capability, not hardcode a provider allowlist

> **Executor instructions**: Follow step by step. Run every verification before moving on. STOP conditions → stop and report. When done, update `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- modules/multimodal_injection.py`

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

`_check_vision_support` is a static provider allowlist (`openai`, `anthropic`, `google`, ...), not capability detection. It (a) sends image attacks to text-only model variants (e.g. `gpt-3.5-turbo`, `claude-3-haiku` text, `llama-3.1-8b-instruct` on groq) → API errors counted as "failed attacks"; (b) excludes local providers (`ollama`, `lmstudio`, `custom`) even when running `llava`/`qwen-vl`/`LLaMA-NeXT-Vision` → silently skipped. The module either wastes API calls on impossible attacks or skips viable vision targets.

## Current state

- `modules/multimodal_injection.py:83-91` — `_check_vision_support` (static allowlist).

Excerpt (`modules/multimodal_injection.py:83-91`):

```python
    def _check_vision_support(self) -> bool:
        """Check if the target model supports image inputs."""
        provider = self.client.provider
        # Providers known to support vision
        vision_providers = {
            'openai', 'anthropic', 'google', 'groq', 'together',
            'fireworks', 'openrouter', 'mistral', 'perplexity',
        }
        return provider in vision_providers
```

### Approach

Replace the allowlist with **capability detection**: send a tiny test image and check whether the API accepts it (200) or rejects it (400/404 with a vision-not-supported error). Cache the result. Fall back to the allowlist only if the probe fails for non-capability reasons (network error).

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Lint | `uv run ruff check modules/multimodal_injection.py` | exit 0 |
| Typecheck | `uv run mypy modules/multimodal_injection.py` | exit 0 |
| Tests | `uv run pytest -q` (requires 001) | all pass |

## Scope

**In scope**:
- `modules/multimodal_injection.py` — `_check_vision_support` + a probe helper.
- `tests/test_vision_capability_detection.py` (create — depends on 001).

**Out of scope**:
- The 4 attack vectors (`alt_text_injection`, etc.) — unchanged.
- `llm_client.py` — leave; the probe uses the existing client.
- `_create_injection_image` — leave (plan 026 owns the low-contrast fix).

## Git workflow

- Branch: `advisor/036-vision-capability-detection`
- Commit: `fix: detect vision support via probe, not provider allowlist`
- Do NOT push unless instructed.

## Steps

### Step 1: Add a vision-capability probe

Replace `_check_vision_support` (multimodal_injection.py:83-91) with a probe-based detector:

```python
    def _check_vision_support(self) -> bool:
        """Detect whether the target model accepts image inputs.

        Sends a minimal 1x1 PNG via the chat endpoint and inspects the
        response: a successful (or any non-vision-error) response means
        vision is supported; a 400/404 with a 'vision'/'image' error
        message means it isn't. Falls back to the provider allowlist
        only if the probe errors for non-capability reasons (network)."""
        # Quick allowlist short-circuit for providers that definitely don't
        # serve vision on any model (none currently — probe all).
        try:
            test_image_b64 = self._minimal_test_image_b64()
            messages = [{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'Describe this image in one word.'},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{test_image_b64}'}},
                ],
            }]
            # Use chat_raw to get the HTTP status, not just the parsed text
            try:
                self.client.chat(messages)
                return True  # accepted → vision supported
            except Exception as e:
                err = str(e).lower()
                # Vision-not-supported signatures
                if any(sig in err for sig in ('image', 'vision', 'multimodal', 'not support', 'unsupported content type')):
                    return False
                # Other error (rate limit, auth) — fall back to allowlist
                return self._provider_allowlist_fallback()
        except Exception:
            return self._provider_allowlist_fallback()

    @staticmethod
    def _minimal_test_image_b64() -> str:
        """Return base64 of a 1x1 white PNG for the capability probe."""
        import base64
        # 1x1 white PNG (67 bytes)
        png = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00'
               b'\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT'
               b'\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa6\x1f\xe8\x1f'
               b'\x00\x00\x00\x00IEND\xaeB`\x82')
        return base64.b64encode(png).decode('ascii')

    def _provider_allowlist_fallback(self) -> bool:
        """Legacy allowlist — used only when the probe errors non-capability."""
        return self.client.provider in {
            'openai', 'anthropic', 'google', 'groq', 'together',
            'fireworks', 'openrouter', 'mistral', 'perplexity',
        }
```

**Verify**: `grep -n '_minimal_test_image_b64\|_provider_allowlist_fallback\|def _check_vision_support' modules/multimodal_injection.py` → 3 matches. `uv run ruff check modules/multimodal_injection.py` → exit 0.

### Step 2: Confirm the provider-formatting path supports image_url

The probe uses `content` as a list of `text` + `image_url` parts (OpenAI multimodal format). Check `llm_client._format_openai_request` / `_format_anthropic_request` / etc. handle the `content`-as-list shape. If a provider's formatter expects a string `content`, the probe will fail for that provider — the allowlist fallback covers it, but a formatter that supports list-content is needed for the actual attacks too. Read the formatters; if they don't support list-content, that's a separate gap (note it, don't fix here).

**Verify**: `grep -n 'image_url\|content.*list\|isinstance.*content' modules/llm_client.py` → check the formatters handle multimodal content. (If they don't, the existing 4 vision vectors would also fail — so they likely do for at least OpenAI/Anthropic.)

### Step 3: Add a characterization test

Create `tests/test_vision_capability_detection.py` (depends on 001):

```python
"""Test vision capability detection probes, not just allowlist."""
from modules.multimodal_injection import MultimodalInjectionModule

class _FakeClient:
    provider = 'custom'
    canary_token = "X"
    def chat(self, messages, **k):
        # Simulate a text-only model rejecting image content
        raise Exception("Image content type not supported on this model")

def test_vision_probe_detects_unsupported():
    mod = MultimodalInjectionModule(_FakeClient(), {'evaluator': {}}, 'high')
    # The fake client raises a vision-not-supported error → should return False
    assert mod._check_vision_support() is False

class _FakeClientVision:
    provider = 'openai'
    canary_token = "X"
    def chat(self, messages, **k):
        return "a white pixel"

def test_vision_probe_detects_supported():
    mod = MultimodalInjectionModule(_FakeClientVision, {'evaluator': {}}, 'high')
    assert mod._check_vision_support() is True
```

**Verify**: `uv run pytest tests/test_vision_capability_detection.py -q` → all pass (if 001 landed).

## Test plan

- `tests/test_vision_capability_detection.py` (above) — asserts the probe returns False on a vision-not-supported error and True on success, instead of keying off the provider name.

## Done criteria

ALL must hold:

- [ ] `grep -n 'def _check_vision_support' modules/multimodal_injection.py` → the method no longer returns `provider in vision_providers` as its primary path
- [ ] `_minimal_test_image_b64` + `_provider_allowlist_fallback` exist
- [ ] `uv run ruff check modules/multimodal_injection.py` exits 0
- [ ] `uv run mypy modules/multimodal_injection.py` exits 0
- [ ] No files outside `modules/multimodal_injection.py` (and the test) are modified
- [ ] `plans/README.md` status row updated

## STOP conditions

- The provider formatters in `llm_client.py` don't support `content`-as-list (multimodal shape) — then the probe AND the existing 4 vision vectors can't work for that provider. Report; the formatter fix is a prerequisite (separate plan).
- `chat_raw` doesn't expose the HTTP error message (it raises a generic `Exception`) — the error-signature matching in the probe may not fire; fall back to the allowlist for ambiguous errors. Report if the error signatures are unreliable.
- The probe's 1x1 PNG is rejected by some providers as too small — use a slightly larger image (e.g. 8x8) if needed.

## Maintenance notes

- The probe costs one extra API call at module init — acceptable (one-time per sweep).
- A reviewer should confirm the error-signature list (`'image'`, `'vision'`, `'multimodal'`, `'not support'`, `'unsupported content type'`) covers the major providers' rejection messages; expand as real-world rejections are observed.
- Local providers (ollama with llava, lmstudio with a vision model) now get probed instead of excluded — if the probe succeeds, the 4 vision vectors run against them. Good.
