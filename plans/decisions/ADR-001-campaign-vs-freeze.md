# ADR-001: Campaign-as-product vs freeze-the-engine

- **Status**: DECISION: <pending maintainer>
- **Date**: 2026-08-21
- **Planned against**: commit `a6a9a9d` (per `plans/048-architecture-decision-memo.md:17`)
- **Drift check**: skipped — executor ran under a no-git constraint; every claim below was re-verified on disk at execution time instead.
- **Gates**: plan [050](../050-dead-surface-sweep.md) wire-or-delete choices; any further investment in legacy-side plans ([016](../016-intensity-gating-all-modules.md), [033–039](../033-delete-or-wire-vendored-attack-py.md)) — see `plans/README.md:241-242`.

## 1. Context

The repo carries two parallel attack stacks and pays for both.

**Legacy stack (default path).** `main.py` unconditionally imports 18 frozen
attack modules at startup (`main.py:18-35`) plus three core infrastructure
imports (`main.py:36-38`). Dispatch is a flat chain of 18 `if args.module ==`
branches (`main.py:783-989`, counted). The legacy surface measured 11,263 LOC
(`wc -l main.py modules/*.py`) and is explicitly lint-frozen:
`[tool.ruff] extend-exclude` in `pyproject.toml` names each frozen module file,
with the comment "frozen/deprecated; lint-ownership tracked only on the
maintained surface".

**Engine stack (`modules/engine/`, 3,057 LOC**, `find modules/engine -name '*.py' | xargs wc -l`**)**.
Cleaner and tested, but reachable from the CLI only through opt-in flags:
`--engine` (`main.py:148-150`), checkpoint path (`main.py:179`), sweep mode
(`main.py:185`), provenance DB path (`main.py:213`). Nearly half its transform
registry is not native: 12 transforms register directly plus 9 legacy bridges
registered by a loop (`legacy_bridge.py:138` over `LEGACY_TARGETS`,
`legacy_bridge.py:18-28`) — 9 of 21 registry ids reach back INTO the frozen
modules through a client-shaped `_Facade` (`legacy_bridge.py:43`). The
reach-in is literal in one place: `modules/engine/transforms/jailbreak/classic.py:37-41`
constructs `modules.jailbreak.JailbreakModule` via `__new__`, bypassing
`__init__`, and reads only the first pattern of each category
(`classic.py:55`, `catalog[category][0]`).

**Two knowledge bases.** `modules/engine/kb/atlas.py` (306 lines) is curated
and self-validating — `validate_kb()` rejects uncited entries and ATLAS IDs
outside a verified whitelist (`atlas.py:16-30`). `modules/technique_kb.py`
(1,199 lines) is frozen, feeds dashboards, and carries a known
fabricated-citation debt documented in run 3 (`plans/README.md:53-54`, fix
planned as 030). The two can disagree about the same technique. Worse, the
engine's own HTML reports render through the legacy generator, which imports
the frozen KB: `modules/report_generator.py:791`
(`from .technique_kb import TECHNIQUE_INFO`).

**Two judges.** Legacy keyword+LLM scoring lives in `modules/judge_evaluator.py:17`
(`class JudgeEvaluator`); the engine has its own `class LLMGoalJudge` at
`modules/engine/eval/llm_judge.py:45`.

**Usage reality.** `rtf.db` contains exactly two tables, `checkpoints` and
`findings`; both hold **0 rows** (`SELECT COUNT(*)` run read-only at execution
time). Note: the plan's suggested probe `SELECT COUNT(*) FROM runs` fails —
no `runs` table exists; this matches `plans/README.md:175-177` ("runs/findings
tables have 0 rows ever — CLI engine mode never completed a recorded run").
The only engine-native consumer that has seen real work is
`scripts/run_opencode_campaign.py`, which builds the pipeline from the engine
registry, the atlas KB, and `OpencodeTarget`
(`scripts/run_opencode_campaign.py:119-125`) and sets `engine.live: true`
(`scripts/run_opencode_campaign.py:154-160`). Recent work (rescore passes,
`opencode_campaign/` transcripts) happened there, not in CLI engine mode.

**Orphaned engine surface.** `modules/engine/backends/stream_handler.py`
(160 lines) and `mitm_proxy.py` (137 lines) have zero production callers —
grep finds references only in `tests/test_mitm.py:10`. `HeartbeatStream`
lives in `backends/gates.py:79` (not `llm_client.py` as the plan guessed) and
is likewise exercised only by `tests/test_session_gates.py:82`. That is ~300
LOC of tested-but-unwired code awaiting the plan-050 wire-or-delete call.

**Cost of the status quo.** Every change pays twice: new techniques must land
in both stacks or accept divergence; the dual KBs already carry contradictory
citation quality; the engine's reports silently render legacy-KB content;
and the provenance tables record nothing, so neither stack can prove what it
did. The prior review framed the destination correctly
(`ARCHITECTURE_REVIEW.md:5`: "monolithic dispatcher… no plugin system… no
checkpointing") and its T1–T11 roadmap (`ARCHITECTURE_REVIEW.md:195-290`)
is now substantially built — but bolted next to the old stack instead of
replacing it.

## 2. Option A — Campaign-as-product (RECOMMENDED)

Promote the campaign runner to the primary interface. The engine becomes the
only attack surface; frozen modules survive only as data catalogs behind the
bridges until they too are unwound.

**Migration sequence:**

1. **Wire the entry point.** Add a `campaign` subcommand to `main.py` (or a
   console script per plan 053's packaging work) that calls
   `scripts/run_opencode_campaign.py`'s existing logic. Nothing else changes.
   *Deletes:* nothing yet; deprecates direct `--engine` flag usage in docs.
2. **Land 040 + 042 first.** Report-integrity (shuffle misattribution) and
   live-mode CLI wiring are prerequisites for trustworthy campaigns
   (`plans/README.md:233-234`). *Deletes:* nothing; fixes the runner.
3. **Untangle the frozen-fiction imports.** Replace the `__new__` reach-in in
   `classic.py:37-41` with a data-level import of the pattern catalog, then
   fix the first-pattern-only limitation (`classic.py:55`). After this step
   the engine reads legacy content without instantiating legacy classes.
   *Deletes:* `_Facade`'s duck-typing surface shrinks accordingly.
4. **Consolidate the KBs.** Atlas becomes the single KB:
   `report_generator.py:791` switches from `technique_kb` to
   `engine/kb/atlas.py`; `technique_kb.py` is demoted to a reference doc (or
   deleted once plan 030's citation fixes are moot). This also resolves plan
   032's fallback/collision work at the root. *Deletes:* dashboard's frozen-KB
   import path.
5. **Retire the legacy dispatch on a schedule.** Remove the 18-branch chain
   (`main.py:783-989`) and `AttackEvaluator`/`JudgeEvaluator` once each
   bridged technique has an engine-native equivalent; delete the orphaned
   backends per plan 050's sweep. *Deletes:* up to ~11k LOC of frozen modules
   as bridges are replaced by native transforms.

**Effect on existing plans:** obsoletes the legacy-side investments in 033–039
(wire vendored templates into legacy catalogs is wasted work if the dispatch
chain dies) and re-scopes 016 (intensity gating matters only where the chain
survives during transition). Re-affirms 040–047 and 051–053, which fix defects
present in both futures.

## 3. Option B — Freeze-the-engine

Declare the engine an experiment. Keep legacy as product; archive
`modules/engine/` and its tests into an `attic/` branch or directory.

**What this costs, concretely:**

- **The tested pipeline**: transform protocol, registry, best-of-N, adaptive
  PAIR-style transforms, error-isolated pipeline (`ARCHITECTURE_REVIEW.md:195-256`
  roadmap items T1/T2/T8/T9) — all built and unit-tested within the last cycle.
- **Checkpoint/resume**: `backends/checkpoint.py` and the `checkpoints` table
  (plan 045's subject) die with the stack; long campaign runs lose resumability.
- **Provenance**: `backends/provenance_db.py` and the `findings` table — the
  only mechanism that could make runs auditable.
- **The campaign runner**: `run_opencode_campaign.py` is engine-native
  (`run_opencode_campaign.py:119-160`) and would be archived with it, along
  with the recent rescore work in `opencode_campaign/`.
- **The curated KB**: `atlas.py`'s validated citations (`atlas.py:16-30`) are
  engine-side; legacy keeps the citation-debt KB instead (plans/README.md:53-54).

**Plans that die:** 042, 043, 045, 046, 047, 048's follow-through, most of
050 (nothing left to wire), and the engine portions of 044 and 049 — roughly
eight of the fourteen run-4 plans.

## 4. Decision

DECISION: <pending maintainer>

**Recommendation: Option A.** The engine is where every correctness fix of
run 4 lands (040–047); the campaign runner is where the actual recent usage
happened; and Option A deletes code on a schedule while Option B deletes the
future. The legacy stack's own documentation calls it frozen and deprecated
(`pyproject.toml` ruff exclude comment), yet it remains the default path —
that contradiction resolves more cheaply toward the maintained stack.

**Strongest counter-arguments, honestly stated:**

1. **Technique breadth is not bridged.** Legacy holds multimodal injection
   (`main.py:893-897`), C2/persistence/exfil lab modules (`main.py:900-983`),
   and defense-tester classifier wiring (`main.py:848-853` imports engine
   classifiers from the *legacy* branch) — none have engine-native
   equivalents today. Retiring the chain before bridging loses coverage.
2. **The campaign runner is opencode-specific.** Its target is hardwired to
   `OpencodeTarget` (`run_opencode_campaign.py:153`); legacy supports many
   providers via `config.json`. Option A needs a backend-general target
   protocol before it can replace CLI usage.
3. **Engine live-mode is not yet reachable.** `engine.live` is unreachable
   via CLI until plan 042 lands (`plans/README.md:70-72`) — meaning most of
   the engine currently fires inert outside the campaign runner. Recommending
   A today is recommending a bet that 042+043 make the engine measurably real;
   revisit after they land (see memo maintenance notes, `048-architecture-decision-memo.md:142-147`).

## 5. Consequences (for Option A)

**Untangling order for the frozen-fiction imports:**

1. `classic.py` reach-in first (`classic.py:37-41`, then the
   `catalog[category][0]` first-pattern limit at `classic.py:55`) — smallest
   blast radius, removes the only `__new__` bypass.
2. `report_generator.py:791` KB swap second — one-line import change plus
   key reconciliation between the two KB shapes; flips dashboards onto
   validated citations and lets `technique_kb` freeze into a reference doc.

Everything else (dispatch retirement, judge consolidation onto `LLMGoalJudge`,
backend wire-or-delete in 050) follows only after these two, so the engine
never again executes legacy *code* — it reads legacy *data* until native
transforms replace each bridge.

**Do not do meanwhile:**

- No new legacy-side features: no new modules wired into the
  `main.py:783-989` chain, no new `technique_kb` entries (fix citations in
  place per 030 if ever needed for reference).
- No new dual-stack APIs: anything touching judging, reporting, or targets
  gets designed against the engine interfaces only.
- No investment in plans 033–039's legacy wiring options until this ADR is
  decided; their delete branches remain valid under either outcome.
