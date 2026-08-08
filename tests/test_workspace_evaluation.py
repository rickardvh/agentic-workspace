from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_workspace import cli
from agentic_workspace.client import AWClientError
from agentic_workspace.config import WorkspaceUsageError
from agentic_workspace.contract_tooling import contract_schema
from agentic_workspace.evaluation import (
    ASSIGNMENT_AUTHORITY_RECEIPT_DIR,
    EVALUATION_OBSERVATION_KIND,
    EVALUATION_PENDING_COLLECTIONS_DIR,
    EVALUATION_SUMMARY_KIND,
    EVALUATIONS_KIND,
    EXTERNAL_EVALUATION_ADAPTER_HOST_RESULT_ADMISSION_INDEX_KIND,
    EXTERNAL_EVALUATION_ADAPTER_HOST_RESULT_DIR,
    EXTERNAL_EVALUATION_ADAPTER_HOST_RESULT_INDEX_KIND,
    EXTERNAL_EVALUATION_ADAPTER_RECEIPT_DIR,
    EXTERNAL_EVALUATION_PROVIDER_RESULT_INBOX_DIR,
    EXTERNAL_EVALUATION_PROVIDER_TRUST_ROOT_DIR,
    EXTERNAL_EVALUATION_PROVIDER_TRUST_ROOT_INDEX_KIND,
    OBSERVATION_RETENTION_CAP,
    PROOF_AUTHORITY_RECEIPT_DIR,
    WORKSPACE_EVALUATIONS_PATH,
    WORKSPACE_LOCAL_EVALUATIONS_DIR,
    _external_delivery_adapter_host_admission_signature_payload,
    _write_indexed_owner_receipt,
    append_observation,
    closure_authority,
    evaluation_collection_actions,
    evaluation_report_delivery_retry_request,
    evaluation_report_delivery_status,
    evaluation_report_payload,
    evaluation_summary,
    execute_evaluation_collection_action,
    external_evaluation_report_delivery_request,
    prune_observations,
    record_external_evaluation_adapter_host_result,
    record_external_evaluation_adapter_receipt,
    record_external_evaluation_report_delivery,
    record_local_evaluation_report_delivery,
    record_material_finding_followup,
    register_evaluation,
    transition_evaluation,
    write_observation_authority,
)

ROOT = Path(__file__).resolve().parents[1]


def _external_evaluation_provider_host_signature(payload: dict[str, object]) -> dict[str, object]:
    script = r"""
import base64
import hashlib
import json
import os
import random
import sys

RSA_SHA256_DER_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def is_probable_prime(candidate):
    if candidate < 2:
        return False
    small_primes = (3, 5, 7, 11, 13, 17, 19, 23, 29, 31)
    if candidate in small_primes:
        return True
    if candidate % 2 == 0 or any(candidate % prime == 0 for prime in small_primes):
        return False
    d = candidate - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for base in (2, 3, 5, 7, 11, 13, 17):
        if base >= candidate:
            continue
        x = pow(base, d, candidate)
        if x in (1, candidate - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, candidate)
            if x == candidate - 1:
                break
        else:
            return False
    return True


def random_prime(bits):
    while True:
        candidate = int.from_bytes(os.urandom(bits // 8), "big")
        candidate |= (1 << (bits - 1)) | 1
        if is_probable_prime(candidate):
            return candidate


payload = json.loads(sys.stdin.read())
random.seed()
e = 65537
while True:
    p = random_prime(256)
    q = random_prime(256)
    if p == q:
        continue
    phi = (p - 1) * (q - 1)
    if phi % e != 0:
        break
n = p * q
d = pow(e, -1, phi)
key_size = (n.bit_length() + 7) // 8
message = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
digest_info = RSA_SHA256_DER_PREFIX + hashlib.sha256(message).digest()
encoded = b"\x00\x01" + (b"\xff" * (key_size - len(digest_info) - 3)) + b"\x00" + digest_info
raw = pow(int.from_bytes(encoded, "big"), d, n).to_bytes(key_size, "big")
print(json.dumps({
    "key": {
        "algorithm": "RS256",
        "issuer": "evaluation-provider-adapter",
        "trusted_channel": "provider-webhook",
        "n": format(n, "x"),
        "e": format(e, "x"),
        "status": "current",
    },
    "signature": base64.urlsafe_b64encode(raw).decode("ascii").rstrip("="),
}, sort_keys=True))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps(payload, sort_keys=True, default=str),
        capture_output=True,
        text=True,
        check=True,
    )
    signed = json.loads(completed.stdout)
    assert isinstance(signed, dict)
    return signed


def _write_external_evaluation_provider_trust_root(
    target_root: Path,
    *,
    key_id: str,
    key: dict[str, object],
    status: str = "current",
    key_revision: str = "fixture-key-rev-1",
    compatibility_status: str = "compatible",
    revoked_at: str = "",
    superseded_by: str = "",
) -> None:
    root = target_root / EXTERNAL_EVALUATION_PROVIDER_TRUST_ROOT_DIR
    root.mkdir(parents=True, exist_ok=True)
    index_path = root / "index.json"
    index = (
        json.loads(index_path.read_text(encoding="utf-8"))
        if index_path.exists()
        else {"kind": EXTERNAL_EVALUATION_PROVIDER_TRUST_ROOT_INDEX_KIND, "keys": {}}
    )
    keys = index.setdefault("keys", {})
    keys[key_id] = {
        **key,
        "status": status,
        "key_revision": key_revision,
        "compatibility_status": compatibility_status,
    }
    if revoked_at:
        keys[key_id]["revoked_at"] = revoked_at
    if superseded_by:
        keys[key_id]["superseded_by"] = superseded_by
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_external_evaluation_adapter_host_result(
    target_root: Path,
    *,
    host_admission_monkeypatch: pytest.MonkeyPatch | None = None,
    import_result: bool = True,
    trust_host_key: bool = True,
    **values: object,
) -> dict[str, object]:
    if host_admission_monkeypatch is not None:
        # Lower-layer publication and receipt tests substitute the already
        # authenticated host boundary. Trust-path tests never use this seam.
        import agentic_workspace.evaluation as evaluation_runtime

        host_admission_monkeypatch.setattr(
            evaluation_runtime,
            "_host_admits_external_delivery_adapter_host_result",
            lambda _ref, _result, *, target_root: bool(target_root),
        )
    workspace_ref = str(values.get("workspace_ref") or f"workspace:path:{target_root.resolve()}")
    audience = str(values.get("audience") or "agentic-workspace.evaluation-external-delivery")
    result = {
        "kind": "agentic-workspace/evaluation-external-delivery-adapter-host-result/v1",
        "status": "current",
        "delivery_id": str(values["delivery_id"]),
        "sink_id": str(values["sink_id"]),
        "producer": str(values["producer"]),
        "status_owner": str(values.get("status_owner") or "provider-adapter"),
        "attempt_revision": str(values["attempt_revision"]),
        "receipt_revision": str(values["receipt_revision"]),
        "capability_revision": str(values["capability_revision"]),
        "capability_status": str(values.get("capability_status") or "current"),
        "delivery_status": str(values["status"]),
        "detail": str(values.get("detail") or ""),
        "supersedes": str(values.get("supersedes") or ""),
        "request_revision": str(values.get("request_revision") or ""),
        "recorded_at": "2026-07-29T00:00:00Z",
        "admission_context": {
            "audience": audience,
            "workspace_ref": workspace_ref,
            "issued_at": str(values.get("issued_at") or "2026-07-29T00:00:00Z"),
            "expires_at": str(values.get("expires_at") or "2099-01-01T00:00:00Z"),
            "nonce": str(
                values["nonce"] if "nonce" in values else f"{values['delivery_id']}:{values['sink_id']}:{values['attempt_revision']}"
            ),
        },
        "custody": {
            "producer": "evaluation-provider-adapter",
            "trusted_channel": "provider-webhook",
            "rule": "Fixture for provider-owned delivery evidence; AW only imports this host result.",
        },
    }
    result_id = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:24]
    result["result_id"] = result_id
    result["result_ref"] = f"external-evaluation-adapter-host-result:{result_id}"
    key_id = f"evaluation-provider-adapter:external-host-fixture:{result_id}"
    result_digest = hashlib.sha256(
        json.dumps(
            {key: value for key, value in result.items() if key not in {"host_admission", "host_admission_ref", "host_admission_verdict"}},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    result["host_admission"] = {
        "kind": "agentic-workspace/evaluation-external-delivery-adapter-host-result-admission/v1",
        "status": str(values.get("host_admission_status") or "current"),
        "algorithm": "RS256",
        "key_id": key_id,
        "result_ref": result["result_ref"],
        "result_digest": result_digest,
    }
    result["host_admission_ref"] = (
        "external-evaluation-adapter-host-result-admission:"
        + hashlib.sha256(
            json.dumps(
                {
                    "result_ref": result["result_ref"],
                    "workspace_ref": workspace_ref,
                    "nonce": result["admission_context"]["nonce"],
                    "overrides": values,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:24]
    )
    result["host_admission_verdict"] = {
        "kind": "agentic-workspace/evaluation-external-delivery-adapter-host-result-verdict/v1",
        "status": str(values.get("verdict_status") or "admitted"),
        "authority": "signed-provider-adapter",
        "producer": result["producer"],
        "delivery_id": result["delivery_id"],
        "sink_id": result["sink_id"],
        "attempt_revision": result["attempt_revision"],
        "capability_revision": result["capability_revision"],
        "result_ref": result["result_ref"],
        "result_digest": result_digest,
        "workspace_ref": workspace_ref,
        "audience": audience,
        "nonce": result["admission_context"]["nonce"],
        "issued_at": str(values.get("issued_at") or "2026-07-29T00:00:00Z"),
        "expires_at": str(values.get("expires_at") or "2099-01-01T00:00:00Z"),
        "verifier_revision": str(values.get("verifier_revision") or "host-provider-resolver:test:v1"),
    }
    if values.get("revoked_at"):
        result["host_admission_verdict"]["revoked_at"] = str(values["revoked_at"])
    if values.get("superseded_by"):
        result["host_admission_verdict"]["superseded_by"] = str(values["superseded_by"])
    provider_result_ref = f"external-evaluation-provider-result:{result_id}"
    inbox_path = target_root / EXTERNAL_EVALUATION_PROVIDER_RESULT_INBOX_DIR / f"{result_id}.json"
    if inbox_path.exists():
        result = json.loads(inbox_path.read_text(encoding="utf-8"))
        imported = (
            record_external_evaluation_adapter_host_result(
                target_root=target_root,
                provider_result_ref=provider_result_ref,
                capability_revision=str(result["capability_revision"]),
            )
            if import_result
            else {}
        )

        def resolver(ref: str) -> dict[str, object]:
            if ref != provider_result_ref:
                raise AssertionError(f"unexpected provider result ref: {ref}")
            return result

        return {
            **imported,
            "result": result,
            "result_id": result_id,
            "result_ref": result["result_ref"],
            "provider_result_ref": provider_result_ref,
            "provider_result_resolver": resolver,
            "host_public_key": {},
            "host_public_key_id": str(result.get("host_admission", {}).get("key_id") or key_id)
            if isinstance(result.get("host_admission"), dict)
            else key_id,
            "provider_result_digest": hashlib.sha256(
                json.dumps(result, sort_keys=True, default=str, separators=(",", ":")).encode()
            ).hexdigest(),
        }
    signature_payload = _external_delivery_adapter_host_admission_signature_payload(
        ref=str(result["result_ref"]),
        result=result,
        verdict=result["host_admission_verdict"],
        admission=result["host_admission"],
    )
    signed = _external_evaluation_provider_host_signature(signature_payload)
    result["host_admission"]["signature"] = str(signed["signature"])
    if trust_host_key:
        _write_external_evaluation_provider_trust_root(
            target_root,
            key_id=str(result["host_admission"]["key_id"]),
            key=signed["key"],
        )

    def resolver(ref: str) -> dict[str, object]:
        if ref != provider_result_ref:
            raise AssertionError(f"unexpected provider result ref: {ref}")
        return result

    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    inbox_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    imported = (
        record_external_evaluation_adapter_host_result(
            target_root=target_root,
            provider_result_ref=provider_result_ref,
            capability_revision=str(result["capability_revision"]),
        )
        if import_result
        else {}
    )
    return {
        **imported,
        "result": result,
        "result_id": result_id,
        "result_ref": result["result_ref"],
        "provider_result_ref": provider_result_ref,
        "provider_result_resolver": resolver,
        "host_public_key": signed["key"],
        "host_public_key_id": key_id,
        "provider_result_digest": hashlib.sha256(
            json.dumps(result, sort_keys=True, default=str, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def _external_evaluation_host_trusted_invocation(host: dict[str, object]) -> list[str]:
    _ = host
    return [sys.executable, str(ROOT / "scripts" / "run_agentic_workspace.py")]


def _init_git_repo(target_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=target_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=target_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=target_root, check=True, capture_output=True, text=True)
    source = target_root / "src" / "feature.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/feature.py"], cwd=target_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=target_root, check=True, capture_output=True, text=True)


def _bound_context(
    target_root: Path,
    *,
    evaluation_id: str = "eval-1969-operating-loop",
    assignment_revision: str = "assignment-rev-1",
    proof_revision: str = "proof-rev-1",
) -> dict:
    target_identity_ref = "user-local:codex-current"
    assignment_ref = _write_indexed_owner_receipt(
        target_root=target_root,
        store_root=ASSIGNMENT_AUTHORITY_RECEIPT_DIR,
        receipt_id=f"assignment-receipt-{assignment_revision}",
        payload={
            "kind": "agentic-workspace/assignment-authority-receipt/v1",
            "receipt_id": f"assignment-receipt:{assignment_revision}",
            "producer": "assignment.lifecycle",
            "revision": assignment_revision,
            "target_identity_ref": target_identity_ref,
            "context_key": "mechanical-follow-through::mechanical-follow-through",
        },
    )
    proof_ref = _write_indexed_owner_receipt(
        target_root=target_root,
        store_root=PROOF_AUTHORITY_RECEIPT_DIR,
        receipt_id=f"proof-receipt-{proof_revision}",
        payload={
            "kind": "agentic-workspace/proof-receipt/v1",
            "receipt_id": f"proof-receipt:{proof_revision}",
            "producer": "aw-proof",
            "revision": proof_revision,
            "result": "passed",
            "verified_by": "aw",
            "provenance": "proof-receipts/run-1.json",
            "subject": {"target_identity_ref": target_identity_ref},
        },
    )
    assignment = {
        "target_identity_ref": target_identity_ref,
        "context_key": "mechanical-follow-through::mechanical-follow-through",
        "assignment_revision": assignment_revision,
        "receipt": {
            "kind": "agentic-workspace/assignment-authority-receipt/v1",
            "receipt_id": f"assignment-receipt:{assignment_revision}",
            "producer": "assignment.lifecycle",
            "revision": assignment_revision,
            "source_ref": assignment_ref,
        },
    }
    proof = {
        "result": "passed",
        "verified_by": "aw",
        "revision": proof_revision,
        "provenance": "proof-receipts/run-1.json",
        "receipt": {
            "kind": "agentic-workspace/proof-receipt/v1",
            "receipt_id": f"proof-receipt:{proof_revision}",
            "producer": "aw-proof",
            "revision": proof_revision,
            "source_ref": proof_ref,
            "subject": {"target_identity_ref": target_identity_ref},
        },
    }
    authority = write_observation_authority(
        target_root=target_root,
        evaluation_id=evaluation_id,
        assignment=assignment,
        proof=proof,
        changed_paths=["src/feature.py"],
    )
    return {
        "assignment": assignment,
        "authority_envelope": authority["authority_envelope"],
        "proof": proof,
    }


def _definition_kwargs() -> dict:
    return {
        "evaluation_id": "eval-1969-operating-loop",
        "question": "Does the state-delta-first operating loop reduce repeated context reconstruction?",
        "subject": {"type": "issue", "refs": ["#1969"]},
        "criteria": [
            {
                "id": "reconstruction-cost",
                "type": "qualitative",
                "question": "Do continuation turns avoid repeated broad rereads?",
                "success_condition": "Repeated context reconstruction is materially reduced.",
                "required": True,
            },
            {
                "id": "coverage",
                "type": "coverage",
                "question": "Are startup and closeout turns both represented?",
                "success_condition": "At least one startup and one closeout observation exist.",
                "required": False,
            },
        ],
        "decision_owner": {"id": "workspace-maintainer", "class": "maintainer"},
        "evidence_sources": [{"id": "dogfood-session-log", "class": "log"}],
        "report_sinks": [{"id": "#1969", "class": "closed-issue"}],
        "selectors": {"issue_refs": ["#1969"], "operation_ids": ["start.context"], "phases": ["startup"]},
        "collection_policy": {"mode": "local-first", "minimum_observations": 1},
        "conclusion_policy": {"rule": "owner-reviews-summary"},
        "action_policy": {"material_negative_finding": "create-bounded-follow-up"},
    }


def _adapter_receipt_file(tmp_path: Path, receipt: dict, *, host_admission_monkeypatch: pytest.MonkeyPatch) -> str:
    host = _write_external_evaluation_adapter_host_result(
        tmp_path,
        host_admission_monkeypatch=host_admission_monkeypatch,
        delivery_id=receipt["delivery_id"],
        sink_id=receipt["sink_id"],
        producer=receipt["producer"],
        attempt_revision=receipt["attempt_revision"],
        receipt_revision=receipt["receipt_revision"],
        capability_revision=receipt["capability_revision"],
        capability_status=receipt.get("capability_status", "current"),
        status=receipt["status"],
        status_owner=receipt.get("status_owner", "provider-adapter"),
        detail=receipt.get("detail", ""),
        supersedes=receipt.get("supersedes", ""),
    )
    result = record_external_evaluation_adapter_receipt(
        target_root=tmp_path,
        delivery_id=receipt["delivery_id"],
        sink_id=receipt["sink_id"],
        producer=receipt["producer"],
        attempt_revision=receipt["attempt_revision"],
        receipt_revision=receipt["receipt_revision"],
        capability_revision=receipt["capability_revision"],
        capability_status=receipt.get("capability_status", "current"),
        status=receipt["status"],
        status_owner=receipt.get("status_owner", "provider-adapter"),
        detail=receipt.get("detail", ""),
        supersedes=receipt.get("supersedes", ""),
        host_result_ref=host["result_ref"],
    )
    return result["receipt_ref"]


def test_external_adapter_receipt_requires_matching_host_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    receipt = {
        "delivery_id": "delivery-1",
        "sink_id": "#1969",
        "producer": "github-issues-adapter",
        "attempt_revision": "attempt-1",
        "receipt_revision": "receipt-1",
        "capability_revision": "github-issues-adapter:v1",
        "status": "delivered",
    }
    with pytest.raises(WorkspaceUsageError, match="host result reference"):
        record_external_evaluation_adapter_receipt(target_root=tmp_path, **receipt)
    with pytest.raises(WorkspaceUsageError, match="provider-owned evidence"):
        record_external_evaluation_adapter_host_result(target_root=tmp_path, **receipt)
    host = _write_external_evaluation_adapter_host_result(tmp_path, host_admission_monkeypatch=monkeypatch, **receipt)
    with pytest.raises(WorkspaceUsageError, match="do not match"):
        record_external_evaluation_adapter_receipt(
            target_root=tmp_path,
            **{**receipt, "sink_id": "#wrong", "host_result_ref": host["result_ref"]},
        )
    recorded = record_external_evaluation_adapter_receipt(target_root=tmp_path, **receipt, host_result_ref=host["result_ref"])
    assert recorded["status"] == "recorded"
    assert recorded["host_result_ref"] == host["result_ref"]


def test_external_host_result_import_is_idempotent_and_append_preserving(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = _write_external_evaluation_adapter_host_result(
        tmp_path,
        delivery_id="delivery-1",
        sink_id="#1969",
        producer="github-issues-adapter",
        attempt_revision="attempt-1",
        receipt_revision="receipt-1",
        capability_revision="github-issues-adapter:v1",
        status="delivered",
        host_admission_monkeypatch=monkeypatch,
    )
    second = _write_external_evaluation_adapter_host_result(
        tmp_path,
        delivery_id="delivery-2",
        sink_id="#1970",
        producer="github-issues-adapter",
        attempt_revision="attempt-1",
        receipt_revision="receipt-2",
        capability_revision="github-issues-adapter:v1",
        status="failed",
        host_admission_monkeypatch=monkeypatch,
    )
    replay = record_external_evaluation_adapter_host_result(
        target_root=tmp_path,
        provider_result_ref=str(first["provider_result_ref"]),
        capability_revision="github-issues-adapter:v1",
    )
    with pytest.raises(WorkspaceUsageError, match="caller-provided external evaluation provider result resolvers are rejected"):
        record_external_evaluation_adapter_host_result(
            target_root=tmp_path,
            provider_result_ref=str(first["provider_result_ref"]),
            capability_revision="github-issues-adapter:v1",
            provider_result_resolver=first["provider_result_resolver"],
        )

    assert replay["result_ref"] == first["result_ref"]
    result_index = json.loads((tmp_path / first["index_ref"]).read_text(encoding="utf-8"))
    admission_index = json.loads((tmp_path / first["admission_index_ref"]).read_text(encoding="utf-8"))
    assert result_index["kind"] == EXTERNAL_EVALUATION_ADAPTER_HOST_RESULT_INDEX_KIND
    assert set(result_index["results"]) == {first["result_id"], second["result_id"]}
    assert admission_index["kind"] == EXTERNAL_EVALUATION_ADAPTER_HOST_RESULT_ADMISSION_INDEX_KIND
    assert len(admission_index["admissions"]) == 2


def test_external_host_result_import_rejects_caller_written_provider_file_without_signed_inbox(tmp_path: Path) -> None:
    result_id = "caller-written-result"
    provider_path = tmp_path / ".agentic-workspace/local/evaluations/external-provider-results" / f"{result_id}.json"
    provider_path.parent.mkdir(parents=True, exist_ok=True)
    provider_path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/evaluation-external-delivery-adapter-host-result/v1",
                "status": "current",
                "result_id": result_id,
                "result_ref": f"external-evaluation-adapter-host-result:{result_id}",
                "delivery_id": "delivery-1",
                "sink_id": "#1969",
                "producer": "github-issues-adapter",
                "attempt_revision": "attempt-1",
                "receipt_revision": "receipt-1",
                "capability_revision": "github-issues-adapter:v1",
                "capability_status": "current",
                "custody": {"producer": "evaluation-provider-adapter", "trusted_channel": "provider-webhook"},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceUsageError, match="signed provider result inbox"):
        record_external_evaluation_adapter_host_result(
            target_root=tmp_path,
            provider_result_ref=f"external-evaluation-provider-result:{result_id}",
        )

    assert not (tmp_path / EXTERNAL_EVALUATION_ADAPTER_HOST_RESULT_DIR / f"{result_id}.json").exists()


def test_external_host_result_import_rolls_back_partial_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_replace = Path.replace
    replace_count = 0

    def fail_second_replace(self: Path, target: Path) -> Path:
        nonlocal replace_count
        replace_count += 1
        if replace_count == 2:
            raise OSError("simulated partial import failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_second_replace)
    with pytest.raises(OSError, match="simulated partial import failure"):
        _write_external_evaluation_adapter_host_result(
            tmp_path,
            host_admission_monkeypatch=monkeypatch,
            delivery_id="delivery-rollback",
            sink_id="#1969",
            producer="github-issues-adapter",
            attempt_revision="attempt-1",
            receipt_revision="receipt-1",
            capability_revision="github-issues-adapter:v1",
            status="delivered",
        )

    host_root = tmp_path / EXTERNAL_EVALUATION_ADAPTER_HOST_RESULT_DIR
    assert not list(host_root.glob("*.json"))
    assert not (host_root / "index.json").exists()


def test_external_adapter_receipt_rejects_target_local_trust_across_process(tmp_path: Path) -> None:
    receipt = {
        "delivery_id": "delivery-1",
        "sink_id": "#1969",
        "producer": "github-issues-adapter",
        "attempt_revision": "attempt-1",
        "receipt_revision": "receipt-1",
        "capability_revision": "github-issues-adapter:v1",
        "status": "delivered",
    }
    host = _write_external_evaluation_adapter_host_result(tmp_path, import_result=False, **receipt)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; "
                "from pathlib import Path; "
                "from agentic_workspace.evaluation import record_external_evaluation_adapter_host_result; "
                f"payload = record_external_evaluation_adapter_host_result(target_root=Path({str(tmp_path)!r}), "
                f"provider_result_ref={str(host['provider_result_ref'])!r}, capability_revision='github-issues-adapter:v1'); "
                "print(json.dumps(payload, sort_keys=True))"
            ),
        ],
        capture_output=True,
        cwd=ROOT,
        text=True,
    )

    assert completed.returncode != 0
    assert "not admitted by the host boundary" in completed.stderr


def test_external_adapter_receipt_does_not_load_repo_or_pythonpath_host_verifiers() -> None:
    source = (ROOT / "src/agentic_workspace/evaluation.py").read_text(encoding="utf-8")
    test_source = (ROOT / "tests/test_workspace_evaluation.py").read_text(encoding="utf-8")

    assert "agentic_workspace_host_adapters.external_evaluation" not in source
    assert "importlib.import_module" not in source
    assert "BEGIN " + "PRIVATE KEY" not in test_source
    assert "_EXTERNAL_EVALUATION_PROVIDER_TEST_RSA" + "_D" not in test_source
    assert "_external_evaluation_provider" + "_test_signature" not in test_source
    assert "_EXTERNAL_EVALUATION_PROVIDER" + "_PUBLIC_KEYS" not in test_source
    assert "_PINNED_EXTERNAL_EVALUATION_PROVIDER" + "_PUBLIC_KEYS" not in test_source
    assert "evaluation-provider-adapter:test-v1" not in source
    assert "_EXTERNAL_EVALUATION_ADAPTER_HOST_ADMISSION_KEYS" not in source
    assert "_external_evaluation_provider_result_store_path" not in source
    assert "tempfile.gettempdir()" not in source
    assert "Path.home()" not in source
    assert "external-evaluation-admission-keys" not in source


def test_external_adapter_receipt_rejects_jointly_forged_local_host_result(tmp_path: Path, monkeypatch) -> None:
    receipt = {
        "delivery_id": "delivery-1",
        "sink_id": "#1969",
        "producer": "github-issues-adapter",
        "attempt_revision": "attempt-1",
        "receipt_revision": "receipt-1",
        "capability_revision": "github-issues-adapter:v1",
        "status": "delivered",
    }
    host = _write_external_evaluation_adapter_host_result(tmp_path, host_admission_monkeypatch=monkeypatch, **receipt)
    monkeypatch.setenv(
        "AW_EXTERNAL_EVALUATION_ADAPTER_HOST_RESULT_ADMISSION_KEYS",
        json.dumps({"caller-key": {"status": "current"}}),
    )
    result_path = tmp_path / host["path"]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["host_admission"] = {
        "kind": "agentic-workspace/evaluation-external-delivery-adapter-host-result-admission/v1",
        "status": "current",
        "key_id": "caller-key",
        "signature": "caller-forged-signature",
    }
    result["host_admission_ref"] = "external-evaluation-adapter-host-result-admission:caller-forged"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    index_path = tmp_path / host["index_ref"]
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["results"][host["result_id"]]["result_digest"] = hashlib.sha256(result_path.read_bytes()).hexdigest()
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(WorkspaceUsageError, match="host boundary"):
        record_external_evaluation_adapter_receipt(
            target_root=tmp_path,
            **receipt,
            host_result_ref=host["result_ref"],
        )


def test_external_host_result_import_rejects_repo_generated_signature_without_host_trust(tmp_path: Path) -> None:
    receipt = {
        "delivery_id": "delivery-1",
        "sink_id": "#1969",
        "producer": "github-issues-adapter",
        "attempt_revision": "attempt-1",
        "receipt_revision": "receipt-1",
        "capability_revision": "github-issues-adapter:v1",
        "status": "delivered",
    }

    with pytest.raises(WorkspaceUsageError, match="host boundary"):
        _write_external_evaluation_adapter_host_result(tmp_path, import_result=True, trust_host_key=False, **receipt)

    assert not any((tmp_path / EXTERNAL_EVALUATION_ADAPTER_HOST_RESULT_DIR).glob("*.json"))


def test_external_host_result_import_rejects_revoked_local_trust_root(tmp_path: Path) -> None:
    receipt = {
        "delivery_id": "delivery-1",
        "sink_id": "#1969",
        "producer": "github-issues-adapter",
        "attempt_revision": "attempt-1",
        "receipt_revision": "receipt-1",
        "capability_revision": "github-issues-adapter:v1",
        "status": "delivered",
    }
    host = _write_external_evaluation_adapter_host_result(tmp_path, import_result=False, **receipt)
    _write_external_evaluation_provider_trust_root(
        tmp_path,
        key_id=str(host["host_public_key_id"]),
        key=host["host_public_key"],
        status="current",
        revoked_at="2026-07-29T00:01:00Z",
    )

    with pytest.raises(WorkspaceUsageError, match="host boundary"):
        record_external_evaluation_adapter_host_result(
            target_root=tmp_path,
            provider_result_ref=str(host["provider_result_ref"]),
            capability_revision="github-issues-adapter:v1",
        )


def test_external_host_result_import_rejects_current_target_local_trust_root(tmp_path: Path) -> None:
    receipt = {
        "delivery_id": "delivery-local-root",
        "sink_id": "#1969",
        "producer": "github-issues-adapter",
        "attempt_revision": "attempt-1",
        "receipt_revision": "receipt-1",
        "capability_revision": "github-issues-adapter:v1",
        "status": "delivered",
    }
    host = _write_external_evaluation_adapter_host_result(tmp_path, import_result=False, **receipt)

    with pytest.raises(WorkspaceUsageError, match="host boundary"):
        record_external_evaluation_adapter_host_result(
            target_root=tmp_path,
            provider_result_ref=str(host["provider_result_ref"]),
            capability_revision="github-issues-adapter:v1",
        )


def test_external_host_result_import_rejects_stale_index_before_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import agentic_workspace.evaluation as evaluation_runtime

    receipt = {
        "delivery_id": "delivery-1",
        "sink_id": "#1969",
        "producer": "github-issues-adapter",
        "attempt_revision": "attempt-1",
        "receipt_revision": "receipt-1",
        "capability_revision": "github-issues-adapter:v1",
        "status": "delivered",
    }
    host = _write_external_evaluation_adapter_host_result(tmp_path, import_result=False, **receipt)
    original_transaction = evaluation_runtime._transactional_json_writes  # type: ignore[attr-defined]
    monkeypatch.setattr(
        evaluation_runtime,
        "_host_admits_external_delivery_adapter_host_result",
        lambda _ref, _result, *, target_root: bool(target_root),
    )

    def mutate_index_before_commit(
        writes: list[tuple[Path, dict[str, object]]],
        *,
        expected_revisions: dict[Path, str] | None = None,
    ) -> dict[Path, str]:
        if expected_revisions:
            host_index_path = tmp_path / EXTERNAL_EVALUATION_ADAPTER_HOST_RESULT_DIR / "index.json"
            host_index_path.parent.mkdir(parents=True, exist_ok=True)
            host_index_path.write_text(
                json.dumps(
                    {"kind": EXTERNAL_EVALUATION_ADAPTER_HOST_RESULT_INDEX_KIND, "results": {"raced": {"status": "current"}}},
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        return original_transaction(writes, expected_revisions=expected_revisions)

    monkeypatch.setattr(evaluation_runtime, "_transactional_json_writes", mutate_index_before_commit)

    with pytest.raises(WorkspaceUsageError, match="index changed before import commit"):
        record_external_evaluation_adapter_host_result(
            target_root=tmp_path,
            provider_result_ref=str(host["provider_result_ref"]),
            capability_revision="github-issues-adapter:v1",
        )


def test_external_evaluation_host_admission_rejects_raw_caller_mapping(tmp_path: Path) -> None:
    import agentic_workspace.evaluation as evaluation_runtime

    _ = tmp_path
    assert not hasattr(evaluation_runtime, "admit_external_evaluation_adapter_host_result")
    assert not hasattr(evaluation_runtime, "ExternalEvaluationAdapterHostResultAdmissionHandle")


def test_external_evaluation_host_admission_issuer_is_not_public_runtime_entrypoint() -> None:
    source = (ROOT / "src/agentic_workspace/evaluation.py").read_text(encoding="utf-8")

    assert "def issue_external_evaluation_adapter_host_result_admission_for_adapter(" not in source
    assert "def admit_external_evaluation_adapter_host_result(" not in source
    assert "def _install_external_evaluation_adapter_host_result_admission_for_adapter_test(" not in source
    assert "ExternalEvaluationAdapterHostResultAdmissionHandle" not in source
    assert "_EXTERNAL_EVALUATION_ADAPTER_HOST_BOUNDARY_TOKEN" not in source
    assert "_CURRENT_EXTERNAL_EVALUATION_ADAPTER_HOST_RESULT_ADMISSIONS" not in source


def test_external_adapter_receipt_accepts_authenticated_host_result_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    receipt = {
        "delivery_id": "delivery-1",
        "sink_id": "#1969",
        "producer": "github-issues-adapter",
        "attempt_revision": "attempt-1",
        "receipt_revision": "receipt-1",
        "capability_revision": "github-issues-adapter:v1",
        "status": "delivered",
    }
    host = _write_external_evaluation_adapter_host_result(tmp_path, host_admission_monkeypatch=monkeypatch, **receipt)

    recorded = record_external_evaluation_adapter_receipt(target_root=tmp_path, **receipt, host_result_ref=host["result_ref"])

    assert recorded["status"] == "recorded"
    assert recorded["host_result_ref"] == host["result_ref"]


def test_external_adapter_receipt_is_idempotent_and_rolls_back_partial_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    receipt = {
        "delivery_id": "delivery-1",
        "sink_id": "#1969",
        "producer": "github-issues-adapter",
        "attempt_revision": "attempt-1",
        "receipt_revision": "receipt-1",
        "capability_revision": "github-issues-adapter:v1",
        "status": "delivered",
    }
    host = _write_external_evaluation_adapter_host_result(tmp_path, host_admission_monkeypatch=monkeypatch, **receipt)
    first = record_external_evaluation_adapter_receipt(target_root=tmp_path, **receipt, host_result_ref=host["result_ref"])
    replay = record_external_evaluation_adapter_receipt(target_root=tmp_path, **receipt, host_result_ref=host["result_ref"])

    assert first["receipt_ref"] == replay["receipt_ref"]
    assert replay["idempotency"] == "replayed"

    failing_receipt = {**receipt, "delivery_id": "delivery-2", "receipt_revision": "receipt-2"}
    failing_host = _write_external_evaluation_adapter_host_result(tmp_path, host_admission_monkeypatch=monkeypatch, **failing_receipt)
    original_replace = Path.replace
    replace_count = 0

    def fail_second_replace(self: Path, target: Path) -> Path:
        nonlocal replace_count
        replace_count += 1
        if replace_count == 2:
            raise OSError("simulated partial receipt failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_second_replace)
    with pytest.raises(OSError, match="simulated partial receipt failure"):
        record_external_evaluation_adapter_receipt(target_root=tmp_path, **failing_receipt, host_result_ref=failing_host["result_ref"])

    receipt_root = tmp_path / EXTERNAL_EVALUATION_ADAPTER_RECEIPT_DIR
    persisted = [path for path in receipt_root.glob("*.json") if path.name != "index.json"]
    assert persisted == [tmp_path / first["receipt_ref"]]
    index = json.loads((receipt_root / "index.json").read_text(encoding="utf-8"))
    assert set(index["receipts"]) == {first["receipt_id"]}


@pytest.mark.parametrize(
    ("case_name", "overrides"),
    [
        ("wrong-audience", {"audience": "other-consumer"}),
        ("missing-nonce", {"nonce": ""}),
        ("expired-admission", {"expires_at": "2026-01-01T00:00:00Z"}),
        ("revoked-admission", {"revoked_at": "2026-07-29T00:00:00Z"}),
        ("wrong-workspace", {"workspace_ref": "workspace:path:not-this-workspace"}),
    ],
)
def test_external_adapter_receipt_rejects_invalid_host_result_admission_lifecycle(
    tmp_path: Path, case_name: str, overrides: dict[str, object]
) -> None:
    receipt = {
        "delivery_id": f"delivery-{case_name}",
        "sink_id": "#1969",
        "producer": "github-issues-adapter",
        "attempt_revision": "attempt-1",
        "receipt_revision": "receipt-1",
        "capability_revision": "github-issues-adapter:v1",
        "status": "delivered",
    }
    with pytest.raises(WorkspaceUsageError, match="host boundary"):
        _write_external_evaluation_adapter_host_result(tmp_path, **receipt, **overrides)


def test_evaluation_collection_actions_match_structured_context_and_stay_quiet(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    workspace_config = tmp_path / ".agentic-workspace" / "config.toml"
    workspace_config.parent.mkdir(parents=True, exist_ok=True)
    workspace_config.write_text("schema_version = 1\n\n[workspace]\nenabled = true\n", encoding="utf-8")
    register_evaluation(target_root=tmp_path, **_definition_kwargs())

    matched = evaluation_collection_actions(
        target_root=tmp_path,
        surface="start",
        issue_refs=["#1969"],
        operation_id="start.context",
        phase="startup",
    )
    assert matched["status"] == "matched"
    action = matched["actions"][0]
    invocation = action.pop("operation_invocation")
    assert invocation["operation_id"] == "evaluation.observe"
    assert invocation["arguments"] == {
        "target": tmp_path.as_posix(),
        "evaluation_id": "eval-1969-operating-loop",
        "criterion": "reconstruction-cost",
        "context": {
            "issue_refs": ["#1969"],
            "operation_ids": ["start.context"],
            "phases": ["startup"],
            "surface": "start",
            "definition_revision": 1,
        },
    }
    assert invocation["idempotency_identity"].startswith("evaluation-observe:")
    assert [action] == [
        {
            "evaluation_id": "eval-1969-operating-loop",
            "criterion": "reconstruction-cost",
            "match_reason": ["issue_refs", "operation_ids", "phases"],
            "decision_owner": {"id": "workspace-maintainer", "class": "maintainer"},
            "report_sinks": [{"id": "#1969", "class": "closed-issue"}],
            "next_action": "record-evaluation-observation-after-bound-proof",
            "executable_operation": "execute_evaluation_collection_action",
            "rule": "Use the evaluation observation operation after assignment, authority, baseline, and proof admission; do not append an unbound reminder observation.",
        }
    ]
    bound_context = _bound_context(tmp_path)
    admitted = execute_evaluation_collection_action(
        target_root=tmp_path,
        action={**action, "operation_invocation": invocation},
        result="supports",
        evidence_refs=["dogfood-session-log://turn-1"],
        context=bound_context,
        finding="startup projection avoided a broad reread",
        recommended_action="keep collecting",
    )
    assert admitted["status"] == "admitted-observation"
    pending_path = tmp_path / EVALUATION_PENDING_COLLECTIONS_DIR / "eval-1969-operating-loop.json"
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    assert pending["collections"][0]["status"] == "admitted-observation"
    suppressed = execute_evaluation_collection_action(
        target_root=tmp_path,
        action={**action, "operation_invocation": invocation},
        result="supports",
        evidence_refs=["dogfood-session-log://turn-1"],
        context=bound_context,
        finding="startup projection avoided a broad reread",
        recommended_action="keep collecting",
    )
    assert suppressed["status"] == "equivalent-observation-suppressed"

    from agentic_workspace.generated_operations import evaluation_observe

    generated = evaluation_observe(
        {
            "evaluation_id": "eval-1969-operating-loop",
            "criterion": "coverage",
            "result": "mixed",
            "evidence_refs": "dogfood-session-log://generated-observe",
            "confidence": "medium",
            "burden": "medium",
            "context": json.dumps(bound_context),
            "finding": "generated observe path admitted",
            "recommended_action": "keep collecting through the public operation",
        },
        target=tmp_path,
        invocation=[sys.executable, str(ROOT / "scripts" / "run_agentic_workspace.py")],
    )
    assert generated["outcome"] == "appended"
    assert generated["criterion"] == "coverage"

    invalid_action = {
        **action,
        "operation_invocation": {
            **invocation,
            "arguments": {
                **invocation["arguments"],
                "criterion": "not-declared",
            },
        },
    }
    with pytest.raises(WorkspaceUsageError, match="not declared"):
        execute_evaluation_collection_action(
            target_root=tmp_path,
            action=invalid_action,
            result="supports",
            evidence_refs=["dogfood-session-log://invalid-criterion"],
            context=bound_context,
        )
    failed_pending = json.loads(pending_path.read_text(encoding="utf-8"))
    failed_entries = [entry for entry in failed_pending["collections"] if entry["status"] == "admission-failed"]
    assert failed_entries
    assert "not-declared" in failed_entries[-1]["failure_reason"]

    quiet = evaluation_collection_actions(
        target_root=tmp_path,
        surface="start",
        issue_refs=["#unrelated"],
        operation_id="start.context",
        phase="startup",
    )
    assert quiet["status"] == "not-applicable"
    assert quiet["actions"] == []

    summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")["summaries"][0]
    loop = summary["operating_loop"]
    assert loop["matching"]["startup_implement_handoff_surfaces"] == ["start", "implement", "handoff"]
    assert loop["matching"]["quiet_non_match"] is True
    assert loop["observe_admission"]["typed_boundary"] == "assignment authority + mutation baseline + proof receipt + definition revision"
    assert loop["specialist_authority"]["specialist_domains"][0]["domain"] == "dogfooding-feedback"
    assert loop["specialist_authority"]["convergence_status"] == "not-yet-converged"
    assert loop["specialist_authority"]["specialist_domains"][0]["convergence_status"] == "not-yet-converged"


def test_evaluation_report_is_quiet_until_explicit_or_material(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    quiet = evaluation_report_payload(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")
    assert quiet["status"] == "not-due"
    explicit = evaluation_report_payload(target_root=tmp_path, evaluation_id="eval-1969-operating-loop", explicit=True)
    assert explicit["status"] == "ready"
    assert explicit["report_authority"]["kind"] == "agentic-workspace/evaluation-report-authority/v1"
    assert explicit["report_authority"]["revision"]
    assert explicit["decision_owner"] == {"id": "workspace-maintainer", "class": "maintainer"}
    assert explicit["report_sinks"] == [{"id": "#1969", "class": "closed-issue"}]
    delivered = record_local_evaluation_report_delivery(target_root=tmp_path, evaluation_id="eval-1969-operating-loop", explicit=True)
    assert delivered["status"] == "recorded-local"
    assert delivered["receipt"]["delivery_scope"] == "local-compilation-receipt-only"
    assert delivered["receipt"]["external_delivery"].startswith("unattempted")
    assert (
        record_local_evaluation_report_delivery(target_root=tmp_path, evaluation_id="eval-1969-operating-loop", explicit=True)["status"]
        == "already-delivered"
    )
    external = external_evaluation_report_delivery_request(target_root=tmp_path, evaluation_id="eval-1969-operating-loop", explicit=True)
    assert external["status"] == "adapter-required"
    assert external["sinks"] == [{"id": "#1969", "class": "closed-issue"}]
    assert external["request_revision"] == external["delivery_id"]
    assert external["authority_revision"] == explicit["report_authority"]["revision"]
    assert record_external_evaluation_report_delivery(target_root=tmp_path, request=external)["status"] == "adapter-receipt-required"
    initial_status = evaluation_report_delivery_status(target_root=tmp_path, evaluation_id="eval-1969-operating-loop", explicit=True)
    assert initial_status["status"] == "pending"
    assert initial_status["sink_statuses"][0]["status"] == "pending"
    failed_receipt = {
        "kind": "agentic-workspace/evaluation-external-delivery-adapter-receipt/v1",
        "producer": "github-issues-adapter",
        "status_owner": "provider-adapter",
        "receipt_revision": "receipt-1",
        "capability_revision": "github-issues-adapter:v1",
        "capability_status": "current",
        "delivery_id": external["delivery_id"],
        "sink_id": "#1969",
        "attempt_revision": "attempt-1",
        "status": "failed",
    }
    assert (
        record_external_evaluation_report_delivery(target_root=tmp_path, request=external, adapter_receipt=failed_receipt)["status"]
        == "adapter-receipt-required"
    )
    unindexed_path = tmp_path / EXTERNAL_EVALUATION_ADAPTER_RECEIPT_DIR / "unindexed.json"
    unindexed_path.parent.mkdir(parents=True, exist_ok=True)
    unindexed_path.write_text(json.dumps({**failed_receipt, "receipt_id": "unindexed"}, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(WorkspaceUsageError, match="provider-owned receipt index"):
        record_external_evaluation_report_delivery(
            target_root=tmp_path,
            request=external,
            adapter_receipt_ref=unindexed_path.relative_to(tmp_path).as_posix(),
        )
    assert (
        record_external_evaluation_report_delivery(
            target_root=tmp_path,
            request=external,
            adapter_receipt_ref=_adapter_receipt_file(
                tmp_path,
                failed_receipt,
                host_admission_monkeypatch=monkeypatch,
            ),
        )["retry"]
        is True
    )
    retry = evaluation_report_delivery_retry_request(target_root=tmp_path, evaluation_id="eval-1969-operating-loop", sink_id="#1969")
    assert retry["status"] == "retryable"
    assert retry["sink_requests"][0]["latest_attempt_revision"] == "attempt-1"
    delivered_receipt = {**failed_receipt, "attempt_revision": "attempt-2", "receipt_revision": "receipt-2", "status": "delivered"}
    assert (
        record_external_evaluation_report_delivery(
            target_root=tmp_path,
            request=external,
            adapter_receipt_ref=_adapter_receipt_file(
                tmp_path,
                delivered_receipt,
                host_admission_monkeypatch=monkeypatch,
            ),
        )["status"]
        == "delivered"
    )
    assert (
        record_external_evaluation_report_delivery(
            target_root=tmp_path,
            request=external,
            adapter_receipt_ref=_adapter_receipt_file(
                tmp_path,
                delivered_receipt,
                host_admission_monkeypatch=monkeypatch,
            ),
        )["status"]
        == "already-delivered"
    )
    delivery_status = evaluation_report_delivery_status(target_root=tmp_path, evaluation_id="eval-1969-operating-loop", explicit=True)
    assert delivery_status["status"] == "delivered"
    loop = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")["summaries"][0]["operating_loop"]
    assert loop["external_delivery"]["request_operation"] == "evaluation.external-request"
    assert loop["external_delivery"]["adapter_receipt_operation"] == "evaluation.external-adapter-receipt"
    assert loop["external_delivery"]["retry_operation"] == "evaluation.retry"
    assert loop["claim_boundary"].startswith("Evaluation compiles owner reports")
    assert delivery_status["sink_statuses"] == [
        {
            "sink_id": "#1969",
            "status": "delivered",
            "attempt_count": 2,
            "latest_attempt_revision": "attempt-2",
            "latest_adapter_receipt_ref": delivery_status["sink_statuses"][0]["latest_adapter_receipt_ref"],
            "retry": False,
            "idempotency_key": external["sink_requests"][0]["idempotency_key"],
        }
    ]


def test_external_evaluation_delivery_rejects_stale_request(tmp_path: Path) -> None:
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    request = external_evaluation_report_delivery_request(target_root=tmp_path, evaluation_id="eval-1969-operating-loop", explicit=True)
    stale_request = {**request, "request_revision": "old-request"}
    receipt = {
        "kind": "agentic-workspace/evaluation-external-delivery-adapter-receipt/v1",
        "producer": "github-issues-adapter",
        "status_owner": "provider-adapter",
        "receipt_revision": "receipt-1",
        "capability_revision": "github-issues-adapter:v1",
        "capability_status": "current",
        "delivery_id": request["delivery_id"],
        "sink_id": "#1969",
        "attempt_revision": "attempt-1",
        "status": "delivered",
    }
    result = record_external_evaluation_report_delivery(target_root=tmp_path, request=stale_request, adapter_receipt=receipt)
    assert result["status"] == "stale-request"
    assert result["retry"] is True


def test_evaluation_register_observe_and_summary_are_schema_valid(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    result = register_evaluation(target_root=tmp_path, **_definition_kwargs())

    assert result["kind"] == EVALUATIONS_KIND
    definitions = json.loads((tmp_path / WORKSPACE_EVALUATIONS_PATH).read_text(encoding="utf-8"))
    Draft202012Validator(contract_schema("evaluation_definition.schema.json")).validate(definitions)
    _bound_context(tmp_path)

    with pytest.raises(WorkspaceUsageError, match="missing-bound-context"):
        append_observation(
            target_root=tmp_path,
            evaluation_id="eval-1969-operating-loop",
            criterion="reconstruction-cost",
            result="supports",
            evidence_refs=["docs/reviews/session-1.md#turn-3"],
            confidence="high",
            burden="low",
            finding="Startup routed directly to current-decision evidence.",
            recommended_action="Continue collection.",
        )

    observed = append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["docs/reviews/session-1.md#turn-3"],
        confidence="high",
        burden="low",
        context=_bound_context(tmp_path),
        finding="Startup routed directly to current-decision evidence.",
        recommended_action="Continue collection.",
    )

    assert observed["kind"] == EVALUATION_OBSERVATION_KIND
    assert observed["result_identity"]["id"].startswith("sha256:")
    observation_path = tmp_path / WORKSPACE_LOCAL_EVALUATIONS_DIR / "eval-1969-operating-loop.jsonl"
    observation = json.loads(observation_path.read_text(encoding="utf-8").strip())
    Draft202012Validator(contract_schema("evaluation_observation.schema.json")).validate(observation)
    assert observation["admission"]["status"] == "admitted"

    summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")
    assert summary["kind"] == EVALUATION_SUMMARY_KIND
    Draft202012Validator(contract_schema("evaluation_summary.schema.json")).validate(summary)
    item = summary["summaries"][0]
    assert item["coverage"]["observation_count"] == 1
    assert item["coverage"]["decision_observation_count"] == 1
    assert item["coverage"]["legacy_unbound_count"] == 0
    assert item["criterion_status"][0]["state"] == "satisfied"
    assert item["fresh_result_admission"]["status"] == "fresh-bound"
    assert item["fresh_result_admission"]["current_result_identity"]["id"] == observed["result_identity"]["id"]
    assert item["fresh_result_admission"]["local_retention"]["max_current_results_per_criterion"] == 1
    assert item["conclusion_readiness"] == {"ready": True, "reason_code": "ready"}
    assert item["next_collection_action"] == "owner-review-or-conclude"
    operating_loop = item["operating_loop"]
    assert operating_loop["kind"] == "agentic-workspace/evaluation-operating-loop/v1"
    assert operating_loop["status"] == "ready-for-owner-review"
    assert operating_loop["observe_admission"]["operation_id"] == "evaluation.observe"
    assert operating_loop["observe_admission"]["current_result_owner"] == "current_evaluation_results"
    assert operating_loop["observe_admission"]["coverage"]["decision_observation_count"] == 1
    assert operating_loop["reporting"]["transition_driven"] is True
    assert operating_loop["external_delivery"]["delivery_claim_rule"].startswith("transport delivery receipts do not change")
    assert operating_loop["next_safe_action"] == "owner-review-report-and-transition"
    assert "universal_lifecycle_authority" in operating_loop["specialist_authority"]


def test_evaluation_update_increments_revision_without_rewriting_observations(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["ref"],
        context=_bound_context(tmp_path),
    )
    observation_path = tmp_path / WORKSPACE_LOCAL_EVALUATIONS_DIR / "eval-1969-operating-loop.jsonl"
    before = observation_path.read_text(encoding="utf-8")

    result = register_evaluation(
        target_root=tmp_path,
        **{**_definition_kwargs(), "question": "Does the operating loop reduce repeated reconstruction and stale proof?"},
    )

    assert result["outcome"] == "updated"
    assert result["revision"] == 2
    assert observation_path.read_text(encoding="utf-8") == before


def test_evaluation_summary_excludes_stale_definition_revision_from_readiness(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context=_bound_context(tmp_path),
    )
    register_evaluation(
        target_root=tmp_path,
        **{**_definition_kwargs(), "question": "Does the operating loop reduce repeated reconstruction and stale proof?"},
    )

    summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")

    item = summary["summaries"][0]
    assert item["revision"] == 2
    assert item["fresh_result_admission"]["status"] == "stale-bound"
    assert item["fresh_result_admission"]["bound_observation_count"] == 0
    assert item["fresh_result_admission"]["current_result_identity"]["status"] == "missing"
    assert item["coverage"]["stale_revision_count"] == 1
    assert item["criterion_status"][0]["state"] == "unobserved"
    assert item["conclusion_readiness"] == {
        "ready": False,
        "reason_code": "requires-bound-current-observation",
    }


def test_evaluation_rejects_log_as_decision_owner(tmp_path: Path) -> None:
    kwargs = _definition_kwargs()
    kwargs["decision_owner"] = {"id": "session-log", "class": "log"}

    with pytest.raises(WorkspaceUsageError, match="logs may be evidence sources or sinks but not decision owners"):
        register_evaluation(target_root=tmp_path, **kwargs)


def test_evaluation_lifecycle_transitions_fail_closed(tmp_path: Path) -> None:
    register_evaluation(target_root=tmp_path, **_definition_kwargs())

    result = transition_evaluation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        lifecycle="paused",
        reason="waiting for another dogfood session",
        expected_revision=1,
    )
    assert result["from"] == "collecting"
    assert result["to"] == "paused"
    assert result["revision_guard"] == "matched"

    with pytest.raises(WorkspaceUsageError, match="invalid evaluation lifecycle transition"):
        transition_evaluation(target_root=tmp_path, evaluation_id="eval-1969-operating-loop", lifecycle="satisfied")
    with pytest.raises(WorkspaceUsageError, match="stale evaluation revision"):
        transition_evaluation(
            target_root=tmp_path,
            evaluation_id="eval-1969-operating-loop",
            lifecycle="archived",
            expected_revision=0,
        )


def test_evaluation_observation_binds_fresh_assignment_authority_and_proof(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())

    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context=_bound_context(tmp_path),
    )

    summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")

    item = summary["summaries"][0]
    assert item["fresh_result_admission"]["status"] == "fresh-bound"
    assert item["fresh_result_admission"]["bound_observation_count"] == 1
    identity = item["fresh_result_admission"]["current_result_identity"]
    assert {
        key: identity[key] for key in ("status", "evaluation_id", "definition_revision", "criterion", "baseline_id", "target_identity_ref")
    } == {
        "status": "present",
        "evaluation_id": "eval-1969-operating-loop",
        "definition_revision": 1,
        "criterion": "reconstruction-cost",
        "baseline_id": _bound_context(tmp_path)["authority_envelope"]["mutation_baseline"]["baseline_id"],
        "target_identity_ref": "user-local:codex-current",
    }
    assert identity["assignment_revision"] == "assignment-rev-1"
    assert identity["recorded_at"]
    assert item["coverage"]["decision_observation_count"] == 1
    assert item["conclusion_readiness"]["ready"] is True
    latest = item["latest_material_changes"][0]
    assert latest["admission"]["status"] == "admitted"
    assert latest["admission"]["baseline_id"] == identity["baseline_id"]
    assert latest["admission"]["target_identity_ref"] == "user-local:codex-current"
    assert "proof-selection" in item["fresh_result_admission"]["admission_contract"]["consumers"]


def test_evaluation_observation_supersedes_previous_current_result(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())

    first = append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context=_bound_context(tmp_path),
    )
    second_context = _bound_context(tmp_path, proof_revision="proof-rev-2")
    second = append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="contradicts",
        evidence_refs=["proof-receipts/run-2.json"],
        context=second_context,
    )

    summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")

    item = summary["summaries"][0]
    assert second["supersedes"] == [first["result_identity"]["id"]]
    assert item["coverage"]["decision_observation_count"] == 1
    assert item["coverage"]["superseded_result_count"] == 1
    assert item["criterion_status"][0]["state"] == "contradicted"
    assert item["fresh_result_admission"]["current_result_identity"]["id"] == second["result_identity"]["id"]
    assert item["fresh_result_admission"]["superseded_result_ids"] == [first["result_identity"]["id"]]
    assert item["fresh_result_admission"]["local_retention"]["historical_record_count"] == 1


def test_evaluation_rejects_stale_mutation_baseline_observation(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    context = _bound_context(tmp_path)
    (tmp_path / "src" / "feature.py").write_text("print('changed')\n", encoding="utf-8")

    with pytest.raises(WorkspaceUsageError, match="dirty-scope|unexpected-path-overlap|scoped-state-fingerprint-changed"):
        append_observation(
            target_root=tmp_path,
            evaluation_id="eval-1969-operating-loop",
            criterion="reconstruction-cost",
            result="supports",
            evidence_refs=["proof-receipts/run-1.json"],
            context=context,
        )


def test_evaluation_rejects_caller_forged_proof_against_authority_receipt(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    context = _bound_context(tmp_path)
    context["proof"]["revision"] = "proof-forged"

    with pytest.raises(WorkspaceUsageError, match="caller-context-stale-or-forged"):
        append_observation(
            target_root=tmp_path,
            evaluation_id="eval-1969-operating-loop",
            criterion="reconstruction-cost",
            result="supports",
            evidence_refs=["proof-receipts/run-1.json"],
            context=context,
        )


def test_evaluation_rejects_authority_store_without_owner_receipts(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    assignment = {
        "target_identity_ref": "user-local:codex-current",
        "context_key": "mechanical-follow-through::mechanical-follow-through",
        "assignment_revision": "assignment-rev-1",
    }
    proof = {
        "result": "passed",
        "verified_by": "aw",
        "revision": "proof-rev-1",
        "provenance": "proof-receipts/run-1.json",
    }

    with pytest.raises(WorkspaceUsageError, match="authority-producer-unresolved"):
        write_observation_authority(
            target_root=tmp_path,
            evaluation_id="eval-1969-operating-loop",
            assignment=assignment,
            proof=proof,
            changed_paths=["src/feature.py"],
        )


def test_evaluation_summary_marks_result_stale_after_same_path_mutation(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context=_bound_context(tmp_path),
    )

    (tmp_path / "src" / "feature.py").write_text("print('changed-after-admission')\n", encoding="utf-8")
    summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")

    item = summary["summaries"][0]
    assert item["fresh_result_admission"]["status"] == "stale-bound"
    assert item["coverage"]["decision_observation_count"] == 0
    assert item["coverage"]["stale_authority_count"] == 1
    freshness = item["fresh_result_admission"]["current_result_resolution"]["freshness_records"][0]
    assert freshness["status"] == "stale"
    assert freshness["reason"] in {"scoped-state-fingerprint-changed", "unexpected-path-overlap", "dirty-scope-not-accounted"}
    assert item["conclusion_readiness"] == {"ready": False, "reason_code": "requires-bound-current-observation"}


def test_evaluation_summary_marks_result_stale_after_proof_replacement(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context=_bound_context(tmp_path, proof_revision="proof-rev-1"),
    )
    _bound_context(tmp_path, proof_revision="proof-rev-2")

    summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")

    item = summary["summaries"][0]
    freshness = item["fresh_result_admission"]["current_result_resolution"]["freshness_records"][0]
    assert item["fresh_result_admission"]["status"] == "stale-bound"
    assert freshness["reason"] == "authority-context-changed"
    assert "proof.revision" in freshness["mismatched_fields"]


def test_evaluation_observation_append_is_idempotent(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    context = _bound_context(tmp_path)
    first = append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context=context,
    )
    second = append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context=context,
    )

    observations = (tmp_path / WORKSPACE_LOCAL_EVALUATIONS_DIR / "eval-1969-operating-loop.jsonl").read_text(encoding="utf-8").splitlines()
    assert first["outcome"] == "appended"
    assert second["outcome"] == "duplicate"
    assert second["idempotency_key"] == first["idempotency_key"]
    assert len(observations) == 1


def test_evaluation_append_enforces_retention_cap_inside_locked_write(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    path = tmp_path / WORKSPACE_LOCAL_EVALUATIONS_DIR / "eval-1969-operating-loop.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    historical = []
    for index in range(OBSERVATION_RETENTION_CAP + 5):
        historical.append(
            {
                "kind": EVALUATION_OBSERVATION_KIND,
                "recorded_at": f"2026-07-22T00:00:{index % 60:02d}Z",
                "evaluation_id": "eval-1969-operating-loop",
                "definition_revision": 1,
                "criterion": "reconstruction-cost",
                "result": "supports",
                "context": {},
                "evidence_refs": [f"old-{index}"],
                "confidence": "medium",
                "burden": "medium",
                "finding": "old",
                "recommended_action": "",
                "idempotency_key": f"old-{index}",
                "admission": {"status": "legacy-unbound", "reason": "seed"},
                "result_identity": {
                    "kind": "agentic-workspace/evaluation-result-identity/v1",
                    "id": f"old-{index}",
                    "status": "historical",
                    "evaluation_id": "eval-1969-operating-loop",
                    "definition_revision": 1,
                    "criterion": "reconstruction-cost",
                },
                "supersedes": [],
            }
        )
    path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in historical), encoding="utf-8")

    observed = append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context=_bound_context(tmp_path),
    )

    retained = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert observed["storage"]["retention_status"] == "compacted"
    assert len(retained) <= OBSERVATION_RETENTION_CAP
    assert any(item.get("idempotency_key") == observed["idempotency_key"] for item in retained)
    assert (tmp_path / WORKSPACE_LOCAL_EVALUATIONS_DIR / "eval-1969-operating-loop.compaction.json").exists()


def test_evaluation_prune_compacts_historical_local_residue(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    first = append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context=_bound_context(tmp_path, proof_revision="proof-rev-1"),
        finding="first",
    )
    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="contradicts",
        evidence_refs=["proof-receipts/run-2.json"],
        context=_bound_context(tmp_path, proof_revision="proof-rev-2"),
        finding="second",
    )

    dry_run = prune_observations(target_root=tmp_path, evaluation_id="eval-1969-operating-loop", dry_run=True)
    receipt = prune_observations(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")

    assert dry_run["status"] == "would-compact"
    assert receipt["status"] == "compacted"
    assert receipt["compacted_count"] == 1
    assert receipt["lineage_summary"][0]["result_identity"] == first["result_identity"]["id"]
    assert receipt["archive_cleanup"]["raw_local_residue_removed"] is True
    assert (tmp_path / WORKSPACE_LOCAL_EVALUATIONS_DIR / "eval-1969-operating-loop.compaction.json").exists()


def test_evaluation_cannot_absorb_missing_implementation_proof() -> None:
    evaluation = {
        "evaluation_id": "eval-1969-operating-loop",
        "decision_owner": {"id": "workspace-maintainer", "class": "maintainer"},
        "criteria": [{"id": "cost"}],
        "evidence_sources": [{"id": "session-log", "class": "log"}],
        "report_sinks": [{"id": "#1969", "class": "closed-issue"}],
        "collection_policy": {"minimum_observations": 1},
        "conclusion_policy": {"rule": "owner-review"},
    }

    blocked = closure_authority(implementation_complete=False, proof_complete=True, evaluation=evaluation)
    assert blocked["issue_closure_authorized"] is False
    assert blocked["blocked_reasons"] == ["implementation-incomplete"]

    authorized = closure_authority(implementation_complete=True, proof_complete=True, evaluation=evaluation)
    assert authorized["issue_closure_authorized"] is True
    Draft202012Validator(contract_schema("evaluation_closure_authority.schema.json")).validate(authorized)


def test_vague_collect_more_evidence_does_not_authorize_closure() -> None:
    vague = {"evaluation_id": "maybe-later", "decision_owner": {"id": "owner", "class": "maintainer"}}

    result = closure_authority(implementation_complete=True, proof_complete=True, evaluation=vague)

    assert result["issue_closure_authorized"] is False
    assert result["blocked_reasons"] == ["longitudinal-evaluation-invalid"]


def test_evaluation_closure_authority_requires_fresh_bound_summary(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    empty_summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")

    blocked = closure_authority(implementation_complete=True, proof_complete=True, evaluation=empty_summary)
    assert blocked["issue_closure_authorized"] is False
    assert blocked["evaluation_admission"] == "invalid"
    assert blocked["blocked_reasons"] == ["longitudinal-evaluation-invalid"]

    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context=_bound_context(tmp_path),
    )
    fresh_summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")

    authorized = closure_authority(implementation_complete=True, proof_complete=True, evaluation=fresh_summary)
    assert authorized["issue_closure_authorized"] is True
    assert authorized["evaluation_admission"] == "fresh-bound-ready"


def test_evaluation_material_finding_requires_bounded_followup_before_closure(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="contradicts",
        evidence_refs=["proof-receipts/run-1.json"],
        context=_bound_context(tmp_path),
        finding="The ordinary path still loses review ownership.",
        recommended_action="Create or reopen one bounded follow-up owner.",
    )

    blocked_summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")
    blocked_item = blocked_summary["summaries"][0]
    assert blocked_item["conclusion_readiness"] == {"ready": False, "reason_code": "material-finding-followup-unresolved"}
    assert blocked_item["next_collection_action"] == "shape-or-resolve-material-finding-owner"
    assert blocked_item["fresh_result_admission"]["finding_followup"]["required_action"] == "create-or-reopen-bounded-follow-up"
    blocked_closure = closure_authority(implementation_complete=True, proof_complete=True, evaluation=blocked_summary)
    assert blocked_closure["issue_closure_authorized"] is False

    continued_observation = append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="contradicts",
        evidence_refs=["proof-receipts/run-2.json"],
        context=_bound_context(tmp_path, proof_revision="proof-rev-2"),
        finding="The ordinary path still loses review ownership.",
        recommended_action="Continue under #2272-follow-up.",
    )
    followup_owner = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "eval-follow-up.plan.json"
    followup_owner.parent.mkdir(parents=True, exist_ok=True)
    followup_owner.write_text(
        json.dumps({"kind": "agentic-planning/execplan/v1", "id": "eval-follow-up", "status": "active"}),
        encoding="utf-8",
    )
    record_material_finding_followup(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        result_identity=continued_observation["result_identity"]["id"],
        owner_ref=".agentic-workspace/planning/execplans/eval-follow-up.plan.json",
        status="continued",
    )
    continued_summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")

    continued_item = continued_summary["summaries"][0]
    assert continued_item["fresh_result_admission"]["finding_followup"]["status"] == "resolved"
    assert continued_item["fresh_result_admission"]["finding_followup"]["routing_receipt_count"] == 1
    assert continued_item["conclusion_readiness"] == {"ready": True, "reason_code": "ready"}
    assert (
        closure_authority(implementation_complete=True, proof_complete=True, evaluation=continued_summary)["issue_closure_authorized"]
        is True
    )


def test_evaluation_cli_register_observe_status(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    criteria = json.dumps({"cost": {"type": "qualitative", "question": "Was cost reduced?", "success_condition": "Cost is lower."}})
    owner = json.dumps({"id": "workspace-maintainer", "class": "maintainer"})

    assert (
        cli.main(
            [
                "evaluation",
                "--target",
                str(tmp_path),
                "--format",
                "json",
                "register",
                "--evaluation-id",
                "eval-cost",
                "--question",
                "Does the change lower operating cost?",
                "--criteria",
                criteria,
                "--decision-owner",
                owner,
                "--evidence-sources",
                "session-log",
                "--report-sinks",
                "#1969",
            ]
        )
        == 0
    )
    registered = json.loads(capsys.readouterr().out)
    assert registered["outcome"] == "registered"

    assert (
        cli.main(
            [
                "evaluation",
                "--target",
                str(tmp_path),
                "--format",
                "json",
                "observe",
                "--evaluation-id",
                "eval-cost",
                "--criterion",
                "cost",
                "--result",
                "supports",
                "--evidence-refs",
                "session-log#1",
                "--context",
                json.dumps(_bound_context(tmp_path, evaluation_id="eval-cost")),
            ]
        )
        == 0
    )
    observed = json.loads(capsys.readouterr().out)
    assert observed["outcome"] == "appended"

    assert cli.main(["evaluation", "--target", str(tmp_path), "--format", "json", "status", "--evaluation-id", "eval-cost"]) == 0
    status = json.loads(capsys.readouterr().out)
    summary = status["summaries"][0]
    assert summary["fresh_result_admission"]["status"] == "fresh-bound"
    assert summary["conclusion_readiness"]["ready"] is True
    assert summary["next_collection_action"] == "owner-review-or-conclude"

    assert (
        cli.main(["evaluation", "--target", str(tmp_path), "--format", "json", "prune", "--evaluation-id", "eval-cost", "--dry-run"]) == 0
    )
    prune = json.loads(capsys.readouterr().out)
    assert prune["operation_id"] == "evaluation.prune"


def test_evaluation_report_delivery_generated_operation_family_fails_closed_without_host_trust(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("schema_version = 1\n\n[workspace]\nenabled = true\n", encoding="utf-8")
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    invocation = [sys.executable, str(ROOT / "scripts" / "run_agentic_workspace.py")]

    from agentic_workspace.generated_operations import (
        evaluation_delivery_status,
        evaluation_external_adapter_receipt,
        evaluation_external_host_result_import,
        evaluation_external_request,
        evaluation_local_delivery,
        evaluation_report_preview,
    )

    preview = evaluation_report_preview(
        {"evaluation_id": "eval-1969-operating-loop", "explicit": True},
        target=tmp_path,
        invocation=invocation,
    )
    assert preview["status"] == "ready"
    local = evaluation_local_delivery(
        {"evaluation_id": "eval-1969-operating-loop", "explicit": True},
        target=tmp_path,
        invocation=invocation,
    )
    assert local["receipt"]["external_delivery"].startswith("unattempted")
    request = evaluation_external_request(
        {"evaluation_id": "eval-1969-operating-loop", "explicit": True},
        target=tmp_path,
        invocation=invocation,
    )
    assert request["status"] == "adapter-required"
    pending = evaluation_delivery_status(
        {"evaluation_id": "eval-1969-operating-loop", "explicit": True},
        target=tmp_path,
        invocation=invocation,
    )
    assert pending["status"] == "pending"
    host = _write_external_evaluation_adapter_host_result(
        tmp_path,
        delivery_id=request["delivery_id"],
        sink_id="#1969",
        producer="github-issues-adapter",
        attempt_revision="attempt-public-1",
        receipt_revision="receipt-public-1",
        capability_revision="github-issues-adapter:v1",
        status="failed",
        import_result=False,
    )
    host_invocation = _external_evaluation_host_trusted_invocation(host)
    with pytest.raises(AWClientError, match="AW operation failed"):
        evaluation_external_host_result_import(
            {
                "provider_result_ref": str(host["provider_result_ref"]),
                "expected_result_digest": str(host["provider_result_digest"]),
                "capability_revision": "github-issues-adapter:v1",
            },
            target=tmp_path,
            invocation=host_invocation,
        )
    with pytest.raises(AWClientError, match="AW operation failed"):
        evaluation_external_adapter_receipt(
            {
                "delivery_id": request["delivery_id"],
                "sink_id": "#1969",
                "producer": "github-issues-adapter",
                "attempt_revision": "attempt-public-1",
                "receipt_revision": "receipt-public-1",
                "capability_revision": "github-issues-adapter:v1",
                "status": "failed",
                "host_result_ref": host["result_ref"],
            },
            target=tmp_path,
            invocation=host_invocation,
        )
