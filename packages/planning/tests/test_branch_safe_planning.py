from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import repo_planning_bootstrap.installer as installer
from repo_planning_bootstrap.installer import (
    apply_integration_proposal,
    archive_execplan,
    close_lane_record,
    close_planning_item,
    install_bootstrap,
    planning_reconcile,
    planning_revision,
    planning_summary,
    propose_integration_transition,
    select_existing_owner,
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


def test_same_issue_relation_conflict_has_supported_revision_guarded_reconcile_route(tmp_path: Path) -> None:
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
    _git(tmp_path, "merge", "--abort")

    current_revision = _relation_record(tmp_path, "2344")["relation_revision"]
    resolved = planning_reconcile(
        target=tmp_path,
        issue="2344",
        priority="p0.9",
        rationale="Resolved overlapping priority edits after reviewing both branch deltas.",
        expected_relation_revision=current_revision,
        apply_issue_relation_reconcile=True,
    )

    relation = _relation_record(tmp_path, "2344")
    assert resolved["issue_relation_reconciliation"]["status"] == "applied"
    assert relation["priority"] == "p0.9"
    assert relation["lane_id"] == "branch-safe"
    assert relation["rationale"].startswith("Resolved overlapping")


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


def test_ordinary_solo_issue_workflow_uses_one_revision_guarded_relation(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    shape_issue_relation(issue="2344", lane="inbox", priority="p0.4", maturity="observed", target=tmp_path)
    relation_revision = _relation_record(tmp_path, "2344")["relation_revision"]
    planning_reconcile(
        target=tmp_path,
        issue="2344",
        lane="branch-safe",
        priority="p0.1",
        depends_on="2328,2331",
        rationale="Grouped and reprioritised through the issue relation owner.",
        maturity="ready-to-promote",
        expected_relation_revision=relation_revision,
        apply_issue_relation_reconcile=True,
    )

    relation = _relation_record(tmp_path, "2344")
    summary = planning_summary(target=tmp_path, profile="full")
    assert relation["lane_id"] == "branch-safe"
    assert relation["priority"] == "p0.1"
    assert relation["depends_on"] == ["2328", "2331"]
    assert relation["maturity"] == "ready-to-promote"
    assert summary["issue_relations"]["record_count"] == 1
    assert summary["issue_relations"]["legacy_authority"]["record_count"] == 0
    assert len(summary["issue_relations"]["by_lane"]["branch-safe"]) == 1


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


def test_feature_branch_direct_terminal_writers_require_integration_proposal(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2345")
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline owner")
    _git(tmp_path, "checkout", "-b", "feature/direct-close")

    blocked_archive = archive_execplan("issue-2345", target=tmp_path)
    local_selection = select_existing_owner("issue-2345", target=tmp_path)
    blocked_shared_selection = select_existing_owner("issue-2345", target=tmp_path, mode="shared", reason="checked-in selection")

    assert blocked_archive.reason_code == "integration-proposal-required-on-feature-branch"
    assert "integration-propose" in blocked_archive.actions[1].detail
    assert local_selection.reason_code == ""
    assert blocked_shared_selection.reason_code == "integration-proposal-required-on-feature-branch"
    assert json.loads((tmp_path / owner_ref).read_text(encoding="utf-8"))["lifecycle"] == "live"
    assert (tmp_path / ".agentic-workspace/local/planning/owner-selection.json").exists()


def test_integration_apply_requires_target_branch_and_accepts_merge_queue_branch(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2345")
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline owner")
    _git(tmp_path, "checkout", "-b", "feature/propose-close")
    propose_integration_transition(
        proposal_id="issue-2345-close-target",
        owner="issue-2345",
        owner_ref=owner_ref,
        requested_transition="close-owner",
        target=tmp_path,
    )
    _commit_all(tmp_path, "propose close")

    feature_apply = apply_integration_proposal(proposal="issue-2345-close-target", target=tmp_path)
    assert feature_apply.reason_code == "integration-apply-target-required"

    _git(tmp_path, "checkout", "main")
    _git(tmp_path, "merge", "--no-ff", "feature/propose-close", "-m", "merge proposal")
    _git(tmp_path, "checkout", "-b", "gh-readonly-queue/main/pr-2348")

    applied = apply_integration_proposal(proposal="issue-2345-close-target", target=tmp_path)

    owner_record = json.loads((tmp_path / owner_ref).read_text(encoding="utf-8"))
    assert applied.reason_code == ""
    assert owner_record["lifecycle"] == "closed"
    assert applied.operation_receipt["authority_boundary"]["branch_admission"]["phase"] == "target"


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


def test_pending_integration_proposal_blocks_owner_selection(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2345")
    propose_integration_transition(
        proposal_id="issue-2345-select",
        owner="issue-2345",
        owner_ref=owner_ref,
        requested_transition="mark-integrated",
        target=tmp_path,
    )

    local_selection = select_existing_owner("issue-2345", target=tmp_path)
    blocked = select_existing_owner("issue-2345", target=tmp_path, mode="shared", reason="checked-in selection")

    assert [action.kind for action in blocked.actions] == ["manual review", "next safe action"]
    assert blocked.reason_code == "pending-integration-proposal-required"
    assert "integration-apply --proposal issue-2345-select" in blocked.actions[1].detail
    assert local_selection.reason_code == ""
    assert (tmp_path / ".agentic-workspace/local/planning/owner-selection.json").exists()


def test_pending_integration_proposal_blocks_state_item_close(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    state_path.write_text(
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "issue-2345", title = "Issue 2345", status = "completed", refs = ["2345"] },
]
queued_items = []
""".lstrip(),
        encoding="utf-8",
    )
    before = state_path.read_text(encoding="utf-8")
    propose_integration_transition(
        proposal_id="issue-2345-state",
        issue="2345",
        requested_transition="keep-open",
        target=tmp_path,
    )

    blocked = close_planning_item("issue-2345", issue="2345", target=tmp_path)

    assert [action.kind for action in blocked.actions] == ["manual review", "next safe action"]
    assert blocked.reason_code == "pending-integration-proposal-required"
    assert "integration-apply --proposal issue-2345-state" in blocked.actions[1].detail
    assert state_path.read_text(encoding="utf-8") == before


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


def test_legacy_issue_authority_migrates_without_loss_and_demotes_sources(tmp_path: Path) -> None:
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
  { id = "branch-safe", title = "Branch safe", issues = ["2344"], priority = "p0.1", maturity = "ready", depends_on = ["2328"], reason = "keeps parent intent", status = "next" },
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

    migrated = planning_reconcile(target=tmp_path, apply_issue_relation_migration=True)

    relation = _relation_record(tmp_path, "2344")
    state_after = state_path.read_text(encoding="utf-8")
    summary_after = planning_summary(target=tmp_path, profile="full")
    assert migrated["issue_relation_migration"]["status"] == "applied"
    assert relation["lane_id"] == "branch-safe"
    assert relation["priority"] == "p0.1"
    assert relation["depends_on"] == ["2328"]
    assert relation["rationale"] == "keeps parent intent"
    assert relation["maturity"] == "ready-to-promote"
    assert "issues" not in state_after
    assert "depends_on" not in state_after
    assert "strategic_relation_refs" in state_after
    assert summary_after["issue_relations"]["legacy_authority"]["record_count"] == 0


def test_integration_apply_rejects_stale_subject_revision(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    shape_issue_relation(issue="2345", lane="branch-safe", priority="p0.2", maturity="shaped", target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2345")
    propose_integration_transition(proposal_id="issue-2345-stale", owner="issue-2345", owner_ref=owner_ref, issue="2345", target=tmp_path)
    relation_revision = _relation_record(tmp_path, "2345")["relation_revision"]
    shape_issue_relation(issue="2345", priority="p0.3", expected_relation_revision=relation_revision, target=tmp_path)
    proposal_path = tmp_path / ".agentic-workspace/planning/integration-proposals/issue-2345-stale.integration-proposal.json"
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposal["expected_planning_revision"] = planning_revision(tmp_path)["target_authority_revision"]
    proposal_path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")

    stale = apply_integration_proposal(proposal="issue-2345-stale", target=tmp_path)

    assert stale.actions[0].kind == "manual review"
    assert stale.reason_code == "stale-integration-subject-revision"
    assert not (tmp_path / ".agentic-workspace/planning/integration-receipts/issue-2345-stale.integration-receipt.json").exists()
    summary = planning_summary(target=tmp_path, profile="full")
    assert any(warning["warning_class"] == "planning_integration_proposal_stale" for warning in summary["warnings"])


def test_integration_apply_rejects_stale_planning_revision(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2345")
    propose_integration_transition(proposal_id="issue-2345-target-stale", owner="issue-2345", owner_ref=owner_ref, target=tmp_path)
    _write_owner(tmp_path, "unrelated-target-change")

    stale = apply_integration_proposal(
        proposal="issue-2345-target-stale",
        target=tmp_path,
    )

    assert stale.actions[0].kind == "manual review"
    assert stale.reason_code == "stale-integration-planning-revision"
    assert not (tmp_path / ".agentic-workspace/planning/integration-receipts/issue-2345-target-stale.integration-receipt.json").exists()


def test_integration_apply_rejects_conflicting_apply_token(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2345")
    propose_integration_transition(proposal_id="issue-2345-token", owner="issue-2345", owner_ref=owner_ref, target=tmp_path)

    stale = apply_integration_proposal(
        proposal="issue-2345-token",
        expected_planning_revision="stale-target",
        target=tmp_path,
    )

    assert [action.kind for action in stale.actions] == ["manual review"]
    assert stale.reason_code == "integration-planning-revision-conflict"


def test_reconcile_reports_structural_mutation_admission_inventory(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    inventory = planning_reconcile(target=tmp_path)["mutation_admission_inventory"]
    by_operation = {entry["operation"]: entry for entry in inventory["entries"]}

    assert by_operation["planning.owner-select.lifecycle --mode local"]["feature_branch_admission"] == "allowed"
    assert by_operation["planning.owner-select.lifecycle --mode shared"]["feature_branch_admission"] == "blocked"
    assert by_operation["planning.integration-apply.lifecycle"]["feature_branch_admission"] == "blocked"
    assert by_operation["planning.reconcile.report --apply-pending-integrations"]["feature_branch_admission"] == "blocked"
    assert by_operation["planning.issue-shape.lifecycle"]["feature_branch_admission"] == "allowed"


def test_issue_2328_2331_feature_replay_is_owner_scoped_and_repair_free(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_refs = {issue: _write_owner(tmp_path, f"issue-{issue}") for issue in ("2328", "2329", "2330", "2331")}
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline owners")

    for issue, owner_ref in owner_refs.items():
        _git(tmp_path, "checkout", "main")
        _git(tmp_path, "checkout", "-b", f"feature/issue-{issue}")
        propose_integration_transition(
            proposal_id=f"issue-{issue}-integrated",
            owner=f"issue-{issue}",
            owner_ref=owner_ref,
            issue=issue,
            requested_transition="mark-integrated",
            proof=f"https://github.example/pr/{issue}",
            target=tmp_path,
        )
        changed_files = _git(tmp_path, "status", "--short", "--untracked-files=all").stdout.splitlines()
        assert changed_files == [f"?? .agentic-workspace/planning/integration-proposals/issue-{issue}-integrated.integration-proposal.json"]
        _commit_all(tmp_path, f"propose issue {issue}")

    for issue in ("2328", "2329", "2330", "2331"):
        _git(tmp_path, "checkout", "main")
        _git(tmp_path, "merge", "--no-ff", f"feature/issue-{issue}", "-m", f"merge issue {issue}")
    applied = planning_reconcile(target=tmp_path, apply_pending_integrations=True)
    _commit_all(tmp_path, "apply pending issue integrations")
    assert applied["pending_integration_apply"]["status"] == "applied"
    assert applied["pending_integration_apply"]["applied_count"] == 4

    receipts = sorted((tmp_path / ".agentic-workspace/planning/integration-receipts").glob("*.integration-receipt.json"))
    proposals = sorted((tmp_path / ".agentic-workspace/planning/integration-proposals").glob("*.integration-proposal.json"))
    assert len(receipts) == 4
    assert len(proposals) == 4
    for issue, owner_ref in owner_refs.items():
        owner = json.loads((tmp_path / owner_ref).read_text(encoding="utf-8"))
        assert owner["lifecycle"] == "live"
        assert owner["relationships"]["integration"]["status"] == "integrated"


def test_stacked_child_proposal_applies_with_parent_in_one_target_reconcile(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    parent_owner = _write_owner(tmp_path, "issue-parent")
    child_owner = _write_owner(tmp_path, "issue-child")
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline owners")

    _git(tmp_path, "checkout", "-b", "feature/parent")
    propose_integration_transition(
        proposal_id="issue-parent-integrated",
        owner="issue-parent",
        owner_ref=parent_owner,
        requested_transition="mark-integrated",
        target=tmp_path,
    )
    _commit_all(tmp_path, "propose parent")

    _git(tmp_path, "checkout", "-b", "feature/child")
    propose_integration_transition(
        proposal_id="issue-child-integrated",
        owner="issue-child",
        owner_ref=child_owner,
        requested_transition="mark-integrated",
        target=tmp_path,
    )
    _commit_all(tmp_path, "propose child")

    _git(tmp_path, "checkout", "main")
    _git(tmp_path, "merge", "--no-ff", "feature/parent", "-m", "merge parent")
    _git(tmp_path, "merge", "--no-ff", "feature/child", "-m", "merge child")

    applied = planning_reconcile(target=tmp_path, apply_pending_integrations=True)

    assert applied["pending_integration_apply"]["status"] == "applied"
    assert applied["pending_integration_apply"]["applied_count"] == 2
    for owner_ref in (parent_owner, child_owner):
        owner = json.loads((tmp_path / owner_ref).read_text(encoding="utf-8"))
        assert owner["relationships"]["integration"]["status"] == "integrated"


def test_pending_integration_batch_rolls_back_owner_proposal_and_receipt_on_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-rollback")
    propose_integration_transition(
        proposal_id="issue-rollback-integrated",
        owner="issue-rollback",
        owner_ref=owner_ref,
        requested_transition="mark-integrated",
        target=tmp_path,
    )
    owner_before = (tmp_path / owner_ref).read_bytes()
    proposal_path = tmp_path / ".agentic-workspace/planning/integration-proposals/issue-rollback-integrated.integration-proposal.json"
    proposal_before = proposal_path.read_bytes()
    receipt_path = tmp_path / ".agentic-workspace/planning/integration-receipts/issue-rollback-integrated.integration-receipt.json"
    original_write = installer._write_schema_backed_planning_record

    def fail_receipt_write(*, record_path: Path, record: dict, schema_path: Path) -> None:
        if record_path == receipt_path:
            raise OSError("injected receipt write failure")
        original_write(record_path=record_path, record=record, schema_path=schema_path)

    monkeypatch.setattr(installer, "_write_schema_backed_planning_record", fail_receipt_write)

    applied = planning_reconcile(target=tmp_path, apply_pending_integrations=True)

    assert applied["pending_integration_apply"]["status"] == "blocked"
    assert applied["pending_integration_apply"]["reason_code"] == "integration-apply-rolled-back"
    assert (tmp_path / owner_ref).read_bytes() == owner_before
    assert proposal_path.read_bytes() == proposal_before
    assert not receipt_path.exists()
