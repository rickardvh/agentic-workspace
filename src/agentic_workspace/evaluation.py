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


def _producer_receipt(payload: dict[str, Any], *, field: str, expected_kind: str, expected_producer: str) -> dict[str, Any]:
    raw_receipt = payload.get("receipt")
    receipt: dict[str, Any] = raw_receipt if isinstance(raw_receipt, dict) else {}
    missing = [
        key
        for key, value in {
            f"{field}.receipt.kind": receipt.get("kind"),
            f"{field}.receipt.receipt_id": receipt.get("receipt_id"),
            f"{field}.receipt.producer": receipt.get("producer"),
            f"{field}.receipt.revision": receipt.get("revision"),
        }.items()
        if value in (None, "", [], {})
    ]
    mismatches: list[str] = []
    if receipt.get("kind") not in (None, expected_kind):
        mismatches.append(f"{field}.receipt.kind")
    if receipt.get("producer") not in (None, expected_producer):
        mismatches.append(f"{field}.receipt.producer")
    return {
        "status": "resolved" if not missing and not mismatches else "rejected",
        "receipt_id": receipt.get("receipt_id"),
        "revision": receipt.get("revision"),
        "producer": receipt.get("producer"),
        "missing_fields": missing,
        "mismatched_fields": mismatches,
    }


def _authority_producer_resolution(*, assignment: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    assignment_receipt = _producer_receipt(
        assignment,
        field="assignment",
        expected_kind="agentic-workspace/assignment-authority-receipt/v1",
        expected_producer="assignment.lifecycle",
    )
    proof_receipt = _producer_receipt(
        proof,
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
    producer_resolution = _authority_producer_resolution(assignment=assignment, proof=proof)
    if producer_resolution["status"] != "resolved":
        missing = ", ".join([*producer_resolution["missing_fields"], *producer_resolution["mismatched_fields"]])
        raise WorkspaceUsageError(
            "evaluation observation authority rejected (authority-producer-unresolved): "
            f"assignment/proof producer receipts are required ({missing})."
        )
    baseline = mutation_baseline_payload(
        target_root=target_root,
        changed_paths=changed_paths,
        assignment_target_identity_ref=str(assignment.get("target_identity_ref") or "").strip() or None,
        assignment_revision=str(assignment.get("assignment_revision") or "").strip() or None,
    )
    payload = {
        "kind": "agentic-workspace/evaluation-observation-authority/v1",
        "evaluation_id": evaluation_id,
        "assignment": assignment,
        "proof": proof,
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


def _material_finding_followup(definition: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    material = [
        item
        for item in observations
        if item.get("result") in {"contradicts", "mixed"}
        and (str(item.get("finding") or "").strip() or str(item.get("recommended_action") or "").strip())
    ]
    unresolved = []
    for item in material:
        context = item.get("context", {}) if isinstance(item.get("context"), dict) else {}
        followup = context.get("finding_followup", {}) if isinstance(context.get("finding_followup"), dict) else {}
        if followup.get("status") not in {"resolved", "continued"} or not followup.get("owner_ref"):
            unresolved.append(
                {
                    "result_identity": item.get("result_identity", {}).get("id") if isinstance(item.get("result_identity"), dict) else None,
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
        finding_followup = _material_finding_followup(definition, current_bound_observations)
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
