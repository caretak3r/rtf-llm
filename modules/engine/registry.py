from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.engine.base import Transform


class TransformRegistryMeta(type):
    registry: dict[str, type[Transform]] = {}

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        transform_id = namespace.get("id")
        if isinstance(transform_id, str):
            if transform_id in mcs.registry:
                raise ValueError(f"Duplicate transform id: {transform_id!r}")
            mcs.registry[transform_id] = cls
        return cls


def register_transform(transform_id: str):
    def decorator(cls: type[Transform]) -> type[Transform]:
        if transform_id in TransformRegistryMeta.registry:
            raise ValueError(f"Duplicate transform id: {transform_id!r}")
        cls.id = transform_id
        TransformRegistryMeta.registry[transform_id] = cls
        return cls

    return decorator


def discover_transforms(package_path: str | None = None) -> dict[str, type[Transform]]:
    if package_path is None:
        import modules.engine.transforms as transforms_pkg

        _walk_package(transforms_pkg, "modules.engine.transforms")
    return dict(TransformRegistryMeta.registry)


def _walk_package(package, package_name: str) -> None:
    for _, modname, is_pkg in pkgutil.walk_packages(
        package.__path__, package_name + ".", onerror=lambda _: None
    ):
        if not is_pkg:
            try:
                importlib.import_module(modname)
            except ImportError as exc:
                print(f"[!] registry skipped {modname}: {exc}")


def all_transforms() -> dict[str, type[Transform]]:
    return dict(TransformRegistryMeta.registry)
