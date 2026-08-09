# Plan 005 — Remove the dead `IndirectInjectionModule` (or wire it in)

- **Finding**: #8 — `modules/indirect_injection.py` defines `IndirectInjectionModule` (71
  lines), but nothing imports or dispatches it. It presents as a live attack module while
  being unreachable, inflating the surface and misleading maintainers.
- **Written against commit**: `e82a0f4`
- **Effort**: S (under an hour)
- **Risk of this change**: LOW — removing genuinely unreferenced code; the plan includes an
  explicit re-verification step so you don't delete something reachable.

## Critical distinction (read before doing anything)

There are **two different things** that share the name `indirect_injection`. Do **not** confuse
them:

1. **The dead class** — `modules/indirect_injection.py` → `class IndirectInjectionModule`.
   This is what this plan removes. It is imported by nothing.
2. **A live pattern category** — the string `'indirect_injection'` used as a key inside
   `modules/prompt_injection.py` (`:65`, `:251` `_get_indirect_injection_patterns`, `:672`,
   `:718`), `modules/technique_kb.py:125`, `modules/report_generator.py:339`, and
   `generate_report.py:132,557`. **These are live and must stay.** They are attack-pattern
   data inside the prompt-injection module, not references to the dead class.

The verification below distinguishes the two by grepping for the **class name**
(`IndirectInjectionModule`) and the **module import path**, never the bare string.

## Evidence (verified)

```
$ grep -rn --include='*.py' 'IndirectInjection' .            # class name
modules/indirect_injection.py:5:class IndirectInjectionModule:   # <- only the definition
```
No import of `IndirectInjectionModule` and no `from modules.indirect_injection import` /
`import modules.indirect_injection` exists anywhere (`main.py`, `modules/comparison.py`,
`modules/purple_team.py`, or any other file). The `all` dispatch in `main.py:282-457` never
instantiates it. There is no dynamic-import-by-name machinery in the repo that could reach it
(the module registries in `comparison.py:31` and `purple_team.py:42` are static dict literals
that do not list it).

## Decision: remove vs. wire in

The functionality it covers (indirect / retrieved-content injection) is **already implemented**
as the live `indirect_injection` pattern category inside `PromptInjectionModule`
(`prompt_injection.py:251` `_get_indirect_injection_patterns`). So the standalone class is
redundant, not a missing feature. **Recommended: delete it.**

If, on reading `modules/indirect_injection.py`, you find it implements meaningfully *different*
behavior that the pattern category does not cover, do **not** delete — STOP and report (see
escape hatches); wiring a new module into dispatch is a larger change than this plan's scope.

## Files in scope

- `modules/indirect_injection.py` — delete.
- `tests/test_no_dead_module.py` (new; only if `tests/` exists from plan 001) — a guard test
  that fails if the file reappears unreferenced.

## Files explicitly OUT of scope

- `modules/prompt_injection.py`, `modules/technique_kb.py`, `modules/report_generator.py`,
  `generate_report.py` — they use the `indirect_injection` **pattern string**; do not touch.
- `main.py` and the registries — no dispatch entry to remove (there is none).

## Steps

### Step 1 — Re-verify it is unreferenced (do this first)

```bash
grep -rn --include='*.py' 'IndirectInjection' . | grep -v 'modules/indirect_injection.py:'
grep -rn --include='*.py' 'indirect_injection import\|import indirect_injection\|modules.indirect_injection' .
```
**Expected**: both commands print **nothing**. If either prints a reference, STOP — the module
is reachable; report the reference and do not delete.

### Step 2 — Read the file to confirm redundancy

Read `modules/indirect_injection.py` in full (71 lines). Confirm its behavior is subsumed by
`PromptInjectionModule._get_indirect_injection_patterns` (`prompt_injection.py:251`). If it is
materially different, STOP (escape hatch). If redundant, proceed.

### Step 3 — Delete

```bash
git rm modules/indirect_injection.py
```

### Step 4 — Confirm nothing broke

```bash
python -c "import main"            # imports the whole module graph; must succeed
python -m py_compile main.py modules/*.py
```
**Expected**: no `ModuleNotFoundError` / `ImportError`; exit 0.

## Done criteria (machine-checkable)

```bash
test ! -f modules/indirect_injection.py && echo "deleted"          # prints "deleted"
python -c "import main; print('import ok')"                        # prints "import ok"
grep -rn --include='*.py' 'IndirectInjectionModule' . || echo "no refs"   # prints "no refs"
```
- `modules/indirect_injection.py` no longer exists.
- The full module graph still imports cleanly via `import main`.
- The live `indirect_injection` pattern category is untouched — sanity check it still exists:
  ```bash
  grep -c "_get_indirect_injection_patterns" modules/prompt_injection.py   # -> 2 (def + call)
  ```

## Test plan

Only if `tests/` exists (plan 001 landed). Add `tests/test_no_dead_module.py`:

```python
import os


def test_indirect_injection_module_file_removed():
    assert not os.path.exists("modules/indirect_injection.py")


def test_indirect_injection_pattern_category_still_live():
    # The pattern category inside PromptInjectionModule must remain.
    src = open("modules/prompt_injection.py").read()
    assert "_get_indirect_injection_patterns" in src
```

If plan 001 hasn't landed, skip the test file and rely on `Done criteria`. Note it in your
report.

## Maintenance note

If indirect/retrieved-content injection ever warrants its own first-class module (distinct from
the pattern category), reintroduce it **and** register it in `main.py`'s dispatch plus the
`comparison.py`/`purple_team.py` `MODULE_MAP`s in the same change — an attack module that isn't
in a registry is invisible. Finding #6 (unified registry) would make that a single edit.

## Escape hatches — STOP and report instead of improvising

- If Step 1 finds any reference to `IndirectInjectionModule` or the module import path, STOP —
  do not delete; report the reference.
- If Step 2 shows the class implements behavior the pattern category lacks, STOP — report it as
  "dead but potentially useful; wiring-in needs a separate plan," and leave the file in place.
- Do not "clean up" the `indirect_injection` pattern strings in `prompt_injection.py` /
  `technique_kb.py` / reports — they are live data.
