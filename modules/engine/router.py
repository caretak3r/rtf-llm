#!/usr/bin/env python3
"""Semantic technique router for adaptive engine dispatch.

Orders registered attack transforms into an attack sequence chosen from
technique profiles, scored against the goal + model identity. Uses a
dependency-free token-overlap scorer by default; a pluggable `embedder`
callable (profile_id, query) -> float can be assigned to upgrade to real
embedding similarity at runtime. Failed probes are dropped and winners
front-loaded on the next dispatch (adaptive execution).
"""

from __future__ import annotations

import math
import re

WORD_RE = re.compile(r"[a-z0-9_]{2,}")

# Per-family seed words so a family match outweighs token noise.
FAMILY_WORDS: dict[str, set[str]] = {
    "jailbreak": {"ignore", "roleplay", "dan", "system", "instructions"},
    "encoding": {"smuggle", "invisible", "unicode", "obfuscation", "fullwidth"},
    "injection": {"extract", "artifact", "canary", "inject", "prompt"},
    "adaptive": {"refine", "iterat", "pivot", "bestof", "pair"},
}


class TechniqueProfile:
    """Searchable profile for one technique id."""

    def __init__(self, transform_id: str) -> None:
        self.id = transform_id
        self.words: set[str] = set(WORD_RE.findall(transform_id.replace("/", " ")))
        family = transform_id.split("/", 1)[0]
        self.words |= FAMILY_WORDS.get(family, set())

    def term_set(self) -> set[str]:
        return self.words


def _tokens(text: str) -> set[str]:
    return set(WORD_RE.findall(text.lower()))


class SemanticRouter:
    """Ranks profiles by semantic similarity to a query."""

    def __init__(self, profiles: list[TechniqueProfile], embedder=None) -> None:
        self.profiles = profiles
        self.embedder = embedder  # optional callable(profile_id, query) -> float

    def rank(self, query: str, k: int) -> list[str]:
        scored = [(self._score(p, query), p.id) for p in self.profiles]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [pid for _, pid in scored[:k]]

    def rerank(self, query: str, failures: set[str], winners: set[str], k: int) -> list[str]:
        """Adaptive: drop failed profiles, front-load winning ones, keep score order."""
        keep = [p for p in self.profiles if p.id not in failures]
        ranked = [
            pid
            for _, pid in sorted(
                ((self._score(p, query), p.id) for p in keep), key=lambda t: (-t[0], t[1])
            )
        ]
        front = [pid for pid in ranked if pid in winners]
        rest = [pid for pid in ranked if pid not in winners]
        return (front + rest)[:k]

    def _score(self, profile: TechniqueProfile, query: str) -> float:
        if self.embedder is not None:
            return self.embedder(profile.id, query)
        q = _tokens(query)
        words = profile.term_set()
        match = len(q & words)
        return 0.0 if match == 0 else match / math.sqrt(len(words))
