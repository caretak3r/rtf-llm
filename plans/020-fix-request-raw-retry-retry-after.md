# Plan 020: Fix `_request_raw` retry logic and `Retry-After` parsing

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- modules/llm_client.py`
> If this file changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

`LLMClient._request_raw` (used by `chat_raw` → model-discovery at startup) has
a bare `except Exception` that catches the `raise_for_status()` from 4xx errors
AND the `ValueError` from `response.json()` and **retries all of them** with
backoff. A bad API key (401) at startup is retried `max_retries` times —
wasting seconds. Worse, `float(Retry-After)` at line 338 crashes with
`ValueError` if a server sends an RFC 7231 HTTP-date format (e.g.
`Wed, 21 Oct 2026 07:28:00 GMT`), and that crash is then swallowed by the same
bare except → blind retry ignoring the requested delay. The sibling method
`_request_with_retry` (the main attack path) has the correct structure:
specific exception handlers, and it does NOT retry 4xx (only 429 and 5xx).
`_request_raw` should mirror that structure.

## Current state

- `modules/llm_client.py:332-354` — `_request_raw` (the broken method).
- `modules/llm_client.py:402-444` — `_request_with_retry` (the correct exemplar to mirror).

Excerpt — the broken method (`modules/llm_client.py:332-354`):

```python
    def _request_raw(self, url, headers, payload, attempt=0):
        """Make a request and return the raw JSON response dict."""
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            self.request_count += 1
            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = float(response.headers.get("Retry-After", self.retry_base_delay))
                wait = min(retry_after + random.uniform(0, 1), self.retry_max_delay)
                time.sleep(wait)
                return self._request_raw(url, headers, payload, attempt + 1)
            if response.status_code >= 500 and attempt < self.max_retries:
                wait = min(self.retry_base_delay * (2 ** attempt) + random.uniform(0, 1), self.retry_max_delay)
                time.sleep(wait)
                return self._request_raw(url, headers, payload, attempt + 1)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.error_count += 1
            if attempt < self.max_retries:
                wait = min(self.retry_base_delay * (2 ** attempt), self.retry_max_delay)
                time.sleep(wait)
                return self._request_raw(url, headers, payload, attempt + 1)
            raise
```

Two bugs: (a) `except Exception` catches the 4xx from `raise_for_status()`
(line 346) and the `ValueError` from `response.json()` (line 347) and retries
them — should not retry 4xx; (b) `float(Retry-After)` (line 338) crashes on
HTTP-date format.

Excerpt — the correct exemplar (`modules/llm_client.py:402-444`):

```python
    def _request_with_retry(self, url, headers, payload, parse_func, attempt=0):
        start = time.time()
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            ...
            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", self.retry_base_delay))
                if attempt < self.max_retries:
                    ...
            if response.status_code >= 500 and attempt < self.max_retries:
                ...
            response.raise_for_status()
            return parse_func(response)
        except requests.exceptions.Timeout:
            ...  # specific handler, retries
        except requests.exceptions.ConnectionError:
            ...  # specific handler, retries
        except requests.exceptions.RequestException as e:
            self.error_count += 1
            raise Exception(f"API request failed: {e}")
        except Exception as e:
            self.error_count += 1
            raise Exception(f"Failed to parse response: {e}")
```

Note: the exemplar does NOT retry on `raise_for_status()` 4xx — it raises.
`_request_raw` must do the same. (Both share the `float(Retry-After)` bug —
fix it in both, since they share the pattern.)

### Repo conventions to match

- `modules/llm_client.py` uses `requests`, `time`, `random`, `colorama` (already imported, lines 6-13).
- Retry structure: specific `except` clauses for `Timeout`/`ConnectionError`, raise for `RequestException`/`Exception` (see exemplar).
- Parse `Retry-After` defensively (int seconds OR HTTP-date).

## Commands you will need

| Purpose   | Command | Expected on success |
|-----------|---------|---------------------|
| Lint      | `uv run ruff check modules/llm_client.py` | exit 0 |
| Typecheck | `uv run mypy modules/llm_client.py` | exit 0 |
| Tests     | `uv run pytest -q` (requires plan 001) | all pass |

## Scope

**In scope** (the only file you should modify):
- `modules/llm_client.py` — `_request_raw` (lines 332-354) and the `float(Retry-After)` line in `_request_with_retry` (line 410).
- `tests/test_llm_client_retry.py` (create — depends on plan 001).

**Out of scope** (do NOT touch):
- `chat()`, `chat_raw()`, `generate()`, `discover_loaded_model()` — routing logic; only the two retry helpers change.
- The provider formatting methods (`_format_*_request`).
- `_parse_*_response` methods.

## Git workflow

- Branch: `advisor/020-fix-request-raw-retry`
- Commit message: `fix: don't retry 4xx in _request_raw; parse Retry-After safely`
- Do NOT push unless instructed.

## Steps

### Step 1: Add a safe Retry-After parser

Add a small helper method (or module-level function) that parses `Retry-After`
handling both integer-seconds and RFC 7231 HTTP-date formats:

```python
import email.utils  # add to imports at top of file

def _parse_retry_after(value):
    """Parse Retry-After header: int seconds or RFC 7231 HTTP-date. Returns float seconds."""
    if not value:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        pass
    try:
        dt = email.utils.parsedate_to_datetime(value)
        if dt is not None:
            import datetime
            return max(0.0, (dt - datetime.datetime.now(dt.tzinfo)).total_seconds())
    except (TypeError, ValueError):
        pass
    return None
```

**Verify**: `grep -n '_parse_retry_after' modules/llm_client.py` → ≥1 match. `uv run ruff check modules/llm_client.py` → exit 0.

### Step 2: Fix `_request_raw` — mirror `_request_with_retry`'s structure

Rewrite `_request_raw` (lines 332-354) to: retry only on 429 and 5xx (already
there), use `_parse_retry_after`, and use **specific** exception handlers
instead of bare `except Exception` (so 4xx from `raise_for_status` and
`ValueError` from `.json()` raise, not retry):

```python
    def _request_raw(self, url, headers, payload, attempt=0):
        """Make a request and return the raw JSON response dict."""
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            self.request_count += 1
            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                wait = min((retry_after or self.retry_base_delay) + random.uniform(0, 1), self.retry_max_delay)
                time.sleep(wait)
                return self._request_raw(url, headers, payload, attempt + 1)
            if response.status_code >= 500 and attempt < self.max_retries:
                wait = min(self.retry_base_delay * (2 ** attempt) + random.uniform(0, 1), self.retry_max_delay)
                time.sleep(wait)
                return self._request_raw(url, headers, payload, attempt + 1)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            self.error_count += 1
            if attempt < self.max_retries:
                wait = min(self.retry_base_delay * (2 ** attempt), self.retry_max_delay)
                time.sleep(wait)
                return self._request_raw(url, headers, payload, attempt + 1)
            raise
        except requests.exceptions.ConnectionError:
            self.error_count += 1
            if attempt < self.max_retries:
                wait = min(self.retry_base_delay * (2 ** attempt), self.retry_max_delay)
                time.sleep(wait)
                return self._request_raw(url, headers, payload, attempt + 1)
            raise
        except requests.exceptions.RequestException as e:
            self.error_count += 1
            raise Exception(f"API request failed: {e}")
```

Key change: `raise_for_status()` (4xx) now raises → caught by
`RequestException` → re-raised (NOT retried). `response.json()` ValueError
propagates (not caught by a retry handler).

**Verify**: `grep -n 'except Exception' modules/llm_client.py` within `_request_raw` → no bare-Exception catch in the rewritten method (the `_request_with_retry` method may still have its own `except Exception` at line 442 for parse errors — that's the exemplar's design; leave it). `uv run ruff check modules/llm_client.py` → exit 0.

### Step 3: Fix `float(Retry-After)` in `_request_with_retry` too

In `_request_with_retry` (line 410), replace:
```python
                retry_after = float(response.headers.get("Retry-After", self.retry_base_delay))
```
with:
```python
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                if retry_after is None:
                    retry_after = self.retry_base_delay
```

**Verify**: `grep -n 'float(response.headers.get' modules/llm_client.py` → no matches (both call sites now use `_parse_retry_after`).

### Step 4: Add characterization tests

Create `tests/test_llm_client_retry.py` (depends on plan 001's harness). Use a
fake `requests.post` that returns a 401, and assert `_request_raw` does NOT
retry (raises immediately). Also test `_parse_retry_after` on an HTTP-date:

```python
"""Characterization tests for _request_raw retry + Retry-After parsing."""
import datetime
import email.utils
from modules.llm_client import _parse_retry_after


def test_parse_retry_after_int_seconds():
    assert _parse_retry_after("5") == 5.0

def test_parse_retry_after_http_date():
    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=10)
    val = email.utils.format_datetime(future)
    result = _parse_retry_after(val)
    assert result is not None and 0 < result <= 15  # ~10s, allow slack

def test_parse_retry_after_garbage_returns_none():
    assert _parse_retry_after("not-a-date") is None
    assert _parse_retry_after(None) is None
```

(Testing that 4xx doesn't retry requires mocking `requests.post` — add if
plan 001's harness supports `unittest.mock`; otherwise the `_parse_retry_after`
unit tests are the core verification.)

**Verify**: `uv run pytest tests/test_llm_client_retry.py -q` → all pass. (If 001 absent, STOP and defer tests; code fix in steps 1-3 can proceed.)

## Test plan

- `tests/test_llm_client_retry.py` (above) — covers `_parse_retry_after` for int, HTTP-date, garbage.
- Edge case: `Retry-After` header absent → falls back to `retry_base_delay`.
- Verification: `uv run pytest tests/test_llm_client_retry.py -q` → all pass.

## Done criteria

ALL must hold:

- [ ] `grep -n '_parse_retry_after' modules/llm_client.py` returns ≥1 match (def) + ≥2 call sites
- [ ] `grep -n 'float(response.headers.get' modules/llm_client.py` returns no matches
- [ ] `_request_raw` has no bare `except Exception` that retries 4xx (visual / grep within the method)
- [ ] `uv run ruff check modules/llm_client.py` exits 0
- [ ] `uv run mypy modules/llm_client.py` exits 0
- [ ] `uv run pytest tests/test_llm_client_retry.py -q` exits 0 (if 001 landed)
- [ ] No files outside the in-scope list are modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:
- `modules/llm_client.py` has drifted from the excerpts (line numbers / structure changed).
- `_request_raw` is called by paths other than `chat_raw`/model-discovery (grep its callers) — the no-retry-4xx change might affect them; report.
- `email.utils` is unavailable (it's stdlib; should always be present — if not, STOP).
- The `except Exception` at line 442 of `_request_with_retry` (parse-error handler) is load-bearing for some flow — do NOT remove it; only fix the `Retry-After` line there.

## Maintenance notes

- A reviewer should confirm the 4xx-no-retry change doesn't break model-discovery: `discover_loaded_model` (line 163) already catches `requests.RequestException` per-URL (lines 195-196) and continues to the next candidate — so a 401 on one endpoint correctly moves to the next without wasting retries. Good.
- The `Retry-After` fix applies to both the raw path and the main attack path — both benefit.
- If a provider returns a non-standard `Retry-After` format, `_parse_retry_after` falls back to `retry_base_delay` rather than crashing.
