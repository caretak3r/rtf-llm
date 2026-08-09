#!/usr/bin/env python3
"""Baseline tests for ConfigManager."""

import json


from modules.config_manager import ConfigManager


def test_loads_existing_config(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"llm": {"provider": "custom", "api_key": "k"}}))
    cm = ConfigManager(str(cfg_path))
    assert cm.config["llm"]["provider"] == "custom"


def test_falls_back_to_defaults_when_missing(tmp_path):
    cm = ConfigManager(str(tmp_path / "nope.json"))
    assert cm.config["llm"]["provider"] == "openai"
    assert cm.config.get("attacks", {}).get("enable_all") is True


def test_falls_back_to_defaults_on_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    cm = ConfigManager(str(bad))
    assert cm.config["llm"]["provider"] == "openai"


def test_env_var_override(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "env-key-123")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    cm = ConfigManager(str(tmp_path / "empty.json"))
    assert cm.config["providers"]["openai"]["api_key"] == "env-key-123"
    # Provider key propagates to llm.api_key
    assert cm.config["llm"]["api_key"] == "env-key-123"


def test_get_with_dot_path(tmp_path):
    cm = ConfigManager(str(tmp_path / "empty.json"))
    assert cm.get("llm.provider") == "openai"
    assert cm.get("llm.missing.key", "fallback") == "fallback"


def test_set_with_dot_path_creates_nested(tmp_path):
    cm = ConfigManager(str(tmp_path / "empty.json"))
    cm.set("custom.nested.value", 42)
    assert cm.config["custom"]["nested"]["value"] == 42


def test_update_config_deep_merge(tmp_path):
    cm = ConfigManager(str(tmp_path / "empty.json"))
    cm.update_config({"llm": {"temperature": 0.1}})
    assert cm.config["llm"]["temperature"] == 0.1
    assert cm.config["llm"]["provider"] == "openai"


def test_save_config_strips_api_keys(tmp_path):
    cm = ConfigManager(str(tmp_path / "empty.json"))
    cm.set("llm.api_key", "super-secret")
    cm.set("providers.openai.api_key", "provider-secret")
    out = tmp_path / "saved.json"
    cm.save_config(str(out))
    data = json.loads(out.read_text())
    assert data["llm"]["api_key"] is None
    assert data["providers"]["openai"]["api_key"] is None


def test_get_llm_config_merges_provider_defaults(tmp_path):
    cm = ConfigManager(str(tmp_path / "empty.json"))
    cm.config["providers"]["openai"]["default_model"] = "gpt-4-test"
    cm.config["llm"]["model"] = ""
    cfg = cm.get_llm_config()
    assert cfg["model"] == "gpt-4-test"
