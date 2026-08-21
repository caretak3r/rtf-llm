from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TransformContext:
    input: str
    target: Any = None
    attacker: Any | None = None
    config: dict = field(default_factory=dict)
    state: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TransformResult:
    output: str
    bypassed: bool = False
    refusal_detected: bool = False
    metrics: dict = field(default_factory=dict)
    artifacts: list = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class PipelineResult:
    results: list[TransformResult]
    context: TransformContext
    total_time_ms: float = 0
    any_bypassed: bool = False


class Transform(ABC):
    @property
    @abstractmethod
    def id(self) -> str: ...

    @abstractmethod
    def transform(self, ctx: TransformContext) -> TransformResult: ...

