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
from modules.engine.registry import register_transform


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

        return TransformResult(
            output=chosen,
            bypassed=False,
            metrics={
                "n_samples": len(candidates),
                "requested_samples": n,
                "diversity_temp": temp,
                "chosen_index": idx,
                "scores": scores,
            },
            artifacts=list(candidates),
        )
