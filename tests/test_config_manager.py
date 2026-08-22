#!/usr/bin/env python3
"""Baseline tests for ConfigManager."""

import json


from modules.config_manager import ConfigManager


def _cm(tmp_path, cfg):
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    return ConfigManager(config_path=str(p))


def test_get_dot_path(tmp_path):
    cm = _cm(tmp_path, {"llm": {"provider": "ollama", "model": "llama3"}})
    assert cm.get("llm.provider") == "ollama"
    assert cm.get("llm.missing", "fallback") == "fallback"


def test_set_creates_nested_path(tmp_path):
    cm = _cm(tmp_path, {"llm": {}})
    cm.set("llm.temperature", 0.2)
    assert cm.get("llm.temperature") == 0.2


def test_get_llm_config_merges_provider_defaults(tmp_path):
    cfg = {
        "llm": {"provider": "openai", "model": "", "api_key": None, "base_url": None},
        "providers": {
            "openai": {
                "default_model": "gpt-4o",
                "base_url": "https://api.openai.com/v1",
            }
        },
    }
    cm = _cm(tmp_path, cfg)
    merged = cm.get_llm_config()
    assert merged["model"] == "gpt-4o"
    assert merged["base_url"] == "https://api.openai.com/v1"


def test_missing_config_file_uses_defaults(tmp_path):
    cm = ConfigManager(config_path=str(tmp_path / "does_not_exist.json"))
    assert cm.get("llm.provider") == "openai"
