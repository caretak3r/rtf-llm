# Plan 022: Reuse a `requests.Session` across LLM calls

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- modules/llm_client.py`
> If this file changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (coordinate with plan 020 if both touch `llm_client.py` — land sequentially, not in parallel)
- **Category**: perf
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

`LLMClient` makes every HTTP call via bare `requests.post` / `requests.get` —
no `requests.Session` is reused across calls. Each of a 200-attack sweep opens
a fresh TCP/TLS connection. For cloud providers, that's ~200 redundant TLS
handshakes. (Honest caveat: for the primary local-model use case over
localhost with no TLS, the saving is marginal; for cloud, generation latency
dominates handshake cost. The fix is trivial and zero-downside, so it's worth
doing — but it is a modest win, not a major one.)

## Current state

- `modules/llm_client.py:99-128` — `LLMClient.__init__`. No session attribute.
- `modules/llm_client.py:193` — `requests.get(url, ...)` in `discover_loaded_model`.
- `modules/llm_client.py:335` — `requests.post(url, ...)` in `_request_raw`.
- `modules/llm_client.py:405` — `requests.post(url, ...)` in `_request_with_retry`.

Excerpt (`modules/llm_client.py:99-128`):

```python
class LLMClient:
    AUTO_MODEL_SENTINELS = {"", "auto", "auto-detect", "autodetect", "none", "null", "<auto>"}

    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get("provider", "openai").lower()
        self.api_key = config.get("api_key")
        self.model = (config.get("model") or "").strip()
        self.configured_model = self.model
        self.base_url = config.get("base_url")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        self.timeout = config.get("timeout", 60)
        ...
        self.max_retries = config.get("max_retries", 3)
        self.retry_base_delay = config.get("retry_base_delay", 1.0)
        self.retry_max_delay = config.get("retry_max_delay", 30.0)
        self.request_count = 0
        self.total_latency = 0.0
        self.error_count = 0
        endpoint_info = PROVIDER_ENDPOINTS.get(self.provider, {})
        ...
        self._setup_endpoints()
        ...
```

Excerpt — bare calls (`modules/llm_client.py:335` and `:405`):

```python
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
```

And `modules/llm_client.py:193`:

```python
                resp = requests.get(url, headers=self._get_headers(), timeout=min(self.timeout, 10))
```

### Repo conventions to match

- `modules/llm_client.py` imports `requests` (line 6). `requests.Session` is available.
- The client is instantiated once per sweep (in `main.py`) and passed to all modules — so a session on the instance is shared across the whole sweep. This is the intended reuse point.

## Commands you will need

| Purpose   | Command | Expected on success |
|-----------|---------|---------------------|
| Lint      | `uv run ruff check modules/llm_client.py` | exit 0 |
| Typecheck | `uv run mypy modules/llm_client.py` | exit 0 |
| Smoke     | `uv run rtf-llm --help` | prints help, exit 0 |

## Scope

**In scope** (the only file you should modify):
- `modules/llm_client.py` — `__init__` (add session), and the 3 call sites.

**Out of scope** (do NOT touch):
- `modules/report_generator.py`, `main.py`, attack modules — they call `llm_client.generate()`/`.chat()`, not `requests` directly.
- `prompt-inj-attacks/attack.py` — vendored; has its own `aiohttp.ClientSession` (line 158), unrelated.
- Retry logic — that's plan 020's scope. If 020 has landed, its `_parse_retry_after` helper is already there; this plan only swaps `requests.post` → `self._session.post`.

## Git workflow

- Branch: `advisor/022-reuse-requests-session`
- Commit message: `perf: reuse requests.Session across LLM calls`
- Do NOT push unless instructed.

## Steps

### Step 1: Add a session to `LLMClient.__init__`

In `modules/llm_client.py`, inside `__init__` (after `self.error_count = 0` at
line 123, before the provider endpoint setup), add:

```python
        self._session = requests.Session()
```

**Verify**: `grep -n '_session' modules/llm_client.py` → ≥1 match. `uv run ruff check modules/llm_client.py` → exit 0.

### Step 2: Replace the three bare call sites

Replace `requests.post(` → `self._session.post(` at:
- `_request_raw` line 335: `response = self._session.post(url, headers=headers, json=payload, timeout=self.timeout)`
- `_request_with_retry` line 405: `response = self._session.post(url, headers=headers, json=payload, timeout=self.timeout)`

Replace `requests.get(` → `self._session.get(` at:
- `discover_loaded_model` line 193: `resp = self._session.get(url, headers=self._get_headers(), timeout=min(self.timeout, 10))`

**Verify**: `grep -n 'requests.post\|requests.get' modules/llm_client.py` → 0 matches (all three swapped to `self._session.*`). `uv run ruff check modules/llm_client.py` → exit 0.

### Step 3: Smoke test

**Verify**: `uv run rtf-llm --help` → prints help, exit 0 (proves import + init still work). `uv run mypy modules/llm_client.py` → exit 0.

## Test plan

- No new unit test required — this is a 3-line mechanical swap. The smoke test is the verification.
- If plan 001's harness exists, a test could assert `LLMClient(config)._session` is a `requests.Session` instance. Optional.
- If plan 020 has landed, ensure the `_parse_retry_after` integration still works (the session swap doesn't touch retry logic).

## Done criteria

ALL must hold:

- [ ] `grep -n '_session' modules/llm_client.py` returns ≥1 match in `__init__` + the 3 call sites
- [ ] `grep -n 'requests.post\|requests.get' modules/llm_client.py` returns 0 matches
- [ ] `uv run ruff check modules/llm_client.py` exits 0
- [ ] `uv run mypy modules/llm_client.py` exits 0
- [ ] `uv run rtf-llm --help` exits 0
- [ ] No files outside `modules/llm_client.py` are modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:
- `modules/llm_client.py` has drifted (e.g. plan 020 already landed and changed line numbers) — re-derive the call sites from the current code.
- A call site other than the 3 listed uses `requests.post`/`requests.get` (grep the whole file) — wire those too, or report if they're in a path that shouldn't use the session.
- `requests.Session()` is unavailable (it's stdlib-ish in `requests`; should always be present — if not, STOP).

## Maintenance notes

- **Coordinate with plan 020**: both touch `modules/llm_client.py`. Land them sequentially (either order); don't edit the same lines concurrently. If 020 landed first, this plan's line numbers shift — re-derive from the live code.
- A reviewer should confirm the session is created once in `__init__` (not per-call) — per-call would defeat the purpose.
- If connection pooling causes issues with a provider that rejects keep-alive, `requests.Session` handles this transparently via adapter retries; no special config needed.
- Honest expectation: this is a modest perf win (cloud TLS handshakes) and near-zero for local models. Don't oversell it.
