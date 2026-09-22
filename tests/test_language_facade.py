"""Structural façade drift belongs here; native owner behavior remains elsewhere."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_language_facade", ROOT / "scripts/check/check_language_facade.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
check_node, check_python = checker.check_node, checker.check_python


def test_public_facade_envelopes_and_drift_rejection(shared_core_binary):
    contract = json.loads((ROOT / "src/core/contracts/source_decision_contract.json").read_text())["language_facade"]
    check_python(contract)
    check_node(contract, ROOT / "src/cli/typescript/native/operating.mjs", shared_core_binary)
    drift = copy.deepcopy(contract)
    drift["operations"][0]["envelope"] = {"invoke": "$context"}
    with pytest.raises(AssertionError):
        check_python(drift)
    with pytest.raises(AssertionError):
        check_node(drift, ROOT / "src/cli/typescript/native/operating.mjs", shared_core_binary)
    drift = copy.deepcopy(contract)
    drift["operations"].pop()
    with pytest.raises(AssertionError):
        check_python(drift)
    with pytest.raises(AssertionError):
        check_node(drift, ROOT / "src/cli/typescript/native/operating.mjs", shared_core_binary)
