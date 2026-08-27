from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation" / "open-issues-closure-2026-08-27.json"


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
    assert "Merge and merge-ready approval remain external human authority" in str(payload["claim_boundary"])
