from __future__ import annotations

import json
import subprocess
from pathlib import Path

from repo_planning_bootstrap.installer import (
    apply_integration_proposal,
    archive_execplan,
    close_lane_record,
    install_bootstrap,
    planning_revision,
    planning_summary,
    propose_integration_transition,
    shape_issue_relation,
)


def _state_bytes(root: Path) -> bytes:
    return (root / ".agentic-workspace/planning/state.toml").read_bytes()


def _relation_record(root: Path, issue: str) -> dict:
    return json.loads((root / f".agentic-workspace/planning/issue-relations/{issue}.issue-relation.json").read_text(encoding="utf-8"))


def _proposal_record(root: Path, proposal: str) -> dict:
    return json.loads(
        (root / f".agentic-workspace/planning/integration-proposals/{proposal}.integration-proposal.json").read_text(encoding="utf-8")
    )


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=check)


def _init_git(root: Path) -> None:
    _git(root, "init")
    _git(root, "config", "user.email", "planning-tests@example.invalid")
    _git(root, "config", "user.name", "Planning Tests")
    _git(root, "checkout", "-b", "main")


def _commit_all(root: Path, message: str) -> None:
    _git(root, "add", ".")
    _git(root, "commit", "-m", message)


def _write_owner(root: Path, owner_id: str) -> str:
    owner_ref = f".agentic-workspace/planning/execplans/{owner_id}.plan.json"
    owner_path = root / owner_ref
    owner_path.parent.mkdir(parents=True, exist_ok=True)
    owner_path.write_text(
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": owner_id,
                "title": owner_id,
                "owner_level": "slice",
                "lifecycle": "live",
                "phase": "implementation",
                "revision": 1,
                "intent": {},
                "parent": {},
                "scope": {},
                "relationships": {},
                "next_action": "finish integration proof",
                "proof": {},
                "continuation": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return owner_ref


def _write_lane(root: Path, lane_id: str) -> str:
    lane_ref = f".agentic-workspace/planning/lanes/{lane_id}.lane.json"
    lane_path = root / lane_ref
    lane_path.parent.mkdir(parents=True, exist_ok=True)
    lane_path.write_text(
        json.dumps(
            {
                "kind": "planning-lane/v1",
                "id": lane_id,
                "title": lane_id,
                "status": "active",
                "parent_decomposition_ref": ".agentic-workspace/planning/decompositions/parent.decomposition.json",
                "lane_outcome": "Prove branch-safe planning.",
                "purpose_for_parent": "Keep integration transitions explicit.",
                "subsystems": [],
                "technical_strategy": "Use schema-backed planning records.",
                "slice_sequence": [],
                "acceptance_boundary": "The lane remains open until a target-branch integration apply closes it.",
                "proof_strategy": "Focused planning tests.",
                "proof_aggregation": {"status": "not-started", "evidence": [], "known_gaps": []},
                "residual_lane_work": "none",
                "lane_to_epic_contribution": "",
                "parent_close_permission": "do-not-close-parent",
                "closeout_state": {"status": "open", "summary": "", "residual_work": "none", "next_owner": "none"},
                "references": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return lane_ref


def test_issue_shape_relation_is_checked_in_but_non_activating(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    before_state = _state_bytes(tmp_path)

    result = shape_issue_relation(
        issue="2344",
        lane="branch-safe-shaping",
        priority="p0.1",
        depends_on="2338,2346",
        rationale="Relation owns strategic lane placement, not execution lifecycle.",
        maturity="shaped",
        target=tmp_path,
    )

    assert [action.kind for action in result.actions] == ["created", "preserved", "proof", "proof"]
    assert _state_bytes(tmp_path) == before_state
    assert not (tmp_path / ".agentic-workspace/local/planning/owner-selection.json").exists()
    assert not (tmp_path / ".agentic-workspace/planning/execplans/2344.plan.json").exists()
    record = _relation_record(tmp_path, "2344")
    assert record["lane_id"] == "branch-safe-shaping"
    assert record["priority"] == "p0.1"
    assert record["depends_on"] == ["2338", "2346"]
    assert record["authority"]["execution_lifecycle"] == "derived-not-owned"

    summary = planning_summary(target=tmp_path, profile="full")
    assert summary["issue_relations"]["record_count"] == 1
    assert summary["lanes"]["strategic_relations"]["by_lane"]["branch-safe-shaping"][0]["external_ref"] == "2344"

    no_op = shape_issue_relation(issue="2344", target=tmp_path)
    assert [action.kind for action in no_op.actions] == ["no-op"]
    assert no_op.mutation_expected is False


def test_disjoint_issue_relations_have_order_independent_derived_view(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    install_bootstrap(target=first)
    install_bootstrap(target=second)

    shape_issue_relation(issue="2344", lane="branch-safe", priority="p0.1", maturity="shaped", target=first)
    shape_issue_relation(issue="2345", lane="branch-safe", priority="p0.2", maturity="shaped", target=first)
    shape_issue_relation(issue="2345", lane="branch-safe", priority="p0.2", maturity="shaped", target=second)
    shape_issue_relation(issue="2344", lane="branch-safe", priority="p0.1", maturity="shaped", target=second)

    first_view = planning_summary(target=first, profile="full")["issue_relations"]["records"]
    second_view = planning_summary(target=second, profile="full")["issue_relations"]["records"]
    assert first_view == second_view
    assert _state_bytes(first) == _state_bytes(second)


def test_disjoint_issue_relations_merge_cleanly_in_either_git_order(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline")

    _git(tmp_path, "checkout", "-b", "issue-2344")
    shape_issue_relation(issue="2344", lane="branch-safe", priority="p0.1", maturity="shaped", target=tmp_path)
    _commit_all(tmp_path, "shape 2344")

    _git(tmp_path, "checkout", "main")
    _git(tmp_path, "checkout", "-b", "issue-2345")
    shape_issue_relation(issue="2345", lane="branch-safe", priority="p0.2", maturity="shaped", target=tmp_path)
    _commit_all(tmp_path, "shape 2345")

    _git(tmp_path, "checkout", "main")
    _git(tmp_path, "checkout", "-b", "merge-2344-2345")
    _git(tmp_path, "merge", "--no-ff", "issue-2344", "-m", "merge 2344")
    _git(tmp_path, "merge", "--no-ff", "issue-2345", "-m", "merge 2345")
    first_order = planning_summary(target=tmp_path, profile="full")["issue_relations"]["records"]
    first_state = _state_bytes(tmp_path)

    _git(tmp_path, "checkout", "main")
    _git(tmp_path, "checkout", "-b", "merge-2345-2344")
    _git(tmp_path, "merge", "--no-ff", "issue-2345", "-m", "merge 2345")
    _git(tmp_path, "merge", "--no-ff", "issue-2344", "-m", "merge 2344")
    second_order = planning_summary(target=tmp_path, profile="full")["issue_relations"]["records"]

    assert first_order == second_order
    assert first_state == _state_bytes(tmp_path)


def test_same_issue_relation_conflicts_at_git_merge_boundary(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    shape_issue_relation(issue="2344", lane="branch-safe", priority="p0.1", maturity="shaped", target=tmp_path)
    base_revision = _relation_record(tmp_path, "2344")["relation_revision"]
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline relation")

    _git(tmp_path, "checkout", "-b", "raise-priority")
    shape_issue_relation(issue="2344", priority="p0.0", expected_relation_revision=base_revision, target=tmp_path)
    _commit_all(tmp_path, "raise priority")

    _git(tmp_path, "checkout", "main")
    _git(tmp_path, "checkout", "-b", "lower-priority")
    shape_issue_relation(issue="2344", priority="p0.9", expected_relation_revision=base_revision, target=tmp_path)
    _commit_all(tmp_path, "lower priority")

    _git(tmp_path, "checkout", "main")
    _git(tmp_path, "merge", "--no-ff", "raise-priority", "-m", "merge raise priority")
    conflict = _git(tmp_path, "merge", "--no-ff", "lower-priority", "-m", "merge lower priority", check=False)

    assert conflict.returncode != 0
    assert "2344.issue-relation.json" in (conflict.stdout + conflict.stderr)


def test_same_issue_relation_requires_current_relation_revision(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    shape_issue_relation(
        issue="2344",
        lane="branch-safe",
        priority="p0.1",
        depends_on="2338",
        rationale="initial relation",
        maturity="observed",
        target=tmp_path,
    )
    before = (tmp_path / ".agentic-workspace/planning/issue-relations/2344.issue-relation.json").read_bytes()

    missing_guard = shape_issue_relation(issue="2344", priority="p0.2", target=tmp_path)

    assert [action.kind for action in missing_guard.actions] == ["manual review", "next safe action"]
    assert missing_guard.reason_code == "issue-relation-revision-required"
    assert (tmp_path / ".agentic-workspace/planning/issue-relations/2344.issue-relation.json").read_bytes() == before

    stale = shape_issue_relation(issue="2344", priority="p0.2", expected_relation_revision="stale", target=tmp_path)

    assert [action.kind for action in stale.actions] == ["manual review", "next safe action"]
    assert stale.reason_code == "stale-issue-relation-revision"
    assert (tmp_path / ".agentic-workspace/planning/issue-relations/2344.issue-relation.json").read_bytes() == before

    current_revision = _relation_record(tmp_path, "2344")["relation_revision"]
    updated = shape_issue_relation(issue="2344", priority="p0.2", expected_relation_revision=current_revision, target=tmp_path)
    assert [action.kind for action in updated.actions] == ["updated", "preserved", "proof", "proof"]
    assert _relation_record(tmp_path, "2344")["priority"] == "p0.2"

    current_revision = _relation_record(tmp_path, "2344")["relation_revision"]
    planning_before_clear = planning_revision(tmp_path)["revision_id"]
    cleared = shape_issue_relation(
        issue="2344",
        depends_on="__clear__",
        rationale="__clear__",
        expected_relation_revision=current_revision,
        expected_planning_revision=planning_before_clear,
        target=tmp_path,
    )
    assert [action.kind for action in cleared.actions] == ["updated", "preserved", "proof", "proof"]
    assert _relation_record(tmp_path, "2344")["depends_on"] == []
    assert _relation_record(tmp_path, "2344")["rationale"] == ""


def test_external_summary_refresh_does_not_rewrite_issue_relation(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    shape_issue_relation(issue="2344", lane="branch-safe", priority="p0.1", maturity="shaped", target=tmp_path)
    relation_path = tmp_path / ".agentic-workspace/planning/issue-relations/2344.issue-relation.json"
    before_relation = relation_path.read_bytes()

    external_path = tmp_path / ".agentic-workspace/planning/external-intent-evidence.json"
    external_path.write_text(
        json.dumps({"kind": "planning-external-intent-evidence/v1", "items": []}) + "\n",
        encoding="utf-8",
    )
    planning_summary(target=tmp_path, profile="full")

    assert relation_path.read_bytes() == before_relation


def test_integration_proposal_is_pending_until_guarded_apply(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    shape_issue_relation(issue="2345", lane="branch-safe", priority="p0.2", maturity="shaped", target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2345")
    before_state = _state_bytes(tmp_path)

    proposed = propose_integration_transition(
        proposal_id="issue-2345-merged",
        owner="issue-2345",
        owner_ref=owner_ref,
        issue="2345",
        requested_transition="mark-integrated",
        proof="https://github.example/pr/1",
        target=tmp_path,
    )

    assert [action.kind for action in proposed.actions] == ["created", "preserved", "proof", "proof"]
    assert _state_bytes(tmp_path) == before_state
    proposal = _proposal_record(tmp_path, "issue-2345-merged")
    assert proposal["status"] == "pending"
    assert proposal["phase"] == "integration-pending"
    summary = planning_summary(target=tmp_path, profile="full")
    assert summary["integration"]["pending_count"] == 1
    assert any(warning["warning_class"] == "planning_integration_proposal_pending" for warning in summary["warnings"])

    applied = apply_integration_proposal(proposal="issue-2345-merged", target=tmp_path)

    assert [action.kind for action in applied.actions] == ["updated", "updated", "created", "preserved", "proof", "proof"]
    assert _state_bytes(tmp_path) == before_state
    owner_record = json.loads((tmp_path / owner_ref).read_text(encoding="utf-8"))
    assert owner_record["lifecycle"] == "live"
    assert owner_record["phase"] == "implementation"
    assert owner_record["revision"] == 2
    assert owner_record["relationships"]["integration"]["status"] == "integrated"
    assert owner_record["relationships"]["integration"]["transition"] == "mark-integrated"
    proposal = _proposal_record(tmp_path, "issue-2345-merged")
    assert proposal["status"] == "integrated"
    assert proposal["phase"] == "integrated-lifecycle-truth"
    receipt_path = tmp_path / ".agentic-workspace/planning/integration-receipts/issue-2345-merged.integration-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["authority_boundary"]["integrated_truth"] == "this receipt"
    assert receipt["authority_boundary"]["owner_body"] == "updated by this transaction"
    assert receipt["authority_boundary"]["aggregate_indexes"] == "derived-regenerated-not-mutated"
    assert receipt["revisions"]["subject_after"] != receipt["revisions"]["subject_before"]

    no_op = apply_integration_proposal(proposal="issue-2345-merged", target=tmp_path)
    assert [action.kind for action in no_op.actions] == ["no-op"]
    assert no_op.mutation_expected is False


def test_integration_apply_supports_close_archive_and_keep_open(tmp_path: Path) -> None:
    for transition, expected_lifecycle in (("close-owner", "closed"), ("archive-owner", "archived")):
        root = tmp_path / transition
        install_bootstrap(target=root)
        owner_ref = _write_owner(root, f"issue-{transition}")
        propose_integration_transition(
            proposal_id=f"{transition}-proposal",
            owner=f"issue-{transition}",
            owner_ref=owner_ref,
            requested_transition=transition,
            target=root,
        )

        applied = apply_integration_proposal(proposal=f"{transition}-proposal", target=root)

        assert applied.reason_code == ""
        owner_record = json.loads((root / owner_ref).read_text(encoding="utf-8"))
        assert owner_record["lifecycle"] == expected_lifecycle
        assert owner_record["phase"] == "complete"

    root = tmp_path / "keep-open"
    install_bootstrap(target=root)
    owner_ref = _write_owner(root, "issue-keep-open")
    before_owner = (root / owner_ref).read_bytes()
    propose_integration_transition(
        proposal_id="keep-open-proposal",
        owner="issue-keep-open",
        owner_ref=owner_ref,
        requested_transition="keep-open",
        target=root,
    )

    applied = apply_integration_proposal(proposal="keep-open-proposal", target=root)

    assert [action.kind for action in applied.actions] == ["updated", "created", "preserved", "proof", "proof"]
    assert (root / owner_ref).read_bytes() == before_owner


def test_pending_integration_proposal_blocks_direct_execplan_archive(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2345")
    propose_integration_transition(
        proposal_id="issue-2345-close",
        owner="issue-2345",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        target=tmp_path,
    )

    blocked = archive_execplan("issue-2345", target=tmp_path)

    assert [action.kind for action in blocked.actions] == ["manual review", "next safe action"]
    assert blocked.reason_code == "pending-integration-proposal-required"
    assert "integration-apply --proposal issue-2345-close" in blocked.actions[1].detail
    assert json.loads((tmp_path / owner_ref).read_text(encoding="utf-8"))["lifecycle"] == "live"


def test_pending_integration_proposal_blocks_direct_lane_close_and_applies_lane_owner(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    lane_ref = _write_lane(tmp_path, "issue-2345-lane")
    propose_integration_transition(
        proposal_id="issue-2345-lane-close",
        owner="issue-2345-lane",
        owner_ref=lane_ref,
        requested_transition="close-owner",
        proof="https://github.example/pr/2348",
        target=tmp_path,
    )

    blocked = close_lane_record("issue-2345-lane", target=tmp_path)

    assert [action.kind for action in blocked.actions] == ["manual review", "next safe action"]
    assert blocked.reason_code == "pending-integration-proposal-required"
    assert "integration-apply --proposal issue-2345-lane-close" in blocked.actions[1].detail

    applied = apply_integration_proposal(proposal="issue-2345-lane-close", target=tmp_path)

    assert applied.reason_code == ""
    lane_record = json.loads((tmp_path / lane_ref).read_text(encoding="utf-8"))
    assert lane_record["status"] == "closed"
    assert lane_record["closeout_state"]["status"] == "closed"
    assert lane_record["proof_aggregation"]["evidence"]
    assert any(action.kind == "preserved" and "current selection and aggregate indexes" in action.detail for action in applied.actions)


def test_legacy_issue_authority_is_demoted_to_issue_relation_migration(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    state_path.write_text(
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "branch-safe", title = "Branch safe", issues = ["2344"], priority = "p0.1", maturity = "ready", status = "next" },
]
candidates = []
""".lstrip(),
        encoding="utf-8",
    )

    summary = planning_summary(target=tmp_path, profile="full")
    legacy = summary["issue_relations"]["legacy_authority"]
    warnings = summary["warnings"]

    assert legacy["record_count"] == 1
    assert legacy["records"][0]["external_ref"] == "2344"
    assert legacy["records"][0]["relation_status"] == "missing"
    assert legacy["records"][0]["authority_status"] == "freshness-demoted"
    assert any(warning["warning_class"] == "planning_issue_relation_legacy_authority_demoted" for warning in warnings)


def test_integration_apply_rejects_stale_subject_revision(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    shape_issue_relation(issue="2345", lane="branch-safe", priority="p0.2", maturity="shaped", target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2345")
    propose_integration_transition(proposal_id="issue-2345-stale", owner="issue-2345", owner_ref=owner_ref, issue="2345", target=tmp_path)
    relation_revision = _relation_record(tmp_path, "2345")["relation_revision"]
    shape_issue_relation(issue="2345", priority="p0.3", expected_relation_revision=relation_revision, target=tmp_path)

    stale = apply_integration_proposal(proposal="issue-2345-stale", target=tmp_path)

    assert [action.kind for action in stale.actions] == ["manual review"]
    assert stale.reason_code == "stale-integration-subject-revision"
    assert not (tmp_path / ".agentic-workspace/planning/integration-receipts/issue-2345-stale.integration-receipt.json").exists()
    summary = planning_summary(target=tmp_path, profile="full")
    assert any(warning["warning_class"] == "planning_integration_proposal_stale" for warning in summary["warnings"])


def test_integration_apply_rejects_stale_planning_revision(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2345")
    propose_integration_transition(proposal_id="issue-2345-target-stale", owner="issue-2345", owner_ref=owner_ref, target=tmp_path)

    stale = apply_integration_proposal(
        proposal="issue-2345-target-stale",
        expected_planning_revision="stale-target",
        target=tmp_path,
    )

    assert [action.kind for action in stale.actions] == ["manual review"]
    assert stale.reason_code == "stale-integration-planning-revision"
    assert not (tmp_path / ".agentic-workspace/planning/integration-receipts/issue-2345-target-stale.integration-receipt.json").exists()
