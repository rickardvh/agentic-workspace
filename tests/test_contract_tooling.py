from __future__ import annotations

import importlib.util
from pathlib import Path


def test_contract_tooling_check_passes() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main([]) == 0
