from __future__ import annotations

import importlib.util
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
    except (ImportError, ModuleNotFoundError):
        pass

    relative_init = Path(generated_root) / "generated_cli_package" / "__init__.py"
    for parent in Path(__file__).resolve().parents:
        candidate = parent / relative_init
        if candidate.is_file():
            spec = importlib.util.spec_from_file_location(module_name, candidate)
            if spec is None or spec.loader is None:
                break
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ModuleNotFoundError(f"{generated_root}/generated_cli_package is unavailable")
