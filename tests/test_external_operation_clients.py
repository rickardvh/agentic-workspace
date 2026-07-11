from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import agentic_workspace.client as public_client
from agentic_workspace import (
    AWClientError,
    detect_workspace,
    external_contract_bundle,
    invoke_operation,
    negotiate_requirements,
    operation_compatibility_fingerprint,
    require_operations,
    resolve_invocation,
)
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


def test_packed_typescript_client_loads_and_enforces_shipped_constraints(tmp_path: Path) -> None:
    completed = subprocess.run(
        [shutil.which("npm") or shutil.which("npm.cmd") or "npm", "pack", "--json", "--pack-destination", str(tmp_path)],
        cwd=ROOT / "generated/workspace/typescript",
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    with tarfile.open(tmp_path / json.loads(completed.stdout)[0]["filename"]) as archive:
        archive.extractall(tmp_path, filter="data")
    script = "import {invokeOperation} from './package/src/client.mjs'; try { invokeOperation('delegation-outcome.append',{delegation_target:'',task_class:'',outcome:'success'},{target:'.',allowRuntimeBacked:true}); } catch(e) { console.log(e.kind); }"
    loaded = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=tmp_path, text=True, capture_output=True)
    assert loaded.returncode == 0, loaded.stderr
    assert loaded.stdout.strip() == "malformed"


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


def test_contract_requirement_negotiation_distinguishes_change_classes() -> None:
    bundle = external_contract_bundle()
    operation_id, operation = next(iter(bundle["operations"].items()))
    compatible = negotiate_requirements({operation_id: operation["compatibility_fingerprint"]}, allow_runtime_backed=True)
    assert compatible["compatible"] is True
    additive = dict(operation["contract"])
    additive["future_additive_field"] = {"preserved": True}
    assert operation_compatibility_fingerprint(additive) == operation["compatibility_fingerprint"]
    breaking_contract = dict(operation["contract"])
    breaking_contract["output"] = {"kind": "breaking"}
    breaking_fingerprint = operation_compatibility_fingerprint(breaking_contract)
    assert breaking_fingerprint != operation["compatibility_fingerprint"]
    breaking = negotiate_requirements({operation_id: breaking_fingerprint}, allow_runtime_backed=True)
    assert breaking == {
        "compatible": False,
        "requirements": [{"operation": operation_id, "status": "incompatible", "reason": "operation fingerprint mismatch"}],
    }
    missing = negotiate_requirements({"does.not.exist": None})
    assert missing["requirements"][0]["status"] == "missing"
    runtime_backed = negotiate_requirements({operation_id: None})
    assert runtime_backed["requirements"][0]["status"] == "runtime-backed"
    script = f"""
import {{ negotiateRequirements, operationCompatibilityFingerprint, externalContractBundle }} from './generated/workspace/typescript/src/client.mjs';
const operation = externalContractBundle().operations[{json.dumps(operation_id)}];
console.log(JSON.stringify([negotiateRequirements({{{json.dumps(operation_id)}: null}}).requirements[0].status, negotiateRequirements({{'does.not.exist': null}}).requirements[0].status, operationCompatibilityFingerprint(operation.contract) === operation.compatibility_fingerprint]));
"""
    result = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["runtime-backed", "missing", True]


def test_schema_compatibility_distinguishes_optional_addition_from_breaking_change(monkeypatch) -> None:
    bundle = external_contract_bundle()
    operation_id, operation = next(iter(bundle["operations"].items()))
    requirement = {"compatibility_surface": copy.deepcopy(operation["compatibility_surface"])}
    additive = copy.deepcopy(bundle)
    schema_name = operation["schemas"][0]
    schema = additive["operations"][operation_id]["compatibility_surface"]["schemas"][schema_name]
    schema.setdefault("properties", {})["future_optional"] = {"type": "string"}
    monkeypatch.setattr(public_client, "external_contract_bundle", lambda: additive)
    assert negotiate_requirements({operation_id: requirement}, allow_runtime_backed=True)["compatible"] is True
    breaking = copy.deepcopy(bundle)
    changed = breaking["operations"][operation_id]["compatibility_surface"]["schemas"][schema_name]
    optional = next(name for name in changed.get("properties", {}) if name not in changed.get("required", []))
    del changed["properties"][optional]
    monkeypatch.setattr(public_client, "external_contract_bundle", lambda: breaking)
    assert negotiate_requirements({operation_id: requirement}, allow_runtime_backed=True)["compatible"] is False


def test_requirement_matrix_reports_unsupported(monkeypatch) -> None:
    bundle = copy.deepcopy(external_contract_bundle())
    operation_id, operation = next(iter(bundle["operations"].items()))
    operation["external_consumption"]["status"] = "target-specific"
    monkeypatch.setattr(public_client, "external_contract_bundle", lambda: bundle)
    assert negotiate_requirements({operation_id: None})["requirements"][0]["status"] == "unsupported"


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
        (1, "{}", "", "malformed"),
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


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "wrong", "path": "x", "record_count": 1, "recorded": {}},
        {"kind": "agentic-workspace/delegation-outcomes/v1", "path": "x", "record_count": 0, "recorded": {}},
    ],
)
def test_python_and_typescript_reject_same_invalid_result(payload: dict[str, object], tmp_path: Path) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text("[workspace]\nenabled = true\n", encoding="utf-8")
    values = {"delegation_target": "fixture", "task_class": "parity", "outcome": "success"}
    with pytest.raises(AWClientError) as python_error:
        invoke_operation(
            "delegation-outcome.append",
            values,
            target=tmp_path,
            invocation=[sys.executable, "-c", f"print({json.dumps(json.dumps(payload))})"],
            allow_runtime_backed=True,
        )
    script = f"""
import {{ invokeOperation }} from './generated/workspace/typescript/src/client.mjs';
try {{ invokeOperation('delegation-outcome.append', {json.dumps(values)}, {{ target: {json.dumps(str(tmp_path))}, invocation: ['node', '-e', {json.dumps("console.log(" + json.dumps(json.dumps(payload)) + ")")}], allowRuntimeBacked: true }}); }} catch (error) {{ console.log(error.kind); }}
"""
    result = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True)
    assert python_error.value.kind == "malformed"
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "malformed"
