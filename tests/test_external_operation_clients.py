from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _python_client():
    path = ROOT / "generated/workspace/python/client.py"
    spec = importlib.util.spec_from_file_location("generated_external_client", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.files = lambda _package: ROOT / "generated/workspace/python"
    return module


def test_python_client_negotiates_and_invokes_json() -> None:
    client = _python_client()
    profile = json.loads((ROOT / "generated/workspace/python/external_consumer_profile.json").read_text(encoding="utf-8"))
    candidate = next(entry for entry in profile["operations"] if entry["external_consumption"]["status"] != "internal")
    client.require_operations([candidate["id"]], allow_runtime_backed=True)
    payload = client.invoke_json(
        ["summary"],
        target=ROOT,
        executable=[sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")],
    )
    assert payload


def test_python_client_fails_closed_for_unknown_operation() -> None:
    with pytest.raises(ValueError, match="unknown"):
        _python_client().require_operations(["does.not.exist"])


def test_typescript_client_public_export_reads_profile() -> None:
    script = "import { externalConsumerProfile } from './generated/workspace/typescript/src/client.mjs'; console.log(externalConsumerProfile().schema_version);"
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "agentic-workspace/external-consumer-profile/v1"
