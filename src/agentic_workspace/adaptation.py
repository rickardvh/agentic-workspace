from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

_QUIET_DISPOSITIONS = {"fixed", "superseded", "dismissed", "not-applicable", "obsolete"}
_OPERATION_CONTRACT_ROOT = Path(__file__).parent / "contracts" / "operations"


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalized(value: Any) -> str:
    text = re.sub(r"https?://\S+", "<url>", str(value or "").strip().lower())
    text = re.sub(r"#[0-9]+", "#<issue>", text)
    text = re.sub(r"\b[0-9a-f]{8,}\b", "<identity>", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\b", "<n>", text)
    return " ".join(text.split())


def _candidate_id(*, source_owner: str, owner_class: str, symptom: str, proposed_delta: str) -> str:
    basis = {
        "source_owner": source_owner,
        "owner_class": owner_class,
        "symptom": _normalized(symptom),
        "proposed_delta": _normalized(proposed_delta),
    }
    return "adapt-" + hashlib.sha256(json.dumps(basis, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]


def simulate_adaptation(candidate: dict[str, Any]) -> dict[str, Any]:
    simulation = _dict(candidate.get("simulation"))
    required = {str(item) for item in _list(simulation.get("required_behaviors")) if str(item)}
    preserved = {str(item) for item in _list(simulation.get("preserved_behaviors")) if str(item)}
    reasons: list[str] = []
    missing_behaviors = sorted(required - preserved)
    if missing_behaviors:
        reasons.append("required-behavior-removed")
    if str(simulation.get("authority_delta") or "none") != "none":
        reasons.append("authority-widened")
    allowed_paths = {str(item) for item in _list(simulation.get("allowed_owner_paths")) if str(item)}
    if allowed_paths and str(candidate.get("source_owner") or "") not in allowed_paths:
        reasons.append("source-owner-outside-admitted-scope")
    before_cost = simulation.get("before_cost")
    after_cost = simulation.get("after_cost")
    if isinstance(before_cost, (int, float)) and isinstance(after_cost, (int, float)) and after_cost > before_cost:
        reasons.append("cost-boundary-worsened")
    before_precision = simulation.get("before_precision")
    after_precision = simulation.get("after_precision")
    if isinstance(before_precision, (int, float)) and isinstance(after_precision, (int, float)) and after_precision < before_precision:
        reasons.append("precision-boundary-worsened")
    complete = bool(required) and before_cost is not None and after_cost is not None
    return {
        "kind": "agentic-workspace/adaptation-simulation/v1",
        "status": "rejected" if reasons else "passed" if complete else "evidence-required",
        "reason_codes": reasons,
        "missing_required_behaviors": missing_behaviors,
        "cost_delta": after_cost - before_cost if isinstance(before_cost, (int, float)) and isinstance(after_cost, (int, float)) else None,
        "precision_delta": (
            after_precision - before_precision
            if isinstance(before_precision, (int, float)) and isinstance(after_precision, (int, float))
            else None
        ),
        "replay_route": candidate.get("validation_route"),
        "rule": "Promotion fails closed when replay removes required behavior, widens authority, or worsens the declared cost/precision boundary.",
    }


def _registered_operation(operation_id: str) -> dict[str, Any] | None:
    contract_path = _OPERATION_CONTRACT_ROOT / f"{operation_id}.json"
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(contract, dict) or str(contract.get("id") or "") != operation_id:
        return None
    return contract


def adaptation_signal_from_proof_route_finding(
    finding: dict[str, Any],
    *,
    semantic_delta: dict[str, Any],
    simulation: dict[str, Any],
    expected_effect: dict[str, Any],
) -> dict[str, Any]:
    """Bind a real route-health signal to its guarded, registered owner operation."""
    signal = copy.deepcopy(_dict(finding.get("improvement_signal_candidate")))
    repair = _dict(finding.get("repair_operation"))
    apply_contract = _dict(repair.get("apply_contract"))
    canonical_surface = str(finding.get("canonical_edit_surface") or "")
    authority_path = str(apply_contract.get("authority_path") or canonical_surface.split("[", 1)[0].strip())
    field_selector = str(apply_contract.get("field_selector") or "")
    changed_paths = [str(path) for path in _list(_dict(signal.get("applicability_identity")).get("changed_paths")) if str(path)]
    operation_id = str(repair.get("operation_id") or "")
    if not signal or not operation_id or not authority_path or not field_selector or not changed_paths:
        raise ValueError("proof-route adaptation requires a current route-health signal and guarded repair operation")
    expected_revision = str(repair.get("expected_authority_revision") or "")
    signal["adaptation"] = {
        "owner_class": "proof-route",
        "source_owner": authority_path,
        "proposed_delta": copy.deepcopy(semantic_delta),
        "authority_requirement": {
            "mode": "existing-typed-operation",
            "operation_id": operation_id,
            "expected_owner_revision": expected_revision,
            "current_owner_revision": str(finding.get("route_authority_revision") or ""),
        },
        "risk_class": "low",
        "expected_effect": copy.deepcopy(expected_effect),
        "validation_route": copy.deepcopy(finding.get("validation_commands") or []),
        "rollback": {
            "mode": "operation-transaction",
            "rule": str(apply_contract.get("rollback_on_failure") or "restore pre-apply owner bytes"),
        },
        "retire_when": "the guarded apply validates and a later equivalent route-health projection is quiet",
        "disposition": "active",
        "simulation": copy.deepcopy(simulation),
        "operation_inputs": {
            "finding_id": str(finding.get("id") or ""),
            "authority_path": authority_path,
            "field_selector": field_selector,
            "changed_paths": changed_paths,
            "idempotency_key": str(apply_contract.get("idempotency_key") or ""),
            "disposition": "fixed",
        },
    }
    return signal


def admit_bounded_adaptation(candidate: dict[str, Any], *, admitted_by: str) -> dict[str, Any]:
    """Record an explicit owner decision without weakening automatic-promotion policy."""
    admitted_by = str(admitted_by or "").strip()
    if str(candidate.get("owner_class") or "") != "scoped-instruction":
        raise ValueError("explicit owner admission is supported only for scoped-instruction adaptations")
    if candidate.get("status") != "owner-review-required":
        raise ValueError("owner admission requires an owner-review-required candidate")
    if not admitted_by:
        raise ValueError("owner admission must identify the admitting human or owner")
    admitted = copy.deepcopy(candidate)
    admitted["owner_admission"] = {
        "kind": "agentic-workspace/adaptation-owner-admission/v1",
        "status": "admitted",
        "admitted_by": admitted_by,
        "scope": "one-candidate-one-owner-revision",
        "candidate_id": str(candidate.get("id") or ""),
        "expected_owner_revision": str(_dict(candidate.get("authority_requirement")).get("expected_owner_revision") or ""),
    }
    admitted["status"] = "promotion-ready"
    admitted["promotion"] = {
        **_dict(admitted.get("promotion")),
        "status": "owner-admitted",
        "automatic": False,
    }
    return admitted


def execute_bounded_adaptation(candidate: dict[str, Any], *, target_root: Path, dry_run: bool = False) -> dict[str, Any]:
    """Execute an admitted low-risk adaptation through its canonical owner operation."""
    authority = _dict(candidate.get("authority_requirement"))
    operation_id = str(authority.get("operation_id") or "")
    contract = _registered_operation(operation_id)
    simulation = _dict(candidate.get("simulation_result")) or simulate_adaptation(candidate)
    if candidate.get("status") != "promotion-ready" or simulation.get("status") != "passed":
        raise ValueError("adaptation execution requires a promotion-ready candidate with a passed simulation")
    if contract is None:
        raise ValueError(f"adaptation operation is not registered: {operation_id}")
    if operation_id not in {"proof.report", "instructions.create"}:
        raise ValueError(f"adaptation operation has no bounded execution adapter: {operation_id}")
    operation_inputs = _dict(candidate.get("operation_inputs"))
    proposed_delta = candidate.get("proposed_delta")
    if not isinstance(proposed_delta, dict):
        raise ValueError("bounded adaptation requires a typed semantic delta")

    if operation_id == "instructions.create":
        admission = _dict(candidate.get("owner_admission"))
        if admission.get("status") != "admitted" or not str(admission.get("admitted_by") or "").strip():
            raise ValueError("scoped-instruction adaptation requires explicit owner admission")
        from agentic_workspace.scoped_instructions import apply_instruction_operation

        operation_result = apply_instruction_operation(
            target_root=target_root,
            operation_id=operation_id,
            values={
                "adaptation_mode": "apply",
                "adaptation_authority_path": str(candidate.get("source_owner") or ""),
                "adaptation_expected_revision": str(authority.get("expected_owner_revision") or ""),
                "adaptation_delta_json": json.dumps(proposed_delta, sort_keys=True),
                "owner_admission": "admitted",
                "owner_admission_by": str(admission.get("admitted_by") or ""),
                "dry_run": dry_run,
            },
        )
        operation_status = str(operation_result.get("status") or "")
        stale = operation_status == "blocked-stale-authority-revision"
        applied = operation_status in {"applied", "already-applied"}
        return {
            "kind": "agentic-workspace/bounded-adaptation-execution/v1",
            "status": "superseded" if stale else "quiet" if applied else "simulated" if dry_run else "blocked",
            "candidate_id": str(candidate.get("id") or ""),
            "operation_id": operation_id,
            "operation_contract": f"src/agentic_workspace/contracts/operations/{operation_id}.json",
            "disposition": "superseded" if stale else "fixed" if applied else "active",
            "automatic_promotion": False,
            "owner_admission": copy.deepcopy(admission),
            "expected_owner_revision": str(authority.get("expected_owner_revision") or ""),
            "post_owner_revision": str(operation_result.get("post_authority_revision") or ""),
            "validation_status": str(operation_result.get("validation_status") or "not-run"),
            "rollback": copy.deepcopy(operation_result.get("rollback")),
            "operation_result": operation_result,
            "rule": "Consequential instruction changes require explicit owner admission and a registered, revision-guarded canonical operation; failed validation restores the pre-apply bytes.",
        }

    from agentic_workspace.workspace_runtime_proof import _proof_route_repair_operation_payload

    operation_result = _proof_route_repair_operation_payload(
        target_root=target_root,
        changed_paths=[str(path) for path in _list(operation_inputs.get("changed_paths")) if str(path)],
        mode="apply",
        finding_id=str(operation_inputs.get("finding_id") or ""),
        authority_path=str(operation_inputs.get("authority_path") or ""),
        field_selector=str(operation_inputs.get("field_selector") or ""),
        expected_revision=str(authority.get("expected_owner_revision") or ""),
        delta_json=json.dumps(proposed_delta, sort_keys=True),
        disposition=str(operation_inputs.get("disposition") or "fixed"),
        idempotency_key=str(operation_inputs.get("idempotency_key") or ""),
        dry_run=dry_run,
    )
    operation_status = str(operation_result.get("status") or "")
    stale = operation_status == "blocked-stale-authority-revision"
    applied = operation_status in {"applied", "already-applied"}
    return {
        "kind": "agentic-workspace/bounded-adaptation-execution/v1",
        "status": "superseded" if stale else "quiet" if applied else "simulated" if dry_run else "blocked",
        "candidate_id": str(candidate.get("id") or ""),
        "operation_id": operation_id,
        "operation_contract": f"src/agentic_workspace/contracts/operations/{operation_id}.json",
        "disposition": "superseded" if stale else "fixed" if applied else "active",
        "expected_owner_revision": str(authority.get("expected_owner_revision") or ""),
        "post_owner_revision": str(operation_result.get("post_authority_revision") or ""),
        "validation_status": str(_dict(operation_result.get("apply_receipt")).get("validation_status") or "not-run"),
        "rollback": copy.deepcopy(operation_result.get("rollback")),
        "operation_result": operation_result,
        "rule": "Only a registered operation can mutate the canonical owner; stale revisions supersede the candidate and failed validation rolls back before an execution receipt is returned.",
    }


def bounded_adaptation_projection(signals: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for signal in signals:
        adaptation = _dict(signal.get("adaptation"))
        required = (
            "owner_class",
            "source_owner",
            "proposed_delta",
            "authority_requirement",
            "expected_effect",
            "validation_route",
            "rollback",
        )
        if not adaptation or any(adaptation.get(field) in (None, "", [], {}) for field in required):
            continue
        candidate = copy.deepcopy(adaptation)
        candidate["symptom"] = str(signal.get("symptom") or "")
        candidate["evidence"] = {
            "fingerprint": str(signal.get("evidence_fingerprint") or ""),
            "source": str(signal.get("source") or ""),
            "observed_during": str(signal.get("observed_during") or ""),
            "cost": str(signal.get("cost") or ""),
            "recurrence": str(signal.get("recurrence") or ""),
        }
        candidate_id = _candidate_id(
            source_owner=str(candidate["source_owner"]),
            owner_class=str(candidate["owner_class"]),
            symptom=candidate["symptom"],
            proposed_delta=str(candidate["proposed_delta"]),
        )
        grouped.setdefault(candidate_id, []).append(candidate)

    candidates: list[dict[str, Any]] = []
    for candidate_id, equivalents in sorted(grouped.items()):
        candidate = equivalents[0]
        authority = _dict(candidate.get("authority_requirement"))
        disposition = str(candidate.get("disposition") or "active")
        simulation = simulate_adaptation(candidate)
        operation_id = str(authority.get("operation_id") or "")
        operation_registered = _registered_operation(operation_id) is not None
        revision_matched = bool(authority.get("expected_owner_revision")) and authority.get("expected_owner_revision") == authority.get(
            "current_owner_revision"
        )
        auto_eligible = (
            candidate.get("risk_class") == "low"
            and authority.get("mode") == "existing-typed-operation"
            and operation_registered
            and revision_matched
            and simulation["status"] == "passed"
        )
        quiet = disposition in _QUIET_DISPOSITIONS
        candidate.update(
            {
                "kind": "agentic-workspace/bounded-adaptation-candidate/v1",
                "id": candidate_id,
                "status": "quiet"
                if quiet
                else "promotion-ready"
                if auto_eligible
                else "rejected"
                if simulation["status"] == "rejected"
                else "owner-review-required",
                "disposition": disposition,
                "equivalent_signal_count": len(equivalents),
                "evidence": [item["evidence"] for item in equivalents[:3]],
                "simulation_result": simulation,
                "promotion": {
                    "status": "existing-operation-ready"
                    if auto_eligible
                    else "not-authorized"
                    if simulation["status"] == "rejected"
                    else "owner-admission-required",
                    "operation_id": authority.get("operation_id"),
                    "operation_registered": operation_registered,
                    "revision_guard": "matched" if revision_matched else "missing-or-stale",
                    "canonical_source_only": True,
                    "learned_override_created": False,
                },
                "retire_when": candidate.get("retire_when")
                or "the canonical owner revision changes and later equivalent evidence no longer contains the original friction",
            }
        )
        candidates.append(candidate)
    active = [candidate for candidate in candidates if candidate["status"] != "quiet"]
    return {
        "kind": "agentic-workspace/bounded-adaptation-projection/v1",
        "status": "attention" if active else "quiet",
        "candidate_count": len(candidates),
        "active_candidate_count": len(active),
        "candidates": candidates,
        "first_line_cost": "none" if not active else "selector-only",
        "rule": "Adaptations are derived from existing improvement evidence, mutate only canonical source owners through existing operations, and never form a learned override layer.",
    }
