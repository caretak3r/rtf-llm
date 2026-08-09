"""Checkpoint/resume + high-water-mark rollback for pipeline runs.

Pattern source: BrokenHill's per-iteration state backups. Data is stored as
atomic JSON (temp file + os.replace) so a killed run never corrupts the
checkpoint. High-water logic keeps the best-so-far result when a resumed
run regresses on the supplied metric.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class CheckpointStore:
    """Disk-backed JSON checkpoint with atomic writes."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)

    def save(self, key: str, data: dict) -> None:
        """Atomically persist a checkpoint entry."""
        update = self.load() or {}
        update[key] = data
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".ckpt-")
        try:
            with os.fdopen(fd, "w") as fh:
                json.dump(update, fh, indent=2)
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            with open(self.path, "r") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return None

    def resume(self, key: str) -> dict | None:
        """Load a single named checkpoint entry, or None if absent."""
        data = self.load()
        if not data:
            return None
        return data.get(key)

    def clear(self) -> None:
        if self.path.exists():
            os.remove(self.path)


def check_high_water(best: float | None, current: float) -> tuple[float, bool]:
    """Return (metric, improved) — keeps the best-so-far metric.

    A regression (current < best) reports improved=False so callers leave
    the stored high-water mark untouched.
    """
    if best is None or current > best:
        return current, True
    return best, False
