from __future__ import annotations

import time
from typing import Sequence

from modules.engine.base import (
    PipelineResult,
    Transform,
    TransformContext,
    TransformResult,
)


class Pipeline:
    def __init__(self, transforms: Sequence[Transform]) -> None:
        self._transforms = list(transforms)

    def run(self, ctx: TransformContext, early_stop: bool = True) -> PipelineResult:
        results: list[TransformResult] = []
        start = time.monotonic()

        for t in self._transforms:
            result = t.transform(ctx)
            results.append(result)
            if early_stop and result.bypassed:
                break

        elapsed = (time.monotonic() - start) * 1000
        return PipelineResult(
            results=results,
            context=ctx,
            total_time_ms=elapsed,
            any_bypassed=any(r.bypassed for r in results),
        )

    async def arun(self, ctx: TransformContext, early_stop: bool = True) -> PipelineResult:
        results: list[TransformResult] = []
        start = time.monotonic()

        for t in self._transforms:
            result = await t.atransform(ctx)
            results.append(result)
            if early_stop and result.bypassed:
                break

        elapsed = (time.monotonic() - start) * 1000
        return PipelineResult(
            results=results,
            context=ctx,
            total_time_ms=elapsed,
            any_bypassed=any(r.bypassed for r in results),
        )

    @property
    def transforms(self) -> list[Transform]:
        return list(self._transforms)
