"""Scratch workdir canary planting + leak predicate."""

import secrets


def test_plant_creates_files_with_token_once_each(tmp_path):
    from scripts.run_opencode_campaign import plant_canary

    token = f"RTF-CANARY-{secrets.token_hex(8)}"
    plant_canary(str(tmp_path), token)
    assert (tmp_path / "AGENTS.md").read_text().count(token) == 1
    assert (tmp_path / "CANARY.txt").read_text().count(token) == 1


def test_plant_leaves_pre_existing_files_untouched(tmp_path):
    from scripts.run_opencode_campaign import plant_canary

    (tmp_path / "README.md").write_text("keep me")
    plant_canary(str(tmp_path), f"RTF-CANARY-{secrets.token_hex(8)}")
    assert (tmp_path / "README.md").read_text() == "keep me"


def test_leak_predicate_positive_and_negative():
    from modules.engine.eval.canary import is_ground_truth_leak

    assert is_ground_truth_leak("here: RTF-CANARY-deadbeef", "RTF-CANARY-deadbeef")
    assert not is_ground_truth_leak("nothing here", "RTF-CANARY-deadbeef")
