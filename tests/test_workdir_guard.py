"""Workdir guard: scratch default, home refusal; droid unsafe-flag gate."""

import subprocess
from pathlib import Path

import pytest


# --- resolve_workdir ----------------------------------------------------------


def test_default_resolves_to_scratch_outside_home(monkeypatch, tmp_path):
    from scripts.run_opencode_campaign import resolve_workdir

    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    out = resolve_workdir(None, out_dir=str(tmp_path / "campout"))
    assert "agent_scratch_" in out
    assert Path(out).is_dir()
    assert Path(out).resolve() != Path.home().resolve()


def test_explicit_home_requires_optin(monkeypatch, tmp_path):
    from scripts.run_opencode_campaign import resolve_workdir

    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(SystemExit):
        resolve_workdir(str(tmp_path), out_dir=str(tmp_path / "x"), allow_home=False)


def test_tilde_home_expands_and_requires_optin(monkeypatch, tmp_path):
    from scripts.run_opencode_campaign import resolve_workdir

    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(SystemExit):
        resolve_workdir("~", out_dir=str(tmp_path / "x"), allow_home=False)


def test_allow_home_optin_permits_home(monkeypatch, tmp_path):
    from scripts.run_opencode_campaign import resolve_workdir

    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    out = resolve_workdir(str(tmp_path), out_dir=str(tmp_path / "x"), allow_home=True)
    assert Path(out).resolve() == tmp_path.resolve()


# --- droid unsafe-permissions gate --------------------------------------------


def test_droid_unsafe_flag_requires_explicit_optin(monkeypatch):
    from modules.llm_client import LLMClient

    monkeypatch.delenv("RTF_ALLOW_UNSAFE_DROID", raising=False)
    client = LLMClient({"provider": "droid"})
    with pytest.raises(RuntimeError, match="RTF_ALLOW_UNSAFE_DROID"):
        client._droid_generate("hello")


def test_droid_unsafe_flag_optin_still_runs(monkeypatch):
    import modules.llm_client as lc
    from modules.llm_client import LLMClient

    monkeypatch.setenv("RTF_ALLOW_UNSAFE_DROID", "1")
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(lc.subprocess, "run", fake_run)
    client = LLMClient({"provider": "droid"})
    assert client._droid_generate("hello") == "ok\n"
    assert "--skip-permissions-unsafe" in seen["cmd"]


def test_explicit_subdir_of_home_requires_optin(monkeypatch, tmp_path):
    """POC regression: ~/Documents as workdir gave a compromised agent
    traversal reach into every operator file via ../.."""
    from scripts.run_opencode_campaign import resolve_workdir

    fakehome = tmp_path / "fakehome"
    (fakehome / "Documents").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fakehome))
    with pytest.raises(SystemExit):
        resolve_workdir(str(fakehome / "Documents"), out_dir=str(tmp_path / "x"))
    out = resolve_workdir(str(fakehome / "Documents"), out_dir=str(tmp_path / "x"), allow_home=True)
    assert Path(out).resolve() == (fakehome / "Documents").resolve()


def test_explicit_symlink_into_home_requires_optin(monkeypatch, tmp_path):
    from scripts.run_opencode_campaign import resolve_workdir

    fakehome = tmp_path / "fakehome"
    fakehome.mkdir()
    link = tmp_path / "link"
    link.symlink_to(fakehome)
    monkeypatch.setenv("HOME", str(fakehome))
    with pytest.raises(SystemExit):
        resolve_workdir(str(link), out_dir=str(tmp_path / "x"))


def test_scratch_under_home_still_allowed(monkeypatch, tmp_path):
    """--out under home stays usable: only EXPLICIT workdir args are fenced."""
    from scripts.run_opencode_campaign import resolve_workdir

    fakehome = tmp_path / "fakehome"
    fakehome.mkdir()
    monkeypatch.setenv("HOME", str(fakehome))
    out = resolve_workdir(None, out_dir=str(fakehome / "campout"))
    assert Path(out).is_dir()
