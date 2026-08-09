#!/usr/bin/env python3
"""Tests for offline benchmark dataset importers."""

import json

import pytest

from modules.engine.datasets import BenchmarkError, load_benchmark, normalize_row


def test_normalize_row_aliases():
    row = normalize_row({"jailbreak": "attack text", "category": "forgery"}, "harmbench")
    assert row["prompt"] == "attack text"
    assert row["benchmark"] == "harmbench"
    assert row["category"] == "forgery"
    assert row["id"] == "0"


def test_normalize_row_requires_prompt():
    with pytest.raises(BenchmarkError):
        normalize_row({"category": "no prompt here"}, "jailbreakbench")


def test_load_jsonl(tmp_path):
    path = tmp_path / "jb.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"prompt": "attack one", "category": "harmful"}),
                json.dumps({"prompt": "attack two"}),
            ]
        )
    )
    rows = load_benchmark(path, "jailbreakbench")
    assert len(rows) == 2
    assert rows[0]["category"] == "harmful"
    assert rows[1]["prompt"] == "attack two"


def test_load_single_json_list(tmp_path):
    path = tmp_path / "sr.json"
    path.write_text(json.dumps([{"question": "q1"}, {"question": "q2"}]))
    rows = load_benchmark(path, "strongREJECT")
    assert [r["prompt"] for r in rows] == ["q1", "q2"]


def test_load_json_data_key(tmp_path):
    path = tmp_path / "hb.json"
    path.write_text(json.dumps({"data": [{"text": "t1"}]}))
    assert load_benchmark(path, "harmbench")[0]["prompt"] == "t1"


def test_load_csv(tmp_path):
    path = tmp_path / "bench.csv"
    path.write_text("behavior,prompt\nb1,p1\nb2,p2\n")
    rows = load_benchmark(path, "jailbreakbench")
    assert len(rows) == 2
    assert rows[0]["category"] == "b1"


def test_missing_file_raises(tmp_path):
    with pytest.raises(BenchmarkError):
        load_benchmark(tmp_path / "nope.jsonl", "harmbench")


def test_unsupported_benchmark_raises(tmp_path):
    path = tmp_path / "x.jsonl"
    path.write_text("{}")
    with pytest.raises(BenchmarkError):
        load_benchmark(path, "llm-attacks")


def test_bad_jsonl_raises(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("{not json}\n")
    with pytest.raises(BenchmarkError):
        load_benchmark(path, "jailbreakbench")
