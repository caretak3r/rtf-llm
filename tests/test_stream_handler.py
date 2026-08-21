"""RefusalAbortingStream strategy semantics, encoded from current code:

- Every token from the source increments tokens_seen, for every strategy.
- SWALLOW yields tokens but never counts them as emitted (tokens_emitted == 0).
- COMMIT yields and counts emitted tokens.
- On a refusal hit the stream stops for every strategy; the triggering token
  is never yielded. RETROACTIVE additionally raises RefusalDetected carrying
  the partial buffer; SWALLOW/COMMIT just end iteration with
  stop_reason=REFUSAL_DETECTED.
- Detection only scans once the buffer reaches each pattern's min_window, and
  the rolling buffer keeps at most max_buffer characters.

These tests are the safety net for plan 050's fix-or-delete decision.
"""

import asyncio
import re

from modules.engine.backends.stream_handler import (
    DEFAULT_REFUSAL_KEYWORDS,
    RefusalAbortingStream,
    RefusalDetected,
    RefusalPattern,
    RefusalStrategy,
    StopReason,
)

HIT = "I can't help with that"


def _pattern(min_window: int = 1) -> list[RefusalPattern]:
    return [RefusalPattern(re.compile(re.escape(HIT), re.IGNORECASE), min_window=min_window)]


def _source(tokens: list[str]):
    async def _gen():
        for token in tokens:
            yield token

    return _gen()


def _collect(tokens, strategy, patterns="default", max_buffer=8192):
    async def _run():
        stream = RefusalAbortingStream(
            _source(tokens),
            None if patterns == "default" else patterns,
            strategy=strategy,
            max_buffer=max_buffer,
        )
        out = []
        refusal = None
        try:
            async for token in stream:
                out.append(token)
        except RefusalDetected as exc:
            refusal = exc
        return out, stream, refusal

    return asyncio.run(_run())


# --- strategy semantics ------------------------------------------------------


def test_swallow_yields_but_does_not_count_emitted():
    out, stream, refusal = _collect(["hello ", "world"], RefusalStrategy.SWALLOW)
    assert out == ["hello ", "world"]
    assert stream.stats.tokens_seen == 2
    assert stream.stats.tokens_emitted == 0
    assert stream.stats.stop_reason is StopReason.COMPLETED
    assert not stream.aborted
    assert refusal is None


def test_commit_yields_and_counts():
    out, stream, refusal = _collect(["hello ", "world"], RefusalStrategy.COMMIT)
    assert out == ["hello ", "world"]
    assert stream.stats.tokens_seen == 2
    assert stream.stats.tokens_emitted == 2
    assert stream.stats.stop_reason is StopReason.COMPLETED
    assert refusal is None


def test_commit_stops_at_refusal_without_raising():
    out, stream, refusal = _collect(
        ["fine ", HIT, " never delivered"], RefusalStrategy.COMMIT, patterns=_pattern()
    )
    assert out == ["fine "]
    assert refusal is None
    assert stream.aborted
    assert stream.stats.stop_reason is StopReason.REFUSAL_DETECTED
    assert stream.stats.matched_pattern is not None
    assert stream.stats.matched_at_char == len("fine ") + len(HIT)
    assert stream.stats.tokens_seen == 2
    assert stream.stats.tokens_emitted == 1


def test_retroactive_raises_refusal_detected_with_partial():
    out, stream, refusal = _collect(
        ["fine ", HIT, " tail"], RefusalStrategy.RETROACTIVE, patterns=_pattern()
    )
    assert out == ["fine "]
    assert refusal is not None
    assert refusal.partial == "fine " + HIT
    assert refusal.pattern == re.escape(HIT)
    assert stream.aborted
    # Current-code quirk: the raised RefusalDetected passes through _run's
    # `except Exception`, which overwrites stop_reason to UPSTREAM_ERROR.
    assert stream.stats.stop_reason is StopReason.UPSTREAM_ERROR


# --- windowing ---------------------------------------------------------------


def test_min_window_blocks_detection_on_short_buffer():
    out, stream, refusal = _collect([HIT], RefusalStrategy.COMMIT, patterns=_pattern(min_window=100))
    assert out == [HIT]
    assert not stream.aborted
    assert stream.stats.stop_reason is StopReason.COMPLETED
    assert refusal is None


def test_max_buffer_trim_prevents_stale_matches():
    # HIT enters the buffer while it is still below min_window; by the time the
    # buffer exceeds min_window it has been trimmed down to trailing filler.
    out, stream, refusal = _collect(
        [HIT, "x" * 200], RefusalStrategy.COMMIT, patterns=_pattern(min_window=100), max_buffer=10
    )
    assert out == [HIT, "x" * 200]
    assert not stream.aborted
    assert stream.stats.stop_reason is StopReason.COMPLETED
    assert refusal is None


def test_default_patterns_detect_after_min_window():
    out, stream, refusal = _collect(
        ["x" * 70, " " + DEFAULT_REFUSAL_KEYWORDS[0]], RefusalStrategy.COMMIT
    )
    assert out == ["x" * 70]
    assert stream.aborted
    assert stream.stats.stop_reason is StopReason.REFUSAL_DETECTED
    assert refusal is None


# --- failure paths and helpers -----------------------------------------------


def test_upstream_error_marks_stop_reason():
    async def _boom():
        yield "ok"
        raise RuntimeError("boom")

    async def _run():
        stream = RefusalAbortingStream(_boom(), _pattern(), strategy=RefusalStrategy.COMMIT)
        out = []
        error = None
        try:
            async for token in stream:
                out.append(token)
        except RuntimeError as exc:
            error = exc
        return out, stream, error

    out, stream, error = asyncio.run(_run())
    assert out == ["ok"]
    assert isinstance(error, RuntimeError)
    assert stream.stats.stop_reason is StopReason.UPSTREAM_ERROR


def test_from_keywords_builds_case_insensitive_patterns():
    patterns = RefusalPattern.from_keywords(["cannot comply"])
    assert len(patterns) == 1
    assert patterns[0].min_window == 64
    assert patterns[0].pattern.search("Please CANNOT COMPLY with this")
