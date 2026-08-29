from __future__ import annotations

import importlib.util
import json
import subprocess
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
REVIEWER_APP = "chatgpt-codex-connector"


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
    login: str = "independent-reviewer",
    app_slug: str | None = REVIEWER_APP,
) -> dict[str, object]:
    comment: dict[str, object] = {
        "id": identifier,
        "author_association": association,
        "user": {"login": login},
        "body": (
            f"decision: {decision}\n<!-- aw-chatgpt-review pr={pr_number} head={head} policy=pr-review-recheck-v1 decision={decision} -->"
        ),
        "html_url": f"https://example.test/review/{identifier}",
    }
    if app_slug is not None:
        comment["performed_via_github_app"] = {"slug": app_slug}
    return comment


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def _review_history_repo(tmp_path: Path) -> tuple[Path, str]:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "clone", str(remote), str(repo)], check=True, capture_output=True)
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.test")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "base.txt")
    _git(repo, "commit", "-m", "base")
    _git(repo, "branch", "-M", "master")
    _git(repo, "push", "origin", "master")
    _git(repo, "switch", "-c", "pr")
    (repo / "pr.txt").write_text("reviewed\n", encoding="utf-8")
    _git(repo, "add", "pr.txt")
    _git(repo, "commit", "-m", "reviewed")
    return repo, _git(repo, "rev-parse", "HEAD")


def _publish_pull_ref(repo: Path) -> str:
    head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "push", "--force", "origin", f"{head}:refs/pull/2501/head")
    return head


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


@pytest.mark.parametrize(
    ("association", "app_slug"),
    [
        ("OWNER", REVIEWER_APP),
        ("MEMBER", None),
        ("COLLABORATOR", "some-other-app"),
        ("NONE", None),
    ],
)
def test_exact_marker_authority_does_not_depend_on_transport_provenance(association: str, app_slug: str | None) -> None:
    decision = _module().review_gate_decision(
        pr_number=2501,
        head_sha=HEAD_A,
        comments=[
            _comment(
                decision="merge-ready",
                association=association,
                login="implementation-owner",
                app_slug=app_slug,
            )
        ],
    )

    assert decision.status == "merge-ready"
    assert decision.conclusion == "success"


def test_latest_well_formed_marker_wins_regardless_of_transport_provenance() -> None:
    decision = _module().review_gate_decision(
        pr_number=2501,
        head_sha=HEAD_A,
        comments=[
            _comment(decision="merge-ready", identifier=1, login="rickardvh", app_slug=REVIEWER_APP),
            _comment(decision="blocked", identifier=2, login="rickardvh", app_slug="some-other-app"),
        ],
    )

    assert decision.status == "review-blocked"
    assert decision.conclusion == "failure"
    assert decision.review_url == "https://example.test/review/2"


def test_prior_merge_ready_decision_admits_patch_preserving_base_merge() -> None:
    module = _module()
    decision = _module().review_gate_decision(
        pr_number=2501,
        head_sha=HEAD_B,
        comments=[_comment(decision="merge-ready", head=HEAD_A)],
        carry_forward=lambda reviewed, current: module.CarryForwardVerdict(
            (reviewed, current) == (HEAD_A, HEAD_B), "trusted-base-merges-preserve-reviewed-patch"
        ),
    )

    assert decision.status == "merge-ready-carried-forward"
    assert decision.conclusion == "success"
    assert HEAD_A in decision.summary
    assert HEAD_B in decision.summary


@pytest.mark.parametrize(
    "reason",
    [
        "ordinary-or-octopus-commit-after-review",
        "merge-parent-is-not-trusted-base-history",
        "merge-does-not-preserve-reviewed-patch",
    ],
)
def test_prior_merge_ready_decision_rejects_untrusted_delta(reason: str) -> None:
    module = _module()
    decision = _module().review_gate_decision(
        pr_number=2501,
        head_sha=HEAD_B,
        comments=[_comment(decision="merge-ready", head=HEAD_A)],
        carry_forward=lambda _reviewed, _current: module.CarryForwardVerdict(False, reason),
    )

    assert decision.status == "review-carry-forward-rejected"
    assert decision.conclusion == "failure"
    assert reason in decision.summary


def test_newer_blocker_supersedes_prior_merge_ready_decision() -> None:
    decision = _module().review_gate_decision(
        pr_number=2501,
        head_sha=HEAD_C,
        comments=[
            _comment(decision="merge-ready", head=HEAD_A, identifier=1),
            _comment(decision="blocked", head=HEAD_B, identifier=2),
        ],
        carry_forward=lambda _reviewed, _current: _module().CarryForwardVerdict(True, "allowed"),
    )

    assert decision.status == "review-blocked"
    assert decision.conclusion == "failure"
    assert decision.review_url == "https://example.test/review/2"


def test_carry_forward_accepts_clean_trusted_base_merge(tmp_path: Path) -> None:
    module = _module()
    repo, reviewed = _review_history_repo(tmp_path)
    _git(repo, "switch", "master")
    (repo / "base.txt").write_text("base\nadvanced\n", encoding="utf-8")
    _git(repo, "commit", "-am", "advance base")
    base_head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "switch", "pr")
    _git(repo, "merge", "--no-edit", "master")
    current = _publish_pull_ref(repo)
    module.REPO_ROOT = repo

    verdict = module._trusted_base_carry_forward(pr_number=2501, reviewed_head=reviewed, current_head=current, base_head=base_head)

    assert verdict.allowed is True


def test_carry_forward_rejects_ordinary_followup_commit(tmp_path: Path) -> None:
    module = _module()
    repo, reviewed = _review_history_repo(tmp_path)
    (repo / "pr.txt").write_text("reviewed\nunreviewed\n", encoding="utf-8")
    _git(repo, "commit", "-am", "unreviewed implementation")
    current = _publish_pull_ref(repo)
    module.REPO_ROOT = repo

    verdict = module._trusted_base_carry_forward(
        pr_number=2501,
        reviewed_head=reviewed,
        current_head=current,
        base_head=_git(repo, "rev-parse", "master"),
    )

    assert verdict == module.CarryForwardVerdict(False, "ordinary-or-octopus-commit-after-review")


def test_carry_forward_rejects_unrelated_branch_merge(tmp_path: Path) -> None:
    module = _module()
    repo, reviewed = _review_history_repo(tmp_path)
    _git(repo, "switch", "-c", "unrelated")
    (repo / "unrelated.txt").write_text("unrelated\n", encoding="utf-8")
    _git(repo, "add", "unrelated.txt")
    _git(repo, "commit", "-m", "unrelated")
    _git(repo, "switch", "pr")
    _git(repo, "merge", "--no-ff", "--no-edit", "unrelated")
    current = _publish_pull_ref(repo)
    module.REPO_ROOT = repo

    verdict = module._trusted_base_carry_forward(
        pr_number=2501,
        reviewed_head=reviewed,
        current_head=current,
        base_head=_git(repo, "rev-parse", "master"),
    )

    assert verdict == module.CarryForwardVerdict(False, "merge-parent-is-not-trusted-base-history")


def test_carry_forward_rejects_conflict_resolution_that_changes_reviewed_patch(tmp_path: Path) -> None:
    module = _module()
    repo, reviewed = _review_history_repo(tmp_path)
    _git(repo, "switch", "master")
    (repo / "pr.txt").write_text("base version\n", encoding="utf-8")
    _git(repo, "add", "pr.txt")
    _git(repo, "commit", "-m", "conflicting base change")
    base_head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "switch", "pr")
    merge = subprocess.run(["git", "merge", "master"], cwd=repo, capture_output=True, text=True)
    assert merge.returncode != 0
    (repo / "pr.txt").write_text("changed during resolution\n", encoding="utf-8")
    _git(repo, "add", "pr.txt")
    _git(repo, "commit", "--no-edit")
    current = _publish_pull_ref(repo)
    module.REPO_ROOT = repo

    verdict = module._trusted_base_carry_forward(pr_number=2501, reviewed_head=reviewed, current_head=current, base_head=base_head)

    assert verdict == module.CarryForwardVerdict(False, "merge-does-not-preserve-reviewed-patch")


def test_server_side_workflow_and_ruleset_consume_the_same_required_check() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    ruleset = RULESET.read_text(encoding="utf-8")

    assert "workflow_run:" in workflow
    assert "pull_request_target:" not in workflow
    assert "issue_comment:" in workflow
    assert "pull_request_review:" in workflow
    assert "scripts/github/review_merge_gate.py" in workflow
    assert '"context": "Review approval"' in ruleset


def test_workflow_run_resolves_its_pull_request() -> None:
    event = {"workflow_run": {"pull_requests": [{"number": 2501}]}}

    assert _module()._pr_number(event) == 2501


def test_review_records_include_conversation_comments_and_active_formal_reviews(monkeypatch) -> None:
    module = _module()
    calls: list[list[str]] = []
    conversation = _comment(decision="blocked", identifier=1)
    formal = {**_comment(decision="merge-ready", identifier=2), "state": "COMMENTED"}
    dismissed = {**_comment(decision="merge-ready", identifier=3), "state": "DISMISSED"}

    def fake_gh_json(args: list[str]) -> list[list[dict[str, object]]]:
        calls.append(args)
        return [[conversation]] if "/issues/" in args[-1] else [[formal, dismissed]]

    monkeypatch.setattr(module, "_gh_json", fake_gh_json)

    records = module._review_records(repository="owner/repo", pr_number=2501)

    assert [record["id"] for record in records] == [1, 2]
    assert "/issues/2501/comments" in calls[0][-1]
    assert "/pulls/2501/reviews" in calls[1][-1]


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
