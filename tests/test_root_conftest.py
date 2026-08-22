"""Root conftest mechanism: the repo root is on sys.path so `import modules`
resolves regardless of how pytest was invoked or where the venv came from.
"""

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent.parent)


def test_repo_root_is_on_sys_path():
    assert ROOT in sys.path[:3]


def test_modules_package_importable():
    import modules

    assert modules.__file__ is not None
    assert Path(modules.__file__).parent.parent == Path(ROOT)
