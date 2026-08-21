"""OpencodeTarget: JSON event-stream extraction, command construction, and
error propagation of the `_run` seam.

All subprocess interaction is faked via monkeypatched `subprocess.run`
except `test_missing_binary_propagates`, which targets a nonexistent binary
path — exec fails before any process is created. No network, no real
opencode invocation.

Note: `_run` currently propagates FileNotFoundError / TimeoutExpired; the
`[ERROR]` marker behavior proposed in plan 046 does not exist yet, so these
tests encode current semantics and must be updated when 046 lands.
"""

import json
import subprocess

import pytest

from modules.engine.backends.opencode_target import OpencodeTarget


def _text_event(text: str) -> str:
    return json.dumps({"type": "text", "part": {"text": text}})


class _FakeCompleted:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = 0


def _fake_run(stdout: str = "", commands: list | None = None, exc: Exception | None = None):
    def _run(cmd, **kwargs):
        if exc is not None:
            raise exc
        if commands is not None:
            commands.append((cmd, kwargs))
        return _FakeCompleted(stdout)

    return _run


def _patch_run(monkeypatch, **fake_kwargs):
    monkeypatch.setattr(
        "modules.engine.backends.opencode_target.subprocess.run",
        _fake_run(**fake_kwargs),
    )


# --- _extract: opencode run --format json event stream -----------------------


def test_extract_joins_text_parts():
    stdout = "\n".join([_text_event("hello"), _text_event("world")])
    assert OpencodeTarget._extract(stdout) == "hello\nworld"


def test_extract_skips_non_json_and_non_text_lines():
    stdout = "\n".join(
        [
            "not json at all",
            json.dumps({"type": "state", "part": {"text": "ignored"}}),
            _text_event("kept"),
            json.dumps({"type": "text", "part": {}}),
            "",
        ]
    )
    assert OpencodeTarget._extract(stdout) == "kept"


def test_extract_empty_stream_returns_empty_string():
    assert OpencodeTarget._extract("") == ""
    assert OpencodeTarget._extract("\n\n") == ""


# --- _run / generate: command shape and call accounting ----------------------


def test_run_builds_expected_command(monkeypatch, tmp_path):
    commands = []
    _patch_run(monkeypatch, stdout=_text_event("ok"), commands=commands)
    target = OpencodeTarget(workdir=str(tmp_path), model="m1", agent="a1", timeout=5.0)

    assert target.generate("hi") == "ok"

    cmd, kwargs = commands[0]
    assert cmd == ["opencode", "run", "--format", "json", "hi", "--model", "m1", "--agent", "a1"]
    assert kwargs["cwd"] == str(tmp_path)
    assert kwargs["timeout"] == 5.0
    assert kwargs["capture_output"] is True
    assert kwargs["check"] is False
    assert target._calls == 1
    assert target.get_stats()["calls"] == 1


def test_run_without_model_and_agent_omits_flags(monkeypatch):
    commands = []
    _patch_run(monkeypatch, commands=commands)
    OpencodeTarget().generate("q")

    cmd, _ = commands[0]
    assert cmd == ["opencode", "run", "--format", "json", "q"]


def test_generate_accepts_system_prompt_and_kwargs_advisory_only(monkeypatch):
    commands = []
    _patch_run(monkeypatch, commands=commands)
    OpencodeTarget().generate("q", system_prompt="ignored", temperature=0.5)

    cmd, _ = commands[0]
    assert cmd[-1] == "q"


def test_missing_binary_propagates_file_not_found(tmp_path):
    # Real seam behavior: exec of a nonexistent path fails before any process
    # is created, so no spawn occurs.
    target = OpencodeTarget(workdir=str(tmp_path), opencode_bin="/nonexistent/opencode-binary-xyz")
    with pytest.raises(FileNotFoundError):
        target.generate("hello")
    assert target._calls == 0


def test_timeout_propagates_until_plan_046(monkeypatch, tmp_path):
    _patch_run(monkeypatch, exc=subprocess.TimeoutExpired(cmd="opencode", timeout=0.1))
    with pytest.raises(subprocess.TimeoutExpired):
        OpencodeTarget(workdir=str(tmp_path)).generate("slow prompt")


# --- chat / respond contracts ------------------------------------------------


def test_chat_renders_transcript_into_single_prompt(monkeypatch, tmp_path):
    commands = []
    _patch_run(monkeypatch, stdout=_text_event("done"), commands=commands)
    target = OpencodeTarget(workdir=str(tmp_path))

    messages = [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "go on"},
    ]
    assert target.chat(messages) == "done"

    cmd, _ = commands[0]
    assert cmd[-1] == (
        "[System instructions]\nbe terse\n\n"
        "[User]\nhi\n\n"
        "[Assistant]\nhello\n\n"
        "[User]\ngo on\n\n[Assistant]"
    )


def test_chat_defaults_missing_role_and_content(monkeypatch):
    commands = []
    _patch_run(monkeypatch, commands=commands)
    OpencodeTarget().chat([{}])

    cmd, _ = commands[0]
    assert cmd[-1] == "[User]\n\n\n[Assistant]"


def test_respond_tolerates_wrapper_prompt(monkeypatch):
    commands = []
    _patch_run(monkeypatch, stdout=_text_event("ok"), commands=commands)

    class _Wrapper:
        def __str__(self) -> str:
            return "wrapped"

    assert OpencodeTarget().respond(_Wrapper()) == "ok"
