"""Pytest bootstrap: make the repo root importable regardless of how pytest was invoked.

Without this, `import modules` only resolves when the project venv is active
AND correctly relocated; a stale/moved .venv silently falls back to a system
pytest and produces mass collection errors (seen 2026-08 after the checkout
moved into red-teaming/).
"""

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
