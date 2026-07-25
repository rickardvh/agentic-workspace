from __future__ import annotations

import importlib.util
from pathlib import Path


def test_composed_operation_scenario_matrix_is_release_gate_ready() -> None:
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_composed_operation_scenarios.py"
    spec = importlib.util.spec_from_file_location("composed_operation_scenarios", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.validate_matrix(module.load_matrix()) == []
