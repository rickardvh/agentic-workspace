from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_workspace import cli
from agentic_workspace.config import WorkspaceUsageError
from agentic_workspace.contract_tooling import contract_schema
from agentic_workspace.evaluation import (
    ASSIGNMENT_AUTHORITY_RECEIPT_DIR,
    EVALUATION_OBSERVATION_KIND,
    EVALUATION_SUMMARY_KIND,
    EVALUATIONS_KIND,
    OBSERVATION_RETENTION_CAP,
    PROOF_AUTHORITY_RECEIPT_DIR,
    WORKSPACE_EVALUATIONS_PATH,
    WORKSPACE_LOCAL_EVALUATIONS_DIR,
    _write_indexed_owner_receipt,
    append_observation,
    closure_authority,
    evaluation_summary,
    prune_observations,
    record_material_finding_followup,
    register_evaluation,
    transition_evaluation,
    write_observation_authority,
)


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
