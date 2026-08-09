#!/usr/bin/env python3
"""Baseline tests for LLMClient (mocked — no live API)."""

import pytest

from modules.llm_client import LLMClient, auto_detect_provider


def test_auto_detect_ollama_port():
    assert auto_detect_provider("http://localhost:11434") == "ollama"


def test_auto_detect_lmstudio_port():
    assert auto_detect_provider("http://127.0.0.1:1234") == "lmstudio"


def test_auto_detect_openai_domain():
    assert auto_detect_provider("https://api.openai.com/v1") == "openai"


def test_auto_detect_none():
    assert auto_detect_provider(None) == "custom"


def test_requires_api_key_for_keyed_provider():
    with pytest.raises(ValueError, match="API key required"):
        LLMClient({"provider": "openai", "model": "gpt-4", "api_key": None})


def test_accepts_api_key_for_keyed_provider():
    client = LLMClient({"provider": "openai", "model": "gpt-4", "api_key": "k"})
    assert client.provider == "openai"
    assert client.model == "gpt-4"


def test_cli_provider_needs_no_key():
    client = LLMClient({"provider": "droid", "model": "droid-1"})
    assert client.provider == "droid"


def test_canary_token_deployed_with_template():
    client = LLMClient(
        {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "k",
            "target_system_prompt": "You are a test bot. TOKEN: {canary}",
        }
    )
    assert client.canary_token
    assert client.canary_token in client.target_system_prompt


def test_canary_disabled_when_target_false():
    client = LLMClient(
        {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "k",
            "target_system_prompt": False,
        }
    )
    assert client.target_system_prompt is None


def test_explicit_model_skips_discovery(monkeypatch):
    """An explicit model must never trigger a network call at init."""
    called = []

    def fail_discovery(self):
        called.append(True)
        raise AssertionError("network discovery called at init")

    monkeypatch.setattr(LLMClient, "discover_loaded_model", fail_discovery)
    LLMClient({"provider": "openai", "model": "gpt-4", "api_key": "k"})
    assert called == []
