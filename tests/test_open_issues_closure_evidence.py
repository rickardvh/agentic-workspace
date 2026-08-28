from __future__ import annotations

import json
from pathlib import Path

from agentic_workspace.reconciliation import compile_reconciliation

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation" / "open-issues-closure-2026-08-27.json"
CLOSURE_REVIEW_PATH = REPO_ROOT / "docs" / "reviews" / "open-issues-closure-2026-08-27.md"
DOGFOOD_DISPOSITION_PATH = (
    REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation" / "open-issues-dogfood-disposition-2026-08-28.json"
)


def _evidence() -> dict[str, object]:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def test_original_open_issue_inventory_has_exactly_one_closure_route() -> None:
    payload = _evidence()
    scope = payload["scope"]
    assert isinstance(scope, dict)
    included = set(scope["included_issues"])
    excluded = set(scope["excluded_later_issues"])
    assert included == {2345, 2562, 2590, 2721, 2725, 2729, 2752, 2754, 2762, 2763, 2765}
    assert included.isdisjoint(excluded)

    routes = payload["closure_routes"]
    assert isinstance(routes, list)
    routed = [issue for route in routes if isinstance(route, dict) for issue in route["issues"]]
    assert set(routed) == included
    assert len(routed) == len(set(routed))


def test_parent_closure_replay_names_every_required_integrated_capability() -> None:
    payload = _evidence()
    replay = payload["integrated_replay"]
    assert isinstance(replay, list)
    capabilities = {row["capability"] for row in replay if isinstance(row, dict)}
    assert capabilities == {
        "direct-bounded-work-and-compact-resume",
        "bounded-external-issue-filing-without-planning-custody",
        "explicit-human-correction",
        "real-nonlocal-delegation-and-return-admission",
        "proportional-proof-admission-publication-and-freshness",
        "complete-pr-review-intake-with-provider-boundary",
        "post-merge-planning-reconciliation",
        "future-relevant-dogfooding-residue-disposition",
        "logical-session-chronology-is-diagnostic-only",
    }
    assert all(row["status"] not in {"missing", "not-checked", "unevaluated"} for row in replay if isinstance(row, dict))


def test_issue_2725_is_repository_memory_not_product_review_authority() -> None:
    payload = _evidence()
    routes = payload["closure_routes"]
    assert isinstance(routes, list)
    route = next(row for row in routes if isinstance(row, dict) and row["issues"] == [2725])
    assert route == {
        "issues": [2725],
        "pull_request": 2776,
        "group": "repository-memory-review-anti-trap",
        "disposition": "repository-local-operational-guidance",
        "portable_aw_contract": False,
    }

    closure_review = CLOSURE_REVIEW_PATH.read_text(encoding="utf-8")
    assert "three product-semantic layers, one repository-local Memory correction" in closure_review
    assert "| Repository-local review anti-trap | #2776 | #2725 |" in closure_review
    assert "| Verifier authority | #2776 | #2725 |" not in closure_review


def test_checked_in_closure_evidence_refs_exist_and_supported_host_trace_is_bounded() -> None:
    payload = _evidence()
    rows = [
        *payload["contract_replay"],
        *payload["integrated_replay"],
    ]
    for row in rows:
        if not isinstance(row, dict):
            continue
        ref = str(row["evidence"])
        if ref.startswith(("tests/", "packages/", "scripts/", "tools/")):
            assert (REPO_ROOT / ref).exists(), ref

    dogfood = json.loads(
        (REPO_ROOT / "tools/model-cli-harness/external-agent-evaluation/nonlocal-delegation-dogfood-2026-08-27.json").read_text(
            encoding="utf-8"
        )
    )
    assert dogfood["ordinary_input"]["explicit_delegation_wording"] is False
    assert dogfood["before_after"]["after"]["real_supported_host"] is True
    assert dogfood["assignment"]["worker_proof_authority"] is False
    assert dogfood["assignment"]["worker_completion_authority"] is False
    assert dogfood["return"]["orchestrator_continuation"] == "reconcile-next-operating-decision"


def test_closure_review_contains_a_subtraction_disposition_for_each_peer_surface() -> None:
    payload = _evidence()
    dispositions = payload["subtraction_and_disposition"]
    assert isinstance(dispositions, list)
    assert len(dispositions) >= 9
    assert all(row.get("surface") and row.get("disposition") for row in dispositions if isinstance(row, dict))
    residue = payload["planning_residue"]
    assert isinstance(residue, dict)
    assert residue["status"] == "integration-proposed"
    assert (REPO_ROOT / str(residue["proposal"])).is_file()
    assert "Merge and review decisions remain governed by repository policy" in str(payload["claim_boundary"])


def test_issue_2724_ordinary_prompt_executes_assignment_without_worker_claim_authority() -> None:
    payload = json.loads(DOGFOOD_DISPOSITION_PATH.read_text(encoding="utf-8"))
    episode = payload["ordinary_assignment_episode"]
    assert "delegate" not in episode["human_intent"].lower()
    assert episode["explicit_delegation_wording"] is False
    assert episode["extra_conversational_permission"] is False
    assert episode["action"] == "dispatch-assigned-target"
    assert episode["transport"] in {"internal", "cli"}
    assert episode["return_status"] == "awaiting-admission"
    assert episode["admission_status"] == "admitted"
    assert episode["integration_status"] == "integrated"
    assert episode["closeout_status"] == "closed"
    assert episode["worker_proof_authority"] is False
    assert episode["worker_completion_authority"] is False
    assert episode["host_proof_result"] == "passed"
    assert all(len(episode[field]) == 64 for field in ("return_sha256", "admission_sha256", "closeout_sha256"))

    counterexample = payload["current_target_counterexample"]
    assert counterexample["selected_target_relation"] == "current-target"
    assert counterexample["assignment_materialized"] is False
    assert counterexample["assignment_residue"] == []


def test_issue_2752_pr_2746_signal_reconciles_to_stronger_owner_without_duplicate_memory() -> None:
    payload = json.loads(DOGFOOD_DISPOSITION_PATH.read_text(encoding="utf-8"))
    replay = payload["pr_2746_future_context_replay"]
    signal = replay["signal"]
    result = compile_reconciliation(
        {
            "result": {"status": "succeeded"},
            "intent": {"status": "satisfied"},
            "proof": {"status": "passed"},
            "future_context_capture": {"status": replay["capture_input_status"]},
            "future_context_signals": [signal],
        }
    )
    reconciliation = result["future_context_reconciliation"]
    disposition = reconciliation["dispositions"][0]

    assert signal["authority_state"] == "owner-admitted"
    assert signal["disposition"]["owner"] == "proof/code/test"
    assert reconciliation["status"] == replay["expected_reconciliation"]["status"]
    assert reconciliation["none_found_allowed"] is False
    assert reconciliation["capture_input_status"] == "not_evaluated"
    assert reconciliation["custody_transfer_safe"] is True
    assert disposition["outcome"] == "already-absorbed"
    assert disposition["duplicate_memory_record_required"] is False
    assert replay["human_supplied_memory_destination"] is False
