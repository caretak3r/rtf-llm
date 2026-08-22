"""Best-of-N sampling transform.

Samples N candidate responses for a prompt (diversity via temperature) and
returns the best candidate by scoring. Reference pattern: Best-of-N sampling
boosts attack success (e.g. ASR ~89% at N=10k for a fixed woven prefix).
Scoring is pluggable; default is a deterministic response-length scorer so the
transform stays offline-testable. Swap in an LLM judge via ctx.config
(engine.best_of_n.scorer) when running live.
"""

from __future__ import annotations

from collections.abc import Callable
from modules.engine.base import Transform, TransformContext, TransformResult
from modules.engine.backends.stream_handler import DEFAULT_REFUSAL_KEYWORDS
from modules.engine.registry import register_transform

_REFUSAL_KEYWORDS = tuple(k.lower() for k in DEFAULT_REFUSAL_KEYWORDS)


def _refusal_detected(ctx: TransformContext, response: str) -> bool:
    """Plan 050 minimal wiring, mirroring adaptive/pair's detector fallback
    chain: LLM goal judge when configured (engine.judge == "llm"), keyword
    fallback otherwise."""
    if (ctx.config or {}).get("engine", {}).get("judge") == "llm" and ctx.target is not None:
        from modules.engine.eval.llm_judge import LLMGoalJudge

        return LLMGoalJudge(ctx.target, goal=ctx.input or "").classify(response)[0]
    lowered = (response or "").lower()
    return any(k in lowered for k in _REFUSAL_KEYWORDS)


def _default_scorer(response: str) -> float:
    """Deterministic offline scorer: longer responses score higher."""
    return float(len(response or ""))


@register_transform("adaptive/best_of_n")
class BestOfN(Transform):
    id = "adaptive/best_of_n"

    def __init__(self, n_samples: int = 5, diversity_temp: float = 0.9):
        self.n_samples = n_samples
        self.diversity_temp = diversity_temp

    def _params(self, ctx: TransformContext) -> tuple[int, float, Callable[[str], float]]:
        cfg = (ctx.config or {}).get("engine", {}).get("best_of_n", {})
        return (
            int(cfg.get("n_samples", self.n_samples)),
            float(cfg.get("diversity_temp", self.diversity_temp)),
            cfg.get("scorer", _default_scorer),
        )

    def transform(self, ctx: TransformContext) -> TransformResult:
        n, temp, scorer = self._params(ctx)
        goal = ctx.input or ""
        target = ctx.target

        # Pre-seeded candidates allow offline/deterministic runs and testing.
        candidates = [str(c) for c in (ctx.state or {}).get("candidates", [])]

        live = (ctx.config or {}).get("engine", {}).get("live", False)
        if target is not None and live:
            for _ in range(len(candidates), n):
                kwargs = {"temperature": temp}
                if hasattr(target, "generate"):
                    candidates.append(str(target.generate(goal, **kwargs)))
                else:
                    break

        if not candidates:
            return TransformResult(
                output=goal,
                bypassed=False,
                error="No candidates available (offline run without --engine live or seed state)",
                metrics={"n_samples": n, "chosen_index": None, "scores": []},
            )

        scores = [scorer(c) for c in candidates]
        idx = max(range(len(scores)), key=lambda i: scores[i])
        chosen = candidates[idx]
        refusal_detected = _refusal_detected(ctx, chosen)
        return TransformResult(
            output=chosen,
            bypassed=not refusal_detected,
            refusal_detected=refusal_detected,
            metrics={
                "n_samples": len(candidates),
                "requested_samples": n,
                "diversity_temp": temp,
                "chosen_index": idx,
                "scores": scores,
            },
            artifacts=list(candidates),
        )
