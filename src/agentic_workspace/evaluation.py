from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentic_workspace.authority_envelope import admit_live_mutation_boundary, mutation_baseline_payload
from agentic_workspace.config import WorkspaceUsageError

EVALUATIONS_KIND = "agentic-workspace/evaluations/v1"
EVALUATION_SUMMARY_KIND = "agentic-workspace/evaluation-summary/v1"
EVALUATION_OBSERVATION_KIND = "agentic-workspace/evaluation-observation/v1"
EVALUATION_CLOSURE_AUTHORITY_KIND = "agentic-workspace/evaluation-closure-authority/v1"
WORKSPACE_EVALUATIONS_PATH = Path(".agentic-workspace/evaluations.json")
WORKSPACE_LOCAL_EVALUATIONS_DIR = Path(".agentic-workspace/local/evaluations")
EXTERNAL_EVALUATION_ADAPTER_RECEIPT_DIR = WORKSPACE_LOCAL_EVALUATIONS_DIR / "external-adapter-receipts"
EVALUATION_PENDING_COLLECTIONS_DIR = WORKSPACE_LOCAL_EVALUATIONS_DIR / "pending-collections"
ASSIGNMENT_AUTHORITY_RECEIPT_DIR = Path(".agentic-workspace/planning/assignment-receipts")
PROOF_AUTHORITY_RECEIPT_DIR = Path(".agentic-workspace/proof/receipts")
EVALUATION_FINDING_FOLLOWUPS_PATH = Path(".agentic-workspace/planning/evaluation-finding-followups.json")
EVALUATION_OWNER_RECEIPT_INDEX_KIND = "agentic-workspace/evaluation-owner-receipt-index/v1"
EXTERNAL_EVALUATION_ADAPTER_RECEIPT_INDEX_KIND = "agentic-workspace/evaluation-external-delivery-adapter-receipt-index/v1"
EVALUATION_FINDING_FOLLOWUPS_KIND = "agentic-workspace/evaluation-finding-followups/v1"
OBSERVATION_RETENTION_CAP = 100
OBSERVATION_BYTE_CAP = 256_000

EVALUATION_LIFECYCLES = (
    "collecting",
    "enough-signal",
    "satisfied",
    "contradicted",
    "inconclusive",
    "paused",
    "superseded",
    "archived",
)
TERMINAL_LIFECYCLES = {"satisfied", "contradicted", "inconclusive", "superseded", "archived"}
VALID_TRANSITIONS: dict[str, set[str]] = {
    "collecting": {"enough-signal", "satisfied", "contradicted", "inconclusive", "paused", "superseded", "archived"},
    "enough-signal": {"collecting", "satisfied", "contradicted", "inconclusive", "paused", "superseded", "archived"},
    "paused": {"collecting", "superseded", "archived"},
    "satisfied": {"archived"},
    "contradicted": {"archived"},
    "inconclusive": {"collecting", "archived"},
    "superseded": {"archived"},
    "archived": set(),
}
VALID_CRITERION_TYPES = {"boolean", "ordinal", "numeric", "qualitative", "coverage"}
VALID_OBSERVATION_RESULTS = {"supports", "contradicts", "mixed", "not-applicable", "unknown"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_BURDEN = {"low", "medium", "high"}
LOG_OWNER_CLASSES = {"log", "transcript", "event-stream", "metric-stream"}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_json(path: Path, *, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkspaceUsageError(f"{path.as_posix()} is not valid JSON: {exc.msg}.") from exc
    if not isinstance(payload, dict):
        raise WorkspaceUsageError(f"{path.as_posix()} must contain a JSON object.")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8", newline="\n")
    tmp_path.replace(path)


class _LocalFileLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None

    def __enter__(self) -> "_LocalFileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(self._fd, str(os.getpid()).encode("utf-8"))
        except FileExistsError as exc:
            raise WorkspaceUsageError(f"evaluation observation store is locked: {self.path.as_posix()}.") from exc
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        self.path.unlink(missing_ok=True)


def _definitions_payload(target_root: Path) -> dict[str, Any]:
    path = target_root / WORKSPACE_EVALUATIONS_PATH
    payload = _load_json(path, default={"kind": EVALUATIONS_KIND, "evaluations": []})
    if payload.get("kind") != EVALUATIONS_KIND:
        raise WorkspaceUsageError(f"{WORKSPACE_EVALUATIONS_PATH.as_posix()} must set kind to {EVALUATIONS_KIND}.")
    evaluations = payload.get("evaluations")
    if not isinstance(evaluations, list):
        raise WorkspaceUsageError(f"{WORKSPACE_EVALUATIONS_PATH.as_posix()} evaluations must be a list.")
    return payload


def _definition_by_id(payload: dict[str, Any], evaluation_id: str) -> dict[str, Any] | None:
    for item in payload["evaluations"]:
        if isinstance(item, dict) and item.get("id") == evaluation_id:
            return item
    return None


def _require_non_empty(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise WorkspaceUsageError(f"{field} is required.")
    return text


def _split_csv(value: str | None) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _parse_json_object(value: str | None, field: str, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if value is None or not str(value).strip():
        return dict(default or {})
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise WorkspaceUsageError(f"{field} must be a JSON object: {exc.msg}.") from exc
    if not isinstance(payload, dict):
        raise WorkspaceUsageError(f"{field} must be a JSON object.")
    return payload


def _parse_criteria(value: str | None) -> list[dict[str, Any]]:
    raw = _parse_json_object(value, "criteria", default={})
    if not raw:
        raise WorkspaceUsageError("criteria is required and must declare at least one criterion.")
    criteria: list[dict[str, Any]] = []
    for criterion_id, spec in raw.items():
        if not isinstance(spec, dict):
            raise WorkspaceUsageError(f"criteria.{criterion_id} must be an object.")
        criterion_type = str(spec.get("type") or "qualitative")
        if criterion_type not in VALID_CRITERION_TYPES:
            allowed = ", ".join(sorted(VALID_CRITERION_TYPES))
            raise WorkspaceUsageError(f"criteria.{criterion_id}.type must be one of: {allowed}.")
        criteria.append(
            {
                "id": str(criterion_id),
                "type": criterion_type,
                "question": _require_non_empty(spec.get("question"), f"criteria.{criterion_id}.question"),
                "success_condition": _require_non_empty(spec.get("success_condition"), f"criteria.{criterion_id}.success_condition"),
                "required": bool(spec.get("required", True)),
            }
        )
    return criteria


def _validate_owner(owner: dict[str, Any], *, field: str) -> None:
    owner_id = _require_non_empty(owner.get("id"), f"{field}.id")
    owner_class = _require_non_empty(owner.get("class"), f"{field}.class")
    if owner_class in LOG_OWNER_CLASSES:
        raise WorkspaceUsageError(
            f"{field} {owner_id!r} is a {owner_class}; logs may be evidence sources or sinks but not decision owners."
        )


def _validate_definition(definition: dict[str, Any]) -> None:
    _require_non_empty(definition.get("id"), "id")
    _require_non_empty(definition.get("question"), "question")
    criteria = definition.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise WorkspaceUsageError("criteria must contain at least one criterion.")
    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise WorkspaceUsageError("criteria entries must be objects.")
        if criterion.get("type") not in VALID_CRITERION_TYPES:
            raise WorkspaceUsageError(f"criterion {criterion.get('id')!r} has unsupported type.")
    owner = definition.get("decision_owner")
    if not isinstance(owner, dict):
        raise WorkspaceUsageError("decision_owner is required.")
    _validate_owner(owner, field="decision_owner")
    if not isinstance(definition.get("evidence_sources"), list) or not definition["evidence_sources"]:
        raise WorkspaceUsageError("evidence_sources must contain at least one source.")
    if not isinstance(definition.get("report_sinks"), list) or not definition["report_sinks"]:
        raise WorkspaceUsageError("report_sinks must contain at least one sink.")
    if definition.get("lifecycle") not in EVALUATION_LIFECYCLES:
        raise WorkspaceUsageError("lifecycle is invalid.")


def _evaluation_admission_contract() -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/evaluation-admission-contract/v1",
        "status": "fail-closed-for-bound-results",
        "required_context": [
            "assignment.target_identity_ref",
            "assignment.context_key",
            "assignment.assignment_revision",
            "authority_envelope.mutation_baseline.baseline_id",
            "authority_envelope.mutation_baseline.head",
            "authority_envelope.mutation_baseline.scope.allowed_paths",
            "proof.provenance",
            "proof.verified_by=aw",
        ],
        "reject_when": [
            "assignment-target-mismatch",
            "baseline-head-changed",
            "scope-expanded",
            "stale-worktree",
            "failed-proof",
            "missing-bound-context",
            "superseded-result",
        ],
        "consumers": ["status", "doctor", "operating-decision", "proof-selection", "closure"],
        "repair_route": "rerun or supersede the evaluation result after refreshing assignment, authority, baseline, and proof context",
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def _owner_receipt_path(*, target_root: Path, store_root: Path, receipt_ref: str) -> Path:
    text = receipt_ref.strip()
    if not text:
        raise WorkspaceUsageError("evaluation owner receipt reference is required.")
    root = (target_root / store_root).resolve()
    if "://" in text:
        receipt_id = text.rsplit("/", 1)[-1].strip().replace(":", "-")
        if not receipt_id:
            raise WorkspaceUsageError("evaluation owner receipt reference has no stable id.")
        return root / f"{receipt_id}.json"
    candidate = Path(text)
    if candidate.is_absolute():
        raise WorkspaceUsageError("evaluation owner receipt reference must be repo-relative.")
    resolved = (target_root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise WorkspaceUsageError("evaluation owner receipt reference must resolve inside its owning store.")
    return resolved


def _load_indexed_owner_receipt(
    *,
    target_root: Path,
    store_root: Path,
    receipt_ref: str,
    expected_kind: str,
    expected_producer: str,
) -> dict[str, Any]:
    path = _owner_receipt_path(target_root=target_root, store_root=store_root, receipt_ref=receipt_ref)
    receipt = _load_json(path, default={})
    receipt_id = str(receipt.get("receipt_id") or path.stem).strip()
    index = _load_json((target_root / store_root / "index.json").resolve(), default={})
    entries = index.get("receipts") if index.get("kind") == EVALUATION_OWNER_RECEIPT_INDEX_KIND else {}
    entry = entries.get(receipt_id) if isinstance(entries, dict) else None
    if not isinstance(entry, dict):
        raise WorkspaceUsageError("evaluation owner receipt is not registered in its owner store index.")
    indexed_path = ((target_root / store_root).resolve() / str(entry.get("path") or "")).resolve()
    if indexed_path != path.resolve():
        raise WorkspaceUsageError("evaluation owner receipt index path does not match the resolved receipt.")
    if str(entry.get("status") or receipt.get("status") or "current") not in {"current", "fresh", "accepted"}:
        raise WorkspaceUsageError("evaluation owner receipt is not current.")
    if entry.get("superseded_by") or receipt.get("superseded_by") or receipt.get("revoked_at"):
        raise WorkspaceUsageError("evaluation owner receipt is superseded or revoked.")
    if receipt.get("kind") != expected_kind:
        raise WorkspaceUsageError("evaluation owner receipt kind does not match the expected producer.")
    if receipt.get("producer") != expected_producer:
        raise WorkspaceUsageError("evaluation owner receipt producer does not match the expected owner.")
    if str(entry.get("revision") or "") and str(receipt.get("revision") or "") and entry.get("revision") != receipt.get("revision"):
        raise WorkspaceUsageError("evaluation owner receipt revision does not match the owner store index.")
    return receipt


def _write_indexed_owner_receipt(
    *,
    target_root: Path,
    store_root: Path,
    receipt_id: str,
    payload: dict[str, Any],
) -> str:
    safe_id = receipt_id.strip().replace(":", "-")
    if not safe_id:
        raise WorkspaceUsageError("receipt_id is required.")
    root = target_root / store_root
    root.mkdir(parents=True, exist_ok=True)
    receipt = {**payload, "receipt_id": payload.get("receipt_id") or safe_id, "status": payload.get("status") or "current"}
    path = root / f"{safe_id}.json"
    _write_json(path, receipt)
    index_path = root / "index.json"
    index = _load_json(index_path, default={"kind": EVALUATION_OWNER_RECEIPT_INDEX_KIND, "receipts": {}})
    raw_receipts = index.get("receipts")
    receipts = raw_receipts if isinstance(raw_receipts, dict) else {}
    receipts[receipt["receipt_id"]] = {
        "path": path.relative_to(root).as_posix(),
        "status": receipt.get("status"),
        "revision": receipt.get("revision"),
    }
    _write_json(index_path, {"kind": EVALUATION_OWNER_RECEIPT_INDEX_KIND, "receipts": receipts})
    return f"aw://{store_root.as_posix()}/{safe_id}"


def _local_receipt_path(*, target_root: Path, store_root: Path, receipt_ref: str, field: str) -> Path:
    text = str(receipt_ref or "").strip()
    if not text:
        raise WorkspaceUsageError(f"{field} is required.")
    if "://" in text:
        raise WorkspaceUsageError(f"{field} must be a repo-relative local receipt path.")
    candidate = Path(text)
    if candidate.is_absolute():
        raise WorkspaceUsageError(f"{field} must be repo-relative.")
    root = (target_root / store_root).resolve()
    resolved = (target_root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise WorkspaceUsageError(f"{field} must resolve inside {store_root.as_posix()}.")
    return resolved


def _load_external_delivery_adapter_receipt(*, target_root: Path, receipt_ref: str) -> dict[str, Any]:
    path = _local_receipt_path(
        target_root=target_root,
        store_root=EXTERNAL_EVALUATION_ADAPTER_RECEIPT_DIR,
        receipt_ref=receipt_ref,
        field="adapter_receipt_ref",
    )
    raw_bytes = path.read_bytes()
    receipt = _load_json(path, default={})
    receipt_id = str(receipt.get("receipt_id") or path.stem).strip()
    index_path = (target_root / EXTERNAL_EVALUATION_ADAPTER_RECEIPT_DIR / "index.json").resolve()
    index = _load_json(index_path, default={})
    entries = index.get("receipts") if index.get("kind") == EXTERNAL_EVALUATION_ADAPTER_RECEIPT_INDEX_KIND else {}
    entry = entries.get(receipt_id) if isinstance(entries, dict) else None
    if not isinstance(entry, dict):
        raise WorkspaceUsageError("external evaluation adapter receipt is not registered in the provider-owned receipt index.")
    indexed_path = ((target_root / EXTERNAL_EVALUATION_ADAPTER_RECEIPT_DIR).resolve() / str(entry.get("path") or "")).resolve()
    if indexed_path != path.resolve():
        raise WorkspaceUsageError("external evaluation adapter receipt index path does not match the resolved receipt.")
    if str(entry.get("status") or receipt.get("status") or "") not in {"current", "fresh", "accepted", "delivered", "failed"}:
        raise WorkspaceUsageError("external evaluation adapter receipt index entry is not current.")
    if entry.get("superseded_by") or entry.get("revoked_at") or receipt.get("superseded_by") or receipt.get("revoked_at"):
        raise WorkspaceUsageError("external evaluation adapter receipt is superseded or revoked.")
    if str(entry.get("producer") or receipt.get("producer") or "").strip() != str(receipt.get("producer") or "").strip():
        raise WorkspaceUsageError("external evaluation adapter receipt producer does not match the provider-owned index.")
    if str(entry.get("receipt_revision") or "") and str(entry.get("receipt_revision")) != str(receipt.get("receipt_revision") or ""):
        raise WorkspaceUsageError("external evaluation adapter receipt revision does not match the provider-owned index.")
    if str(entry.get("capability_revision") or "") and str(entry.get("capability_revision")) != str(
        receipt.get("capability_revision") or ""
    ):
        raise WorkspaceUsageError("external evaluation adapter capability revision does not match the provider-owned index.")
    receipt.setdefault("source_ref", path.relative_to(target_root).as_posix())
    receipt["_source_ref"] = path.relative_to(target_root).as_posix()
    receipt["_source_digest"] = hashlib.sha256(raw_bytes).hexdigest()
    receipt["_index_ref"] = index_path.relative_to(target_root).as_posix()
    return receipt


def record_external_evaluation_adapter_receipt(
    *,
    target_root: Path,
    delivery_id: str,
    sink_id: str,
    producer: str,
    attempt_revision: str,
    receipt_revision: str,
    capability_revision: str,
    status: str,
    detail: str = "",
    capability_status: str = "current",
    status_owner: str = "provider-adapter",
    supersedes: str = "",
) -> dict[str, Any]:
    """Record the producer-owned receipt consumed by external delivery admission."""
    normalized_status = _require_non_empty(status, "status")
    if normalized_status not in {"delivered", "failed"}:
        raise WorkspaceUsageError("status must be delivered or failed.")
    if status_owner not in {"provider-adapter", "external-operation-adapter"}:
        raise WorkspaceUsageError("status_owner must identify the provider adapter.")
    if capability_status not in {"current", "fresh", "accepted"}:
        raise WorkspaceUsageError("capability_status must be current, fresh, or accepted.")
    delivery_identity = _require_non_empty(delivery_id, "delivery_id")
    sink_identity = _require_non_empty(sink_id, "sink_id")
    attempt_identity = _require_non_empty(attempt_revision, "attempt_revision")
    receipt_identity = _require_non_empty(receipt_revision, "receipt_revision")
    producer_identity = _require_non_empty(producer, "producer")
    capability_identity = _require_non_empty(capability_revision, "capability_revision")
    receipt_id = hashlib.sha256(
        json.dumps(
            {
                "delivery_id": delivery_identity,
                "sink_id": sink_identity,
                "producer": producer_identity,
                "attempt_revision": attempt_identity,
                "receipt_revision": receipt_identity,
                "capability_revision": capability_identity,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:24]
    root = target_root / EXTERNAL_EVALUATION_ADAPTER_RECEIPT_DIR
    receipt = {
        "kind": "agentic-workspace/evaluation-external-delivery-adapter-receipt/v1",
        "receipt_id": receipt_id,
        "delivery_id": delivery_identity,
        "sink_id": sink_identity,
        "producer": producer_identity,
        "status_owner": status_owner,
        "attempt_revision": attempt_identity,
        "receipt_revision": receipt_identity,
        "capability_revision": capability_identity,
        "capability_status": capability_status,
        "status": normalized_status,
        "detail": detail,
        "supersedes": supersedes,
        "recorded_at": _now(),
    }
    path = root / f"{receipt_id}.json"
    _write_json(path, receipt)
    index_path = root / "index.json"
    index = _load_json(index_path, default={"kind": EXTERNAL_EVALUATION_ADAPTER_RECEIPT_INDEX_KIND, "receipts": {}})
    raw_entries = index.get("receipts")
    entries: dict[str, Any] = raw_entries if isinstance(raw_entries, dict) else {}
    if supersedes and supersedes in entries and isinstance(entries[supersedes], dict):
        entries[supersedes] = {**entries[supersedes], "status": "superseded", "superseded_by": receipt_id}
    entries[receipt_id] = {
        "path": path.relative_to(root).as_posix(),
        "status": normalized_status,
        "producer": producer_identity,
        "receipt_revision": receipt_identity,
        "capability_revision": capability_identity,
        "capability_status": capability_status,
        "delivery_id": delivery_identity,
        "sink_id": sink_identity,
        "attempt_revision": attempt_identity,
    }
    _write_json(index_path, {"kind": EXTERNAL_EVALUATION_ADAPTER_RECEIPT_INDEX_KIND, "receipts": entries})
    return {
        "kind": "agentic-workspace/evaluation-external-delivery-adapter-receipt-record/v1",
        "status": "recorded",
        "receipt_id": receipt_id,
        "receipt_ref": path.relative_to(target_root).as_posix(),
        "index_ref": index_path.relative_to(target_root).as_posix(),
        "delivery_id": delivery_identity,
        "sink_id": sink_identity,
        "producer": producer_identity,
        "attempt_revision": attempt_identity,
        "receipt_revision": receipt_identity,
        "capability_revision": capability_identity,
        "retryable": normalized_status != "delivered",
    }


def _producer_receipt(
    payload: dict[str, Any],
    *,
    target_root: Path,
    store_root: Path,
    field: str,
    expected_kind: str,
    expected_producer: str,
) -> dict[str, Any]:
    raw_receipt = payload.get("receipt")
    receipt: dict[str, Any] = raw_receipt if isinstance(raw_receipt, dict) else {}
    receipt_ref = str(receipt.get("receipt_ref") or receipt.get("source_ref") or payload.get("receipt_ref") or "").strip()
    owner_receipt: dict[str, Any] = {}
    owner_error = ""
    if receipt_ref:
        try:
            owner_receipt = _load_indexed_owner_receipt(
                target_root=target_root,
                store_root=store_root,
                receipt_ref=receipt_ref,
                expected_kind=expected_kind,
                expected_producer=expected_producer,
            )
        except WorkspaceUsageError as exc:
            owner_error = str(exc)
    missing = [
        key
        for key, value in {
            f"{field}.receipt.kind": receipt.get("kind"),
            f"{field}.receipt.receipt_id": receipt.get("receipt_id"),
            f"{field}.receipt.producer": receipt.get("producer"),
            f"{field}.receipt.revision": receipt.get("revision"),
            f"{field}.receipt.source_ref": receipt_ref,
            f"{field}.owner_receipt": owner_receipt,
        }.items()
        if value in (None, "", [], {})
    ]
    mismatches: list[str] = []
    if receipt.get("kind") not in (None, expected_kind):
        mismatches.append(f"{field}.receipt.kind")
    if receipt.get("producer") not in (None, expected_producer):
        mismatches.append(f"{field}.receipt.producer")
    for key in ("kind", "receipt_id", "producer", "revision"):
        if owner_receipt and receipt.get(key) not in (None, owner_receipt.get(key)):
            mismatches.append(f"{field}.receipt.{key}")
    return {
        "status": "resolved" if not missing and not mismatches else "rejected",
        "receipt_id": owner_receipt.get("receipt_id") or receipt.get("receipt_id"),
        "revision": owner_receipt.get("revision") or receipt.get("revision"),
        "producer": owner_receipt.get("producer") or receipt.get("producer"),
        "receipt_ref": receipt_ref or None,
        "owner_error": owner_error or None,
        "missing_fields": missing,
        "mismatched_fields": mismatches,
        "owner_receipt": owner_receipt or None,
    }


def _authority_producer_resolution(*, target_root: Path, assignment: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    assignment_receipt = _producer_receipt(
        assignment,
        target_root=target_root,
        store_root=ASSIGNMENT_AUTHORITY_RECEIPT_DIR,
        field="assignment",
        expected_kind="agentic-workspace/assignment-authority-receipt/v1",
        expected_producer="assignment.lifecycle",
    )
    proof_receipt = _producer_receipt(
        proof,
        target_root=target_root,
        store_root=PROOF_AUTHORITY_RECEIPT_DIR,
        field="proof",
        expected_kind="agentic-workspace/proof-receipt/v1",
        expected_producer="aw-proof",
    )
    mismatches: list[str] = []
    if assignment_receipt.get("revision") not in (None, assignment.get("assignment_revision")):
        mismatches.append("assignment.receipt.revision")
    if proof_receipt.get("revision") not in (None, proof.get("revision")):
        mismatches.append("proof.receipt.revision")
    if str(proof.get("verified_by") or "").strip() != "aw":
        mismatches.append("proof.verified_by")
    missing = [*assignment_receipt["missing_fields"], *proof_receipt["missing_fields"]]
    mismatches.extend([*assignment_receipt["mismatched_fields"], *proof_receipt["mismatched_fields"]])
    status = "resolved" if not missing and not mismatches else "rejected"
    return {
        "kind": "agentic-workspace/evaluation-authority-producer-resolution/v1",
        "status": status,
        "assignment_receipt": assignment_receipt,
        "proof_receipt": proof_receipt,
        "missing_fields": missing,
        "mismatched_fields": mismatches,
        "rule": (
            "Evaluation observation authority is derived from assignment and proof owner receipts; caller dictionaries "
            "are comparison input only and cannot manufacture producer authority."
        ),
    }


def _result_identity_payload(
    *,
    evaluation_id: str,
    definition_revision: int,
    criterion: str,
    result: str,
    recorded_at: str,
    admission: dict[str, Any],
    proof: dict[str, Any],
) -> dict[str, Any]:
    identity_source = {
        "evaluation_id": evaluation_id,
        "definition_revision": definition_revision,
        "criterion": criterion,
        "result": result,
        "recorded_at": recorded_at,
        "baseline_id": admission.get("baseline_id"),
        "baseline_head": admission.get("baseline_head"),
        "target_identity_ref": admission.get("target_identity_ref"),
        "assignment_revision": admission.get("assignment_revision"),
        "proof_revision": proof.get("revision"),
        "proof_provenance": proof.get("provenance"),
        "proof_receipt_id": proof.get("receipt", {}).get("receipt_id") if isinstance(proof.get("receipt"), dict) else None,
    }
    digest = hashlib.sha256(json.dumps(identity_source, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
    return {
        "kind": "agentic-workspace/evaluation-result-identity/v1",
        "id": f"sha256:{digest[:24]}",
        "status": "current",
        **identity_source,
    }


def _observation_admission(
    *,
    target_root: Path,
    context: dict[str, Any],
    authority: dict[str, Any],
    evaluation_id: str,
    definition_revision: int,
    criterion: str,
    result: str,
    recorded_at: str,
    previous_current_results: list[dict[str, Any]],
) -> dict[str, Any]:
    envelope = authority.get("authority_envelope", {}) if isinstance(authority.get("authority_envelope"), dict) else {}
    baseline = envelope.get("mutation_baseline", {}) if isinstance(envelope.get("mutation_baseline"), dict) else {}
    proof = authority.get("proof", {}) if isinstance(authority.get("proof"), dict) else {}
    assignment = authority.get("assignment", {}) if isinstance(authority.get("assignment"), dict) else {}
    producer_resolution = authority.get("producer_resolution", {}) if isinstance(authority.get("producer_resolution"), dict) else {}
    submitted_proof = context.get("proof", {}) if isinstance(context.get("proof"), dict) else {}
    submitted_assignment = context.get("assignment", {}) if isinstance(context.get("assignment"), dict) else {}
    submitted_authority = context.get("authority_envelope", {}) if isinstance(context.get("authority_envelope"), dict) else {}
    submitted_baseline = (
        submitted_authority.get("mutation_baseline", {}) if isinstance(submitted_authority.get("mutation_baseline"), dict) else {}
    )
    submitted_missing_context = [
        field
        for field, value in {
            "submitted.assignment.target_identity_ref": submitted_assignment.get("target_identity_ref"),
            "submitted.assignment.context_key": submitted_assignment.get("context_key"),
            "submitted.assignment.assignment_revision": submitted_assignment.get("assignment_revision"),
            "submitted.authority_envelope.mutation_baseline": submitted_baseline if submitted_baseline else None,
            "submitted.proof.result": submitted_proof.get("result"),
            "submitted.proof.verified_by": submitted_proof.get("verified_by"),
            "submitted.proof.provenance": submitted_proof.get("provenance"),
        }.items()
        if value in (None, "", [], {})
    ]
    if submitted_missing_context:
        return {
            "status": "rejected",
            "reason": "missing-bound-context",
            "missing_fields": submitted_missing_context,
            "repair_route": "observe with submitted context copied from the current AW authority receipt",
        }
    if producer_resolution.get("status") != "resolved":
        return {
            "status": "rejected",
            "reason": "authority-producer-unresolved",
            "producer_resolution": producer_resolution,
            "repair_route": "record observation authority from assignment/proof owner receipts before observing",
        }
    missing_context = [
        field
        for field, value in {
            "assignment.target_identity_ref": assignment.get("target_identity_ref"),
            "assignment.context_key": assignment.get("context_key"),
            "assignment.assignment_revision": assignment.get("assignment_revision"),
            "assignment.receipt.receipt_id": assignment.get("receipt", {}).get("receipt_id")
            if isinstance(assignment.get("receipt"), dict)
            else None,
            "authority_envelope.mutation_baseline": baseline if baseline else None,
            "proof.result": proof.get("result"),
            "proof.verified_by": proof.get("verified_by"),
            "proof.provenance": proof.get("provenance"),
            "proof.receipt.receipt_id": proof.get("receipt", {}).get("receipt_id") if isinstance(proof.get("receipt"), dict) else None,
        }.items()
        if value in (None, "", [], {})
    ]
    if missing_context:
        return {
            "status": "rejected",
            "reason": "missing-bound-context",
            "missing_fields": missing_context,
            "repair_route": "observe with current assignment identity, live mutation baseline scope, and AW proof receipt",
        }
    mismatches = [
        field
        for field, submitted, resolved in [
            ("assignment.target_identity_ref", submitted_assignment.get("target_identity_ref"), assignment.get("target_identity_ref")),
            ("assignment.context_key", submitted_assignment.get("context_key"), assignment.get("context_key")),
            ("assignment.assignment_revision", submitted_assignment.get("assignment_revision"), assignment.get("assignment_revision")),
            ("proof.revision", submitted_proof.get("revision"), proof.get("revision")),
            (
                "assignment.receipt.receipt_id",
                submitted_assignment.get("receipt", {}).get("receipt_id")
                if isinstance(submitted_assignment.get("receipt"), dict)
                else None,
                assignment.get("receipt", {}).get("receipt_id") if isinstance(assignment.get("receipt"), dict) else None,
            ),
            (
                "proof.receipt.receipt_id",
                submitted_proof.get("receipt", {}).get("receipt_id") if isinstance(submitted_proof.get("receipt"), dict) else None,
                proof.get("receipt", {}).get("receipt_id") if isinstance(proof.get("receipt"), dict) else None,
            ),
            (
                "authority_envelope.mutation_baseline.baseline_id",
                submitted_baseline.get("baseline_id"),
                baseline.get("baseline_id"),
            ),
        ]
        if submitted not in (None, "", [], {}) and submitted != resolved
    ]
    if mismatches:
        return {
            "status": "rejected",
            "reason": "caller-context-stale-or-forged",
            "mismatched_fields": mismatches,
            "repair_route": "refresh the observation context from the current AW authority receipt before observing",
        }
    if str(proof.get("result") or "").strip() != "passed" or str(proof.get("verified_by") or "").strip() != "aw":
        return {
            "status": "rejected",
            "reason": "failed-proof",
            "repair_route": "rerun AW proof before admitting this evaluation observation",
        }
    expected_scope = baseline.get("scope", {}) if isinstance(baseline.get("scope"), dict) else {}
    changed_paths = (
        _string_list(envelope.get("changed_paths"))
        or _string_list(context.get("changed_paths"))
        or _string_list(expected_scope.get("allowed_paths"))
    )
    mutation_admission = admit_live_mutation_boundary(
        boundary_id="evaluation-observation-admission",
        target_root=target_root,
        expected=baseline,
        assignment_target_identity_ref=str(assignment.get("target_identity_ref") or "").strip() or None,
        assignment_revision=str(assignment.get("assignment_revision") or "").strip() or None,
        allowed_paths=changed_paths or None,
    )
    if mutation_admission.get("status") == "rejected":
        first_failure = next((item for item in mutation_admission.get("failures", []) if isinstance(item, dict)), {})
        return {
            "status": "rejected",
            "reason": str(first_failure.get("reason") or "mutation-baseline-revalidation-failed"),
            "mutation_baseline_revalidation": mutation_admission,
            "repair_route": str(first_failure.get("repair") or "refresh mutation baseline and rerun this evaluation observation"),
        }
    result_identity = _result_identity_payload(
        evaluation_id=evaluation_id,
        definition_revision=definition_revision,
        criterion=criterion,
        result=result,
        recorded_at=recorded_at,
        admission={
            "baseline_id": baseline.get("baseline_id"),
            "baseline_head": baseline.get("head"),
            "target_identity_ref": assignment.get("target_identity_ref"),
            "assignment_revision": assignment.get("assignment_revision"),
        },
        proof=proof,
    )
    supersedes = [
        item["result_identity"]["id"]
        for item in previous_current_results
        if isinstance(item.get("result_identity"), dict) and item["result_identity"].get("id")
    ]
    return {
        "status": "admitted",
        "reason": "fresh-bound-context",
        "bound_context": True,
        "baseline_id": baseline.get("baseline_id"),
        "baseline_head": baseline.get("head"),
        "assignment_revision": assignment.get("assignment_revision"),
        "target_identity_ref": assignment.get("target_identity_ref"),
        "mutation_baseline_revalidation": mutation_admission,
        "proof": {"result": proof.get("result"), "verified_by": proof.get("verified_by"), "revision": proof.get("revision")},
        "authority_resolution": {
            "status": "resolved-from-owner-receipts",
            "source": WORKSPACE_LOCAL_EVALUATIONS_DIR.joinpath(f"{evaluation_id}.authority.json").as_posix(),
            "caller_context_trusted": False,
            "producer_resolution": producer_resolution,
        },
        "result_identity": result_identity,
        "supersedes": supersedes,
        "supersession": {
            "status": "supersedes-current-result" if supersedes else "first-current-result",
            "predecessor_count": len(supersedes),
        },
    }


def register_evaluation(
    *,
    target_root: Path,
    evaluation_id: str,
    question: str,
    subject: dict[str, Any],
    criteria: list[dict[str, Any]],
    decision_owner: dict[str, Any],
    evidence_sources: list[dict[str, Any]],
    report_sinks: list[dict[str, Any]],
    selectors: dict[str, Any] | None = None,
    collection_policy: dict[str, Any] | None = None,
    conclusion_policy: dict[str, Any] | None = None,
    action_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _definitions_payload(target_root)
    now = _now()
    existing = _definition_by_id(payload, evaluation_id)
    revision = int(existing.get("revision", 0)) + 1 if existing else 1
    lifecycle = str(existing.get("lifecycle", "collecting")) if existing else "collecting"
    definition = {
        "id": evaluation_id,
        "revision": revision,
        "lifecycle": lifecycle,
        "question": question,
        "subject": subject,
        "criteria": criteria,
        "selectors": selectors or {},
        "collection_policy": collection_policy or {"mode": "local-first", "minimum_observations": 1},
        "decision_owner": decision_owner,
        "evidence_sources": evidence_sources,
        "report_sinks": report_sinks,
        "conclusion_policy": conclusion_policy or {"rule": "owner-reviews-summary", "terminal_states": sorted(TERMINAL_LIFECYCLES)},
        "action_policy": action_policy or {"material_negative_finding": "create-or-reopen-bounded-follow-up"},
        "admission_contract": _evaluation_admission_contract(),
        "created_at": str(existing.get("created_at", now)) if existing else now,
        "updated_at": now,
    }
    _validate_definition(definition)
    if existing:
        payload["evaluations"] = [definition if item is existing else item for item in payload["evaluations"]]
        outcome = "updated"
    else:
        payload["evaluations"].append(definition)
        outcome = "registered"
    _write_json(target_root / WORKSPACE_EVALUATIONS_PATH, payload)
    return {
        "kind": EVALUATIONS_KIND,
        "path": WORKSPACE_EVALUATIONS_PATH.as_posix(),
        "outcome": outcome,
        "evaluation_id": evaluation_id,
        "revision": revision,
        "lifecycle": lifecycle,
    }


def register_evaluation_from_values(*, target_root: Path, values: dict[str, Any]) -> dict[str, Any]:
    return register_evaluation(
        target_root=target_root,
        evaluation_id=_require_non_empty(values.get("evaluation_id"), "evaluation_id"),
        question=_require_non_empty(values.get("question"), "question"),
        subject=_parse_json_object(values.get("subject"), "subject", default={"type": "workspace-task"}),
        criteria=_parse_criteria(values.get("criteria")),
        decision_owner=_parse_json_object(values.get("decision_owner"), "decision_owner"),
        evidence_sources=[{"id": item, "class": "external-ref"} for item in _split_csv(values.get("evidence_sources"))],
        report_sinks=[{"id": item, "class": "issue-or-report"} for item in _split_csv(values.get("report_sinks"))],
        selectors=_parse_json_object(values.get("selectors"), "selectors", default={}),
        collection_policy=_parse_json_object(values.get("collection_policy"), "collection_policy", default={}),
        conclusion_policy=_parse_json_object(values.get("conclusion_policy"), "conclusion_policy", default={}),
        action_policy=_parse_json_object(values.get("action_policy"), "action_policy", default={}),
    )


def _observation_path(target_root: Path, evaluation_id: str) -> Path:
    return target_root / WORKSPACE_LOCAL_EVALUATIONS_DIR / f"{evaluation_id}.jsonl"


def _observation_authority_path(target_root: Path, evaluation_id: str) -> Path:
    return target_root / WORKSPACE_LOCAL_EVALUATIONS_DIR / f"{evaluation_id}.authority.json"


def write_observation_authority(
    *,
    target_root: Path,
    evaluation_id: str,
    assignment: dict[str, Any],
    proof: dict[str, Any],
    changed_paths: list[str],
) -> dict[str, Any]:
    producer_resolution = _authority_producer_resolution(target_root=target_root, assignment=assignment, proof=proof)
    if producer_resolution["status"] != "resolved":
        missing = ", ".join([*producer_resolution["missing_fields"], *producer_resolution["mismatched_fields"]])
        raise WorkspaceUsageError(
            "evaluation observation authority rejected (authority-producer-unresolved): "
            f"assignment/proof producer receipts are required ({missing})."
        )
    assignment_owner_receipt = producer_resolution["assignment_receipt"]["owner_receipt"]
    proof_owner_receipt = producer_resolution["proof_receipt"]["owner_receipt"]
    if not isinstance(assignment_owner_receipt, dict) or not isinstance(proof_owner_receipt, dict):
        raise WorkspaceUsageError("evaluation observation authority rejected (authority-producer-unresolved): owner receipts are required.")
    resolved_assignment = {
        "target_identity_ref": assignment_owner_receipt.get("target_identity_ref"),
        "context_key": assignment_owner_receipt.get("context_key"),
        "assignment_revision": assignment_owner_receipt.get("revision"),
        "receipt": {
            "kind": assignment_owner_receipt.get("kind"),
            "receipt_id": assignment_owner_receipt.get("receipt_id"),
            "producer": assignment_owner_receipt.get("producer"),
            "revision": assignment_owner_receipt.get("revision"),
            "source_ref": producer_resolution["assignment_receipt"].get("receipt_ref"),
        },
    }
    resolved_proof = {
        "result": proof_owner_receipt.get("result"),
        "verified_by": proof_owner_receipt.get("verified_by"),
        "revision": proof_owner_receipt.get("revision"),
        "provenance": proof_owner_receipt.get("provenance"),
        "receipt": {
            "kind": proof_owner_receipt.get("kind"),
            "receipt_id": proof_owner_receipt.get("receipt_id"),
            "producer": proof_owner_receipt.get("producer"),
            "revision": proof_owner_receipt.get("revision"),
            "source_ref": producer_resolution["proof_receipt"].get("receipt_ref"),
            "subject": proof_owner_receipt.get("subject"),
        },
    }
    baseline = mutation_baseline_payload(
        target_root=target_root,
        changed_paths=changed_paths,
        assignment_target_identity_ref=str(resolved_assignment.get("target_identity_ref") or "").strip() or None,
        assignment_revision=str(resolved_assignment.get("assignment_revision") or "").strip() or None,
    )
    payload = {
        "kind": "agentic-workspace/evaluation-observation-authority/v1",
        "evaluation_id": evaluation_id,
        "assignment": resolved_assignment,
        "proof": resolved_proof,
        "producer_resolution": producer_resolution,
        "authority_envelope": {"mutation_baseline": baseline, "changed_paths": changed_paths},
        "recorded_at": _now(),
        "owner": "aw-evaluation-authority-store",
        "owner_rule": "Only assignment/proof owner receipts can advance this local authority record; observe callers supply stale/forgery comparison context only.",
    }
    _write_json(_observation_authority_path(target_root, evaluation_id), payload)
    return payload


def _load_observation_authority(target_root: Path, evaluation_id: str) -> dict[str, Any]:
    path = _observation_authority_path(target_root, evaluation_id)
    payload = _load_json(path, default={})
    if not payload:
        raise WorkspaceUsageError(
            f"evaluation observation authority is missing for {evaluation_id!r}; run or record AW-owned assignment/proof authority first."
        )
    return payload


def _load_observations(target_root: Path, evaluation_id: str) -> list[dict[str, Any]]:
    path = _observation_path(target_root, evaluation_id)
    if not path.exists():
        return []
    observations: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WorkspaceUsageError(f"{path.as_posix()} line {line_number} is invalid JSON: {exc.msg}.") from exc
        if not isinstance(payload, dict):
            raise WorkspaceUsageError(f"{path.as_posix()} line {line_number} must be a JSON object.")
        observations.append(payload)
    return observations


def _finding_followups_payload(target_root: Path) -> dict[str, Any]:
    payload = _load_json(
        target_root / EVALUATION_FINDING_FOLLOWUPS_PATH, default={"kind": EVALUATION_FINDING_FOLLOWUPS_KIND, "receipts": []}
    )
    receipts = payload.get("receipts")
    if payload.get("kind") != EVALUATION_FINDING_FOLLOWUPS_KIND or not isinstance(receipts, list):
        raise WorkspaceUsageError(f"{EVALUATION_FINDING_FOLLOWUPS_PATH.as_posix()} must contain evaluation finding follow-up receipts.")
    return payload


def record_material_finding_followup(
    *,
    target_root: Path,
    evaluation_id: str,
    result_identity: str,
    owner_ref: str,
    status: str = "continued",
) -> dict[str, Any]:
    normalized_owner = _require_non_empty(owner_ref, "owner_ref")
    normalized_result = _require_non_empty(result_identity, "result_identity")
    if status not in {"continued", "resolved"}:
        raise WorkspaceUsageError("finding follow-up status must be continued or resolved.")
    if not normalized_owner.startswith("#") and not (target_root / normalized_owner).exists():
        raise WorkspaceUsageError("finding follow-up owner_ref must reference an existing local owner or a GitHub issue ref.")
    payload = _finding_followups_payload(target_root)
    receipt_id = hashlib.sha256(
        json.dumps(
            {"evaluation_id": evaluation_id, "result_identity": normalized_result, "owner_ref": normalized_owner},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    receipt = {
        "kind": "agentic-workspace/evaluation-finding-followup-receipt/v1",
        "receipt_id": receipt_id,
        "operation_id": "evaluation.material-finding.route",
        "evaluation_id": evaluation_id,
        "result_identity": normalized_result,
        "owner_ref": normalized_owner,
        "status": status,
        "recorded_at": _now(),
        "idempotency_key": f"evaluation-finding-followup:{receipt_id}",
    }
    receipts = [item for item in payload["receipts"] if not (isinstance(item, dict) and item.get("receipt_id") == receipt_id)]
    receipts.append(receipt)
    _write_json(target_root / EVALUATION_FINDING_FOLLOWUPS_PATH, {"kind": EVALUATION_FINDING_FOLLOWUPS_KIND, "receipts": receipts})
    return receipt


def _observation_store_revision(observations: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(observations, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()[:16]


def _observation_idempotency_key(observation: dict[str, Any], authority: dict[str, Any]) -> str:
    source = {
        key: observation.get(key)
        for key in ("evaluation_id", "definition_revision", "criterion", "result", "evidence_refs", "finding", "recommended_action")
    }
    source["authority_baseline_id"] = (
        authority.get("authority_envelope", {}).get("mutation_baseline", {}).get("baseline_id")
        if isinstance(authority.get("authority_envelope"), dict)
        else None
    )
    source["proof_revision"] = authority.get("proof", {}).get("revision") if isinstance(authority.get("proof"), dict) else None
    return (
        "evaluation-observe:"
        + hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()[:24]
    )


def _jsonl_bytes(observations: list[dict[str, Any]]) -> int:
    return len("".join(json.dumps(item, sort_keys=True) + "\n" for item in observations).encode("utf-8"))


def _retention_plan(observations: list[dict[str, Any]]) -> dict[str, Any]:
    retained = list(observations)

    def removable_indexes() -> list[int]:
        admitted = [item for item in retained if isinstance(item.get("admission"), dict) and item["admission"].get("status") == "admitted"]
        superseded_ids = {
            str(result_id)
            for item in admitted
            for result_id in _string_list(item.get("supersedes") or item.get("admission", {}).get("supersedes"))
        }
        current_ids = {
            str(item.get("result_identity", {}).get("id") or "")
            for item in admitted
            if isinstance(item.get("result_identity"), dict) and str(item.get("result_identity", {}).get("id") or "") not in superseded_ids
        }
        removable: list[int] = []
        for index, item in enumerate(retained):
            result_id = str(item.get("result_identity", {}).get("id") or "") if isinstance(item.get("result_identity"), dict) else ""
            if result_id and result_id in current_ids:
                continue
            removable.append(index)
        return removable

    compacted: list[dict[str, Any]] = []
    while len(retained) > OBSERVATION_RETENTION_CAP:
        removable = removable_indexes()
        if not removable:
            break
        compacted.append(retained.pop(removable[0]))
    while _jsonl_bytes(retained) > OBSERVATION_BYTE_CAP:
        removable = removable_indexes()
        if not removable:
            break
        compacted.append(retained.pop(removable[0]))
    within_cap = len(retained) <= OBSERVATION_RETENTION_CAP and _jsonl_bytes(retained) <= OBSERVATION_BYTE_CAP
    return {
        "status": "within-cap" if within_cap and not compacted else "compacted" if within_cap else "rejected-over-cap",
        "retained": retained,
        "compacted": compacted,
        "retained_count": len(retained),
        "compacted_count": len(compacted),
        "byte_count": _jsonl_bytes(retained),
        "record_cap": OBSERVATION_RETENTION_CAP,
        "byte_cap": OBSERVATION_BYTE_CAP,
        "lineage_summary": [
            {
                "result_identity": item.get("result_identity", {}).get("id") if isinstance(item.get("result_identity"), dict) else None,
                "criterion": item.get("criterion"),
                "result": item.get("result"),
            }
            for item in compacted
        ],
    }


def append_observation(
    *,
    target_root: Path,
    evaluation_id: str,
    criterion: str,
    result: str,
    evidence_refs: list[str],
    confidence: str = "medium",
    burden: str = "medium",
    context: dict[str, Any] | None = None,
    finding: str = "",
    recommended_action: str = "",
) -> dict[str, Any]:
    definitions = _definitions_payload(target_root)
    definition = _definition_by_id(definitions, evaluation_id)
    if definition is None:
        raise WorkspaceUsageError(f"evaluation {evaluation_id!r} is not registered.")
    if definition.get("lifecycle") in TERMINAL_LIFECYCLES:
        raise WorkspaceUsageError(f"evaluation {evaluation_id!r} is terminal and cannot accept new observations.")
    criterion_ids = {str(item.get("id")) for item in definition.get("criteria", []) if isinstance(item, dict)}
    if criterion not in criterion_ids:
        raise WorkspaceUsageError(f"criterion {criterion!r} is not declared for evaluation {evaluation_id!r}.")
    if result not in VALID_OBSERVATION_RESULTS:
        raise WorkspaceUsageError(f"result must be one of: {', '.join(sorted(VALID_OBSERVATION_RESULTS))}.")
    if confidence not in VALID_CONFIDENCE:
        raise WorkspaceUsageError(f"confidence must be one of: {', '.join(sorted(VALID_CONFIDENCE))}.")
    if burden not in VALID_BURDEN:
        raise WorkspaceUsageError(f"burden must be one of: {', '.join(sorted(VALID_BURDEN))}.")
    recorded_at = _now()
    observation = {
        "kind": EVALUATION_OBSERVATION_KIND,
        "recorded_at": recorded_at,
        "evaluation_id": evaluation_id,
        "definition_revision": definition["revision"],
        "criterion": criterion,
        "result": result,
        "context": context or {},
        "evidence_refs": evidence_refs,
        "confidence": confidence,
        "burden": burden,
        "finding": finding,
        "recommended_action": recommended_action,
    }
    authority = _load_observation_authority(target_root, evaluation_id)
    observation["idempotency_key"] = _observation_idempotency_key(observation, authority)
    path = _observation_path(target_root, evaluation_id)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with _LocalFileLock(lock_path):
        previous_observations = _load_observations(target_root, evaluation_id)
        previous_revision = _observation_store_revision(previous_observations)
        duplicate = next((item for item in previous_observations if item.get("idempotency_key") == observation["idempotency_key"]), None)
        if isinstance(duplicate, dict):
            return {
                "kind": EVALUATION_OBSERVATION_KIND,
                "path": WORKSPACE_LOCAL_EVALUATIONS_DIR.joinpath(f"{evaluation_id}.jsonl").as_posix(),
                "outcome": "duplicate",
                "evaluation_id": evaluation_id,
                "criterion": criterion,
                "result": duplicate.get("result"),
                "result_identity": duplicate.get("result_identity"),
                "supersedes": duplicate.get("supersedes", []),
                "idempotency_key": observation["idempotency_key"],
                "store_revision": previous_revision,
            }
        previous_current_results = [
            item
            for item in previous_observations
            if isinstance(item.get("admission"), dict)
            and item["admission"].get("status") == "admitted"
            and int(item.get("definition_revision", 0) or 0) == int(definition["revision"])
            and item.get("criterion") == criterion
            and isinstance(item.get("result_identity"), dict)
        ]
        admission = _observation_admission(
            target_root=target_root,
            context=observation["context"],
            authority=authority,
            evaluation_id=evaluation_id,
            definition_revision=int(definition["revision"]),
            criterion=criterion,
            result=result,
            recorded_at=recorded_at,
            previous_current_results=previous_current_results,
        )
        if admission["status"] == "rejected":
            raise WorkspaceUsageError(f"evaluation observation rejected ({admission['reason']}): {admission['repair_route']}.")
        observation["admission"] = admission
        observation["result_identity"] = admission["result_identity"]
        observation["supersedes"] = admission["supersedes"]
        next_observations = [*previous_observations, observation]
        retention = _retention_plan(next_observations)
        if retention["status"] == "rejected-over-cap":
            raise WorkspaceUsageError(
                "evaluation observation rejected (retention-cap-exceeded): no safe historical compaction can keep "
                f"{OBSERVATION_RETENTION_CAP} records and {OBSERVATION_BYTE_CAP} bytes."
            )
        retained_observations = [item for item in retention["retained"] if isinstance(item, dict)]
        _atomic_write_text(path, "".join(json.dumps(item, sort_keys=True) + "\n" for item in retained_observations))
        if retention["compacted"]:
            _write_json(
                target_root / WORKSPACE_LOCAL_EVALUATIONS_DIR / f"{evaluation_id}.compaction.json",
                {
                    "kind": "agentic-workspace/evaluation-append-compaction-receipt/v1",
                    "operation_id": "evaluation.observe",
                    "evaluation_id": evaluation_id,
                    "status": retention["status"],
                    "store_revision_before": previous_revision,
                    "store_revision_after": _observation_store_revision(retained_observations),
                    "lineage_summary": retention["lineage_summary"],
                    "compacted_count": retention["compacted_count"],
                    "retained_count": retention["retained_count"],
                    "byte_count": retention["byte_count"],
                },
            )
        store_revision = _observation_store_revision(retained_observations)
    return {
        "kind": EVALUATION_OBSERVATION_KIND,
        "path": WORKSPACE_LOCAL_EVALUATIONS_DIR.joinpath(f"{evaluation_id}.jsonl").as_posix(),
        "outcome": "appended",
        "evaluation_id": evaluation_id,
        "criterion": criterion,
        "result": result,
        "result_identity": observation["result_identity"],
        "supersedes": observation["supersedes"],
        "idempotency_key": observation["idempotency_key"],
        "store_revision": store_revision,
        "storage": {
            "mode": "locked-atomic-rewrite",
            "lock": WORKSPACE_LOCAL_EVALUATIONS_DIR.joinpath(f"{evaluation_id}.jsonl.lock").as_posix(),
            "retention_cap": OBSERVATION_RETENTION_CAP,
            "byte_cap": OBSERVATION_BYTE_CAP,
            "retention_status": retention["status"],
            "retained_count": retention["retained_count"],
            "compacted_count": retention["compacted_count"],
            "byte_count": retention["byte_count"],
        },
    }


def append_observation_from_values(*, target_root: Path, values: dict[str, Any]) -> dict[str, Any]:
    return append_observation(
        target_root=target_root,
        evaluation_id=_require_non_empty(values.get("evaluation_id"), "evaluation_id"),
        criterion=_require_non_empty(values.get("criterion"), "criterion"),
        result=_require_non_empty(values.get("result"), "result"),
        evidence_refs=_split_csv(values.get("evidence_refs")),
        confidence=str(values.get("confidence") or "medium"),
        burden=str(values.get("burden") or "medium"),
        context=_parse_json_object(values.get("context"), "context", default={}),
        finding=str(values.get("finding") or ""),
        recommended_action=str(values.get("recommended_action") or ""),
    )


def _pending_collection_identity(
    *,
    action: dict[str, Any],
    result: str,
    evidence_refs: list[str],
    context: dict[str, Any],
    authority: dict[str, Any],
) -> str:
    source = {
        "operation_invocation": action.get("operation_invocation"),
        "result": result,
        "evidence_refs": evidence_refs,
        "context": context,
        "authority_revision": authority.get("proof", {}).get("revision") if isinstance(authority.get("proof"), dict) else None,
        "mutation_baseline": authority.get("authority_envelope", {}).get("mutation_baseline")
        if isinstance(authority.get("authority_envelope"), dict)
        else None,
    }
    digest = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
    return f"evaluation-pending-collection:{digest[:24]}"


def execute_evaluation_collection_action(
    *,
    target_root: Path,
    action: dict[str, Any],
    result: str,
    evidence_refs: list[str],
    confidence: str = "medium",
    burden: str = "medium",
    context: dict[str, Any] | None = None,
    finding: str = "",
    recommended_action: str = "",
) -> dict[str, Any]:
    """Execute a projected collection action through the normal observation admission gate."""
    raw_invocation = action.get("operation_invocation")
    invocation: dict[str, Any] = raw_invocation if isinstance(raw_invocation, dict) else {}
    if invocation.get("operation_id") != "evaluation.observe":
        raise WorkspaceUsageError("evaluation collection action must invoke evaluation.observe.")
    raw_arguments = invocation.get("arguments")
    arguments: dict[str, Any] = raw_arguments if isinstance(raw_arguments, dict) else {}
    evaluation_id = _require_non_empty(arguments.get("evaluation_id") or action.get("evaluation_id"), "evaluation_id")
    criterion = _require_non_empty(arguments.get("criterion") or action.get("criterion"), "criterion")
    requested_target = str(arguments.get("target") or "").strip()
    if requested_target and Path(requested_target).resolve() != target_root.resolve():
        raise WorkspaceUsageError("evaluation collection action target does not match target_root.")
    raw_projected_context = arguments.get("context")
    projected_context: dict[str, Any] = raw_projected_context if isinstance(raw_projected_context, dict) else {}
    submitted_context: dict[str, Any] = context if isinstance(context, dict) else {}
    observation_context = {**projected_context, **submitted_context}
    authority = _load_observation_authority(target_root, evaluation_id)
    pending_id = _pending_collection_identity(
        action=action,
        result=result,
        evidence_refs=evidence_refs,
        context=observation_context,
        authority=authority,
    )
    pending_path = target_root / EVALUATION_PENDING_COLLECTIONS_DIR / f"{evaluation_id}.json"
    pending_payload = _load_json(
        pending_path,
        default={"kind": "agentic-workspace/evaluation-pending-collections/v1", "evaluation_id": evaluation_id, "collections": []},
    )
    raw_collections = pending_payload.get("collections")
    collections = raw_collections if isinstance(raw_collections, list) else []
    pending_entry = {
        "id": pending_id,
        "status": "pending-admission",
        "operation_id": "evaluation.observe",
        "evaluation_id": evaluation_id,
        "criterion": criterion,
        "result": result,
        "evidence_refs": evidence_refs,
        "projected_action": action,
        "authority_snapshot": {
            "assignment_revision": authority.get("assignment", {}).get("assignment_revision")
            if isinstance(authority.get("assignment"), dict)
            else None,
            "proof_revision": authority.get("proof", {}).get("revision") if isinstance(authority.get("proof"), dict) else None,
            "baseline_id": authority.get("authority_envelope", {}).get("mutation_baseline", {}).get("baseline_id")
            if isinstance(authority.get("authority_envelope"), dict)
            and isinstance(authority.get("authority_envelope", {}).get("mutation_baseline"), dict)
            else None,
        },
        "recorded_at": _now(),
    }
    next_collections = [item for item in collections if not (isinstance(item, dict) and item.get("id") == pending_id)]
    try:
        admitted = append_observation(
            target_root=target_root,
            evaluation_id=evaluation_id,
            criterion=criterion,
            result=result,
            evidence_refs=evidence_refs,
            confidence=confidence,
            burden=burden,
            context=observation_context,
            finding=finding,
            recommended_action=recommended_action,
        )
    except WorkspaceUsageError as exc:
        failed_entry = {**pending_entry, "status": "admission-failed", "failure_reason": str(exc)}
        _write_json(
            pending_path,
            {
                "kind": "agentic-workspace/evaluation-pending-collections/v1",
                "evaluation_id": evaluation_id,
                "collections": [*next_collections, failed_entry],
            },
        )
        raise
    collection_status = "equivalent-observation-suppressed" if admitted.get("outcome") == "duplicate" else "admitted-observation"
    pending_entry = {
        **pending_entry,
        "status": collection_status,
        "observation_idempotency_key": admitted.get("idempotency_key"),
        "result_identity": admitted.get("result_identity"),
        "store_revision": admitted.get("store_revision"),
    }
    _write_json(
        pending_path,
        {
            "kind": "agentic-workspace/evaluation-pending-collections/v1",
            "evaluation_id": evaluation_id,
            "collections": [*next_collections, pending_entry],
        },
    )
    return {
        "kind": "agentic-workspace/evaluation-collection-admission/v1",
        "status": collection_status,
        "pending_collection_id": pending_id,
        "pending_collection_path": EVALUATION_PENDING_COLLECTIONS_DIR.joinpath(f"{evaluation_id}.json").as_posix(),
        "observation": admitted,
    }


def _criterion_status(definition: dict[str, Any], observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_criterion: dict[str, list[dict[str, Any]]] = {}
    for observation in observations:
        by_criterion.setdefault(str(observation.get("criterion")), []).append(observation)
    status: list[dict[str, Any]] = []
    for criterion in definition.get("criteria", []):
        if not isinstance(criterion, dict):
            continue
        criterion_id = str(criterion.get("id"))
        observed = by_criterion.get(criterion_id, [])
        has_support = any(item.get("result") == "supports" for item in observed)
        has_contradiction = any(item.get("result") == "contradicts" for item in observed)
        state = "contradicted" if has_contradiction else "satisfied" if has_support else "unobserved"
        status.append(
            {
                "criterion": criterion_id,
                "type": criterion.get("type"),
                "required": bool(criterion.get("required", True)),
                "observation_count": len(observed),
                "state": state,
                "latest_result": observed[-1].get("result") if observed else None,
            }
        )
    return status


def _current_result_freshness(
    *,
    target_root: Path | None,
    evaluation_id: str,
    observation: dict[str, Any],
    authority: dict[str, Any],
) -> dict[str, Any]:
    if target_root is None:
        return {"status": "not-checked", "stale": False, "reason": "target-root-not-supplied"}
    producer_resolution = authority.get("producer_resolution", {}) if isinstance(authority.get("producer_resolution"), dict) else {}
    if producer_resolution.get("status") != "resolved":
        return {"status": "stale", "stale": True, "reason": "authority-producer-unresolved"}
    assignment = authority.get("assignment", {}) if isinstance(authority.get("assignment"), dict) else {}
    proof = authority.get("proof", {}) if isinstance(authority.get("proof"), dict) else {}
    envelope = authority.get("authority_envelope", {}) if isinstance(authority.get("authority_envelope"), dict) else {}
    baseline = envelope.get("mutation_baseline", {}) if isinstance(envelope.get("mutation_baseline"), dict) else {}
    admission = observation.get("admission", {}) if isinstance(observation.get("admission"), dict) else {}
    identity = observation.get("result_identity", {}) if isinstance(observation.get("result_identity"), dict) else {}
    mismatches = [
        field
        for field, observed, current in [
            ("assignment.target_identity_ref", admission.get("target_identity_ref"), assignment.get("target_identity_ref")),
            ("assignment.assignment_revision", admission.get("assignment_revision"), assignment.get("assignment_revision")),
            ("proof.revision", identity.get("proof_revision"), proof.get("revision")),
            ("proof.provenance", identity.get("proof_provenance"), proof.get("provenance")),
            (
                "proof.receipt_id",
                identity.get("proof_receipt_id"),
                proof.get("receipt", {}).get("receipt_id") if isinstance(proof.get("receipt"), dict) else None,
            ),
            ("authority_envelope.mutation_baseline.baseline_id", admission.get("baseline_id"), baseline.get("baseline_id")),
            ("authority_envelope.mutation_baseline.head", admission.get("baseline_head"), baseline.get("head")),
        ]
        if observed not in (None, "", [], {}) and observed != current
    ]
    if mismatches:
        return {"status": "stale", "stale": True, "reason": "authority-context-changed", "mismatched_fields": mismatches}
    expected_scope = baseline.get("scope", {}) if isinstance(baseline.get("scope"), dict) else {}
    changed_paths = _string_list(envelope.get("changed_paths")) or _string_list(expected_scope.get("allowed_paths"))
    mutation_admission = admit_live_mutation_boundary(
        boundary_id="evaluation-current-result-consumption",
        target_root=target_root,
        expected=baseline,
        assignment_target_identity_ref=str(assignment.get("target_identity_ref") or "").strip() or None,
        assignment_revision=str(assignment.get("assignment_revision") or "").strip() or None,
        allowed_paths=changed_paths or None,
    )
    if mutation_admission.get("status") == "rejected":
        first_failure = next((item for item in mutation_admission.get("failures", []) if isinstance(item, dict)), {})
        return {
            "status": "stale",
            "stale": True,
            "reason": str(first_failure.get("reason") or "mutation-baseline-revalidation-failed"),
            "mutation_baseline_revalidation": mutation_admission,
        }
    return {
        "status": "fresh",
        "stale": False,
        "reason": "live-authority-revalidated",
        "mutation_baseline_revalidation": mutation_admission,
        "authority_source": WORKSPACE_LOCAL_EVALUATIONS_DIR.joinpath(f"{evaluation_id}.authority.json").as_posix(),
    }


def _material_finding_followup(target_root: Path, definition: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        followup_payload = _finding_followups_payload(target_root)
        followup_receipts = [item for item in followup_payload["receipts"] if isinstance(item, dict)]
    except WorkspaceUsageError:
        followup_receipts = []
    material = [
        item
        for item in observations
        if item.get("result") in {"contradicts", "mixed"}
        and (str(item.get("finding") or "").strip() or str(item.get("recommended_action") or "").strip())
    ]
    unresolved = []
    for item in material:
        result_identity = item.get("result_identity", {}).get("id") if isinstance(item.get("result_identity"), dict) else None
        followup = next(
            (
                receipt
                for receipt in followup_receipts
                if receipt.get("evaluation_id") == definition.get("id")
                and receipt.get("result_identity") == result_identity
                and receipt.get("status") in {"resolved", "continued"}
                and receipt.get("owner_ref")
            ),
            None,
        )
        if not followup:
            unresolved.append(
                {
                    "result_identity": result_identity,
                    "criterion": item.get("criterion"),
                    "result": item.get("result"),
                    "finding": item.get("finding"),
                    "recommended_action": item.get("recommended_action"),
                }
            )
    return {
        "status": "unresolved" if unresolved else "resolved" if material else "not-material",
        "material_finding_count": len(material),
        "unresolved_count": len(unresolved),
        "unresolved": unresolved,
        "routing_receipt_count": len(followup_receipts),
        "issue_shaping_authority": "repo-owned bounded issue/Planning owner workflow",
        "required_action": "create-or-reopen-bounded-follow-up" if unresolved else "none",
        "policy": definition.get("action_policy", {}),
    }


def current_evaluation_results(
    definition: dict[str, Any],
    observations: list[dict[str, Any]],
    *,
    target_root: Path | None = None,
) -> dict[str, Any]:
    admitted_observations = [
        item for item in observations if isinstance(item.get("admission"), dict) and item["admission"].get("status") == "admitted"
    ]
    legacy_unbound_observations = [
        item for item in observations if isinstance(item.get("admission"), dict) and item["admission"].get("status") == "legacy-unbound"
    ]
    superseded_ids = {
        str(result_id)
        for item in admitted_observations
        for result_id in _string_list(item.get("supersedes") or item.get("admission", {}).get("supersedes"))
    }
    bound_observations = [
        item
        for item in admitted_observations
        if isinstance(item.get("admission"), dict)
        and item["admission"].get("bound_context")
        and isinstance(item.get("result_identity"), dict)
    ]
    current_revision = int(definition["revision"])
    authority: dict[str, Any] = {}
    authority_error = ""
    if target_root is not None:
        try:
            authority = _load_observation_authority(target_root, str(definition["id"]))
        except WorkspaceUsageError as exc:
            authority_error = str(exc)
    current_bound_observations: list[dict[str, Any]] = []
    stale_observations: list[dict[str, Any]] = []
    freshness_records: list[dict[str, Any]] = []
    for item in bound_observations:
        if int(item.get("definition_revision", 0) or 0) != current_revision:
            continue
        if str(item.get("result_identity", {}).get("id") or "") in superseded_ids:
            continue
        freshness = (
            {"status": "stale", "stale": True, "reason": "authority-record-unavailable", "error": authority_error}
            if target_root is not None and not authority
            else _current_result_freshness(
                target_root=target_root,
                evaluation_id=str(definition["id"]),
                observation=item,
                authority=authority,
            )
        )
        freshness_records.append(
            {
                "result_identity": item.get("result_identity", {}).get("id") if isinstance(item.get("result_identity"), dict) else None,
                **freshness,
            }
        )
        if freshness.get("stale"):
            stale_item = dict(item)
            stale_item["stale_reason"] = freshness.get("reason")
            stale_item["freshness"] = freshness
            stale_observations.append(stale_item)
        else:
            current_bound_observations.append(item)
    historical_observations = [
        item
        for item in [*admitted_observations, *legacy_unbound_observations, *stale_observations]
        if item not in current_bound_observations
    ]
    return {
        "kind": "agentic-workspace/evaluation-current-result-resolution/v1",
        "status": "present" if current_bound_observations else "missing",
        "current_revision": current_revision,
        "current_observations": current_bound_observations,
        "historical_observations": historical_observations,
        "admitted_observations": admitted_observations,
        "legacy_unbound_observations": legacy_unbound_observations,
        "bound_observations": bound_observations,
        "stale_observations": stale_observations,
        "freshness_records": freshness_records,
        "superseded_ids": sorted(superseded_ids),
        "recovery": "append-observation-with-current-authority" if not current_bound_observations else "none",
        "consumer_rule": (
            "status, doctor, operating-decision, proof-selection, closure, and Planning consume this current-result resolver; "
            "superseded, stale, inconclusive, and rejected observations are historical evidence only."
        ),
    }


def evaluation_summary(*, target_root: Path, evaluation_id: str | None = None) -> dict[str, Any]:
    definitions = _definitions_payload(target_root)
    selected = [
        item for item in definitions["evaluations"] if isinstance(item, dict) and (evaluation_id is None or item.get("id") == evaluation_id)
    ]
    if evaluation_id and not selected:
        raise WorkspaceUsageError(f"evaluation {evaluation_id!r} is not registered.")
    summaries: list[dict[str, Any]] = []
    for definition in selected:
        observations = _load_observations(target_root, str(definition["id"]))
        current_results = current_evaluation_results(definition, observations, target_root=target_root)
        admitted_observations = current_results["admitted_observations"]
        legacy_unbound_observations = current_results["legacy_unbound_observations"]
        bound_observations = current_results["bound_observations"]
        stale_observations = current_results["stale_observations"]
        current_revision = current_results["current_revision"]
        current_bound_observations = current_results["current_observations"]
        historical_observations = current_results["historical_observations"]
        superseded_ids = set(current_results["superseded_ids"])
        legacy_unbound_count = len(legacy_unbound_observations)
        superseded_count = len(
            [item for item in bound_observations if str(item.get("result_identity", {}).get("id") or "") in superseded_ids]
        )
        stale_revision_count = len(bound_observations) - len(current_bound_observations)
        criteria = _criterion_status(definition, current_bound_observations)
        required = [item for item in criteria if item["required"]]
        satisfied = [item for item in required if item["state"] == "satisfied"]
        contradictions = [item for item in criteria if item["state"] == "contradicted"]
        min_observations = int(definition.get("collection_policy", {}).get("minimum_observations", 1))
        finding_followup = _material_finding_followup(target_root, definition, current_bound_observations)
        conclusion_ready = (
            len(current_bound_observations) >= min_observations
            and (len(satisfied) == len(required) or bool(contradictions) or definition.get("lifecycle") == "enough-signal")
            and finding_followup["status"] != "unresolved"
        )
        freshness_status = (
            "fresh-bound"
            if current_bound_observations
            else "stale-bound"
            if bound_observations
            else "legacy-unbound"
            if legacy_unbound_observations
            else "missing"
        )
        not_ready_reason = (
            "material-finding-followup-unresolved"
            if finding_followup["status"] == "unresolved"
            else "requires-bound-current-observation"
            if historical_observations
            else "needs-more-observations-or-owner-review"
        )
        current_result = current_bound_observations[-1] if current_bound_observations else {}
        current_admission = current_result.get("admission", {}) if isinstance(current_result.get("admission"), dict) else {}
        current_result_identity = {
            "status": "present" if current_result else "missing",
            "evaluation_id": definition["id"],
            "definition_revision": current_revision,
            "criterion": current_result.get("criterion"),
            "recorded_at": current_result.get("recorded_at"),
            "baseline_id": current_admission.get("baseline_id"),
            "target_identity_ref": current_admission.get("target_identity_ref"),
            "assignment_revision": current_admission.get("assignment_revision"),
            "superseded": str(current_result.get("result_identity", {}).get("id") or "") in superseded_ids if current_result else False,
        }
        current_identity = current_result.get("result_identity", {}) if isinstance(current_result.get("result_identity"), dict) else {}
        if current_identity:
            current_result_identity.update(
                {key: current_identity[key] for key in ("id", "result", "proof_revision") if key in current_identity}
            )
        summaries.append(
            {
                "evaluation_id": definition["id"],
                "revision": definition["revision"],
                "lifecycle": definition["lifecycle"],
                "coverage": {
                    "criterion_count": len(criteria),
                    "observed_criterion_count": len([item for item in criteria if item["observation_count"]]),
                    "observation_count": len(admitted_observations),
                    "decision_observation_count": len(current_bound_observations),
                    "historical_observation_count": len(historical_observations),
                    "legacy_unbound_count": legacy_unbound_count,
                    "stale_revision_count": stale_revision_count,
                    "stale_authority_count": len(stale_observations),
                    "superseded_result_count": superseded_count,
                    "minimum_observations": min_observations,
                },
                "criterion_status": criteria,
                "contradictions": contradictions,
                "latest_material_changes": current_bound_observations[-3:],
                "fresh_result_admission": {
                    "status": freshness_status,
                    "bound_observation_count": len(current_bound_observations),
                    "historical_observation_count": len(historical_observations),
                    "ignored_statuses": ["legacy-unbound", "stale-definition-revision", "rejected"],
                    "superseded_result_ids": sorted(superseded_ids),
                    "current_result_identity": current_result_identity,
                    "current_result_resolution": {
                        "status": current_results["status"],
                        "recovery": current_results["recovery"],
                        "freshness_records": current_results["freshness_records"],
                        "stale_count": len(stale_observations),
                        "consumer_rule": current_results["consumer_rule"],
                    },
                    "finding_followup": finding_followup,
                    "local_retention": {
                        "status": "within-cap"
                        if len(observations) <= OBSERVATION_RETENTION_CAP
                        and len(json.dumps(observations, sort_keys=True).encode("utf-8")) <= OBSERVATION_BYTE_CAP
                        else "prune-or-compact-required",
                        "max_current_results_per_criterion": 1,
                        "record_cap": OBSERVATION_RETENTION_CAP,
                        "byte_cap": OBSERVATION_BYTE_CAP,
                        "current_record_count": len(observations),
                        "current_byte_count": len(json.dumps(observations, sort_keys=True).encode("utf-8")),
                        "historical_record_count": len(historical_observations),
                        "cleanup_operation": "evaluation.prune",
                        "cleanup_proof": "dry-run reports removable superseded or legacy local JSONL records before apply",
                    },
                    "admission_contract": definition.get("admission_contract", _evaluation_admission_contract()),
                    "consumer_rule": (
                        "status, doctor, operating-decision, proof-selection, and closure consumers use only current "
                        "definition-revision observations admitted with bound assignment, authority, baseline, and proof context"
                    ),
                },
                "conclusion_readiness": {
                    "ready": conclusion_ready,
                    "reason_code": "ready" if conclusion_ready else not_ready_reason,
                },
                "owner": definition["decision_owner"],
                "sinks": definition["report_sinks"],
                "next_collection_action": "owner-review-or-conclude"
                if conclusion_ready
                else "shape-or-resolve-material-finding-owner"
                if finding_followup["status"] == "unresolved"
                else "migrate-or-append-bound-observation"
                if historical_observations
                else "append-observation",
            }
        )
    return {"kind": EVALUATION_SUMMARY_KIND, "path": WORKSPACE_EVALUATIONS_PATH.as_posix(), "summaries": summaries}


def evaluation_report_payload(*, target_root: Path, evaluation_id: str, explicit: bool = False) -> dict[str, Any]:
    """Compile a compact owner-facing report without delivering it to a sink."""
    authority = evaluation_report_authority(target_root=target_root, evaluation_id=evaluation_id, explicit=explicit)
    if authority["status"] == "not-due":
        return {
            "kind": "agentic-workspace/evaluation-report/v1",
            "status": "not-due",
            "evaluation_id": evaluation_id,
            "report_authority": authority,
            "delivery": "not-due",
        }
    return {
        "kind": "agentic-workspace/evaluation-report/v1",
        "status": "ready",
        "evaluation_id": evaluation_id,
        "subject": authority["subject"],
        "question": authority["question"],
        "coverage": authority["coverage"],
        "material_findings": authority["material_findings"],
        "contradictions": authority["contradictions"],
        "conclusion": authority["conclusion"],
        "decision_owner": authority["decision_owner"],
        "report_sinks": authority["report_sinks"],
        "recommended_action": authority["recommended_action"],
        "report_authority": authority,
        "delivery": "recommendation-only; external delivery requires an adapter receipt",
    }


def evaluation_report_authority(*, target_root: Path, evaluation_id: str, explicit: bool = False) -> dict[str, Any]:
    """Resolve the current owner, sink, result, evidence, and finding authority for one report."""
    definitions = _definitions_payload(target_root)
    definition = _definition_by_id(definitions, evaluation_id)
    if definition is None:
        raise WorkspaceUsageError(f"evaluation {evaluation_id!r} is not registered.")
    summary = evaluation_summary(target_root=target_root, evaluation_id=evaluation_id)["summaries"][0]
    admission = summary.get("fresh_result_admission") if isinstance(summary.get("fresh_result_admission"), dict) else {}
    raw_finding_followup = admission.get("finding_followup")
    finding_followup = raw_finding_followup if isinstance(raw_finding_followup, dict) else {}
    meaningful = bool(
        explicit
        or (summary.get("conclusion_readiness") if isinstance(summary.get("conclusion_readiness"), dict) else {}).get("ready")
        or summary.get("contradictions")
        or finding_followup.get("status") == "unresolved"
    )
    current_result = admission.get("current_result_identity") if isinstance(admission.get("current_result_identity"), dict) else {}
    authority_source = {
        "evaluation_id": evaluation_id,
        "definition_revision": definition.get("revision"),
        "lifecycle": definition.get("lifecycle"),
        "decision_owner": definition.get("decision_owner", {}),
        "report_sinks": definition.get("report_sinks", []),
        "current_result_identity": current_result,
        "coverage": summary.get("coverage", {}),
        "conclusion": summary.get("conclusion_readiness", {}),
        "material_findings": finding_followup.get("unresolved", []),
        "contradictions": summary.get("contradictions", []),
        "finding_followup_status": finding_followup.get("status"),
    }
    revision = hashlib.sha256(json.dumps(authority_source, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()[:24]
    return {
        "kind": "agentic-workspace/evaluation-report-authority/v1",
        "status": "ready" if meaningful else "not-due",
        "revision": revision,
        "source": "current-definition-plus-admitted-summary",
        "evaluation_id": evaluation_id,
        "definition_revision": definition.get("revision"),
        "subject": definition.get("subject", {}),
        "question": definition.get("question", ""),
        "coverage": summary.get("coverage", {}),
        "material_findings": finding_followup.get("unresolved", []),
        "contradictions": summary.get("contradictions", []),
        "conclusion": summary.get("conclusion_readiness", {}),
        "current_result_identity": current_result,
        "thresholds": definition.get("reporting", {}),
        "confidence_evidence": {
            "criterion_status": summary.get("criterion_status", []),
            "latest_material_changes": summary.get("latest_material_changes", []),
        },
        "material_finding_owner": finding_followup.get("owner", definition.get("decision_owner", {})),
        "decision_owner": definition.get("decision_owner", {}),
        "report_sinks": definition.get("report_sinks", []),
        "recommended_action": definition.get("action_policy", {}),
        "authority_source": authority_source,
        "rule": "Reports compile only from the current definition and admitted evaluation summary resolved at report time.",
    }


def record_local_evaluation_report_delivery(*, target_root: Path, evaluation_id: str, explicit: bool = False) -> dict[str, Any]:
    """Persist a local compilation receipt without claiming external sink delivery."""
    report = evaluation_report_payload(target_root=target_root, evaluation_id=evaluation_id, explicit=explicit)
    if report["status"] != "ready":
        return {"kind": "agentic-workspace/evaluation-report-delivery/v1", "status": "not-due", "report": report}
    identity = hashlib.sha256(
        json.dumps(
            {
                "evaluation_id": evaluation_id,
                "coverage": report["coverage"],
                "conclusion": report["conclusion"],
                "findings": report["material_findings"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:24]
    path = target_root / WORKSPACE_LOCAL_EVALUATIONS_DIR / f"{evaluation_id}.report-deliveries.json"
    previous = _load_json(path, default={"deliveries": []})
    deliveries = previous.get("deliveries", []) if isinstance(previous.get("deliveries"), list) else []
    existing = next((item for item in deliveries if isinstance(item, dict) and item.get("identity") == identity), None)
    if existing:
        return {
            "kind": "agentic-workspace/evaluation-report-delivery/v1",
            "status": "already-delivered",
            "receipt": existing,
            "report": report,
        }
    receipt = {
        "identity": identity,
        "status": "recorded-local",
        "evaluation_id": evaluation_id,
        "declared_sinks": report["report_sinks"],
        "delivery_scope": "local-compilation-receipt-only",
        "external_delivery": "unattempted; require one adapter receipt per external sink",
    }
    _write_json(path, {"deliveries": [*deliveries, receipt]})
    return {"kind": "agentic-workspace/evaluation-report-delivery/v1", "status": "recorded-local", "receipt": receipt, "report": report}


def external_evaluation_report_delivery_request(*, target_root: Path, evaluation_id: str, explicit: bool = False) -> dict[str, Any]:
    """Prepare, but never perform, an external report delivery."""
    report = evaluation_report_payload(target_root=target_root, evaluation_id=evaluation_id, explicit=explicit)
    sinks = [
        sink
        for sink in report.get("report_sinks", [])
        if isinstance(sink, dict) and sink.get("class") in {"issue-or-report", "closed-issue"}
    ]
    if report["status"] != "ready" or not sinks:
        return {"kind": "agentic-workspace/evaluation-external-delivery-request/v1", "status": "not-due", "report": report}
    raw_report_authority = report.get("report_authority")
    report_authority: dict[str, Any] = raw_report_authority if isinstance(raw_report_authority, dict) else {}
    identity_source = {
        "evaluation_id": evaluation_id,
        "sinks": sinks,
        "authority_revision": report_authority.get("revision"),
        "current_result_identity": report_authority.get("current_result_identity"),
    }
    identity = hashlib.sha256(json.dumps(identity_source, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()[:24]
    return {
        "kind": "agentic-workspace/evaluation-external-delivery-request/v1",
        "status": "adapter-required",
        "delivery_id": identity,
        "request_revision": identity,
        "authority_revision": report_authority.get("revision"),
        "sinks": sinks,
        "sink_requests": [
            {
                "sink_id": str(sink.get("id") or ""),
                "sink_class": str(sink.get("class") or ""),
                "idempotency_key": hashlib.sha256(
                    json.dumps({"delivery_id": identity, "sink": sink}, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()[:24],
            }
            for sink in sinks
        ],
        "report": report,
        "authority_boundary": (
            "This request recommends delivery to the declared external sink; a provider adapter must record one "
            "producer receipt per sink and never changes the evaluation conclusion."
        ),
    }


def record_external_evaluation_report_delivery(
    *,
    target_root: Path,
    request: dict[str, Any],
    succeeded: bool | None = None,
    detail: str = "",
    adapter_receipt: dict[str, Any] | None = None,
    adapter_receipt_ref: str | Path | None = None,
) -> dict[str, Any]:
    """Persist adapter outcome; a failed attempt remains retryable."""
    if request.get("status") != "adapter-required":
        return {"kind": "agentic-workspace/evaluation-external-delivery-receipt/v1", "status": "not-due"}
    evaluation_id = str(request.get("report", {}).get("evaluation_id") or "")
    identity = str(request.get("delivery_id") or "")
    current_request = external_evaluation_report_delivery_request(target_root=target_root, evaluation_id=evaluation_id, explicit=True)
    if current_request.get("delivery_id") != identity or current_request.get("request_revision") != request.get("request_revision"):
        return {
            "kind": "agentic-workspace/evaluation-external-delivery-receipt/v1",
            "status": "stale-request",
            "delivery_id": identity,
            "current_delivery_id": current_request.get("delivery_id"),
            "retry": True,
        }
    receipt_ref = str(adapter_receipt_ref or "").strip()
    receipt = _load_external_delivery_adapter_receipt(target_root=target_root, receipt_ref=receipt_ref) if receipt_ref else {}
    if not receipt:
        return {
            "kind": "agentic-workspace/evaluation-external-delivery-receipt/v1",
            "status": "adapter-receipt-required",
            "delivery_id": identity,
            "retry": True,
            "rule": (
                "External evaluation delivery must be recorded from a provider-owned local adapter receipt file, "
                "not caller success flags or inline dictionaries."
            ),
        }
    if adapter_receipt is not None:
        return {
            "kind": "agentic-workspace/evaluation-external-delivery-receipt/v1",
            "status": "adapter-receipt-required",
            "delivery_id": identity,
            "retry": True,
            "rule": "Inline adapter_receipt is ignored; pass adapter_receipt_ref for a current producer-owned local receipt.",
        }
    if receipt.get("kind") != "agentic-workspace/evaluation-external-delivery-adapter-receipt/v1":
        raise WorkspaceUsageError("adapter_receipt.kind is invalid for evaluation external delivery.")
    if str(receipt.get("producer") or "").strip() == "":
        raise WorkspaceUsageError("adapter_receipt.producer is required.")
    if str(receipt.get("status_owner") or "").strip() not in {"provider-adapter", "external-operation-adapter"}:
        raise WorkspaceUsageError("adapter_receipt.status_owner must identify the provider adapter.")
    if str(receipt.get("receipt_revision") or "").strip() == "":
        raise WorkspaceUsageError("adapter_receipt.receipt_revision is required.")
    if str(receipt.get("capability_revision") or "").strip() == "":
        raise WorkspaceUsageError("adapter_receipt.capability_revision is required.")
    if str(receipt.get("capability_status") or "current").strip() not in {"current", "fresh", "accepted"}:
        raise WorkspaceUsageError("adapter_receipt capability is not current.")
    if receipt.get("superseded_by") or receipt.get("revoked_at"):
        raise WorkspaceUsageError("adapter_receipt is superseded or revoked.")
    if receipt.get("delivery_id") != identity:
        raise WorkspaceUsageError("adapter_receipt.delivery_id does not match the current request.")
    attempt_revision = str(receipt.get("attempt_revision") or "").strip()
    sink_id = str(receipt.get("sink_id") or "").strip()
    if not attempt_revision or not sink_id:
        raise WorkspaceUsageError("adapter_receipt.attempt_revision and adapter_receipt.sink_id are required.")
    status = str(receipt.get("status") or ("delivered" if succeeded else "failed"))
    if status not in {"delivered", "failed"}:
        raise WorkspaceUsageError("adapter_receipt.status must be delivered or failed.")
    sink_requests = request.get("sink_requests", []) if isinstance(request.get("sink_requests"), list) else []
    sink_request = next((item for item in sink_requests if isinstance(item, dict) and item.get("sink_id") == sink_id), None)
    if not sink_request:
        raise WorkspaceUsageError("adapter_receipt.sink_id is not part of the current delivery request.")
    path = target_root / WORKSPACE_LOCAL_EVALUATIONS_DIR / f"{evaluation_id}.external-deliveries.json"
    payload = _load_json(path, default={"deliveries": []})
    deliveries = payload.get("deliveries", []) if isinstance(payload.get("deliveries"), list) else []
    existing = next(
        (
            item
            for item in deliveries
            if isinstance(item, dict)
            and item.get("identity") == identity
            and item.get("sink_id") == sink_id
            and item.get("status") == "delivered"
        ),
        None,
    )
    if existing:
        return {
            "kind": "agentic-workspace/evaluation-external-delivery-receipt/v1",
            "status": "already-delivered",
            "delivery_id": identity,
            "sink_id": sink_id,
        }
    stored = {
        "identity": identity,
        "request_revision": request.get("request_revision"),
        "authority_revision": request.get("authority_revision"),
        "status": status,
        "detail": detail or receipt.get("detail", ""),
        "sink_id": sink_id,
        "idempotency_key": sink_request.get("idempotency_key"),
        "attempt_revision": attempt_revision,
        "producer": receipt.get("producer"),
        "adapter_receipt_ref": receipt.get("_source_ref"),
        "adapter_receipt_digest": receipt.get("_source_digest"),
        "adapter_receipt_revision": receipt.get("receipt_revision"),
        "capability_revision": receipt.get("capability_revision"),
        "adapter_receipt": receipt,
    }
    _write_json(path, {"deliveries": [*deliveries, stored]})
    return {
        "kind": "agentic-workspace/evaluation-external-delivery-receipt/v1",
        "status": stored["status"],
        "delivery_id": identity,
        "sink_id": sink_id,
        "attempt_revision": attempt_revision,
        "retry": status != "delivered",
    }


def evaluation_report_delivery_status(*, target_root: Path, evaluation_id: str, explicit: bool = True) -> dict[str, Any]:
    """Project delivery status from local compilation and producer-owned adapter receipts."""
    request = external_evaluation_report_delivery_request(target_root=target_root, evaluation_id=evaluation_id, explicit=explicit)
    if request.get("status") != "adapter-required":
        return {
            "kind": "agentic-workspace/evaluation-delivery-status/v1",
            "status": "not-due",
            "evaluation_id": evaluation_id,
            "request": request,
        }
    delivery_id = str(request.get("delivery_id") or "")
    local_payload = _load_json(
        target_root / WORKSPACE_LOCAL_EVALUATIONS_DIR / f"{evaluation_id}.report-deliveries.json",
        default={"deliveries": []},
    )
    external_payload = _load_json(
        target_root / WORKSPACE_LOCAL_EVALUATIONS_DIR / f"{evaluation_id}.external-deliveries.json",
        default={"deliveries": []},
    )
    local_receipts = [item for item in local_payload.get("deliveries", []) if isinstance(item, dict)]
    external_receipts = [
        item for item in external_payload.get("deliveries", []) if isinstance(item, dict) and str(item.get("identity") or "") == delivery_id
    ]
    sink_requests = request.get("sink_requests", []) if isinstance(request.get("sink_requests"), list) else []
    sink_statuses: list[dict[str, Any]] = []
    for sink_request in sink_requests:
        if not isinstance(sink_request, dict):
            continue
        sink_id = str(sink_request.get("sink_id") or "")
        attempts = [item for item in external_receipts if str(item.get("sink_id") or "") == sink_id]
        latest = attempts[-1] if attempts else {}
        sink_statuses.append(
            {
                "sink_id": sink_id,
                "status": str(latest.get("status") or "pending"),
                "attempt_count": len(attempts),
                "latest_attempt_revision": latest.get("attempt_revision"),
                "latest_adapter_receipt_ref": latest.get("adapter_receipt_ref"),
                "retry": str(latest.get("status") or "") != "delivered",
                "idempotency_key": sink_request.get("idempotency_key"),
            }
        )
    delivered_count = len([item for item in sink_statuses if item.get("status") == "delivered"])
    failed_count = len([item for item in sink_statuses if item.get("status") == "failed"])
    pending_count = len([item for item in sink_statuses if item.get("status") == "pending"])
    overall = "delivered" if sink_statuses and delivered_count == len(sink_statuses) else "retryable" if failed_count else "pending"
    return {
        "kind": "agentic-workspace/evaluation-delivery-status/v1",
        "status": overall,
        "evaluation_id": evaluation_id,
        "delivery_id": delivery_id,
        "authority_revision": request.get("authority_revision"),
        "local_compilation_receipt_count": len(local_receipts),
        "sink_statuses": sink_statuses,
        "delivered_count": delivered_count,
        "failed_count": failed_count,
        "pending_count": pending_count,
        "retry": overall != "delivered",
        "request": request,
        "authority_boundary": "Delivery status is projected from stored local compilation receipts and admitted provider-owned adapter receipts only.",
    }


def evaluation_report_delivery_retry_request(*, target_root: Path, evaluation_id: str, sink_id: str = "") -> dict[str, Any]:
    """Return the current retryable delivery request without minting delivery success."""
    status = evaluation_report_delivery_status(target_root=target_root, evaluation_id=evaluation_id, explicit=True)
    if status.get("status") == "not-due":
        return {"kind": "agentic-workspace/evaluation-delivery-retry/v1", "status": "not-due", "delivery_status": status}
    retryable = [
        item
        for item in status.get("sink_statuses", [])
        if isinstance(item, dict) and item.get("retry") is True and (not sink_id or str(item.get("sink_id") or "") == str(sink_id))
    ]
    return {
        "kind": "agentic-workspace/evaluation-delivery-retry/v1",
        "status": "retryable" if retryable else "nothing-to-retry",
        "evaluation_id": evaluation_id,
        "delivery_id": status.get("delivery_id"),
        "sink_requests": retryable,
        "request": status.get("request"),
        "rule": "Retry reuses the current delivery request and waits for a fresh producer adapter receipt.",
    }


def evaluation_collection_actions(
    *,
    target_root: Path,
    surface: str,
    issue_refs: list[str] | None = None,
    operation_id: str | None = None,
    phase: str | None = None,
) -> dict[str, Any]:
    """Project only collecting evaluations selected by structured work facts."""
    context = {
        "issue_refs": {str(item) for item in issue_refs or [] if str(item).strip()},
        "operation_ids": {str(operation_id)} if operation_id else set(),
        "phases": {str(phase)} if phase else set(),
        "surfaces": {str(surface)},
        "commands": {str(surface)},
        "profiles": {"default"},
    }
    actions: list[dict[str, Any]] = []
    for definition in _definitions_payload(target_root)["evaluations"]:
        if not isinstance(definition, dict) or str(definition.get("lifecycle") or "") != "collecting":
            continue
        selectors = definition.get("selectors")
        if not isinstance(selectors, dict):
            continue
        matched_by: list[str] = []
        for selector, observed in context.items():
            expected = {str(item) for item in selectors.get(selector, []) if str(item).strip()}
            if not expected:
                continue
            if not expected.intersection(observed):
                matched_by = []
                break
            matched_by.append(selector)
        else:
            if not matched_by:
                continue
            criteria = definition.get("criteria") if isinstance(definition.get("criteria"), list) else []
            criterion = next((item for item in criteria if isinstance(item, dict) and item.get("required", True)), {})
            evaluation_id = str(definition.get("id") or "")
            criterion_id = str(criterion.get("id") or "")
            observation_context = {
                "issue_refs": sorted(context["issue_refs"]),
                "operation_ids": sorted(context["operation_ids"]),
                "phases": sorted(context["phases"]),
                "surface": surface,
                "definition_revision": definition.get("revision"),
            }
            actions.append(
                {
                    "evaluation_id": evaluation_id,
                    "criterion": criterion_id,
                    "match_reason": matched_by,
                    "decision_owner": definition.get("decision_owner", {}),
                    "report_sinks": definition.get("report_sinks", []),
                    "next_action": "record-evaluation-observation-after-bound-proof",
                    "executable_operation": "execute_evaluation_collection_action",
                    "operation_invocation": {
                        "kind": "agentic-workspace/operation-invocation/v1",
                        "operation_id": "evaluation.observe",
                        "arguments": {
                            "target": target_root.as_posix(),
                            "evaluation_id": evaluation_id,
                            "criterion": criterion_id,
                            "context": observation_context,
                        },
                        "effect_class": "local-record-append",
                        "authority_class": "evaluation-admission",
                        "required_before_apply": ["current assignment", "current mutation baseline", "current proof receipt"],
                        "idempotency_identity": _observation_idempotency_key(
                            {
                                "evaluation_id": evaluation_id,
                                "definition_revision": definition.get("revision"),
                                "criterion": criterion_id,
                                "result": "pending-collection",
                                "evidence_refs": [],
                            },
                            {},
                        ),
                    },
                    "rule": "Use the evaluation observation operation after assignment, authority, baseline, and proof admission; do not append an unbound reminder observation.",
                }
            )
    return {
        "kind": "agentic-workspace/evaluation-collection-actions/v1",
        "status": "matched" if actions else "not-applicable",
        "surface": surface,
        "actions": actions,
        "rule": "Only explicitly selected collecting evaluations appear; non-matching work stays quiet.",
    }


def prune_observations(*, target_root: Path, evaluation_id: str, dry_run: bool = False) -> dict[str, Any]:
    definitions = _definitions_payload(target_root)
    definition = _definition_by_id(definitions, evaluation_id)
    if definition is None:
        raise WorkspaceUsageError(f"evaluation {evaluation_id!r} is not registered.")
    path = _observation_path(target_root, evaluation_id)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with _LocalFileLock(lock_path):
        observations = _load_observations(target_root, evaluation_id)
        current_results = current_evaluation_results(definition, observations, target_root=target_root)
        keep_ids = {str(item.get("idempotency_key") or "") for item in current_results["current_observations"]}
        retained = [item for item in observations if str(item.get("idempotency_key") or "") in keep_ids]
        if len(retained) > OBSERVATION_RETENTION_CAP:
            retained = retained[-OBSERVATION_RETENTION_CAP:]
        compacted = [item for item in observations if item not in retained]
        receipt = {
            "kind": "agentic-workspace/evaluation-prune-receipt/v1",
            "operation_id": "evaluation.prune",
            "evaluation_id": evaluation_id,
            "dry_run": dry_run,
            "status": "would-compact" if dry_run and compacted else "compacted" if compacted else "within-cap",
            "original_count": len(observations),
            "retained_count": len(retained),
            "compacted_count": len(compacted),
            "store_revision_before": _observation_store_revision(observations),
            "store_revision_after": _observation_store_revision(retained),
            "lineage_summary": [
                {
                    "result_identity": item.get("result_identity", {}).get("id") if isinstance(item.get("result_identity"), dict) else None,
                    "criterion": item.get("criterion"),
                    "result": item.get("result"),
                }
                for item in compacted
            ],
            "archive_cleanup": {
                "raw_local_residue_removed": bool(compacted and not dry_run),
                "path": WORKSPACE_LOCAL_EVALUATIONS_DIR.joinpath(f"{evaluation_id}.jsonl").as_posix(),
            },
        }
        if compacted and not dry_run:
            _atomic_write_text(path, "".join(json.dumps(item, sort_keys=True) + "\n" for item in retained))
            _write_json(target_root / WORKSPACE_LOCAL_EVALUATIONS_DIR / f"{evaluation_id}.compaction.json", receipt)
        return receipt


def transition_evaluation(
    *, target_root: Path, evaluation_id: str, lifecycle: str, reason: str = "", expected_revision: int | None = None
) -> dict[str, Any]:
    definitions = _definitions_payload(target_root)
    definition = _definition_by_id(definitions, evaluation_id)
    if definition is None:
        raise WorkspaceUsageError(f"evaluation {evaluation_id!r} is not registered.")
    if expected_revision is not None and int(definition.get("revision", 0) or 0) != expected_revision:
        raise WorkspaceUsageError(
            f"stale evaluation revision for {evaluation_id!r}: expected {expected_revision}, current {definition.get('revision')}."
        )
    current = str(definition.get("lifecycle"))
    if lifecycle not in VALID_TRANSITIONS.get(current, set()):
        raise WorkspaceUsageError(f"invalid evaluation lifecycle transition: {current} -> {lifecycle}.")
    definition["lifecycle"] = lifecycle
    definition["updated_at"] = _now()
    definition["last_transition"] = {"from": current, "to": lifecycle, "reason": reason, "recorded_at": definition["updated_at"]}
    _write_json(target_root / WORKSPACE_EVALUATIONS_PATH, definitions)
    return {
        "kind": EVALUATIONS_KIND,
        "path": WORKSPACE_EVALUATIONS_PATH.as_posix(),
        "outcome": "transitioned",
        "evaluation_id": evaluation_id,
        "from": current,
        "to": lifecycle,
        "revision": definition["revision"],
        "revision_guard": "matched" if expected_revision is not None else "not-provided",
    }


def _emit_evaluation_result(payload: dict[str, Any], output_format: str) -> int:
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(f"Kind: {payload.get('kind', '')}")
    if "outcome" in payload:
        print(f"Outcome: {payload['outcome']}")
    if "evaluation_id" in payload:
        print(f"Evaluation: {payload['evaluation_id']}")
    if "path" in payload:
        print(f"Path: {payload['path']}")
    if payload.get("summaries"):
        for item in payload["summaries"]:
            print(
                f"- {item['evaluation_id']}: {item['lifecycle']}; "
                f"observations={item['coverage']['observation_count']}; "
                f"next={item['next_collection_action']}"
            )
    return 0


def _evaluation_adapter_payload(args: Any, *, target_root: Path) -> dict[str, Any]:
    values = vars(args)
    command = str(getattr(args, "evaluation_command", ""))
    if command == "register":
        return register_evaluation_from_values(target_root=target_root, values=values)
    if command == "observe":
        return append_observation_from_values(target_root=target_root, values=values)
    if command == "status":
        return evaluation_summary(target_root=target_root, evaluation_id=getattr(args, "evaluation_id", None))
    if command == "report-preview":
        return evaluation_report_payload(
            target_root=target_root,
            evaluation_id=_require_non_empty(getattr(args, "evaluation_id", ""), "evaluation_id"),
            explicit=bool(getattr(args, "explicit", False)),
        )
    if command == "local-delivery":
        return record_local_evaluation_report_delivery(
            target_root=target_root,
            evaluation_id=_require_non_empty(getattr(args, "evaluation_id", ""), "evaluation_id"),
            explicit=bool(getattr(args, "explicit", False)),
        )
    if command == "external-request":
        return external_evaluation_report_delivery_request(
            target_root=target_root,
            evaluation_id=_require_non_empty(getattr(args, "evaluation_id", ""), "evaluation_id"),
            explicit=bool(getattr(args, "explicit", False)),
        )
    if command == "external-adapter-receipt":
        return record_external_evaluation_adapter_receipt(
            target_root=target_root,
            delivery_id=_require_non_empty(getattr(args, "delivery_id", ""), "delivery_id"),
            sink_id=_require_non_empty(getattr(args, "sink_id", ""), "sink_id"),
            producer=_require_non_empty(getattr(args, "producer", ""), "producer"),
            attempt_revision=_require_non_empty(getattr(args, "attempt_revision", ""), "attempt_revision"),
            receipt_revision=_require_non_empty(getattr(args, "receipt_revision", ""), "receipt_revision"),
            capability_revision=_require_non_empty(getattr(args, "capability_revision", ""), "capability_revision"),
            capability_status=str(getattr(args, "capability_status", "current") or "current"),
            status=_require_non_empty(getattr(args, "status", ""), "status"),
            status_owner=str(getattr(args, "status_owner", "provider-adapter") or "provider-adapter"),
            detail=str(getattr(args, "detail", "") or ""),
            supersedes=str(getattr(args, "supersedes", "") or ""),
        )
    if command == "external-delivery":
        request = external_evaluation_report_delivery_request(
            target_root=target_root,
            evaluation_id=_require_non_empty(getattr(args, "evaluation_id", ""), "evaluation_id"),
            explicit=bool(getattr(args, "explicit", False)),
        )
        return record_external_evaluation_report_delivery(
            target_root=target_root,
            request=request,
            adapter_receipt_ref=_require_non_empty(getattr(args, "adapter_receipt_ref", ""), "adapter_receipt_ref"),
        )
    if command == "delivery-status":
        return evaluation_report_delivery_status(
            target_root=target_root,
            evaluation_id=_require_non_empty(getattr(args, "evaluation_id", ""), "evaluation_id"),
            explicit=bool(getattr(args, "explicit", False)),
        )
    if command == "retry":
        return evaluation_report_delivery_retry_request(
            target_root=target_root,
            evaluation_id=_require_non_empty(getattr(args, "evaluation_id", ""), "evaluation_id"),
            sink_id=str(getattr(args, "sink_id", "") or ""),
        )
    if command == "transition":
        return transition_evaluation(
            target_root=target_root,
            evaluation_id=_require_non_empty(getattr(args, "evaluation_id", ""), "evaluation_id"),
            lifecycle=_require_non_empty(getattr(args, "lifecycle", ""), "lifecycle"),
            reason=str(getattr(args, "reason", "") or ""),
            expected_revision=int(getattr(args, "expected_revision", 0) or 0) or None,
        )
    if command in {"prune", "compact"}:
        return prune_observations(
            target_root=target_root,
            evaluation_id=_require_non_empty(getattr(args, "evaluation_id", ""), "evaluation_id"),
            dry_run=bool(getattr(args, "dry_run", False)),
        )
    raise WorkspaceUsageError(f"unsupported evaluation command: {command}")


def _run_evaluation_adapter(args: Any) -> int:
    output_format = str(getattr(args, "format", "text") or "text")
    try:
        payload = _evaluation_adapter_payload(args, target_root=Path(str(getattr(args, "target", ".") or ".")).resolve())
    except WorkspaceUsageError as exc:
        if output_format == "json":
            print(json.dumps({"kind": "agentic-workspace/evaluation-error/v1", "status": "failed", "reason": str(exc)}, indent=2))
            return 2
        raise
    return _emit_evaluation_result(payload, output_format)


def closure_authority(*, implementation_complete: bool, proof_complete: bool, evaluation: dict[str, Any] | None) -> dict[str, Any]:
    summary_entries = []
    if isinstance(evaluation, dict) and isinstance(evaluation.get("summaries"), list):
        summary_entries = [item for item in evaluation["summaries"] if isinstance(item, dict)]
    elif isinstance(evaluation, dict) and isinstance(evaluation.get("fresh_result_admission"), dict):
        summary_entries = [evaluation]
    valid_definition = bool(
        isinstance(evaluation, dict)
        and evaluation.get("evaluation_id")
        and evaluation.get("decision_owner")
        and evaluation.get("criteria")
        and evaluation.get("evidence_sources")
        and evaluation.get("report_sinks")
        and evaluation.get("collection_policy")
        and evaluation.get("conclusion_policy")
    )
    valid_summary = bool(
        summary_entries
        and all(
            _summary_entry.get("conclusion_readiness", {}).get("ready") is True
            and _summary_entry.get("fresh_result_admission", {}).get("status") == "fresh-bound"
            and _summary_entry.get("fresh_result_admission", {}).get("current_result_identity", {}).get("status") == "present"
            for _summary_entry in summary_entries
        )
    )
    valid_evaluation = valid_summary or valid_definition
    authorized = implementation_complete and proof_complete and (evaluation is None or valid_evaluation)
    blocked_reasons: list[str] = []
    if not implementation_complete:
        blocked_reasons.append("implementation-incomplete")
    if not proof_complete:
        blocked_reasons.append("present-tense-proof-incomplete")
    if evaluation is not None and not valid_evaluation:
        blocked_reasons.append("longitudinal-evaluation-invalid")
    return {
        "kind": EVALUATION_CLOSURE_AUTHORITY_KIND,
        "implementation_proof": "complete" if implementation_complete and proof_complete else "blocked",
        "longitudinal_evaluation": "valid" if valid_evaluation else "not-required" if evaluation is None else "invalid",
        "evaluation_admission": "fresh-bound-ready"
        if valid_summary
        else "definition-only"
        if valid_definition
        else "not-required"
        if evaluation is None
        else "invalid",
        "issue_closure_authorized": authorized,
        "blocked_reasons": blocked_reasons,
        "rule": "Evaluation may carry future uncertainty only after present-tense implementation and proof are complete.",
    }
