from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

from jsonschema import Draft202012Validator

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from planning_test_support import *


def test_intake_artifact_routes_freehand_markdown_to_queued_execplan(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(tmp_path / "DOC_CLEANUP_PLAN.md", "# Documentation Cleanup Plan\n\n- Continue later.\n")

    assert (
        planning_cli.main(
            [
                "intake-artifact",
                "--artifact",
                "DOC_CLEANUP_PLAN.md",
                "--target",
                str(tmp_path),
                "--id",
                "doc-cleanup",
                "--title",
                "Documentation Cleanup",
                "--queue",
                "--remove-source",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    record_path = tmp_path / ".agentic-workspace/planning/execplans/doc-cleanup.plan.json"
    state = installer_mod._read_state_from_toml(tmp_path)
    warnings = planning_summary(target=tmp_path, profile="compact")["planning_surface_health"]["warnings"]

    assert payload["warnings"] == []
    assert any(action["kind"] == "created" and action["path"].endswith("doc-cleanup.plan.json") for action in payload["actions"])
    assert any(action["kind"] == "removed" and action["path"].endswith("DOC_CLEANUP_PLAN.md") for action in payload["actions"])
    assert record_path.exists()
    assert not (tmp_path / "DOC_CLEANUP_PLAN.md").exists()
    assert state["todo"]["queued_items"][0]["id"] == "doc-cleanup"
    assert "planning_artifact_freehand" not in {warning["warning_class"] for warning in warnings}


def test_intake_artifact_routes_misplaced_decomposition_to_canonical_path(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    source_path = tmp_path / ".agentic-workspace/planning/planning-decomposition-shop.json"
    _write(
        source_path,
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Shop",
                "status": "shaping",
                "larger_intended_outcome": "Build shop.",
                "non_goals": [],
                "candidate_lanes": [],
                "proof_expectations": [],
                "promotion_rule": "Promote ready lanes.",
            },
            indent=2,
        ),
    )

    assert (
        planning_cli.main(
            [
                "intake-artifact",
                "--artifact",
                ".agentic-workspace/planning/planning-decomposition-shop.json",
                "--target",
                str(tmp_path),
                "--route",
                "decomposition",
                "--id",
                "shop",
                "--remove-source",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    canonical_path = tmp_path / ".agentic-workspace/planning/decompositions/shop.decomposition.json"
    warnings = planning_summary(target=tmp_path, profile="compact")["planning_surface_health"]["warnings"]

    assert payload["warnings"] == []
    assert canonical_path.exists()
    assert not source_path.exists()
    assert "planning_decomposition_artifact_misplaced" not in {warning["warning_class"] for warning in warnings}


def test_promote_todo_item_to_execplan_scaffolds_plan_and_updates_todo(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: direct-item
  Status: in-progress
  Surface: direct
  Why now: this thread needs a bounded execution contract.
  Next Action: sketch the first implementation step.
  Done When: the bounded change is implemented and validated.
""",
    )

    result = promote_todo_item_to_execplan("direct-item", target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "direct-item.md"
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "direct-item.plan.json"

    assert not plan_path.exists()
    assert record_path.exists()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    todo_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert record["kind"] == "planning-execplan/v1"
    assert record["execplan_profile"]["task_shape"] == "bounded"
    assert "canonical_core" in record["execplan_profile"]["required_core"]
    assert record["canonical_core"]["requested_outcome"] == "this thread needs a bounded execution contract."
    assert record["canonical_core"]["next_action"] == "sketch the first implementation step."
    assert record["canonical_core"]["proof_expectations"] == ["Fill in the narrowest command that proves the promoted work."]
    assert record["active_milestone"]["id"] == "direct-item"
    assert record["intent_continuity"]["this slice completes the larger intended outcome"] == "yes"
    assert record["intent_continuity"]["continuation surface"] == "none"
    assert record["required_continuation"]["required follow-on for the larger intended outcome"] == "no"
    assert record["iterative_follow_through"]["proof achieved now"] == "pending"
    assert record["intent_interpretation"]["inferred intended outcome"] == "this thread needs a bounded execution contract."
    assert record["context_budget"]["tiny resumability note"] == "sketch the first implementation step."
    assert record["execution_run"]["run status"] == "not-run-yet"
    assert record["finished_run_review"]["review status"] == "pending"
    assert record["improvement_signal_review"]["status"] == "not_checked"
    assert "no_signal_found" in record["improvement_signal_review"]["accepted statuses"]
    assert record["improvement_signal_review"]["source"] == "operating_posture"
    assert "smoothness/helpfulness gaps" in record["improvement_signal_review"]["guidance"]
    assert record["improvement_signal_review"]["owner classes"] == [
        "issue",
        "Memory",
        "Planning",
        "docs/checks/contracts",
        "direct fix",
        "dismissed with reason",
    ]
    assert record["improvement_signal_review"]["ordinary output cap"] == 3
    assert record["delegated_judgment"]["requested outcome"] == "this thread needs a bounded execution contract."
    assert installer_mod.planning_record_schema_findings(record_path) == []
    assert "Surface: .agentic-workspace/planning/execplans/direct-item.md" in todo_text
    assert "Next Action:" not in todo_text
    assert "Done When:" not in todo_text
    assert any(action.kind == "created" and action.path == record_path for action in result.actions)


def test_promote_todo_item_to_execplan_supports_compact_toml_active_items(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "compact-item", maturity = "active", status = "active", surface = "direct", why_now = "this thread needs the package command to dogfood compact state.", next_action = "promote the compact item.", done_when = "the command creates a plan." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    result = promote_todo_item_to_execplan("compact-item", target=tmp_path)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "compact-item.plan.json"

    assert record_path.exists()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    summary = planning_summary(target=tmp_path)
    assert record["kind"] == "planning-execplan/v1"
    assert record["active_milestone"]["id"] == "compact-item"
    assert record["delegated_judgment"]["requested outcome"] == "this thread needs the package command to dogfood compact state."
    assert record["context_budget"]["pre-work config pull"] == (
        "Use compact config/startup/summary outputs before opening raw planning or routing files."
    )
    assert 'kind = "agentic-planning-state"' in state_text
    assert 'schema_version = "planning-state/v1"' in state_text
    assert 'maturity = "active"' in state_text
    assert 'status = "active"' in state_text
    assert 'surface = ".agentic-workspace/planning/execplans/compact-item.plan.json"' in state_text
    assert "next_action" not in state_text
    assert "done_when" not in state_text
    assert summary["follow_through_contract"]["status"] == "present"
    assert summary["intent_interpretation_contract"]["status"] == "present"
    assert summary["context_budget_contract"]["status"] == "present"
    assert summary["context_budget_contract"]["tiny_resumability_note"] == "promote the compact item."
    assert summary["execution_run_contract"]["status"] == "present"
    assert summary["finished_run_review_contract"]["status"] == "present"
    assert any(action.kind == "created" and action.path == record_path for action in result.actions)


def test_promote_todo_item_to_execplan_preserves_compact_state_types(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "typed-item", status = "active", surface = "direct", why_now = "promotion must keep structured state valid.", next_action = "promote the typed item.", done_when = "state remains clean.", owner_role = "implementation", review_role = "validation", handoff_ready = true, refs = ["#545"] },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    result = promote_todo_item_to_execplan("typed-item", target=tmp_path)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "typed-item.plan.json"

    assert record_path.exists()
    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    state = tomllib.loads(state_text)
    state_item = state["todo"]["active_items"][0]
    summary = planning_summary(target=tmp_path)
    assert 'surface = ".agentic-workspace/planning/execplans/typed-item.plan.json"' in state_text
    assert 'maturity = "active"' in state_text
    assert "handoff_ready = true" in state_text
    assert 'refs = ["#545"]' in state_text
    assert 'handoff_ready = "True"' not in state_text
    assert 'refs = "#545"' not in state_text
    assert state_item["handoff_ready"] is True
    assert state_item["refs"] == ["#545"]
    assert state_item["maturity"] == "active"
    assert state_item["status"] == "active"
    assert state_item["surface"] == ".agentic-workspace/planning/execplans/typed-item.plan.json"
    assert summary["planning_surface_health"]["status"] == "clean"
    assert summary["planning_record"]["execplan_profile"]["task_shape"] == "delegation"
    assert summary["planning_record"]["canonical_core"]["next_action"] == "promote the typed item."
    assert summary["todo"]["active_items"][0]["handoff_ready"] is True
    assert summary["todo"]["active_items"][0]["maturity"] == "active"
    assert any(action.kind == "created" and action.path == record_path for action in result.actions)


def test_promote_todo_item_to_execplan_supports_work_items_state(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = [
  { id = "work-item", type = "slice", maturity = "ready", status = "next", why_now = "this ready slice should become active.", next_action = "promote the work item.", done_when = "the command creates a plan.", owner_role = "implementation", review_role = "validation", handoff_ready = true },
]

[active]
execplans = []
""",
    )

    result = promote_todo_item_to_execplan("work-item", target=tmp_path)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "work-item.plan.json"

    assert record_path.exists()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    summary = planning_summary(target=tmp_path)
    assert record["kind"] == "planning-execplan/v1"
    assert record["context_budget"]["tiny resumability note"] == "promote the work item."
    assert "[active]" in state_text
    assert "work_items = []" in state_text
    assert 'path = ".agentic-workspace/planning/execplans/work-item.plan.json"' in state_text
    assert "next_action" not in state_text
    assert summary["todo"]["active_items"][0]["id"] == "work-item"
    assert summary["execplans"]["active_count"] == 1
    assert summary["work_maturity"]["active_execplans"][0]["source_bucket"] == "active.execplans"
    assert summary["planning_record"]["status"] == "present"
    assert summary["follow_through_contract"]["status"] == "present"
    assert summary["intent_interpretation_contract"]["status"] == "present"
    assert summary["context_budget_contract"]["status"] == "present"
    assert summary["context_budget_contract"]["tiny_resumability_note"] == "promote the work item."
    assert summary["execution_run_contract"]["status"] == "present"
    assert summary["finished_run_review_contract"]["status"] == "present"
    assert any(action.kind == "created" and action.path == record_path for action in result.actions)


def test_promote_todo_item_to_execplan_supports_roadmap_lane_state(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[active]
execplans = []

[roadmap]
lanes = [
  { type = "lane", id = "safer-promotion", maturity = "candidate", status = "next", priority = "P1", refs = "GitHub #700", title = "Safer promotion", outcome = "Promotion uses a command instead of hand-authored state.", reason = "Manual active state is easy to get subtly wrong.", promotion_signal = "Promote before broad work.", suggested_first_slice = "Add a command path." },
]
candidates = []
""",
    )

    result = promote_todo_item_to_execplan("safer-promotion", target=tmp_path)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "safer-promotion.plan.json"

    assert record_path.exists()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))
    summary = planning_summary(target=tmp_path)
    assert record["context_budget"]["tiny resumability note"] == "Add a command path."
    assert record["delegated_judgment"]["requested outcome"] == "Manual active state is easy to get subtly wrong."
    assert state["roadmap"]["lanes"] == []
    assert state["active"]["execplans"][0]["id"] == "safer-promotion"
    assert state["active"]["execplans"][0]["path"] == ".agentic-workspace/planning/execplans/safer-promotion.plan.json"
    assert state["active"]["execplans"][0]["maturity"] == "active"
    assert state["active"]["execplans"][0]["status"] == "active"
    assert summary["planning_record"]["status"] == "present"
    assert any(action.kind == "created" and action.path == record_path for action in result.actions)


def test_promote_to_plan_supports_decomposition_lane(tmp_path: Path) -> None:
    decomposition_path = tmp_path / ".agentic-workspace" / "planning" / "decompositions" / "dogfood.decomposition.json"
    decomposition_path.parent.mkdir(parents=True, exist_ok=True)
    decomposition_path.write_text(
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Dogfood planning safety",
                "status": "ready-for-lane-promotion",
                "larger_intended_outcome": "Prevent broad work from bypassing planning.",
                "parent_acceptance": {
                    "original_intent": "Prevent broad work from bypassing planning.",
                    "acceptance_target": "Broad work keeps parent acceptance, residual intent, and proof boundary visible across slices.",
                    "parent_proof_required": "Focused workspace and Planning tests prove parent acceptance is preserved.",
                    "residual_intent_rule": "Promoted lanes must name residual parent intent before closeout.",
                    "clarification_needed_when": "A child slice would otherwise claim parent completion from local proof.",
                },
                "non_goals": [],
                "candidate_lanes": [
                    {
                        "id": "safety-slice",
                        "title": "Safety slice",
                        "readiness": "ready",
                        "outcome": "Represent JSON/text planning behavior in schema-valid promoted work.",
                        "owner_surface": "",
                        "proof": "Focused workspace tests pass.",
                        "slice_contribution_to_parent": "Adds schema-valid promoted work behavior.",
                        "residual_parent_intent": "runtime closeout proof remains.",
                        "parent_proof_boundary": "slice-only",
                        "human_confirmation_needed": ["maintainer accepts parent closure proof before closing parent"],
                        "depends_on": [],
                        "parallel_with": [],
                    }
                ],
                "dependency_assumptions": [],
                "parallelization_assumptions": [],
                "proof_expectations": ["Focused workspace tests pass."],
                "promotion_rule": "Promote ready lanes only.",
                "references": [],
                "notes": "",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = promote_todo_item_to_execplan("safety-slice", target=tmp_path)

    assert [action.kind for action in result.actions] == ["created", "updated", "updated", "proof", "proof"]
    assert any("summary --target . --format json" in action.detail for action in result.actions if action.kind == "proof")
    assert any("doctor --target . --modules planning --format json" in action.detail for action in result.actions if action.kind == "proof")
    state = tomllib.loads((tmp_path / ".agentic-workspace" / "planning" / "state.toml").read_text(encoding="utf-8"))
    active = state["todo"]["active_items"][0]
    assert active["id"] == "safety-slice"
    assert active["surface"] == ".agentic-workspace/planning/execplans/safety-slice.plan.json"

    plan = json.loads((tmp_path / ".agentic-workspace" / "planning" / "execplans" / "safety-slice.plan.json").read_text(encoding="utf-8"))
    assert "JSON/text" in plan["canonical_core"]["next_action"]
    assert plan["parent_acceptance"]["original_intent"] == "Prevent broad work from bypassing planning."
    assert plan["parent_acceptance"]["current_slice"] == "Represent JSON/text planning behavior in schema-valid promoted work."
    assert plan["parent_acceptance"]["residual_parent_intent"] == "runtime closeout proof remains."
    assert plan["parent_acceptance"]["proof_boundary"] == "slice-only"
    assert plan["intent_continuity"]["this slice completes the larger intended outcome"] == "no"
    assert plan["required_continuation"]["required follow-on for the larger intended outcome"] == "yes"

    decomposition = json.loads(decomposition_path.read_text(encoding="utf-8"))
    schema_path = (
        _Path(__file__).resolve().parents[1]
        / "bootstrap"
        / ".agentic-workspace"
        / "planning"
        / "schemas"
        / "planning-decomposition.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema_errors = sorted(Draft202012Validator(schema).iter_errors(decomposition), key=lambda error: list(error.path))
    assert [error.message for error in schema_errors] == []
    lane = decomposition["candidate_lanes"][0]
    assert lane["readiness"] == "promoted"
    assert lane["owner_surface"] == ".agentic-workspace/planning/execplans/safety-slice.plan.json"
    assert "promoted_execplan" not in lane
    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]
    assert not any(
        warning["warning_class"] == "execplan_missing_file_reference" and "JSON/text" in warning["message"] for warning in warnings
    )


def test_planning_summary_validates_planning_state_v1_maturity_contract(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json", why_now = "prove active maturity points to an execplan." },
]
queued_items = [
  { id = "ready-slice", maturity = "ready", status = "next", refs = ["#497"], owner_role = "implementation", review_role = "validation", handoff_ready = true, next_action = "implement schema validation.", done_when = "tests prove required fields.", proof = ["uv run pytest packages/planning/tests/test_installer.py -q"] },
]

[roadmap]
lanes = [
  { id = "maturity-lane", maturity = "shaped", status = "deferred", title = "Maturity lane", issues = ["#496"], outcome = "explicit maturity", reason = "avoid bucket inference", promotion_signal = "select a ready slice" },
]
candidates = []
""",
    )
    _write_execplan_record(
        tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json",
        item_id="active-plan",
        status="in-progress",
    )

    summary = planning_summary(target=tmp_path)

    assert summary["planning_surface_health"]["status"] == "clean"
    assert summary["warning_count"] == 0


def test_planning_summary_warns_for_invalid_planning_state_v1_maturity_contract(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-without-plan", maturity = "active", status = "active", surface = "direct" },
]
queued_items = [
  { id = "ready-missing-proof", maturity = "ready", status = "next", owner_role = ["implementation"], handoff_ready = "yes", next_action = "do work.", done_when = "done." },
]

[roadmap]
lanes = [
  { id = "bad-maturity", maturity = "someday", status = "later", title = "Bad maturity" },
]
candidates = [
  { id = "closed-without-residue", maturity = "closed", status = "done" },
]
""",
    )

    summary = planning_summary(target=tmp_path)
    messages = [warning["message"] for warning in summary["planning_surface_health"]["warnings"]]
    historical_warning = next(
        warning
        for warning in summary["planning_surface_health"]["warnings"]
        if warning["warning_class"] == "historical_work_in_live_planning_state"
    )
    active_owner_warning = next(
        warning
        for warning in summary["planning_surface_health"]["warnings"]
        if "active item active-without-plan requires an execplan" in warning["message"]
    )
    live_state_rule = summary["planning_surface_health"]["authoring_affordances"]["live_state_rule"]

    assert summary["planning_surface_health"]["status"] == "not-clean"
    assert any("active item active-without-plan requires an execplan" in message for message in messages)
    owner_repair = active_owner_warning["repair_affordance"]
    assert owner_repair["missing_owner"] == "execplan surface"
    assert owner_repair["expected_state_field"] == "execplan or surface"
    assert owner_repair["expected_shape"] == ".agentic-workspace/planning/execplans/<id>.plan.json"
    assert "new-plan --id active-without-plan" in owner_repair["command_owned_repair"]
    assert owner_repair["field_absent_after_closeout"] == "todo.active_items[] entry"
    assert any("ready item ready-missing-proof requires proof" in message for message in messages)
    assert any("ready item ready-missing-proof requires review_role" in message for message in messages)
    assert any("ready item ready-missing-proof requires handoff_ready = true" in message for message in messages)
    assert any("ready item ready-missing-proof requires refs, owner_role, or owner" in message for message in messages)
    assert any("ready-missing-proof owner_role must be a non-empty string" in message for message in messages)
    assert any("ready-missing-proof handoff_ready must be true or false" in message for message in messages)
    assert any("bad-maturity must use one maturity" in message for message in messages)
    assert any("closed-without-residue is completed, dismissed, closed, or historical work" in message for message in messages)
    assert "live/selectable state only" in live_state_rule
    assert historical_warning["suggested_fix"] == live_state_rule


def test_planning_summary_projects_explicit_work_maturity_buckets(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Active plan", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json", why_now = "active maturity owns execution.", handoff_ready = true },
]
queued_items = [
  { id = "ready-slice", title = "Ready slice", maturity = "ready", status = "next", refs = ["#499"], owner_role = "implementation", review_role = "validation", handoff_ready = true, next_action = "implement ready slice.", done_when = "ready slice done.", proof = ["uv run pytest tests/test_installer.py"], adaptive_assurance = { level = "high", proof_profiles = ["access_control"], required_refs = ["security_refs"] }, traceability_refs = { security_refs = ["SEC-1"] }, control_gates = [{ id = "security-review", status = "pending", blocking = true }] },
  { id = "shape-candidate", title = "Shape candidate", maturity = "candidate", status = "next", next_action = "shape the candidate." },
  { id = "blocked-ready", title = "Blocked ready", maturity = "ready", status = "blocked", owner_role = "implementation", review_role = "validation", handoff_ready = true, next_action = "unblock.", done_when = "unblocked.", proof = ["manual proof"] },
]

[roadmap]
lanes = [
  { id = "deferred-lane", title = "Deferred lane", maturity = "shaped", status = "deferred", issues = ["#496"], outcome = "later.", reason = "not now.", promotion_signal = "later." },
]
candidates = []
""",
    )
    _write_execplan_record(
        tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json",
        item_id="active-plan",
        status="in-progress",
    )

    summary = planning_summary(target=tmp_path)
    compact = planning_summary(target=tmp_path, profile="compact")
    report = planning_report(target=tmp_path)

    work_maturity = summary["work_maturity"]
    assert work_maturity["status"] == "active"
    assert work_maturity["active_execplans"][0]["id"] == "active-plan"
    assert work_maturity["active_execplans"][0]["source_bucket"] == "todo.active_items"
    assert work_maturity["ready_slices"][0]["id"] == "ready-slice"
    assert work_maturity["ready_slices"][0]["adaptive_assurance"]["level"] == "high"
    assert work_maturity["ready_slices"][0]["traceability_refs"]["security_refs"] == ["SEC-1"]
    assert work_maturity["ready_slices"][0]["control_gates"][0]["id"] == "security-review"
    assert work_maturity["needs_shaping"][0]["id"] == "shape-candidate"
    assert work_maturity["deferred_lanes"][0]["id"] == "deferred-lane"
    assert work_maturity["blocked_items"][0]["id"] == "blocked-ready"
    assert work_maturity["counts"] == {
        "active_execplans": 1,
        "ready_slices": 1,
        "needs_shaping": 1,
        "deferred_lanes": 1,
        "blocked_items": 1,
        "closed_items": 0,
        "residue_routing_needed": 0,
    }
    assert compact["work_maturity"]["ready_slices"][0]["id"] == "ready-slice"
    assert report["work_maturity"]["blocked_items"][0]["id"] == "blocked-ready"
    assert report["status"]["ready_slice_count"] == 1


def test_planning_summary_uses_work_items_state_shape(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = [
  { id = "ready-slice", type = "slice", title = "Ready slice", maturity = "ready", status = "next", refs = ["#500"], owner_role = "implementation", review_role = "validation", handoff_ready = true, next_action = "implement ready slice.", done_when = "ready slice done.", proof = ["uv run pytest tests/test_installer.py"] },
  { id = "maturity-lane", type = "lane", title = "Maturity lane", maturity = "shaped", status = "deferred", issues = ["#496"], outcome = "later.", reason = "not now.", promotion_signal = "later.", suggested_first_slice = "#501" },
]

[active]
execplans = [
  { id = "active-plan", title = "Active plan", maturity = "active", status = "active", path = ".agentic-workspace/planning/execplans/active-plan.plan.json", why_now = "active maturity owns execution.", handoff_ready = true },
]
""",
    )
    _write_execplan_record(
        tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json",
        item_id="active-plan",
        status="in-progress",
    )

    summary = planning_summary(target=tmp_path)
    report = planning_report(target=tmp_path)

    assert summary["todo"]["active_items"][0]["id"] == "active-plan"
    assert summary["todo"]["queued_items"][0]["id"] == "ready-slice"
    assert summary["roadmap"]["lane_count"] == 1
    assert summary["roadmap"]["candidate_count"] == 0
    assert summary["roadmap"]["candidates"] == []
    assert summary["roadmap"]["candidate_lanes"][0]["id"] == "maturity-lane"
    assert summary["work_maturity"]["active_execplans"][0]["source_bucket"] == "active.execplans"
    assert summary["work_maturity"]["ready_slices"][0]["id"] == "ready-slice"
    assert summary["work_maturity"]["deferred_lanes"][0]["id"] == "maturity-lane"
    assert report["status"]["ready_slice_count"] == 1


def test_promote_todo_item_to_execplan_accepts_bom_prefixed_compact_toml(tmp_path: Path) -> None:
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_bytes(
        b"\xef\xbb\xbf"
        + b"""
[todo]
active_items = [
  { id = "bom-compact", status = "in-progress", surface = "direct", why_now = "Windows-authored TOML should still be parsed." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
"""
    )

    result = promote_todo_item_to_execplan("bom-compact", target=tmp_path)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "bom-compact.plan.json"

    assert record_path.exists()
    assert any(action.kind == "created" and action.path == record_path for action in result.actions)


def test_promote_todo_item_to_execplan_refuses_existing_execplan_surface(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: this item is already routed through an execplan.
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    result = promote_todo_item_to_execplan("plan-alpha", target=tmp_path)

    assert any(action.kind == "manual review" and "already points at" in action.detail for action in result.actions)


def test_promote_todo_item_to_execplan_refuses_existing_compact_execplan_surface(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", why_now = "this item is already routed through an execplan." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_execplan_record(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json",
        status="in-progress",
    )

    result = promote_todo_item_to_execplan("plan-alpha", target=tmp_path)

    assert any(action.kind == "manual review" and "already points at" in action.detail for action in result.actions)


def test_promote_todo_item_to_execplan_creates_missing_compact_execplan_surface(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "active", path = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", why_now = "this item is active but the plan was not created yet.", next_action = "create the plan." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    result = promote_todo_item_to_execplan("plan-alpha", target=tmp_path)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"

    assert record_path.exists()
    assert any(action.kind == "created" and action.path == record_path for action in result.actions)
    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))
    item = state["todo"]["active_items"][0]
    assert item["path"] == ".agentic-workspace/planning/execplans/plan-alpha.plan.json"
    assert item["surface"] == ".agentic-workspace/planning/execplans/plan-alpha.plan.json"
    assert "next_action" not in item


def test_planning_cli_dogfoods_compact_state_for_summary_promote_and_archive(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "compact-cli", status = "in-progress", surface = "direct", why_now = "prove package commands use compact state.", next_action = "promote through the CLI.", done_when = "archive through the CLI." },
]
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1883-workspace-provide-bounded-chat-agent-output-prof", maturity = "candidate", status = "next", priority = "P2", refs = "GitHub #1883", title = "[Workspace]: Provide bounded chat-agent output profiles for ordinary AW routing", outcome = "Route the upstream issue into a bounded Agentic Workspace slice before implementation.", reason = "Open prioritized upstream issue from refreshed external intent evidence.", promotion_signal = "Promote when this issue is selected for implementation or grouped into a bounded lane.", suggested_first_slice = "Inspect the issue body, choose the smallest workflow shape, and record exact proof before closeout." },
]
""",
    )

    assert planning_cli.main(["summary", "--target", str(tmp_path), "--format", "json"]) == 0
    summary_payload = json.loads(capsys.readouterr().out)
    assert summary_payload["todo"]["active_items"][0]["id"] == "compact-cli"
    assert summary_payload["execution_readiness"]["status"] == "active-item-without-execplan"

    assert planning_cli.main(["promote-to-plan", "compact-cli", "--target", str(tmp_path), "--format", "json"]) == 0
    promote_payload = json.loads(capsys.readouterr().out)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "compact-cli.plan.json"
    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert promote_payload["actions"][0]["kind"] == "created"
    assert record_path.exists()
    assert 'surface = ".agentic-workspace/planning/execplans/compact-cli.plan.json"' in state_text
    assert "next_action" not in state_text
    assert "done_when" not in state_text

    _write_execplan_record(record_path, item_id="compact-cli", status="completed")
    assert planning_cli.main(["archive-plan", "compact-cli", "--target", str(tmp_path), "--apply-cleanup", "--format", "json"]) == 0
    archive_payload = json.loads(capsys.readouterr().out)
    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert any(action["kind"] == "closed" and action["path"].endswith("compact-cli.plan.json") for action in archive_payload["actions"])
    assert any(action["kind"] == "closeout distillation" for action in archive_payload["actions"])
    assert not record_path.exists()
    assert "compact-cli" not in state_text
    state = tomllib.loads(state_text)
    assert state["roadmap"]["candidates"] == [
        {
            "id": "github-1883-workspace-provide-bounded-chat-agent-output-prof",
            "maturity": "candidate",
            "status": "next",
            "priority": "P2",
            "refs": "GitHub #1883",
            "title": "[Workspace]: Provide bounded chat-agent output profiles for ordinary AW routing",
            "outcome": "Route the upstream issue into a bounded Agentic Workspace slice before implementation.",
            "reason": "Open prioritized upstream issue from refreshed external intent evidence.",
            "promotion_signal": "Promote when this issue is selected for implementation or grouped into a bounded lane.",
            "suggested_first_slice": "Inspect the issue body, choose the smallest workflow shape, and record exact proof before closeout.",
        }
    ]


def test_archive_prepare_closeout_allows_direct_slice_scope(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "direct-slice.plan.json"
    _write_execplan_record(record_path, item_id="direct-slice", status="completed")

    result = archive_execplan(
        "direct-slice",
        target=tmp_path,
        prepare_closeout=True,
        dry_run=True,
        closure_decision="archive-and-close",
        intent_satisfied="yes",
    )

    assert not any(action.kind == "manual review" for action in result.actions)
    assert any(action.kind == "would update" and '"closeout scope": "slice"' in action.detail for action in result.actions)


def test_archive_prepare_closeout_blocks_lane_proxy_archive_and_close(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "generated-cli-proxy.plan.json"
    _write_execplan_record(record_path, item_id="generated-cli-proxy", status="completed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["intent_continuity"] = {
        "larger intended outcome": "Complete implementation-independent generated CLI behavior.",
        "this slice completes the larger intended outcome": "no",
        "continuation surface": ".agentic-workspace/planning/state.toml roadmap lane generated-cli-runtime",
    }
    record["required_continuation"] = {
        "required follow-on for the larger intended outcome": "yes",
        "owner surface": ".agentic-workspace/planning/state.toml roadmap lane generated-cli-runtime",
        "activation trigger": "continue generic runtime ownership after proxy validation",
    }
    installer_mod._write_execplan_record(record_path=record_path, record=record)

    result = archive_execplan(
        "generated-cli-proxy",
        target=tmp_path,
        prepare_closeout=True,
        dry_run=True,
        closure_decision="archive-and-close",
        intent_satisfied="yes",
    )

    assert any(warning["warning_class"] == "archive_larger_intent_proxy_closeout_blocked" for warning in result.warnings)
    assert any(action.kind == "manual review" for action in result.actions)


def test_archive_blocks_prefilled_lane_proxy_archive_and_close(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "generated-cli-proxy.plan.json"
    _write_execplan_record(record_path, item_id="generated-cli-proxy", status="completed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["intent_continuity"] = {
        "larger intended outcome": "Complete implementation-independent generated CLI behavior.",
        "this slice completes the larger intended outcome": "no",
        "continuation surface": ".agentic-workspace/planning/state.toml roadmap lane generated-cli-runtime",
    }
    record["required_continuation"] = {
        "required follow-on for the larger intended outcome": "yes",
        "owner surface": ".agentic-workspace/planning/state.toml roadmap lane generated-cli-runtime",
        "activation trigger": "continue generic runtime ownership after proxy validation",
    }
    record["closure_check"]["closeout scope"] = "lane"
    record["closure_check"]["larger-intent status"] = "closed"
    record["closure_check"]["closure decision"] = "archive-and-close"
    record["intent_satisfaction"]["was original intent fully satisfied?"] = "yes"
    record["intent_satisfaction"]["unsolved intent passed to"] = "none"
    installer_mod._write_execplan_record(record_path=record_path, record=record)

    result = archive_execplan("generated-cli-proxy", target=tmp_path, dry_run=True)

    assert any(warning["warning_class"] == "archive_larger_intent_proxy_closeout_blocked" for warning in result.warnings)
    assert any(action.kind == "manual review" for action in result.actions)


def test_planning_cli_new_plan_creates_valid_active_scaffold(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)

    assert (
        planning_cli.main(
            [
                "new-plan",
                "--id",
                "Plan Alpha",
                "--title",
                "Plan Alpha",
                "--source",
                "#666",
                "--target",
                str(tmp_path),
                "--activate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    assert payload["outcome"] == "applied"
    assert payload["mutation_applied"] is True
    assert payload["reason_code"] == "mutation-applied"
    assert payload["conflict_owner"] is None
    assert payload["recovery_command"] is None
    assert any(action["kind"] == "created" and action["path"].endswith("plan-alpha.plan.json") for action in payload["actions"])
    assert any(
        action["kind"] == "next" and "tighten scaffold fields" in action["detail"] and "adaptive_assurance" in action["detail"]
        for action in payload["actions"]
    )
    assert record_path.exists()
    assert not installer_mod.planning_record_schema_findings(record_path)

    summary = planning_summary(target=tmp_path, profile="compact")
    assert summary["todo"]["active_items"][0]["id"] == "plan-alpha"
    assert summary["execplans"]["active_execplans"][0]["path"].endswith("plan-alpha.plan.json")


def test_planning_cli_new_plan_queue_creates_schema_clean_ready_item(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)

    assert (
        planning_cli.main(
            [
                "new-plan",
                "--id",
                "Queued Protocol",
                "--title",
                "Queued Protocol",
                "--source",
                "#1198",
                "--target",
                str(tmp_path),
                "--queue",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    summary = planning_summary(target=tmp_path, profile="compact")
    queued_item = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))["todo"]["queued_items"][
        0
    ]
    assert queued_item["id"] == "queued-protocol"
    assert queued_item["maturity"] == "ready"
    assert queued_item["status"] == "next"
    assert queued_item["owner_role"] == "implementation"
    assert queued_item["review_role"] == "validation"
    assert queued_item["handoff_ready"] is True
    assert queued_item["next_action"].startswith("Tighten scaffold fields")
    assert queued_item["done_when"] == "Queued Protocol is implemented, validated, and closed out honestly."
    assert "implement --changed" in queued_item["proof"]
    assert summary["planning_surface_health"]["status"] == "clean"


def test_archive_prepare_closeout_routes_improvement_signal_review_states(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    record_path = tmp_path / ".agentic-workspace/planning/execplans/signal-closeout.plan.json"
    _write_execplan_record(record_path, item_id="signal-closeout", status="completed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["execution_summary"]["knowledge promoted (Memory/Docs/Config)"] = "none"
    record["improvement_signal_review"] = {
        "status": "signals_routed",
        "signals found": [{"summary": "PR review comments need behavior-level dogfooding evidence.", "owner": "issue"}],
        "signals routed": [
            {"summary": "Create follow-up issue for repeated review evidence gaps.", "owner": "issue"},
            {"summary": "Capture reusable dogfooding routing lesson.", "owner": "Memory"},
            {"summary": "Document closeout reflection routing examples.", "owner": "docs/checks/contracts"},
        ],
        "signals dismissed": [
            {"summary": "One-off local terminal timeout after a deliberately broad suite.", "owner": "dismissed with reason"}
        ],
    }
    _write(record_path, json.dumps(record, indent=2) + "\n")

    assert (
        planning_cli.main(
            [
                "archive-plan",
                "signal-closeout",
                "--target",
                str(tmp_path),
                "--prepare-closeout",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    details = [action["detail"] for action in payload["actions"]]
    patch_detail = next(detail for detail in details if detail.startswith("prepared closeout patch: "))
    closeout_patch = json.loads(patch_detail.removeprefix("prepared closeout patch: "))
    buckets = closeout_patch["closeout_distillation"]["buckets"]
    assert {
        "summary": "Create follow-up issue for repeated review evidence gaps.",
        "source": "improvement_signal_review.signals routed",
        "owner": "issue",
    } in buckets["issue_follow_up"]
    assert {
        "summary": "Capture reusable dogfooding routing lesson.",
        "source": "improvement_signal_review.signals routed",
        "owner": "Memory",
    } in buckets["memory"]
    assert {
        "summary": "Document closeout reflection routing examples.",
        "source": "improvement_signal_review.signals routed",
        "owner": "docs/checks/contracts",
    } in buckets["docs"]
    assert {
        "summary": "One-off local terminal timeout after a deliberately broad suite.",
        "source": "improvement_signal_review.signals dismissed",
        "owner": "dismissed with reason",
    } in buckets["discard"]

    record["improvement_signal_review"] = {
        "status": "no_signal_found",
        "signals found": [],
        "signals routed": [],
        "signals dismissed": [],
    }
    _write(record_path, json.dumps(record, indent=2) + "\n")

    assert (
        planning_cli.main(
            [
                "archive-plan",
                "signal-closeout",
                "--target",
                str(tmp_path),
                "--prepare-closeout",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    details = [action["detail"] for action in payload["actions"]]
    patch_detail = next(detail for detail in details if detail.startswith("prepared closeout patch: "))
    closeout_patch = json.loads(patch_detail.removeprefix("prepared closeout patch: "))
    buckets = closeout_patch["closeout_distillation"]["buckets"]
    assert {
        "summary": "Improvement signal review was checked and no signal was found.",
        "source": "improvement_signal_review.status",
        "owner": "none",
    } in buckets["discard"]


def test_planning_cli_new_plan_activate_refuses_implicit_active_switch(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "current-plan", title = "Current Plan", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/current-plan.plan.json", why_now = "Already active." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    assert (
        planning_cli.main(
            [
                "new-plan",
                "--id",
                "Next Plan",
                "--title",
                "Next Plan",
                "--target",
                str(tmp_path),
                "--activate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert any(action["kind"] == "manual review" and "--switch-active" in action["detail"] for action in payload["actions"])
    summary = planning_summary(target=tmp_path, profile="compact")
    assert [item["id"] for item in summary["todo"]["active_items"]] == ["current-plan"]


def test_planning_cli_new_plan_switch_active_demotes_existing_active_items(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    current_record_path = tmp_path / ".agentic-workspace/planning/execplans/current-plan.plan.json"
    _write_execplan_record(current_record_path, item_id="current-plan", status="active")
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "current-plan", title = "Current Plan", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/current-plan.plan.json", why_now = "Already active." },
]
queued_items = [
  { id = "queued-plan", title = "Queued Plan", maturity = "ready", status = "next", surface = ".agentic-workspace/planning/execplans/queued-plan.plan.json", why_now = "Already queued." },
]

[roadmap]
lanes = []
candidates = []
""",
    )

    assert (
        planning_cli.main(
            [
                "new-plan",
                "--id",
                "Next Plan",
                "--title",
                "Next Plan",
                "--source",
                "#896",
                "--target",
                str(tmp_path),
                "--activate",
                "--switch-active",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))
    current_record = installer_mod._load_execplan_record(current_record_path)

    assert any(action["kind"] == "updated" and "active_items" in action["detail"] for action in payload["actions"])
    assert any(action["kind"] == "updated" and action["path"].endswith("current-plan.plan.json") for action in payload["actions"])
    assert [item["id"] for item in state["todo"]["active_items"]] == ["next-plan"]
    assert [item["id"] for item in state["todo"]["queued_items"]] == ["current-plan", "queued-plan"]
    assert state["todo"]["queued_items"][0]["status"] == "next"
    assert state["todo"]["queued_items"][0]["maturity"] == "ready"
    assert state["todo"]["queued_items"][0]["switched_from_active_by"] == "next-plan"
    assert current_record["active_milestone"]["status"] == "planned"
    assert current_record["active_milestone"]["ready"] == "queued"
    assert current_record["active_milestone"]["switched_from_active_by"] == "next-plan"
    summary = planning_summary(target=tmp_path, profile="compact")
    assert summary["planning_surface_health"]["warning_count"] == 0
    assert summary["execplans"]["active_count"] == 1
    assert summary["execplans"]["active_execplans"][0]["path"].endswith("next-plan.plan.json")


def test_planning_cli_new_plan_prep_only_scopes_to_planning_surfaces(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    install_bootstrap(target=tmp_path)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "baseline", "-q"],
        cwd=tmp_path,
        check=True,
    )

    assert (
        planning_cli.main(
            [
                "new-plan",
                "--id",
                "Shop Prep",
                "--title",
                "Shop Prep",
                "--target",
                str(tmp_path),
                "--activate",
                "--prep-only",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "shop-prep.plan.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))

    assert any("--verbose --format json" in action["detail"] for action in payload["actions"] if action["kind"] == "next")
    assert any("prep-only route" in action["detail"] and "manual JSON tightening" in action["detail"] for action in payload["actions"])
    assert any("after summary verification, stop" in action["detail"] for action in payload["actions"] if action["kind"] == "next")
    assert record["immediate_next_action"] == [
        "Run agentic-workspace summary --target . --verbose --format json, confirm the planning state is clean, then stop without product scaffolding."
    ]
    assert record["machine_readable_contract"]["planning_mode"]["prep_only"] is True
    assert "task_intent_promotion" not in record
    assert record["machine_readable_contract"]["planning_mode"]["halt_after_summary"] is True
    assert "HALT: prep-only mode active" in record["machine_readable_contract"]["planning_mode"]["halt_instruction"]
    assert "Do not manually tighten" in record["machine_readable_contract"]["planning_mode"]["halt_instruction"]
    assert "PLANNING_STATE" in record["machine_readable_contract"]["planning_mode"]["halt_instruction"]
    assert record["machine_readable_contract"]["planning_mode"]["minimal_success_criteria"] == [
        "prep-only execplan registered in Planning state",
        "agentic-workspace summary --target . --verbose --format json exits successfully",
        "only canonical Planning surfaces changed",
    ]
    assert "defer during prep-only" in record["machine_readable_contract"]["planning_mode"]["manual_tightening_policy"]
    assert ".agentic-workspace/planning/state.toml" in record["machine_readable_contract"]["planning_mode"]["allowed_outputs"]
    assert "PLANNING_STATE" in record["machine_readable_contract"]["planning_mode"]["forbidden_outputs"]
    assert "src" in record["machine_readable_contract"]["planning_mode"]["forbidden_outputs"]
    assert record["control_gates"][0]["id"] == "prep-only-halt"
    assert record["control_gates"][0]["blocking"] is True
    assert record["control_gates"][0]["evidence"] == ["agentic-workspace summary --target . --verbose --format json"]
    assert record["execution_bounds"]["stop before touching"].startswith("README, PLANNING_STATE, HANDOFF, SLICES")
    assert "src/" in record["execution_bounds"]["stop before touching"]
    assert record["execution_bounds"]["required validation commands"] == "agentic-workspace summary --target . --verbose --format json"
    assert "ad hoc JSON validation loops" in record["execution_bounds"]["manual JSON validation"]
    assert record["touched_paths"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/",
        ".agentic-workspace/planning/decompositions/",
    ]
    assert not installer_mod.planning_record_schema_findings(record_path)

    summary = planning_summary(target=tmp_path, profile="compact")
    assert summary["schema"]["profile"] == "compact-prep-only"
    assert summary["stop_now"]["do_not_open_execplan"] is True
    assert "handoff_contract" not in summary
    prep_only_contract = summary["planning_record"]["prep_only_contract"]
    assert prep_only_contract["is_prep_only"] is True
    assert prep_only_contract["halt_after_summary"] is True
    assert "HALT: prep-only mode active" in prep_only_contract["halt_instruction"]
    assert "src" in prep_only_contract["forbidden_outputs"]

    (tmp_path / "README.md").write_text("# Drift\n", encoding="utf-8")
    summary_with_drift = planning_summary(target=tmp_path, profile="compact")
    assert summary_with_drift["planning_surface_health"]["status"] == "not-clean"
    assert any(warning["warning_class"] == "prep_only_scope_violation" for warning in summary_with_drift["warnings"])


def test_planning_cli_new_plan_refuses_duplicate_without_overwrite(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.local.toml",
        '[workspace]\ncli_invoke = "uv run python scripts/run_agentic_workspace.py"\n',
    )
    args = [
        "new-plan",
        "--id",
        "Plan Alpha",
        "--title",
        "Plan Alpha",
        "--target",
        str(tmp_path),
        "--format",
        "json",
    ]

    assert planning_cli.main(args) == 0
    capsys.readouterr()
    assert planning_cli.main(args) == 0
    payload = json.loads(capsys.readouterr().out)

    assert any(action["kind"] == "manual review" and "already exists" in action["detail"] for action in payload["actions"])
    assert payload["outcome"] == "blocked"
    assert payload["mutation_applied"] is False
    assert payload["reason_code"] == "target-already-exists"
    assert payload["conflict_owner"] == ".agentic-workspace/planning/execplans/plan-alpha.plan.json"
    assert payload["recovery_command"].startswith("uv run python scripts/run_agentic_workspace.py planning new-plan ")
    assert '--id "plan-alpha"' in payload["recovery_command"]
    assert '--title "Plan Alpha"' in payload["recovery_command"]
    assert "--target . --overwrite --format json" in payload["recovery_command"]
    assert str(tmp_path) not in payload["recovery_command"]


def test_planning_summary_exposes_ordered_roadmap_batch_guidance(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "first-lane", title = "First lane", priority = "P0", issues = ["#1"], outcome = "First.", reason = "Needed first.", promotion_signal = "Start here.", suggested_first_slice = "Do first slice." },
  { id = "second-lane", title = "Second lane", priority = "P1", issues = ["#2"], outcome = "Second.", reason = "Needed second.", promotion_signal = "After first.", suggested_first_slice = "Do second slice." },
]
candidates = []
""",
    )

    summary = planning_summary(target=tmp_path, profile="compact")
    batch = summary["execution_readiness"]["ordered_batch"]

    assert summary["execution_readiness"]["status"] == "roadmap-needs-promotion"
    assert batch["status"] == "present"
    assert [item["id"] for item in batch["items"]] == ["first-lane", "second-lane"]
    assert batch["first_promotion_command"].endswith("promote-to-plan first-lane --target . --format json")
    assert summary["execution_readiness"]["recommendation"]["ordered_batch"]["items"][0]["issues"] == ["#1"]


def test_planning_summary_ordered_batch_uses_state_candidate_identity(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-824-typescript-weak-agent-safe-root", maturity = "candidate", status = "deferred", priority = "P2", refs = "GitHub #824", title = "Define weak-agent-safe promotion criteria for the root TypeScript adapter", promotion_signal = "Promote after read-only conformance is stable.", suggested_first_slice = "Add IR criteria and generated-package proof." },
]
""",
    )

    summary = planning_summary(target=tmp_path, profile="compact")
    batch = summary["execution_readiness"]["ordered_batch"]

    assert batch["status"] == "present"
    assert batch["items"][0]["id"] == "github-824-typescript-weak-agent-safe-root"
    assert batch["items"][0]["title"] == "Define weak-agent-safe promotion criteria for the root TypeScript adapter"
    assert batch["items"][0]["issues"] == ["#824"]
    assert batch["items"][0]["promotion_command"].endswith(
        "promote-to-plan github-824-typescript-weak-agent-safe-root --target . --format json"
    )


def test_promote_to_plan_replaces_generic_external_intent_with_issue_specific_outcome(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1687-specific-plan-intent", maturity = "candidate", status = "deferred", priority = "P1", refs = ["#1687"], title = "Promote external-intent candidates with issue-specific plan intent", outcome = "Route the upstream issue into a bounded Agentic Workspace slice before implementation.", reason = "Open prioritized upstream issue from refreshed external intent evidence.", promotion_signal = "Ready after issue review.", suggested_first_slice = "Implement the promotion-specific fallback." },
]
""",
    )

    assert (
        planning_cli.main(
            [
                "promote-to-plan",
                "github-1687-specific-plan-intent",
                "--target",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    record = json.loads(
        (tmp_path / ".agentic-workspace" / "planning" / "execplans" / "github-1687-specific-plan-intent.plan.json").read_text(
            encoding="utf-8"
        )
    )

    assert record["canonical_core"]["requested_outcome"] == (
        "Resolve #1687: Promote external-intent candidates with issue-specific plan intent."
    )
    assert "Open prioritized upstream issue" not in record["canonical_core"]["requested_outcome"]
    assert record["machine_readable_contract"]["intent"]["outcome"] == record["canonical_core"]["requested_outcome"]


def test_planning_summary_continuation_view_prefers_fresh_execplan_over_stale_todo(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/resume-lane.plan.json"
    record = installer_mod._build_execplan_record_from_todo_item(
        title="Resume Lane",
        item_id="resume-lane",
        status="active",
        why_now="Preserve the active intent.",
        next_action="Use the fresher execplan action.",
        done_when="The active intent is fully satisfied.",
    )
    record["proof_report"] = {
        "validation proof": "Passed current characterization proof.",
        "proof achieved now": "yes",
        'evidence for "proof achieved" state': "Current proof receipt.",
    }
    record["intent_satisfaction"] = {
        "original intent": "Preserve the active intent.",
        "was original intent fully satisfied?": "yes",
        "evidence of intent satisfaction": "Current proof receipt.",
        "unsolved intent passed to": "none",
    }
    record["completion_gate"] = {
        "kind": "agentic-workspace/completion-gate/v1",
        "status": "allowed",
        "active_intent_satisfied": True,
        "human_accepted_partial": False,
        "claim_level_requested": "full-intent-complete",
        "claim_level_allowed": "full-intent-complete",
        "required_next_action": "close-complete",
        "claim_authorization": {
            "allowed_claim_classes": ["full_intent_complete"],
            "blocked_claim_classes": [],
        },
    }
    _write(plan_path, json.dumps(record, indent=2))
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "resume-lane", title = "Resume Lane", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/resume-lane.plan.json", why_now = "Old todo projection.", next_action = "Stale todo action.", done_when = "Old todo done text.", proof = "Old todo proof." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    summary = planning_summary(target=tmp_path, profile="tiny")
    active_item = summary["todo"]["active_items"][0]
    view = summary["continuation_view"]

    assert active_item["next_action"] == "Use the fresher execplan action."
    assert active_item["projection_freshness"] == "superseded-state-field"
    assert active_item["projection_overrides"][0]["field"] == "next_action"
    assert active_item["projection_overrides"][0]["stale_value"] == "Stale todo action."
    assert summary["planning_surface_health"]["recommended_next_action"] == "Use the fresher execplan action."
    assert summary["execution_readiness"]["recommendation"]["summary"] == "Use the fresher execplan action."
    assert summary["current_execution_pressure"]["recommended_next_action"] == "Use the fresher execplan action."
    assert summary["decision_packet"]["next_action"] == "Use the fresher execplan action."
    assert view["answers"]["preserved_intent"] == "Preserve the active intent."
    assert view["answers"]["next_safe_action"] == "Use the fresher execplan action."
    assert view["resume_predicate"]["status"] == "pass"
    assert view["claim_boundary"]["claim_level_allowed"] == "full-intent-complete"
    assert view["proof_state"]["status"] == "present"
    assert view["stale_projections"][0]["field"] == "todo.active_items[0].next_action"
    assert view["stale_projections"][0]["stale_value"] == "Stale todo action."
    assert view["stale_projections"][0]["chosen_value"] == "Use the fresher execplan action."
    assert any(
        item["claim"] == "planning state projection" and item["freshness"] == "stale-projection" for item in view["source_freshness"]
    )
    assert "raw transcript material" in view["omitted_detail"]
    assert view["write_responsibility"]["summary_start"].startswith("summary/start render")


def test_planning_summary_continuation_view_routes_unsatisfied_intent_to_continuation(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/unfinished-lane.plan.json"
    record = installer_mod._build_execplan_record_from_todo_item(
        title="Unfinished Lane",
        item_id="unfinished-lane",
        status="active",
        why_now="Replace broad test structure.",
        next_action="Continue replacing the remaining tests.",
        done_when="Most existing tests are replaced by contract-owned conformance tests.",
    )
    record["proof_report"] = {
        "validation proof": "Partial proof only.",
        "proof achieved now": "yes",
        'evidence for "proof achieved" state': "One contract fixture.",
    }
    record["intent_satisfaction"] = {
        "original intent": "Replace broad test structure.",
        "was original intent fully satisfied?": "no",
        "evidence of intent satisfaction": "Only one conversion landed.",
        "unsolved intent passed to": "#follow-up",
    }
    record["required_continuation"] = {
        "required follow-on for the larger intended outcome": "yes",
        "owner surface": ".agentic-workspace/planning/execplans/unfinished-lane.plan.json",
        "activation trigger": "Continue current work.",
    }
    record["completion_gate"] = {
        "kind": "agentic-workspace/completion-gate/v1",
        "status": "continue-required",
        "active_intent_satisfied": False,
        "human_accepted_partial": False,
        "claim_level_requested": "full-intent-complete",
        "claim_level_allowed": "partial-progress",
        "required_next_action": "continue-current-work",
        "claim_authorization": {
            "allowed_claim_classes": ["partial_progress"],
            "blocked_claim_classes": ["full_intent_complete", "issue_closure"],
        },
    }
    _write(plan_path, json.dumps(record, indent=2))
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "unfinished-lane", title = "Unfinished Lane", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/unfinished-lane.plan.json", next_action = "Continue replacing the remaining tests.", done_when = "Replace tests.", proof = "Partial proof." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    summary = planning_summary(target=tmp_path, profile="compact")
    view = summary["continuation_view"]

    assert view["answers"]["claim_allowed"] == "partial-progress"
    assert view["resume_predicate"]["status"] == "continue-with-boundary"
    assert view["resume_predicate"]["required_next_action"] == "continue-current-work"
    assert view["claim_boundary"]["status"] == "continue-required"
    assert view["claim_boundary"]["active_intent_satisfied"] is False
    assert "full_intent_complete" in view["claim_boundary"]["blocked_claim_classes"]
    assert "blocked_claims" not in view["claim_boundary"]
    assert view["answers"]["next_safe_action"] == "Continue replacing the remaining tests."


def test_finished_work_inspection_treats_state_roadmap_owner_as_routed_continuation(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "capability-routing", title = "Capability routing", priority = "P0", issues = [], outcome = "Continue capability routing.", reason = "Parent continuation.", promotion_signal = "Continue when ready.", suggested_first_slice = "Next routing slice." },
]
candidates = []
""",
    )
    archive_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "partial.plan.json"
    _write_execplan_record(archive_path, item_id="partial", status="completed")
    record = json.loads(archive_path.read_text(encoding="utf-8"))
    record["intent_satisfaction"] = {
        "original intent": "Improve capability routing.",
        "was original intent fully satisfied?": "no",
        "evidence of intent satisfaction": "one bounded slice landed.",
        "unsolved intent passed to": ".agentic-workspace/planning/state.toml roadmap lane capability-routing",
    }
    record["closure_check"] = {
        "slice status": "bounded slice complete",
        "larger-intent status": "open",
        "closure decision": "archive-but-keep-lane-open",
        "why this decision is honest": "the parent remains open and is already routed to roadmap.",
        "evidence carried forward": ".agentic-workspace/planning/state.toml roadmap lane capability-routing",
        "reopen trigger": "promote capability-routing",
    }
    installer_mod._write_execplan_record(record_path=archive_path, record=record)

    summary = planning_summary(target=tmp_path, profile="compact")
    inspection = summary["finished_work_inspection_contract"]

    assert inspection["derived_follow_up_candidates"] == []
    assert inspection["counts"]["routed_continuation_count"] == 1
    assert "inspections" not in inspection
    full = planning_summary(target=tmp_path, profile="full")
    assert full["finished_work_inspection_contract"]["inspections"][0]["classification"] == "routed_partial"


def test_finished_work_inspection_rejects_schema_invalid_finished_work_evidence(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write_finished_work_evidence(
        tmp_path / ".agentic-workspace/planning/finished-work-evidence.json",
        items=[{"system": "manual", "id": "", "status": "open"}],
    )

    summary = planning_summary(target=tmp_path)

    evidence = summary["finished_work_inspection_contract"]["evidence"]
    assert evidence["status"] == "invalid"
    assert "schema validation failed" in evidence["reason"]
    assert any("items.0.id" in finding for finding in evidence["schema_findings"])


def test_finished_work_inspection_derives_reopeners_from_external_evidence(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    _write(
        archive_dir / "closed-lane.md",
        (
            "# Closed Lane\n\n"
            "## Intent Satisfaction\n\n"
            "- Was original intent fully satisfied?: yes\n\n"
            "## Closure Check\n\n"
            "- Closure decision: archive-and-close\n"
            "- Larger-intent status: closed\n\n"
            "Implemented #1.\n"
        ),
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#99",
                "title": "Reopened externally",
                "status": "open",
                "kind": "issue",
                "parent_id": "",
                "planning_residue_expected": "required",
                "reopens": ["#1"],
            }
        ],
    )

    summary = planning_summary(target=tmp_path)

    contract = summary["finished_work_inspection_contract"]
    assert contract["counts"]["likely_premature_closeout_count"] == 1
    assert contract["derived_follow_up_candidates"][0]["reopened_by"] == ["#99"]


def test_finished_work_inspection_uses_external_status_over_stale_sidecar(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    _write(
        archive_dir / "closed-lane.md",
        (
            "# Closed Lane\n\n"
            "## Intent Satisfaction\n\n"
            "- Was original intent fully satisfied?: yes\n\n"
            "## Closure Check\n\n"
            "- Closure decision: archive-and-close\n"
            "- Larger-intent status: closed\n\n"
            "Implemented #1.\n"
        ),
    )
    _write_finished_work_evidence(
        tmp_path / ".agentic-workspace/planning/finished-work-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#99",
                "title": "Stale sidecar title",
                "status": "open",
                "kind": "issue",
                "reopens": ["#1"],
            }
        ],
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#99",
                "title": "Source-owned title",
                "status": "closed",
                "kind": "issue",
                "parent_id": "",
                "planning_residue_expected": "required",
            }
        ],
    )

    summary = planning_summary(target=tmp_path)

    contract = summary["finished_work_inspection_contract"]
    assert contract["counts"]["likely_premature_closeout_count"] == 0
    assert contract["counts"]["derived_follow_up_candidate_count"] == 0
