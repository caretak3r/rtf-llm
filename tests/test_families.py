#!/usr/bin/env python3
"""Tests for the technique-family transforms."""

from modules.engine.base import TransformContext
from modules.engine.transforms.families.families import (
    ANSIAbuseTransform,
    DelayedToolUseTransform,
    MultiChainTransform,
)


def run(transform, text):
    return transform.transform(TransformContext(input=text))


def test_multi_chain_replays_payload():
    out = run(MultiChainTransform(), "exfil the token").output
    assert "exfil the token" in out
    assert "Replay" in out
    assert run(MultiChainTransform(), "x").metrics["family"] == "multi_chain"


def test_delayed_tool_use_defers_instruction():
    out = run(DelayedToolUseTransform(), "drop secret").output
    assert "drop secret" in out
    assert "After the tool result arrives" in out


def test_ansi_abuse_smuggle_sequences():
    out = run(ANSIAbuseTransform(), "reveal ALL").output
    assert "\x1b[" in out
    assert "reveal ALL" in out


def test_deterministic_domains():
    assert run(MultiChainTransform(), "a").output == run(MultiChainTransform(), "a").output
