from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentic_workspace.config import WorkspaceUsageError

EVALUATIONS_KIND = "agentic-workspace/evaluations/v1"
EVALUATION_SUMMARY_KIND = "agentic-workspace/evaluation-summary/v1"
EVALUATION_OBSERVATION_KIND = "agentic-workspace/evaluation-observation/v1"
EVALUATION_CLOSURE_AUTHORITY_KIND = "agentic-workspace/evaluation-closure-authority/v1"
WORKSPACE_EVALUATIONS_PATH = Path(".agentic-workspace/evaluations.json")
WORKSPACE_LOCAL_EVALUATIONS_DIR = Path(".agentic-workspace/local/evaluations")

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
            "authority_envelope.mutation_baseline.baseline_id",
            "authority_envelope.mutation_baseline.head",
            "proof.provenance",
        ],
        "reject_when": [
            "assignment-target-mismatch",
            "baseline-head-changed",
            "scope-expanded",
            "stale-worktree",
            "failed-proof",
            "superseded-result",
        ],
        "consumers": ["status", "doctor", "operating-decision", "proof-selection"],
        "repair_route": "rerun or supersede the evaluation result after refreshing assignment, authority, baseline, and proof context",
    }


def _observation_admission(context: dict[str, Any]) -> dict[str, Any]:
    authority = context.get("authority_envelope", {}) if isinstance(context.get("authority_envelope"), dict) else {}
    baseline = authority.get("mutation_baseline", {}) if isinstance(authority.get("mutation_baseline"), dict) else {}
    proof = context.get("proof", {}) if isinstance(context.get("proof"), dict) else {}
    assignment = context.get("assignment", {}) if isinstance(context.get("assignment"), dict) else {}
    stale_reason = str(baseline.get("revalidation_status") or "").strip()
    if stale_reason in {"stale", "mismatch", "rejected", "failed"}:
        return {
            "status": "rejected",
            "reason": "stale-worktree",
            "repair_route": "refresh mutation baseline and rerun or supersede this evaluation observation",
        }
    if str(proof.get("result") or "").strip() == "failed":
        return {
            "status": "rejected",
            "reason": "failed-proof",
            "repair_route": "rerun proof before admitting this evaluation observation",
        }
    required_present = bool(
        assignment.get("target_identity_ref")
        and assignment.get("context_key")
        and baseline.get("baseline_id")
        and baseline.get("head")
        and proof.get("provenance")
    )
    return {
        "status": "admitted" if required_present else "legacy-unbound",
        "reason": "fresh-bound-context" if required_present else "missing-bound-context",
        "bound_context": required_present,
        "baseline_id": baseline.get("baseline_id"),
        "target_identity_ref": assignment.get("target_identity_ref"),
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
    observation = {
        "kind": EVALUATION_OBSERVATION_KIND,
        "recorded_at": _now(),
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
    admission = _observation_admission(observation["context"])
    if admission["status"] == "rejected":
        raise WorkspaceUsageError(f"evaluation observation rejected ({admission['reason']}): {admission['repair_route']}.")
    observation["admission"] = admission
    path = _observation_path(target_root, evaluation_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(observation, sort_keys=True) + "\n")
    return {
        "kind": EVALUATION_OBSERVATION_KIND,
        "path": WORKSPACE_LOCAL_EVALUATIONS_DIR.joinpath(f"{evaluation_id}.jsonl").as_posix(),
        "outcome": "appended",
        "evaluation_id": evaluation_id,
        "criterion": criterion,
        "result": result,
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
        admitted_observations = [
            item
            for item in observations
            if isinstance(item.get("admission"), dict) and item["admission"].get("status") in {"admitted", "legacy-unbound"}
        ]
        bound_observations = [
            item for item in admitted_observations if isinstance(item.get("admission"), dict) and item["admission"].get("bound_context")
        ]
        current_revision = int(definition["revision"])
        current_bound_observations = [
            item for item in bound_observations if int(item.get("definition_revision", 0) or 0) == current_revision
        ]
        historical_observations = [item for item in admitted_observations if item not in current_bound_observations]
        legacy_unbound_count = len(
            [
                item
                for item in admitted_observations
                if isinstance(item.get("admission"), dict) and item["admission"].get("status") == "legacy-unbound"
            ]
        )
        stale_revision_count = len(bound_observations) - len(current_bound_observations)
        criteria = _criterion_status(definition, current_bound_observations)
        required = [item for item in criteria if item["required"]]
        satisfied = [item for item in required if item["state"] == "satisfied"]
        contradictions = [item for item in criteria if item["state"] == "contradicted"]
        min_observations = int(definition.get("collection_policy", {}).get("minimum_observations", 1))
        conclusion_ready = len(current_bound_observations) >= min_observations and (
            len(satisfied) == len(required) or bool(contradictions) or definition.get("lifecycle") == "enough-signal"
        )
        freshness_status = (
            "fresh-bound"
            if current_bound_observations
            else "stale-bound"
            if bound_observations
            else "legacy-unbound"
            if admitted_observations
            else "missing"
        )
        not_ready_reason = "requires-bound-current-observation" if historical_observations else "needs-more-observations-or-owner-review"
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
        }
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
                    "current_result_identity": current_result_identity,
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
                else "migrate-or-append-bound-observation"
                if historical_observations
                else "append-observation",
            }
        )
    return {"kind": EVALUATION_SUMMARY_KIND, "path": WORKSPACE_EVALUATIONS_PATH.as_posix(), "summaries": summaries}


def transition_evaluation(*, target_root: Path, evaluation_id: str, lifecycle: str, reason: str = "") -> dict[str, Any]:
    definitions = _definitions_payload(target_root)
    definition = _definition_by_id(definitions, evaluation_id)
    if definition is None:
        raise WorkspaceUsageError(f"evaluation {evaluation_id!r} is not registered.")
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
