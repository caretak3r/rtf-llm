from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import AsyncIterator


class RefusalStrategy(Enum):
    SWALLOW = auto()
    COMMIT = auto()
    RETROACTIVE = auto()


class StopReason(Enum):
    COMPLETED = auto()
    REFUSAL_DETECTED = auto()
    UPSTREAM_ERROR = auto()
    CANCELLED = auto()


@dataclass(frozen=True)
class RefusalPattern:
    pattern: re.Pattern[str]
    min_window: int = 64

    @classmethod
    def from_keywords(cls, keywords: list[str]) -> list[RefusalPattern]:
        return [cls(re.compile(re.escape(k), re.IGNORECASE)) for k in keywords]


DEFAULT_REFUSAL_KEYWORDS = [
    "I can't help with",
    "I cannot help with",
    "I'm not able to assist",
    "I am not able to assist",
    "As an AI",
    "I cannot fulfill",
    "I can't fulfill",
    "I'm unable to",
    "I am unable to",
    "I won't help with",
    "I will not help with",
    "I cannot provide",
    "I can't provide",
    "我不能帮助你",
    "这样不好",
    "那不行",
    "抱歉，我无法",
    "我不能",
]


class RefusalAbortingStream:
    __slots__ = (
        "_source",
        "_patterns",
        "_strategy",
        "_max_buffer",
        "_buffer",
        "_stats",
        "_aborted",
        "_completed",
    )

    def __init__(
        self,
        source: AsyncIterator[str],
        patterns: list[RefusalPattern] | None = None,
        *,
        strategy: RefusalStrategy = RefusalStrategy.COMMIT,
        max_buffer: int = 8192,
    ) -> None:
        self._source = source
        self._patterns = patterns or RefusalPattern.from_keywords(DEFAULT_REFUSAL_KEYWORDS)
        self._strategy = strategy
        self._max_buffer = max_buffer
        self._buffer: str = ""
        self._stats = HandlerStats()
        self._aborted = False
        self._completed = False

    def __aiter__(self) -> AsyncIterator[str]:
        return self._run()

    @property
    def stats(self) -> HandlerStats:
        return self._stats

    @property
    def aborted(self) -> bool:
        return self._aborted

    async def aclose(self) -> None:
        if self._completed:
            return
        close = getattr(self._source, "aclose", None)
        if close is not None:
            await close()
        self._completed = True

    async def _run(self) -> AsyncIterator[str]:
        try:
            async for token in self._source:
                self._stats.tokens_seen += 1
                self._stats.chars_seen += len(token)
                self._buffer += token
                if len(self._buffer) > self._max_buffer:
                    self._buffer = self._buffer[-self._max_buffer :]

                hit = self._scan()
                if hit is not None:
                    await self._handle_refusal(hit)
                    return

                if self._strategy is RefusalStrategy.SWALLOW:
                    yield token
                else:
                    self._stats.tokens_emitted += 1
                    yield token

            self._stats.stop_reason = StopReason.COMPLETED
        except Exception:
            self._stats.stop_reason = StopReason.UPSTREAM_ERROR
            raise
        finally:
            await self.aclose()

    def _scan(self) -> RefusalPattern | None:
        for p in self._patterns:
            if len(self._buffer) < p.min_window:
                continue
            if p.pattern.search(self._buffer):
                self._stats.matched_pattern = p
                self._stats.matched_at_char = self._stats.chars_seen
                return p
        return None

    async def _handle_refusal(self, p: RefusalPattern) -> None:
        self._aborted = True
        self._stats.stop_reason = StopReason.REFUSAL_DETECTED
        if self._strategy is RefusalStrategy.RETROACTIVE:
            raise RefusalDetected(pattern=p.pattern.pattern, partial=self._buffer)


class RefusalDetected(Exception):
    def __init__(self, pattern: str, partial: str) -> None:
        self.pattern = pattern
        self.partial = partial
        super().__init__(f"refusal matched: {pattern!r}")


@dataclass
class HandlerStats:
    tokens_seen: int = 0
    chars_seen: int = 0
    tokens_emitted: int = 0
    stop_reason: StopReason | None = None
    matched_pattern: RefusalPattern | None = None
    matched_at_char: int | None = None
