from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from datetime import date
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from planning_test_support import *


def test_planning_record_schemas_validate_templates() -> None:
    payload = installer_mod.payload_root()

    assert installer_mod.planning_record_schema_findings(payload / ".agentic-workspace/planning/execplans/TEMPLATE.plan.json") == []
    assert installer_mod.planning_record_schema_findings(payload / ".agentic-workspace/planning/reviews/TEMPLATE.review.json") == []


def test_execplan_template_surfaces_archive_closeout_terminal_values() -> None:
    payload = installer_mod.payload_root()
    template = json.loads((payload / ".agentic-workspace/planning/execplans/TEMPLATE.plan.json").read_text(encoding="utf-8"))

    assert template["closure_check"]["slice status"] == "bounded slice complete"
    assert template["closure_check"]["larger-intent status"] == "closed"
    assert template["closure_check"]["closure decision"] == "archive-and-close"
    assert "accepted values" in template["closure_check"]
    assert "archive-but-keep-lane-open" in template["closure_check"]["accepted values"]
    assert "archive-plan <plan> --prepare-closeout" in template["closure_check"]["accepted values"]
    assert template["durable_residue"]["status"] == "none"
    assert template["task_intent_promotion"]["decision"] == "pending"
    assert "subsystem-intent" in template["task_intent_promotion"]["accepted values"]
    assert template["post_decomposition_delegation"]["status"] == "pending"
    assert "delegate-exploration" in template["post_decomposition_delegation"]["route candidates"]
    assert "actual friction" in template["delegation_outcome_feedback"]
    assert template["improvement_signal_review"]["status"] == "not_checked"
    assert "no_signal_found" in template["improvement_signal_review"]["accepted statuses"]
    assert template["improvement_signal_review"]["source"] == "operating_posture"
    assert "smoothness/helpfulness gaps" in template["improvement_signal_review"]["guidance"]
    assert "Memory" in template["improvement_signal_review"]["owner classes"]
    assert "dismissed with reason" in template["improvement_signal_review"]["owner classes"]
    assert template["improvement_signal_review"]["ordinary output cap"] == 3


def test_planning_record_schema_rejects_unknown_execplan_fields(tmp_path: Path) -> None:
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["surprise_machine_field"] = "not in the schema"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    findings = installer_mod.planning_record_schema_findings(record_path)

    assert any("surprise_machine_field" in finding for finding in findings)


def test_planning_record_schema_rejects_pending_durable_residue_status(tmp_path: Path) -> None:
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="completed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["durable_residue"]["status"] = "pending"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    findings = installer_mod.planning_record_schema_findings(record_path)

    assert any("durable_residue.status" in finding and "pending" in finding for finding in findings)


def test_planning_summary_does_not_treat_json_template_as_active_execplan(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/execplans/TEMPLATE.plan.json",
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "title": "Template",
                "goal": ["Template scaffold."],
                "non_goals": [],
                "active_milestone": {
                    "id": "template",
                    "status": "active",
                    "scope": "Template only.",
                    "ready": "ready",
                    "blocked": "none",
                },
                "validation_commands": [],
                "completion_criteria": [],
            }
        ),
    )

    summary = planning_summary(target=tmp_path)

    assert summary["execplans"]["active_count"] == 0


def test_planning_summary_exposes_low_collaboration_pressure(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", 'kind = "agentic-planning-state"\nschema_version = "planning-state/v1"\n')

    summary = planning_summary(target=tmp_path, profile="compact")

    pressure = summary["planning_surface_health"]["collaboration_pressure"]
    assert pressure["kind"] == "planning-collaboration-pressure/v1"
    assert pressure["status"] == "normal"
    assert pressure["risk"] == "low"
    assert pressure["metrics"]["state_line_count"] == 2


def test_planning_summary_flags_changed_shared_planning_surfaces(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/plan-alpha.plan.json"
    _write(
        state_path,
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "plan-alpha", title = "Plan Alpha", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", handoff_ready = true }
]
queued_items = []
""",
    )
    _write_execplan_record(plan_path, item_id="plan-alpha", status="in-progress")

    summary = planning_summary(target=tmp_path, profile="compact")

    pressure = summary["planning_surface_health"]["collaboration_pressure"]
    assert pressure["status"] == "attention"
    assert pressure["risk"] == "high"
    assert pressure["shared_state_changed"] is True
    assert ".agentic-workspace/planning/state.toml" in pressure["changed_shared_surfaces"]


def test_planning_summary_exposes_live_state_authoring_affordance_when_clean(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    summary = planning_summary(target=tmp_path)
    affordances = summary["planning_surface_health"]["authoring_affordances"]

    assert summary["planning_surface_health"]["status"] == "clean"
    assert "live/selectable state only" in affordances["live_state_rule"]
    assert "closed_work_item_scaffold" not in affordances
    assert "closed_work_item_rule" not in affordances


def test_planning_summary_exposes_residue_governance_review_routing(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    reviews_dir = tmp_path / ".agentic-workspace" / "planning" / "reviews"
    _write(
        reviews_dir / "2026-06-04-command-generation.review.json",
        json.dumps(
            {
                "kind": "planning-review/v1",
                "title": "Command generation seam review",
                "date": "2026-06-04",
                "classification": "extraction-seam",
                "findings": [
                    {
                        "title": "Non-AW fixture needed",
                        "summary": "Command generation needs a non-AW portability fixture.",
                    }
                ],
            },
            indent=2,
        ),
    )
    _write(
        reviews_dir / "2026-06-01-memory.review.json",
        json.dumps(
            {
                "kind": "planning-review/v1",
                "title": "Memory review",
                "date": "2026-06-01",
                "classification": "memory",
                "findings": [],
            },
            indent=2,
        ),
    )

    summary = planning_summary(target=tmp_path, profile="compact", task_text="command generation seam")

    residue = summary["residue_governance"]
    assert residue["status"] == "present"
    assert residue["matrix_class_count"] >= 6
    assert residue["review_routing"]["status"] == "matches"
    assert residue["review_routing"]["do_not_bulk_read"] is True
    assert residue["review_routing"]["read_first"][0] == ".agentic-workspace/planning/reviews/2026-06-04-command-generation.review.json"
    assert residue["review_routing"]["relevant_reviews"][0]["matched_tokens"]


def test_planning_tiny_summary_surfaces_recent_review_residue_without_bulk_reading(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    reviews_dir = tmp_path / ".agentic-workspace" / "planning" / "reviews"
    _write(
        reviews_dir / "2026-06-04-retention.review.json",
        json.dumps(
            {
                "kind": "planning-review/v1",
                "title": "Residue retention review",
                "date": "2026-06-04",
                "classification": "residue-governance",
                "findings": [],
            },
            indent=2,
        ),
    )

    summary = planning_summary(target=tmp_path, profile="tiny")

    residue = summary["residue_governance"]
    assert residue["review_count"] == 1
    assert residue["review_routing"]["status"] == "recent-only"
    assert residue["review_routing"]["read_first"] == [".agentic-workspace/planning/reviews/2026-06-04-retention.review.json"]


def test_planning_summary_projects_decomposition_records(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/decompositions/shop.decomposition.json",
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Shop build",
                "status": "ready-for-lane-promotion",
                "larger_intended_outcome": "Build the shop.",
                "non_goals": ["Do not implement everything in one lane."],
                "candidate_lanes": [
                    {
                        "id": "storefront",
                        "title": "Storefront",
                        "readiness": "ready",
                        "outcome": "Browsable storefront.",
                        "owner_surface": ".agentic-workspace/planning/execplans/storefront.plan.json",
                        "proof": "Build and smoke test.",
                        "depends_on": [],
                        "parallel_with": [],
                    }
                ],
                "dependency_assumptions": [],
                "parallelization_assumptions": [],
                "proof_expectations": ["Promoted lanes carry exact proof."],
                "promotion_rule": "Promote ready lanes only.",
                "references": [],
                "notes": "",
            },
            indent=2,
        ),
    )

    summary = planning_summary(target=tmp_path, profile="compact")

    assert summary["decomposition"]["status"] == "present"
    assert summary["decomposition"]["record_count"] == 1
    assert summary["decomposition"]["ready_lane_count"] == 1
    assert summary["decomposition"]["records"][0]["candidate_lanes"][0]["id"] == "storefront"


def test_planning_summary_warns_for_misplaced_decomposition_records(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / "planning/ecommerce-app-decomposition.json",
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Shop build",
                "status": "needs-shaping",
                "larger_intended_outcome": "Build the shop.",
                "non_goals": [],
                "candidate_lanes": [],
                "proof_expectations": [],
                "promotion_rule": "Promote ready lanes only.",
            },
            indent=2,
        ),
    )

    summary = planning_summary(target=tmp_path, profile="compact")

    warnings = summary["planning_surface_health"]["warnings"]
    assert summary["planning_surface_health"]["status"] == "not-clean"
    assert any(warning["warning_class"] == "planning_decomposition_artifact_misplaced" for warning in warnings)


def test_planning_summary_warns_for_freehand_planning_artifacts(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/documentation_cleanup_plan.json",
        json.dumps({"goal": ["Clean up docs later."], "completion_criteria": ["Future agent can continue."]}, indent=2),
    )

    summary = planning_summary(target=tmp_path, profile="compact")

    warnings = summary["planning_surface_health"]["warnings"]
    warning = next(warning for warning in warnings if warning["warning_class"] == "planning_artifact_freehand")
    assert "intake-artifact" in warning["suggested_fix"]
    assert summary["planning_surface_health"]["status"] == "not-clean"


def test_planning_summary_warns_for_noncanonical_records_directory(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/records/ecommerce-plan.json",
        json.dumps({"goal": ["Prepare ecommerce app."], "milestones": ["foundation"]}, indent=2),
    )

    summary = planning_summary(target=tmp_path, profile="compact")

    warnings = summary["planning_surface_health"]["warnings"]
    warning = next(warning for warning in warnings if warning["warning_class"] == "planning_artifact_freehand")
    assert "intake-artifact" in warning["message"]
    assert summary["planning_surface_health"]["status"] == "not-clean"


def test_planning_summary_warns_for_unregistered_live_execplan(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/execplans/orphan-lane.plan.json",
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "active_milestone": {
                    "status": "active",
                },
            },
            indent=2,
        ),
    )

    summary = planning_summary(target=tmp_path, profile="compact")

    warnings = summary["planning_surface_health"]["warnings"]
    warning = next(warning for warning in warnings if warning["warning_class"] == "execplan_unregistered")
    assert warning["path"] == ".agentic-workspace/planning/execplans/orphan-lane.plan.json"
    assert "new-plan" in warning["suggested_fix"]
    assert summary["planning_surface_health"]["status"] == "not-clean"


def test_planning_summary_treats_markdown_and_canonical_execplan_siblings_as_registered(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "plan-alpha", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/plan-alpha.md", why_now = "legacy markdown linkage remains accepted." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(tmp_path / ".agentic-workspace/planning/execplans/plan-alpha.md", _minimal_execplan())
    _write(
        tmp_path / ".agentic-workspace/planning/execplans/plan-alpha.plan.json",
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "active_milestone": {
                    "status": "active",
                },
            },
            indent=2,
        ),
    )

    summary = planning_summary(target=tmp_path, profile="compact")

    warnings = summary["planning_surface_health"]["warnings"]
    assert not any(warning["warning_class"] == "execplan_unregistered" for warning in warnings)


def test_planning_cli_create_review_writes_valid_review_record(tmp_path: Path, capsys) -> None:
    result = planning_cli.main(
        [
            "create-review",
            "Lane Closeout",
            "--title",
            "Lane Closeout",
            "--scope",
            "#372",
            "--classification",
            "closeout",
            "--target",
            str(tmp_path),
            "--format",
            "json",
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    today = date.today().isoformat()
    assert payload["message"] == f"Create review record '{today}-lane-closeout'"
    record_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / f"{today}-lane-closeout.review.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["kind"] == "planning-review/v1"
    assert record["title"] == "Lane Closeout"
    assert record["scope"] == ["#372"]
    assert record["classification"] == "closeout"
    assert record["retention"]["closeout shape"] == "shrink"
    assert "findings promoted" in record["retention"]["trigger"]
    assert record["review_mode"]["mode"] == "closeout"
    assert record["findings"] == []
    assert record["prose_templates"]["review_finding"]["field_map"]["Evidence"] == "findings[].evidence + findings[].source"
    assert record["prose_templates"]["handoff_or_closeout"]["sections"][-1] == "Next owner"
    assert installer_mod.planning_record_schema_findings(record_path) == []
    assert payload["actions"][0]["kind"] == "created"


def test_planning_record_writers_reject_invalid_schema_shapes(tmp_path: Path) -> None:
    execplan = installer_mod._build_execplan_record_from_todo_item(
        title="Bad Plan",
        item_id="bad-plan",
        status="in-progress",
        why_now="prove writer validation.",
        next_action="attempt invalid write.",
        done_when="writer refuses malformed records.",
    )
    execplan["unexpected"] = "not allowed"
    with pytest.raises(ValueError, match="planning-execplan.schema.json"):
        installer_mod._write_execplan_record(
            record_path=tmp_path / ".agentic-workspace/planning/execplans/bad-plan.plan.json",
            record=execplan,
        )

    review = installer_mod._new_review_record(title="Bad Review", scope="review", classification="review")
    review["unexpected"] = "not allowed"
    with pytest.raises(ValueError, match="planning-review.schema.json"):
        installer_mod._write_review_record(
            record_path=tmp_path / ".agentic-workspace/planning/reviews/bad-review.review.json",
            record=review,
        )

    assert not (tmp_path / ".agentic-workspace/planning/execplans/bad-plan.plan.json").exists()
    assert not (tmp_path / ".agentic-workspace/planning/reviews/bad-review.review.json").exists()


def test_planning_cli_create_review_dry_run_does_not_write(tmp_path: Path, capsys) -> None:
    result = planning_cli.main(
        [
            "create-review",
            "future-review",
            "--title",
            "Future Review",
            "--target",
            str(tmp_path),
            "--dry-run",
            "--format",
            "json",
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["actions"][0]["kind"] == "would create"
    today = date.today().isoformat()
    assert not (tmp_path / ".agentic-workspace" / "planning" / "reviews" / f"{today}-future-review.review.json").exists()


def test_planning_cli_create_review_preserves_date_prefixed_slug(tmp_path: Path, capsys) -> None:
    today = date.today().isoformat()
    result = planning_cli.main(
        [
            "create-review",
            f"{today}-future-review",
            "--title",
            "Future Review",
            "--target",
            str(tmp_path),
            "--format",
            "json",
        ]
    )

    assert result == 0
    capsys.readouterr()
    assert (tmp_path / ".agentic-workspace" / "planning" / "reviews" / f"{today}-future-review.review.json").exists()


def test_planning_tiny_summary_uses_fast_path_without_checker(tmp_path: Path, monkeypatch) -> None:
    install_bootstrap(target=tmp_path)

    def fail_checker(_target_root: Path) -> list[dict[str, object]]:
        raise AssertionError("tiny summary should not run the full planning checker")

    monkeypatch.setattr(installer_mod, "_run_planning_checker", fail_checker)

    summary = planning_summary(target=tmp_path, profile="tiny")

    assert summary["profile"] == "tiny"
    assert summary["planning_surface_health"]["status"] == "clean"


def test_planning_tiny_report_uses_fast_summary_path(tmp_path: Path, monkeypatch) -> None:
    install_bootstrap(target=tmp_path)

    def fail_checker(_target_root: Path) -> list[dict[str, object]]:
        raise AssertionError("tiny report should not run the full planning checker")

    monkeypatch.setattr(installer_mod, "_run_planning_checker", fail_checker)

    report = installer_mod.planning_report_tiny(target=tmp_path)

    assert report["kind"] == "planning-module-report/v1"
    assert report["profile"] == "tiny"
    assert set(report) <= {
        "kind",
        "profile",
        "module",
        "target_root",
        "health",
        "status",
        "active",
        "finding_count",
        "findings",
        "next_action",
        "residue_governance",
        "detail_commands",
    }
    assert report["status"]["active_todo_count"] == 0


def test_planning_summary_prefers_canonical_execplan_record_when_markdown_stales(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: keep the canonical sidecar authoritative.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="in-progress")

    summary = planning_summary(target=tmp_path)

    assert summary["planning_record"]["requested_outcome"] == "this item needs a bounded execution contract."
    assert summary["planning_record"]["next_action"] == "add one checker."
    assert summary["planning_record"]["task"]["surface"] == ".agentic-workspace/planning/execplans/plan-alpha.md"
    assert summary["planning_record"]["system_intent_alignment"]["relevant system intent"] == (
        "Preserve larger user or product outcome separately from the bounded slice."
    )
    assert summary["machine_first_planning"]["status"] == "canonical-active"
    assert summary["machine_first_planning"]["active_canonical_count"] == 1
    assert summary["machine_first_planning"]["active_markdown_fallback_count"] == 0
    assert summary["machine_first_planning"]["canonical_active_execplans"] == [".agentic-workspace/planning/execplans/plan-alpha.plan.json"]


def test_planning_summary_prefers_execplan_canonical_core_and_warns_on_projection_drift(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "plan-alpha", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json" },
]
queued_items = []
""",
    )
    record_path = tmp_path / ".agentic-workspace/planning/execplans/plan-alpha.plan.json"
    _write_execplan_record(record_path, item_id="plan-alpha", status="in-progress")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["canonical_core"]["next_action"] = "Use the canonical core."
    record["canonical_core"]["proof_expectations"] = ["uv run pytest canonical.py"]
    record["canonical_core"]["completion_criteria"] = ["Canonical core wins."]
    record["immediate_next_action"] = ["Legacy next action."]
    record["validation_commands"] = ["uv run pytest legacy.py"]
    installer_mod._write_execplan_record(record_path=record_path, record=record)

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]

    assert summary["planning_record"]["next_action"] == "Use the canonical core."
    assert summary["planning_record"]["proof_expectations"] == ["uv run pytest canonical.py"]
    assert summary["resumable_contract"]["completion_criteria"] == ["Canonical core wins."]
    assert summary["resumable_contract"]["current_next_action_source"] == "canonical_core.next_action"
    assert any(warning["warning_class"] == "execplan_canonical_projection_drift" for warning in warnings)


def test_upgrade_backfills_canonical_review_records(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    review_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "review-alpha.md"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        """
# Review Alpha

## Goal

- Check one narrow planning boundary.

## Scope

- `.agentic-workspace/planning/reviews/`

## Non-Goals

- No implementation work.

## Review Mode

- Mode: review-promotion
- Review question: should this review stay live?
- Default finding cap: 2
- Inputs inspected first: reviews README

## Review Method

- Commands used: uv run pytest packages/planning/tests/test_installer.py -q
- Evidence sources: local review artifact

## Findings

### Finding: stale residue

- Summary: the review should shrink after promotion.
- Evidence: the artifact is no longer the only durable owner.
- Risk if unchanged: review residue grows into a parallel archive.
- Suggested action: move durable residue into a structured record.
- Confidence: high
- Source: static-analysis
- Promotion target: `.agentic-workspace/planning/state.toml (roadmap)`
- Promotion trigger: when the finding is confirmed
- Post-remediation note shape: shrink

## Recommendation

- Promote: yes
- Defer: no
- Dismiss: no

## Validation / Inspection Commands

- uv run pytest packages/planning/tests/test_installer.py -q

## Drift Log

- 2026-04-23: Review created.
""".strip()
        + "\n",
        encoding="utf-8",
    )

    upgrade_bootstrap(target=tmp_path)

    record_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "review-alpha.review.json"
    assert record_path.exists()
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    assert payload["kind"] == "planning-review/v1"
    assert payload["title"] == "Review Alpha"
    assert payload["review_mode"]["mode"] == "review-promotion"
    assert payload["findings"][0]["title"] == "stale residue"
    assert payload["retention"]["closeout shape"] == "shrink"


def test_planning_summary_reports_active_items_and_warnings(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Priority 1: Candidate alpha; promote when maintained report signal appears.

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    summary = planning_summary(target=tmp_path)

    assert summary["kind"] == "planning-summary/v1"
    assert summary["schema"]["schema_version"] == "planning-summary-schema/v1"
    assert summary["schema"]["command"] == "agentic-workspace summary --format json --verbose"
    assert "planning_record" in summary["schema"]["shared_fields"]
    assert "machine_first_planning" in summary["schema"]["shared_fields"]
    assert "planning_surface_health" in summary["schema"]["shared_fields"]
    assert summary["todo"]["active_count"] == 1
    assert summary["execplans"]["active_count"] == 1
    assert summary["machine_first_planning"]["status"] == "markdown-fallback-active"
    assert summary["machine_first_planning"]["canonical_record_extension"] == ".plan.json"
    assert summary["machine_first_planning"]["active_canonical_count"] == 0
    assert summary["machine_first_planning"]["active_markdown_fallback_count"] == 1
    assert "sidecar is canonical" in summary["machine_first_planning"]["rule"]
    assert summary["execution_readiness"]["status"] == "planning-backed"
    assert summary["execution_readiness"]["broad_work_allowed"] is True
    assert summary["execution_readiness"]["recommendation"]["id"] == "continue-active-plan"
    assert summary["planning_surface_health"]["status"] == "clean"
    assert summary["planning_surface_health"]["warning_count"] == 0
    assert summary["planning_surface_health"]["recommended_next_action"] == "No planning-surface drift detected."
    assert summary["planning_record"]["status"] == "present"
    assert summary["planning_record"]["task"]["id"] == "plan-alpha"
    assert summary["planning_record"]["task"]["surface"] == ".agentic-workspace/planning/execplans/plan-alpha.md"
    assert summary["planning_record"]["next_action"] == "Add one checker."
    assert summary["planning_record"]["proof_expectations"] == ["uv run pytest tests/test_check_planning_surfaces.py"]
    assert summary["planning_record"]["closure_check"]["closure decision"] == "keep-active"
    assert summary["planning_record"]["system_intent_alignment"]["slice shaping bias"] == (
        "Keep this slice small but route continuation explicitly."
    )
    assert summary["planning_record"]["system_intent_alignment"]["broader-lane validation question"] == (
        "Did this slice advance the parent lane rather than only local task completion?"
    )
    assert summary["planning_record"]["agent_may_decide"] == (
        "Bounded decomposition, validation tightening, and plan-local residue routing."
    )
    assert summary["planning_record"]["escalate_when"] == (
        "The requested outcome, owned surface, time horizon, or meaningful validation story would change."
    )
    assert summary["planning_record"]["continuation_owner"] == ".agentic-workspace/planning/execplans/plan-alpha.md"
    assert summary["active_contract"]["status"] == "present"
    assert summary["active_contract"]["view_of"] == "planning_record"
    assert summary["active_contract"]["todo_item"]["id"] == "plan-alpha"
    assert summary["active_contract"]["intent"]["requested_outcome"] == "Keep scope clear."
    assert summary["active_contract"]["proof_expectations"] == ["uv run pytest tests/test_check_planning_surfaces.py"]
    assert summary["active_contract"]["tool_verification"]["status"] == "unspecified"
    assert summary["active_contract"]["tool_verification"]["required_tools"] == []
    assert summary["active_contract"]["touched_scope"] == ["scripts/check/check_planning_surfaces.py"]
    assert summary["active_contract"]["minimal_refs"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/plan-alpha.md",
    ]
    assert summary["resumable_contract"]["status"] == "present"
    assert summary["resumable_contract"]["view_of"] == "planning_record"
    assert summary["resumable_contract"]["current_next_action"] == "Add one checker."
    assert summary["resumable_contract"]["active_milestone"]["scope"] == "maintain planning discipline."
    assert summary["resumable_contract"]["completion_criteria"] == ["Warning classes are emitted for known drift."]
    assert summary["resumable_contract"]["tool_verification"]["status"] == "unspecified"
    assert summary["follow_through_contract"]["status"] == "present"
    assert summary["follow_through_contract"]["what_this_slice_enabled"] == "Added one bounded planning improvement."
    assert summary["follow_through_contract"]["validation_still_needed"] == ("run the bounded planning checker test before archive.")
    assert summary["follow_through_contract"]["larger_intended_outcome"] == "Land plan alpha end to end."
    assert summary["intent_interpretation_contract"]["status"] == "present"
    assert summary["intent_interpretation_contract"]["literal_request"] == "Keep scope clear."
    assert summary["intent_interpretation_contract"]["interpretation_distance"] == "low"
    assert summary["context_budget_contract"]["status"] == "present"
    assert summary["context_budget_contract"]["live_working_set"] == (
        "the active checker change, proof command, and closure state for this bounded slice."
    )
    assert summary["context_budget_contract"]["pre_work_config_pull"] == (
        "ask which repo or local config materially constrains this bounded slice and where those limits must show up in execution bounds, stop conditions, or review."
    )
    assert summary["context_budget_contract"]["pre_work_memory_pull"] == (
        "ask what durable planning guidance should be recovered before execution and which planning surface it concerns."
    )
    assert summary["context_budget_contract"]["tiny_resumability_note"] == (
        "keep the warning-class boundary explicit if this slice is revisited later."
    )
    assert summary["execution_run_contract"]["status"] == "present"
    assert summary["execution_run_contract"]["run_status"] == "not-run-yet"
    assert summary["execution_run_contract"]["handoff_source"] == "agentic-planning handoff --format json"
    assert summary["execution_run_contract"]["changed_surfaces"] == "none yet; execution has not changed files."
    assert summary["finished_run_review_contract"]["status"] == "present"
    assert summary["finished_run_review_contract"]["review_status"] == "pending"
    assert summary["finished_run_review_contract"]["config_compliance"] == "pending"
    assert summary["finished_run_review_contract"]["config_trust"] == "pending"
    assert summary["hierarchy_contract"]["status"] == "present"
    assert summary["hierarchy_contract"]["current_layer"] == "execution"
    assert summary["hierarchy_contract"]["parent_lane"]["id"] == "plan-alpha-lane"
    assert summary["hierarchy_contract"]["parent_lane"]["source"] == "execplan"
    assert summary["hierarchy_contract"]["active_chunk"]["milestone_id"] == "plan-alpha"
    assert summary["hierarchy_contract"]["active_chunk"]["next_action"] == "Add one checker."
    assert summary["hierarchy_contract"]["next_likely_chunk"] == (
        "finish the current milestone and archive if no larger follow-on remains."
    )
    assert summary["hierarchy_contract"]["proof_state"]["proof_expectations"] == ["uv run pytest tests/test_check_planning_surfaces.py"]
    assert summary["hierarchy_contract"]["closure_check"]["closure decision"] == "keep-active"
    assert summary["handoff_contract"]["status"] == "present"
    assert summary["handoff_contract"]["task"]["id"] == "plan-alpha"
    assert summary["handoff_contract"]["read_first"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/plan-alpha.md",
    ]
    assert summary["handoff_contract"]["pre_work_config_pull"] == (
        "ask which repo or local config materially constrains this bounded slice and where those limits must show up in execution bounds, stop conditions, or review."
    )
    assert summary["handoff_contract"]["pre_work_memory_pull"] == (
        "ask what durable planning guidance should be recovered before execution and which planning surface it concerns."
    )
    assert summary["handoff_contract"]["owned_write_scope"] == ["scripts/check/check_planning_surfaces.py"]
    assert summary["handoff_contract"]["context_budget"]["status"] == "present"
    assert summary["handoff_contract"]["execution_bounds"]["allowed paths"] == "scripts/check/check_planning_surfaces.py"
    assert summary["handoff_contract"]["stop_conditions"]["stop when"].startswith("the work needs broader")
    assert summary["handoff_contract"]["intent_interpretation"]["status"] == "present"
    assert summary["handoff_contract"]["system_intent_alignment"]["intent evidence source"] == (
        ".agentic-workspace/docs/system-intent-contract.md"
    )
    assert summary["handoff_contract"]["return_with"]["execution_run_fields"][0] == "run status"
    assert summary["handoff_contract"]["return_with"]["execution_run_fields"][5] == "changed surfaces"
    assert summary["handoff_contract"]["return_with"]["execution_summary_fields"][3] == "post-work posterity capture"
    assert summary["handoff_contract"]["worker_contract"]["allowed_execution_methods"][1] == "read-only exploration"
    assert summary["handoff_contract"]["worker_contract"]["worker_owns_by_default"][0] == (
        "read-only exploration for one explicit question when assigned"
    )
    assert summary["roadmap"]["candidate_count"] == 1
    assert summary["roadmap"]["candidates"] == [
        {
            "priority": "1",
            "summary": "Candidate alpha; promote when maintained report signal appears.",
        }
    ]
    assert summary["system_intent"]["canonical_doc"] == ".agentic-workspace/docs/system-intent-contract.md"
    if summary["warning_count"] != 0:
        print(f"DEBUG: warnings found: {summary['warnings']}")
    assert summary["warning_count"] == 0


def test_planning_summary_exposes_adaptive_assurance_fields(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", why_now = "high assurance work needs compact refs." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    record = installer_mod._build_execplan_record_from_todo_item(
        title="Plan Alpha",
        item_id="plan-alpha",
        status="in-progress",
        why_now="high assurance work needs compact refs.",
        next_action="implement the bounded slice.",
        done_when="the slice is implemented and validated.",
    )
    record["adaptive_assurance"] = {
        "level": "high",
        "reason": "touches access control and auditability",
        "agent_may_escalate": True,
        "agent_may_deescalate": False,
        "strict_closeout": True,
        "required_refs": ["requirement_refs", "security_refs"],
        "proof_profiles": ["access_control", "auditability"],
        "required_gates": ["security-review"],
    }
    record["traceability_refs"] = {
        "requirement_refs": ["REQ-7"],
        "security_refs": ["SEC-2"],
        "audit_refs": ["AUD-1"],
    }
    record["control_gates"] = [
        {
            "id": "security-review",
            "owner_role": "security",
            "required_for": ["access-control"],
            "status": "pending",
            "evidence": [],
            "blocking": True,
            "next_action": "obtain security review",
        }
    ]
    record["implementation_blockers"] = [
        {
            "id": "auth-policy",
            "status": "blocked",
            "do_not_implement": True,
            "blocked_by": ["security-review"],
            "allowed_work": ["write interface placeholder"],
            "evidence": [],
            "next_action": "wait for policy owner",
        }
    ]
    record["test_data_policy"] = {
        "classification": "synthetic-only",
        "forbidden": ["real_personal_identity"],
        "fixture_owner": "test-data",
        "proof_required": ["sensitive_data"],
        "refs": ["TESTDATA.md"],
    }
    record["layer_scaffold"] = {
        "type": "access_control",
        "required_refs": ["security_refs"],
        "common_risks": ["privilege escalation"],
        "suggested_proof_profiles": ["access_control"],
        "suggested_gates": ["security-review"],
        "non_goals": ["authorization redesign"],
        "durable_residue_prompts": ["promote stable policy to decision record"],
    }
    record["architecture_decision_promotion"] = {
        "status": "needed",
        "target": "docs/decisions/",
        "decision_refs": [],
        "promotion_needed": True,
        "notes": "promote stable access-control boundary",
    }
    record["threat_failure_aids"] = [
        {
            "id": "access-control-checklist",
            "concern": "access_control",
            "source_ref": ".agentic-workspace/agent-aids/access-control.md",
            "advisory": "review support only",
        }
    ]
    installer_mod._write_execplan_record(record_path=record_path, record=record)

    summary = planning_summary(target=tmp_path, profile="compact")

    planning_record = summary["planning_record"]
    assert planning_record["adaptive_assurance"]["level"] == "high"
    assert planning_record["traceability_refs"]["requirement_refs"] == ["REQ-7"]
    assert planning_record["control_gates"][0]["blocking"] is True
    assert planning_record["implementation_blockers"][0]["do_not_implement"] is True
    assert planning_record["test_data_policy"]["classification"] == "synthetic-only"
    assert planning_record["layer_scaffold"]["type"] == "access_control"
    assert planning_record["architecture_decision_promotion"]["promotion_needed"] is True
    assert planning_record["threat_failure_aids"][0]["id"] == "access-control-checklist"


def test_planning_summary_compact_profile_trims_heavy_sections(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.md", why_now = "keep compact startup cheap." }
]
queued_items = []

[roadmap]
lanes = [
  { id = "tracked-lane", title = "Tracked lane", priority = "first", issues = ["EXT-1"], outcome = "Keep tracked.", reason = "Needed.", promotion_signal = "Promote when needed.", suggested_first_slice = "Do the thing." },
]
candidates = [
  { priority = "first", summary = "Tracked lane" },
]
""",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Tracked lane",
                "status": "open",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "required",
            }
        ],
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    summary = planning_summary(target=tmp_path, profile="compact")

    assert summary["profile"] == "compact"
    assert summary["schema"]["schema_version"] == "planning-summary-compact-schema/v1"
    assert summary["schema"]["command"] == "agentic-workspace summary --format json --verbose"
    assert summary["schema"]["default_tiny_command"] == "agentic-workspace summary --format json"
    assert summary["schema"]["full_profile_command"] == "agentic-workspace summary --format json --verbose"
    assert summary["machine_first_planning"]["status"] == "markdown-fallback-active"
    assert summary["machine_first_planning"]["active_markdown_fallback_count"] == 1
    assert summary["execution_readiness"]["status"] == "planning-backed"
    assert summary["execution_readiness"]["recommendation"]["id"] == "continue-active-plan"
    assert summary["planning_record"]["system_intent_alignment"]["relevant system intent"] == (
        "Preserve larger user or product outcome separately from the bounded slice."
    )
    assert "system_intent_alignment" not in summary["handoff_contract"]
    assert "return_with" not in summary["handoff_contract"]
    assert "candidate_lanes" not in summary["roadmap"]
    assert summary["roadmap"]["candidates"] == [{"priority": "first", "summary": "Tracked lane"}]
    assert "signals" not in summary["intent_validation_contract"]
    assert "external_evidence" not in summary["intent_validation_contract"]
    assert "sample_items" not in json.dumps(summary["intent_validation_contract"])
    assert "derived_follow_up_candidates" not in summary["finished_work_inspection_contract"]
    assert "inspections" not in summary["finished_work_inspection_contract"]
    assert summary["ownership_review"]["repo_owned_surface_count"] >= 1
    assert "repo_owned_surfaces" not in summary["ownership_review"]
    assert "shared_fields" in summary["schema"]
    assert len(json.dumps(summary, sort_keys=True)) < 30000


def test_planning_summary_flags_roadmap_work_without_active_plan(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "dogfooding-guardrail", title = "Dogfooding guardrail", priority = "first", issues = ["#322"], outcome = "Make planned work use planning.", reason = "A broad run bypassed active planning.", promotion_signal = "Promote before broad work.", suggested_first_slice = "Add readiness guardrail." },
]
candidates = [
  { priority = "first", summary = "Dogfooding guardrail" },
]
""",
    )

    summary = planning_summary(target=tmp_path, profile="compact")

    readiness = summary["execution_readiness"]
    assert readiness["status"] == "roadmap-needs-promotion"
    assert readiness["broad_work_allowed"] is False
    assert readiness["direct_work_allowed"] is True
    assert readiness["recommendation"]["id"] == "promote-before-broad-work"
    assert "Roadmap candidates are not execution authority" in readiness["rule"]
    first_item = readiness["recommendation"]["ordered_batch"]["items"][0]
    assert first_item["starter_slice_guidance"]["starter_slice"] == "Add readiness guardrail."
    assert first_item["starter_slice_guidance"]["starter_slice_rule"] == (
        "Suggested first slice is starter guidance, not completion scope."
    )
    assert first_item["starter_slice_guidance"]["full_intent_boundary"] == "Make planned work use planning."


def test_planning_summary_warns_on_closed_lanes_in_live_state(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = [
  { id = "done-lane", type = "lane", title = "Done lane", maturity = "closed", status = "done", priority = "first", issues = ["#1"], outcome = "Done.", reason = "Done.", promotion_signal = "None.", suggested_first_slice = "", closure = "archive-and-close", durable_residue = "planning" },
]

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "also-done", title = "Also done", maturity = "closed", status = "done", priority = "second", issues = ["#2"], outcome = "Done.", reason = "Done.", promotion_signal = "None.", suggested_first_slice = "", closure = "archive-and-close", durable_residue = "planning" },
]
candidates = [
  { priority = "first", summary = "Done lane" },
  { priority = "second", summary = "Also done" },
]
""",
    )

    summary = planning_summary(target=tmp_path, profile="compact")

    assert summary["roadmap"]["lane_count"] == 0
    assert summary["roadmap"]["candidate_count"] == 0
    assert summary["roadmap"]["candidates"] == []
    assert summary["planning_surface_health"]["status"] == "not-clean"
    assert any(
        warning["warning_class"] == "historical_work_in_live_planning_state" for warning in summary["planning_surface_health"]["warnings"]
    )
    assert summary["execution_readiness"]["status"] == "narrow-direct-ready"
    assert summary["execution_readiness"]["recommendation"]["id"] == "stay-direct-for-narrow-work"
    assert summary["autopilot_loop"]["status"] == "blocked"


def test_planning_summary_reports_candidate_lanes(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Candidate Lanes

- Lane: Native candidate-lane queue for deferred grouped work
  ID: native-candidate-lanes
  Priority: highest
  Issues: #135
  Outcome: keep grouped deferred work repo-native and promotable without ad hoc queue prose.
  Why now: the ad hoc roadmap queue shape itself is the next planning friction.
  Promotion signal: promote when one thin native shape can replace the grouped queue prose.
  Suggested first slice: define the minimum lane fields and translate one real lane into them.
- Lane: Memory trust, usefulness, and cleanup ergonomics
  ID: memory-trust-usefulness-cleanup
  Priority: second
  Issues: #96, #97, #98, #99, #100
  Outcome: make Memory cheaper to trust, inspect, and clean up.
  Why later: wait until the planning slice lands.
  Promotion signal: promote when the candidate-lane slice lands.
  Suggested first slice: start with evidence-backed note trust states.
""",
    )

    summary = planning_summary(target=tmp_path)

    assert summary["roadmap"]["lane_count"] == 2
    assert summary["roadmap"]["candidate_count"] == 2
    assert summary["roadmap"]["candidates"] == [
        {"priority": "highest", "summary": "Native candidate-lane queue for deferred grouped work"},
        {"priority": "second", "summary": "Memory trust, usefulness, and cleanup ergonomics"},
    ]
    assert summary["roadmap"]["candidate_lanes"][0]["id"] == "native-candidate-lanes"
    assert summary["roadmap"]["candidate_lanes"][0]["issues"] == ["#135"]
    assert summary["roadmap"]["candidate_lanes"][0]["references"] == [{"kind": "issue", "target": "#135", "role": "related-work"}]
    assert summary["roadmap"]["candidate_lanes"][1]["issues"] == ["#96", "#97", "#98", "#99", "#100"]
    assert summary["roadmap"]["candidate_lanes"][1]["promotion_signal"] == "promote when the candidate-lane slice lands."


def test_planning_summary_normalizes_structured_lane_references_from_state_toml(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.md", why_now = "keep lane references queryable above the execplan layer." }
]
queued_items = []

[roadmap]
lanes = [
  { id = "machine-first-planning-chain", title = "Machine-first planning chain", priority = "second", issues = ["#261", "#280"], references = [{ kind = "plan", target = ".agentic-workspace/planning/execplans/archive/machine-first-planning-chain-first-slice-2026-04-23.plan.json", role = "prior-proof", label = "First sidecar proof" }] }
]
candidates = [
  { priority = "second", summary = "Machine-first planning chain" }
]
""",
    )
    _write_execplan_record(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json",
        item_id="plan-alpha",
    )

    summary = planning_summary(target=tmp_path)

    assert summary["roadmap"]["candidate_lanes"][0]["references"] == [
        {
            "kind": "plan",
            "target": ".agentic-workspace/planning/execplans/archive/machine-first-planning-chain-first-slice-2026-04-23.plan.json",
            "role": "prior-proof",
            "label": "First sidecar proof",
        },
        {
            "kind": "issue",
            "target": "#261",
            "role": "related-work",
        },
        {
            "kind": "issue",
            "target": "#280",
            "role": "related-work",
        },
    ]


def test_planning_summary_reports_required_tools_when_execplan_declares_them(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan_with_required_tools())

    summary = planning_summary(target=tmp_path)

    assert summary["planning_record"]["tool_verification"]["status"] == "required-tools-declared"
    assert summary["planning_record"]["tool_verification"]["required_tools"] == ["browser", "gh"]
    assert summary["active_contract"]["tool_verification"]["required_tools"] == ["browser", "gh"]
    assert summary["resumable_contract"]["tool_verification"]["required_tools"] == ["browser", "gh"]


def test_planning_report_derives_compact_module_state_from_summary(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: report-lane
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/report-lane.md
  Why now: derive compact module state.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n\n## Next Candidate Queue\n- Later lane.\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "report-lane.md", _minimal_execplan())

    report = planning_report(target=tmp_path)

    assert report["kind"] == "planning-module-report/v1"
    assert report["schema"]["command"] == "agentic-planning report --format json"
    assert report["status"]["active_todo_count"] == 1
    assert report["status"]["active_execplan_count"] == 1
    assert report["status"]["roadmap_lane_count"] == 0
    assert report["next_action"]["summary"] == "Add one checker."
    assert report["system_intent"]["canonical_doc"] == ".agentic-workspace/docs/system-intent-contract.md"
    helpers = {helper["artifact"]: helper for helper in report["writer_helpers"]["helpers"]}
    assert "promote-to-plan" in helpers["execplan"]["command"]
    assert "create-review" in helpers["review_record"]["command"]


def test_planning_report_flags_lower_trust_config_closeout(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: report-lane
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/report-lane.md
  Why now: derive compact module state.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n\n## Next Candidate Queue\n- Later lane.\n")
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "report-lane.md",
        _minimal_execplan()
        .replace("- Review status: pending\n", "- Review status: completed\n")
        .replace("- Scope respected: pending\n", "- Scope respected: yes\n")
        .replace("- Proof status: pending\n", "- Proof status: satisfied\n")
        .replace("- Intent served: pending\n", "- Intent served: yes\n")
        .replace(
            "- Config compliance: pending\n",
            "- Config compliance: bypassed repo-local config and left the resulting bounds underspecified.\n",
        )
        .replace("- Misinterpretation risk: pending\n", "- Misinterpretation risk: medium\n")
        .replace("- Follow-on decision: pending\n", "- Follow-on decision: repair-before-close\n"),
    )

    summary = planning_summary(target=tmp_path)
    report = planning_report(target=tmp_path)

    assert summary["finished_run_review_contract"]["config_trust"] == "lower-trust"
    assert "bypass" in summary["finished_run_review_contract"]["recommended_next_action"].lower()
    assert report["health"] == "attention-needed"
    assert any(finding["warning_class"] == "config_compliance_lower_trust" for finding in report["findings"])


def test_planning_summary_exposes_compact_planning_surface_health_when_not_clean(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md",
        _minimal_execplan().replace("## Delegated Judgment", "## Delegated Notes"),
    )

    summary = planning_summary(target=tmp_path)

    assert summary["planning_surface_health"]["status"] == "not-clean"
    assert summary["planning_surface_health"]["warning_count"] >= 1
    assert summary["planning_surface_health"]["warnings"][0]["warning_class"] == "execplan_structure_drift"
    assert "Restore the current template sections" in summary["planning_surface_health"]["recommended_next_action"]


def test_planning_summary_warns_when_execplan_next_action_references_missing_file(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(plan_path)
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["immediate_next_action"] = ["Review implementation slices in plan.md before coding."]
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]

    assert any(warning["warning_class"] == "execplan_missing_file_reference" for warning in warnings)
    assert any("plan.md" in warning["message"] for warning in warnings)


def test_planning_summary_ignores_conceptual_slash_phrases_in_execplan_next_action(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(plan_path)
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["immediate_next_action"] = ["Represent behavior in operation IR/contracts before generating target executors."]
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]

    assert not any(
        warning["warning_class"] == "execplan_missing_file_reference" and "IR/contracts" in warning["message"] for warning in warnings
    )


def test_planning_summary_ignores_slash_separated_category_phrases_in_execplan_next_action(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(plan_path)
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["immediate_next_action"] = ["Harden focused tests/contracts/docs before closeout."]
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]

    assert not any(
        warning["warning_class"] == "execplan_missing_file_reference" and "tests/contracts/docs" in warning["message"]
        for warning in warnings
    )


def test_planning_summary_ignores_generic_prose_slash_taxonomy_in_execplan_next_action(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(plan_path)
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["immediate_next_action"] = [
        "Reconcile parser/help/dispatch/executable behavior across source/installed/Docker proof/closeout paths."
    ]
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]

    assert not any(warning["warning_class"] == "execplan_missing_file_reference" for warning in warnings)


def test_planning_summary_ignores_known_conceptual_slash_pairs_in_execplan_next_action(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(plan_path)
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["immediate_next_action"] = ["Generate one compact Codex plugin/adaptor metadata target from SkillSpec."]
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]

    assert not any(
        warning["warning_class"] == "execplan_missing_file_reference" and "plugin/adaptor" in warning["message"] for warning in warnings
    )


def test_planning_summary_warns_when_non_prep_plan_keeps_prep_only_residue(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(plan_path)
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["control_gates"] = [
        {
            "id": "prep-only-halt",
            "owner_role": "implementation",
            "required_for": ["before implementation"],
            "status": "pending",
            "evidence": [],
            "blocking": True,
            "next_action": "HALT: prep-only mode active.",
        }
    ]
    record["machine_readable_contract"]["planning_mode"] = {"prep_only": False}
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]

    assert any(warning["warning_class"] == "execplan_stale_mode_residue" for warning in warnings)
    assert summary["planning_surface_health"]["status"] == "not-clean"


def test_planning_summary_ignores_jsx_tags_in_execplan_next_action(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(plan_path)
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    option_close = "</" + "option>"
    select_close = "</" + "select>"
    record["immediate_next_action"] = [f"Fix the select markup in src/Picker.tsx around <option>A{option_close}."]
    installer_mod._write_execplan_record(record_path=plan_path, record=record)
    _write(
        tmp_path / "src" / "Picker.tsx",
        f'export function Picker() {{ return <select><option value="a">A{option_close}{select_close}; }}',
    )

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]

    assert not any(
        warning["warning_class"] == "execplan_missing_file_reference" and "/" + "option" in warning["message"] for warning in warnings
    )


def test_planning_summary_preserves_dot_prefixed_reference_paths(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(plan_path)
    review_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "review-alpha.review.json"
    _write(review_path, "{}")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["references"] = [
        {
            "kind": "source",
            "target": "review-alpha",
            "label": "review-alpha",
            "role": "evidence",
            "locator": ".agentic-workspace/planning/reviews/review-alpha.review.json",
        }
    ]
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]

    assert not any(warning["warning_class"] == "execplan_missing_file_reference" for warning in warnings)


def test_planning_summary_warns_on_historical_work_in_live_state(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = [
  { id = "done-history", title = "Done history", maturity = "closed", status = "done", path = ".agentic-workspace/planning/execplans/archive/done-history.plan.json", durable_residue = "evidence_only", residue_owner = "archive", residue_promotion_trigger = "none" },
]

[todo]
active_items = []
queued_items = []
""",
    )

    summary = planning_summary(target=tmp_path)
    warnings = summary["planning_surface_health"]["warnings"]

    assert summary["planning_surface_health"]["status"] == "not-clean"
    assert any(warning["warning_class"] == "historical_work_in_live_planning_state" for warning in warnings)
    assert "not in state.toml" in summary["planning_surface_health"]["recommended_next_action"]


def test_planning_summary_exposes_intent_validation_contract(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "tracked-lane", title = "Tracked lane", priority = "first", issues = ["EXT-1"], outcome = "Keep tracked.", reason = "Needed.", promotion_signal = "Promote when needed.", suggested_first_slice = "Do the thing." },
]
candidates = [
  { priority = "first", summary = "Tracked lane" },
]
""",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Tracked lane",
                "status": "open",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
            {
                "system": "manual",
                "id": "EXT-2",
                "title": "Untracked lane",
                "status": "open",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
            {
                "system": "manual",
                "id": "EXT-3",
                "title": "Closed without residue",
                "status": "closed",
                "kind": "slice",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
        ],
    )

    summary = planning_summary(target=tmp_path)

    assert "intent_validation_contract" in summary["schema"]["shared_fields"]
    contract = summary["intent_validation_contract"]
    assert contract["status"] == "present"
    assert contract["external_evidence"]["status"] == "loaded"
    assert contract["external_evidence"]["item_count"] == 3
    assert contract["current_external_work"]["status"] == "loaded"
    assert contract["current_external_work"]["open_count"] == 2
    assert contract["current_external_work"]["closed_count"] == 1
    assert "provider-agnostic" in contract["current_external_work"]["provider_rule"]
    reconciliation = contract["external_work_reconciliation"]
    assert reconciliation["kind"] == "planning-external-work-reconciliation/v1"
    assert reconciliation["status"] == "attention"
    assert reconciliation["provider_rule"].startswith("Core planning consumes provider-agnostic")
    assert reconciliation["freshness"]["fresh_enough_to_trust"] is True
    assert reconciliation["freshness"]["trust_scope"] == "snapshot"
    assert reconciliation["freshness"]["refresh_after_mutation"] is True
    assert "external-intent refresh-github" in reconciliation["freshness"]["refresh_command"]
    assert reconciliation["external_work_state"]["untracked_open_count"] == 1
    promotion_action = reconciliation["promotion_action"]
    assert promotion_action["action"] == "promote-external-work-to-planning"
    assert promotion_action["provider_neutral"] is True
    assert promotion_action["target_surfaces"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/<lane>.plan.json",
    ]
    assert "do not duplicate active state" in promotion_action["state_rule"]
    assert reconciliation["closeout_state"]["needs_audit_count"] == 1
    assert reconciliation["landed_open_state"]["implemented_and_unclosed_count"] == 0
    assert contract["historical_audit_references"]["status"] == "needs-audit"
    assert "not current external-work state" in contract["historical_audit_references"]["rule"]
    assert contract["counts"]["tracked_external_open_count"] == 1
    assert contract["counts"]["untracked_external_open_count"] == 1
    assert contract["counts"]["lower_trust_closeout_count"] == 1
    assert contract["counts"]["attention_count"] == 2
    assert contract["signals"][0]["kind"] == "external_open_untracked"
    assert contract["signals"][1]["kind"] == "closed_without_planning_residue"


def test_planning_summary_surfaces_external_intent_refresh_metadata(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    evidence_path = tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "refreshed_at": "2026-04-27T12:00:00+00:00",
                "refresh_metadata": {
                    "adapter": "github-gh-cli",
                    "repository": "acme/project",
                    "item_count": 1,
                    "open_count": 1,
                    "closed_count": 0,
                    "limit": 200,
                },
                "items": [
                    {
                        "system": "github",
                        "id": "#445",
                        "title": "Refresh external evidence",
                        "status": "open",
                        "kind": "issue",
                        "parent_id": "",
                        "planning_residue_expected": "required",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = planning_summary(target=tmp_path)

    current_external_work = summary["intent_validation_contract"]["current_external_work"]
    assert current_external_work["path"] == ".agentic-workspace/local/cache/external-intent-evidence.json"
    assert current_external_work["storage"] == "cache"
    assert current_external_work["refreshed_at"] == "2026-04-27T12:00:00+00:00"
    assert current_external_work["refresh_metadata"]["adapter"] == "github-gh-cli"
    assert current_external_work["refresh_metadata"]["repository"] == "acme/project"
    assert current_external_work["trust_scope"] == "snapshot"
    assert current_external_work["refresh_after_mutation"] is True
    assert "not live tracker truth" in current_external_work["snapshot_rule"]
    reconciliation = summary["intent_validation_contract"]["external_work_reconciliation"]
    assert reconciliation["freshness"]["refreshed_at"] == "2026-04-27T12:00:00+00:00"
    assert reconciliation["freshness"]["refresh_metadata"]["adapter"] == "github-gh-cli"
    assert reconciliation["freshness"]["trust_scope"] == "snapshot"
    assert reconciliation["freshness"]["refresh_after_mutation"] is True
    assert "external-intent refresh-github" in reconciliation["freshness"]["refresh_command"]
    assert reconciliation["promotion_action"]["action"] == "promote-external-work-to-planning"
    assert reconciliation["promotion_action"]["provider_neutral"] is True


def test_planning_summary_accepts_bom_external_intent_evidence(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    evidence_path = tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "planning-external-intent-evidence/v1",
        "refresh_metadata": {
            "adapter": "github-gh-cli",
            "repository": "acme/project",
            "item_count": 1,
            "open_count": 1,
            "closed_count": 0,
        },
        "items": [
            {
                "system": "github",
                "id": "#533",
                "status": "open",
            }
        ],
    }
    evidence_path.write_bytes(("\ufeff" + json.dumps(payload, indent=2) + "\n").encode("utf-8"))

    summary = planning_summary(target=tmp_path)

    external_evidence = summary["intent_validation_contract"]["external_evidence"]
    assert external_evidence["status"] == "loaded"
    assert external_evidence["item_count"] == 1
    assert summary["intent_validation_contract"]["current_external_work"]["open_count"] == 1


def test_planning_summary_rejects_external_intent_count_drift(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\n	candidates = []\n",
    )
    evidence_path = tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "refresh_metadata": {
                    "item_count": 2,
                    "open_count": 0,
                    "closed_count": 0,
                },
                "items": [
                    {
                        "system": "github",
                        "id": "#533",
                        "status": "open",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = planning_summary(target=tmp_path)

    external_evidence = summary["intent_validation_contract"]["external_evidence"]
    assert external_evidence["status"] == "invalid"
    assert "refresh_metadata.item_count must equal 1 from items" in external_evidence["reason"]
    assert any("refresh_metadata.open_count must equal 1 from items" in finding for finding in external_evidence["schema_findings"])


def test_planning_summary_rejects_schema_invalid_external_intent_evidence(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[{"system": "manual", "id": "", "status": "open"}],
    )

    summary = planning_summary(target=tmp_path)

    external_evidence = summary["intent_validation_contract"]["external_evidence"]
    assert external_evidence["status"] == "invalid"
    assert "schema validation failed" in external_evidence["reason"]
    assert any("items.0.id" in finding for finding in external_evidence["schema_findings"])
    assert summary["intent_validation_contract"]["current_external_work"]["status"] == "invalid"


def test_planning_summary_reconciles_lower_trust_closeouts_from_review_artifact(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Closed with proof",
                "status": "closed",
                "kind": "slice",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
            {
                "system": "manual",
                "id": "EXT-2",
                "title": "Closed with follow-up",
                "status": "closed",
                "kind": "slice",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
            {
                "system": "manual",
                "id": "EXT-3",
                "title": "Closed without audit",
                "status": "closed",
                "kind": "slice",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
        ],
    )
    _write(
        tmp_path / ".agentic-workspace/planning/reviews/lower-trust.review.json",
        json.dumps(
            {
                "kind": "planning-review/v1",
                "title": "Lower Trust",
                "issue_classifications": [
                    {
                        "id": "EXT-1",
                        "title": "Closed with proof",
                        "classification": "fully_satisfied_with_evidence",
                        "live_state": "closed",
                        "evidence": "commit abc123",
                        "follow_up": "none",
                    },
                    {
                        "id": "EXT-2",
                        "title": "Closed with follow-up",
                        "classification": "covered_by_open_followup",
                        "live_state": "closed",
                        "evidence": "bounded slice landed",
                        "follow_up": "EXT-4",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
    )

    summary = planning_summary(target=tmp_path, profile="compact")
    reconciliation = summary["intent_validation_contract"]["closeout_reconciliation"]

    assert reconciliation["status"] == "needs-audit"
    assert reconciliation["counts"]["reconciled_count"] == 2
    assert reconciliation["counts"]["evidence_present_count"] == 1
    assert reconciliation["counts"]["follow_up_open_count"] == 1
    assert reconciliation["counts"]["needs_audit_count"] == 1
    assert reconciliation["omitted_item_count"] == 0
    assert "sample_items_by_state" not in reconciliation
    assert summary["intent_validation_contract"]["counts"]["closeout_reconciled_count"] == 2
    assert summary["intent_validation_contract"]["counts"]["closeout_needs_audit_count"] == 1


def test_planning_summary_reports_open_issue_with_landed_archive_evidence(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "stale-tracker", title = "Stale tracker", priority = "first", issues = ["EXT-OPEN"], outcome = "Close stale tracker.", reason = "Landed evidence exists.", promotion_signal = "Review open tracker.", suggested_first_slice = "Close or reroute." },
]
candidates = []
""",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-OPEN",
                "title": "Still open upstream",
                "status": "open",
                "kind": "slice",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
        ],
    )
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    plan_path = archive_dir / "stale-tracker.plan.json"
    _write_execplan_record(plan_path, item_id="stale-tracker", status="completed")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["references"] = [{"kind": "issue", "target": "EXT-OPEN", "role": "source"}]
    record["intent_satisfaction"] = {
        "original intent": "Implement EXT-OPEN.",
        "was original intent fully satisfied?": "yes",
        "evidence of intent satisfaction": "The bounded implementation landed.",
        "unsolved intent passed to": "none",
    }
    record["closure_check"] = {
        "slice status": "completed",
        "larger-intent status": "closed",
        "closure decision": "archive-and-close",
        "why this decision is honest": "The archived plan says the issue landed.",
        "evidence carried forward": "test archive",
        "reopen trigger": "upstream item remains open",
    }
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path, profile="compact")
    reconciliation = summary["intent_validation_contract"]["landed_open_issue_reconciliation"]

    assert reconciliation["status"] == "implemented-and-unclosed"
    assert reconciliation["counts"]["implemented_and_unclosed_count"] == 1
    assert "sample_items" not in reconciliation
    assert summary["intent_validation_contract"]["counts"]["landed_open_issue_count"] == 1
    assert "close or reroute" in summary["intent_validation_contract"]["recommended_next_action"].lower()


def test_planning_summary_does_not_treat_follow_up_role_as_landed_open_issue(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#900",
                "title": "Parent lane remains open",
                "status": "open",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
        ],
    )
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    plan_path = archive_dir / "child-slice.plan.json"
    _write_execplan_record(plan_path, item_id="child-slice", status="completed")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["references"] = [
        {"kind": "issue", "target": "#901", "role": "closed_item"},
        {"kind": "issue", "target": "#900", "role": "parent_intent"},
    ]
    record["closure_check"] = {
        "slice status": "completed",
        "larger-intent status": "open",
        "closure decision": "archive-and-close",
        "why this decision is honest": "The child slice landed while the parent lane remains active.",
        "evidence carried forward": "#900 remains a follow-up context reference, not this closeout target.",
        "reopen trigger": "parent lane work is lost",
    }
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path, profile="compact")
    reconciliation = summary["intent_validation_contract"]["landed_open_issue_reconciliation"]

    assert reconciliation["status"] == "absent"
    assert reconciliation["counts"]["implemented_and_unclosed_count"] == 0
    assert reconciliation["counts"]["ambiguous_open_reference_count"] == 0
    assert summary["intent_validation_contract"]["counts"]["landed_open_issue_count"] == 0


def test_planning_summary_accepts_historical_closeout_baseline(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Historical closeout",
                "status": "closed",
                "kind": "slice",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
        ],
    )
    _write(
        tmp_path / ".agentic-workspace/planning/reviews/historical-baseline.review.json",
        json.dumps(
            {
                "kind": "planning-review/v1",
                "title": "Historical Baseline",
                "issue_classifications": [
                    {
                        "id": "EXT-1",
                        "title": "Historical closeout",
                        "classification": "accepted_historical_baseline",
                        "live_state": "closed",
                        "evidence": "Legacy debt accepted as baseline.",
                        "follow_up": "none",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
    )

    summary = planning_summary(target=tmp_path, profile="compact")
    reconciliation = summary["intent_validation_contract"]["closeout_reconciliation"]

    assert reconciliation["status"] == "present"
    assert reconciliation["counts"]["historical_baseline_count"] == 1
    assert reconciliation["counts"]["needs_audit_count"] == 0
    assert reconciliation["omitted_item_count"] == 0
    assert "sample_items_by_state" not in reconciliation
    assert summary["intent_validation_contract"]["counts"]["closeout_needs_audit_count"] == 0


def test_planning_summary_does_not_treat_historical_followups_as_current_work(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Closed with historical follow-up",
                "status": "closed",
                "kind": "slice",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
        ],
    )
    _write(
        tmp_path / ".agentic-workspace/planning/reviews/historical-followup.review.json",
        json.dumps(
            {
                "kind": "planning-review/v1",
                "title": "Historical Follow-up",
                "issue_classifications": [
                    {
                        "id": "EXT-1",
                        "title": "Closed with historical follow-up",
                        "classification": "covered_by_open_followup",
                        "live_state": "closed",
                        "evidence": "bounded slice landed",
                        "follow_up": "legacy follow-up recorded for audit",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
    )

    summary = planning_summary(target=tmp_path, profile="compact")
    contract = summary["intent_validation_contract"]

    assert contract["current_external_work"]["open_count"] == 0
    assert contract["historical_audit_references"]["follow_up_open_count"] == 1
    assert "sources" not in contract["historical_audit_references"]
    assert "--verbose` for historical review source paths" in contract["historical_audit_references"]["detail"]
    assert contract["closeout_reconciliation"]["counts"]["follow_up_open_count"] == 1
    assert "items_by_state" not in contract["closeout_reconciliation"]
    assert "--verbose` for full reconciliation sources" in contract["closeout_reconciliation"]["detail"]
    assert contract["recommended_next_action"] == "No dangling larger intent or lower-trust closeout signals detected."


def test_planning_summary_prioritizes_current_execution_over_historical_audit_backlog(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "current-lane", status = "in-progress", source = "github:#448", surface = ".agentic-workspace/planning/execplans/current-lane.plan.json", why_now = "current requested lane for #442." }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    current_plan = tmp_path / ".agentic-workspace/planning/execplans/current-lane.plan.json"
    _write_execplan_record(current_plan, item_id="current-lane", status="in-progress")
    current_record = json.loads(current_plan.read_text(encoding="utf-8"))
    current_record["references"] = [
        {
            "kind": "github-issue",
            "target": "https://github.com/example/repo/issues/448",
            "label": "#448 current lane",
            "role": "source_intent",
            "locator": "issue",
        },
        {
            "kind": "github-issue",
            "target": "https://github.com/example/repo/issues/442",
            "label": "#442 parent lane",
            "role": "parent_intent",
            "locator": "issue",
        },
    ]
    current_record["machine_readable_contract"]["execution"]["next_step"] = "Keep implementing #448."
    installer_mod._write_execplan_record(record_path=current_plan, record=current_record)

    archive_dir = tmp_path / ".agentic-workspace/planning/execplans/archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for number in range(441, 447):
        archived_plan = archive_dir / f"historical-{number}.plan.json"
        _write_execplan_record(
            archived_plan,
            item_id=f"historical-{number}",
            status="completed",
            references=[
                {
                    "kind": "github-issue",
                    "target": f"https://github.com/example/repo/issues/{number}",
                    "label": f"#{number} delivered child",
                    "role": "closed_item",
                    "locator": "issue",
                },
                {
                    "kind": "github-issue",
                    "target": "https://github.com/example/repo/issues/442",
                    "label": "#442 parent lane",
                    "role": "parent_intent",
                    "locator": "issue",
                },
            ],
        )
        archived_record = json.loads(archived_plan.read_text(encoding="utf-8"))
        archived_record["title"] = f"Historical {number}"
        archived_record["intent_satisfaction"]["was original intent fully satisfied?"] = "no"
        archived_record["closure_check"]["larger-intent status"] = "open"
        archived_record["closure_check"]["closure decision"] = "archive-but-keep-lane-open"
        installer_mod._write_execplan_record(record_path=archived_plan, record=archived_record)

    compact = planning_summary(target=tmp_path, profile="compact")
    full = planning_summary(target=tmp_path, profile="full")

    assert compact["current_execution_pressure"]["status"] == "active-execution"
    assert compact["current_execution_pressure"]["active_task"]["id"] == "current-lane"
    assert compact["current_execution_pressure"]["recommended_next_action"] == "add one checker."
    audit = compact["historical_audit_pressure"]
    assert audit["status"] == "backgrounded-by-active-execution"
    assert audit["current_lane_refs"] == ["#442", "#448"]
    assert audit["candidate_count"] == 6
    assert audit["omitted_candidate_count"] == 6
    assert audit["sample_candidates"] == []
    assert audit["recommended_next_action"].startswith("Continue current_execution_pressure first")
    compact_finished = compact["finished_work_inspection_contract"]
    assert compact_finished["counts"]["omitted_inspection_count"] == 1
    assert compact_finished["counts"]["omitted_derived_follow_up_candidate_count"] == 1
    assert "inspections" not in compact_finished
    assert "derived_follow_up_candidates" not in compact_finished
    assert "finished-work inspection detail" in compact_finished["detail"]
    assert len(full["finished_work_inspection_contract"]["derived_follow_up_candidates"]) == 6


def test_planning_summary_exposes_autopilot_loop_status_for_required_continuation(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "autopilot-loop-status", status = "in-progress", source = "github:#468", surface = ".agentic-workspace/planning/execplans/autopilot-loop-status.plan.json", why_now = "remaining #442 continuation." }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/autopilot-loop-status.plan.json"
    _write_execplan_record(plan_path, item_id="autopilot-loop-status", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["references"] = [
        {
            "kind": "github-issue",
            "target": "https://github.com/example/repo/issues/468",
            "label": "#468 loop status",
            "role": "source_intent",
            "locator": "issue",
        },
        {
            "kind": "github-issue",
            "target": "https://github.com/example/repo/issues/442",
            "label": "#442 parent lane",
            "role": "parent_intent",
            "locator": "issue",
        },
    ]
    record["required_continuation"] = {
        "required follow-on for the larger intended outcome": "yes",
        "required follow-on detail": "One more slice remains before the parent can close.",
        "owner surface": ".agentic-workspace/planning/state.toml",
        "activation trigger": "after this slice",
    }
    record["parent_lane"] = {
        "id": "#442",
        "title": "Autopilot intent loop",
        "priority": "1",
        "issues": "#442, #468",
    }
    record["closure_check"] = {
        "slice status": "open",
        "larger-intent status": "open",
        "closure decision": "keep-active",
        "why this decision is honest": "#442 is still being evaluated.",
        "evidence carried forward": "#468 owns the remaining status gap.",
        "reopen trigger": "loop status is absent",
    }
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    compact = planning_summary(target=tmp_path, profile="compact")

    assert "autopilot_loop" in compact["schema"]["shared_fields"]
    loop = compact["autopilot_loop"]
    assert loop["allowed_statuses"] == ["satisfied", "continued", "blocked", "routed"]
    assert loop["status"] == "continued"
    assert loop["current_task"]["id"] == "autopilot-loop-status"
    assert loop["larger_intent_status"] == "open"
    assert loop["closure_decision"] == "keep-active"
    assert loop["required_follow_on"] == "yes"
    assert loop["recommended_next_action"] == "add one checker."
    assert installer_mod._execplan_parent_lane(plan_path)["id"] == "#442"


def test_planning_report_promotes_intent_validation_signals_to_findings(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-9",
                "title": "Untracked lane",
                "status": "open",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "required",
            }
        ],
    )

    report = planning_report(target=tmp_path)

    assert report["intent_validation"]["counts"]["untracked_external_open_count"] == 1
    assert report["status"]["intent_validation_attention_count"] == 1
    assert any(finding["warning_class"] == "external_open_untracked" for finding in report["findings"])


def test_planning_summary_exposes_finished_work_inspection_contract(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    _write(
        archive_dir / "system-intent-and-planning-trust-2026-04-21.md",
        (
            "# System Intent And Planning Trust\n\n"
            "## Intent Satisfaction\n\n"
            "- Was original intent fully satisfied?: yes\n\n"
            "## Closure Check\n\n"
            "- Closure decision: archive-and-close\n"
            "- Larger-intent status: closed\n\n"
            "Implemented #220, #222, and #229.\n"
        ),
    )
    _write(
        archive_dir / "bounded-delegation-and-run-contracts-2026-04-21.md",
        (
            "# Bounded Delegation And Run Contracts\n\n"
            "## Intent Satisfaction\n\n"
            "- Was original intent fully satisfied?: no\n\n"
            "## Closure Check\n\n"
            "- Closure decision: archive-but-keep-lane-open\n"
            "- Larger-intent status: open\n\n"
            "Implemented #233 and left #241 open.\n"
        ),
    )
    _write_finished_work_evidence(
        tmp_path / ".agentic-workspace/planning/finished-work-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#260",
                "title": "Finished-work intent inspection",
                "status": "open",
                "kind": "lane",
                "reopens": ["#220", "#222", "#229"],
            }
        ],
    )

    summary = planning_summary(target=tmp_path)

    assert "finished_work_inspection_contract" in summary["schema"]["shared_fields"]
    contract = summary["finished_work_inspection_contract"]
    assert contract["status"] == "present"
    assert contract["counts"]["archived_closeout_count"] == 2
    assert contract["counts"]["likely_premature_closeout_count"] == 1
    assert contract["counts"]["partial_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 2
    assert contract["counts"]["attention_count"] == 2
    assert contract["evidence"]["status"] == "loaded"
    assert contract["evidence"]["item_count"] == 1
    assert {inspection["classification"] for inspection in contract["inspections"]} == {
        "partial",
        "likely_premature_closeout",
    }
    assert {signal["kind"] for signal in contract["signals"]} == {
        "intent_continuation_required",
        "likely_premature_closeout",
    }
    candidates_by_plan = {candidate["source_plan"]: candidate for candidate in contract["derived_follow_up_candidates"]}
    partial_candidate = next(
        candidate for path, candidate in candidates_by_plan.items() if path.endswith("bounded-delegation-and-run-contracts-2026-04-21.md")
    )
    reopened_candidate = next(candidate for candidate in candidates_by_plan.values() if candidate["reopened_by"] == ["#260"])
    assert partial_candidate["kind"] == "intent-derived-continuation"
    assert reopened_candidate["classification"] == "likely_premature_closeout"


def test_planning_summary_inspects_machine_first_archived_execplans_for_required_continuation(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Generated CLI continuation",
                "status": "open",
                "kind": "issue",
                "parent_id": "",
                "planning_residue_expected": "required",
            }
        ],
    )
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    plan_path = archive_dir / "generated-cli-migration.plan.json"
    _write_execplan_record(
        plan_path,
        item_id="generated-cli-migration",
        status="completed",
        references=[
            {
                "kind": "external-task",
                "target": "EXT-1",
                "label": "Generated CLI continuation",
                "role": "next_lane",
                "locator": "external evidence",
            }
        ],
    )
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["title"] = "Generated CLI Migration"
    record["intent_satisfaction"] = {
        "original intent": "Remove reliance on a single hand-authored CLI implementation.",
        "was original intent fully satisfied?": "no",
        "evidence of intent satisfaction": "The first adapter slice landed, but runtime work still depends on hand-authored CLI code.",
        "unsolved intent passed to": "intent-derived continuation candidate",
    }
    record["closure_check"] = {
        "slice status": "bounded slice complete",
        "larger-intent status": "open",
        "closure decision": "archive-but-keep-lane-open",
        "why this decision is honest": "The slice landed but the larger generated-CLI intent remains open.",
        "evidence carried forward": "generated adapter proof",
        "reopen trigger": "future direct CLI edits continue",
    }
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["archived_closeout_count"] == 1
    assert contract["counts"]["partial_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 1
    candidate = contract["derived_follow_up_candidates"][0]
    assert candidate["source_plan"] == ".agentic-workspace/planning/execplans/archive/generated-cli-migration.plan.json"
    assert candidate["recommended_owner"] == ".agentic-workspace/planning/state.toml"
    assert summary["execution_readiness"]["status"] == "intent-continuation-needs-promotion"
    assert summary["execution_readiness"]["recommendation"]["id"] == "promote-intent-derived-continuation"


def test_planning_summary_keeps_unowned_archived_continuation_audit_only(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    plan_path = archive_dir / "abstract-follow-on.plan.json"
    _write_execplan_record(plan_path, item_id="abstract-follow-on", status="completed")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["title"] = "Abstract Follow-On"
    record["intent_satisfaction"] = {
        "original intent": "Keep autopilot looping until the larger intent is satisfied.",
        "was original intent fully satisfied?": "no",
        "evidence of intent satisfaction": "The detection slice landed.",
        "unsolved intent passed to": "autopilot loop enforcement follow-on",
    }
    record["closure_check"] = {
        "slice status": "bounded slice complete",
        "larger-intent status": "open",
        "closure decision": "archive-but-keep-lane-open",
        "why this decision is honest": "The slice landed while the larger intent remained open.",
        "evidence carried forward": "summary reports derived continuations",
        "reopen trigger": "agents continue from archives without concrete ownership",
    }
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["partial_count"] == 1
    assert contract["counts"]["unowned_continuation_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 0
    inspection = contract["inspections"][0]
    assert inspection["classification"] == "unowned_partial"
    assert contract["signals"][0]["kind"] == "unowned_intent_continuation"
    assert contract["derived_follow_up_candidates"] == []
    assert summary["execution_readiness"]["status"] == "narrow-direct-ready"


def test_planning_summary_warns_when_durable_residue_is_archive_only(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[],
    )
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    plan_path = archive_dir / "archive-only-residue.plan.json"
    _write_execplan_record(plan_path, item_id="archive-only-residue", status="completed")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["title"] = "Archive Only Residue"
    record["durable_residue"] = {
        "status": "evidence_only",
        "learned constraint": "Agents should not rely on archived plans as the only home for product-shape motivation.",
        "motivation worth preserving": "Future work should route durable intent to a stronger owner instead of rediscovering it from archives.",
        "canonical owner now": "archive",
        "promotion trigger": "next residue-routing pass",
        "retention after promotion": "shrink",
    }
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["archive_only_durable_residue_count"] == 1
    assert contract["counts"]["attention_count"] == 1
    assert contract["archive_only_durable_residue"][0]["kind"] == "archive_only_durable_residue"
    assert contract["archive_only_durable_residue"][0]["recommended_action"] == (
        "route residue to Memory, docs, contracts, checks, or planning"
    )
    assert contract["signals"][0]["message"].endswith(
        "route the residue to Memory, docs, contracts, checks, or planning instead of relying on archive lookup."
    )
    assert summary["execution_readiness"]["status"] == "narrow-direct-ready"


def test_planning_summary_keeps_historical_archive_pressure_audit_only_when_current_work_is_quiet(
    tmp_path: Path,
) -> None:
    install_bootstrap(target=tmp_path)
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[],
    )
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    plan_path = archive_dir / "generated-cli-migration.plan.json"
    _write_execplan_record(plan_path, item_id="generated-cli-migration", status="completed")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["title"] = "Generated CLI Migration"
    record["intent_satisfaction"] = {
        "original intent": "Remove reliance on a single hand-authored CLI implementation.",
        "was original intent fully satisfied?": "no",
        "evidence of intent satisfaction": "The first adapter slice landed, but runtime work still depends on hand-authored CLI code.",
        "unsolved intent passed to": "intent-derived continuation candidate",
    }
    record["closure_check"] = {
        "slice status": "bounded slice complete",
        "larger-intent status": "open",
        "closure decision": "archive-but-keep-lane-open",
        "why this decision is honest": "The slice landed but the larger generated-CLI intent remains open.",
        "evidence carried forward": "generated adapter proof",
        "reopen trigger": "future direct CLI edits continue",
    }
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]
    readiness = summary["execution_readiness"]

    assert contract["counts"]["unowned_continuation_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 0
    assert readiness["status"] == "narrow-direct-ready"
    assert readiness["historical_derived_follow_up_candidate_count"] == 0


def test_planning_summary_suppresses_child_continuation_consumed_by_later_parent_archive(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    child_path = archive_dir / "source-payload-install-sync-proof.plan.json"
    _write_execplan_record(
        child_path,
        item_id="source-payload-install-sync-proof",
        status="completed",
        references=[
            {
                "kind": "github-issue",
                "target": "#410",
                "label": "root CLI authority audit",
                "role": "closed_item",
                "locator": "GitHub issue",
            },
            {
                "kind": "github-issue",
                "target": "#411",
                "label": "source payload sync proof",
                "role": "closed_item",
                "locator": "GitHub issue",
            },
        ],
    )
    child_record = json.loads(child_path.read_text(encoding="utf-8"))
    child_record["title"] = "Source Payload Install Sync Proof"
    child_record["intent_satisfaction"] = {
        "original intent": "Strengthen architecture boundaries after contract expansion.",
        "was original intent fully satisfied?": "no",
        "evidence of intent satisfaction": "This child slice landed, but parent validation remained open.",
        "unsolved intent passed to": ".agentic-workspace/planning/state.toml architecture-boundary lane for parent validation",
    }
    child_record["closure_check"] = {
        "slice status": "bounded slice complete",
        "larger-intent status": "open",
        "closure decision": "archive-but-keep-lane-open",
        "why this decision is honest": "The child slice landed while parent validation remained open.",
        "evidence carried forward": "source payload proof",
        "reopen trigger": "parent validation fails",
    }
    installer_mod._write_execplan_record(record_path=child_path, record=child_record)

    parent_path = archive_dir / "architecture-boundary-parent-validation.plan.json"
    _write_execplan_record(parent_path, item_id="architecture-boundary-parent-validation", status="completed")
    parent_record = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_record["title"] = "Architecture Boundary Parent Validation"
    parent_record["intent_satisfaction"] = {
        "original intent": "Strengthen architecture boundaries after contract expansion.",
        "was original intent fully satisfied?": "yes",
        "evidence of intent satisfaction": "Parent acceptance mapped to closed children #410 and #411.",
        "unsolved intent passed to": "none",
    }
    parent_record["closure_check"] = {
        "slice status": "parent lane complete",
        "larger-intent status": "closed",
        "closure decision": "archive-and-close",
        "why this decision is honest": "The later parent archive consumed child follow-on refs #410 and #411.",
        "evidence carried forward": "parent proof references #410 and #411",
        "reopen trigger": "new boundary issue opens",
    }
    parent_record["proof_report"] = {
        "validation proof": "summary and reconciliation",
        "proof achieved now": "parent lane validated",
        'evidence for "proof achieved" state': "closed children #410 and #411 were mapped to parent acceptance",
    }
    installer_mod._write_execplan_record(record_path=parent_path, record=parent_record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["partial_count"] == 1
    assert contract["counts"]["superseded_continuation_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 0
    inspection = next(
        item
        for item in contract["inspections"]
        if item["plan"] == ".agentic-workspace/planning/execplans/archive/source-payload-install-sync-proof.plan.json"
    )
    assert inspection["classification"] == "superseded_partial"
    assert inspection["superseded_by"] == [
        ".agentic-workspace/planning/execplans/archive/architecture-boundary-parent-validation.plan.json"
    ]
    assert contract["derived_follow_up_candidates"] == []
    assert summary["execution_readiness"]["status"] == "narrow-direct-ready"


def test_planning_summary_suppresses_archived_child_when_continuation_is_active(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "active-follow-on", status = "in-progress", source = "github:#463", surface = ".agentic-workspace/planning/execplans/active-follow-on.plan.json", why_now = "active continuation for #461" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    active_path = tmp_path / ".agentic-workspace/planning/execplans/active-follow-on.plan.json"
    _write_execplan_record(
        active_path,
        item_id="active-follow-on",
        status="in-progress",
        references=[
            {
                "kind": "github-issue",
                "target": "#463",
                "label": "active follow-on",
                "role": "source_intent",
                "locator": "issue",
            },
            {
                "kind": "github-issue",
                "target": "#461",
                "label": "parent lane",
                "role": "parent_intent",
                "locator": "issue",
            },
        ],
    )

    archive_dir = tmp_path / ".agentic-workspace/planning/execplans/archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    child_path = archive_dir / "completed-child.plan.json"
    _write_execplan_record(
        child_path,
        item_id="completed-child",
        status="completed",
        references=[
            {
                "kind": "github-issue",
                "target": "#462",
                "label": "completed child",
                "role": "closed_item",
                "locator": "issue",
            },
            {
                "kind": "github-issue",
                "target": "#461",
                "label": "parent lane",
                "role": "parent_intent",
                "locator": "issue",
            },
        ],
    )
    child_record = json.loads(child_path.read_text(encoding="utf-8"))
    child_record["intent_satisfaction"]["was original intent fully satisfied?"] = "no"
    child_record["intent_satisfaction"]["unsolved intent passed to"] = ".agentic-workspace/planning/state.toml active continuation for #461"
    child_record["closure_check"]["larger-intent status"] = "open"
    child_record["closure_check"]["closure decision"] = "archive-but-keep-lane-open"
    installer_mod._write_execplan_record(record_path=child_path, record=child_record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["partial_count"] == 1
    assert contract["counts"]["routed_continuation_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 0
    inspection = contract["inspections"][0]
    assert inspection["classification"] == "routed_partial"
    assert inspection["routed_by"] == [".agentic-workspace/planning/execplans/active-follow-on.plan.json"]
    assert contract["derived_follow_up_candidates"] == []
    assert summary["execution_readiness"]["status"] == "planning-backed"


def test_planning_summary_suppresses_archived_child_when_continuation_is_in_roadmap(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "parent-lane", title = "Parent lane", priority = "1", issues = ["#701", "#702"], outcome = "continue parent", reason = "next child #702 remains open", promotion_signal = "after child #700", suggested_first_slice = "#702" },
]
candidates = []
""",
    )

    archive_dir = tmp_path / ".agentic-workspace/planning/execplans/archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    child_path = archive_dir / "completed-child.plan.json"
    _write_execplan_record(
        child_path,
        item_id="completed-child",
        status="completed",
        references=[
            {
                "kind": "github-issue",
                "target": "#700",
                "label": "completed child",
                "role": "source_intent",
                "locator": "issue",
            },
            {
                "kind": "github-issue",
                "target": "#701",
                "label": "parent lane",
                "role": "parent_intent",
                "locator": "issue",
            },
            {
                "kind": "github-issue",
                "target": "#702",
                "label": "next child",
                "role": "next_lane",
                "locator": "issue",
            },
        ],
    )
    child_record = json.loads(child_path.read_text(encoding="utf-8"))
    child_record["intent_satisfaction"]["was original intent fully satisfied?"] = "yes"
    child_record["intent_satisfaction"]["unsolved intent passed to"] = ".agentic-workspace/planning/state.toml roadmap lane parent-lane"
    child_record["closure_check"]["larger-intent status"] = "open"
    child_record["closure_check"]["closure decision"] = "archive-but-keep-lane-open"
    installer_mod._write_execplan_record(record_path=child_path, record=child_record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["partial_count"] == 1
    assert contract["counts"]["routed_continuation_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 0
    inspection = contract["inspections"][0]
    assert inspection["classification"] == "routed_partial"
    assert inspection["intent_satisfied"] == "yes"
    assert inspection["routed_by"] == [".agentic-workspace/planning/state.toml roadmap lane parent-lane"]
    assert contract["derived_follow_up_candidates"] == []
    assert summary["execution_readiness"]["status"] == "roadmap-needs-promotion"


def test_planning_summary_uses_roadmap_refs_for_archived_continuation_routing(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "parent-lane", title = "Parent lane", priority = "1", refs = "GitHub #901, #902", outcome = "continue parent", reason = "remaining work is tracked externally", promotion_signal = "when selected", suggested_first_slice = "next child" },
]
candidates = []
""",
    )

    archive_dir = tmp_path / ".agentic-workspace/planning/execplans/archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    child_path = archive_dir / "completed-child.plan.json"
    _write_execplan_record(
        child_path,
        item_id="completed-child",
        status="completed",
        references=[
            {
                "kind": "github-issue",
                "target": "#900",
                "label": "completed child",
                "role": "source_intent",
                "locator": "issue",
            },
            {
                "kind": "github-issue",
                "target": "#901",
                "label": "parent lane",
                "role": "parent_intent",
                "locator": "issue",
            },
            {
                "kind": "github-issue",
                "target": "#902",
                "label": "next child",
                "role": "next_lane",
                "locator": "issue",
            },
        ],
    )
    child_record = json.loads(child_path.read_text(encoding="utf-8"))
    child_record["intent_satisfaction"]["was original intent fully satisfied?"] = "yes"
    child_record["intent_satisfaction"]["unsolved intent passed to"] = ".agentic-workspace/planning/state.toml roadmap lane parent-lane"
    child_record["closure_check"]["larger-intent status"] = "open"
    child_record["closure_check"]["closure decision"] = "archive-but-keep-lane-open"
    installer_mod._write_execplan_record(record_path=child_path, record=child_record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert {reference["target"] for reference in summary["roadmap"]["candidate_lanes"][0]["references"]} == {"#901", "#902"}
    assert contract["counts"]["partial_count"] == 1
    assert contract["counts"]["routed_continuation_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 0
    inspection = contract["inspections"][0]
    assert inspection["classification"] == "routed_partial"
    assert inspection["routed_by"] == [".agentic-workspace/planning/state.toml roadmap lane parent-lane"]
    assert contract["derived_follow_up_candidates"] == []
    assert summary["execution_readiness"]["status"] == "roadmap-needs-promotion"


def test_planning_summary_suppresses_archived_child_when_continuation_is_in_work_items(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = [
  { id = "parent-lane", type = "lane", title = "Parent lane", maturity = "shaped", status = "deferred", priority = "1", issues = ["#801", "#802"], outcome = "continue parent", reason = "next child #802 remains open", promotion_signal = "after child #800", suggested_first_slice = "#802" },
]

[active]
execplans = []
""",
    )

    archive_dir = tmp_path / ".agentic-workspace/planning/execplans/archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    child_path = archive_dir / "completed-child.plan.json"
    _write_execplan_record(
        child_path,
        item_id="completed-child",
        status="completed",
        references=[
            {
                "kind": "github-issue",
                "target": "#800",
                "label": "completed child",
                "role": "source_intent",
                "locator": "issue",
            },
            {
                "kind": "github-issue",
                "target": "#801",
                "label": "parent lane",
                "role": "parent_intent",
                "locator": "issue",
            },
            {
                "kind": "github-issue",
                "target": "#802",
                "label": "next child",
                "role": "next_lane",
                "locator": "issue",
            },
        ],
    )
    child_record = json.loads(child_path.read_text(encoding="utf-8"))
    child_record["intent_satisfaction"]["was original intent fully satisfied?"] = "yes"
    child_record["intent_satisfaction"]["unsolved intent passed to"] = ".agentic-workspace/planning/state.toml work_items lane parent-lane"
    child_record["closure_check"]["larger-intent status"] = "open"
    child_record["closure_check"]["closure decision"] = "archive-but-keep-lane-open"
    installer_mod._write_execplan_record(record_path=child_path, record=child_record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["partial_count"] == 1
    assert contract["counts"]["routed_continuation_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 0
    inspection = contract["inspections"][0]
    assert inspection["classification"] == "routed_partial"
    assert inspection["intent_satisfied"] == "yes"
    assert inspection["routed_by"] == [".agentic-workspace/planning/state.toml work_items lane parent-lane"]
    assert contract["derived_follow_up_candidates"] == []
    assert summary["execution_readiness"]["status"] == "roadmap-needs-promotion"


def test_planning_summary_suppresses_archived_child_when_parent_ref_is_externally_closed(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#701",
                "title": "Closed parent lane",
                "status": "closed",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "optional",
            },
            {
                "system": "manual",
                "id": "#700",
                "title": "Closed child slice",
                "status": "closed",
                "kind": "issue",
                "parent_id": "#701",
                "planning_residue_expected": "optional",
            },
        ],
    )

    archive_dir = tmp_path / ".agentic-workspace/planning/execplans/archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    child_path = archive_dir / "completed-child.plan.json"
    _write_execplan_record(
        child_path,
        item_id="completed-child",
        status="completed",
        references=[
            {
                "kind": "github-issue",
                "target": "#700",
                "label": "completed child",
                "role": "closed_item",
                "locator": "issue",
            },
            {
                "kind": "github-issue",
                "target": "#701",
                "label": "parent lane",
                "role": "parent_intent",
                "locator": "issue",
            },
        ],
    )
    child_record = json.loads(child_path.read_text(encoding="utf-8"))
    child_record["intent_satisfaction"]["was original intent fully satisfied?"] = "yes"
    child_record["intent_satisfaction"]["unsolved intent passed to"] = "#701 parent assessment"
    child_record["closure_check"]["larger-intent status"] = "open"
    child_record["closure_check"]["closure decision"] = "archive-but-keep-lane-open"
    installer_mod._write_execplan_record(record_path=child_path, record=child_record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["partial_count"] == 1
    assert contract["counts"]["externally_closed_continuation_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 0
    inspection = contract["inspections"][0]
    assert inspection["classification"] == "externally_closed_partial"
    assert inspection["externally_closed_by"] == ["#701"]
    assert contract["signals"] == []
    assert contract["derived_follow_up_candidates"] == []
    assert summary["execution_readiness"]["status"] == "narrow-direct-ready"


def test_planning_summary_suppresses_legacy_archived_child_when_all_tracked_refs_are_closed(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#700",
                "title": "Closed parent",
                "status": "closed",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "optional",
            },
            {
                "system": "manual",
                "id": "#701",
                "title": "Closed child",
                "status": "closed",
                "kind": "issue",
                "parent_id": "#700",
                "planning_residue_expected": "optional",
            },
        ],
    )

    archive_dir = tmp_path / ".agentic-workspace/planning/execplans/archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    child_path = archive_dir / "legacy-completed-child.plan.json"
    _write_execplan_record(child_path, item_id="legacy-completed-child", status="completed", references=[])
    child_record = json.loads(child_path.read_text(encoding="utf-8"))
    child_record["intent_satisfaction"]["was original intent fully satisfied?"] = "yes"
    child_record["intent_satisfaction"]["unsolved intent passed to"] = ".agentic-workspace/planning/state.toml roadmap"
    child_record["closure_check"]["larger-intent status"] = "open"
    child_record["closure_check"]["closure decision"] = "archive-but-keep-lane-open"
    child_record["proof_report"]['evidence for "proof achieved" state'] = "Closed historical refs #700 and #701."
    installer_mod._write_execplan_record(record_path=child_path, record=child_record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["partial_count"] == 1
    assert contract["counts"]["externally_closed_continuation_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 0
    inspection = contract["inspections"][0]
    assert inspection["classification"] == "externally_closed_partial"
    assert inspection["externally_closed_by"] == ["#700", "#701"]
    assert contract["signals"] == []
    assert contract["derived_follow_up_candidates"] == []
    assert summary["execution_readiness"]["status"] == "narrow-direct-ready"


def test_planning_summary_keeps_legacy_archived_child_active_when_any_tracked_ref_is_open_or_missing(
    tmp_path: Path,
) -> None:
    install_bootstrap(target=tmp_path)
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#700",
                "title": "Closed parent",
                "status": "closed",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "optional",
            },
            {
                "system": "manual",
                "id": "#701",
                "title": "Open child",
                "status": "open",
                "kind": "issue",
                "parent_id": "#700",
                "planning_residue_expected": "required",
            },
        ],
    )

    archive_dir = tmp_path / ".agentic-workspace/planning/execplans/archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    child_path = archive_dir / "legacy-open-child.plan.json"
    _write_execplan_record(child_path, item_id="legacy-open-child", status="completed", references=[])
    child_record = json.loads(child_path.read_text(encoding="utf-8"))
    child_record["intent_satisfaction"]["was original intent fully satisfied?"] = "yes"
    child_record["intent_satisfaction"]["unsolved intent passed to"] = ".agentic-workspace/planning/state.toml roadmap"
    child_record["closure_check"]["larger-intent status"] = "open"
    child_record["closure_check"]["closure decision"] = "archive-but-keep-lane-open"
    child_record["proof_report"]['evidence for "proof achieved" state'] = "Mixed historical refs #700, #701, and MISSING-1."
    installer_mod._write_execplan_record(record_path=child_path, record=child_record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["externally_closed_continuation_count"] == 0
    assert contract["counts"]["derived_follow_up_candidate_count"] == 1
    candidate = contract["derived_follow_up_candidates"][0]
    assert candidate["source_plan"] == ".agentic-workspace/planning/execplans/archive/legacy-open-child.plan.json"
    assert candidate["tracked_refs"] == ["#700", "#701", "MISSING-1"]
    assert summary["execution_readiness"]["status"] == "intent-continuation-needs-promotion"


def test_planning_summary_keeps_reopened_legacy_archived_child_active_even_when_refs_are_closed(
    tmp_path: Path,
) -> None:
    install_bootstrap(target=tmp_path)
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#700",
                "title": "Closed parent",
                "status": "closed",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "optional",
            },
            {
                "system": "manual",
                "id": "#701",
                "title": "Closed child",
                "status": "closed",
                "kind": "issue",
                "parent_id": "#700",
                "planning_residue_expected": "optional",
            },
        ],
    )
    _write_finished_work_evidence(
        tmp_path / ".agentic-workspace/planning/finished-work-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#900",
                "title": "Reopened closed historical refs",
                "status": "open",
                "kind": "issue",
                "reopens": ["#700", "#701"],
            }
        ],
    )

    archive_dir = tmp_path / ".agentic-workspace/planning/execplans/archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    child_path = archive_dir / "legacy-reopened-child.plan.json"
    _write_execplan_record(child_path, item_id="legacy-reopened-child", status="completed", references=[])
    child_record = json.loads(child_path.read_text(encoding="utf-8"))
    child_record["intent_satisfaction"]["was original intent fully satisfied?"] = "yes"
    child_record["intent_satisfaction"]["unsolved intent passed to"] = ".agentic-workspace/planning/state.toml roadmap"
    child_record["closure_check"]["larger-intent status"] = "open"
    child_record["closure_check"]["closure decision"] = "archive-but-keep-lane-open"
    child_record["proof_report"]['evidence for "proof achieved" state'] = "Closed but reopened historical refs #700 and #701."
    installer_mod._write_execplan_record(record_path=child_path, record=child_record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["externally_closed_continuation_count"] == 0
    assert contract["counts"]["likely_premature_closeout_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 1
    candidate = contract["derived_follow_up_candidates"][0]
    assert candidate["classification"] == "likely_premature_closeout"
    assert candidate["tracked_refs"] == ["#700", "#701"]
    assert candidate["reopened_by"] == ["#900"]


def test_planning_summary_suppresses_reopened_archive_when_reopening_refs_are_closed(
    tmp_path: Path,
) -> None:
    install_bootstrap(target=tmp_path)
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#900",
                "title": "Closed reopening",
                "status": "closed",
                "kind": "issue",
                "parent_id": "",
                "planning_residue_expected": "optional",
            },
        ],
    )
    _write_finished_work_evidence(
        tmp_path / ".agentic-workspace/planning/finished-work-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#900",
                "title": "Reopened historical refs",
                "status": "open",
                "kind": "issue",
                "reopens": ["#700"],
            }
        ],
    )

    archive_dir = tmp_path / ".agentic-workspace/planning/execplans/archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    child_path = archive_dir / "legacy-reopened-then-closed.plan.json"
    _write_execplan_record(child_path, item_id="legacy-reopened-then-closed", status="completed", references=[])
    child_record = json.loads(child_path.read_text(encoding="utf-8"))
    child_record["intent_satisfaction"]["was original intent fully satisfied?"] = "yes"
    child_record["closure_check"]["larger-intent status"] = "closed"
    child_record["closure_check"]["closure decision"] = "archive-and-close"
    child_record["proof_report"]['evidence for "proof achieved" state'] = "Historical ref #700 was later reopened by #900."
    installer_mod._write_execplan_record(record_path=child_path, record=child_record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["likely_premature_closeout_count"] == 0
    assert contract["counts"]["externally_closed_continuation_count"] == 0
    assert contract["counts"]["derived_follow_up_candidate_count"] == 0
    inspection = contract["inspections"][0]
    assert inspection["classification"] == "clearly_landed"
    assert summary["execution_readiness"]["status"] == "narrow-direct-ready"


def test_planning_summary_suppresses_partial_archive_when_unsolved_ref_is_closed(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#230",
                "title": "Closed parent lane",
                "status": "closed",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "optional",
            },
        ],
    )

    archive_dir = tmp_path / ".agentic-workspace/planning/execplans/archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    child_path = archive_dir / "closed-unsolved-ref.plan.json"
    _write_execplan_record(
        child_path,
        item_id="closed-unsolved-ref",
        status="completed",
        references=[
            {
                "kind": "github-issue",
                "target": "#347",
                "label": "closed child",
                "role": "closed_item",
                "locator": "issue",
            },
        ],
    )
    child_record = json.loads(child_path.read_text(encoding="utf-8"))
    child_record["intent_satisfaction"]["was original intent fully satisfied?"] = "no"
    child_record["intent_satisfaction"]["unsolved intent passed to"] = "#230"
    child_record["closure_check"]["larger-intent status"] = "open"
    child_record["closure_check"]["closure decision"] = "archive-but-keep-lane-open"
    installer_mod._write_execplan_record(record_path=child_path, record=child_record)

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]

    assert contract["counts"]["partial_count"] == 1
    assert contract["counts"]["externally_closed_continuation_count"] == 1
    assert contract["counts"]["derived_follow_up_candidate_count"] == 0
    inspection = contract["inspections"][0]
    assert inspection["classification"] == "externally_closed_partial"
    assert inspection["externally_closed_by"] == ["#230"]
    assert summary["execution_readiness"]["status"] == "narrow-direct-ready"


def test_planning_summary_uses_reference_roles_before_prose_issue_refs(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    plan_path = archive_dir / "role-aware-closeout.plan.json"
    _write_execplan_record(
        plan_path,
        item_id="role-aware-closeout",
        status="completed",
        references=[
            {
                "kind": "github-issue",
                "target": "#500",
                "label": "delivered slice",
                "role": "closed_item",
                "locator": "issue",
            },
            {
                "kind": "github-issue",
                "target": "#442",
                "label": "parent lane",
                "role": "parent_intent",
                "locator": "issue",
            },
            {
                "kind": "github-issue",
                "target": "#445",
                "label": "next lane",
                "role": "next_lane",
                "locator": "issue",
            },
        ],
    )
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["proof_report"] = {
        "validation proof": "focused tests",
        "proof achieved now": "implemented #500 while preserving parent #442 and next lane #445.",
        'evidence for "proof achieved" state': "role-aware refs distinguish closure from context",
    }
    installer_mod._write_execplan_record(record_path=plan_path, record=record)
    _write_finished_work_evidence(
        tmp_path / ".agentic-workspace/planning/finished-work-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#600",
                "title": "Parent continuation remains open",
                "status": "open",
                "kind": "lane",
                "reopens": ["#442"],
            }
        ],
    )

    summary = planning_summary(target=tmp_path)
    contract = summary["finished_work_inspection_contract"]
    inspection = contract["inspections"][0]

    assert contract["counts"]["role_aware_reference_plan_count"] == 1
    assert contract["counts"]["non_closure_reference_count"] == 2
    assert contract["counts"]["likely_premature_closeout_count"] == 0
    assert contract["counts"]["clearly_landed_count"] == 1
    assert inspection["tracked_refs"] == ["#500"]
    assert inspection["non_closure_refs"] == ["#442", "#445"]
    assert inspection["reference_roles"]["by_role"] == {
        "closed_item": ["#500"],
        "next_lane": ["#445"],
        "parent_intent": ["#442"],
    }


def test_planning_summary_exposes_closeout_distillation_contract(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "distill-closeout.plan.json"
    _write_execplan_record(plan_path, item_id="distill-closeout", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["required_continuation"] = {
        "required follow-on for the larger intended outcome": "yes",
        "owner surface": ".agentic-workspace/planning/state.toml",
        "activation trigger": "continue #344",
    }
    record["execution_summary"] = {
        "outcome delivered": "Added closeout distillation.",
        "validation confirmed": "focused tests",
        "follow-on routed to": "#344 memory routing",
        "post-work posterity capture": "No durable learning beyond continuation; local execution details should die.",
        "knowledge promoted (Memory/Docs/Config)": "none",
        "resume from": "next milestone",
    }
    record["references"] = [{"kind": "external-work", "target": "#344", "label": "Memory routing follow-up", "role": "follow-up"}]
    installer_mod._write_execplan_record(record_path=plan_path, record=record)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        (
            "[todo]\n"
            "active_items = [\n"
            '  { id = "distill-closeout", status = "in-progress", surface = ".agentic-workspace/planning/execplans/distill-closeout.plan.json", why_now = "prove closeout distillation." },\n'
            "]\n"
            "queued_items = []\n"
        ),
    )

    summary = planning_summary(target=tmp_path)
    contract = summary["closeout_distillation_contract"]

    assert "closeout_distillation_contract" in summary["schema"]["shared_fields"]
    assert contract["status"] == "present"
    assert (
        contract["archive_role"]
        == "completed execplans are removed after distillation by default; legacy archives are compatibility evidence only"
    )
    assert contract["counts"]["intentionally_discarded_count"] == 1
    assert contract["buckets"]["discard"][0]["owner"] == "discard"
    assert contract["buckets"]["continuation"][0]["summary"] == "#344 memory routing"
    assert contract["buckets"]["issue_follow_up"][0]["source"] == "#344"

    report = planning_report(target=tmp_path)
    assert report["closeout_distillation"]["counts"]["intentionally_discarded_count"] == 1
    assert report["active"]["closeout_distillation_contract"]["buckets"]["discard"][0]["source"] == (
        "execution_summary.knowledge promoted (Memory/Docs/Config)"
    )


def test_planning_report_promotes_finished_work_inspection_signals_to_findings(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    _write(
        archive_dir / "system-intent-and-planning-trust-2026-04-21.md",
        (
            "# System Intent And Planning Trust\n\n"
            "## Intent Satisfaction\n\n"
            "- Was original intent fully satisfied?: yes\n\n"
            "## Closure Check\n\n"
            "- Closure decision: archive-and-close\n"
            "- Larger-intent status: closed\n\n"
            "Implemented #220 and #222.\n"
        ),
    )
    _write_finished_work_evidence(
        tmp_path / ".agentic-workspace/planning/finished-work-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#260",
                "title": "Finished-work intent inspection",
                "status": "open",
                "kind": "lane",
                "reopens": ["#220"],
            }
        ],
    )

    report = planning_report(target=tmp_path)

    assert report["finished_work_inspection"]["counts"]["likely_premature_closeout_count"] == 1
    assert report["status"]["finished_work_inspection_attention_count"] == 1
    assert report["next_action"]["summary"].startswith("Inspect archived closeouts flagged by reopening evidence")
    assert any(finding["warning_class"] == "likely_premature_closeout" for finding in report["findings"])


def test_planning_summary_dedupes_unavailable_projection_reason_fragments(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    summary = planning_summary(target=tmp_path, profile="compact")

    assert summary["projection_state"]["status"] == "idle"
    assert summary["projection_state"]["reason"] == "no active planning record"
    assert "projection_state" in summary["schema"]["shared_fields"]
    assert summary["hierarchy_contract"]["reason"] == "no active planning record"
    assert summary["hierarchy_contract"]["reason_code"] == "idle-no-active-planning-record"
    assert summary["handoff_contract"]["reason_code"] == "idle-no-active-planning-record"


def test_planning_summary_can_expose_active_contract_from_execplan_without_todo_row(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "# TODO\n\n## Now\n\n- Active execplan: .agentic-workspace/planning/execplans/plan-alpha.md\n",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    summary = planning_summary(target=tmp_path)

    assert summary["todo"]["active_count"] == 0
    assert summary["execplans"]["active_count"] == 1
    assert summary["planning_record"]["status"] == "present"
    assert summary["planning_record"]["task"]["id"] == "plan-alpha"
    assert summary["planning_record"]["task"]["surface"] == ".agentic-workspace/planning/execplans/plan-alpha.md"
    assert summary["planning_record"]["continuation_owner"] == ".agentic-workspace/planning/execplans/plan-alpha.md"
    assert summary["active_contract"]["status"] == "present"
    assert summary["resumable_contract"]["status"] == "present"
    assert summary["follow_through_contract"]["status"] == "present"
    assert summary["context_budget_contract"]["status"] == "present"
    assert summary["hierarchy_contract"]["status"] == "present"
    assert summary["active_contract"]["todo_item"]["id"] == ""
    assert summary["active_contract"]["minimal_refs"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/plan-alpha.md",
    ]


def test_planning_summary_schema_describes_projection_fields(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")

    summary = planning_summary(target=tmp_path)

    assert summary["schema"]["view_fields"]["planning_record"][0] == "task"
    assert "intent_interpretation" in summary["schema"]["view_fields"]["planning_record"]
    assert "execution_run" in summary["schema"]["view_fields"]["planning_record"]
    assert "finished_run_review" in summary["schema"]["view_fields"]["planning_record"]
    assert "delegation_outcome_feedback" in summary["schema"]["view_fields"]["planning_record"]
    assert "post_decomposition_delegation" in summary["schema"]["view_fields"]["planning_record"]
    assert "tool_verification" in summary["schema"]["view_fields"]["planning_record"]
    assert "system_intent_alignment" in summary["schema"]["view_fields"]["planning_record"]
    assert "tool_verification" in summary["schema"]["view_fields"]["resumable_contract"]
    assert "follow_through_contract" in summary["schema"]["shared_fields"]
    assert "intent_interpretation_contract" in summary["schema"]["shared_fields"]
    assert "context_budget_contract" in summary["schema"]["shared_fields"]
    assert "execution_run_contract" in summary["schema"]["shared_fields"]
    assert "finished_run_review_contract" in summary["schema"]["shared_fields"]
    assert "intent_validation_contract" in summary["schema"]["shared_fields"]
    assert "finished_work_inspection_contract" in summary["schema"]["shared_fields"]
    assert "hierarchy_contract" in summary["schema"]["shared_fields"]
    assert "handoff_contract" in summary["schema"]["shared_fields"]
    assert "planning_surface_health" in summary["schema"]["view_fields"]
    assert "literal_request" in summary["schema"]["view_fields"]["intent_interpretation_contract"]
    assert "live_working_set" in summary["schema"]["view_fields"]["context_budget_contract"]
    assert "pre_work_config_pull" in summary["schema"]["view_fields"]["context_budget_contract"]
    assert "pre_work_memory_pull" in summary["schema"]["view_fields"]["context_budget_contract"]
    assert "run_status" in summary["schema"]["view_fields"]["execution_run_contract"]
    assert "changed_surfaces" in summary["schema"]["view_fields"]["execution_run_contract"]
    assert "review_status" in summary["schema"]["view_fields"]["finished_run_review_contract"]
    assert "config_compliance" in summary["schema"]["view_fields"]["finished_run_review_contract"]
    assert "config_trust" in summary["schema"]["view_fields"]["finished_run_review_contract"]
    assert "counts" in summary["schema"]["view_fields"]["intent_validation_contract"]
    assert "inspections" in summary["schema"]["view_fields"]["finished_work_inspection_contract"]
    assert "parent_lane" in summary["schema"]["view_fields"]["hierarchy_contract"]
    assert "next_likely_slice" in summary["schema"]["view_fields"]["follow_through_contract"]
    assert "read_first" in summary["schema"]["view_fields"]["handoff_contract"]
    assert "pre_work_config_pull" in summary["schema"]["view_fields"]["handoff_contract"]
    assert "pre_work_memory_pull" in summary["schema"]["view_fields"]["handoff_contract"]
    assert "system_intent_alignment" in summary["schema"]["view_fields"]["handoff_contract"]
    assert "post_decomposition_delegation" in summary["schema"]["view_fields"]["handoff_contract"]
    assert "delegation_outcome_feedback" in summary["schema"]["view_fields"]["handoff_contract"]


def test_planning_summary_exposes_ownership_review(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")

    summary = planning_summary(target=tmp_path)
    report = planning_report(target=tmp_path)
    planning_cli._print_summary(summary)
    planning_cli._print_report(report)
    out = capsys.readouterr().out

    ownership_review = summary["ownership_review"]
    assert ownership_review["status"] == "present"
    assert ".agentic-workspace/planning/" in ownership_review["package_owned_roots"]
    assert ".agentic-workspace/planning/state.toml" not in ownership_review["repo_owned_surfaces"]
    assert "AGENTS.md" in ownership_review["repo_owned_surfaces"]
    assert "ROADMAP.md" not in ownership_review["repo_owned_surfaces"]
    assert ownership_review["minimal_repo_hook"] == "AGENTS.md#agentic-workspace:workflow"
    assert "ownership_review" in summary["schema"]["shared_fields"]
    assert "Ownership review:" in out


def test_summary_command_defaults_to_tiny_json_and_accepts_verbose_detail(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.md", why_now = "keep compact startup cheap." }
]
queued_items = []

[roadmap]
lanes = [
  { id = "tracked-lane", title = "Tracked lane", priority = "first", issues = ["EXT-1"], outcome = "Keep tracked.", reason = "Needed.", promotion_signal = "Promote when needed.", suggested_first_slice = "Do the thing." },
]
candidates = [
  { priority = "first", summary = "Tracked lane" },
]
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    exit_code = planning_cli.main(["summary", "--target", str(tmp_path), "--format", "json"])
    default_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert default_payload["profile"] == "tiny"
    assert default_payload["schema"]["schema_version"] == "planning-summary-tiny-schema/v1"
    assert default_payload["schema"]["select_command"] == "agentic-workspace summary --select <field.path> --format json"
    assert default_payload["schema"]["verbose_command"] == "agentic-workspace summary --verbose --format json"

    exit_code = planning_cli.main(["summary", "--target", str(tmp_path), "--format", "json", "--verbose"])
    full_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert full_payload["profile"] == "full"
    assert full_payload["schema"]["schema_version"] == "planning-summary-schema/v1"
    assert full_payload["schema"]["command"] == "agentic-workspace summary --format json --verbose"
    assert "candidate_lanes" in full_payload["roadmap"]


def test_summary_command_accepts_task_scoped_compact_context(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "adaptive-routing", status = "active", surface = ".agentic-workspace/planning/execplans/adaptive-routing.md", why_now = "adaptive routing needs a bounded slice." }
]
queued_items = []

[roadmap]
lanes = []
candidates = [
  { priority = "first", summary = "Adaptive read budget routing" },
]
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "adaptive-routing.md", _minimal_execplan())

    exit_code = planning_cli.main(
        [
            "summary",
            "--target",
            str(tmp_path),
            "--format",
            "json",
            "--task",
            "Improve adaptive read budget routing",
            "--changed",
            "generated/workspace/python/cli.py",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["profile"] == "compact-task"
    assert payload["schema"]["schema_version"] == "planning-summary-compact-task-schema/v1"
    assert payload["task_scope"]["task_text_available"] is True
    assert payload["task_scope"]["changed_paths"] == ["generated/workspace/python/cli.py"]
    assert "adaptive" in payload["task_scope"]["match_tokens"]
    assert "historical_audit_pressure" not in payload
    assert payload["detail_commands"]["broad_compact"] == "agentic-workspace summary --verbose --format json"


def test_task_scoped_summary_prefers_matched_roadmap_when_active_only_matches_generic_words(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "typescript-lane", status = "active", surface = ".agentic-workspace/planning/execplans/typescript-lane.md", why_now = "active lane." }
]
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-831-scoped-generated-surface-repair", status = "next", priority = "P1", title = "Keep generated-surface repair scoped to the reported drift", suggested_first_slice = "Change the generated-handoff repair action." },
]
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "typescript-lane.md", _minimal_execplan())

    exit_code = planning_cli.main(
        [
            "summary",
            "--target",
            str(tmp_path),
            "--format",
            "json",
            "--task",
            "Implement the prioritized friction lane",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["task_scope"]["recommendation_source"] == "matched-roadmap-candidate"
    assert payload["task_scope"]["matched_roadmap_candidate"]["id"] == "github-831-scoped-generated-surface-repair"


def test_planning_summary_human_view_starts_with_planning_record(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Candidate alpha; promote when maintained report signal appears.

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    summary = planning_summary(target=tmp_path)
    planning_cli._print_summary(summary)
    out = capsys.readouterr().out

    assert "Planning-surface health:" in out
    assert "- Status: clean" in out
    assert "Planning record:" in out
    assert "Planning hierarchy view:" in out
    assert "Parent lane: plan-alpha-lane" in out
    assert "Requested outcome: Keep scope clear." in out
    assert "Continuation owner: .agentic-workspace/planning/execplans/plan-alpha.md" in out
    assert "Active contract view:" in out
    assert "Resumable contract view:" in out
    assert "Follow-through contract view:" in out
    assert "Context budget contract view:" in out
    assert "Intent-interpretation contract view:" in out
    assert "Execution-run contract view:" in out
    assert "Finished-run review contract view:" in out


def test_summary_text_prints_planning_record_before_contract_views(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n\n## Next Candidate Queue\n\n- Candidate alpha\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    exit_code = planning_cli.main(["summary", "--target", str(tmp_path)])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "Planning hierarchy view:" in captured
    assert "Planning record:" in captured
    assert "Active contract view:" in captured
    assert "Resumable contract view:" in captured
    assert captured.index("Planning record:") < captured.index("Active contract view:")
    assert "- Next action: Add one checker." in captured


def test_summary_text_prints_required_tools_when_declared(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan_with_required_tools())

    exit_code = planning_cli.main(["summary", "--target", str(tmp_path)])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "- Required tools: browser, gh" in captured


def test_planning_report_exposes_hierarchy_projection(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: report-lane
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/report-lane.md
  Why now: derive compact module state.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Candidate Lanes

- Lane: Report lane parent
  ID: plan-alpha-lane
  Priority: first
  Issues: #140
  Outcome: test the hierarchy projection.
  Why now: exercise the derived hierarchy view.
  Promotion signal: promote when report output needs a live parent lane.
  Suggested first slice: use one real plan.
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "report-lane.md", _minimal_execplan())

    report = planning_report(target=tmp_path)

    assert report["active"]["hierarchy_contract"]["status"] == "present"
    assert report["active"]["hierarchy_contract"]["parent_lane"]["id"] == "plan-alpha-lane"
    assert report["active"]["hierarchy_contract"]["parent_lane"]["title"] == "Report lane parent"


def test_planning_summary_tracks_near_term_todo_queue(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: active slice first.

- ID: plan-beta
  Status: planned
  Surface: direct
  Why now: next same-thread chunk after the active slice lands.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Candidate Lanes

- Lane: Report lane parent
  ID: plan-alpha-lane
  Priority: first
  Issues: #140
  Outcome: test the hierarchy projection.
  Why now: exercise the derived hierarchy view.
  Promotion signal: promote when report output needs a live parent lane.
  Suggested first slice: use one real plan.
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    summary = planning_summary(target=tmp_path)
    report = planning_report(target=tmp_path)

    assert summary["todo"]["queued_count"] == 1
    assert summary["todo"]["queued_items"][0]["id"] == "plan-beta"
    assert summary["hierarchy_contract"]["near_term_queue"][0]["id"] == "plan-beta"
    assert report["status"]["queued_todo_count"] == 1


def test_resolve_target_root_keeps_explicit_repo_target_when_local_tree_exists(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    (repo_root / ".agentic-workspace" / "local-only").mkdir(parents=True)

    resolved = installer_mod.resolve_target_root(repo_root)

    assert resolved == repo_root


def test_resolve_target_root_local_only_uses_agentic_workspace_local_only_subtree(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)

    resolved = installer_mod.resolve_target_root(repo_root, local_only=True)

    assert resolved == repo_root / ".agentic-workspace" / "local-only"
