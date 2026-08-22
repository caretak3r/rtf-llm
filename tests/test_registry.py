"""Registry behavior: silent-skip warning for broken transform modules
(plan 050 Item 9) and clean discovery of valid siblings."""

import importlib
import uuid

from modules.engine.registry import TransformRegistryMeta, _walk_package


def test_walk_package_warns_on_broken_import_and_registers_valid_sibling(
    tmp_path, monkeypatch, capsys
):
    pkg_name = "tmp_reg_pkg_" + uuid.uuid4().hex[:8]
    pkg_dir = tmp_path / pkg_name
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "broken.py").write_text("raise ImportError('boom-typo-module')\n")
    tid = f"{pkg_name}/valid"
    (pkg_dir / "valid.py").write_text(
        "from modules.engine.registry import register_transform\n"
        "\n"
        f"@register_transform({tid!r})\n"
        "class _Valid:\n"
        f"    id = {tid!r}\n"
        "\n"
        "    def transform(self, ctx): ...\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    pkg = importlib.import_module(pkg_name)
    _walk_package(pkg, pkg_name)

    out = capsys.readouterr().out
    assert "[!] registry skipped" in out
    assert f"{pkg_name}.broken" in out
    assert "boom-typo-module" in out
    assert tid in TransformRegistryMeta.registry

    # Do not leak the tmp id into the shared registry for other tests.
    del TransformRegistryMeta.registry[tid]
