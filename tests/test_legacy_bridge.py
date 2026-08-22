"""Legacy bridge: live-gate error path, campaign folding into TransformResult,
and the _Facade client shim. Legacy attack modules are replaced by fakes via
monkeypatched importlib — no frozen modules/*.py code is imported.
"""

import types

from modules.engine.base import TransformContext
from modules.engine.registry import all_transforms
from modules.engine.transforms.legacy import legacy_bridge as lb

TID = "legacy/prompt_injection"


class _FakeTarget:
    model = "fake-model"

    def __init__(self):
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "resp: " + prompt


class _ChatTarget:
    model = "chat-model"

    def __init__(self):
        self.chat_calls = []

    def chat(self, messages, **kwargs):
        self.chat_calls.append((messages, kwargs))
        return "chat-reply"

    def get_stats(self):
        return {"calls": len(self.chat_calls)}


def _bridge(intensity: str = "low"):
    return lb._bridge(TID)(intensity=intensity)


def _ctx(target=None, config=None) -> TransformContext:
    return TransformContext(input="probe", target=target, config=config or {})


def _install_fake_module(monkeypatch, campaign=None, exc=None):
    calls = {}

    class _FakeLegacyModule:
        def __init__(self, client, cfg, intensity="low"):
            calls["client"] = client
            calls["cfg"] = cfg
            calls["intensity"] = intensity

        def run_all_attacks(self):
            if exc is not None:
                raise exc
            return campaign

    fake_mod = types.SimpleNamespace(PromptInjectionModule=_FakeLegacyModule)
    monkeypatch.setattr(lb, "importlib", types.SimpleNamespace(import_module=lambda name: fake_mod))
    return calls


# --- live gate ---------------------------------------------------------------


def test_live_gate_off_without_target():
    result = _bridge().transform(_ctx())
    assert result.error == f"{TID} requires a live target (engine.live=true)"
    assert result.output == ""
    assert result.bypassed is False


def test_live_gate_off_when_engine_live_false():
    result = _bridge().transform(_ctx(target=_FakeTarget(), config={"engine": {"live": False}}))
    assert "requires a live target" in result.error
    assert result.bypassed is False


# --- campaign folding --------------------------------------------------------


def test_live_gate_on_folds_campaign(monkeypatch):
    campaign = {
        "module": TID,
        "intensity": "high",
        "attacks": [
            {"pattern": "p1", "response": "r1", "success": True, "category": "cat1"},
            {"prompt": "p2", "response": "r2", "success": False, "category": "cat1"},
            {"pattern": "p3", "response": "", "success": False, "category": "cat2"},
        ],
    }
    calls = _install_fake_module(monkeypatch, campaign=campaign)
    target = _FakeTarget()

    result = _bridge(intensity="high").transform(
        _ctx(target=target, config={"engine": {"live": True}})
    )

    assert result.error is None
    assert result.output == TID
    assert result.bypassed is True
    assert result.refusal_detected is False
    assert result.metrics == {
        "campaign": TID,
        "intensity": "high",
        "attacks": 3,
        "successful": 1,
        "categories": 2,
    }
    assert len(result.artifacts) == 3
    assert result.artifacts[0] == {"pattern": "p1", "response": "r1", "category": "cat1"}
    assert result.artifacts[1]["pattern"] == "p2"  # prompt fallback for pattern
    # facade wired to the engine target; rate limiting zeroed in module config
    assert calls["client"]._target is target
    assert calls["cfg"]["rate_limiting"]["delay_between_requests"] == 0.0
    assert calls["intensity"] == "high"


def test_output_falls_back_to_transform_id_when_campaign_has_no_module(monkeypatch):
    _install_fake_module(monkeypatch, campaign={"attacks": []})
    result = _bridge().transform(_ctx(target=_FakeTarget(), config={"engine": {"live": True}}))
    assert result.output == TID
    assert result.bypassed is False
    assert result.metrics["successful"] == 0
    assert result.metrics["categories"] == 0


def test_artifacts_without_pattern_or_response_are_dropped(monkeypatch):
    _install_fake_module(monkeypatch, campaign={"attacks": [{"response": "", "success": False}]})
    result = _bridge().transform(_ctx(target=_FakeTarget(), config={"engine": {"live": True}}))
    assert result.artifacts == []


def test_campaign_failure_returns_error(monkeypatch):
    _install_fake_module(monkeypatch, exc=RuntimeError("kaboom"))
    result = _bridge().transform(_ctx(target=_FakeTarget(), config={"engine": {"live": True}}))
    assert result.error == f"{TID} campaign failed: kaboom"
    assert result.bypassed is False
    assert result.metrics == {"intensity": "low"}


def test_import_failure_returns_error(monkeypatch):
    def _boom(name):
        raise ImportError("no such module")

    monkeypatch.setattr(lb, "importlib", types.SimpleNamespace(import_module=_boom))
    result = _bridge().transform(_ctx(target=_FakeTarget(), config={"engine": {"live": True}}))
    assert result.error.startswith("import failed:")
    assert "no such module" in result.error


# --- registration ------------------------------------------------------------


def test_all_legacy_ids_registered():
    registered = all_transforms()
    for tid in lb.LEGACY_TARGETS:
        assert tid in registered


# --- _Facade -----------------------------------------------------------------


def test_facade_chat_delegates_when_target_has_chat():
    target = _ChatTarget()
    facade = lb._Facade(target)
    assert facade.chat([{"role": "user", "content": "hi"}], temperature=0) == "chat-reply"
    messages, kwargs = target.chat_calls[0]
    assert messages == [{"role": "user", "content": "hi"}]
    assert kwargs == {"temperature": 0}


def test_facade_chat_collapses_multi_turn_into_single_prompt():
    target = _FakeTarget()
    facade = lb._Facade(target)
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
    ]
    reply = facade.chat(messages)
    expected_prompt = "system: sys\n\nuser: u1\n\nassistant: a1"
    assert target.prompts == [expected_prompt]
    assert reply == "resp: " + expected_prompt


def test_facade_generate_coerces_and_defaults_client_attributes():
    target = _FakeTarget()
    facade = lb._Facade(target)
    assert facade.provider == "opencode"
    assert facade.model == "fake-model"
    assert facade.canary_token is None
    assert facade.target_system_prompt is None
    assert facade.generate("hi", system_prompt="ignored") == "resp: hi"


def test_facade_get_stats_passthrough_and_empty_default():
    assert lb._Facade(_ChatTarget()).get_stats() == {"calls": 0}
    assert lb._Facade(_FakeTarget()).get_stats() == {}
