from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import agentic_workspace.client as public_client
from agentic_workspace import AWClientError, detect_workspace, invoke_operation, require_operations, resolve_invocation
from agentic_workspace.generated_operations import config_report, delegation_outcome_append

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


def test_typescript_client_fails_closed_and_detects_workspace() -> None:
    script = """
import { AWClientError, detectWorkspace, requireOperations } from './generated/workspace/typescript/src/client.mjs';
const state = detectWorkspace('.');
let kind = '';
try { requireOperations(['does.not.exist']); } catch (error) { if (error instanceof AWClientError) kind = error.kind; }
console.log(JSON.stringify({ status: state.status, kind }));
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"status": "enabled", "kind": "incompatible"}


def test_typescript_invokes_same_schema_valid_operation_as_python() -> None:
    script = f"""
import {{ invokeOperation }} from './generated/workspace/typescript/src/client.mjs';
const payload = invokeOperation('config.report', {{}}, {{ target: {json.dumps(str(ROOT))}, invocation: [{json.dumps(sys.executable)}, {json.dumps(str(ROOT / "scripts/run_agentic_workspace.py"))}], allowRuntimeBacked: true }});
console.log(JSON.stringify({{ kind: payload.kind, additivePreserved: Object.keys(payload).length > 4 }}));
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"kind": "agentic-workspace/config-tiny/v1", "additivePreserved": True}


def test_public_python_client_detects_and_resolves_workspace(tmp_path: Path) -> None:
    assert detect_workspace(tmp_path)["status"] == "absent"
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('[workspace]\ncli_invoke = "uv run agentic-workspace"\n', encoding="utf-8")
    assert detect_workspace(tmp_path)["status"] == "enabled"
    assert resolve_invocation(tmp_path) == ["uv", "run", "agentic-workspace"]


def test_public_requirement_negotiation_rejects_unknown_status() -> None:
    with pytest.raises(AWClientError) as exc:
        require_operations(["does.not.exist"])
    assert exc.value.kind == "incompatible"


def test_public_operation_client_invokes_by_operation_identity() -> None:
    payload = invoke_operation(
        "config.report",
        {},
        target=ROOT,
        invocation=[sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")],
        allow_runtime_backed=True,
    )
    assert payload["kind"] == "agentic-workspace/config-tiny/v1"


def test_generated_operation_specific_wrapper_uses_public_contract() -> None:
    payload = config_report(
        {},
        target=ROOT,
        invocation=[sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")],
    )
    assert payload["kind"] == "agentic-workspace/config-tiny/v1"
    assert callable(delegation_outcome_append)


def test_public_client_classifies_disabled_and_invocation_unavailable(tmp_path: Path) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text("[workspace]\nenabled = false\n", encoding="utf-8")
    with pytest.raises(AWClientError) as disabled:
        invoke_operation("config.report", {}, target=tmp_path, allow_runtime_backed=True)
    assert disabled.value.kind == "disabled"
    config.write_text("[workspace]\nenabled = true\n", encoding="utf-8")
    with pytest.raises(AWClientError) as unavailable:
        invoke_operation("config.report", {}, target=tmp_path, invocation=[str(tmp_path / "missing")], allow_runtime_backed=True)
    assert unavailable.value.kind == "invocation-unavailable"


@pytest.mark.parametrize(
    ("returncode", "stdout", "stderr", "expected"),
    [
        (0, "[]", "", "malformed"),
        (0, "not-json", "", "malformed"),
        (2, '{"status":"rejected"}', "", "rejected"),
        (1, '{"status":"failed"}', "", "failed"),
    ],
)
def test_public_client_classifies_result_and_failure_envelopes(
    monkeypatch, returncode: int, stdout: str, stderr: str, expected: str
) -> None:
    monkeypatch.setattr(
        public_client.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr),
    )
    with pytest.raises(AWClientError) as error:
        invoke_operation("config.report", {}, target=ROOT, allow_runtime_backed=True)
    assert error.value.kind == expected


def test_python_and_typescript_mutation_operation_parity(tmp_path: Path) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text("[workspace]\nenabled = true\n", encoding="utf-8")
    values = {"delegation_target": "fixture", "task_class": "parity", "outcome": "success"}
    python_payload = invoke_operation(
        "delegation-outcome.append",
        values,
        target=tmp_path,
        invocation=[sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")],
        allow_runtime_backed=True,
    )
    script = f"""
import {{ invokeOperation }} from './generated/workspace/typescript/src/client.mjs';
const payload = invokeOperation('delegation-outcome.append', {json.dumps(values)}, {{ target: {json.dumps(str(tmp_path))}, invocation: [{json.dumps(sys.executable)}, {json.dumps(str(ROOT / "scripts/run_agentic_workspace.py"))}], allowRuntimeBacked: true }});
console.log(JSON.stringify(payload));
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    typescript_payload = json.loads(completed.stdout)
    assert python_payload["kind"] == typescript_payload["kind"] == "agentic-workspace/delegation-outcomes/v1"
    assert python_payload["recorded"]["outcome"] == typescript_payload["recorded"]["outcome"] == "success"
