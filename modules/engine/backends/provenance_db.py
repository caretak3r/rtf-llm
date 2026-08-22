#!/usr/bin/env python3
"""SQLite provenance DB for engine findings.

Stores every finding from a run along with its provenance links
(via_technique / via_target), hosts checkpoints, and computes run-to-run
diffs. stdlib sqlite3 only; the database file doubles as the run
artifact registry waiting for the session artifact layout (b14).
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       TEXT    NOT NULL,
    technique    TEXT    NOT NULL,
    via_technique TEXT,
    via_target   TEXT,
    prompt       TEXT,
    status       TEXT    NOT NULL,
    score        REAL,
    created_at   REAL    NOT NULL
);
CREATE TABLE IF NOT EXISTS checkpoints (
    run_id     TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_findings_run ON findings(run_id);
"""


class ProvenanceDB:
    """Thread-safe-by-convention wrapper over the sqlite findings store."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        if self.db_path.parent != Path(""):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def record_finding(
        self,
        run_id: str,
        technique: str,
        via_technique: str | None,
        via_target: str | None,
        prompt: str | None,
        status: str,
        score: float | None,
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO findings"
            " (run_id, technique, via_technique, via_target, prompt, status, score, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, technique, via_technique, via_target, prompt, status, score, time.time()),
        )
        self.conn.commit()
        return cur.lastrowid

    def findings_for_run(self, run_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, technique, via_technique, via_target, status, score, prompt"
            " FROM findings WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        cols = ["id", "technique", "via_technique", "via_target", "status", "score", "prompt"]
        return [dict(zip(cols, row)) for row in rows]

    def runs(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT run_id FROM findings ORDER BY created_at"
        ).fetchall()
        return [r[0] for r in rows]

    def save_checkpoint(self, run_id: str, payload: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO checkpoints (run_id, payload, updated_at) VALUES (?, ?, ?)",
            (run_id, json.dumps(payload), time.time()),
        )
        self.conn.commit()

    def load_checkpoint(self, run_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT payload FROM checkpoints WHERE run_id = ?", (run_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def diff(self, run_a: str, run_b: str) -> dict:
        """Return findings present in run_b but not run_a (added) and vice versa."""

        def key(f: dict) -> tuple:
            return (f["technique"], f["status"], f.get("via_technique"), f.get("via_target"))

        a = {key(f) for f in self.findings_for_run(run_a)}
        b = {key(f) for f in self.findings_for_run(run_b)}
        return {
            "run_a": run_a,
            "run_b": run_b,
            "added": [f for f in self.findings_for_run(run_b) if key(f) not in a],
            "removed": [f for f in self.findings_for_run(run_a) if key(f) not in b],
            "unchanged": sum(1 for f in self.findings_for_run(run_b) if key(f) in a),
        }

    def close(self) -> None:
        self.conn.close()
