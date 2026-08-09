#!/usr/bin/env python3
"""Tests for the Best-of-N sampler transform."""

from modules.engine.base import TransformContext
from modules.engine.transforms.adaptive.best_of_n import BestOfN


def test_selects_best_candidate_by_default_scorer():
    t = BestOfN()
    ctx = TransformContext(input="goal", state={"candidates": ["short", "much longer candidate"]})
    res = t.transform(ctx)
    assert res.output == "much longer candidate"
    assert res.metrics["chosen_index"] == 1
    assert res.metrics["n_samples"] == 2
    assert not res.metrics["scores"][0] > res.metrics["scores"][1]


def test_no_candidates_returns_error():
    t = BestOfN()
    res = t.transform(TransformContext(input="goal"))
    assert res.error is not None


def test_config_overrides_samples_and_scorer():
    t = BestOfN()
    cfg = {
        "engine": {
            "best_of_n": {
                "n_samples": int(3),
                "scorer": lambda s: 1.0 if "x" in s else 0.0,
            }
        }
    }
    ctx = TransformContext(
        input="goal",
        config=cfg,
        state={"candidates": ["no", "has x here"]},
    )
    res = t.transform(ctx)
    assert res.output == "has x here"
    assert res.metrics["n_samples"] == 2


def test_live_target_generates_missing_candidates():
    class Target:
        def __init__(self):
            self.calls = []

        def generate(self, prompt, **kwargs):
            self.calls.append((prompt, kwargs))
            return f"candidate-{len(self.calls)}"

    target = Target()
    t = BestOfN(n_samples=3)
    cfg = {"engine": {"live": True, "best_of_n": {"n_samples": 3, "diversity_temp": 0.7}}}
    res = t.transform(TransformContext(input="goal", target=target, config=cfg))
    assert len(target.calls) == 3
    assert res.metrics["n_samples"] == 3
    assert target.calls[0][1]["temperature"] == 0.7
