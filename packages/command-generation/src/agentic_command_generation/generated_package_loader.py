from __future__ import annotations

import importlib.util
import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType


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
