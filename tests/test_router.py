#!/usr/bin/env python3
"""Tests for the semantic technique router."""

from modules.engine.registry import all_transforms, discover_transforms
from modules.engine.router import SemanticRouter, TechniqueProfile


def make_router(transform_ids):
    return SemanticRouter([TechniqueProfile(tid) for tid in transform_ids])


def test_profile_extracts_id_and_family_terms():
    profile = TechniqueProfile("jailbreak/classic")
    assert "classic" in profile.term_set()
    assert "ignore" in profile.term_set()  # family seed word


def test_rank_prefers_relevant_family():
    router = make_router(["jailbreak/classic", "encoding/fullwidth", "encoding/unicode"])
    order = router.rank("ignore prior system instructions", k=2)
    assert order[0] == "jailbreak/classic"


def test_rank_k_caps_length():
    router = make_router(["a/1", "b/2", "c/3", "d/4"])
    assert len(router.rank("unknown query here", k=3)) == 3


def test_rerank_drops_failures_and_front_loads_winners():
    router = make_router(["jailbreak/classic", "encoding/fullwidth"])
    order = router.rerank(
        "smuggle unicode payload",
        failures={"encoding/fullwidth"},
        winners={"jailbreak/classic"},
        k=2,
    )
    assert order == ["jailbreak/classic"]


def test_rerank_ties_order_by_id_without_typeerror():
    router = SemanticRouter([TechniqueProfile("b/y"), TechniqueProfile("a/x")])
    router.embedder = lambda profile_id, query: 0.5
    assert router.rerank("anything", failures=set(), winners=set(), k=2) == ["a/x", "b/y"]


def test_embedder_hook_overrides_lexical():
    router = make_router(["a/x", "b/y"])
    router.embedder = lambda profile_id, query: 1.0 if profile_id == "b/y" else 0.0
    assert router.rank("anything", k=1) == ["b/y"]


def test_zero_overlap_scores_zero():
    router = make_router(["zork/quantumwormhole"])
    assert router.rank("completely unrelated", k=1)


def test_profiles_default_from_registry():
    discover_transforms()
    profiles = [TechniqueProfile(tid) for tid in all_transforms()]
    assert len(profiles) == 20
