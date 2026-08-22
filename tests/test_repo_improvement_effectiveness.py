from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workspace.repo_improvement_effectiveness import (
    compile_repo_improvement_effectiveness,
    register_repo_improvement_evaluation,
)


def _candidate(**overrides: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "id": "candidate-proof-reentry",
        "suspected_owner": "proof-owner",
        "evidence_refs": ["#2649"],
        "improvement_claim": {
            "action_id": "repo-improvement-action:aaaaaaaaaaaaaaaa",
            "execution_id": "repo-improvement-execution:bbbbbbbbbbbbbbbb",
            "source_owner": "proof-owner",
            "expected_benefit": "later proof selection avoids unrelated reruns",
            "regression_dimension": "missing changed-claim coverage",
            "comparable_task_shape": "runtime-contract-change",
            "requires_later_observation": True,
            "minimum_comparable_observations": 2,
            "report_sink": "#2648",
        },
        "implementation_proof": {
            "status": "passed",
            "evidence_refs": ["tests/test_proof_selector.py"],
            "fully_establishes_claim": False,
        },
        "later_observations": [],
    }
    candidate.update(overrides)
    return candidate


def _observation(
    observation_id: str,
    *,
    friction_recurred: bool,
    benefit_effect: str,
    shifted_cost: str = "none",
    **overrides: object,
) -> dict[str, object]:
    observation: dict[str, object] = {
        "observation_id": observation_id,
        "candidate_id": "candidate-proof-reentry",
        "task_shape": "runtime-contract-change",
        "comparable": True,
        "friction_recurred": friction_recurred,
        "benefit_effect": benefit_effect,
        "shifted_cost": shifted_cost,
        "evidence_refs": [f"proof:{observation_id}"],
        "owner": "proof-owner",
    }
    observation.update(overrides)
    return observation


def _validate(payload: dict[str, object]) -> None:
    schema = json.loads(
        Path("src/agentic_workspace/contracts/schemas/repo_improvement_effectiveness.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)


def test_deterministic_improvement_closes_on_present_proof_without_evaluation_ceremony() -> None:
    claim = dict(_candidate()["improvement_claim"])
    claim["requires_later_observation"] = False
    proof = dict(_candidate()["implementation_proof"])
    proof["fully_establishes_claim"] = True

    result = compile_repo_improvement_effectiveness(candidate=_candidate(improvement_claim=claim, implementation_proof=proof))

    _validate(result)
    assert result["classification"] == "resolved-deterministically"
    assert result["evaluation_definition"] == {}
    assert result["signal_state"] == "mitigated"
    assert result["recurring_context_required"] is False
    assert result["ordinary_projection"] == {}
    assert result["residue"]["signal"] == "retire"


def test_longitudinal_claim_reuses_one_owner_bound_evaluation_definition(tmp_path: Path) -> None:
    result = compile_repo_improvement_effectiveness(candidate=_candidate())
    definition = result["evaluation_definition"]

    _validate(result)
    assert result["classification"] == "awaiting-later-observation"
    assert definition["subject"]["candidate_id"] == "candidate-proof-reentry"
    assert definition["collection_policy"]["minimum_observations"] == 2
    assert definition["collection_policy"]["privacy_safe_context_required"] is True
    assert {item["id"] for item in definition["criteria"]} == {"recurrence", "operability-benefit", "shifted-cost"}
    registration = register_repo_improvement_evaluation(target_root=tmp_path, effectiveness=result)
    assert registration["outcome"] == "registered"
    stored = json.loads((tmp_path / ".agentic-workspace/evaluations.json").read_text(encoding="utf-8"))
    assert len(stored["evaluations"]) == 1
    assert stored["evaluations"][0]["id"] == definition["id"]


def test_two_comparable_nonrecurrences_resolve_and_retire_all_active_pressure() -> None:
    observations = [
        _observation("later-1", friction_recurred=False, benefit_effect="reduced"),
        _observation("later-2", friction_recurred=False, benefit_effect="resolved"),
    ]
    result = compile_repo_improvement_effectiveness(
        candidate=_candidate(
            later_observations=observations,
            counterexample_rationale="Broad proof used to rerun unrelated Planning tests.",
            expensive_to_rediscover=True,
        )
    )

    assert result["classification"] == "resolved"
    assert result["identity"]["candidate_id"] == "candidate-proof-reentry"
    assert result["identity"]["action_id"] == "repo-improvement-action:aaaaaaaaaaaaaaaa"
    assert result["identity"]["execution_id"] == "repo-improvement-execution:bbbbbbbbbbbbbbbb"
    assert result["identity"]["later_observation_refs"] == ["proof:later-1", "proof:later-2"]
    assert result["signal_state"] == "mitigated"
    assert result["evaluation_definition"] == {}
    assert result["ordinary_projection"] == {}
    assert result["residue"] == {
        "signal": "retire",
        "planning": "close-or-shrink",
        "review": "resolve",
        "memory": "retire",
        "durable_rationale": "Broad proof used to rerun unrelated Planning tests.",
    }

    from agentic_workspace.workspace_runtime_core import _improvement_pressure_payload

    pressure = _improvement_pressure_payload(
        {
            "improvement_signal_candidates": [
                _candidate(
                    later_observations=observations,
                    counterexample_rationale="Broad proof used to rerun unrelated Planning tests.",
                    expensive_to_rediscover=True,
                )
            ]
        }
    )
    assert pressure["status"] == "quiet"
    assert pressure["active_record_refs"] == []
    assert pressure["posture_obligations"] == []
    assert pressure["records"][0]["state"] == "mitigated"


def test_single_nonrecurrence_is_inconclusive_not_causal_success() -> None:
    result = compile_repo_improvement_effectiveness(
        candidate=_candidate(later_observations=[_observation("later-1", friction_recurred=False, benefit_effect="resolved")])
    )

    assert result["classification"] == "inconclusive-comparison"
    assert result["signal_state"] == "active"
    assert result["recurring_context_required"] is True


def test_reduced_but_recurring_friction_is_partial_and_returns_to_same_owner() -> None:
    result = compile_repo_improvement_effectiveness(
        candidate=_candidate(later_observations=[_observation("later-1", friction_recurred=True, benefit_effect="reduced")])
    )

    assert result["classification"] == "partial-improvement"
    assert result["owner"] == "proof-owner"
    assert result["identity"]["candidate_id"] == "candidate-proof-reentry"
    assert result["human_visibility"] == "compact-owner-visible"


def test_recurrence_without_benefit_is_failed_improvement_not_duplicate_work() -> None:
    result = compile_repo_improvement_effectiveness(
        candidate=_candidate(later_observations=[_observation("later-1", friction_recurred=True, benefit_effect="unchanged")])
    )

    assert result["classification"] == "recurrence-failed-improvement"
    assert result["disposition"] == "refine-promote-or-revert"
    assert "originating source owner" in result["next_action"]
    assert result["ordinary_projection"]["owner"] == "proof-owner"


def test_local_improvement_global_regression_is_owner_visible() -> None:
    result = compile_repo_improvement_effectiveness(
        candidate=_candidate(
            later_observations=[_observation("later-1", friction_recurred=False, benefit_effect="resolved", shifted_cost="material")]
        )
    )

    assert result["classification"] == "local-improvement-global-regression"
    assert result["human_visibility"] == "compact-owner-visible"
    assert result["signal_state"] == "active"


def test_misclassification_and_stronger_owner_obsolescence_retire_original_pressure() -> None:
    misclassified = compile_repo_improvement_effectiveness(
        candidate=_candidate(
            later_observations=[_observation("later-1", friction_recurred=False, benefit_effect="unchanged", misclassified=True)]
        )
    )
    obsolete = compile_repo_improvement_effectiveness(
        candidate=_candidate(stronger_owner={"status": "absorbed", "owner_ref": "docs/proof-contract.md"})
    )

    assert misclassified["classification"] == "misclassified"
    assert misclassified["signal_state"] == "obsolete"
    assert misclassified["residue"]["memory"] == "retire"
    assert obsolete["classification"] == "obsolete-stronger-owner"
    assert obsolete["ordinary_projection"] == {}
    assert obsolete["recurring_context_required"] is False


def test_raw_transcript_observation_is_rejected_and_not_retained() -> None:
    raw = _observation("later-raw", friction_recurred=False, benefit_effect="resolved", transcript="secret raw transcript")
    result = compile_repo_improvement_effectiveness(candidate=_candidate(later_observations=[raw]))

    assert result["rejected_raw_context_observation_count"] == 1
    assert result["comparable_observation_count"] == 0
    assert "secret raw transcript" not in json.dumps(result)


def test_real_dogfood_sequence_records_operability_retirement_not_only_test_success() -> None:
    evidence = json.loads(Path("docs/reviews/repo-improvement-effectiveness-dogfood-2652.json").read_text(encoding="utf-8"))
    candidate = {
        "id": evidence["candidate_id"],
        "suspected_owner": evidence["improvement"]["owner"],
        "evidence_refs": [evidence["signal"]["evidence_ref"]],
        "improvement_claim": {
            "source_owner": evidence["improvement"]["owner"],
            "expected_benefit": evidence["improvement"]["expected_benefit"],
            "regression_dimension": evidence["improvement"]["regression_dimension"],
            "comparable_task_shape": evidence["comparable_task_shape"],
            "requires_later_observation": True,
        },
        "implementation_proof": {
            "status": "passed",
            "evidence_refs": evidence["improvement"]["implementation_proof"],
        },
        "later_observations": [{**item, "comparable": True} for item in evidence["later_observations"]],
        "counterexample_rationale": evidence["conclusion"]["retirement"],
        "expensive_to_rediscover": True,
    }
    conclusion = compile_repo_improvement_effectiveness(candidate=candidate)

    assert evidence["status"] == "concluded"
    assert evidence["signal"]["cost"].startswith("171.6 seconds")
    assert len(evidence["later_observations"]) == 2
    assert all(item["friction_recurred"] is False for item in evidence["later_observations"])
    assert evidence["conclusion"]["attributable_unrelated_planning_runs_before"] == 2
    assert evidence["conclusion"]["attributable_unrelated_planning_runs_after"] == 0
    assert evidence["conclusion"]["claim_coverage_preserved"] is True
    assert evidence["conclusion"]["recurring_context_required"] is False
    assert conclusion["classification"] == "resolved"
    assert conclusion["signal_state"] == "mitigated"
    assert conclusion["recurring_context_required"] is False
    assert conclusion["ordinary_projection"] == {}
