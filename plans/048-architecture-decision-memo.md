# Plan 048: Architecture decision memo — campaign-as-product vs freeze-the-engine

> **Executor instructions**: This is a WRITING plan — the deliverable is a
> decision memo, not code. Research everything from the repo itself. Do not
> modify source. Write exactly one new file and update the index. When done,
> update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git rev-parse --short HEAD` — note it in the memo header.

## Status

- **Priority**: P1 (gates the big refactors; the S-fixes 040-047 proceed regardless)
- **Effort**: M (reading + writing)
- **Risk**: NONE (no code)
- **Depends on**: none; SHOULD be read before executing 050's wire-or-delete choices and before any legacy-side plan (016, 033-039)
- **Category**: direction / architecture
- **Planned at**: commit `a6a9a9d`, 2026-08-21

## Why this matters

The repo carries two parallel attack stacks and pays for both:

- **Legacy stack** (default): `main.py:18-35` imports all 20 frozen
  modules unconditionally; dispatch is an 18-branch `if args.module ==`
  chain (`main.py:783-986`). ~7.7k LOC, ruff-exempt, lint-frozen.
- **Engine stack** (`modules/engine/`, ~3.1k LOC): clean, tested, behind
  opt-in flags. Its bridges (`transforms/legacy/legacy_bridge.py`,
  9 of 20 registry ids) reach back INTO the frozen modules — including a
  `__new__` reach-in (`transforms/jailbreak/classic.py:37-41` constructs
  `modules.jailbreak.JailbreakModule` via `__new__`, bypassing `__init__`)
  and engine reports rendering through legacy `report_generator.py:791`
  importing frozen `technique_kb`.
- **Two knowledge bases**: `kb/atlas.py` (306 lines, tested, curated) vs
  `technique_kb.py` (1,199 lines, frozen, feeds dashboards). They can
  disagree about the same technique.
- **Two judges**: `JudgeEvaluator` (legacy) vs `LLMGoalJudge` (engine).
- **Usage reality**: `rtf.db` provenance tables have 0 rows ever — CLI
  engine mode has never completed a recorded run. The only engine-native
  consumer is `scripts/run_opencode_campaign.py`, which is where actual
  recent work happened (`opencode_campaign/`, rescore passes).

Every future change pays a dual-stack tax until someone decides which
stack is the product. This memo makes that decision explicit, with a
migration sequence either way.

## Evidence inventory (verify each before citing — open the files)

| Fact | Where to verify |
|---|---|
| 20 unconditional frozen imports at CLI startup | `main.py:18-35`, `wc -l` the frozen files |
| 18-branch dispatch chain | `main.py:783-986` |
| 9/20 registry ids are legacy bridges | `modules/engine/registry.py` + `transforms/legacy/legacy_bridge.py` `_FACADES` |
| `__new__` reach-in into frozen jailbreak | `transforms/jailbreak/classic.py:37-55` (also note `catalog[category][0]` first-pattern-only) |
| Engine reports render via legacy generator | `modules/report_generator.py:791` imports `technique_kb` |
| Dual KBs | `modules/engine/kb/atlas.py` (306 lines) vs `modules/technique_kb.py` (1,199 lines) |
| Dual judges | `modules/judge_evaluator.py` vs `modules/engine/eval/llm_judge.py` |
| Zero provenance rows from CLI mode | `sqlite3 rtf.db 'SELECT COUNT(*) FROM findings;'` and `... FROM runs;` (read-only) |
| Campaign runner is engine-native | `scripts/run_opencode_campaign.py:129-160` |
| Orphaned backends (~500 LOC) | `stream_handler.py`, `mitm_proxy.py`, `HeartbeatStream` in `llm_client.py` — grep for callers |
| Prior review's scorecard | `ARCHITECTURE_REVIEW.md` (T1-T11) — which items remain open |

## Deliverable

Write `plans/decisions/ADR-001-campaign-vs-freeze.md` (create the
`plans/decisions/` directory) with EXACTLY this structure:

1. **Context** — one page: the dual-stack facts above (with file:line
   citations you verified), current usage reality, cost of the status quo.
2. **Option A — Campaign-as-product** (RECOMMENDED): promote
   `scripts/run_opencode_campaign.py` to the primary interface
   (`rtf-llm campaign ...` console entry or `main.py campaign`
   subcommand); engine becomes the only attack surface; frozen modules
   survive ONLY as data catalogs behind bridges; legacy dispatch chain,
   `AttackEvaluator`, `JudgeEvaluator` are retired on a schedule.
   Include: a 5-step migration sequence, what gets deleted at each step,
   which existing plans (016, 033-039) this obsoletes or re-scopes, and
   the dual-KB consolidation step (atlas becomes the single KB;
   `report_generator` imports atlas; technique_kb demoted to reference
   doc).
3. **Option B — Freeze-the-engine**: declare the engine an experiment,
   keep legacy as product, archive `modules/engine/` + its tests. Include
   what that costs (lose: tested pipeline, checkpoint, provenance,
   campaign runner) and which open plans die.
4. **Decision** — left as `DECISION: <pending maintainer>` with a
   recommendation paragraph for Option A and the three strongest
   counter-arguments against it (honest cons: e.g. legacy has multimodal/
   C2 technique breadth not yet bridged; campaign runner is
   opencode-specific today; engine live-mode only just became reachable
   per plan 042).
5. **Consequences** — for the recommended option: the untangling order for
   the frozen-fiction imports (classic.py reach-in first, report_generator
   KB swap second), and a "do not do meanwhile" list (no new legacy-side
   features).

## Repo conventions to match

- Docs live under `docs/` and `plans/`; this memo belongs in
  `plans/decisions/` because it gates plan execution (index links to it).
- Prose style: short declarative sentences, evidence-cited, no marketing
  tone — match `ARCHITECTURE_REVIEW.md`'s voice.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| LOC counts | `wc -l main.py modules/*.py \| sort -rn \| head` | facts for Context |
| Engine LOC | `find modules/engine -name '*.py' \| xargs wc -l \| tail -1` | fact |
| Provenance reality | `sqlite3 rtf.db 'SELECT COUNT(*) FROM runs;'` (READ-ONLY) | number |
| Bridge inventory | `grep -n "legacy/" modules/engine/registry.py` | list |

## Scope

**In scope**: `plans/decisions/ADR-001-campaign-vs-freeze.md` (create);
`plans/README.md` (add link + status row only).

**Out of scope**: ALL source files. No refactors "while you're in there."

## Git workflow

- Branch: `advisor/048-architecture-adr`
- Commit message: `docs: ADR-001 — campaign-as-product vs freeze-the-engine decision memo`
- Do NOT push unless instructed.

## Done criteria

ALL must hold:

- [ ] `plans/decisions/ADR-001-campaign-vs-freeze.md` exists with all 5 sections
- [ ] Every factual claim in Context carries a `file:line` you personally opened
- [ ] Both options state what the maintainer LOSES by choosing them
- [ ] `plans/README.md` links the memo and marks affected plans (016, 033-039, 050) as "pending ADR-001" where applicable
- [ ] No source files modified (`git status --short` shows only the two plan files)

## STOP conditions

Stop and report back if:
- The repo state has materially changed (e.g. legacy dispatch already
  retired) — rewrite Context from the new reality instead of forcing it.
- You cannot verify a load-bearing claim (mark it explicitly as unverified
  rather than dropping it in as fact).

## Maintenance notes

- Whichever option wins, the S-fix plans (040-047, 051-053) remain valid —
  they fix defects that exist in both futures.
- Revisit this memo after 042+043 land: live-mode reachability plus canary
  ground truth are the two facts most likely to firm up Option A.
