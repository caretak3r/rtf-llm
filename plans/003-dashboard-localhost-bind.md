# Plan 003 — Default the dashboard server to loopback (`127.0.0.1`)

- **Finding**: #3 — After every run the framework starts an unauthenticated static HTTP
  server bound to `0.0.0.0` (all interfaces), serving the entire report directory (including
  `llm_redteam.log`) with directory listing enabled.
- **Written against commit**: `e82a0f4`
- **Effort**: S (about an hour with the test)
- **Risk of this change**: LOW — changes a default bind address; remote binding stays
  available behind an explicit flag. No change to report generation or attack logic.

## Why this matters

`serve_dashboard` runs `SimpleHTTPRequestHandler` rooted at the report directory. Two defaults
combine into a network exposure:

- `main.py:65` — `def serve_dashboard(report_path, host='0.0.0.0', port=8090):`
- `main.py:172-173` — `--serve-host` argparse default is `'0.0.0.0'`
- `main.py:498-499` — this server is started automatically after every run unless `--no-serve`.

`SimpleHTTPRequestHandler` serves directory listings, so anyone who can reach the host on
port 8090 (same LAN, VPN, or via a misconfigured NAT) can browse and download every report
under `docs/reports/` plus the attack log. Those artifacts contain the deployed target system
prompt, the ground-truth canary token, and verbatim model responses — the most sensitive
output of an engagement. Binding to loopback by default keeps the local "open the dashboard
in my browser" convenience while removing the network exposure. Operators who genuinely need
remote access can still pass `--serve-host 0.0.0.0` explicitly.

## Conventions to follow

- Keep the colorama status-print style already used in `serve_dashboard`
  (`{Fore.CYAN}[*] ...{Style.RESET_ALL}`, `{Fore.YELLOW}[!] ...{Style.RESET_ALL}`).
- `main.py` already treats `0.0.0.0` specially when composing the browser URL
  (`main.py:80-81` rewrites it to `localhost`); keep that logic working.

## Files in scope

- `main.py` — the `serve_dashboard` default (line 65) and the `--serve-host` argparse
  default (lines 172-173). Optionally a one-line warning when a non-loopback host is chosen.
- `README.md` — update the flag docs for `--serve-host` (the reference table lists the old
  `default: 0.0.0.0`).
- `tests/test_serve_host_default.py` (new; only if `tests/` exists from plan 001).

## Files explicitly OUT of scope

- The `HTTPServer`/`DashboardHandler` internals and the port-bump recursion — leave behavior
  as-is; only the default host changes.
- `config.json` — the serve host is a CLI concern, not a config key today; don't add one.

## The change

1. `main.py:65` — change the function default:

   ```python
   def serve_dashboard(report_path, host='127.0.0.1', port=8090):
   ```

2. `main.py:172-173` — change the argparse default and help text:

   ```python
   parser.add_argument('--serve-host', default='127.0.0.1',
                      help='Host to serve the dashboard on (default: 127.0.0.1; '
                           'pass 0.0.0.0 to expose on all interfaces)')
   ```

3. (Recommended) Add an explicit warning when the operator opts into a non-loopback bind.
   Immediately after the `try:` and successful `HTTPServer(...)` construction in
   `serve_dashboard` (i.e. right after `main.py:78`), add:

   ```python
           if host not in ('127.0.0.1', 'localhost', '::1'):
               print(f"{Fore.YELLOW}[!] Dashboard is bound to {host} and reachable from "
                     f"other machines. Reports contain sensitive engagement output.{Style.RESET_ALL}")
   ```

   Place this before the existing `print(f"\n{Fore.CYAN}[*] Serving dashboard ...")` line so
   the warning appears first.

Leave the browser-URL rewrite at `main.py:80-81` intact — with the new default `host` is
`127.0.0.1`, so the URL will already be `http://127.0.0.1:8090/...`, which browsers open fine.

## Done criteria (machine-checkable)

```bash
python -m py_compile main.py                                   # exit 0
python -c "import ast,inspect; src=open('main.py').read(); assert \"host='0.0.0.0'\" not in src and \"default='0.0.0.0'\" not in src, 'still binds 0.0.0.0'; print('ok')"
python main.py --help | grep -A1 'serve-host'                  # shows default: 127.0.0.1
```
- Neither `host='0.0.0.0'` nor `default='0.0.0.0'` appears in `main.py`.
- `--help` output documents the loopback default.

## Test plan

Only if `tests/` exists (plan 001 landed). Add `tests/test_serve_host_default.py` asserting
the argparse default, without starting a server:

```python
import ast


def test_serve_host_defaults_to_loopback():
    src = open("main.py").read()
    # The argparse default must be loopback, not all-interfaces.
    assert "default='0.0.0.0'" not in src
    assert "host='0.0.0.0'" not in src
    assert "127.0.0.1" in src
```

(An AST/text assertion is sufficient here; binding a real socket in a unit test is flaky and
unnecessary for a default-value change.)

## Maintenance note

If a future change adds a config-driven serve host, apply the same default (loopback) and
keep the non-loopback warning. Do not re-widen the default to `0.0.0.0` for convenience — the
served directory contains sensitive engagement artifacts. This finding pairs conceptually with
finding #4 (those same reports are auto-published to GitHub Pages); if #4 is planned later,
cross-reference it.

## Escape hatches — STOP and report instead of improvising

- If `serve_dashboard` or the argparse block has already been changed to loopback at this
  commit, STOP — the finding is already resolved; report that.
- Do **not** attempt to add authentication to the server or replace `SimpleHTTPRequestHandler`
  in this plan — that's a larger design change outside this scope. Loopback-by-default is the
  agreed fix here.
