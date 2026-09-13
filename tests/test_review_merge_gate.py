from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

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
        "node_id": f"node-{identifier}",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "_source_unedited": True,
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
        ("NONE", REVIEWER_APP),
        ("MEMBER", None),
        ("COLLABORATOR", "some-other-app"),
        ("NONE", None),
    ],
)
def test_marker_requires_configured_app_independent_of_login_and_association(association: str, app_slug: str | None) -> None:
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

    assert decision.status == ("merge-ready" if app_slug == REVIEWER_APP else "review-missing")
    assert decision.conclusion == ("success" if app_slug == REVIEWER_APP else "failure")


@pytest.mark.parametrize("app_slug", [None, "some-other-app"])
@pytest.mark.parametrize("admitted", ["blocked", "merge-ready"])
def test_copied_marker_cannot_supersede_admitted_reviewer_decision(app_slug, admitted) -> None:
    decision = _module().review_gate_decision(
        pr_number=2501,
        head_sha=HEAD_A,
        comments=[
            _comment(decision=admitted, identifier=1, login="rickardvh", app_slug=REVIEWER_APP),
            _comment(decision="merge-ready" if admitted == "blocked" else "blocked", identifier=2, login="rickardvh", app_slug=app_slug),
        ],
    )

    assert decision.status == ("review-blocked" if admitted == "blocked" else "merge-ready")
    assert decision.conclusion == ("failure" if admitted == "blocked" else "success")
    assert decision.review_url == "https://example.test/review/1"


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
    assert "pull_request_review:" not in workflow
    assert "scripts/github/review_merge_gate.py" in workflow
    assert "ref: ${{ vars.REVIEW_GATE_COMMIT }}" in workflow
    assert "472e94b85d9ec1a8d5e0da0e63d13ee1621eb558" not in workflow
    assert "persist-credentials: false" in workflow
    assert "ref: ${{ github.event.repository.default_branch }}" not in workflow
    assert "ref: ${{ github.event.pull_request.head" not in workflow
    assert '"context": "Review approval"' in ruleset
    publisher = yaml.load(workflow, Loader=yaml.BaseLoader)
    assert publisher["concurrency"]["cancel-in-progress"] == "false"
    assert set(publisher["on"]) == {"workflow_run", "issue_comment"}
    assert publisher["on"]["workflow_run"]["workflows"] == ["CI", "Review event"]
    job = publisher["jobs"]["review-authority"]
    assert job["permissions"] == {"contents": "read"}
    assert job["environment"] == "review-publisher"
    assert job["steps"][0]["env"] == {"REVIEW_GATE_COMMIT": "${{ vars.REVIEW_GATE_COMMIT }}"}
    assert "^[0-9a-f]{40}$" in job["steps"][0]["run"]
    token = next(step for step in job["steps"] if step.get("id") == "publisher-token")
    assert token["uses"] == "actions/create-github-app-token@fee1f7d63c2ff003460e3d139729b119787bc349"
    assert token["with"] == {
        "app-id": "${{ vars.REVIEW_PUBLISHER_APP_ID }}",
        "private-key": "${{ secrets.REVIEW_PUBLISHER_PRIVATE_KEY }}",
        "owner": "${{ github.repository_owner }}",
        "repositories": "${{ github.event.repository.name }}",
        "permission-checks": "write",
        "permission-contents": "read",
        "permission-issues": "read",
        "permission-pull-requests": "read",
    }
    assert job["steps"][-1]["env"]["GH_TOKEN"] == "${{ steps.publisher-token.outputs.token }}"
    relay = yaml.load((WORKFLOW.parent / "review-event.yml").read_text(), Loader=yaml.BaseLoader)
    assert relay["name"] == "Review event"
    assert relay["on"] == {"pull_request_review": {"types": ["submitted", "edited", "dismissed"]}}
    assert relay["permissions"] == {}
    assert set(relay["jobs"]) == {"notify"}
    assert set(relay["jobs"]["notify"]) == {"runs-on", "steps"}
    assert relay["jobs"]["notify"]["steps"] == [
        {"name": "Notify trusted publisher", "run": "echo 'Review state changed; the trusted publisher must reobserve it.'"}
    ]


def test_required_review_source_cannot_default_to_candidate_actions():
    spec = importlib.util.spec_from_file_location("render_review_ruleset", ROOT / "scripts/github/render_review_ruleset.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    template = json.loads(RULESET.read_text())
    app = {"id": 123456, "slug": "dedicated-review-fixture", "permissions": {"checks": "write", "statuses": "write"}}
    rendered = module.render_ruleset(template, app)
    checks = next(rule for rule in rendered["rules"] if rule["type"] == "required_status_checks")["parameters"]["required_status_checks"]
    assert next(check for check in checks if check["context"] == "Review approval") == {
        "context": "Review approval",
        "integration_id": 123456,
    }
    assert "REVIEW_PUBLISHER_APP_ID" in json.dumps(template)
    for invalid in (
        {},
        {**app, "id": None},
        {**app, "id": "123456"},
        {**app, "id": 0},
        {**app, "id": 15368},
        {**app, "slug": "github-actions"},
        {**app, "permissions": {"checks": "read"}},
        {**app, "permissions": {"checks": "write"}},
        {**app, "permissions": {"checks": "write", "statuses": "read"}},
    ):
        with pytest.raises(ValueError):
            module.render_ruleset(template, invalid)
    # An accidentally restored name-only rule must not be deployable by this path.
    for rule in template["rules"]:
        if rule["type"] == "required_status_checks":
            for check in rule["parameters"]["required_status_checks"]:
                check.pop("integration_id", None)
    with pytest.raises(ValueError):
        module.render_ruleset(template, app)


@pytest.mark.parametrize("decision,expected", [("merge-ready", "success"), ("blocked", "failure"), (None, "failure")])
def test_workflow_run_resolves_its_pull_request(tmp_path, monkeypatch, decision, expected) -> None:
    # The relay supplies only a PR identity. Its old head, conclusion and output
    # cannot grant approval: the publisher must re-read current GitHub sources.
    event = {
        "workflow_run": {
            "pull_requests": [{"number": 2501}],
            "head_sha": HEAD_B,
            "conclusion": "success",
            "outputs": {"decision": "merge-ready"},
        }
    }
    module = _module()
    assert module._pr_number(event) == 2501
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event))
    calls = []
    posted = []

    def github(args):
        calls.append(args)
        if args[-1] == "repos/owner/repo/pulls/2501":
            return {"head": {"sha": HEAD_A}, "base": {"sha": HEAD_C}}
        if "/issues/" in args[-1]:
            return [[_comment(decision=decision)]] if decision else [[]]
        return [[]]

    monkeypatch.setattr(module, "_gh_json", github)
    monkeypatch.setattr(module, "_post_check", lambda **kwargs: posted.append(kwargs))
    monkeypatch.setattr(module, "_watermark_check", lambda *args: ({}, {"after": "2025-01-01T00:00:00Z", "latest": None}))
    monkeypatch.setattr(module, "_save_watermark", lambda *args: None)
    monkeypatch.setattr(
        module,
        "_gh_payload",
        lambda *args: {"data": {"nodes": [{"id": "node-1", "body": _comment(decision=decision)["body"], "lastEditedAt": None}]}},
    )
    assert module.main(["--event", str(event_path), "--repository", "owner/repo", "--publisher-app-id", "123456"]) == 0
    assert posted[0]["decision"].conclusion == "failure"
    assert posted[-1]["head_sha"] == HEAD_A
    assert posted[-1]["decision"].conclusion == expected
    assert len(calls) == 5


def test_review_records_preserve_dismissed_formal_review_tombstones(monkeypatch) -> None:
    module = _module()
    calls: list[list[str]] = []
    conversation = _comment(decision="blocked", identifier=1)
    formal = {**_comment(decision="merge-ready", identifier=2), "state": "COMMENTED"}
    dismissed = {**_comment(decision="merge-ready", identifier=3), "state": "DISMISSED"}

    def fake_gh_json(args: list[str]) -> list[list[dict[str, object]]]:
        calls.append(args)
        return [[conversation]] if "/issues/" in args[-1] else [[formal, dismissed]]

    monkeypatch.setattr(module, "_gh_json", fake_gh_json)
    monkeypatch.setattr(
        module,
        "_gh_payload",
        lambda *args: {
            "data": {
                "nodes": [{"id": row["node_id"], "body": row["body"], "lastEditedAt": None} for row in (conversation, formal, dismissed)]
            }
        },
    )

    records = module._review_records(repository="owner/repo", pr_number=2501)

    assert [record["id"] for record in records] == [1, 2, 3]
    assert module.review_gate_decision(pr_number=2501, head_sha=HEAD_A, comments=records).conclusion == "failure"
    assert "/issues/2501/comments" in calls[0][-1]
    assert "/pulls/2501/reviews" in calls[1][-1]


@pytest.mark.parametrize("last_edit", ["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"])
def test_edited_terminal_body_cannot_be_admitted_even_before_first_observation(monkeypatch, last_edit):
    module = _module()
    comment = _comment(decision="merge-ready")
    monkeypatch.setattr(module, "_gh_json", lambda args: [[comment]] if "/issues/" in args[-1] else [[]])
    monkeypatch.setattr(
        module,
        "_gh_payload",
        lambda *args: {"data": {"nodes": [{"id": comment["node_id"], "body": comment["body"], "lastEditedAt": last_edit}]}},
    )
    records = module._review_records(repository="owner/repo", pr_number=2501)
    assert module.review_gate_decision(pr_number=2501, head_sha=HEAD_A, comments=records).conclusion == "failure"


@pytest.mark.parametrize("admitted", ["blocked", "merge-ready"])
@pytest.mark.parametrize("mutation", ["delete", "edit", "dismiss-before-observation"])
def test_publisher_watermark_survives_fresh_process_source_tampering(tmp_path, monkeypatch, admitted, mutation):
    # In-memory GitHub transport; each invocation loads a fresh publisher module.
    # Exercise real serialization, App/anchor validation, PATCH/readback and
    # exact-head publication ordering across independent evaluations.
    app_id = 123456
    anchor = "d" * 40
    state = {
        "kind": "review-decision-watermark/v1",
        "repository": "owner/repo",
        "pr_number": 2501,
        "anchor": anchor,
        "after": "2025-01-01T00:00:00Z",
        "latest": None,
    }
    check = {
        "id": 99,
        "name": "Review decision watermark / PR 2501",
        "head_sha": anchor,
        "app": {"id": app_id},
        "output": {"text": json.dumps(state)},
    }
    older = _comment(decision="merge-ready", identifier=1)
    newest = _comment(decision=admitted, identifier=2)
    records = [older] if mutation == "dismiss-before-observation" else [older, newest]
    edits = set()
    posted = []
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"issue": {"number": 2501, "pull_request": {"url": "pr"}}}))
    writes = []
    fail_write = False
    corrupt_readback = False
    current_head = HEAD_A

    def github(args):
        endpoint = args[-1]
        if "/commits/" in endpoint:
            return [{"check_runs": [deepcopy(check), {**deepcopy(check), "app": {"id": 15368}}]}]
        if endpoint.endswith("check-runs/99"):
            if corrupt_readback:
                return {**deepcopy(check), "output": {"text": "{}"}}
            return deepcopy(check)
        if "/issues/" in endpoint:
            return [deepcopy([row for row in records if "state" not in row])]
        if endpoint.endswith("/reviews?per_page=100"):
            return [deepcopy([row for row in records if "state" in row])]
        return {"head": {"sha": current_head}, "base": {"sha": HEAD_C}}

    def payload(method, endpoint, value):
        if endpoint == "graphql":
            return {
                "data": {
                    "nodes": [
                        {"id": row["node_id"], "body": row["body"], "lastEditedAt": "2026-01-02T00:00:00Z" if row["id"] in edits else None}
                        for row in records
                    ]
                }
            }
        assert method == "PATCH" and endpoint.endswith("check-runs/99")
        if fail_write:
            raise RuntimeError("publisher state publication interrupted")
        check["output"] = deepcopy(value["output"])
        writes.append(json.loads(check["output"]["text"]))
        return deepcopy(check)

    def run():
        module = _module()
        monkeypatch.setattr(module, "_git", lambda *args, **kwargs: subprocess.CompletedProcess([], 0, stdout=anchor))
        monkeypatch.setattr(module, "_gh_json", github)
        monkeypatch.setattr(module, "_gh_payload", payload)
        monkeypatch.setattr(module, "_post_check", lambda **kwargs: posted.append(kwargs["decision"].conclusion))
        assert module.main(["--event", str(event_path), "--repository", "owner/repo", "--publisher-app-id", str(app_id)]) == 0
        return posted[-1]

    assert run() == ("success" if mutation == "dismiss-before-observation" or admitted == "merge-ready" else "failure")
    if mutation == "delete":
        records.pop()
    elif mutation == "dismiss-before-observation":
        # B is created and dismissed between evaluations. Only GitHub's retained
        # DISMISSED record is available; the relay carries no review snapshot.
        assert writes[-1]["latest"]["order"][1] == 1
        records.append({**newest, "state": "DISMISSED"})
    else:
        records[-1] = _comment(decision="merge-ready", identifier=2)
        edits.add(2)
    assert run() == "failure"
    assert writes[-1]["latest"]["order"][1] == 2
    assert writes[-1]["latest"]["tainted"] is True
    assert run() == "failure"  # a later unrelated wake-up cannot revive older approval
    current_head = HEAD_B
    records.append(_comment(decision="merge-ready", identifier=3, head=HEAD_B))
    assert run() == "success"
    assert writes[-1]["latest"]["order"][1] == 3
    assert writes[-1]["latest"]["tainted"] is False
    assert posted[::2] == ["failure"] * 4
    fail_write = True
    with pytest.raises(RuntimeError, match="publication interrupted"):
        run()
    assert posted[-1] == "failure"  # interruption cannot leave the prior success current
    fail_write = False
    corrupt_readback = True
    with pytest.raises(ValueError, match="readback mismatch"):
        run()
    assert posted[-1] == "failure"


def test_missing_or_lost_watermark_requires_a_fresh_reviewer_decision():
    module = _module()
    state = {"after": "2026-01-01T00:00:00Z", "latest": None}
    old = _comment(decision="merge-ready")
    state = module.advance_watermark(state, [old], {})
    assert state["latest"]["tainted"]
    newer = {**_comment(decision="merge-ready", identifier=2), "created_at": "2026-01-02T00:00:00Z"}
    state = module.advance_watermark(state, [old, newer], {})
    assert not state["latest"]["tainted"]
    deleted = {**_comment(decision="blocked", identifier=3), "created_at": "2026-01-03T00:00:00Z"}
    state = module.advance_watermark(state, [old, newer], {"action": "deleted", "comment": deleted})
    assert state["latest"]["order"][1] == 3 and state["latest"]["tainted"]


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
