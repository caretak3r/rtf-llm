#!/usr/bin/env python3
"""Default-config anchoring is cwd-independent."""

import json

from modules.config_manager import ConfigManager, _default_config_path


def test_default_path_absolute_and_exists():
    p = _default_config_path()
    assert p.is_absolute()
    assert p.name == "config.json"
    assert p.exists()


def test_cwd_does_not_change_resolution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cm = ConfigManager()
    assert cm.resolved_source == _default_config_path().resolve()


def test_local_cwd_config_wins_over_anchored_default(tmp_path, monkeypatch):
    local = tmp_path / "config.json"
    local.write_text(json.dumps({"llm": {"provider": "custom-local"}}))
    monkeypatch.chdir(tmp_path)
    cm = ConfigManager()
    assert cm.resolved_source == local.resolve()
    assert cm.config["llm"]["provider"] == "custom-local"


def test_explicit_missing_path_still_uses_builtin_defaults(tmp_path):
    cm = ConfigManager(str(tmp_path / "nope.json"))
    assert cm.resolved_source is None
    assert cm.config["llm"]["provider"] == "openai"
