from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from tests.test_workspace_proof_cli import _host_runtime_for_review_ref, _write_independent_review_host_result

import agentic_workspace.client as public_client
from agentic_workspace import (
    AWClientError,
    detect_workspace,
    external_contract_bundle,
    external_readiness_report,
    invoke_operation,
    negotiate_requirements,
    operation_compatibility_fingerprint,
    require_operations,
    resolve_invocation,
)
from agentic_workspace.config import WorkspaceUsageError
from agentic_workspace.generated_operations import (
    assignment_admit,
    assignment_export,
    assignment_import,
    assignment_integrate,
    assignment_override,
    config_report,
    correction_event_prune_compact,
    correction_event_query,
    correction_event_submit,
    delegation_outcome_append,
)
from agentic_workspace.workspace_runtime_proof import (
    INDEPENDENT_REVIEW_HOST_RESULT_DIR,
    INDEPENDENT_REVIEW_HOST_RESULT_INDEX_KIND,
    INDEPENDENT_REVIEW_RESULT_DIR,
    INDEPENDENT_REVIEW_RESULT_INDEX_KIND,
    _independent_review_scope_digest,
    admit_independent_review_result_operation,
    record_trusted_independent_review_result,
)

ROOT = Path(__file__).resolve().parents[1]


def _independent_review_host_result_fixture(tmp_path: Path, *, changed_paths: list[str] | None = None, **overrides: object):
    changed = changed_paths or ["src/feature.py"]
    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "separate-actor",
        "assignment_id": str(overrides.get("assignment_id") or "assign-1"),
        "assignment_revision": str(overrides.get("assignment_revision") or "assignment-rev-1"),
        "proof_subject_revision": str(overrides.get("proof_subject_revision") or "proof-rev-1"),
        "review_revision": str(overrides.get("review_revision") or "review-rev-1"),
        "scope_digest": _independent_review_scope_digest(changed),
        "changed_paths": changed,
        "implementer": {"actor_id": "codex-implementer", "provider": "openai", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "github", "role": "reviewer", "fresh_context": True},
        "reviewed_at": "2026-07-31T00:00:00Z",
        "expires_at": str(overrides.get("expires_at") or "2099-01-01T00:00:00Z"),
        "custody": {
            "producer": "github-review-adapter",
            "trusted_channel": "github-review-webhook",
            "authority_ref": "github-pr-review:1",
        },
    }
    if overrides.get("revoked_at"):
        review_result["admission_revoked_at"] = str(overrides["revoked_at"])
    if overrides.get("verdict_expires_at"):
        review_result["admission_expires_at"] = str(overrides["verdict_expires_at"])
    host_result_ref = _write_independent_review_host_result(tmp_path, review_result)
    host_result_id = host_result_ref.removeprefix("independent-review-host-result:")
    host_result = json.loads((tmp_path / INDEPENDENT_REVIEW_HOST_RESULT_DIR / f"{host_result_id}.json").read_text(encoding="utf-8"))

    def resolver(ref: str) -> dict[str, object]:
        if ref != host_result_ref:
            raise AssertionError(f"unexpected host result ref: {ref}")
        return host_result

    return host_result_ref, host_result, resolver


def _readiness_conformance_evidence(profile: dict, operation: dict, *, status: str = "passed") -> dict:
    return {
        "kind": "agentic-workspace/external-operation-conformance-result/v1",
        "status": status,
        "operation_id": operation["id"],
        "operation_fingerprint": operation["operation_compatibility"]["fingerprint"],
        "profile_fingerprint": profile["compatibility"]["fingerprint"],
        "runtime_exception_revision": "#2044@accepted",
        "transports": {
            "cli-json": {"status": "passed"},
            "python": {"status": "passed"},
            "typescript": {"status": "passed"},
            "vendor-neutral": {"status": "passed"},
        },
        "cases": {
            "absent": {"status": "passed"},
            "disabled": {"status": "passed"},
            "incompatible": {"status": "passed"},
            "malformed": {"status": "passed"},
            "retryable": {"status": "passed"},
            "additive-field": {"status": "passed"},
            "mutation-applied": {"status": "passed"},
            "mutation-noop": {"status": "passed"},
            "mutation-rejected": {"status": "passed"},
            "mutation-failed": {"status": "passed"},
        },
    }


def _readiness_conformance_receipt_store(profile: dict, operation: dict, *, status: str = "passed") -> dict:
    receipt = {
        **_readiness_conformance_evidence(profile, operation, status=status),
        "kind": "agentic-workspace/external-operation-conformance-receipt/v1",
        "receipt_ref": f"external-conformance:{operation['id']}:test",
        "executed_at": "2026-07-26T20:00:00Z",
        "custody": {
            "operation_id": "external-operation-conformance.run",
            "producer": "agentic-workspace.operation-conformance-runner",
            "trusted_channel": "producer-owned-test-fixture",
        },
    }
    return {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": [receipt]}


def _published_readiness_receipt_store(store: dict) -> dict:
    payload = copy.deepcopy(store)
    publication_payload = {key: value for key, value in payload.items() if key != "mirror_publication"}
    digest = hashlib.sha256(json.dumps(publication_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    payload["mirror_publication"] = {
        "kind": "agentic-workspace/external-operation-conformance-mirror-publication/v1",
        "status": "published",
        "payload_digest": f"sha256:{digest}",
    }
    return payload


def test_external_readiness_report_fails_closed_for_runtime_backed_operations() -> None:
    report = external_readiness_report(["assignment.export", "does.not.exist"])
    assert report["status"] == "not-ready"
    runtime_backed, unknown = report["excluded_operations"]
    assert runtime_backed["id"] == "assignment.export"
    assert runtime_backed["status"] == "runtime-backed"
    assert runtime_backed["evidence"]["conformance_refs"]
    assert runtime_backed["evidence"]["conformance_result"] == {}
    assert "executed-conformance-receipt" in runtime_backed["missing_evidence"]
    assert runtime_backed["evidence"]["runtime_exceptions"]
    assert unknown["id"] == "does.not.exist"
    assert "released-python-resource" in unknown["missing_evidence"]


def test_external_readiness_report_requires_released_client_and_conformance_evidence(monkeypatch) -> None:
    profile = copy.deepcopy(public_client.external_consumer_profile())
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "assignment.export")
    candidate["external_consumption"] = {"status": "supported"}
    candidate["operation_resources"]["typescript"]["exists"] = False
    candidate["conformance"] = []
    monkeypatch.setattr(public_client, "external_consumer_profile", lambda: profile)

    report = external_readiness_report(["assignment.export"])

    assert report["status"] == "not-ready"
    excluded = report["excluded_operations"][0]
    assert set(excluded["missing_evidence"]) == {
        "released-typescript-resource",
        "conformance-reference",
        "executed-conformance-receipt",
    }
    assert excluded["evidence"]["conformance_result"] == {}


def test_external_readiness_report_requires_current_executed_cross_transport_conformance(monkeypatch) -> None:
    profile = copy.deepcopy(public_client.external_consumer_profile())
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "assignment.export")
    candidate["external_consumption"]["status"] = "supported"
    monkeypatch.setattr(public_client, "external_consumer_profile", lambda: profile)
    monkeypatch.setattr(
        public_client, "external_operation_conformance_receipts", lambda: _readiness_conformance_receipt_store(profile, candidate)
    )

    report = external_readiness_report(["assignment.export"])

    assert report["status"] == "ready"
    assert report["supported_operations"] == ["assignment.export"]
    assert report["excluded_operations"] == []

    stale_profile = copy.deepcopy(profile)
    stale_profile["compatibility"]["fingerprint"] = "sha256:stale"
    monkeypatch.setattr(public_client, "external_consumer_profile", lambda: stale_profile)
    monkeypatch.setattr(
        public_client,
        "external_operation_conformance_receipts",
        lambda: _readiness_conformance_receipt_store(profile, candidate),
    )

    stale_report = external_readiness_report(["assignment.export"])

    assert stale_report["status"] == "not-ready"
    assert "executed-conformance-receipt" in stale_report["excluded_operations"][0]["missing_evidence"]


def test_external_readiness_report_ignores_inline_profile_conformance_evidence(monkeypatch) -> None:
    profile = copy.deepcopy(public_client.external_consumer_profile())
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "assignment.export")
    candidate["external_consumption"]["status"] = "supported"
    candidate["conformance_evidence"] = _readiness_conformance_evidence(profile, candidate)
    monkeypatch.setattr(public_client, "external_consumer_profile", lambda: profile)
    monkeypatch.setattr(
        public_client,
        "external_operation_conformance_receipts",
        lambda: {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": []},
    )

    report = external_readiness_report(["assignment.export"])

    assert report["status"] == "not-ready"
    assert "executed-conformance-receipt" in report["excluded_operations"][0]["missing_evidence"]


def test_packaged_conformance_receipt_store_fails_closed_without_full_external_evidence() -> None:
    store = public_client.external_operation_conformance_receipts()
    assert store["kind"] == "agentic-workspace/external-operation-conformance-receipt-store/v1"
    assert store["status"] == "recorded"
    receipts = {receipt["operation_id"]: receipt for receipt in store["receipts"]}
    assert {"config.report", "delegation-outcome.append"}.issubset(receipts)
    config_receipt = receipts["config.report"]
    assert config_receipt["status"] == "failed"
    assert config_receipt["transports"]["vendor-neutral"]["status"] == "passed"
    assert config_receipt["cases"]["absent"]["status"] == "not-run"
    assert config_receipt["freshness"]["strategy"] == "revision-bound-explicit-revocation"
    delegation_receipt = receipts["delegation-outcome.append"]
    assert delegation_receipt["status"] == "failed"
    assert delegation_receipt["runtime_exception_revision"] == ""
    assert delegation_receipt["runtime_exception_admission"]["reason"] == "missing-operation-specific-runtime-exception-revision"
    assert delegation_receipt["transports"]["vendor-neutral"]["status"] == "not-run"
    assert delegation_receipt["operation_result_evidence"]


def test_external_readiness_report_rejects_explicitly_revoked_and_superseded_receipts(monkeypatch) -> None:
    profile = copy.deepcopy(public_client.external_consumer_profile())
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "assignment.export")
    candidate["external_consumption"]["status"] = "supported"
    base_receipt = _readiness_conformance_receipt_store(profile, candidate)["receipts"][0]
    monkeypatch.setattr(public_client, "external_consumer_profile", lambda: profile)
    for marker in ({"revoked_at": "2026-07-29T00:00:00Z"}, {"superseded_by": "newer"}, {"status": "stale"}):
        stale = {**base_receipt, **marker}
        monkeypatch.setattr(
            public_client,
            "external_operation_conformance_receipts",
            lambda stale=stale: {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": [stale]},
        )
        report = external_readiness_report(["assignment.export"])
        assert report["status"] == "not-ready"
        assert "executed-conformance-receipt" in report["excluded_operations"][0]["missing_evidence"]
    expired_only = {**base_receipt, "expires_at": "2000-01-01T00:00:00Z"}
    monkeypatch.setattr(
        public_client,
        "external_operation_conformance_receipts",
        lambda: {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": [expired_only]},
    )
    report = external_readiness_report(["assignment.export"])
    assert report["status"] == "not-ready"
    assert "executed-conformance-receipt" in report["excluded_operations"][0]["missing_evidence"]


def test_generated_clients_reject_expired_conformance_receipts(monkeypatch, tmp_path: Path) -> None:
    profile = copy.deepcopy(json.loads((ROOT / "generated/workspace/python/external_consumer_profile.json").read_text(encoding="utf-8")))
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "assignment.export")
    candidate["external_consumption"]["status"] = "supported"
    receipt_store = _published_readiness_receipt_store(_readiness_conformance_receipt_store(profile, candidate))
    receipt_store["receipts"][0]["expires_at"] = "2000-01-01T00:00:00Z"

    python_client = _python_client()
    monkeypatch.setattr(python_client, "external_consumer_profile", lambda: profile)
    monkeypatch.setattr(python_client, "external_operation_conformance_receipts", lambda: receipt_store)
    python_report = python_client.external_readiness_report(["assignment.export"])
    assert python_report["status"] == "not-ready"
    assert "executed-conformance-receipt" in python_report["excluded_operations"][0]["missing_evidence"]

    package_root = tmp_path / "typescript"
    shutil.copytree(ROOT / "generated/workspace/typescript", package_root)
    (package_root / "external_consumer_profile.json").write_text(json.dumps(profile), encoding="utf-8")
    (package_root / "external_operation_conformance_receipts.json").write_text(json.dumps(receipt_store), encoding="utf-8")
    script = (
        "import { externalReadinessReport } from './src/client.mjs';"
        "console.log(JSON.stringify(externalReadinessReport(['assignment.export'])));"
    )
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=package_root, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    typescript_report = json.loads(completed.stdout)
    assert typescript_report["status"] == "not-ready"
    assert "executed-conformance-receipt" in typescript_report["excluded_operations"][0]["missing_evidence"]


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


def test_generated_python_client_resolves_config_local_cli_invoke(tmp_path: Path) -> None:
    client = _python_client()
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    config_dir = tmp_path / ".agentic-workspace"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n',
        encoding="utf-8",
    )
    local_command = f"{Path(sys.executable).as_posix()} {(ROOT / 'scripts/run_agentic_workspace.py').as_posix()}"
    (config_dir / "config.local.toml").write_text(
        "schema_version = 1\n[workspace]\ncli_invoke = " + json.dumps(local_command) + "\n",
        encoding="utf-8",
    )

    assert client.resolve_invocation(tmp_path) == [Path(sys.executable).as_posix(), (ROOT / "scripts/run_agentic_workspace.py").as_posix()]
    payload = client.invoke_json(["config", "--verbose"], target=tmp_path)

    assert local_command in json.dumps(payload)


def test_python_client_fails_closed_for_unknown_operation() -> None:
    with pytest.raises(ValueError, match="unknown"):
        _python_client().require_operations(["does.not.exist"])


def test_typescript_client_public_export_reads_profile() -> None:
    script = "import { externalConsumerProfile } from './generated/workspace/typescript/src/client.mjs'; console.log(externalConsumerProfile().schema_version);"
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "agentic-workspace/external-consumer-profile/v1"


def test_generated_clients_share_fail_closed_readiness_contract() -> None:
    python_report = _python_client().external_readiness_report(["assignment.export", "does.not.exist"])
    script = "import { externalReadinessReport } from './generated/workspace/typescript/src/client.mjs'; console.log(JSON.stringify(externalReadinessReport(['assignment.export', 'does.not.exist'])));"
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert python_report == json.loads(completed.stdout)


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


def test_packed_python_client_loads_external_readiness_without_source_checkout(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "wheels"
    site_dir = tmp_path / "site"
    build = subprocess.run(
        [shutil.which("uv") or shutil.which("uv.exe") or "uv", "build", "--wheel", "--out-dir", str(wheel_dir)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    wheel = next(wheel_dir.glob("agentic_workspace-*.whl"))
    install = subprocess.run(
        [
            shutil.which("uv") or shutil.which("uv.exe") or "uv",
            "pip",
            "install",
            "--python",
            sys.executable,
            "--no-deps",
            "--target",
            str(site_dir),
            str(wheel),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert install.returncode == 0, install.stderr
    install_jsonschema = subprocess.run(
        [
            shutil.which("uv") or shutil.which("uv.exe") or "uv",
            "pip",
            "install",
            "--python",
            sys.executable,
            "--target",
            str(site_dir),
            "jsonschema",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert install_jsonschema.returncode == 0, install_jsonschema.stderr
    script = f"""
import json
import sys
from pathlib import Path

site = Path({str(site_dir)!r})
root = Path({str(ROOT)!r}).resolve()
sys.path = [str(site)] + [item for item in sys.path if str(root) not in str(Path(item or '.').resolve())]
import agentic_workspace

report = agentic_workspace.external_readiness_report(['does.not.exist'])
print(json.dumps({{'module': agentic_workspace.__file__, 'status': report['status'], 'missing': report['excluded_operations'][0]['missing_evidence']}}))
"""
    loaded = subprocess.run(
        [shutil.which("uv") or shutil.which("uv.exe") or "uv", "run", "--project", str(ROOT), "python", "-c", script],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert loaded.returncode == 0, loaded.stderr
    payload = json.loads(loaded.stdout)
    assert str(ROOT) not in payload["module"]
    assert payload["status"] == "not-ready"
    assert "released-python-resource" in payload["missing"]


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


def test_typescript_client_resolves_config_local_cli_invoke(tmp_path: Path) -> None:
    config_dir = tmp_path / ".agentic-workspace"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n',
        encoding="utf-8",
    )
    local_command = f"{Path(sys.executable).as_posix()} {(ROOT / 'scripts/run_agentic_workspace.py').as_posix()}"
    (config_dir / "config.local.toml").write_text(
        "schema_version = 1\n[workspace]\ncli_invoke = " + json.dumps(local_command) + "\n",
        encoding="utf-8",
    )
    script = f"""
import {{ detectWorkspace, resolveInvocation }} from './generated/workspace/typescript/src/client.mjs';
const target = {json.dumps(str(tmp_path))};
console.log(JSON.stringify({{ state: detectWorkspace(target), command: resolveInvocation(target) }}));
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["state"]["status"] == "enabled"
    assert payload["state"]["config"] == "config.local.toml"
    assert payload["command"] == [Path(sys.executable).as_posix(), (ROOT / "scripts/run_agentic_workspace.py").as_posix()]


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


def test_assignment_lifecycle_operations_are_generated_runtime_backed() -> None:
    operation_ids = [
        "assignment.export",
        "assignment.import",
        "assignment.admit",
        "assignment.reject",
        "assignment.repair",
        "assignment.reassign",
        "assignment.integrate",
        "assignment.close",
        "assignment.cleanup",
        "assignment.override",
    ]
    assert require_operations(operation_ids, allow_runtime_backed=True) is None
    statuses = {
        entry["identity"]: entry["external_consumption"]["status"]
        for entry in external_contract_bundle()["operations"].values()
        if entry["identity"] in operation_ids
    }
    assert set(statuses) == set(operation_ids)
    assert set(statuses.values()) == {"runtime-backed"}


def test_assignment_lifecycle_generated_wrappers_persist_local_artifacts(tmp_path: Path) -> None:
    from agentic_workspace import workspace_runtime_core

    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n', encoding="utf-8"
    )
    invocation = [sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")]
    assignment_gate = {
        "status": "handoff-required",
        "assignment_policy": "required-best-fit",
        "selected_target": "planner",
        "required_next_action": "prepare-assigned-handoff",
        "target_identity_ref": "target:planner@2026-07-21",
        "target_revision": "target-rev-1",
        "task_class": "mechanical-follow-through",
        "scope_class": "narrow-code-change",
        "plan_ref": ".agentic-workspace/planning/execplans/plan.plan.json",
        "plan_revision": "plan-rev-1",
        "slice_id": "slice-1",
        "slice_revision": "slice-rev-1",
        "assignment_decision_revision": "assignment-rev-1",
        "role": "implementer",
        "allowed_effects": ["repo-write"],
        "allowed_paths": ["src/feature.py"],
        "proof_obligation": {"id": "proof:feature", "revision": "proof-rev-1"},
        "stop_conditions": ["scope-expanded"],
        "mutation_baseline": "baseline-1",
    }
    assignment_policy = {"manual_transport_policy": {"value": "allowed"}}
    delegation_decision = {
        "decision": "assignment-handoff-required",
        "delegation_next_step": {
            "execution_methods": ["manual"],
            "handoff_run_id": "run-1",
            "return_schema": "delegated-return/v1",
        },
    }
    proof_receipt = {"result": "passed", "verified_by": "aw", "revision": "proof-rev-1"}
    identity = workspace_runtime_core._assignment_identity_payload(
        assignment_gate=assignment_gate,
        assignment_policy=assignment_policy,
        delegation_decision=delegation_decision,
    )
    assignment_dir = tmp_path / ".agentic-workspace/planning/assignments"
    assignment_dir.mkdir(parents=True)
    proof_dir = tmp_path / ".agentic-workspace/proof/receipts"
    proof_dir.mkdir(parents=True)
    baseline_file = tmp_path / ".agentic-workspace/planning/mutation-baseline.json"
    baseline_file.parent.mkdir(parents=True, exist_ok=True)
    proof_ref = ".agentic-workspace/proof/receipts/proof-feature.json"
    (tmp_path / proof_ref).write_text(json.dumps(proof_receipt), encoding="utf-8")
    baseline_file.write_text(json.dumps({"current_baseline": "baseline-1"}), encoding="utf-8")
    (assignment_dir / "assign-1.assignment.json").write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/planning-assignment/v1",
                "assignment_id": "assign-1",
                "current_revision": identity["revision"],
                "status": "current",
                "target_name": "planner",
                "assignment_gate": assignment_gate,
                "assignment_policy": assignment_policy,
                "delegation_decision": delegation_decision,
                "aw_proof_receipt_ref": proof_ref,
                "current_attempt": {"run_id": "run-1", "owner": "planner", "status": "handoff-prepared"},
                "accepted_result_refs": [],
            }
        ),
        encoding="utf-8",
    )
    export = assignment_export(
        {
            "assignment_id": "assign-1",
            "assignment_revision": identity["revision"],
            "target_name": "planner",
            "run_id": "run-1",
        },
        target=tmp_path,
        invocation=invocation,
    )
    imported = assignment_import(
        {
            "run_id": "run-1",
            "return_json": json.dumps(
                {"assignment_revision": identity["revision"], "target": "planner", "changed_paths": ["src/feature.py"]}
            ),
        },
        target=tmp_path,
        invocation=invocation,
    )
    blocked = assignment_integrate(
        {"run_id": "run-1"},
        target=tmp_path,
        invocation=invocation,
    )
    admitted = assignment_admit(
        {"run_id": "run-1"},
        target=tmp_path,
        invocation=invocation,
    )
    integrated = assignment_integrate(
        {"run_id": "run-1"},
        target=tmp_path,
        invocation=invocation,
    )
    override = assignment_override(
        {"assignment_id": "assign-1", "reason": "maintainer approved", "scope": "src/feature.py", "expires_at": "2026-07-23T00:00:00Z"},
        target=tmp_path,
        invocation=invocation,
    )

    assert export["status"] == "handoff-prepared"
    assert imported["status"] == "awaiting-admission"
    assert blocked["reason_code"] == "return-not-admitted"
    assert admitted["status"] == "admitted"
    assert integrated["status"] == "integrated"
    assert override["status"] == "override-recorded"
    assert (tmp_path / ".agentic-workspace/local/assignment-runs/run-1/received/awaiting-admission").is_dir()
    override_ref = next(ref for ref in override["artifact_refs"] if ref.endswith("override/override.json"))
    override_receipt = json.loads((tmp_path / override_ref).read_text())
    assert override_receipt["claim_effect"] == "downgrade-until-revalidated"
    packet_ref = next(ref for ref in export["artifact_refs"] if ref.endswith("export/packet.json"))
    packet = json.loads((tmp_path / packet_ref).read_text())
    assert packet["authority_refs"]["planning_assignment"] == ".agentic-workspace/planning/assignments/assign-1.assignment.json"
    assert "current_authorities" not in export["state"]


def test_assignment_lifecycle_public_admit_rejects_caller_authority_strings(tmp_path: Path) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n', encoding="utf-8"
    )
    invocation = [sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")]
    with pytest.raises(AWClientError) as excinfo:
        assignment_admit(
            {"run_id": "run-1", "current_authority_ref": "planning:rev", "live_mutation_baseline": "baseline-1"},
            target=tmp_path,
            invocation=invocation,
        )

    assert excinfo.value.kind == "malformed"
    assert "current_authority_ref" in excinfo.value.details["errors"][0]
    assert "live_mutation_baseline" in excinfo.value.details["errors"][0]


def test_assignment_lifecycle_public_contract_omits_caller_authority_inputs() -> None:
    authority_inputs = {
        "assignment_gate_json",
        "assignment_policy_json",
        "delegation_decision_json",
        "aw_proof_receipt_json",
        "run_state_json",
        "current_authority_ref",
        "live_mutation_baseline",
        "packet_json",
    }
    for operation in external_contract_bundle()["operations"].values():
        if not operation["identity"].startswith("assignment."):
            continue
        input_names = {entry["name"] for entry in operation["contract"]["inputs"]}
        assert not authority_inputs & input_names


def test_independent_review_import_uses_protected_host_store_and_append_preserves_indexes(tmp_path: Path) -> None:
    first_ref, _first_host, first_resolver = _independent_review_host_result_fixture(tmp_path)
    second_ref, _second_host, second_resolver = _independent_review_host_result_fixture(
        tmp_path,
        changed_paths=["src/other.py"],
        assignment_id="assign-2",
        assignment_revision="assignment-rev-2",
        proof_subject_revision="proof-rev-2",
        review_revision="review-rev-2",
    )

    with _host_runtime_for_review_ref(first_ref):
        first = record_trusted_independent_review_result(
            target_root=tmp_path,
            review_result={"host_result_ref": first_ref},
        )
        replay = record_trusted_independent_review_result(
            target_root=tmp_path,
            review_result={"host_result_ref": first_ref},
        )
    with _host_runtime_for_review_ref(second_ref):
        second = record_trusted_independent_review_result(
            target_root=tmp_path,
            review_result={"host_result_ref": second_ref},
        )
    with pytest.raises(WorkspaceUsageError, match="caller-provided independent review host result resolvers are rejected"):
        record_trusted_independent_review_result(
            target_root=tmp_path,
            review_result={"host_result_ref": first_ref},
            host_result_resolver=first_resolver,
        )

    assert replay["result_ref"] == first["result_ref"]
    host_index = json.loads((tmp_path / INDEPENDENT_REVIEW_HOST_RESULT_DIR / "index.json").read_text(encoding="utf-8"))
    trusted_index = json.loads((tmp_path / INDEPENDENT_REVIEW_RESULT_DIR / "index.json").read_text(encoding="utf-8"))
    assert host_index["kind"] == INDEPENDENT_REVIEW_HOST_RESULT_INDEX_KIND
    assert set(host_index["results"]) == {
        first_ref.removeprefix("independent-review-host-result:"),
        second_ref.removeprefix("independent-review-host-result:"),
    }
    assert trusted_index["kind"] == INDEPENDENT_REVIEW_RESULT_INDEX_KIND
    assert len(trusted_index["results"]) == 2
    assert first["status"] == "stored"
    assert second["status"] == "stored"


def test_independent_review_import_rejects_caller_written_host_file_without_resolver(tmp_path: Path) -> None:
    host_id = "caller-authored"
    host_ref = f"independent-review-host-result:{host_id}"
    host_result = {"kind": "agentic-workspace/independent-review-host-result/v1", "status": "current", "host_result_ref": host_ref}
    old_path = tmp_path / ".agentic-workspace/local/independent-review-host-results" / f"{host_id}.json"
    old_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.write_text(json.dumps(host_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(WorkspaceUsageError, match="protected host-result index"):
        record_trusted_independent_review_result(target_root=tmp_path, review_result={"host_result_ref": host_ref})

    assert not (tmp_path / INDEPENDENT_REVIEW_RESULT_DIR / "index.json").exists()


def test_assignment_admit_host_result_ref_succeeds_with_protected_host_store(tmp_path: Path) -> None:
    host_ref, _host_result, _resolver = _independent_review_host_result_fixture(tmp_path)

    with _host_runtime_for_review_ref(host_ref):
        admitted = admit_independent_review_result_operation(
            target_root=tmp_path,
            values={"host_result_ref": host_ref, "required_mode": "separate-actor"},
            changed_paths=["src/feature.py"],
        )

    assert admitted["status"] == "admitted"
    assert admitted["receipt"]["review_result"]["custody"]["host_result_ref"] == host_ref


def test_correction_event_generated_operations_store_query_and_preserve_low_authority(tmp_path: Path) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n', encoding="utf-8"
    )
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'current_target = "user-local:fast-worker"',
                "",
                "[local_memory]",
                "target_guidance_enabled = true",
                'user_guidance_root = "~/.agentic-workspace/target-guidance"',
                'correction_events_path = ".agentic-workspace/local/correction-events.json"',
                "",
                "[delegation_targets.fast_worker]",
                'target_id = "user-local:fast-worker"',
                'target_revision = "rev-1"',
                'aliases = ["fast"]',
                'revision_policy = "preserve"',
                'strength = "strong"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )
    invocation = [sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")]
    event = {
        "delivery_id": "delivery-1",
        "target_identity_ref": "fast",
        "target_revision": "rev-1",
        "task_class": "mechanical-follow-through",
        "scope_class": "narrow-code-change",
        "invariant_id": "narrow-edits",
        "behavior_class": "edit-scope",
        "desired_behavior": "Prefer narrow edits.",
        "replaced_behavior": "Broad edits.",
        "source_ref": "review-thread-1",
        "evidence_hash": "sha256:review-thread-1",
        "route_decisions": ["target-guidance", "target-suitability"],
    }
    trusted_receipt = {
        "authority": "pr-review",
        "producer_class": "human-reviewer",
        "producer_id": "reviewer-1",
        "source": "github-review",
        "source_ref": "review-thread-1",
        "status": "current",
    }
    receipt_ref = ".agentic-workspace/local/correction-authority-receipts/review-thread-1.json"
    (tmp_path / receipt_ref).parent.mkdir(parents=True)
    (tmp_path / receipt_ref).write_text(json.dumps(trusted_receipt), encoding="utf-8")

    submitted = correction_event_submit(
        {"event_json": json.dumps(event), "trusted_authority_receipt_ref": receipt_ref},
        target=tmp_path,
        invocation=invocation,
    )
    low_authority = correction_event_submit(
        {"event_json": json.dumps({**event, "delivery_id": "delivery-2", "source_ref": "agent-note-1"})},
        target=tmp_path,
        invocation=invocation,
    )
    queried = correction_event_query({}, target=tmp_path, invocation=invocation)
    compacted = correction_event_prune_compact({}, target=tmp_path, invocation=invocation)

    assert submitted["status"] == "stored"
    assert submitted["admitted_event_count"] == 1
    assert low_authority["status"] == "stored"
    assert low_authority["low_authority_event_count"] == 1
    assert low_authority["admission"]["derived_routes"]["low_authority"]
    low_authority_ids = set(low_authority["admission"]["derived_routes"]["low_authority"])
    assert low_authority_ids.isdisjoint(low_authority["admission"]["derived_routes"]["target_guidance"])
    assert queried["admitted_event_count"] == 1
    assert queried["low_authority_event_count"] == 1
    assert compacted["status"] == "compacted"
    assert (tmp_path / ".agentic-workspace/local/correction-events.json").is_file()
    assert submitted["receipt_ref"].startswith(".agentic-workspace/local/correction-event-receipts/")


def test_correction_event_public_contract_omits_caller_authority_inputs() -> None:
    caller_authority_inputs = {"subjects_json", "trusted_authority_receipt_json"}
    correction_operations = {
        "correction-event.submit",
        "correction-event.query",
        "correction-event.correct-dispute",
        "correction-event.withdraw-supersede",
        "correction-event.prune-compact",
    }
    for operation in external_contract_bundle()["operations"].values():
        if operation["identity"] not in correction_operations:
            continue
        input_names = {entry["name"] for entry in operation["contract"]["inputs"]}
        assert not caller_authority_inputs & input_names
        assert "trusted_authority_receipt_ref" in input_names


def test_correction_event_typescript_cli_delegates_to_python_authority_boundary(tmp_path: Path) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n', encoding="utf-8"
    )
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'current_target = "user-local:fast-worker"',
                "",
                "[local_memory]",
                "target_guidance_enabled = true",
                'user_guidance_root = "~/.agentic-workspace/target-guidance"',
                'correction_events_path = ".agentic-workspace/local/correction-events.json"',
                "",
                "[delegation_targets.fast_worker]",
                'target_id = "user-local:fast-worker"',
                'target_revision = "rev-1"',
                'aliases = ["fast"]',
                'revision_policy = "preserve"',
                'strength = "strong"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )
    receipt_ref = ".agentic-workspace/local/correction-authority-receipts/review-thread-1.json"
    (tmp_path / receipt_ref).parent.mkdir(parents=True)
    (tmp_path / receipt_ref).write_text(
        json.dumps(
            {
                "authority": "pr-review",
                "producer_class": "human-reviewer",
                "producer_id": "reviewer-1",
                "source": "github-review",
                "source_ref": "review-thread-1",
                "status": "current",
            }
        ),
        encoding="utf-8",
    )
    event = {
        "delivery_id": "delivery-ts-1",
        "target_identity_ref": "fast",
        "target_revision": "rev-1",
        "task_class": "mechanical-follow-through",
        "scope_class": "narrow-code-change",
        "invariant_id": "narrow-edits",
        "behavior_class": "edit-scope",
        "desired_behavior": "Prefer narrow edits.",
        "replaced_behavior": "Broad edits.",
        "source_ref": "review-thread-1",
        "evidence_hash": "sha256:review-thread-1",
        "route_decisions": ["target-guidance", "target-suitability"],
    }

    result = subprocess.run(
        [
            "node",
            str(ROOT / "generated/workspace/typescript/src/cli.mjs"),
            "correction-event",
            "submit",
            "--target",
            str(tmp_path),
            "--event-json",
            json.dumps(event),
            "--trusted-authority-receipt-ref",
            receipt_ref,
            "--format",
            "json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "stored"
    assert payload["admitted_event_count"] == 1
    assert payload["low_authority_event_count"] == 0
    assert payload["receipt_ref"].startswith(".agentic-workspace/local/correction-event-receipts/")


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
    role = next(role for role, schemas in operation["compatibility_surface"]["schemas"].items() if schemas)
    schema_name = next(iter(operation["compatibility_surface"]["schemas"][role]))
    schema = additive["operations"][operation_id]["compatibility_surface"]["schemas"][role][schema_name]
    schema.setdefault("properties", {})["future_optional"] = {"type": "string"}
    monkeypatch.setattr(public_client, "external_contract_bundle", lambda: additive)
    assert negotiate_requirements({operation_id: requirement}, allow_runtime_backed=True)["compatible"] is True
    breaking = copy.deepcopy(bundle)
    changed = breaking["operations"][operation_id]["compatibility_surface"]["schemas"][role][schema_name]
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


@pytest.mark.parametrize(
    ("role", "old_schema", "new_schema", "compatible"),
    [
        ("input", {"required": ["a"]}, {"required": ["a", "b"]}, False),
        ("input", {"enum": ["a", "b"]}, {"enum": ["a"]}, False),
        ("input", {"enum": ["a"]}, {"enum": ["a", "b"]}, True),
        ("input", {"type": ["string"]}, {"type": ["string", "null"]}, True),
        ("output", {"required": ["a"]}, {"required": []}, False),
        ("output", {"enum": ["a"]}, {"enum": ["a", "b"]}, False),
        ("output", {"type": ["string"]}, {"type": ["string", "null"]}, False),
    ],
)
def test_python_and_typescript_role_aware_compatibility(
    role: str, old_schema: dict[str, object], new_schema: dict[str, object], compatible: bool
) -> None:
    old = {"contract": {}, "schemas": {role: {"fixture": old_schema}}}
    new = {"contract": {}, "schemas": {role: {"fixture": new_schema}}}
    assert public_client.compatibility_surface_satisfied(old, new) is compatible
    script = f"import {{compatibilitySurfaceSatisfied}} from './generated/workspace/typescript/src/client.mjs'; console.log(compatibilitySurfaceSatisfied({json.dumps(old)}, {json.dumps(new)}));"
    result = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(compatible).lower()


@pytest.mark.parametrize(
    "change,compatible",
    [("add_optional", True), ("add_required", False), ("make_required", False), ("remove_optional", False), ("tighten_type", False)],
)
def test_python_and_typescript_operation_input_evolution(change: str, compatible: bool) -> None:
    old = {
        "contract": {"inputs": [{"name": "a", "required": False, "type": "string"}]},
        "schemas": {"input": {"fixture": {"type": "object", "properties": {"a": {"type": "string"}}, "required": []}}},
    }
    new = copy.deepcopy(old)
    if change.startswith("add_"):
        required = change == "add_required"
        new["contract"]["inputs"].append({"name": "b", "required": required, "type": "string"})
        new["schemas"]["input"]["fixture"]["properties"]["b"] = {"type": "string"}
        if required:
            new["schemas"]["input"]["fixture"]["required"].append("b")
    elif change == "make_required":
        new["contract"]["inputs"][0]["required"] = True
        new["schemas"]["input"]["fixture"]["required"].append("a")
    elif change == "remove_optional":
        new["contract"]["inputs"] = []
        del new["schemas"]["input"]["fixture"]["properties"]["a"]
    else:
        new["contract"]["inputs"][0]["type"] = "integer"
        new["schemas"]["input"]["fixture"]["properties"]["a"]["type"] = "integer"
    assert public_client.compatibility_surface_satisfied(old, new) is compatible
    script = f"import {{compatibilitySurfaceSatisfied}} from './generated/workspace/typescript/src/client.mjs'; console.log(compatibilitySurfaceSatisfied({json.dumps(old)}, {json.dumps(new)}));"
    result = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(compatible).lower()


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
    python_target = tmp_path / "python"
    typescript_target = tmp_path / "typescript"
    for target in (python_target, typescript_target):
        config = target / ".agentic-workspace/config.toml"
        config.parent.mkdir(parents=True)
        config.write_text("[workspace]\nenabled = true\n", encoding="utf-8")
    values = {"delegation_target": "fixture", "task_class": "parity", "scope_class": "parity", "outcome": "success"}
    python_payload = invoke_operation(
        "delegation-outcome.append",
        values,
        target=python_target,
        invocation=[sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")],
        allow_runtime_backed=True,
    )
    script = f"""
import {{ invokeOperation }} from './generated/workspace/typescript/src/client.mjs';
const payload = invokeOperation('delegation-outcome.append', {json.dumps(values)}, {{ target: {json.dumps(str(typescript_target))}, invocation: [{json.dumps(sys.executable)}, {json.dumps(str(ROOT / "scripts/run_agentic_workspace.py"))}], allowRuntimeBacked: true }});
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
    values = {"delegation_target": "fixture", "task_class": "parity", "scope_class": "parity", "outcome": "success"}
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
