#!/usr/bin/env python3
"""Offline benchmark dataset importers (jailbreakbench / harmbench / strongREJECT).

Loads local JSONL / JSON / CSV files and normalizes them into a single
internal row schema. No network access, no heavy deps: the framework's
evaluation loop  runs prompts straight from these records.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

SUPPORTED = ("jailbreakbench", "harmbench", "strongreject")

# Common field aliases seen across the three offline formats.
CATEGORY_KEYS = ("category", "behavior", "goal_category", "harm_category")
PROMPT_KEYS = ("prompt", "jailbreak", "prompt_text", "question", "text")
ID_KEYS = ("id", "index", "idx", "row_id")


class BenchmarkError(ValueError):
    """Raised when a benchmark file cannot be loaded or normalized."""


def _first(row: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) or isinstance(value, int):
            return str(value)
    return None


def normalize_row(row: dict, benchmark: str) -> dict:
    """Map an arbitrary offline row to the internal evaluation schema."""
    prompt = _first(row, PROMPT_KEYS)
    if not prompt:
        raise BenchmarkError(f"row has no recognised prompt field: {list(row)[:6]}")
    return {
        "benchmark": benchmark,
        "id": _first(row, ID_KEYS) or "0",
        "category": _first(row, CATEGORY_KEYS) or "uncategorized",
        "prompt": prompt,
        "source": row.get("source") or "offline",
    }


def _read_jsonl(path: Path, benchmark: str) -> list[dict]:
    rows = []
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(normalize_row(json.loads(line), benchmark))
        except (ValueError, json.JSONDecodeError) as exc:
            raise BenchmarkError(f"bad JSONL record in {path}: {exc}") from exc
    return rows


def _read_single_json(path: Path, benchmark: str) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise BenchmarkError(f"invalid JSON in {path}: {exc}") from exc
    items = data if isinstance(data, list) else data.get("data") or data.get("prompts") or []
    if not isinstance(items, list):
        raise BenchmarkError(f"unrecognised JSON shape in {path}")
    return [normalize_row(row, benchmark) for row in items]


def _read_csv(path: Path, benchmark: str) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [normalize_row(row, benchmark) for row in reader]


def load_benchmark(path: str | Path, benchmark: str = "jailbreakbench") -> list[dict]:
    if benchmark.lower() not in SUPPORTED:
        raise BenchmarkError(f"unsupported benchmark '{benchmark}'; expected one of {SUPPORTED}")
    path = Path(path)
    if not path.exists():
        raise BenchmarkError(f"dataset file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return _read_jsonl(path, benchmark)
    if suffix == ".json":
        return _read_single_json(path, benchmark)
    if suffix == ".csv":
        return _read_csv(path, benchmark)
    raise BenchmarkError(f"unsupported file type '{suffix}' for benchmark file {path}")
