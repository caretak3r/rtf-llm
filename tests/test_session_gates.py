#!/usr/bin/env python3
"""Tests for session artifacts, hard-stop gates, and stall detection."""

import time

import pytest

from modules.engine.backends.gates import (
    GateAborted,
    StallDetector,
    StallError,
    hard_stop_gate,
)
from modules.engine.backends.session import SessionArtifacts, find_sessions


def test_session_creates_isolated_subdirs(tmp_path):
    session = SessionArtifacts(tmp_path, label="alpha")
    for name in ("recon", "prompts", "responses", "logs", "report"):
        assert session.dirs[name].is_dir()


def test_two_runs_isolated(tmp_path):
    first = SessionArtifacts(tmp_path, label="run-a")
    second = SessionArtifacts(tmp_path, label="run-b")
    assert first.session_dir != second.session_dir
    assert len(find_sessions(tmp_path)) == 2


def test_write_prompt_artifact(tmp_path):
    session = SessionArtifacts(tmp_path)
    path = session.write("prompts", "001.txt", "hello")
    assert path.exists()
    assert path.read_text() == "hello"


def test_write_json(tmp_path):
    session = SessionArtifacts(tmp_path)
    path = session.write_json("recon", "identity.json", {"name": "gpt-4"})
    assert '"name": "gpt-4"' in path.read_text()


def test_unknown_kind_raises(tmp_path):
    session = SessionArtifacts(tmp_path)
    with pytest.raises(ValueError):
        session.write("nonsense", "x.txt", "y")


def test_gate_accepts_confirmation(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "YES")
    hard_stop_gate("proceed?")


def test_gate_aborts_on_decline(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "no")
    with pytest.raises(GateAborted):
        hard_stop_gate("proceed?")


def test_gate_aborts_on_eof(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError()))
    with pytest.raises(GateAborted):
        hard_stop_gate("proceed?")


def test_stall_detector_flags_and_check():
    with StallDetector(0.1) as detector:
        time.sleep(0.3)
        with pytest.raises(StallError):
            detector.check()


def test_stall_detector_no_stall_with_beats():
    detector = StallDetector(5.0)
    detector.beat()
    assert detector.check() is None


