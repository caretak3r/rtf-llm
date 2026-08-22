#!/usr/bin/env python3
"""Tests for checkpoint/resume + high-water rollback."""

from modules.engine.backends.checkpoint import CheckpointStore, check_high_water


def test_save_and_load_roundtrip(tmp_path):
    store = CheckpointStore(tmp_path / "ckpt.json")
    store.save("run:1", {"iter": 3, "jailbreaks": 2})
    assert store.load()["run:1"]["iter"] == 3
    assert store.resume("run:1")["jailbreaks"] == 2


def test_load_missing_returns_none(tmp_path):
    store = CheckpointStore(tmp_path / "nope.json")
    assert store.load() is None
    assert store.resume("anything") is None


def test_atomic_write_never_corrupts_on_load(tmp_path):
    p = tmp_path / "ckpt.json"
    store = CheckpointStore(p)
    store.save("k", {"v": 1})
    p.write_text("{corrupted json")
    assert store.load() is None
    store.save("k2", {"v": 2})
    assert store.resume("k2") == {"v": 2}


def test_resume_after_new_save_preserves_old_entries(tmp_path):
    store = CheckpointStore(tmp_path / "ckpt.json")
    store.save("attempt:1", {"jailbreaks": 4})
    store.save("attempt:2", {"jailbreaks": 7})
    assert store.resume("attempt:1")["jailbreaks"] == 4
    assert store.resume("attempt:2")["jailbreaks"] == 7


def test_clear_removes_file(tmp_path):
    p = tmp_path / "ckpt.json"
    store = CheckpointStore(p)
    store.save("k", {"v": 1})
    store.clear()
    assert not p.exists()


def test_high_water_keeps_best(tmp_path):
    store = CheckpointStore(tmp_path / "ckpt.json")
    store.save("high-water", {"metric": 0.8})
    best = store.resume("high-water")["metric"]

    current, improved = check_high_water(best, 0.6)
    assert not improved
    assert current == 0.8
    assert store.resume("high-water")["metric"] == 0.8

    current, improved = check_high_water(best, 0.95)
    assert improved
    assert current == 0.95


def test_high_water_first_run(tmp_path):
    best, improved = check_high_water(None, 0.5)
    assert improved is True
    assert best == 0.5


def test_resume_roundtrip_done_seeds(tmp_path):
    store = CheckpointStore(tmp_path / "ckpt.json")
    store.save(
        "latest",
        {"iteration": 3, "metric": 0.5, "seeds": 5, "done_seeds": [1, 2]},
    )
    assert store.resume("latest")["done_seeds"] == [1, 2]


def test_corrupt_state_warns_and_returns_none(tmp_path, capsys):
    p = tmp_path / "ckpt.json"
    store = CheckpointStore(p)
    store.save("latest", {"iteration": 1, "metric": 1, "seeds": 3})
    p.write_text("{not json")
    assert store.resume("latest") is None
    assert "Checkpoint corrupted, starting fresh" in capsys.readouterr().out


def test_remaining_seeds_math(tmp_path):
    store = CheckpointStore(tmp_path / "ckpt.json")
    assert list(store.remaining_seeds(None, 3)) == [1, 2, 3]
    assert list(store.remaining_seeds({"done_seeds": [1, 2]}, 5)) == [3, 4, 5]


def test_high_water_blocks_regression_overwrite(tmp_path):
    store = CheckpointStore(tmp_path / "ckpt.json")
    assert store.save("latest", {"metric": 8}) is True
    assert store.save("latest", {"metric": 3}) is False
    assert store.resume("latest")["metric"] == 8
    assert store.save("latest", {"metric": 3}, force=True) is True
    assert store.resume("latest")["metric"] == 3


def test_interrupted_run_resumes_from_last_seed(tmp_path):
    p = tmp_path / "ckpt.json"
    store = CheckpointStore(p)
    for seed, metric in ((1, 2), (2, 4)):
        store.save(
            "latest",
            {
                "iteration": seed,
                "metric": metric,
                "seeds": 4,
                "done_seeds": [s for s in (1, 2) if s <= seed],
            },
            force=True,
        )

    # Simulated crash before seeds 3-4; a fresh process resumes.
    resumed = CheckpointStore(p).resume("latest")
    assert resumed["done_seeds"] == [1, 2]
    assert list(CheckpointStore(p).remaining_seeds(resumed, 4)) == [3, 4]
