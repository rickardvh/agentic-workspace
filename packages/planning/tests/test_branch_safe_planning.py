from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

import repo_planning_bootstrap.installer as installer
from repo_planning_bootstrap.installer import (
    apply_integration_proposal,
    archive_execplan,
    close_lane_record,
    close_planning_item,
    create_execplan_scaffold,
    install_bootstrap,
    planning_reconcile,
    planning_revision,
    planning_summary,
    propose_integration_transition,
    select_existing_owner,
    shape_issue_relation,
    upgrade_bootstrap,
)


def _state_bytes(root: Path) -> bytes:
    path = root / ".agentic-workspace/planning/state.toml"
    return path.read_bytes() if path.is_file() else b""


def _planning_persistent_snapshot(root: Path) -> dict[str, bytes]:
    paths = [path for path in (root / ".agentic-workspace/planning").rglob("*") if path.is_file()]
    for local_root in ("planning", "decision-point-intent", "planning-archive-exports"):
        paths.extend(path for path in (root / ".agentic-workspace/local" / local_root).rglob("*") if path.is_file())
    roadmap = root / "ROADMAP.md"
    if roadmap.is_file():
        paths.append(roadmap)
    last_closeout = root / ".agentic-workspace/local/planning-last-closeout.json"
    if last_closeout.is_file():
        paths.append(last_closeout)
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(paths)}


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


def _feature_completion_evidence(issue: str) -> dict[str, str]:
    return {
        "what_happened": f"Implemented issue {issue} on the feature head.",
        "scope_touched": "Planning integration proposal lifecycle.",
        "changed_surfaces": "installer.py and focused branch-safe Planning tests.",
        "review_summary": "Reviewed the bounded feature-head scope and proof.",
        "outcome_summary": f"Issue {issue} is feature-complete pending target integration.",
    }


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


def _attach_owner_to_lane(root: Path, lane_id: str, owner_id: str, owner_ref: str) -> Path:
    lane_path = root / _write_lane(root, lane_id)
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    lane["slice_sequence"] = [
        {
            "id": owner_id,
            "title": owner_id,
            "status": "active",
            "execplan_ref": owner_ref,
            "depends_on": [],
            "purpose_for_lane": "Deliver the current bounded slice.",
        }
    ]
    lane["current_slice"] = owner_id
    lane_path.write_text(json.dumps(lane, indent=2) + "\n", encoding="utf-8")
    return lane_path


def test_fresh_install_derives_planning_without_global_state(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    assert not (tmp_path / ".agentic-workspace/planning/state.toml").exists()
    summary = planning_summary(target=tmp_path, profile="full")
    assert summary["todo"]["active_items"] == []
    assert summary["todo"]["queued_items"] == []
    assert summary["roadmap"]["candidates"] == []


def test_new_plan_selects_locally_without_rewriting_legacy_aggregate(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    state_path.write_text(
        'kind = "agentic-planning-state"\nschema_version = "planning-state/v1"\n\n'
        "[todo]\nactive_items = []\nqueued_items = []\n\n"
        "[roadmap]\nlanes = []\ncandidates = []\n",
        encoding="utf-8",
    )
    before = state_path.read_bytes()

    result = create_execplan_scaffold(
        plan_id="owner-a",
        title="Owner A",
        source="issue #2801",
        activate=True,
        switch_active=True,
        target=tmp_path,
    )

    assert result.reason_code == ""
    assert state_path.read_bytes() == before
    selection = json.loads((tmp_path / ".agentic-workspace/local/planning/owner-selection.json").read_text(encoding="utf-8"))
    assert selection["selected_owner"]["id"] == "owner-a"
    assert planning_summary(target=tmp_path, profile="full")["todo"]["active_items"][0]["id"] == "owner-a"


def test_new_plan_activation_preserves_existing_current_work_identity(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    create_execplan_scaffold(plan_id="owner-a", title="Owner A", activate=True, target=tmp_path)
    selection_path = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    selection["current_work_id"] = "thread-dogfood-2928"
    selection_path.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")

    created = create_execplan_scaffold(plan_id="owner-b", title="Owner B", activate=True, switch_active=True, target=tmp_path)
    after_create = json.loads(selection_path.read_text(encoding="utf-8"))

    assert created.reason_code == ""
    assert after_create["selected_owner"]["id"] == "owner-b"
    assert after_create["current_work_id"] == "thread-dogfood-2928"
    assert any("thread-dogfood-2928" in action.detail for action in created.actions)

    overwritten = create_execplan_scaffold(
        plan_id="owner-b",
        title="Owner B tightened",
        activate=True,
        switch_active=True,
        overwrite=True,
        target=tmp_path,
    )
    after_overwrite = json.loads(selection_path.read_text(encoding="utf-8"))

    assert overwritten.reason_code == ""
    assert after_overwrite["selected_owner"]["id"] == "owner-b"
    assert after_overwrite["current_work_id"] == "thread-dogfood-2928"


def test_upgrade_retires_legacy_state_idempotently_and_preserves_natural_owners(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "owner-a")
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    state_path.write_text(
        f'''kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [{{ id = "owner-a", status = "active", surface = "{owner_ref}" }}]
queued_items = [{{ id = "stale-queue", status = "next", refs = ["#99"] }}]

[roadmap]
lanes = [{{ id = "branch-safe", issues = ["2801"], priority = "p0.1", depends_on = ["2800"], reason = "bounded relation" }}]
candidates = [{{ id = "external-backlog", refs = ["#123"] }}]
''',
        encoding="utf-8",
    )

    first = upgrade_bootstrap(target=tmp_path)
    receipt_path = tmp_path / ".agentic-workspace/local/planning/legacy-state-migration.json"
    receipt_before = receipt_path.read_bytes()

    assert not state_path.exists()
    assert any(action.kind == "removed" and action.path == state_path for action in first.actions)
    receipt = json.loads(receipt_before)
    dispositions = {entry["field"]: entry["disposition"] for entry in receipt["field_dispositions"]}
    assert dispositions["todo.active_items"] == "localise"
    assert dispositions["todo.queued_items"] == "drop"
    assert dispositions["roadmap.lanes"] == "derive"
    assert dispositions["roadmap.candidates"] == "return-to-external-evidence"
    assert _relation_record(tmp_path, "2801")["lane_id"] == "branch-safe"
    assert planning_summary(target=tmp_path, profile="full")["todo"]["active_items"][0]["id"] == "owner-a"

    second = upgrade_bootstrap(target=tmp_path)
    assert not state_path.exists()
    assert receipt_path.read_bytes() == receipt_before
    assert not any(action.path == state_path and action.kind in {"created", "updated"} for action in second.actions)


def test_disjoint_owner_activation_merges_in_either_order_without_aggregate_repair(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    (tmp_path / ".gitignore").write_text(".agentic-workspace/local/\n", encoding="utf-8")
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline without aggregate")

    for owner_id in ("owner-a", "owner-b"):
        _git(tmp_path, "checkout", "main")
        _git(tmp_path, "checkout", "-b", owner_id)
        create_execplan_scaffold(plan_id=owner_id, title=owner_id, activate=True, switch_active=True, target=tmp_path)
        assert not (tmp_path / ".agentic-workspace/planning/state.toml").exists()
        assert _git(tmp_path, "status", "--short", "--untracked-files=all").stdout.splitlines() == [
            f"?? .agentic-workspace/planning/execplans/{owner_id}.plan.json"
        ]
        _commit_all(tmp_path, f"create {owner_id}")

    for branch, order in (("merge-a-b", ("owner-a", "owner-b")), ("merge-b-a", ("owner-b", "owner-a"))):
        _git(tmp_path, "checkout", "main")
        _git(tmp_path, "checkout", "-b", branch)
        for owner_id in order:
            _git(tmp_path, "merge", "--no-ff", owner_id, "-m", f"merge {owner_id}")
        assert not (tmp_path / ".agentic-workspace/planning/state.toml").exists()
        assert {path.name for path in (tmp_path / ".agentic-workspace/planning/execplans").glob("owner-*.plan.json")} == {
            "owner-a.plan.json",
            "owner-b.plan.json",
        }


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


def test_integration_proposal_dry_run_projects_the_typed_apply_invocation(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2865")
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline pending owner")
    _git(tmp_path, "checkout", "-b", "feature/2865-complete")
    before_subject = installer._integration_subject_revision(target_root=tmp_path, owner_ref=owner_ref, external_ref="#2865")
    before_planning = installer._planning_target_authority_revision(tmp_path)["revision_id"]

    preview = propose_integration_transition(
        proposal_id="issue-2865-archive",
        owner="issue-2865",
        owner_ref=owner_ref,
        issue="#2865",
        requested_transition="archive-owner",
        proof="proof://feature-head/2865",
        **_feature_completion_evidence("#2865"),
        record_feature_completion=True,
        expected_subject_revision=before_subject,
        expected_planning_revision=before_planning,
        target=tmp_path,
        dry_run=True,
    )

    lifecycle_plan = installer._lifecycle_plan_payload(preview)
    invocation = lifecycle_plan["operation_invocation"]
    assert lifecycle_plan["operation"] == "integration-propose"
    assert invocation["operation_id"] == "planning.integration-propose.lifecycle"
    assert invocation["arguments"]["proposal_id"] == "issue-2865-archive"
    assert invocation["arguments"]["requested_transition"] == "archive-owner"
    assert invocation["arguments"]["expected_subject_revision"] == before_subject
    assert invocation["arguments"]["expected_planning_revision"] == before_planning
    assert invocation["arguments"]["record_feature_completion"] is True
    assert invocation["arguments"]["what_happened"] == "Implemented issue #2865 on the feature head."
    assert lifecycle_plan["next_safe_command"] == invocation["renderings"]["cli"]
    assert "archive-plan" not in lifecycle_plan["next_safe_command"]

    command = shlex.split(lifecycle_plan["next_safe_command"])
    executable = shutil.which(command[0])
    assert executable is not None
    applied = subprocess.run([executable, *command[1:]], text=True, capture_output=True, check=False)
    assert applied.returncode == 0, applied.stderr
    payload = json.loads(applied.stdout)
    assert payload["operation_receipt"]["proposal_id"] == "issue-2865-archive"
    proposal = _proposal_record(tmp_path, "issue-2865-archive")
    assert proposal["requested_transition"] == "archive-owner"
    assert proposal["expected_subject_revision"] != before_subject
    assert proposal["expected_planning_revision"] != before_planning


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
        assert owner_record["relationships"]["integration"]["transition"] == transition
        assert owner_record["relationships"]["integration"]["receipt_ref"].endswith(f"{transition}-proposal.integration-receipt.json")

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
    assert "--record-feature-completion" in blocked_archive.recovery_command
    assert "--expect-subject-revision" in blocked_archive.recovery_command
    assert "--expect-planning-revision" in blocked_archive.recovery_command
    assert local_selection.reason_code == ""
    assert blocked_shared_selection.reason_code == "shared-selection-retired"
    assert json.loads((tmp_path / owner_ref).read_text(encoding="utf-8"))["lifecycle"] == "live"
    assert (tmp_path / ".agentic-workspace/local/planning/owner-selection.json").exists()


def test_feature_branch_closeout_rejection_is_non_mutating(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2491")
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline owner")
    _git(tmp_path, "checkout", "-b", "feature/rejected-closeout")
    before = _planning_persistent_snapshot(tmp_path)

    blocked = installer.closeout_execplan("issue-2491", target=tmp_path)

    assert blocked.reason_code == "integration-proposal-required-on-feature-branch"
    assert "--record-feature-completion" in blocked.recovery_command
    assert _planning_persistent_snapshot(tmp_path) == before
    assert json.loads((tmp_path / owner_ref).read_text(encoding="utf-8"))["lifecycle"] == "live"


def test_feature_complete_integration_proposal_updates_owner_and_applies_on_target(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2851")
    owner_path = tmp_path / owner_ref
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    owner["relationships"]["proof_posture"] = {"state": "accepted", "refs": ["proof://feature-head/2851"]}
    owner["proof"]["refs"] = ["proof://feature-head/2851"]
    owner_path.write_text(json.dumps(owner, indent=2) + "\n", encoding="utf-8")
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline proven owner")
    _git(tmp_path, "checkout", "-b", "feature/2851-complete")
    before_subject = installer._integration_subject_revision(target_root=tmp_path, owner_ref=owner_ref, external_ref="")
    before_planning = installer._planning_target_authority_revision(tmp_path)["revision_id"]

    proposed = propose_integration_transition(
        proposal_id="issue-2851-archive",
        owner="issue-2851",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        expected_subject_revision=before_subject,
        expected_planning_revision=before_planning,
        target=tmp_path,
    )

    assert proposed.reason_code == ""
    guard = proposed.revision_guards["expect_planning_revision"]
    assert guard == {
        "cli_option": "--expect-planning-revision",
        "authority": "target-authority",
        "source_field": "planning_revision.target_authority_revision",
        "current_value": before_planning,
    }
    assert proposed.to_dict()["revision_guards"]["rule"].startswith(
        "--expect-planning-revision consumes planning_revision.target_authority_revision"
    )
    feature_owner = json.loads(owner_path.read_text(encoding="utf-8"))
    proposal = _proposal_record(tmp_path, "issue-2851-archive")
    assert feature_owner["lifecycle"] == "live"
    assert feature_owner["phase"] == "closeout"
    assert feature_owner["relationships"]["integration"]["status"] == "feature-complete-integration-pending"
    assert "Apply integration proposal" in feature_owner["next_action"]
    assert proposal["proof_refs"] == ["proof://feature-head/2851"]
    assert proposal["expected_subject_revision"] == installer._integration_subject_revision(
        target_root=tmp_path, owner_ref=owner_ref, external_ref=""
    )
    assert proposal["expected_planning_revision"] == installer._planning_target_authority_revision(tmp_path)["revision_id"]

    replay = propose_integration_transition(
        proposal_id="issue-2851-archive",
        owner="issue-2851",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        expected_subject_revision=proposal["expected_subject_revision"],
        target=tmp_path,
    )
    assert replay.mutation_expected is False
    assert [action.kind for action in replay.actions] == ["no-op"]

    _commit_all(tmp_path, "feature complete proposal")
    _git(tmp_path, "checkout", "main")
    _git(tmp_path, "merge", "--no-ff", "feature/2851-complete", "-m", "merge feature completion")
    applied = apply_integration_proposal(proposal="issue-2851-archive", target=tmp_path)
    assert applied.reason_code == ""
    integrated_owner = json.loads(owner_path.read_text(encoding="utf-8"))
    assert integrated_owner["lifecycle"] == "archived"
    assert integrated_owner["phase"] == "complete"


def test_feature_completion_mode_atomically_records_proof_and_proposes_integration(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2862")
    owner_path = tmp_path / owner_ref
    owner_before = json.loads(owner_path.read_text(encoding="utf-8"))
    owner_before["intent"] = {"outcome": "Implemented issue #2862 on the feature head."}
    owner_before["scope"] = {"owned": ["Planning integration proposal lifecycle."]}
    owner_before["continuation"] = {
        "owner": ".agentic-workspace/planning/execplans/issue-2863-next.plan.json",
        "residual_intent": "Continue with issue #2863 after target integration.",
    }
    owner_path.write_text(json.dumps(owner_before, indent=2) + "\n", encoding="utf-8")
    lane_path = _attach_owner_to_lane(tmp_path, "delivery-lane", "issue-2862", owner_ref)
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline pending owner")
    _git(tmp_path, "checkout", "-b", "feature/2862-complete")
    before_subject = installer._integration_subject_revision(target_root=tmp_path, owner_ref=owner_ref, external_ref="")
    before_planning = installer._planning_target_authority_revision(tmp_path)["revision_id"]

    proposed = propose_integration_transition(
        proposal_id="issue-2862-archive",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        proof="proof://feature-head/2862,ci://feature-head/2862",
        record_feature_completion=True,
        expected_subject_revision=before_subject,
        expected_planning_revision=before_planning,
        target=tmp_path,
    )

    assert proposed.reason_code == ""
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    proposal = _proposal_record(tmp_path, "issue-2862-archive")
    assert owner["lifecycle"] == "live"
    assert owner["phase"] == "closeout"
    assert owner["relationships"]["proof_posture"] == {
        "state": "accepted",
        "refs": ["proof://feature-head/2862", "ci://feature-head/2862"],
    }
    assert owner["proof_report"]["validation proof"] == "proof://feature-head/2862, ci://feature-head/2862"
    assert owner["execution_run"]["run status"] == "completed"
    assert owner["execution_run"]["what happened"] == "Implemented issue #2862 on the feature head."
    assert owner["execution_run"]["scope touched"] == "Planning integration proposal lifecycle."
    assert owner["execution_run"]["changed surfaces"] == "Planning integration proposal lifecycle."
    assert owner["finished_run_review"]["review status"] == "complete"
    assert owner["finished_run_review"]["scope respected"] == "Reviewed feature-head scope: Planning integration proposal lifecycle."
    assert owner["execution_summary"]["outcome delivered"] == "Implemented issue #2862 on the feature head."
    assert owner["intent_satisfaction"]["was original intent fully satisfied?"] == "yes"
    assert owner["relationships"]["integration"]["status"] == "feature-complete-integration-pending"
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    assert [item["status"] for item in lane["slice_sequence"]] == ["integration-pending", "planned"]
    assert lane["slice_sequence"][0]["proof"] == "proof://feature-head/2862, ci://feature-head/2862"
    assert lane["proof_aggregation"]["status"] == "partial"
    assert lane["closeout_state"]["next_owner"] == ".agentic-workspace/planning/execplans/issue-2863-next.plan.json"
    assert proposal["proof_refs"] == ["proof://feature-head/2862", "ci://feature-head/2862"]
    assert proposal["expected_subject_revision"] == installer._integration_subject_revision(
        target_root=tmp_path, owner_ref=owner_ref, external_ref=""
    )

    replay = propose_integration_transition(
        proposal_id="issue-2862-archive",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        proof="proof://feature-head/2862,ci://feature-head/2862",
        record_feature_completion=True,
        expected_subject_revision=proposal["expected_subject_revision"],
        expected_planning_revision=proposal["expected_planning_revision"],
        target=tmp_path,
    )
    assert replay.mutation_expected is False
    assert [action.kind for action in replay.actions] == ["no-op"]

    _commit_all(tmp_path, "feature completion with lane contribution")
    _git(tmp_path, "checkout", "main")
    _git(tmp_path, "merge", "--no-ff", "feature/2862-complete", "-m", "merge feature completion")
    applied = apply_integration_proposal(proposal="issue-2862-archive", target=tmp_path)

    assert applied.reason_code == ""
    integrated_owner = json.loads(owner_path.read_text(encoding="utf-8"))
    integrated_lane = json.loads(lane_path.read_text(encoding="utf-8"))
    assert integrated_owner["lifecycle"] == "archived"
    assert [item["status"] for item in integrated_lane["slice_sequence"]] == ["completed", "ready"]
    assert integrated_lane["current_slice"] == "issue-2863-next"
    assert integrated_lane["status"] == "active"


def test_feature_completion_mode_rolls_back_owner_when_proposal_write_fails(tmp_path: Path, monkeypatch) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2862-rollback")
    owner_path = tmp_path / owner_ref
    lane_path = _attach_owner_to_lane(tmp_path, "rollback-lane", "issue-2862-rollback", owner_ref)
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline pending owner")
    _git(tmp_path, "checkout", "-b", "feature/2862-rollback")
    before_owner = owner_path.read_bytes()
    before_lane = lane_path.read_bytes()
    before_subject = installer._integration_subject_revision(target_root=tmp_path, owner_ref=owner_ref, external_ref="")
    before_planning = installer._planning_target_authority_revision(tmp_path)["revision_id"]
    original_write = installer._write_schema_backed_planning_record
    write_count = 0

    def fail_proposal_write(*, record_path: Path, record: dict[str, Any], schema_path: Path) -> None:
        nonlocal write_count
        write_count += 1
        if write_count == 3:
            record_path.write_text("partial\n", encoding="utf-8")
            raise OSError("simulated proposal failure")
        original_write(record_path=record_path, record=record, schema_path=schema_path)

    monkeypatch.setattr(installer, "_write_schema_backed_planning_record", fail_proposal_write)
    proposed = propose_integration_transition(
        proposal_id="issue-2862-rollback",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        proof="proof://feature-head/2862",
        **_feature_completion_evidence("#2862"),
        record_feature_completion=True,
        expected_subject_revision=before_subject,
        expected_planning_revision=before_planning,
        target=tmp_path,
    )

    assert proposed.reason_code == "integration-proposal-rolled-back"
    assert owner_path.read_bytes() == before_owner
    assert lane_path.read_bytes() == before_lane
    assert not (tmp_path / ".agentic-workspace/planning/integration-proposals/issue-2862-rollback.integration-proposal.json").exists()


def _completion_correction_fixture(tmp_path: Path, owner_id: str) -> tuple[str, Path, Path, dict[str, Any]]:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, owner_id)
    owner_path = tmp_path / owner_ref
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    owner["intent"] = {"outcome": f"Implement {owner_id} on the feature head."}
    owner["scope"] = {"owned": ["Planning completion truth."]}
    owner["continuation"] = {"owner": "none", "residual_intent": "none"}
    owner_path.write_text(json.dumps(owner, indent=2) + "\n", encoding="utf-8")
    lane_path = _attach_owner_to_lane(tmp_path, f"{owner_id}-lane", owner_id, owner_ref)
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline completed owner")
    _git(tmp_path, "checkout", "-b", f"feature/{owner_id}")
    before_subject = installer._integration_subject_revision(target_root=tmp_path, owner_ref=owner_ref, external_ref="")
    before_planning = installer._planning_target_authority_revision(tmp_path)["revision_id"]
    proposal_id = f"{owner_id}-proposal"
    proposed = propose_integration_transition(
        proposal_id=proposal_id,
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        proof=f"proof://{owner_id}",
        **_feature_completion_evidence(owner_id),
        record_feature_completion=True,
        expected_subject_revision=before_subject,
        expected_planning_revision=before_planning,
        target=tmp_path,
    )
    assert proposed.reason_code == ""
    return owner_ref, owner_path, lane_path, _proposal_record(tmp_path, proposal_id)


def _completion_correction_request(
    *, tmp_path: Path, owner_ref: str, lane_path: Path, proposal: dict[str, Any], disposition: str
) -> dict[str, Any]:
    owner = json.loads((tmp_path / owner_ref).read_text(encoding="utf-8"))
    return {
        "target": tmp_path,
        "plan": owner_ref,
        "patch": {"intent": {"outcome": "Corrected after admitted blocking review."}},
        "expected_planning_revision": planning_revision(tmp_path)["revision_id"],
        "expected_owner_revision": owner["revision"],
        "expected_lane_revision": installer._record_revision(json.loads(lane_path.read_text(encoding="utf-8"))),
        "completion_correction": {
            "id": f"{owner['id']}-review-correction",
            "disposition": disposition,
            "review_refs": ["review://blocking/2951"],
            "proof_refs": ["proof://corrected/2951"] if disposition == "remain-feature-complete" else [],
            "completion_evidence": (
                {
                    "what_happened": "Corrected feature-head implementation remains complete.",
                    "scope_touched": "Planning completion truth.",
                    "changed_surfaces": "installer.py and focused tests.",
                    "review_summary": "Reviewed corrected completion evidence.",
                    "outcome_summary": "Corrected feature completion awaits target integration.",
                }
                if disposition == "remain-feature-complete"
                else {}
            ),
            "next_action": "Repair the reviewed completion truth and rerun focused validation.",
            "expected_proposal_revision": proposal["proposal_revision"],
            "expected_target_authority_revision": installer._planning_target_authority_revision(tmp_path)["revision_id"],
        },
    }


def test_targeted_write_completion_correction_reopens_and_invalidates_proposal(tmp_path: Path) -> None:
    owner_ref, owner_path, lane_path, proposal = _completion_correction_fixture(tmp_path, "issue-2951-reopen")
    unrelated_ref = _write_owner(tmp_path, "unrelated-owner")
    unrelated_before = (tmp_path / unrelated_ref).read_bytes()
    request = _completion_correction_request(
        tmp_path=tmp_path, owner_ref=owner_ref, lane_path=lane_path, proposal=proposal, disposition="reopen"
    )

    preview = installer.targeted_execplan_write(**request)
    applied = installer.targeted_execplan_write(**request, apply=True)

    assert preview["status"] == "preview"
    assert preview["completion_correction"]["proposal_outcome"] == "rejected"
    assert applied["status"] == "applied"
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    updated_proposal = _proposal_record(tmp_path, proposal["id"])
    assert owner["phase"] == "implementation"
    assert owner["finished_run_review"]["review status"] == "blocking"
    assert owner["closure_check"]["closure decision"] == "continue"
    assert lane["slice_sequence"][0]["status"] == "active"
    assert updated_proposal["status"] == updated_proposal["phase"] == "rejected"
    assert (tmp_path / unrelated_ref).read_bytes() == unrelated_before
    assert installer.targeted_execplan_write(**request, apply=True)["status"] == "already-applied"


def test_targeted_write_completion_correction_reopen_retracts_only_child_evidence(tmp_path: Path) -> None:
    owner_ref, _owner_path, lane_path, proposal = _completion_correction_fixture(tmp_path, "issue-2951-evidence")
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    lane["slice_sequence"].append(
        {
            "id": "other-slice",
            "title": "other-slice",
            "status": "completed",
            "execplan_ref": ".agentic-workspace/planning/execplans/other-slice.plan.json",
            "depends_on": [],
            "purpose_for_lane": "Preserve independent evidence.",
            "proof": "proof://other-slice",
        }
    )
    lane["proof_aggregation"]["evidence"].append("proof://other-slice")
    lane_path.write_text(json.dumps(lane, indent=2) + "\n", encoding="utf-8")
    request = _completion_correction_request(
        tmp_path=tmp_path, owner_ref=owner_ref, lane_path=lane_path, proposal=proposal, disposition="reopen"
    )

    assert installer.targeted_execplan_write(**request, apply=True)["status"] == "applied"

    updated_lane = json.loads(lane_path.read_text(encoding="utf-8"))
    assert f"proof://{proposal['owner']['id']}" not in updated_lane["proof_aggregation"]["evidence"]
    assert "proof://other-slice" in updated_lane["proof_aggregation"]["evidence"]


def test_targeted_write_completion_correction_preserves_later_sibling_shared_evidence(tmp_path: Path) -> None:
    owner_ref, _owner_path, lane_path, proposal = _completion_correction_fixture(tmp_path, "issue-2951-shared-evidence")
    shared_proof = f"proof://{proposal['owner']['id']}"
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    lane["slice_sequence"].append(
        {
            "id": "later-sibling",
            "title": "later-sibling",
            "status": "completed",
            "execplan_ref": ".agentic-workspace/planning/execplans/later-sibling.plan.json",
            "depends_on": [],
            "purpose_for_lane": "Retain independently contributed shared proof.",
            "proof": shared_proof,
        }
    )
    lane_path.write_text(json.dumps(lane, indent=2) + "\n", encoding="utf-8")
    request = _completion_correction_request(
        tmp_path=tmp_path, owner_ref=owner_ref, lane_path=lane_path, proposal=proposal, disposition="reopen"
    )

    assert installer.targeted_execplan_write(**request, apply=True)["status"] == "applied"

    updated_lane = json.loads(lane_path.read_text(encoding="utf-8"))
    assert shared_proof in updated_lane["proof_aggregation"]["evidence"]


def test_targeted_write_completion_correction_no_material_source_patch_is_byte_preserving(tmp_path: Path) -> None:
    owner_ref, owner_path, lane_path, proposal = _completion_correction_fixture(tmp_path, "issue-2951-noop")
    proposal_path = tmp_path / f".agentic-workspace/planning/integration-proposals/{proposal['id']}.integration-proposal.json"
    before = {path: path.read_bytes() for path in (owner_path, lane_path, proposal_path)}
    request = _completion_correction_request(
        tmp_path=tmp_path, owner_ref=owner_ref, lane_path=lane_path, proposal=proposal, disposition="reopen"
    )
    request["patch"] = {"intent": json.loads(owner_path.read_text(encoding="utf-8"))["intent"]}

    preview = installer.targeted_execplan_write(**request)
    applied = installer.targeted_execplan_write(**request, apply=True)

    assert preview["status"] == applied["status"] == "no-op"
    assert {path: path.read_bytes() for path in before} == before


def test_targeted_write_completion_correction_refreshes_current_proposal_and_rejects_stale_guard(tmp_path: Path) -> None:
    owner_ref, owner_path, lane_path, proposal = _completion_correction_fixture(tmp_path, "issue-2951-complete")
    request = _completion_correction_request(
        tmp_path=tmp_path,
        owner_ref=owner_ref,
        lane_path=lane_path,
        proposal=proposal,
        disposition="remain-feature-complete",
    )
    stale = dict(request)
    stale["completion_correction"] = dict(request["completion_correction"])
    stale["completion_correction"]["expected_proposal_revision"] = "stale"
    assert installer.targeted_execplan_write(**stale)["status"] == "stale-integration-proposal-revision"

    applied = installer.targeted_execplan_write(**request, apply=True)
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    refreshed = _proposal_record(tmp_path, proposal["id"])
    assert applied["status"] == "applied"
    assert owner["phase"] == "closeout"
    assert owner["intent_satisfaction"]["was original intent fully satisfied?"] == "yes"
    assert refreshed["status"] == "pending"
    assert refreshed["proposal_revision"] != proposal["proposal_revision"]
    assert refreshed["expected_subject_revision"] == installer._integration_subject_revision(
        target_root=tmp_path, owner_ref=owner_ref, external_ref=""
    )


def test_targeted_write_completion_correction_rolls_back_owner_lane_and_proposal(tmp_path: Path, monkeypatch) -> None:
    owner_ref, owner_path, lane_path, proposal = _completion_correction_fixture(tmp_path, "issue-2951-rollback")
    proposal_path = tmp_path / f".agentic-workspace/planning/integration-proposals/{proposal['id']}.integration-proposal.json"
    before = {path: path.read_bytes() for path in (owner_path, lane_path, proposal_path)}
    request = _completion_correction_request(
        tmp_path=tmp_path, owner_ref=owner_ref, lane_path=lane_path, proposal=proposal, disposition="reopen"
    )
    original_write = installer._write_schema_backed_planning_record

    def fail_proposal(*, record_path: Path, record: dict[str, Any], schema_path: Path) -> None:
        if record_path == proposal_path:
            record_path.write_text("partial\n", encoding="utf-8")
            raise OSError("injected proposal write failure")
        original_write(record_path=record_path, record=record, schema_path=schema_path)

    monkeypatch.setattr(installer, "_write_schema_backed_planning_record", fail_proposal)
    result = installer.targeted_execplan_write(**request, apply=True)

    assert result["status"] == "rolled-back"
    assert {path: path.read_bytes() for path in before} == before


def test_feature_completion_rejects_stale_or_unproven_owner(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2851-negative")
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline unproven owner")
    _git(tmp_path, "checkout", "-b", "feature/2851-negative")
    before = _planning_persistent_snapshot(tmp_path)

    unproven = propose_integration_transition(
        proposal_id="issue-2851-negative",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        proof="proof://caller-asserted",
        expected_subject_revision="stale",
        target=tmp_path,
    )

    assert unproven.reason_code == "feature-completion-proof-required"
    assert _planning_persistent_snapshot(tmp_path) == before

    current_subject = installer._integration_subject_revision(target_root=tmp_path, owner_ref=owner_ref, external_ref="")
    current_planning = installer._planning_target_authority_revision(tmp_path)["revision_id"]
    missing_evidence = propose_integration_transition(
        proposal_id="issue-2851-negative",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        proof="proof://feature-head/2851",
        record_feature_completion=True,
        expected_subject_revision=current_subject,
        expected_planning_revision=current_planning,
        target=tmp_path,
    )
    assert missing_evidence.reason_code == "feature-completion-evidence-required"
    assert all(option in missing_evidence.recovery_command for option in ("--what-happened", "--scope-touched", "--changed-surfaces"))
    assert _planning_persistent_snapshot(tmp_path) == before

    missing_target_guard = propose_integration_transition(
        proposal_id="issue-2851-negative",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        proof="proof://feature-head/2851",
        **_feature_completion_evidence("#2851"),
        record_feature_completion=True,
        expected_subject_revision=current_subject,
        target=tmp_path,
    )
    assert missing_target_guard.reason_code == "feature-completion-planning-revision-required"
    assert _planning_persistent_snapshot(tmp_path) == before

    stale_feature_owner = propose_integration_transition(
        proposal_id="issue-2851-negative",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        proof="proof://feature-head/2851",
        **_feature_completion_evidence("#2851"),
        record_feature_completion=True,
        expected_subject_revision="stale",
        expected_planning_revision=installer._planning_target_authority_revision(tmp_path)["revision_id"],
        target=tmp_path,
    )
    assert stale_feature_owner.reason_code == "stale-feature-completion-subject-revision"
    assert current_subject in stale_feature_owner.recovery_command
    assert "--record-feature-completion" in stale_feature_owner.recovery_command
    assert _planning_persistent_snapshot(tmp_path) == before

    owner_path = tmp_path / owner_ref
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    owner["relationships"]["proof_posture"] = {"state": "accepted", "refs": ["proof://feature-head/2851"]}
    owner["proof"]["refs"] = ["proof://feature-head/2851"]
    owner_path.write_text(json.dumps(owner, indent=2) + "\n", encoding="utf-8")
    current_subject = installer._integration_subject_revision(target_root=tmp_path, owner_ref=owner_ref, external_ref="")
    stale_planning = propose_integration_transition(
        proposal_id="issue-2851-negative",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        expected_subject_revision=current_subject,
        expected_planning_revision="stale",
        target=tmp_path,
    )
    assert stale_planning.reason_code == "stale-feature-completion-planning-revision"
    current_target_authority = planning_revision(tmp_path)["target_authority_revision"]
    assert current_target_authority in stale_planning.actions[0].detail
    assert "planning_revision.target_authority_revision" in stale_planning.actions[0].detail
    assert f"--expect-planning-revision {current_target_authority}" in stale_planning.recovery_command
    stale = propose_integration_transition(
        proposal_id="issue-2851-negative",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        expected_subject_revision="stale",
        target=tmp_path,
    )
    assert stale.reason_code == "stale-feature-completion-subject-revision"
    assert not (tmp_path / ".agentic-workspace/planning/integration-proposals/issue-2851-negative.integration-proposal.json").exists()


def test_pending_integration_proposal_blocks_closeout_before_mutation(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-2491")
    propose_integration_transition(
        proposal_id="issue-2491-archive",
        owner="issue-2491",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        target=tmp_path,
    )
    before = _planning_persistent_snapshot(tmp_path)

    blocked = installer.closeout_execplan("issue-2491", target=tmp_path)

    assert blocked.reason_code == "pending-integration-proposal-required"
    assert _planning_persistent_snapshot(tmp_path) == before


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

    assert [action.kind for action in blocked.actions] == ["manual review"]
    assert blocked.reason_code == "shared-selection-retired"
    assert "--mode local" in blocked.recovery_command
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
    state_before = state_path.read_text(encoding="utf-8")

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
    assert state_after == state_before
    legacy_after = summary_after["issue_relations"]["legacy_authority"]
    assert legacy_after["record_count"] == 1
    assert legacy_after["records"][0]["relation_status"] == "present"
    assert legacy_after["records"][0]["authority_status"] == "freshness-demoted"


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


def test_integration_proposal_refresh_updates_only_freshness_and_unblocks_reconcile(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-refresh")
    propose_integration_transition(
        proposal_id="issue-refresh-archive",
        owner="issue-refresh",
        owner_ref=owner_ref,
        requested_transition="archive-owner",
        proof="proof://stable",
        parent_boundary="parent remains independently owned",
        invariant="do not widen lifecycle authority",
        target=tmp_path,
    )
    proposal_before = _proposal_record(tmp_path, "issue-refresh-archive")
    owner_path = tmp_path / owner_ref
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    owner["next_action"] = "current target-branch closeout state"
    owner_path.write_text(json.dumps(owner, indent=2) + "\n", encoding="utf-8")
    subject_revision = installer._integration_subject_revision(target_root=tmp_path, owner_ref=owner_ref)
    target_revision = planning_revision(tmp_path)["target_authority_revision"]

    refreshed = propose_integration_transition(
        proposal_id="issue-refresh-archive",
        refresh_existing=True,
        expected_proposal_revision=proposal_before["proposal_revision"],
        expected_subject_revision=subject_revision,
        expected_planning_revision=target_revision,
        target=tmp_path,
    )

    assert [action.kind for action in refreshed.actions] == ["updated", "preserved", "proof", "proof"]
    proposal_after = _proposal_record(tmp_path, "issue-refresh-archive")
    immutable_fields = (
        "status",
        "phase",
        "requested_transition",
        "owner",
        "external_ref",
        "proof_refs",
        "parent_boundary",
        "preserved_invariants",
        "created_at",
        "authority_boundary",
    )
    assert {field: proposal_after[field] for field in immutable_fields} == {field: proposal_before[field] for field in immutable_fields}
    assert proposal_after["expected_subject_revision"] == subject_revision
    assert proposal_after["expected_planning_revision"] == target_revision
    assert proposal_after["proposal_revision"] != proposal_before["proposal_revision"]
    assert refreshed.operation_receipt["outcome"] == "refreshed"
    assert refreshed.operation_receipt["changed_fields"] == [
        "expected_planning_revision",
        "expected_subject_revision",
        "proposal_revision",
        "updated_at",
    ]

    preview = planning_reconcile(target=tmp_path, preview=True)
    assert preview["status"] == "preview"
    assert preview["proposal"]["eligible_proposals"] == ["issue-refresh-archive"]
    assert preview["proposal"]["semantic_conflicts"] == []

    replay = propose_integration_transition(
        proposal_id="issue-refresh-archive",
        refresh_existing=True,
        expected_proposal_revision=proposal_after["proposal_revision"],
        expected_subject_revision=subject_revision,
        expected_planning_revision=target_revision,
        target=tmp_path,
    )
    assert [action.kind for action in replay.actions] == ["no-op"]
    assert replay.mutation_expected is False
    assert replay.operation_receipt["outcome"] == "no-op"


@pytest.mark.parametrize(
    ("guard", "reason_code"),
    (
        ("proposal", "stale-integration-proposal-revision"),
        ("subject", "stale-integration-refresh-subject-revision"),
        ("planning", "stale-integration-refresh-planning-revision"),
    ),
)
def test_integration_proposal_refresh_rejects_stale_guards_without_mutation(tmp_path: Path, guard: str, reason_code: str) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-refresh-guard")
    propose_integration_transition(
        proposal_id="issue-refresh-guard",
        owner="issue-refresh-guard",
        owner_ref=owner_ref,
        target=tmp_path,
    )
    proposal_path = tmp_path / ".agentic-workspace/planning/integration-proposals/issue-refresh-guard.integration-proposal.json"
    proposal = _proposal_record(tmp_path, "issue-refresh-guard")
    before = proposal_path.read_bytes()
    values = {
        "expected_proposal_revision": proposal["proposal_revision"],
        "expected_subject_revision": proposal["expected_subject_revision"],
        "expected_planning_revision": planning_revision(tmp_path)["target_authority_revision"],
    }
    values[f"expected_{guard}_revision"] = "stale-guard"

    rejected = propose_integration_transition(
        proposal_id="issue-refresh-guard",
        refresh_existing=True,
        target=tmp_path,
        **values,
    )

    assert rejected.reason_code == reason_code
    assert proposal_path.read_bytes() == before


def test_integration_proposal_refresh_rejects_non_pending_or_semantic_input(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-refresh-closed")
    propose_integration_transition(
        proposal_id="issue-refresh-closed",
        owner="issue-refresh-closed",
        owner_ref=owner_ref,
        target=tmp_path,
    )
    proposal = _proposal_record(tmp_path, "issue-refresh-closed")
    guards = {
        "expected_proposal_revision": proposal["proposal_revision"],
        "expected_subject_revision": proposal["expected_subject_revision"],
        "expected_planning_revision": planning_revision(tmp_path)["target_authority_revision"],
    }

    semantic = propose_integration_transition(
        proposal_id="issue-refresh-closed",
        refresh_existing=True,
        requested_transition="archive-owner",
        target=tmp_path,
        **guards,
    )
    assert semantic.reason_code == "integration-refresh-semantic-input-rejected"

    apply_integration_proposal(proposal="issue-refresh-closed", target=tmp_path)
    integrated = _proposal_record(tmp_path, "issue-refresh-closed")
    rejected = propose_integration_transition(
        proposal_id="issue-refresh-closed",
        refresh_existing=True,
        expected_proposal_revision=integrated["proposal_revision"],
        expected_subject_revision=integrated["expected_subject_revision"],
        expected_planning_revision=planning_revision(tmp_path)["target_authority_revision"],
        target=tmp_path,
    )
    assert rejected.reason_code == "integration-refresh-pending-required"


def test_integration_proposal_refresh_allows_external_keep_open_subject_with_legacy_owner_ref(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    propose_integration_transition(
        proposal_id="external-keep-open",
        owner="legacy-state",
        owner_ref=".agentic-workspace/planning/state.toml",
        external_ref="2345",
        requested_transition="keep-open",
        target=tmp_path,
    )
    proposal = _proposal_record(tmp_path, "external-keep-open")
    relation_path = tmp_path / ".agentic-workspace/planning/issue-relations/2345.issue-relation.json"
    relation_path.parent.mkdir(parents=True, exist_ok=True)
    relation_path.write_text('{"external_ref": "2345", "changed": true}\n', encoding="utf-8")
    subject_revision = installer._integration_subject_revision(
        target_root=tmp_path,
        owner_ref=".agentic-workspace/planning/state.toml",
        external_ref="2345",
    )

    refreshed = propose_integration_transition(
        proposal_id="external-keep-open",
        refresh_existing=True,
        expected_proposal_revision=proposal["proposal_revision"],
        expected_subject_revision=subject_revision,
        expected_planning_revision=planning_revision(tmp_path)["target_authority_revision"],
        target=tmp_path,
    )

    assert refreshed.reason_code == ""
    assert refreshed.operation_receipt["outcome"] == "refreshed"


def test_integration_proposal_refresh_rolls_back_write_failure(tmp_path: Path, monkeypatch) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-refresh-rollback")
    propose_integration_transition(
        proposal_id="issue-refresh-rollback",
        owner="issue-refresh-rollback",
        owner_ref=owner_ref,
        target=tmp_path,
    )
    proposal_path = tmp_path / ".agentic-workspace/planning/integration-proposals/issue-refresh-rollback.integration-proposal.json"
    proposal = _proposal_record(tmp_path, "issue-refresh-rollback")
    owner_path = tmp_path / owner_ref
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    owner["next_action"] = "force a freshness refresh"
    owner_path.write_text(json.dumps(owner, indent=2) + "\n", encoding="utf-8")
    before = proposal_path.read_bytes()

    def fail_after_partial_write(*, record_path: Path, record: dict[str, Any], schema_path: Path) -> None:
        del record, schema_path
        record_path.write_text("partial\n", encoding="utf-8")
        raise OSError("simulated write failure")

    monkeypatch.setattr(installer, "_write_schema_backed_planning_record", fail_after_partial_write)
    refreshed = propose_integration_transition(
        proposal_id="issue-refresh-rollback",
        refresh_existing=True,
        expected_proposal_revision=proposal["proposal_revision"],
        expected_subject_revision=installer._integration_subject_revision(target_root=tmp_path, owner_ref=owner_ref),
        expected_planning_revision=planning_revision(tmp_path)["target_authority_revision"],
        target=tmp_path,
    )

    assert refreshed.reason_code == "integration-refresh-rolled-back"
    assert refreshed.operation_receipt == {}
    assert proposal_path.read_bytes() == before


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
    lane_path = _attach_owner_to_lane(tmp_path, "issue-2328-lane", "issue-2328", owner_refs["2328"])
    _init_git(tmp_path)
    _commit_all(tmp_path, "baseline owners")

    for issue, owner_ref in owner_refs.items():
        _git(tmp_path, "checkout", "main")
        _git(tmp_path, "checkout", "-b", f"feature/issue-{issue}")
        if issue == "2328":
            propose_integration_transition(
                proposal_id=f"issue-{issue}-integrated",
                owner=f"issue-{issue}",
                owner_ref=owner_ref,
                issue=issue,
                requested_transition="archive-owner",
                proof=f"https://github.example/pr/{issue}",
                **_feature_completion_evidence(f"#{issue}"),
                record_feature_completion=True,
                expected_subject_revision=installer._integration_subject_revision(
                    target_root=tmp_path, owner_ref=owner_ref, external_ref=issue
                ),
                expected_planning_revision=installer._planning_target_authority_revision(tmp_path)["revision_id"],
                target=tmp_path,
            )
        else:
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
        proposal_status = f"?? .agentic-workspace/planning/integration-proposals/issue-{issue}-integrated.integration-proposal.json"
        if issue == "2328":
            assert set(changed_files) == {
                f" M {owner_ref}",
                " M .agentic-workspace/planning/lanes/issue-2328-lane.lane.json",
                proposal_status,
            }
        else:
            assert changed_files == [proposal_status]
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
        assert owner["lifecycle"] == ("archived" if issue == "2328" else "live")
        assert owner["relationships"]["integration"]["status"] == "integrated"
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    assert lane["slice_sequence"][0]["status"] == "completed"
    assert lane["current_slice"] == "aggregate-final-lane-proof"


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


def test_stale_disjoint_proposal_is_skipped_while_current_owner_applies(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    stale_owner_ref = _write_owner(tmp_path, "issue-stale-owner")
    current_owner_ref = _write_owner(tmp_path, "issue-current-owner")
    propose_integration_transition(
        proposal_id="issue-stale-owner-integrated",
        owner="issue-stale-owner",
        owner_ref=stale_owner_ref,
        requested_transition="mark-integrated",
        target=tmp_path,
    )
    propose_integration_transition(
        proposal_id="issue-current-owner-integrated",
        owner="issue-current-owner",
        owner_ref=current_owner_ref,
        requested_transition="mark-integrated",
        target=tmp_path,
    )
    stale_owner_path = tmp_path / stale_owner_ref
    stale_owner = json.loads(stale_owner_path.read_text(encoding="utf-8"))
    stale_owner["next_action"] = "changed independently after proposal"
    stale_owner_path.write_text(json.dumps(stale_owner, indent=2) + "\n", encoding="utf-8")

    applied = planning_reconcile(target=tmp_path, apply_pending_integrations=True)["pending_integration_apply"]

    assert applied["status"] == "applied"
    assert applied["applied_count"] == 1
    assert applied["receipts"] == ["issue-current-owner-integrated"]
    assert len(applied["skipped_proposals"]) == 1
    conflict = applied["skipped_proposals"][0]
    assert conflict["proposal_id"] == "issue-stale-owner-integrated"
    assert conflict["owner_ref"] == stale_owner_ref
    assert conflict["reason_code"] == "stale-integration-subject-revision"
    assert conflict["expected_subject_revision"] != conflict["current_subject_revision"]
    assert conflict["proposal_revision"]
    assert conflict["current_target_authority_revision"] == applied["target_authority_before"]
    assert _proposal_record(tmp_path, "issue-stale-owner-integrated")["status"] == "pending"
    assert _proposal_record(tmp_path, "issue-current-owner-integrated")["status"] == "integrated"
    assert json.loads((tmp_path / current_owner_ref).read_text(encoding="utf-8"))["relationships"]["integration"]["status"] == "integrated"


def test_stale_target_authority_compiles_one_bounded_preview_apply_transaction(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _init_git(tmp_path)
    completed_owner_refs = [_write_owner(tmp_path, owner_id) for owner_id in ("issue-2793-parent", "issue-2793-child")]
    unrelated_owner_ref = _write_owner(tmp_path, "unrelated-live-owner")
    select_existing_owner(owner="unrelated-live-owner", target=tmp_path)
    shape_issue_relation(issue="2793", lane="closeout", priority="p0.2", maturity="ready-to-promote", target=tmp_path)
    for index, owner_ref in enumerate(completed_owner_refs):
        propose_integration_transition(
            proposal_id=f"issue-2793-{index}-integrated",
            owner_ref=owner_ref,
            requested_transition="mark-integrated",
            proof=f"proof://2793/{index}",
            target=tmp_path,
        )
    # This unrelated target-authority change makes both proposal CAS revisions
    # stale without changing either proposal's bounded semantic subject.
    unrelated_path = tmp_path / unrelated_owner_ref
    unrelated = json.loads(unrelated_path.read_text(encoding="utf-8"))
    unrelated["next_action"] = "preserve this unrelated human intent"
    unrelated_path.write_text(json.dumps(unrelated, indent=2) + "\n", encoding="utf-8")
    unrelated_before = unrelated_path.read_bytes()
    relation_path = tmp_path / ".agentic-workspace/planning/issue-relations/2793.issue-relation.json"
    relation_before = relation_path.read_bytes()
    selection_path = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    selection_before = selection_path.read_bytes()
    assert not (tmp_path / ".agentic-workspace/planning/state.toml").exists()

    preview = planning_reconcile(target=tmp_path, preview=True)

    assert preview["status"] == "preview"
    assert preview["transaction_class"] == "target-authority-integration"
    proposal = preview["proposal"]
    assert proposal["affected_owner_refs"] == sorted(completed_owner_refs)
    assert proposal["eligible_proposals"] == ["issue-2793-0-integrated", "issue-2793-1-integrated"]
    assert proposal["refreshed_proposals"] == proposal["eligible_proposals"]
    assert [item["operation"] for item in proposal["operations"]] == [
        "refresh-target-authority-and-apply",
        "refresh-target-authority-and-apply",
    ]
    assert len(json.dumps(preview)) < 20_000
    assert "--preview" in proposal["preview_command"]
    assert f"--proposal {proposal['proposal_id']}" in proposal["apply_command"]
    assert unrelated_path.read_bytes() == unrelated_before

    applied = planning_reconcile(
        target=tmp_path,
        apply=True,
        proposal=proposal["proposal_id"],
        expected_planning_revision=proposal["source"]["planning_revision"],
    )

    assert applied["status"] == "applied"
    assert applied["receipt"]["applied_proposals"] == proposal["eligible_proposals"]
    assert applied["postcondition"]["repository_views"] == "derived-no-second-reconciliation-required"
    assert unrelated_path.read_bytes() == unrelated_before
    assert relation_path.read_bytes() == relation_before
    assert selection_path.read_bytes() == selection_before
    assert not (tmp_path / ".agentic-workspace/planning/state.toml").exists()
    for owner_ref in completed_owner_refs:
        owner = json.loads((tmp_path / owner_ref).read_text(encoding="utf-8"))
        assert owner["relationships"]["integration"]["status"] == "integrated"

    replay = planning_reconcile(
        target=tmp_path,
        apply=True,
        proposal=proposal["proposal_id"],
        expected_planning_revision=proposal["source"]["planning_revision"],
    )
    assert replay["status"] == "already-applied"
    assert replay["receipt"] == applied["receipt"]


def test_target_authority_transaction_keeps_stale_subject_conflict_out_of_disjoint_apply(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _init_git(tmp_path)
    stale_owner_ref = _write_owner(tmp_path, "semantic-conflict")
    eligible_owner_ref = _write_owner(tmp_path, "disjoint-eligible")
    for proposal_id, owner_ref in (("semantic-conflict", stale_owner_ref), ("disjoint-eligible", eligible_owner_ref)):
        propose_integration_transition(proposal_id=proposal_id, owner_ref=owner_ref, target=tmp_path)
    stale_path = tmp_path / stale_owner_ref
    stale_owner = json.loads(stale_path.read_text(encoding="utf-8"))
    stale_owner["next_action"] = "genuine human-authored semantic change"
    stale_path.write_text(json.dumps(stale_owner, indent=2) + "\n", encoding="utf-8")

    preview = planning_reconcile(target=tmp_path, preview=True)

    assert preview["status"] == "preview"
    proposal = preview["proposal"]
    assert proposal["eligible_proposals"] == ["disjoint-eligible"]
    assert proposal["semantic_conflicts"][0]["proposal_id"] == "semantic-conflict"
    assert proposal["semantic_conflicts"][0]["reason_code"] == "stale-integration-subject-revision"

    applied = planning_reconcile(
        target=tmp_path,
        apply=True,
        proposal=proposal["proposal_id"],
        expected_planning_revision=proposal["source"]["planning_revision"],
    )
    assert applied["status"] == "applied"
    assert _proposal_record(tmp_path, "semantic-conflict")["status"] == "pending"
    assert _proposal_record(tmp_path, "disjoint-eligible")["status"] == "integrated"


def test_target_authority_transaction_returns_exact_regeneration_after_preview_cas_drift(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _init_git(tmp_path)
    owner_ref = _write_owner(tmp_path, "cas-refresh-owner")
    propose_integration_transition(proposal_id="cas-refresh-owner", owner_ref=owner_ref, proof="proof://stable", target=tmp_path)
    preview = planning_reconcile(target=tmp_path, preview=True)
    prior = preview["proposal"]
    _write_owner(tmp_path, "unrelated-cas-advance")

    stale_apply = planning_reconcile(
        target=tmp_path,
        apply=True,
        proposal=prior["proposal_id"],
        expected_planning_revision=prior["source"]["planning_revision"],
    )

    assert stale_apply["status"] == "blocked"
    assert stale_apply["reason"] == "proposal-stale-or-mismatched"
    assert stale_apply["expected_proposal"] != prior["proposal_id"]
    assert stale_apply["preview_command"].count("planning reconcile") == 1
    refreshed = planning_reconcile(target=tmp_path, preview=True)
    assert refreshed["proposal"]["proposal_id"] == stale_apply["expected_proposal"]
    assert refreshed["proposal"]["eligible_proposals"] == prior["eligible_proposals"]
    assert refreshed["proposal"]["operations"][0]["operation"] == "refresh-target-authority-and-apply"


def test_same_owner_pending_proposals_fail_closed_before_disjoint_apply(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_ref = _write_owner(tmp_path, "issue-overlap")
    for proposal_id in ("issue-overlap-first", "issue-overlap-second"):
        propose_integration_transition(
            proposal_id=proposal_id,
            owner="issue-overlap",
            owner_ref=owner_ref,
            requested_transition="mark-integrated",
            target=tmp_path,
        )

    blocked = planning_reconcile(target=tmp_path, apply_pending_integrations=True)["pending_integration_apply"]

    assert blocked["status"] == "blocked"
    assert blocked["reason_code"] == "overlapping-integration-proposals-require-reconcile"
    assert blocked["overlapping_owners"] == [owner_ref]
    assert all(
        _proposal_record(tmp_path, proposal_id)["status"] == "pending" for proposal_id in ("issue-overlap-first", "issue-overlap-second")
    )


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
