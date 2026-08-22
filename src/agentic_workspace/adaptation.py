from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

_QUIET_DISPOSITIONS = {"fixed", "retained", "deferred", "dismissed", "not-applicable", "obsolete"}
_MATERIAL_COVERAGE_EFFECTS = {"action", "authority", "proof", "claim", "procedure", "continuation"}
_CONSEQUENTIAL_OWNER_CLASSES = {"architecture", "security", "authority", "public-contract"}
_COVERAGE_SOURCE_CLASSES = {"machine", "repo", "human", "review", "agent"}
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


def coverage_signal_from_observation(observation: dict[str, Any]) -> dict[str, Any]:
    """Translate one bounded operating-fact observation into existing adaptation evidence."""

    source_class = str(observation.get("source_class") or "agent").strip().lower()
    if source_class not in _COVERAGE_SOURCE_CLASSES:
        raise ValueError(f"unsupported coverage evidence source class: {source_class}")
    effects = sorted(
        {str(effect).strip() for effect in _list(observation.get("affected_effects")) if str(effect).strip() in _MATERIAL_COVERAGE_EFFECTS}
    )
    owner_class = str(observation.get("owner_class") or "").strip()
    source_owner = str(observation.get("source_owner") or "").strip()
    observed_addition = str(observation.get("observed_addition") or "").strip()
    operation_id = str(observation.get("operation_id") or "").strip()
    source_refs = sorted({str(ref).strip() for ref in _list(observation.get("source_refs")) if str(ref).strip()})
    evidence_refs = sorted({str(ref).strip() for ref in _list(observation.get("evidence_refs")) if str(ref).strip()})
    material = bool(observation.get("material", bool(effects))) and bool(effects)
    deterministic = observation.get("admission") == "deterministic"
    consequential = owner_class in _CONSEQUENTIAL_OWNER_CLASSES or bool(observation.get("consequential"))
    authoritative_evidence = source_class in {"machine", "repo"}
    mode = "existing-typed-operation" if deterministic and authoritative_evidence and not consequential else "explicit-owner-admission"
    risk_class = "low" if mode == "existing-typed-operation" else "consequential"
    owner_revision = str(observation.get("owner_revision") or "").strip()
    recurrence_identity = str(observation.get("recurrence_identity") or "").strip()
    if not recurrence_identity:
        recurrence_identity = (
            "coverage:"
            + hashlib.sha256(
                json.dumps(
                    {
                        "source_owner": source_owner,
                        "owner_class": owner_class,
                        "effects": effects,
                        "source_refs": source_refs,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()[:20]
        )
    proposed_delta = copy.deepcopy(observation.get("proposed_delta") or {})
    simulation = copy.deepcopy(_dict(observation.get("simulation")))
    if material and not all((owner_class, source_owner, observed_addition, operation_id, source_refs, evidence_refs)):
        raise ValueError("material coverage observations require owner, operation, source, and evidence identity")
    if not simulation:
        simulation = {
            "required_behaviors": [f"preserve-{effect}" for effect in effects] or ["no-operating-effect"],
            "preserved_behaviors": [f"preserve-{effect}" for effect in effects] or ["no-operating-effect"],
            "authority_delta": "none",
            "allowed_owner_paths": [source_owner] if source_owner else [],
            "before_cost": 1,
            "after_cost": 1,
        }
    disposition = str(observation.get("disposition") or ("active" if material else "not-applicable"))
    return {
        "symptom": observed_addition or "repository observation has no material AW operating effect",
        "cost": str(observation.get("rediscovery_cost") or "bounded operating-context rediscovery"),
        "source": source_class,
        "observed_during": str(observation.get("observed_during") or "ordinary-work-reconciliation"),
        "recurrence": str(observation.get("recurrence") or "first-observation"),
        "evidence_fingerprint": recurrence_identity,
        "adaptation": {
            "owner_class": owner_class or "outside-aw-responsibility",
            "source_owner": source_owner or "none",
            "proposed_delta": proposed_delta or {"action": "no-aw-change"},
            "authority_requirement": {
                "mode": mode,
                "operation_id": operation_id,
                "expected_owner_revision": owner_revision,
                "current_owner_revision": owner_revision,
            },
            "risk_class": risk_class,
            "expected_effect": {effect: "represented-by-canonical-owner" for effect in effects},
            "validation_route": copy.deepcopy(_list(observation.get("validation_route"))),
            "rollback": {"mode": "operation-transaction", "revision": owner_revision},
            "retire_when": "the canonical owner admits or explicitly dismisses this source/effect identity",
            "disposition": disposition,
            "simulation": simulation,
            "operation_inputs": copy.deepcopy(_dict(observation.get("operation_inputs"))),
            "coverage": {
                "kind": "agentic-workspace/coverage-candidate-evidence/v1",
                "identity": recurrence_identity,
                "observed_addition": observed_addition,
                "source_class": source_class,
                "source_refs": source_refs,
                "evidence_refs": evidence_refs,
                "affected_effects": effects,
                "confidence": str(observation.get("confidence") or ("high" if authoritative_evidence else "advisory")),
                "authority": "evidence" if source_class in {"agent", "human", "review"} else "structured-source",
                "material": material,
                "admission": "deterministic" if mode == "existing-typed-operation" else "decision-required",
                "must_resolve_before_closeout": bool(observation.get("must_resolve_before_closeout", material)),
                "defer_until": str(observation.get("defer_until") or ""),
            },
        },
    }


def machine_observed_coverage_signals(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Admit only structured owner declarations as machine-observed coverage evidence."""

    supported = {
        "proof-route-declaration": ("proof-route", "proof", "proof.report", ["proof", "claim"]),
        "generated-surface-declaration": (
            "generated-projection",
            "generated-references",
            "generated-command-packages.refresh",
            ["action", "authority", "procedure"],
        ),
        "ownership-boundary-declaration": ("ownership", "ownership", "ownership.classify-paths", ["action", "authority"]),
        "module-capability-declaration": (
            "module-capability",
            "assignment",
            "assignment.resolve-target",
            ["action", "procedure", "continuation"],
        ),
    }
    signals: list[dict[str, Any]] = []
    for record in records:
        declaration_kind = str(record.get("declaration_kind") or "")
        mapping = supported.get(declaration_kind)
        if mapping is None:
            continue
        owner_class, default_owner, operation_id, default_effects = mapping
        signals.append(
            coverage_signal_from_observation(
                {
                    **record,
                    "source_class": "machine",
                    "owner_class": owner_class,
                    "source_owner": str(record.get("source_owner") or default_owner),
                    "operation_id": str(record.get("operation_id") or operation_id),
                    "affected_effects": _list(record.get("affected_effects")) or default_effects,
                    "admission": str(record.get("admission") or "deterministic"),
                }
            )
        )
    return signals


def coverage_candidate_findings(projection: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose unresolved candidates through the existing context-consequence path."""

    findings: list[dict[str, Any]] = []
    for candidate in _list(projection.get("candidates")):
        candidate = _dict(candidate)
        coverage = _dict(candidate.get("coverage"))
        if not coverage or candidate.get("status") == "quiet":
            continue
        defer_until = str(coverage.get("defer_until") or "")
        must_resolve = coverage.get("must_resolve_before_closeout") is True and not defer_until
        findings.append(
            {
                "kind": "agentic-workspace/coverage-candidate/v1",
                "id": str(candidate.get("id") or ""),
                "finding_class": "coverage-gap",
                "lifecycle": "unresolved",
                "severity": "material",
                "owner": str(candidate.get("source_owner") or candidate.get("owner_class") or "workspace-maintainer"),
                "task_relevant": coverage.get("material") is True,
                "affected_decisions": copy.deepcopy(_list(coverage.get("affected_effects"))),
                "evidence_refs": copy.deepcopy(_list(coverage.get("evidence_refs"))),
                "current_task_effect": "requires disposition before broad clean closeout" if must_resolve else "",
                **({"defer_until": defer_until} if defer_until else {}),
                "coverage_candidate": copy.deepcopy(candidate),
            }
        )
    return findings


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


def _path_revision(path: Path) -> str:
    try:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _operation_runtime_consumed(contract: dict[str, Any] | None) -> bool:
    return isinstance(contract, dict) and contract.get("migration_status") == "runtime-consumed"


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


def admit_bounded_adaptation(
    candidate: dict[str, Any],
    *,
    admitted_by: str,
    choice: str = "admit",
    decision_revision: str = "",
    defer_until: str = "",
) -> dict[str, Any]:
    """Record an explicit owner decision without weakening automatic-promotion policy."""
    admitted_by = str(admitted_by or "").strip()
    owner_class = str(candidate.get("owner_class") or "")
    if owner_class not in {"scoped-instruction", "memory"}:
        raise ValueError("explicit owner admission is supported only for scoped-instruction or Memory adaptations")
    if candidate.get("status") != "owner-review-required":
        raise ValueError("owner admission requires an owner-review-required candidate")
    if not admitted_by:
        raise ValueError("owner admission must identify the admitting human or owner")
    if choice not in {"admit", "update", "retain", "defer", "dismiss"}:
        raise ValueError(f"unsupported maintenance decision choice: {choice}")
    if choice == "defer" and not defer_until:
        raise ValueError("deferred maintenance decisions require an exact re-entry trigger")
    admitted = copy.deepcopy(candidate)
    admitted["owner_admission"] = {
        "kind": "agentic-workspace/adaptation-owner-admission/v1",
        "status": "admitted",
        "admitted_by": admitted_by,
        "choice": choice,
        "decision_revision": decision_revision,
        "defer_until": defer_until,
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
    if not _operation_runtime_consumed(contract):
        raise ValueError(f"adaptation operation is not runtime-consumed authority: {operation_id}")
    if operation_id not in {"proof.report", "instructions.create", "workspace.memory-create-note.apply"}:
        raise ValueError(f"adaptation operation has no bounded execution adapter: {operation_id}")
    operation_inputs = _dict(candidate.get("operation_inputs"))
    proposed_delta = candidate.get("proposed_delta")
    if not isinstance(proposed_delta, dict):
        raise ValueError("bounded adaptation requires a typed semantic delta")

    if operation_id in {"instructions.create", "workspace.memory-create-note.apply"}:
        admission = _dict(candidate.get("owner_admission"))
        if admission.get("status") != "admitted" or not str(admission.get("admitted_by") or "").strip():
            raise ValueError("consequential adaptation requires explicit owner admission")
        choice = str(admission.get("choice") or "admit")
        if choice in {"retain", "defer", "dismiss"}:
            if operation_id != "instructions.create":
                raise ValueError(f"{operation_id} does not support persisted {choice} disposition")
            source_path = target_root / str(candidate.get("source_owner") or "")
            expected_revision = str(authority.get("expected_owner_revision") or "")
            if operation_id == "instructions.create" and source_path.exists():
                from agentic_workspace.scoped_instructions import read_instruction

                current_revision = read_instruction(source_path, root=target_root).revision
            else:
                current_revision = _path_revision(source_path)
            if not expected_revision or current_revision != expected_revision:
                return {
                    "kind": "agentic-workspace/bounded-adaptation-execution/v1",
                    "status": "superseded",
                    "candidate_id": str(candidate.get("id") or ""),
                    "operation_id": operation_id,
                    "disposition": "superseded",
                    "expected_owner_revision": expected_revision,
                    "current_owner_revision": current_revision,
                    "mutation_applied": False,
                    "owner_admission": copy.deepcopy(admission),
                    "rule": "A non-mutating semantic disposition is rejected when its presented owner revision is no longer current.",
                }
    if operation_id == "workspace.memory-create-note.apply":
        from repo_memory_bootstrap.installer import create_memory_note

        manifest_path = target_root / ".agentic-workspace/memory/repo/manifest.toml"
        expected_revision = str(authority.get("expected_owner_revision") or "")
        current_revision = _path_revision(manifest_path)
        if not expected_revision or current_revision != expected_revision:
            return {
                "kind": "agentic-workspace/bounded-adaptation-execution/v1",
                "status": "superseded",
                "candidate_id": str(candidate.get("id") or ""),
                "operation_id": operation_id,
                "operation_contract": f"src/agentic_workspace/contracts/operations/{operation_id}.json",
                "disposition": "superseded",
                "automatic_promotion": False,
                "owner_admission": copy.deepcopy(admission),
                "expected_owner_revision": expected_revision,
                "current_owner_revision": current_revision,
                "mutation_applied": False,
                "rule": "Memory coverage admission fails closed when its canonical manifest revision changed after owner review.",
            }
        if proposed_delta.get("action") != "create_memory_note":
            raise ValueError("Memory coverage admission requires a create_memory_note semantic delta")
        result = create_memory_note(
            slug=str(proposed_delta.get("slug") or ""),
            title=str(proposed_delta.get("title") or "") or None,
            target=target_root,
            folder=str(proposed_delta.get("folder") or "domains"),
            note_type=str(proposed_delta.get("note_type") or "domain"),
            summary=str(proposed_delta.get("summary") or ""),
            applies_to=[str(item) for item in _list(proposed_delta.get("applies_to"))],
            use_when=[str(item) for item in _list(proposed_delta.get("use_when"))],
            routes_from=[str(item) for item in _list(proposed_delta.get("routes_from"))],
            stale_when=[str(item) for item in _list(proposed_delta.get("stale_when"))],
            evidence=[str(item) for item in _list(proposed_delta.get("evidence"))],
            memory_role=str(proposed_delta.get("memory_role") or ""),
            dry_run=dry_run,
        ).to_dict()
        actions = [_dict(item) for item in _list(result.get("actions"))]
        blocked = any(item.get("kind") == "manual review" for item in actions)
        applied = not dry_run and not blocked and any(item.get("kind") == "created" for item in actions)
        return {
            "kind": "agentic-workspace/bounded-adaptation-execution/v1",
            "status": "blocked" if blocked else "simulated" if dry_run else "quiet" if applied else "blocked",
            "candidate_id": str(candidate.get("id") or ""),
            "operation_id": operation_id,
            "operation_contract": f"src/agentic_workspace/contracts/operations/{operation_id}.json",
            "disposition": "fixed" if applied else "active",
            "automatic_promotion": False,
            "owner_admission": copy.deepcopy(admission),
            "expected_owner_revision": expected_revision,
            "post_owner_revision": _path_revision(manifest_path),
            "mutation_applied": applied,
            "operation_result": result,
            "rule": "Memory coverage enters the canonical manifest and note only after explicit owner admission and a matching manifest revision.",
        }
    if operation_id == "instructions.create":
        from agentic_workspace.scoped_instructions import apply_instruction_operation

        choice = str(admission.get("choice") or "admit")
        disposition_record = {
            "candidate_id": str(candidate.get("id") or ""),
            "choice": choice,
            "decision_revision": str(admission.get("decision_revision") or ""),
            "defer_until": str(admission.get("defer_until") or ""),
            "admitted_by": str(admission.get("admitted_by") or ""),
        }
        operation_result = apply_instruction_operation(
            target_root=target_root,
            operation_id=operation_id,
            values={
                "name": Path(str(candidate.get("source_owner") or "")).stem,
                "adaptation_mode": "disposition" if choice in {"retain", "defer", "dismiss"} else "apply",
                "adaptation_authority_path": str(candidate.get("source_owner") or ""),
                "adaptation_expected_revision": str(authority.get("expected_owner_revision") or ""),
                "adaptation_delta_json": json.dumps(proposed_delta, sort_keys=True),
                "adaptation_disposition_json": json.dumps(disposition_record, sort_keys=True),
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
            "status": (
                "superseded"
                if stale
                else "deferred"
                if applied and choice == "defer"
                else "quiet"
                if applied
                else "simulated"
                if dry_run
                else "blocked"
            ),
            "candidate_id": str(candidate.get("id") or ""),
            "operation_id": operation_id,
            "operation_contract": f"src/agentic_workspace/contracts/operations/{operation_id}.json",
            "disposition": "superseded" if stale else choice if applied else "active",
            "automatic_promotion": False,
            "owner_admission": copy.deepcopy(admission),
            "expected_owner_revision": str(authority.get("expected_owner_revision") or ""),
            "post_owner_revision": str(operation_result.get("post_authority_revision") or ""),
            "validation_status": str(operation_result.get("validation_status") or "not-run"),
            "mutation_applied": bool(operation_result.get("mutation_applied", applied)),
            "rollback": copy.deepcopy(operation_result.get("rollback")),
            "operation_result": operation_result,
            "rule": "Consequential instruction choices dispatch through the registered canonical operation, persist source-bound disposition, and restore pre-apply bytes on failed validation.",
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


def bounded_adaptation_projection(signals: list[dict[str, Any]], *, target_root: Path | None = None) -> dict[str, Any]:
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
        coverage_identity = str(_dict(candidate.get("coverage")).get("identity") or "")
        candidate_id = (
            "adapt-" + hashlib.sha256(coverage_identity.encode()).hexdigest()[:20]
            if coverage_identity
            else _candidate_id(
                source_owner=str(candidate["source_owner"]),
                owner_class=str(candidate["owner_class"]),
                symptom=candidate["symptom"],
                proposed_delta=str(candidate["proposed_delta"]),
            )
        )
        grouped.setdefault(candidate_id, []).append(candidate)

    candidates: list[dict[str, Any]] = []
    for candidate_id, equivalents in sorted(grouped.items()):
        candidate = equivalents[0]
        authority = _dict(candidate.get("authority_requirement"))
        disposition = str(candidate.get("disposition") or "active")
        persisted_disposition: dict[str, Any] = {}
        if target_root is not None and candidate.get("owner_class") == "scoped-instruction":
            from agentic_workspace.scoped_instructions import instruction_maintenance_disposition

            persisted_disposition = instruction_maintenance_disposition(
                target_root / str(candidate.get("source_owner") or ""),
                candidate_id=candidate_id,
            )
            coverage = _dict(candidate.get("coverage"))
            trigger_matches = str(persisted_disposition.get("defer_until") or "") == str(coverage.get("defer_until") or "")
            if persisted_disposition.get("status") == "current" and trigger_matches:
                disposition = {
                    "admit": "fixed",
                    "update": "fixed",
                    "retain": "retained",
                    "defer": "deferred",
                    "dismiss": "dismissed",
                }.get(str(persisted_disposition.get("choice") or ""), disposition)
            elif persisted_disposition and not trigger_matches:
                persisted_disposition = {**persisted_disposition, "status": "stale-trigger-changed"}
        simulation = simulate_adaptation(candidate)
        operation_id = str(authority.get("operation_id") or "")
        operation_contract = _registered_operation(operation_id)
        operation_registered = operation_contract is not None
        operation_runtime_consumed = _operation_runtime_consumed(operation_contract)
        revision_matched = bool(authority.get("expected_owner_revision")) and authority.get("expected_owner_revision") == authority.get(
            "current_owner_revision"
        )
        auto_eligible = (
            candidate.get("risk_class") == "low"
            and authority.get("mode") == "existing-typed-operation"
            and operation_registered
            and operation_runtime_consumed
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
                "persisted_disposition": persisted_disposition,
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
                    "operation_runtime_consumed": operation_runtime_consumed,
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
