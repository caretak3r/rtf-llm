"""Checkpoint/resume + high-water-mark rollback for pipeline runs.

Pattern source: BrokenHill's per-iteration state backups. Data is stored as
atomic JSON (temp file + os.replace) so a killed run never corrupts the
checkpoint. High-water logic keeps the best-so-far result when a resumed
run regresses on the supplied metric.

Resume granularity is per-SEED: the engine records ``done_seeds`` after each
fully recorded seed, so a crashed sweep restarts from the next seed rather
than duplicating the whole run. Per-TRANSFORM resume would need
pipeline-level state and is deliberately out of scope here. Single-process
assumption: no locking; concurrent writers to one checkpoint file will
clobber each other.
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

    def save(self, key: str, data: dict, force: bool = False) -> bool:
        """Atomically persist a checkpoint entry.

        High-water gate: refuses to overwrite an existing entry whose
        ``metric`` is strictly better than the incoming one unless
        ``force`` is set. Returns True when the entry was written.
        """
        update = self.load() or {}
        existing = update.get(key)
        if (
            not force
            and isinstance(existing, dict)
            and isinstance(existing.get("metric"), (int, float))
            and isinstance(data.get("metric"), (int, float))
            and existing["metric"] > data["metric"]
        ):
            return False
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
        return True

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            with open(self.path, "r") as fh:
                return json.load(fh)
        except json.JSONDecodeError as exc:
            print(f"[!] Checkpoint corrupted, starting fresh: {exc}")
            return None
        except OSError:
            return None

    def remaining_seeds(self, state: dict | None, total: int) -> range:
        """Seeds still to run, given a resumed state."""
        if not state:
            return range(1, total + 1)
        done = set(state.get("done_seeds") or [])
        return (
            range(1, total + 1)
            if total <= max(done, default=0)
            else range(max(done, default=0) + 1, total + 1)
        )

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
