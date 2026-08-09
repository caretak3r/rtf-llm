# Plan 004 — Make the `attacks.enable_*` flags and `max_requests_per_minute` real (or remove them)

- **Finding**: #7 — `config.json` and `ConfigManager`'s defaults advertise nine
  `attacks.enable_*` flags and a `rate_limiting.max_requests_per_minute` cap that **no code
  reads**. Setting `enable_jailbreak: false` or lowering the request cap does nothing — the
  config silently lies about what's configurable.
- **Written against commit**: `e82a0f4`
- **Effort**: S (about half a day with tests)
- **Risk of this change**: LOW to MED depending on the option chosen below. The recommended
  option (wire the enable flags into the `all` dispatch) is behavior-additive and defaults to
  the current behavior when flags are absent.

## Evidence (verified)

`grep` across the repo shows these keys are **defined but never read**:

- `modules/config_manager.py:91-98` and `config.json:91-98` define
  `enable_prompt_injection`, `enable_jailbreak`, `enable_data_extraction`,
  `enable_system_prompt_extraction`, `enable_adversarial_inputs`, `enable_role_confusion`,
  `enable_context_injection`, `enable_weight_manipulation`, plus `enable_all`
  (`config_manager.py:90`). The only enable-flag anyone reads is `enable_multi_turn`
  (`main.py:330`) — and that one isn't even present in the defaults or `config.json`.
- `modules/config_manager.py:122` / `config.json:154` define
  `rate_limiting.max_requests_per_minute: 60`; no reader exists. The only throttle actually
  applied is the fixed `time.sleep(delay_between_requests)` scattered through the modules.

The dispatch in `main.py:282-457` is driven purely by `args.module`; the `enable_*` flags are
never consulted for `--module all`.

## Decision: which fix

Pick **Option A** (recommended). It removes the lie by making the flags do the obvious thing,
consistent with how `enable_multi_turn` is already treated at `main.py:330`.

### Option A (recommended) — Wire `enable_<module>` into the `all` run

When `--module all`, skip a module if its `attacks.enable_<module>` flag is explicitly
`false`. Absent/`true` → run it (preserves today's behavior). Leave `max_requests_per_minute`
as a documentation fix (see below) since honoring it properly requires a shared rate limiter
(finding #9) that is out of scope here.

### Option B (only if the maintainer prefers) — Delete the dead keys

Remove the nine `enable_*` keys and `max_requests_per_minute` from `config.json` and
`config_manager._get_default_config`, and note in the README that module selection is via
`--module`. Smaller surface, but throws away a genuinely useful capability. **Do not choose
this without maintainer confirmation** — default to Option A.

The rest of this plan implements **Option A**.

## Conventions to follow

- Match the existing `enable_multi_turn` idiom at `main.py:330`:
  `config.get('attacks', {}).get('enable_multi_turn', True)` — default `True` when absent.
- Module keys in the `attacks` section use the snake_case module name
  (`enable_prompt_injection`, etc.), matching the result-tuple names appended in `main.py`.

## Files in scope

- `main.py` — the `if args.module == '<x>' or args.module == 'all':` guards for the eight
  toggle-able red-team modules (prompt-injection, jailbreak, data-extraction,
  system-prompt-extraction, adversarial-inputs, role-confusion, context-injection,
  weight-manipulation).
- `README.md` and/or `docs/cli-options.md` — document that `attacks.enable_*` gate the `all`
  sweep, and that `max_requests_per_minute` is **not currently enforced** (see maintenance
  note) so users don't rely on it.
- `tests/test_enable_flags.py` (new; only if `tests/` exists from plan 001).

## Files explicitly OUT of scope

- The single-module path: `--module jailbreak` must **always** run jailbreak regardless of the
  flag (an explicit module request overrides the `all`-sweep gate). Only the `== 'all'` branch
  consults the flag.
- `multi-turn` (already gated), `defense-tester`, `purple-team`, `multimodal-injection`, and
  all lab/comparison modules — leave their guards unchanged; the `attacks.enable_*` set in the
  config only covers the eight core red-team modules listed above.
- Implementing a real token-bucket for `max_requests_per_minute` — that's finding #9.

## The change (Option A)

For each of the eight core modules, add an enable-gate that only applies to the `all` sweep.
Define a tiny helper near the top of the dispatch (just before `main.py:282`) to avoid
repeating the pattern:

```python
        attacks_cfg = config.get('attacks', {})

        def _enabled(module_key):
            # Explicit single-module runs always run; the 'all' sweep honors the flag.
            if args.module != 'all':
                return True
            return attacks_cfg.get(f'enable_{module_key}', True)
```

Then change each guard. For example, prompt-injection at `main.py:282`:

```python
        if args.module == 'prompt-injection' or (args.module == 'all' and _enabled('prompt_injection')):
```

Apply the analogous edit to these seven guards (use the snake_case key in parentheses):

| Guard line (approx) | Module key |
|---|---|
| `main.py:288` jailbreak | `jailbreak` |
| `main.py:294` data-extraction | `data_extraction` |
| `main.py:300` system-prompt-extraction | `system_prompt_extraction` |
| `main.py:306` adversarial-inputs | `adversarial_inputs` |
| `main.py:312` role-confusion | `role_confusion` |
| `main.py:318` context-injection | `context_injection` |
| `main.py:324` weight-manipulation | `weight_manipulation` |

Leave `multi-turn` (`main.py:330`) exactly as it is — it already gates on
`enable_multi_turn`. Do not touch the defense-tester/purple-team/multimodal/lab/comparison
branches.

## Done criteria (machine-checkable)

```bash
python -m py_compile main.py                       # exit 0
# All eight core guards now consult _enabled(...):
grep -c "_enabled(" main.py                         # -> 8
```
Behavioral check (no live model needed — uses a config that disables one module and confirms
the gate logic; run only if the executor can execute `main.py` far enough, otherwise rely on
the unit test):

- With default `config.json` (all flags true) and `--module all`, every core module still runs
  (unchanged behavior).
- With `attacks.enable_jailbreak` set to `false` and `--module all`, the jailbreak banner
  (`[*] Running Jailbreak Attacks...`) does **not** appear.
- With `--module jailbreak` and `enable_jailbreak: false`, jailbreak **does** run (explicit
  request overrides the gate).

## Test plan

Only if `tests/` exists (plan 001 landed). The `_enabled` logic is pure and can be tested by
replicating it (it depends only on `args.module` and the config dict):

```python
def enabled(module_key, module_arg, attacks_cfg):
    if module_arg != 'all':
        return True
    return attacks_cfg.get(f'enable_{module_key}', True)


def test_all_sweep_honors_disable_flag():
    assert enabled('jailbreak', 'all', {'enable_jailbreak': False}) is False


def test_all_sweep_defaults_enabled_when_flag_absent():
    assert enabled('jailbreak', 'all', {}) is True


def test_explicit_module_overrides_disable_flag():
    assert enabled('jailbreak', 'jailbreak', {'enable_jailbreak': False}) is True
```

If plan 001 hasn't landed, skip the test file and verify via `Done criteria`. Note it in your
report.

## Maintenance note

`max_requests_per_minute` remains **unenforced** after this plan — it needs a shared rate
limiter, which is finding #9 (sweep concurrency). Until that lands, the docs must say the cap
is advisory/not enforced so operators don't assume protection. When #9 is implemented, wire
`max_requests_per_minute` into the limiter and remove the doc caveat. If finding #6 (unified
module registry) lands, the `_enabled` gate should move into the registry's `all`-iteration so
there's a single place that maps module key → enable flag.

## Escape hatches — STOP and report instead of improvising

- If the maintainer's intent is unclear and you're tempted toward Option B (deletion), STOP
  and report — deleting a documented-looking capability is a product decision, not an executor
  call. Default to Option A.
- If the `attacks` section in `config.json` already contains `enable_multi_turn` or the guards
  already consult the flags, the finding is partially stale — report the actual state.
