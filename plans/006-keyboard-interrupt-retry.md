# Plan 006 — Fix bare `except Exception` that swallows KeyboardInterrupt during retries

- **Finding**: #6 — `modules/llm_client.py` has two bare `except Exception` catches, one in
  `_request_raw` (lines ~345-354) and one in `_request_with_retry` (lines ~445-447), that
  catch *everything* including `KeyboardInterrupt`. On retry exhaustion the operator must
  hold Ctrl+C through the full retry chain before the signal finally breaks out.
- **Written against commit**: `e82a0f4`
- **Effort**: S (minutes to apply; minutes to verify)
- **Risk of this change**: LOW — only narrows exception filtering; no behavior change for
  HTTP errors or retry logic.

## Why this matters

When an operator runs a long sweep and wants to cancel with `Ctrl+C`, the
`KeyboardInterrupt` is caught by these bare handlers, converted into a retry cycle, and
only propagates after all retries are exhausted and all `time.sleep()` waits have run.
For `max_retries=5` with exponential backoff the operator can be blocked for tens of
seconds with no way to stop the process.

Current — `_request_raw` (`modules/llm_client.py:345-354`):

```python
        except Exception as e:
            self.error_count += 1
            if attempt < self.max_retries:
                wait = min(self.retry_base_delay * (2 ** attempt), self.retry_max_delay)
                time.sleep(wait)
                return self._request_raw(url, headers, payload, attempt + 1)
            raise
```

Current — `_request_with_retry` (`modules/llm_client.py:445-447`):

```python
        except Exception as e:
            self.error_count += 1
            raise Exception(f"Failed to parse response: {e}")
```

In the second method `KeyboardInterrupt` never even reaches a re-raise path; it is
immediately wrapped as `Exception("Failed to parse response: ...")` and bubbles out as a
confusing parse error, losing the original signal semantics.

## Reproduction (before the fix)

```bash
python -c "
import modules.llm_client as lc, requests, time
# Monkey-patch to force failure so we enter the generic except path
old_post = requests.post
def slow_fail(*a, **k):
    time.sleep(0.5)
    raise KeyboardInterrupt('simulated')
requests.post = slow_fail

c = lc.LLMClient()
c.max_retries = 2
c.retry_base_delay = 0.1
try:
    c._request_raw('http://x', {}, {})
except KeyboardInterrupt:
    print('KeyboardInterrupt propagated --- GOOD')
except Exception as e:
    print(type(e).__name__, e, '--- BAD: swallowed or wrapped')
"
```

**Expected before fix**: `Exception Failed to parse response: simulated --- BAD` (or
retry loop then wrapped).  
**Expected after fix**: `KeyboardInterrupt propagated --- GOOD`.

> If the executor environment can't import `modules.llm_client` (missing dependencies),
> rely on `py_compile` + the `grep` checks below instead.

## Conventions to follow

- The codebase already uses colorama `Fore.YELLOW` for retry messages — preserve that.
- Python ≥3.14, uv-managed; no new dependencies.

## Files in scope

- `modules/llm_client.py` — `_request_raw` and `_request_with_retry` only.

## Files explicitly OUT of scope

- Any other file in `modules/` or elsewhere — do not broaden the fix.
- The retry timing math, backoff strategy, or the `max_retries` config — untouched.

## The change

### 1. `_request_raw` (lines ~345-354)

Insert a `KeyboardInterrupt` catch-before-retry, then narrow the remaining catch to the
actual failure modes (`requests` errors and `ValueError` from `.json()` / bad payloads).

Current:

```python
        except Exception as e:
            self.error_count += 1
            if attempt < self.max_retries:
                wait = min(self.retry_base_delay * (2 ** attempt), self.retry_max_delay)
                time.sleep(wait)
                return self._request_raw(url, headers, payload, attempt + 1)
            raise
```

Replace with:

```python
        except KeyboardInterrupt:
            raise
        except (requests.exceptions.RequestException, ValueError) as e:
            self.error_count += 1
            if attempt < self.max_retries:
                wait = min(self.retry_base_delay * (2 ** attempt), self.retry_max_delay)
                time.sleep(wait)
                return self._request_raw(url, headers, payload, attempt + 1)
            raise
```

### 2. `_request_with_retry` (lines ~445-447)

Same principle: let `KeyboardInterrupt` pass, narrow the catch to what the `parse_func`
actually can throw (typically `KeyError`, `ValueError`, or `json.JSONDecodeError`).

Current:

```python
        except Exception as e:
            self.error_count += 1
            raise Exception(f"Failed to parse response: {e}")
```

Replace with:

```python
        except KeyboardInterrupt:
            raise
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            self.error_count += 1
            raise Exception(f"Failed to parse response: {e}")
```

> Note: `json.JSONDecodeError` is a subclass of `ValueError`, but listing it explicitly
> makes the intent self-documenting for future readers. If the environment's JSON decoder
> raises a different type, add it here — do **not** fall back to `Exception`.

## Done criteria (machine-checkable)

```bash
python -m py_compile modules/llm_client.py                  # exit 0
grep -n "except Exception" modules/llm_client.py || echo "no bare catches remain"
# The grep should print only lines outside these two functions (if any).
```

- `py_compile` passes with no syntax errors.
- No bare `except Exception` remains inside `_request_raw` or `_request_with_retry`.
- Both functions contain `except KeyboardInterrupt: raise` before their narrowed catches.

## Test plan

No new test file is required — this is a UX/behavioral guard, not a logic change. Verify
with the reproduction snippet under **Reproduction** above, or with a minimal inline check:

```bash
python -c "
import ast, sys
src = open('modules/llm_client.py').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.ExceptHandler):
        if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == 'Exception'):
            print('bare/wide except at line', node.lineno)
            sys.exit(1)
print('no bare/wide except handlers found')
"
```

> The AST walk above is intentionally strict — it will flag *any* bare `except:` or
> `except Exception:` in the file. If other unrelated handlers exist, scope the check to the
> two function bodies instead.

## Maintenance note

Any future retry logic in `llm_client.py` must follow this pattern:

1. `except KeyboardInterrupt: raise` first.
2. Only catch the specific exception types that are *expected* and *retry-worthy*.
3. Never catch `Exception` (or bare `except:`) in a retry loop.

If a new provider integration introduces a new failure mode (e.g. a custom auth error),
add that exception type explicitly; do not regress to `Exception`.

## Escape hatches — STOP and report instead of improvising

- If either method has already been refactored (line numbers moved / no bare
  `except Exception` present), STOP — the finding may be stale for this commit. Report
  what you found.
- If `py_compile` fails after the edit, double-check indentation and parenthesis balance
  before assuming a deeper issue.
