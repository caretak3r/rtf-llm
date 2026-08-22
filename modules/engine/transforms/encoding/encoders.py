"""Obfuscation encoders for prompt smuggling.

Provides composable Unicode-based obfuscation transforms: invisible
character injection, emoji variation selector insertion, and fullwidth
(ASCII -> Unicode) homoglyph reduction. Each encoder keeps the payload
readable to the target model while evading naive text scanners.
"""

from __future__ import annotations

from modules.engine.base import Transform, TransformContext, TransformResult
from modules.engine.registry import register_transform

VARIATION_SELECTORS = (0xFE00, 0xFE01, 0xFE02, 0xFE03, 0xFE0E, 0xFE0F)
FULLWIDTH_OFFSET = 0xFEE0


@register_transform("encoding/unicode")
class UnicodeEncoder(Transform):
    """Interleave an invisible character after every payload character."""

    id = "encoding/unicode"

    def __init__(self, invisible: str = "\u200b") -> None:
        self.invisible = invisible

    def transform(self, ctx: TransformContext) -> TransformResult:
        encoded = self.invisible.join(ctx.input) + self.invisible
        return TransformResult(
            output=encoded, metrics={"encoder": "unicode", "inserted": len(ctx.input) + 1}
        )


@register_transform("encoding/variation_selector")
class VariationSelectorEncoder(Transform):
    """Inject emoji variation selectors between alphanumeric characters."""

    id = "encoding/variation_selector"

    def transform(self, ctx: TransformContext) -> TransformResult:
        out = []
        injected = 0
        for i, ch in enumerate(ctx.input):
            out.append(ch)
            if i % 2 == 0 and ch.isalnum():
                out.append(chr(VARIATION_SELECTORS[injected % len(VARIATION_SELECTORS)]))
                injected += 1
        return TransformResult(
            output="".join(out), metrics={"encoder": "variation_selector", "injected": injected}
        )


@register_transform("encoding/fullwidth")
class FullwidthEncoder(Transform):
    """Reduce ASCII characters to fullwidth Unicode homoglyphs."""

    id = "encoding/fullwidth"

    def transform(self, ctx: TransformContext) -> TransformResult:
        out = []
        for ch in ctx.input:
            code = ord(ch)
            if 0x21 <= code <= 0x7E:
                out.append(chr(code + FULLWIDTH_OFFSET))
            elif ch == " ":
                out.append("\u3000")
            else:
                out.append(ch)
        return TransformResult(output="".join(out), metrics={"encoder": "fullwidth"})


def is_obfuscated(text: str) -> bool:
    """Detect whether the text contains any of the encodings this module applies."""
    for ch in text:
        if ch == "\u200b" or 0xFE00 <= ord(ch) <= 0xFE0F:
            return True
        code = ord(ch)
        if 0xFF01 <= code <= 0xFF5E or ch == "\u3000":
            return True
    return False
