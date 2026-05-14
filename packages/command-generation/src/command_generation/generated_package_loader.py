from __future__ import annotations

import importlib.util
import json
import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any


def load_generated_cli_package(
    *,
    bundled_module: str,
    generated_root: str,
    module_name: str,
) -> ModuleType:
    try:
        return import_module(bundled_module)
    except (ImportError, ModuleNotFoundError, ValueError):
        pass

    relative_init = Path(generated_root) / "generated_cli_package" / "__init__.py"
    for parent in Path(__file__).resolve().parents:
        candidate = parent / relative_init
        if candidate.is_file():
            spec = importlib.util.spec_from_file_location(module_name, candidate)
            if spec is None or spec.loader is None:
                break
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
    raise ModuleNotFoundError(f"{generated_root}/generated_cli_package is unavailable")


def load_generated_cli_package_module(
    *,
    bundled_module: str,
    generated_root: str,
    file_name: str,
    module_name: str,
) -> ModuleType:
    try:
        return import_module(bundled_module)
    except (ImportError, ModuleNotFoundError, ValueError):
        pass

    package = load_generated_cli_package(
        bundled_module="",
        generated_root=generated_root,
        module_name=module_name.rsplit(".", 1)[0] if "." in module_name else f"{module_name}_package",
    )
    package_name = package.__name__
    relative_path = Path(generated_root) / "generated_cli_package" / file_name
    for parent in Path(__file__).resolve().parents:
        candidate = parent / relative_path
        if candidate.is_file():
            submodule_name = f"{package_name}.{Path(file_name).stem}"
            spec = importlib.util.spec_from_file_location(submodule_name, candidate)
            if spec is None or spec.loader is None:
                break
            module = importlib.util.module_from_spec(spec)
            sys.modules[submodule_name] = module
            spec.loader.exec_module(module)
            return module
    raise ModuleNotFoundError(f"{generated_root}/generated_cli_package/{file_name} is unavailable")


def _load_module_from_init(init_path: Path, module_name: str) -> ModuleType | None:
    spec = importlib.util.spec_from_file_location(module_name, init_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _entrypoints_from_package(package_payload: dict[str, Any]) -> set[str]:
    entrypoints: set[str] = set()
    for target in package_payload.get("targets", []):
        if isinstance(target, dict):
            entrypoints.update(str(entrypoint) for entrypoint in target.get("entrypoints", []) if isinstance(entrypoint, str))
    return entrypoints


def _candidate_generated_package_dirs() -> list[Path]:
    candidates: list[Path] = []
    for parent in Path(__file__).resolve().parents:
        generated_root = parent / "generated" / "python"
        if generated_root.is_dir():
            candidates.extend(sorted(generated_root.glob("*/generated_cli_package")))
    for path_entry in sys.path:
        if not path_entry:
            continue
        root = Path(path_entry)
        if not root.is_dir():
            continue
        candidates.extend(sorted(root.glob("*/_generated_cli_package_impl")))
    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(candidate)
    return unique


def load_generated_cli_package_for_entrypoint(entrypoint: str) -> ModuleType:
    normalized_entrypoint = Path(entrypoint.replace("\\", "/")).name
    for package_dir in _candidate_generated_package_dirs():
        command_package_path = package_dir / "command_package.json"
        init_path = package_dir / "__init__.py"
        if not command_package_path.is_file() or not init_path.is_file():
            continue
        try:
            package_payload = json.loads(command_package_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if normalized_entrypoint not in _entrypoints_from_package(package_payload):
            continue
        module_name = "_command_generation_entrypoint_" + normalized_entrypoint.replace("-", "_")
        module = _load_module_from_init(init_path, module_name)
        if module is not None:
            return module
    raise ModuleNotFoundError(f"generated CLI package for entrypoint {normalized_entrypoint!r} is unavailable")


def load_generated_cli_module_for_entrypoint(entrypoint: str, module_file: str) -> ModuleType:
    package = load_generated_cli_package_for_entrypoint(entrypoint)
    module_stem = Path(module_file).stem
    return import_module(f"{package.__name__}.{module_stem}")
