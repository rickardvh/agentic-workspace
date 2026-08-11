from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "github" / "review_merge_gate.py"
WORKFLOW = ROOT / ".github" / "workflows" / "exact-head-review.yml"
RULESET = ROOT / ".github" / "rulesets" / "master-support-bearing.json"
HEAD_A = "a" * 40
HEAD_B = "b" * 40
HEAD_C = "c" * 40


def _module():
    spec = importlib.util.spec_from_file_location("review_merge_gate", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _comment(
    *,
    decision: str,
    head: str = HEAD_A,
    association: str = "OWNER",
    identifier: int = 1,
    pr_number: int = 2501,
) -> dict[str, object]:
    return {
        "id": identifier,
        "author_association": association,
        "body": (
            f"decision: {decision}\n<!-- aw-chatgpt-review pr={pr_number} head={head} policy=pr-review-recheck-v1 decision={decision} -->"
        ),
        "html_url": f"https://example.test/review/{identifier}",
    }


@pytest.mark.parametrize(
    ("pr_number", "head_sha", "comments", "expected_status"),
    [
        pytest.param(2497, HEAD_A, [_comment(decision="blocked", pr_number=2497)], "review-blocked", id="2497-blocked-head"),
        pytest.param(
            2498,
            HEAD_B,
            [_comment(decision="blocked", head=HEAD_A, pr_number=2498)],
            "review-blocked",
            id="2498-stale-head",
        ),
        pytest.param(
            2499,
            HEAD_B,
            [_comment(decision="blocked", head=HEAD_A, pr_number=2499)],
            "review-blocked",
            id="2499-stale-head",
        ),
        pytest.param(
            2500,
            HEAD_B,
            [_comment(decision="blocked", head=HEAD_A, pr_number=2500)],
            "review-blocked",
            id="2500-stale-head",
        ),
        pytest.param(2501, HEAD_A, [], "review-missing", id="2501-generated-release-without-review"),
    ],
)
def test_incident_replays_fail_closed(pr_number: int, head_sha: str, comments: list[dict[str, object]], expected_status: str) -> None:
    decision = _module().review_gate_decision(pr_number=pr_number, head_sha=head_sha, comments=comments)

    assert decision.status == expected_status
    assert decision.conclusion == "failure"


def test_prior_merge_ready_without_ancestry_proof_fails_closed() -> None:
    decision = _module().review_gate_decision(
        pr_number=2501,
        head_sha=HEAD_B,
        comments=[_comment(decision="merge-ready", head=HEAD_A)],
    )

    assert decision.status == "review-ancestry-unverified"
    assert decision.conclusion == "failure"
    assert HEAD_A in decision.summary


def test_latest_current_head_merge_ready_decision_admits_merge() -> None:
    decision = _module().review_gate_decision(
        pr_number=2501,
        head_sha=HEAD_A,
        comments=[_comment(decision="blocked", identifier=1), _comment(decision="merge-ready", identifier=2)],
    )

    assert decision.status == "merge-ready"
    assert decision.conclusion == "success"
    assert decision.review_url == "https://example.test/review/2"


def test_prior_merge_ready_decision_admits_descendant_head() -> None:
    decision = _module().review_gate_decision(
        pr_number=2501,
        head_sha=HEAD_B,
        comments=[_comment(decision="merge-ready", head=HEAD_A)],
        is_ancestor=lambda reviewed, current: (reviewed, current) == (HEAD_A, HEAD_B),
    )

    assert decision.status == "merge-ready-carried-forward"
    assert decision.conclusion == "success"
    assert HEAD_A in decision.summary
    assert HEAD_B in decision.summary


def test_prior_merge_ready_decision_rejects_diverged_head() -> None:
    decision = _module().review_gate_decision(
        pr_number=2501,
        head_sha=HEAD_B,
        comments=[_comment(decision="merge-ready", head=HEAD_A)],
        is_ancestor=lambda _reviewed, _current: False,
    )

    assert decision.status == "review-diverged-head"
    assert decision.conclusion == "failure"


def test_newer_blocker_supersedes_prior_merge_ready_decision() -> None:
    decision = _module().review_gate_decision(
        pr_number=2501,
        head_sha=HEAD_C,
        comments=[
            _comment(decision="merge-ready", head=HEAD_A, identifier=1),
            _comment(decision="blocked", head=HEAD_B, identifier=2),
        ],
        is_ancestor=lambda _reviewed, _current: True,
    )

    assert decision.status == "review-blocked"
    assert decision.conclusion == "failure"
    assert decision.review_url == "https://example.test/review/2"


def test_untrusted_marker_cannot_authorize_merge() -> None:
    decision = _module().review_gate_decision(
        pr_number=2501, head_sha=HEAD_A, comments=[_comment(decision="merge-ready", association="NONE")]
    )

    assert decision.status == "review-missing"
    assert decision.conclusion == "failure"


def test_server_side_workflow_and_ruleset_consume_the_same_required_check() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    ruleset = RULESET.read_text(encoding="utf-8")

    assert "workflow_run:" in workflow
    assert "pull_request_target:" not in workflow
    assert "issue_comment:" in workflow
    assert "scripts/github/review_merge_gate.py" in workflow
    assert '"context": "Review approval"' in ruleset


def test_workflow_run_resolves_its_pull_request() -> None:
    event = {"workflow_run": {"pull_requests": [{"number": 2501}]}}

    assert _module()._pr_number(event) == 2501


def test_check_run_posts_the_review_link_at_the_supported_top_level(monkeypatch) -> None:
    module = _module()
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    module._post_check(
        repository="owner/repo",
        head_sha=HEAD_A,
        decision=module.GateDecision(
            status="merge-ready",
            conclusion="success",
            title="approved",
            summary="approved current head",
            review_url="https://example.test/review/2",
        ),
    )

    payload = json.loads(calls[0][1]["input"])
    assert payload["details_url"] == "https://example.test/review/2"
    assert "details_url" not in payload["output"]
