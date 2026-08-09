"""Tests for the MITRE ATLAS technique KB (modules.engine.kb.atlas)."""

from __future__ import annotations

from modules.engine.kb.atlas import (
    ATLAS_VERIFIED_IDS,
    TECHNIQUE_KB,
    coverage_map,
    render_coverage_table,
    to_documents,
    validate_kb,
)


def test_kb_covers_core_families():
    expected = {
        "direct_injection",
        "indirect_injection",
        "ignore_instructions",
        "encoding_attacks",
        "jailbreak_roleplay",
        "exfiltration",
        "supply_chain",
        "poisoning",
    }
    assert expected <= set(TECHNIQUE_KB)


def test_kb_validation_passes():
    assert validate_kb() == []


def test_kb_validation_flags_fabricated_atlas_id(monkeypatch):
    monkeypatch.setitem(TECHNIQUE_KB["direct_injection"], "atlas", "AML.T9999")
    violations = validate_kb()
    monkeypatch.setitem(TECHNIQUE_KB["direct_injection"], "atlas", "AML.T0051")
    assert any("not in verified whitelist" in v for v in violations)


def test_kb_validation_flags_uncited_entry(monkeypatch):
    monkeypatch.setitem(TECHNIQUE_KB["poisoning"], "references", [])
    violations = validate_kb()
    monkeypatch.setitem(
        TECHNIQUE_KB["poisoning"], "references", TECHNIQUE_KB["poisoning"]["references"]
    )
    assert any("zero citations" in v for v in violations)


def test_verified_ids_well_formed():
    for tech_id in ATLAS_VERIFIED_IDS:
        assert tech_id.startswith("AML.T")
        assert len(tech_id.split(".")[-1]) == 5


def test_every_entry_has_atlas_and_defense():
    for name, entry in TECHNIQUE_KB.items():
        assert entry["atlas"] in ATLAS_VERIFIED_IDS, name
        assert entry["description"], name
        assert entry["defense"], name


def test_coverage_map_covers_all_families():
    cm = coverage_map()
    assert set(cm) == {"claude", "gpt", "gemini", "llama", "mistral"}
    for techniques in cm.values():
        assert set(techniques) == set(TECHNIQUE_KB)


def test_coverage_table_renders():
    table = render_coverage_table()
    assert "claude" in table and "gpt" in table
    assert f"{len(TECHNIQUE_KB)}" in table


def test_to_documents_indexable():
    docs = to_documents()
    assert len(docs) == len(TECHNIQUE_KB)
    for doc in docs:
        assert doc["id"].startswith("kb-")
        assert doc["text"]
        assert doc["metadata"]["atlas"] in ATLAS_VERIFIED_IDS


def test_references_all_have_real_urls():
    for name, entry in TECHNIQUE_KB.items():
        for ref in entry["references"]:
            assert ref["url"].startswith("http"), (name, ref)
