# Plan 042: Wire `engine.live` via CLI + expose zhipu/droid/glm providers (T10/T11)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat a6a9a9d..HEAD -- main.py config.json modules/llm_client.py`
> If these changed since this plan was written, compare excerpts before proceeding.

## Status

- **Priority**: P0
- **Effort**: S
- **Risk**: MEDIUM (turns previously-inert engine transforms live — that is the point; gates below keep it explicit)
- **Depends on**: none (land before 045/046/047 if those are in flight — shared `main.py` region)
- **Category**: wiring / ARCHITECTURE_REVIEW T10+T11
- **Planned at**: commit `a6a9a9d`, 2026-08-21

## Why this matters

The engine's live-firing gate reads `config["engine"]["live"]`
(e.g. `modules/engine/transforms/legacy/legacy_bridge.py:107-112`,
`transforms/adaptive/pair_transform.py:101-107`,
`transforms/jailbreak/classic.py:64`). `main.py`'s engine block builds
`engine_ctx_config` but only ever sets `best_of_n` (lines 653-658) — it
never sets `"live": True`, and `config.json` has no `engine` key. Result:
`--engine` runs 11 of 20 registered transforms (9 legacy bridges, PAIR,
best-of-N live sampling, classic live-fire) in inert error mode
(`"requires a live target (engine.live=true)"`) even against a configured
target. The only live engine path today is
`scripts/run_opencode_campaign.py`, which hand-builds
`{"engine": {"live": True}}` (lines 154-160).

Separately, `modules/llm_client.py` already supports `zhipu`, `glm`,
`bedrock` (OpenAI-compatible list) and `droid` (CLI provider), but
`main.py --provider` choices end at `any` and `config.json` `providers`
has no entries — ARCHITECTURE_REVIEW T10/T11, never done.

## Current state

Excerpt (`main.py:652-658`):

```python
            pipeline = Pipeline(transforms)
            engine_ctx_config = dict(config)
            engine_ctx_config.setdefault("engine", {})
            engine_ctx_config["engine"]["best_of_n"] = {
                "n_samples": args.n_samples,
                "diversity_temp": args.diversity_temp,
            }
```

Excerpt (`modules/engine/transforms/legacy/legacy_bridge.py:106-113`):

```python
        def transform(self, ctx: TransformContext) -> TransformResult:
            live = (ctx.config or {}).get("engine", {}).get("live", False)
            if ctx.target is None or not live:
                return TransformResult(
                    output="",
                    bypassed=False,
                    error=f"{tid} requires a live target (engine.live=true)",
                )
```

Excerpt (`scripts/run_opencode_campaign.py:154-160`) — the working pattern:

```python
    config = {
        "engine": {
            "live": True,
            "judge": args.judge,
            "best_of_n": {"n_samples": args.n_samples, "diversity_temp": 0.9},
        }
    }
```

## Repo conventions to match

- CLI flags: `parser.add_argument("--flag", ...)` groups in `main()` —
  follow the existing `--engine` flag block's help-string style.
- Config defaults live in `modules/config_manager.py` `DEFAULT_CONFIG` —
  add the `engine` default there too, mirroring how other sections default.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Lint | `uv run ruff check main.py modules/config_manager.py` | exit 0 |
| Tests | `uv run pytest -q` | all pass |
| New tests | `uv run pytest tests/test_engine_cli_config.py -q` | all pass |
| Smoke | `uv run python main.py --list-transforms` | prints registered transforms |

## Scope

**In scope**:
- `main.py` — engine-config construction (extract a pure helper) + `--provider` choices + new `--engine-offline` flag.
- `modules/config_manager.py` — `engine` default section.
- `config.json` — `engine` key + `zhipu`/`droid`/`glm` provider entries.
- `tests/test_engine_cli_config.py` (create).

**Out of scope**:
- `modules/llm_client.py` — providers already supported there; do not refactor it.
- Any transform or the pipeline itself.
- Plan 045's checkpoint region (adjacent lines — coordinate, land sequentially).

## Git workflow

- Branch: `advisor/042-engine-live-wiring`
- Commit message: `feat: wire engine.live through CLI + expose zhipu/droid/glm providers`
- Do NOT push unless instructed.

## Steps

### Step 1: Pure helper for engine context config

In `main.py`, add a module-level function (above `main()`):

```python
def build_engine_config(config: dict, live: bool, n_samples: int, diversity_temp: float) -> dict:
    """Engine-view of the run config: explicit live gate + best_of_n params."""
    engine_cfg = dict((config or {}).get("engine") or {})
    engine_cfg["live"] = bool(live)
    engine_cfg["best_of_n"] = {"n_samples": n_samples, "diversity_temp": diversity_temp}
    merged = dict(config or {})
    merged["engine"] = engine_cfg
    return merged
```

Replace lines 652-658's config construction with:

```python
            engine_ctx_config = build_engine_config(
                config,
                live=not args.engine_offline,
                n_samples=args.n_samples,
                diversity_temp=args.diversity_temp,
            )
```

Add the flag next to `--engine` in the parser:

```python
    parser.add_argument(
        "--engine-offline",
        action="store_true",
        help="Engine mode without live firing (static prompt construction only)",
    )
```

**Verify**: `uv run python main.py --list-transforms` → exit 0.

### Step 2: Provider choices + config entries

In `main.py`, find the `--provider` argument's `choices=[...]` list; append
`"zhipu"`, `"glm"`, `"droid"`, `"bedrock"` (verify each exists in
`modules/llm_client.py` `OPENAI_COMPATIBLE_PROVIDERS` / `CLI_PROVIDERS`
first — read those constants; if a name differs there, use THAT name).

In `config.json` `providers` add entries mirroring the existing provider
shape (copy the `openai` entry; set `default_model`/`base_url` per
`PROVIDER_ENDPOINTS` in `llm_client.py`; `api_key: null`).

In `modules/config_manager.py` `DEFAULT_CONFIG`, add:

```python
            "engine": {"live": False},
```

**Verify**: `uv run python -c "from modules.config_manager import ConfigManager; c=ConfigManager(); print(c.config['engine'])"` → `{'live': False}`.

### Step 3: Tests

Create `tests/test_engine_cli_config.py`:

```python
"""build_engine_config: explicit live gate + best_of_n passthrough."""
from main import build_engine_config


def test_live_defaults_off_and_params_set():
    cfg = build_engine_config({"llm": {"provider": "openai"}}, live=False, n_samples=5, diversity_temp=0.9)
    assert cfg["engine"]["live"] is False
    assert cfg["engine"]["best_of_n"] == {"n_samples": 5, "diversity_temp": 0.9}
    assert cfg["llm"]["provider"] == "openai"  # passthrough preserved


def test_live_true_overrides_config_default():
    cfg = build_engine_config({"engine": {"live": False}}, live=True, n_samples=1, diversity_temp=0.0)
    assert cfg["engine"]["live"] is True
```

**Verify**: `uv run pytest tests/test_engine_cli_config.py -q` → all pass.

## Done criteria

ALL must hold:

- [ ] `grep -n "engine_offline" main.py` → ≥2 matches (flag + use)
- [ ] `grep -n '"live"' main.py` → present in `build_engine_config`
- [ ] `uv run python main.py --help` lists `zhipu`, `glm`, `droid`, `bedrock` in provider choices
- [ ] `uv run pytest -q` → all pass
- [ ] `uv run ruff check .` → exit 0
- [ ] No files outside the in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:
- `main.py` engine block has drifted (e.g. plan 040/045 already rewrote it) — reconcile with the new shape instead of force-applying.
- A provider name in `llm_client.py` does not match the four listed here — use the real names, note the diff.
- `config.json` has uncommitted operator edits (real keys) — do not print or commit them; add only the new keys.

## Maintenance notes

- After this lands, `--engine` against a configured target fires legacy
  bridges for real. Reviewers should confirm the `--engine-offline` escape
  hatch and the `seeds`/`force` gates (main.py:672-682) still bound cost.
- Plan 048 (architecture memo) decides the long-term role of the bridge
  path; this plan only makes the existing contract reachable.
- `config.json` `engine.live` default stays False; the CLI flag is the
  operator's explicit opt-in per run.
