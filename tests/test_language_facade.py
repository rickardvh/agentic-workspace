"""Structural façade drift belongs here; native owner behavior remains elsewhere."""

import copy
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_language_facade", ROOT / "src/tooling/check/check_language_facade.py")
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


def test_source_public_import_is_native_and_fails_closed(tmp_path, shared_core_binary):
    script = """
import importlib.util, json, sys
import agentic_workspace as aw
for module in ("decision", "contract_tooling", "static_read_profile", "review_stack_topology"):
    assert importlib.util.find_spec("agentic_workspace." + module) is None
assert not any(name in sys.modules for name in (
    'agentic_workspace.client', 'aw_maintainer.native_conformance',
    'agentic_workspace.workspace_runtime_core', 'agentic_workspace.modules'))
assert not hasattr(aw, 'invoke_operation')
assert not hasattr(aw, 'compile_source_decision')
print(json.dumps(aw.start({'target': '.', 'task': 'Inspect this consumer'})))
"""
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src/cli/python"), "AGENTIC_WORKSPACE_CORE_BINARY": str(shared_core_binary)}
    result = subprocess.run([sys.executable, "-c", script], cwd=tmp_path, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "decision_packet" in json.loads(result.stdout)
    environment["AGENTIC_WORKSPACE_CORE_BINARY"] = str(tmp_path / "missing-core")
    rejected = subprocess.run([sys.executable, "-c", script], cwd=tmp_path, env=environment, capture_output=True, text=True)
    assert rejected.returncode != 0
    assert "core is unavailable" in rejected.stderr
    assert not (tmp_path / ".agentic-workspace").exists()
