#!/usr/bin/env python3
"""Per-run session artifact layout.

Every run creates an isolated session_<timestamp>_<label>/ directory with
recon, prompts, responses, logs and report subdirs. The provenance DB
(run_id) stays the canonical index; these dirs hold the raw artifacts.
"""

from __future__ import annotations

import time
from pathlib import Path

SUBDIRS = ("recon", "prompts", "responses", "logs", "report")


class SessionArtifacts:
    """Creates and owns the artifact tree for one run."""

    def __init__(self, root: str | Path, label: str = "run") -> None:
        self.root = Path(root)
        self.label = label
        self.session_dir = self.root / f"session_{int(time.time())}_{label}"
        self.dirs = {name: self.session_dir / name for name in SUBDIRS}
        for path in self.dirs.values():
            path.mkdir(parents=True, exist_ok=True)

    def write(self, kind: str, filename: str, content: str) -> Path:
        """Write one artifact into a subdir (kind must be a known subdir)."""
        if kind not in self.dirs:
            raise ValueError(f"unknown artifact kind '{kind}'; expected one of {SUBDIRS}")
        path = self.dirs[kind] / filename
        path.write_text(content)
        return path

    def write_json(self, kind: str, filename: str, data: dict) -> Path:
        import json

        return self.write(kind, filename, json.dumps(data, indent=2))

    def __str__(self) -> str:
        return str(self.session_dir)


def find_sessions(root: str | Path) -> list[Path]:
    """All session dirs under root, newest first."""
    paths = sorted(Path(root).glob("session_*"))
    return list(reversed(paths))
