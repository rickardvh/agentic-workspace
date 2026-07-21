from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_workspace import cli
from agentic_workspace.config import WorkspaceUsageError
from agentic_workspace.contract_tooling import contract_schema
from agentic_workspace.evaluation import (
    EVALUATION_OBSERVATION_KIND,
    EVALUATION_SUMMARY_KIND,
    EVALUATIONS_KIND,
    WORKSPACE_EVALUATIONS_PATH,
    WORKSPACE_LOCAL_EVALUATIONS_DIR,
    append_observation,
    closure_authority,
    evaluation_summary,
    register_evaluation,
    transition_evaluation,
)


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
    result = register_evaluation(target_root=tmp_path, **_definition_kwargs())

    assert result["kind"] == EVALUATIONS_KIND
    definitions = json.loads((tmp_path / WORKSPACE_EVALUATIONS_PATH).read_text(encoding="utf-8"))
    Draft202012Validator(contract_schema("evaluation_definition.schema.json")).validate(definitions)

    observed = append_observation(
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

    assert observed["kind"] == EVALUATION_OBSERVATION_KIND
    observation_path = tmp_path / WORKSPACE_LOCAL_EVALUATIONS_DIR / "eval-1969-operating-loop.jsonl"
    observation = json.loads(observation_path.read_text(encoding="utf-8").strip())
    Draft202012Validator(contract_schema("evaluation_observation.schema.json")).validate(observation)
    assert observation["admission"]["status"] == "legacy-unbound"

    summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")
    assert summary["kind"] == EVALUATION_SUMMARY_KIND
    Draft202012Validator(contract_schema("evaluation_summary.schema.json")).validate(summary)
    item = summary["summaries"][0]
    assert item["coverage"]["observation_count"] == 1
    assert item["coverage"]["decision_observation_count"] == 0
    assert item["coverage"]["legacy_unbound_count"] == 1
    assert item["criterion_status"][0]["state"] == "unobserved"
    assert item["fresh_result_admission"]["status"] == "legacy-unbound"
    assert item["fresh_result_admission"]["historical_observation_count"] == 1
    assert item["conclusion_readiness"] == {
        "ready": False,
        "reason_code": "requires-bound-current-observation",
    }
    assert item["next_collection_action"] == "migrate-or-append-bound-observation"


def test_evaluation_update_increments_revision_without_rewriting_observations(tmp_path: Path) -> None:
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["ref"],
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
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context={
            "assignment": {
                "target_identity_ref": "user-local:codex-current",
                "context_key": "mechanical-follow-through::mechanical-follow-through",
            },
            "authority_envelope": {
                "mutation_baseline": {
                    "baseline_id": "abc123",
                    "head": "def456",
                    "revalidation_status": "fresh",
                }
            },
            "proof": {"result": "passed", "provenance": "proof-receipts/run-1.json"},
        },
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
    )
    assert result["from"] == "collecting"
    assert result["to"] == "paused"

    with pytest.raises(WorkspaceUsageError, match="invalid evaluation lifecycle transition"):
        transition_evaluation(target_root=tmp_path, evaluation_id="eval-1969-operating-loop", lifecycle="satisfied")


def test_evaluation_observation_binds_fresh_assignment_authority_and_proof(tmp_path: Path) -> None:
    register_evaluation(target_root=tmp_path, **_definition_kwargs())

    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context={
            "assignment": {
                "target_identity_ref": "user-local:codex-current",
                "context_key": "mechanical-follow-through::mechanical-follow-through",
            },
            "authority_envelope": {
                "mutation_baseline": {
                    "baseline_id": "abc123",
                    "head": "def456",
                    "revalidation_status": "fresh",
                }
            },
            "proof": {"result": "passed", "provenance": "proof-receipts/run-1.json"},
        },
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
        "baseline_id": "abc123",
        "target_identity_ref": "user-local:codex-current",
    }
    assert identity["recorded_at"]
    assert item["coverage"]["decision_observation_count"] == 1
    assert item["conclusion_readiness"]["ready"] is True
    latest = item["latest_material_changes"][0]
    assert latest["admission"]["status"] == "admitted"
    assert latest["admission"]["baseline_id"] == "abc123"
    assert latest["admission"]["target_identity_ref"] == "user-local:codex-current"
    assert "proof-selection" in item["fresh_result_admission"]["admission_contract"]["consumers"]


def test_evaluation_rejects_stale_mutation_baseline_observation(tmp_path: Path) -> None:
    register_evaluation(target_root=tmp_path, **_definition_kwargs())

    with pytest.raises(WorkspaceUsageError, match="stale-worktree"):
        append_observation(
            target_root=tmp_path,
            evaluation_id="eval-1969-operating-loop",
            criterion="reconstruction-cost",
            result="supports",
            evidence_refs=["proof-receipts/run-1.json"],
            context={
                "assignment": {
                    "target_identity_ref": "user-local:codex-current",
                    "context_key": "mechanical-follow-through::mechanical-follow-through",
                },
                "authority_envelope": {
                    "mutation_baseline": {
                        "baseline_id": "abc123",
                        "head": "def456",
                        "revalidation_status": "stale",
                    }
                },
                "proof": {"result": "passed", "provenance": "proof-receipts/run-1.json"},
            },
        )


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
    register_evaluation(target_root=tmp_path, **_definition_kwargs())
    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["legacy-log"],
    )
    legacy_summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")

    blocked = closure_authority(implementation_complete=True, proof_complete=True, evaluation=legacy_summary)
    assert blocked["issue_closure_authorized"] is False
    assert blocked["evaluation_admission"] == "invalid"
    assert blocked["blocked_reasons"] == ["longitudinal-evaluation-invalid"]

    append_observation(
        target_root=tmp_path,
        evaluation_id="eval-1969-operating-loop",
        criterion="reconstruction-cost",
        result="supports",
        evidence_refs=["proof-receipts/run-1.json"],
        context={
            "assignment": {
                "target_identity_ref": "user-local:codex-current",
                "context_key": "mechanical-follow-through::mechanical-follow-through",
            },
            "authority_envelope": {
                "mutation_baseline": {
                    "baseline_id": "abc123",
                    "head": "def456",
                    "revalidation_status": "fresh",
                }
            },
            "proof": {"result": "passed", "provenance": "proof-receipts/run-1.json"},
        },
    )
    fresh_summary = evaluation_summary(target_root=tmp_path, evaluation_id="eval-1969-operating-loop")

    authorized = closure_authority(implementation_complete=True, proof_complete=True, evaluation=fresh_summary)
    assert authorized["issue_closure_authorized"] is True
    assert authorized["evaluation_admission"] == "fresh-bound-ready"


def test_evaluation_cli_register_observe_status(tmp_path: Path, capsys) -> None:
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
            ]
        )
        == 0
    )
    observed = json.loads(capsys.readouterr().out)
    assert observed["outcome"] == "appended"

    assert cli.main(["evaluation", "--target", str(tmp_path), "--format", "json", "status", "--evaluation-id", "eval-cost"]) == 0
    status = json.loads(capsys.readouterr().out)
    summary = status["summaries"][0]
    assert summary["fresh_result_admission"]["status"] == "legacy-unbound"
    assert summary["conclusion_readiness"]["ready"] is False
    assert summary["next_collection_action"] == "migrate-or-append-bound-observation"
