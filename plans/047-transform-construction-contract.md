# Plan 047: Deterministic transform construction + router tie safety

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat a6a9a9d..HEAD -- modules/engine/registry.py main.py scripts/run_opencode_campaign.py modules/engine/router.py modules/engine/transforms/adaptive/pair_transform.py`
> If these changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (touches `main.py` construction block and campaign script — coordinate with 040/042)
- **Category**: correctness / API contract
- **Planned at**: commit `a6a9a9d`, 2026-08-21

## Why this matters

Three related contract defects around transform construction and ranking:

1. **TypeError-probing construction** (`main.py:627-640`,
   `run_opencode_campaign.py:129-135`): both call sites try `cls()` first
   and fall back to `cls(client=..., config=...)` on `TypeError`. A
   `TypeError` raised INSIDE a constructor body (a real bug) is silently
   misread as "needs kwargs", producing a confusing second failure or a
   differently-configured instance. The correct contract is signature
   inspection.
2. **`--pair-turns` silently ignored**: `PairTransform.__init__(self,
   max_turns: int = 3)` (`pair_transform.py:96`) — the zero-arg `cls()`
   succeeds, the kwargs fallback never fires, and the CLI flag never
   reaches the transform.
3. **`SemanticRouter.rerank` crashes on score ties** (`router.py:60`):
   `sorted(((self._score(p, q), p) for p in ...), reverse=True)` compares
   the second tuple element (`TechniqueProfile`, no `__lt__`) whenever
   scores tie. `rank` (line 53) already pairs with `p.id` strings and is
   safe — `rerank` should do the same.

## Current state

Excerpt (`main.py:627-640`, abridged):

```python
            for tid in requested:
                cls = registry.get(tid)
                try:
                    transforms.append(cls())
                except TypeError:
                    try:
                        transforms.append(cls(client=llm_client, config=engine_ctx_config))
                    except Exception as e:
                        print(f"[!] Skipping {tid}: {e}")
```

(Read the full block — there is a per-id try around `registry.get` as
well; preserve it.)

Excerpt (`modules/engine/router.py:57-64`):

```python
    def rerank(self, query: str, profiles: Sequence[TechniqueProfile]) -> list[TechniqueProfile]:
        """Order profiles by heuristic score, best first."""
        scored = ((self._score(p, query), p) for p in profiles)
        return [p for _, p in sorted(scored, reverse=True)]
```

Excerpt (`modules/engine/transforms/adaptive/pair_transform.py:94-97`):

```python
    def __init__(self, max_turns: int = 3) -> None:
        super().__init__()
        self.max_turns = max(1, int(max_turns))
```

## Repo conventions to match

- `registry.py` raises `ValueError` with a short message on contract
  violations — match that tone.
- Pure helpers live near their primary consumer; `construct_transform`
  belongs in `registry.py` (it is the construction authority).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Lint | `uv run ruff check .` | exit 0 |
| Tests | `uv run pytest -q` | all pass |
| New tests | `uv run pytest tests/test_router.py tests/test_transform_construction.py -q` | all pass |

## Scope

**In scope**:
- `modules/engine/registry.py` — new `construct_transform(cls, **available)` helper.
- `main.py` + `scripts/run_opencode_campaign.py` — use the helper at their construction blocks; thread `pair_turns` in main.py.
- `modules/engine/router.py` — tie-safe `rerank`.
- `modules/engine/transforms/adaptive/pair_transform.py` — accept `intensity`/`config`-style kwargs via the helper only (no signature change needed if the helper filters; verify).
- `tests/test_transform_construction.py` (create), `tests/test_router.py` (extend).

**Out of scope**:
- `Transform` base class changes.
- Which kwargs each transform accepts (that is per-transform design).
- Plan 050's deletions (`get_transform` etc.) — separate sweep.

## Git workflow

- Branch: `advisor/047-construction-contract`
- Commit message: `fix: signature-based transform construction, honor --pair-turns, tie-safe rerank`
- Do NOT push unless instructed.

## Steps

### Step 1: `construct_transform` in registry.py

```python
def construct_transform(cls: type, **available: object) -> object:
    """Build a transform, passing only the kwargs its __init__ accepts.

    Zero-arg-constructible transforms ignore `available` entirely; the rest
    get the intersection of their signature and `available`. A TypeError
    from the constructor body now propagates (it is a bug, not a signal).
    """
    try:
        return cls()
    except TypeError as exc:
        # Distinguish "wrong args" from "bug inside __init__" via signature.
        import inspect

        params = inspect.signature(cls.__init__).parameters
        accepts_any = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
        if accepts_any or len(params) <= 1:  # only self -> genuine body bug
            raise
    import inspect

    params = inspect.signature(cls.__init__).parameters
    kwargs = {k: v for k, v in available.items() if k in params or any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()
    )}
    return cls(**kwargs)
```

(Single `import inspect` at module top, not inline — clean this up; the
draft shows the logic, you write the tidy version. Keep the
"zero-arg + body-TypeError propagates" semantics exactly.)

**Verify**: `uv run python -c "from modules.engine.registry import construct_transform; print('ok')"` → `ok`.

### Step 2: Use it at both call sites

- `main.py:627-640`: replace the try/TypeError ladder with
  `transforms.append(construct_transform(cls, client=llm_client, config=engine_ctx_config))`
  inside the existing per-id error handling.
- `run_opencode_campaign.py:129-135`: same, with
  `client=None, config=config` (match what the script currently passes —
  read it first).
- `main.py`: thread `--pair-turns`: add
  `pair_turns=args.pair_turns` to the `available` kwargs for ALL
  transforms (helper filters it out for everyone else) — verify the flag
  exists (`grep -n "pair-turns" main.py`); if it doesn't exist yet, add it
  beside `--pair-model`.

**Verify**: `uv run python main.py --list-transforms` → exit 0.

### Step 3: Tie-safe rerank

```python
        scored = ((self._score(p, query), p.id, p) for p in profiles)
        return [p for _, _, p in sorted(scored, key=lambda t: (-t[0], t[1]))]
```

**Verify**: `uv run pytest tests/test_router.py -q` → green.

### Step 4: Tests

Create `tests/test_transform_construction.py`:

```python
"""construct_transform: signature filtering + body-TypeError propagation."""
import pytest

from modules.engine.registry import construct_transform


class Zero:
    def __init__(self):
        self.seen = {}


class Needs:
    def __init__(self, client=None, config=None):
        self.seen = {"client": client, "config": config}


class Buggy:
    def __init__(self):
        raise TypeError("bug inside body")


def test_zero_arg_ignores_available():
    t = construct_transform(Zero, client="c", config={})
    assert t.seen == {}


def test_kwargs_filtered_by_signature():
    t = construct_transform(Needs, client="c", config={"a": 1}, pair_turns=4)
    assert t.seen == {"client": "c", "config": {"a": 1}}


def test_body_typeerror_propagates():
    with pytest.raises(TypeError, match="bug inside body"):
        construct_transform(Buggy, client="c")
```

Extend `tests/test_router.py` with a tie case (two profiles, same score —
assert no exception and deterministic id order).

**Verify**: new tests green; full suite green.

## Done criteria

ALL must hold:

- [ ] `grep -n "except TypeError" main.py scripts/run_opencode_campaign.py` → no construction-ladder matches remain
- [ ] `grep -n "construct_transform" main.py scripts/run_opencode_campaign.py modules/engine/registry.py` → matches
- [ ] `grep -n "pair_turns" main.py` → flag threaded into construction
- [ ] rerank tie test passes; `uv run pytest -q` → all green
- [ ] `uv run ruff check .` → exit 0
- [ ] No files outside the in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:
- A transform's `__init__` requires kwargs the helper can't supply and
  previously worked via the TypeError ladder (audit the 20 registered ids —
  `--list-transforms` — before declaring success).
- `registry.get` signature changed.
- `pair_transform` already accepts the kwargs (then Step 2 is a no-op — note it).

## Maintenance notes

- New transforms should either be zero-arg or declare exactly the kwargs
  they need; `construct_transform` makes both styles work without ladders.
- `rerank` remains unused in production paths (see plan 050) — this fix
  keeps it correct should the router get wired.
