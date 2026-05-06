from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from planning_test_support import *


def test_planning_summary_projects_handoff_role_metadata(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json", why_now = "prove handoff role metadata is queryable.", decision_owner = "human", strategy_role = "product/architecture", owner_role = "implementation", delivery_role = "implementation", review_role = "validation", knowledge_owner = "planning/docs", handoff_ready = true },
]
queued_items = []

[roadmap]
lanes = []
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
    handoff = planning_handoff(target=tmp_path)

    expected_role_metadata = {
        "decision_owner": "human",
        "strategy_role": "product/architecture",
        "owner_role": "implementation",
        "delivery_role": "implementation",
        "review_role": "validation",
        "knowledge_owner": "planning/docs",
        "handoff_ready": True,
    }
    assert summary["active_contract"]["role_metadata"] == expected_role_metadata
    assert summary["active_contract"]["next_role_needed"] == "implementation"
    assert summary["planning_record"]["role_metadata"] == expected_role_metadata
    assert summary["handoff_contract"]["role_metadata"] == expected_role_metadata
    assert summary["handoff_contract"]["next_role_needed"] == "implementation"
    assert compact["handoff_contract"]["role_metadata"] == expected_role_metadata
    assert handoff["handoff_contract"]["role_metadata"] == expected_role_metadata


def test_planning_summary_and_handoff_expose_structured_execplan_references(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: keep explicit references queryable for continuation and handoff.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write_execplan_record(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json",
        references=[
            {
                "kind": "issue",
                "target": "#280",
                "role": "related-work",
                "label": "Structured references",
            },
            {
                "kind": "file",
                "target": "packages/planning/src/repo_planning_bootstrap/installer.py",
                "role": "implementation-target",
                "locator": "L2000-L2100",
            },
        ],
    )

    summary = planning_summary(target=tmp_path)
    handoff = planning_handoff(target=tmp_path)

    assert summary["planning_record"]["references"] == [
        {
            "kind": "issue",
            "target": "#280",
            "role": "related-work",
            "label": "Structured references",
        },
        {
            "kind": "file",
            "target": "packages/planning/src/repo_planning_bootstrap/installer.py",
            "role": "implementation-target",
            "locator": "L2000-L2100",
        },
    ]
    assert "#280" in summary["active_contract"]["minimal_refs"]
    assert "packages/planning/src/repo_planning_bootstrap/installer.py" in summary["active_contract"]["minimal_refs"]
    assert handoff["handoff_contract"]["references"][0]["target"] == "#280"
    assert handoff["handoff_contract"]["references"][1]["role"] == "implementation-target"


def test_planning_summary_and_handoff_project_review_residue_from_structured_references(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: keep review residue queryable without rereading full review artifacts.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write_execplan_record(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json",
        references=[
            {
                "kind": "review",
                "target": ".agentic-workspace/planning/reviews/review-alpha.review.json",
                "role": "review-target",
                "label": "Review Alpha",
            }
        ],
    )
    _write_review_record(tmp_path / ".agentic-workspace" / "planning" / "reviews" / "review-alpha.review.json")

    summary = planning_summary(target=tmp_path)
    handoff = planning_handoff(target=tmp_path)

    assert summary["planning_record"]["review_residue"] == [
        {
            "kind": "review",
            "target": ".agentic-workspace/planning/reviews/review-alpha.review.json",
            "role": "review-target",
            "label": "Review Alpha",
            "title": "Review Alpha",
            "finding_count": 1,
            "finding_titles": ["stale residue"],
            "promotion_targets": [".agentic-workspace/planning/state.toml (roadmap)"],
            "recommendation": {
                "promote": "yes",
                "defer": "no",
                "dismiss": "no",
            },
            "retention": {
                "closeout shape": "shrink",
                "trigger": "after the finding is promoted into planning state",
                "proof surface": "canonical review record plus promoted planning residue",
            },
        }
    ]
    assert handoff["handoff_contract"]["review_residue"][0]["target"] == ".agentic-workspace/planning/reviews/review-alpha.review.json"
    assert handoff["handoff_contract"]["review_residue"][0]["finding_titles"] == ["stale residue"]
    assert handoff["handoff_contract"]["review_residue"][0]["retention"]["closeout shape"] == "shrink"


def test_planning_handoff_schema_names_required_worker_packet_fields(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")

    handoff = planning_handoff(target=tmp_path)

    assert handoff["handoff_contract"]["status"] == "unavailable"
    assert handoff["schema"]["required_worker_packet_fields"] == [
        "intent",
        "constraints",
        "read_first_refs",
        "owned_scope",
        "proof_expectations",
        "stop_conditions",
        "return_contract",
        "target_posture",
    ]
    assert "bounded execplan" in handoff["schema"]["unavailable_fallback"]


def test_planning_handoff_derives_compact_worker_contract(tmp_path: Path) -> None:
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
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    handoff = planning_handoff(target=tmp_path)

    assert handoff["kind"] == "planning-handoff/v1"
    assert handoff["schema"]["schema_version"] == "planning-handoff-schema/v1"
    assert handoff["schema"]["canonical_doc"] == ".agentic-workspace/docs/execution-flow-contract.md"
    assert handoff["handoff_contract"]["status"] == "present"
    assert handoff["handoff_contract"]["next_action"] == "Add one checker."
    assert handoff["handoff_contract"]["capability_posture"]["execution class"] == "mechanical-follow-through"
    assert handoff["handoff_contract"]["capability_posture"]["recommended strength"] == "weak"
    assert handoff["handoff_contract"]["context_budget"]["status"] == "present"
    assert handoff["handoff_contract"]["intent_interpretation"]["status"] == "present"
    assert handoff["handoff_contract"]["execution_bounds"]["allowed paths"] == "scripts/check/check_planning_surfaces.py"
    assert handoff["handoff_contract"]["stop_conditions"]["stop when"].startswith("the work needs broader")
    assert handoff["handoff_contract"]["return_with"]["execution_summary_fields"][3] == "post-work posterity capture"
    assert handoff["handoff_contract"]["return_with"]["finished_run_review_fields"][0] == "review status"
    assert handoff["handoff_contract"]["return_with"]["finished_run_review_fields"][4] == "config compliance"
    assert handoff["handoff_contract"]["return_with"]["prose_templates"]["handoff_or_closeout"]["sections"] == [
        "Intent",
        "What changed",
        "Proof",
        "Remaining risk",
        "Durable residue",
        "Next owner",
    ]
    assert handoff["handoff_contract"]["worker_contract"]["worker_must_not_own_by_default"][0] == "roadmap routing"


def test_planning_handoff_command_emits_json(tmp_path: Path, capsys) -> None:
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
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    exit_code = planning_cli.main(["handoff", "--target", str(tmp_path), "--format", "json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "planning-handoff/v1"
    assert payload["handoff_contract"]["status"] == "present"
