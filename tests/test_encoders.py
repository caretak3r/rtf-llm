#!/usr/bin/env python3
"""Tests for the Unicode obfuscation encoders."""

from modules.engine.base import TransformContext
from modules.engine.registry import all_transforms
from modules.engine.transforms.encoding.encoders import (
    FullwidthEncoder,
    UnicodeEncoder,
    VariationSelectorEncoder,
    is_obfuscated,
)


def run(transform, text):
    return transform.transform(TransformContext(input=text))


def test_unicode_invisible_interleave():
    out = run(UnicodeEncoder(), "ab").output
    assert out == "a\u200bb\u200b"


def test_variation_selector_injects():
    out = run(VariationSelectorEncoder(), "abc").output
    assert "\ufe00" in out


def test_fullwidth_reduces_ascii():
    out = run(FullwidthEncoder(), "hi ok").output
    assert out == "\uff48\uff49\u3000\uff4f\uff4b"


def test_detector_finds_and_clean():
    assert is_obfuscated(run(FullwidthEncoder(), "hi").output)
    assert not is_obfuscated("plain 123")


def test_registered():
    ids = set(all_transforms())
    assert "encoding/unicode" in ids
    assert "encoding/variation_selector" in ids
    assert "encoding/fullwidth" in ids
