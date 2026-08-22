# Plan 024: Restrict dashboard to serve only the report file

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- main.py modules/report_generator.py`
> If these changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (complementary to plan 003 which narrows the bind; land together for defense-in-depth)
- **Category**: security
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

The dashboard HTTP server (`serve_dashboard` in `main.py`) uses stdlib
`SimpleHTTPRequestHandler` with only `__init__` + `log_message` overridden — no
`do_GET` override. So stdlib behavior applies: a directory listing on `GET /`
AND arbitrary file fetch for **every** file under `report_dir`. That directory
also contains `llm_redteam.log`, which `report_generator.py` writes with
200-char attack patterns (line 105) and **300-char LLM response snippets**
(lines 112-116, when `include_responses` defaults to True). Anyone reaching the
running dashboard can `GET /llm_redteam.log` to read response snippets that
may hold the canary token or extracted system-prompt content. This is
over-disclosure beyond serving the single requested report. Plan 003 narrows
the *bind* (to localhost); this plan narrows *what is served* — independent,
complementary defense-in-depth.

## Current state

- `main.py:65-78` — `serve_dashboard` + `DashboardHandler`.
- `modules/report_generator.py:49` — writes `llm_redteam.log` into `output_dir` (same as report_dir).
- `modules/report_generator.py:105` — logs 200-char attack patterns.
- `modules/report_generator.py:112-116` — logs 300-char response snippets when `include_responses` (default True).

Excerpt (`main.py:65-78`):

```python
def serve_dashboard(report_path, host='0.0.0.0', port=8090):
    """Serve the HTML dashboard on an HTTP server."""
    report_dir = os.path.dirname(os.path.abspath(report_path))
    report_file = os.path.basename(report_path)

    class DashboardHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=report_dir, **kwargs)

        def log_message(self, format, *args):
            pass  # Suppress per-request logging

    try:
        server = HTTPServer((host, port), DashboardHandler)
        ...
```

No `do_GET` override → stdlib serves the whole directory + directory listing.

Excerpt (`modules/report_generator.py:49`):

```python
        log_file = os.path.join(self.output_dir, 'llm_redteam.log')
```

### Repo conventions to match

- `main.py` imports `HTTPServer`, `SimpleHTTPRequestHandler` from `http.server` (line 18).
- `os` is imported (line 14). `os.path` used throughout.

## Commands you will need

| Purpose   | Command | Expected on success |
|-----------|---------|---------------------|
| Lint      | `uv run ruff check main.py` | exit 0 |
| Typecheck | `uv run mypy main.py` | exit 0 |
| Tests     | `uv run pytest -q` (requires plan 001) | all pass |

## Scope

**In scope** (the only files you should modify):
- `main.py` — `serve_dashboard` / `DashboardHandler` only.
- `tests/test_dashboard_handler.py` (create — depends on plan 001; optional).

**Out of scope** (do NOT touch):
- `modules/report_generator.py` — do NOT move the log file or change logging (that's a separate concern; this plan restricts serving, not writing).
- The `0.0.0.0` bind default — that's plan 003's scope. This plan restricts `do_GET` regardless of bind.
- `generate_report.py` — not involved in serving.

## Git workflow

- Branch: `advisor/024-restrict-dashboard-serving`
- Commit message: `fix: restrict dashboard to serve only the report file`
- Do NOT push unless instructed.

## Steps

### Step 1: Override `do_GET` and `list_directory` on `DashboardHandler`

In `main.py`, add `do_GET` and `list_directory` overrides to `DashboardHandler`
so it serves **only** `report_file` (the requested report) and returns 404 for
everything else (including the directory listing and `llm_redteam.log`):

```python
    class DashboardHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=report_dir, **kwargs)

        def do_GET(self):
            # Serve only the requested report file; 404 everything else
            path = self.translate_path(self.path)
            if os.path.basename(path) == report_file:
                super().do_GET()
            else:
                self.send_error(404, "Not found")

        def list_directory(self, path):
            # Disable directory listing
            self.send_error(404, "Not found")

        def log_message(self, format, *args):
            pass  # Suppress per-request logging
```

`super().do_GET()` (via `SimpleHTTPRequestHandler`) still handles the
single-file serve correctly; the guard ensures only `report_file` is
reachable. `translate_path` + `os.path.basename` prevents path-tricks (e.g.
`/llm_redteam.log` → basename `llm_redteam.log` ≠ `report_file` → 404).

**Verify**: `grep -n 'def do_GET\|def list_directory' main.py` → 2 matches. `uv run ruff check main.py` → exit 0. `uv run mypy main.py` → exit 0.

### Step 2: Add a characterization test (optional, if plan 001 landed)

Create `tests/test_dashboard_handler.py`:

```python
"""Test that the dashboard serves only the report file."""
import os
import tempfile
from http.server import HTTPServer
import urllib.request
from main import serve_dashboard  # may need to refactor serve_dashboard to accept a handler for testing
```

If `serve_dashboard` is hard to unit-test as-is (it calls `serve_forever`),
the test can instead construct `DashboardHandler` directly with a mock request.
If that's too involved, defer the test and rely on the manual verification
below. The core guarantee (404 on `llm_redteam.log`) is the contract.

**Verify** (manual, if no test): `uv run ruff check main.py` → exit 0.

### Step 3: Manual smoke test (optional)

```bash
# create a fake report dir with a report + a log
mkdir -p /tmp/dash-test && echo '<html>report</html>' > /tmp/dash-test/report.html && echo 'secret-log' > /tmp/dash-test/llm_redteam.log
# in a Python REPL or small script, call serve_dashboard('/tmp/dash-test/report.html', host='127.0.0.1', port=8099)
# then: curl http://127.0.0.1:8099/report.html → 200, report content
#       curl http://127.0.0.1:8099/llm_redteam.log → 404
#       curl http://127.0.0.1:8099/ → 404 (no directory listing)
```

**Verify**: `curl` on the report file returns 200; on `llm_redteam.log` and `/` returns 404.

## Test plan

- `tests/test_dashboard_handler.py` (optional) — assert `do_GET` returns 404 for any path except `report_file`; assert `list_directory` returns 404.
- If `serve_dashboard` is hard to test as-is, the manual smoke test in step 3 is acceptable verification.
- Verification: report file serves (200); log file and directory listing return 404.

## Done criteria

ALL must hold:

- [ ] `grep -n 'def do_GET' main.py` returns 1 match in `DashboardHandler`
- [ ] `grep -n 'def list_directory' main.py` returns 1 match in `DashboardHandler`
- [ ] `do_GET` serves only `report_file` (404 otherwise) — verified by manual smoke or test
- [ ] `uv run ruff check main.py` exits 0
- [ ] `uv run mypy main.py` exits 0
- [ ] No files outside `main.py` (and optionally `tests/test_dashboard_handler.py`) are modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:
- `main.py` `serve_dashboard` has drifted from the excerpt (e.g. already uses `ThreadingHTTPServer` or has a custom handler).
- The `translate_path` + `basename` check is insufficient on the target Python version — verify `SimpleHTTPRequestHandler.translate_path` exists (it does on 3.10+); if the signature differs, adapt.
- Restricting `do_GET` breaks the dashboard's own asset loading (if the HTML report references sibling assets like CSS/JS/images in the same dir) — check whether `report_file` is self-contained. If the report loads sibling assets, the guard must allow those too (whitelist by extension or check the report's asset references). Report if this is the case before proceeding.

## Maintenance notes

- **Complementary to plan 003**: 003 narrows the bind (localhost); 024 narrows the served surface. Both should land for defense-in-depth. If 003 has already landed, 024 is still independently valuable (restricts what a local or LAN client can fetch).
- A reviewer should confirm the HTML report (`html_dashboard_template.html` output) is self-contained (inline CSS/JS) — if it references sibling files, the `do_GET` guard would 404 them. Verify by inspecting a generated report's `<link>`/`<script src>` tags. If assets are external, whitelist them.
- If `include_responses` logging is later made opt-in (a separate improvement), the `llm_redteam.log` exposure shrinks, but restricting `do_GET` is still the right structural fix — don't rely on logging changes alone.
- Future: if the dashboard gains interactive features (e.g. report comparison), the `do_GET` whitelist will need updating — note this in the handler's docstring.
