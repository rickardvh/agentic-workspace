from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def _write_repo_local_proof_target(target: Path) -> None:
    _init_git_repo(target)
    _write(
        target / "Makefile",
        """
schema-reference-docs:
\tpython -c "print('schema docs')"

typecheck:
\tpython -m compileall src

typecheck-planning:
\tpython -m compileall packages/planning/src

check-planning:
\tpython -c "print('planning checks')"

test-workspace:
\tpython -c "print('workspace tests')"

test-planning:
\tpython -c "print('planning tests')"
""",
    )
    _write(target / "scripts" / "check" / "check_agent_aids.py", "print('agent aids ok')\n")
    _write(target / "scripts" / "check" / "check_generated_command_packages.py", "print('generated packages ok')\n")
    _write(target / "scripts" / "generate" / "generate_command_packages.py", "print('generate packages ok')\n")
    _write(target / "README.md", "# Fixture\n")
    _write(target / "docs" / ".keep", "")
    _write(target / ".agentic-workspace" / "docs" / "agent-installation.md", "# Install\n")
    _write(target / "packages" / "planning" / "README.md", "# Planning\n")
    _write(target / "packages" / "memory" / "README.md", "# Memory\n")
    _write(
        target / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.proof_profiles.workspace_behavior]
required_commands = ["make test-workspace"]
optional_commands = []
review_aids = []

[assurance.subsystem_profiles.workspace-cli-runtime]
assurance_level = "high"
scope_refs = ["ownership.subsystems.workspace-cli-runtime"]
requirement_refs = [".agentic-workspace/OWNERSHIP.toml#subsystems.workspace-cli-runtime"]
required_evidence = ["workspace_runtime_proof"]
proof_profile = "workspace_behavior"
force = "required-before-closeout"
blocked_without_evidence = ["claim-work-complete"]
claim_boundary = "workspace-runtime-routing"
""",
    )
    _write(
        target / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "workspace-cli-runtime"
paths = ["generated/workspace/python/**", "src/agentic_workspace/workspace_runtime*.py"]
owns = ["workspace command routing"]
proof = ["uv run pytest tests/test_workspace_cli.py -q"]
""",
    )
    _write(
        target / ".agentic-workspace" / "verification" / "manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[scenarios.generated_adapter_local_conformance]
protocol_id = "generated_adapter_conformance"
title = "Generated adapter local conformance"
steps = []
expected_observations = []
pass_evidence_labels = ["generated_adapter_conformance"]
fail_evidence_labels = ["generated_adapter_conformance_drift"]

[scenarios.closeout_intent_satisfaction_review]
protocol_id = "closeout_intent_satisfaction"
title = "Closeout intent satisfaction review"
steps = []
expected_observations = []
pass_evidence_labels = ["closeout_intent_satisfaction"]
fail_evidence_labels = ["closeout_intent_gap"]

[scenarios.requirement_grounding_delegation_review]
protocol_id = "requirement_grounding_delegation"
title = "Requirement grounding delegation review"
steps = []
expected_observations = []
pass_evidence_labels = ["requirement_grounding_delegation"]
fail_evidence_labels = ["requirement_grounding_gap"]

[protocols.generated_adapter_conformance]
title = "Generated adapter conformance"
purpose = "Generated workspace adapter changes need conformance evidence."
applies_to_paths = ["generated/workspace/python/**"]
scenario_refs = ["generated_adapter_local_conformance"]
steps = []
expected_evidence = ["generated_adapter_conformance"]
review_owner = "maintainer"

[protocols.closeout_intent_satisfaction]
title = "Closeout intent satisfaction"
purpose = "Workspace runtime changes need closeout intent review."
applies_to_paths = ["generated/workspace/python/**", "src/agentic_workspace/workspace_runtime*.py"]
scenario_refs = ["closeout_intent_satisfaction_review"]
steps = []
expected_evidence = ["closeout_intent_satisfaction"]
review_owner = "maintainer"

[protocols.requirement_grounding_delegation]
title = "Requirement grounding delegation"
purpose = "Workspace runtime changes need requirement grounding review."
applies_to_paths = ["generated/workspace/python/**", "src/agentic_workspace/workspace_runtime*.py"]
scenario_refs = ["requirement_grounding_delegation_review"]
steps = []
expected_evidence = ["requirement_grounding_delegation"]
review_owner = "maintainer"

[proof_routes.generated_adapter_conformance]
protocol_refs = ["generated_adapter_conformance"]
scenario_refs = ["generated_adapter_local_conformance"]
commands = [
  "uv run python scripts/generate/generate_command_packages.py --check",
  "uv run python scripts/check/check_generated_command_packages.py --require-node",
]
proof_lane_hint = "generated-adapter-conformance"

[proof_routes.closeout_intent_satisfaction]
protocol_refs = ["closeout_intent_satisfaction"]
scenario_refs = ["closeout_intent_satisfaction_review"]
commands = ["uv run python scripts/run_agentic_workspace.py report --target . --section closeout_trust --format json"]
proof_lane_hint = "closeout-intent-satisfaction"

[proof_routes.requirement_grounding_delegation]
protocol_refs = ["requirement_grounding_delegation"]
scenario_refs = ["requirement_grounding_delegation_review"]
commands = [
  "uv run python scripts/run_agentic_workspace.py implement --changed <paths> --select requirement_grounding,context.delegation_decision,context.plan_delegation_packet --format json",
]
proof_lane_hint = "requirement-grounding-delegation"
""",
    )
    _write(
        target / ".agentic-workspace" / "system-intent" / "intent.toml",
        """
schema_version = 1
kind = "workspace-system-intent/v1"
summary = "Keep proof routing scoped."
governing_intents = []
anti_intents = []
decision_tests = ["Use focused proof selection for changed paths."]
open_questions = []
confidence = "high"
needs_review = false
""",
    )


def _write_empty_proof_planning_state(target_root: Path) -> None:
    _write(
        target_root / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )


def test_proof_runtime_helpers_route_through_proof_owner(tmp_path: Path) -> None:
    assert workspace_runtime_primitives._verification_report_payload is workspace_runtime_proof._verification_report_payload
    assert workspace_runtime_primitives._tiny_proof_payload is workspace_runtime_proof._tiny_proof_payload
    assert workspace_runtime_primitives._tiny_proof_obligations_payload is workspace_runtime_proof._tiny_proof_obligations_payload
    assert workspace_runtime_primitives._active_planning_record_for_proof is workspace_runtime_proof._active_planning_record_for_proof
    assert workspace_runtime_implement._verification_report_payload is workspace_runtime_proof._verification_report_payload
    assert workspace_runtime_implement._tiny_proof_obligations_payload is workspace_runtime_proof._tiny_proof_obligations_payload
    assert workspace_runtime_core._active_planning_record_for_proof(target_root=tmp_path) == {
        "status": "unavailable",
        "reason": "planning state unavailable",
    }


def test_tiny_proof_obligations_summarizes_multiple_manual_obligations() -> None:
    payload = workspace_runtime_proof._tiny_proof_obligations_payload(
        {
            "kind": "agentic-workspace/proof-obligations/v1",
            "required_proof": {
                "status": "required",
                "commands": ["make test-workspace"],
                "manual_verification_required": True,
                "manual_obligation_count": 2,
                "manual_obligations": [
                    {
                        "id": "verification:first",
                        "required": True,
                        "status": "missing-evidence",
                        "missing_evidence": ["first"],
                        "reference_material": ["docs/first.md"],
                        "claim_boundary": "blocked",
                    },
                    {
                        "id": "verification:second",
                        "required": True,
                        "status": "missing-evidence",
                        "missing_evidence": ["second"],
                        "reference_material": ["docs/second.md"],
                        "claim_boundary": "blocked",
                    },
                ],
                "action_effect": {"force": "required_before_claim", "blocked_until_reconciled": ["claim-task-complete"]},
            },
            "recommended_confidence_checks": {"status": "available", "commands": [], "rule": "advisory only"},
            "completion_claim_rule": "Completion claims remain blocked.",
        }
    )

    required = payload["required_proof"]
    assert required["manual_obligation_count"] == 2
    assert [item["id"] for item in required["manual_obligations"]] == ["verification:first", "verification:second"]
    assert required["manual_obligations"][0]["resolution"] == {
        "inspect": ["docs/first.md"],
        "record": ["first"],
        "detail_selector": "proof.proof_obligations.required_proof.manual_obligations",
        "closeout_format": "manual obligation <id>: inspected <refs>; recorded <evidence>; claim boundary <claim_boundary>",
    }


def test_proof_command_reports_routes_and_current_health(tmp_path: Path, monkeypatch, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "planning").mkdir()
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))
    monkeypatch.setattr(
        cli,
        "_run_lifecycle_command",
        lambda **kwargs: {
            "health": "healthy",
            "warnings": [],
            "needs_review": [],
            "stale_generated_surfaces": [],
        },
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["canonical_doc"] == ".agentic-workspace/docs/proof-surfaces-contract.md"
    assert payload["command"] == "agentic-workspace proof --target ./repo --format json"
    assert payload["default_routes"]["planning_surfaces"] == "agentic-workspace summary --target ./repo --format json"
    assert payload["current"]["installed_modules"] == ["planning"]
    assert payload["current"]["status_health"] == "healthy"
    assert payload["current"]["doctor_health"] == "healthy"
    assert payload["current"]["warnings"] == []
    assert payload["current"]["needs_review"] == []
    assert calls == []


def test_proof_route_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))
    monkeypatch.setattr(
        cli,
        "_run_lifecycle_command",
        lambda **kwargs: {
            "health": "healthy",
            "warnings": [],
            "needs_review": [],
            "stale_generated_surfaces": [],
        },
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--route", "workspace_proof", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "proof"
    assert payload["selector"] == {"route": "workspace_proof"}
    assert payload["matched"] is True
    assert payload["answer"] == {
        "id": "workspace_proof",
        "command": "agentic-workspace proof --target ./repo --format json",
    }
    assert payload["target"] == tmp_path.as_posix()


def test_proof_current_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "planning").mkdir()
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))
    monkeypatch.setattr(
        cli,
        "_run_lifecycle_command",
        lambda **kwargs: {
            "health": "healthy",
            "warnings": [],
            "needs_review": [],
            "stale_generated_surfaces": [],
        },
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--current", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"current": True}
    assert payload["answer"]["installed_modules"] == ["planning"]
    assert payload["answer"]["status_health"] == "healthy"


def test_proof_route_selector_smoke_works_without_mocked_lifecycle(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--modules", "planning"]) == 0
    capsys.readouterr()

    assert cli.main(["proof", "--verbose", "--target", str(target), "--route", "workspace_proof", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"route": "workspace_proof"}
    assert payload["answer"]["id"] == "workspace_proof"
    assert payload["answer"]["command"] == "agentic-workspace proof --target ./repo --format json"


def test_proof_changed_selector_returns_path_based_validation_lane(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["surface"] == "proof"
    assert payload["selector"] == {"changed": [".agentic-workspace/planning/state.toml"]}
    answer = payload["answer"]
    expected_target = tmp_path.as_posix()
    assert answer["kind"] == "proof-selection/v1"
    assert answer["selected_lanes"][0]["id"] == "planning_surfaces"
    assert answer["required_commands"] == [
        f'{REPO_LOCAL_CLI_INVOKE} summary --target "{expected_target}" --format json',
        f'{REPO_LOCAL_CLI_INVOKE} doctor --target "{expected_target}" --modules planning --format json',
    ]
    assert answer["validation_plan"]["kind"] == "validation-plan/v1"
    assert answer["validation_plan"]["status"] == "inspect-before-run"
    first_step = answer["validation_plan"]["required"][0]
    assert first_step["order"] == 1
    assert first_step["command"] == f'{REPO_LOCAL_CLI_INVOKE} summary --target "{expected_target}" --format json'
    assert first_step["cwd"] == "."
    assert first_step["run"] == f'{REPO_LOCAL_CLI_INVOKE} summary --target "{expected_target}" --format json'
    assert first_step["required"] is True
    assert first_step["lane_id"] == "planning_surfaces"
    assert first_step["action"] == "run-validation-command"
    assert first_step["risk"] == "read-only validation"
    assert first_step["required_inputs"] == ["changed_paths", "selected_lanes"]
    assert first_step["next_proof"] == "continue to the next required step, then rerun proof selection if changed paths expand"
    assert answer["validation_plan"]["primary_next_action"] == first_step
    assert answer["validation_plan"]["next_proof"] == "proof is complete when all required steps pass for the current changed paths"
    assert answer["durable_intent"]["kind"] == "agentic-workspace/durable-intent-decision/v1"
    assert any(item.startswith("Relevant durable intent may add proof") for item in answer["escalate_when"])


def _append_focused_proof_runtime_lane(target: Path) -> None:
    config = target / ".agentic-workspace" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.proof_runtime]
purpose = "Focused proof runtime behavior."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py", "tests/test_workspace_proof_cli.py"]
commands = ["uv run pytest tests/test_workspace_proof_cli.py -k changed_selector -q"]
review_aids = ["Confirm changed proof routing behavior is exercised."]
evidence_concepts = ["focused-proof-runtime"]
proof_profiles = ["workspace_behavior"]
authority_refs = [".agentic-workspace/config.toml", "docs/maintainer/testing-strategy.md"]
escalation = ["focused proof does not exercise the changed behavior"]
claim_boundary = "focused-proof-runtime-required"
owner = "workspace-cli-runtime"
""",
        encoding="utf-8",
    )


def _append_session_logging_lane(target: Path) -> None:
    config = target / ".agentic-workspace" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.session_logging]
purpose = "Focused session logging behavior."
applies_to_paths = ["src/agentic_workspace/session_logging.py", "tests/test_workspace_session_logging.py"]
commands = ["uv run pytest tests/test_workspace_session_logging.py -q"]
review_aids = ["Confirm local diagnostic boundaries and persistence behavior."]
evidence_concepts = ["focused-session-logging"]
proof_profiles = ["workspace_behavior"]
authority_refs = [".agentic-workspace/config.toml"]
escalation = ["session-log persistence or local diagnostic boundaries changed"]
claim_boundary = "focused-session-logging-required"
owner = "workspace-cli-runtime"
""",
        encoding="utf-8",
    )


def test_proof_changed_selector_uses_focused_domain_route(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "def test_changed_selector():\n    assert True\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "domain:proof_runtime")

    assert lane["execution_mode"] == "serial-recommended"
    assert lane["domain_lane"]["source"] == ".agentic-workspace/config.toml [assurance.domain_proof_lanes]"
    assert lane["domain_lane"]["purpose"] == "Focused proof runtime behavior."
    assert "make test-workspace" not in answer["required_commands"]
    assert "focused proof does not exercise the changed behavior" in lane["escalate_when"]
    assert answer["focused_route_coverage_audit"]["status"] == "covered"


def test_proof_changed_selector_domain_route_covers_multi_path_scope(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "def test_changed_selector():\n    assert True\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "tests/test_workspace_proof_cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lanes = [lane for lane in answer["selected_lanes"] if lane["id"] == "domain:proof_runtime"]

    assert len(lanes) == 1
    assert lanes[0]["matched_paths"] == [
        "src/agentic_workspace/workspace_runtime_proof.py",
        "tests/test_workspace_proof_cli.py",
    ]
    assert answer["required_commands"].count("uv run pytest tests/test_workspace_proof_cli.py -k changed_selector -q") == 1
    assert "make test-workspace" not in answer["required_commands"]
    assert answer["focused_route_coverage_audit"]["missing_focused_route_paths"] == []


def test_proof_changed_selector_uses_domain_route_without_broad_coverage_fallback(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_session_logging_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "session_logging.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_session_logging.py", "def test_session_logging():\n    assert True\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/session_logging.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "domain:session_logging")

    assert lane["domain_lane"]["purpose"] == "Focused session logging behavior."
    assert answer["required_commands"] == ["uv run pytest tests/test_workspace_session_logging.py -q"]
    assert answer["proof_narrowness"]["status"] == "narrow_required"
    assert "does not authorize broad-suite fallback" in answer["focused_route_coverage_audit"]["coverage_evidence"]["rule"]


def test_proof_changed_selector_reports_missing_focused_route_as_maintenance_gap(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "unknown_runtime.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/unknown_runtime.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    audit = answer["focused_route_coverage_audit"]

    assert audit["status"] == "attention"
    assert audit["missing_focused_route_paths"] == ["src/agentic_workspace/unknown_runtime.py"]
    assert audit["maintenance_gap"]["status"] == "present"
    assert answer["route_refinement_required"]["status"] == "required"
    assert answer["route_refinement_required"]["uncovered_paths"] == ["src/agentic_workspace/unknown_runtime.py"]
    assert "make test-workspace" not in answer["required_commands"]
    assert "make lint-workspace" not in answer["required_commands"]
    assert answer["manual_verification"]["status"] == "route-refinement-required"
    assert answer["proof_next_decision"]["next"]["action"] == "route-refinement-required"


def test_proof_changed_selector_blocks_claim_for_partial_focused_route_gap(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "src" / "agentic_workspace" / "unknown_runtime.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "def test_changed_selector():\n    assert True\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "src/agentic_workspace/unknown_runtime.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]

    assert answer["route_refinement_required"]["status"] == "required"
    assert answer["route_refinement_required"]["uncovered_paths"] == ["src/agentic_workspace/unknown_runtime.py"]
    assert "uv run pytest tests/test_workspace_proof_cli.py -k changed_selector -q" in answer["required_commands"]
    assert "make test-workspace" not in answer["required_commands"]
    assert "make lint-workspace" not in answer["required_commands"]
    assert answer["manual_verification"]["status"] == "route-refinement-required"
    assert answer["proof_next_decision"]["next"]["action"] == "route-refinement-required"
    assert answer["proof_next_decision"]["next"]["command"] is None
    assert answer["proof_route_decision"]["manual_fallback"]["status"] == "route-refinement-required"


def test_proof_changed_reports_domain_route_inventory_audit(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "def test_changed_selector():\n    assert True\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    inventory = json.loads(capsys.readouterr().out)["answer"]["domain_proof_route_inventory_audit"]
    assert inventory["kind"] == "agentic-workspace/domain-proof-route-inventory-audit/v1"
    assert inventory["route_count"] == 1
    assert inventory["routes"][0]["id"] == "proof_runtime"
    assert inventory["routes"][0]["live_match_count"] == 2
    assert inventory["coverage_evidence"]["status"] == "advisory-only"


def test_proof_routine_context_surfaces_workflow_obligation_match(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[workflow_obligations.workspace_closeout]
summary = "Run workspace closeout checks."
stage = "closeout"
force = "required-before-closeout"
scope_tags = ["workspace"]
commands = ["agentic-workspace report --target . --section closeout_trust --format json"]
review_hint = "Workspace orchestration applies to workspace paths."
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    binding = answer["current_work_context"]
    assert binding["kind"] == "agentic-workspace/current-work-context/v1"
    assert binding["authority"] == "local-advisory-binding"
    routine = answer["routine_work_context"]
    assert routine["surface"] == "proof"
    assert routine["categories"]["authority"]["status"] == "attention"
    assert routine["categories"]["authority"]["signals"]["workflow_obligation_matches"] == 1
    assert routine["categories"]["evidence_proof"]["status"] == "attention"
    assert routine["categories"]["evidence_proof"]["signals"]["workflow_obligation_matches"] == 1
    assert routine["knowledge_authority_review"]["workflow_obligation_match_count"] == 1


def test_proof_routes_changed_path_to_verification_protocol(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "tests" / "test_runbook_review.py", "def test_runbook_review_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace/verification/manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[scenarios.runbook_walkthrough]
protocol_id = "runbook_review"
title = "Runbook walkthrough"
steps = ["Review the recovery runbook"]
expected_observations = ["Recovery steps and owner are visible"]
pass_evidence_labels = ["manual_runbook_review"]
fail_evidence_labels = ["runbook_gap"]

[protocols.runbook_review]
title = "Runbook review"
purpose = "Manual verification for runbook changes."
applies_to_paths = ["docs/runbooks/**"]
scenario_refs = ["runbook_walkthrough"]
steps = ["Run the runbook walkthrough"]
expected_evidence = ["manual_runbook_review"]
review_owner = "ops-review"
review_aids = ["Record observations in the closeout evidence."]

[proof_routes.runbook_review_route]
protocol_refs = ["runbook_review"]
scenario_refs = ["runbook_walkthrough"]
commands = ["uv run pytest tests/test_runbook_review.py"]
review_aids = ["Record route-specific proof notes."]
proof_lane_hint = "runbook-verification"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/runbooks/recovery.md",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["verification"]["active_count"] == 1
    assert answer["verification"]["evidence_status"][0]["state"] == "missing-evidence"
    lanes = {lane["id"]: lane for lane in answer["selected_lanes"]}
    assert "verification:runbook_review" in lanes
    assert lanes["verification:runbook_review"]["verification_scenario_refs"] == ["runbook_walkthrough"]
    assert lanes["verification:runbook_review"]["verification_proof_route_ids"] == ["runbook_review_route"]
    assert lanes["verification:runbook_review"]["required_commands"] == ["uv run pytest tests/test_runbook_review.py"]
    assert answer["routine_work_context"]["categories"]["evidence_proof"]["signals"]["active_verification_protocols"] == 1


def test_proof_routes_active_assurance_requirement_to_verification_protocol(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "tests" / "test_privacy.py", "def test_privacy_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.proof_profiles.privacy]
required_commands = ["uv run pytest tests/test_privacy.py"]
review_aids = ["Review privacy data handling manually."]

[assurance.requirements.privacy_data]
level = "high"
applies_to_paths = ["src/privacy/**"]
required_evidence = ["manual_privacy_review"]
proof_profile = "privacy"
force = "required-before-closeout"
blocking_claims = ["claim-work-complete", "close-parent-lane"]
review_owner = "privacy-review"
""",
    )
    _write(
        tmp_path / ".agentic-workspace/verification/manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[protocols.privacy_manual_review]
title = "Privacy manual review"
purpose = "Repeatable review protocol for privacy-sensitive code."
applies_to_paths = ["src/privacy/**"]
assurance_requirement_refs = ["privacy_data"]
proof_profiles = ["privacy"]
expected_evidence = ["manual_privacy_review"]
review_owner = "privacy-review"
review_aids = ["Confirm data minimisation and retention assumptions."]
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/privacy/export.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["verification"]["active_protocols"][0]["id"] == "privacy_manual_review"
    lanes = {lane["id"]: lane for lane in answer["selected_lanes"]}
    assert "assurance-requirement:privacy_data" in lanes
    assert "verification:privacy_manual_review" in lanes
    status = answer["assurance_requirements"]["evidence_status"][0]
    assert status["verification_protocols"][0]["protocol_id"] == "privacy_manual_review"
    assert status["verification_missing_evidence"] == ["manual_privacy_review"]
    obligations = answer["manual_proof_obligations"]
    assert obligations[0]["id"] == "verification:privacy_manual_review"
    assert obligations[0]["required"] is True
    assert obligations[0]["missing_evidence"] == ["manual_privacy_review"]
    assert obligations[0]["authority"]["authority"] == "verification-manual-protocol"
    required = answer["proof_obligations"]["required_proof"]
    assert required["manual_verification_required"] is True
    assert required["manual_obligation_count"] == 1
    assert required["manual_obligations"][0]["id"] == "verification:privacy_manual_review"


def test_proof_routes_manual_verification_protocol_without_command(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/verification/manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[protocols.retention_policy_review]
title = "Retention policy review"
purpose = "Manual verification for retention-sensitive changes."
applies_to_paths = ["privacy/**"]
expected_evidence = ["manual_retention_review"]
review_owner = "privacy-review"
authority_refs = ["docs/privacy-policy.md#retention", "regulation:P.3"]
steps = ["Read the retention rule", "Compare changed behavior to the rule"]
review_aids = ["Record whether regulation P.3 remains satisfied."]
""",
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "privacy/export.txt", "--verbose", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    obligation = answer["manual_proof_obligations"][0]
    assert obligation["id"] == "verification:retention_policy_review"
    assert obligation["reference_material"] == ["docs/privacy-policy.md#retention", "regulation:P.3"]
    assert obligation["missing_evidence"] == ["manual_retention_review"]
    assert obligation["claim_boundary"] == "completion-claims-qualified-until-manual-evidence-recorded-or-waived"
    assert answer["proof_route_maintenance"]["status"] == "attention"
    assert answer["proof_route_maintenance"]["manual_obligation_count"] == 1


def test_proof_accumulates_repeated_changed_flags(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    script_path = tmp_path / "scripts" / "run_agentic_workspace.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("print('ok')\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["answer"]["changed_paths"] == [
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "tests/test_workspace_proof_cli.py",
    ]
    lanes = {lane["id"]: lane for lane in payload["answer"]["selected_lanes"]}
    assert "runtime_mirror_consistency" in lanes
    assert (
        "uv run python scripts/run_agentic_workspace.py report --target . --section runtime_mirror_consistency --format json"
        in lanes["runtime_mirror_consistency"]["required_commands"]
    )


def test_proof_tiny_profile_returns_next_validation_action(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--changed",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload)
    assert payload["kind"] == "proof-next-decision/v1"
    assert set(payload) <= {
        "kind",
        "target",
        "selector",
        "sufficiency",
        "next",
        "required_commands",
        "proof_command_adjustments",
        "unavailable_proof_commands",
        "proof_strategy",
        "target_proof_capabilities",
        "manual_verification",
        "warnings",
        "intent_proof",
        "proof_narrowness",
        "detail_command",
        "detail_command_template",
        "proof_route_selection",
        "proof_closeout_summary",
    }
    assert payload["selector"] == {"changed": ["generated/workspace/python/cli.py"]}
    assert payload["proof_narrowness"]["status"] == "broad_required"
    assert payload["proof_narrowness"]["broad_suite_boundary_status"] == "explicit-escalation-required"
    assert payload["proof_narrowness"]["broad_suite_boundary_reason"]
    assert payload["next"]["action"] == "route-refinement-required"
    assert payload["next"]["command"] is None
    assert payload["manual_verification"]["status"] == "route-refinement-required"
    assert "make test-workspace" not in payload["required_commands"]
    assert payload["warnings"] == []
    assert "answer" not in payload
    assert "selected_lanes" not in encoded
    assert "validation_plan" not in encoded
    assert payload["detail_command_template"]["runnable"] is False
    assert payload["detail_command_template"]["placeholders"] == {"paths": ["generated/workspace/python/cli.py"]}
    assert len(encoded) < 4500


def test_proof_route_escalation_gate_blocks_generic_broad_fallback(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--select",
                "proof_route_escalation_gate,proof_narrowness,proof_route_strategy_decision,proof_next_decision,manual_verification",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    boundary = values["proof_narrowness"]["broad_suite_boundary"]
    gate = values["proof_route_escalation_gate"]
    assert boundary["status"] == "explicit-escalation-required"
    assert boundary["requires_explicit_escalation"] is True
    assert gate["status"] == "blocked-explicit-escalation-required"
    assert gate["requires_explicit_escalation"] is True
    assert gate["friction_inputs"]["recurring_validation_friction"] == "lifecycle-managed active validation-friction improvement signals"
    assert gate["friction_inputs"]["applicable_live_findings"] == []
    assert gate["friction_inputs"]["candidate_only_sources"] == ["session-log slow-command friction candidates"]
    assert gate["proof_route_strategy_decision"]["outcome"] == "broad-escalation-required"
    assert gate["cross_surface_projection"]["route_decision_surface"] == "proof_route_strategy_decision"
    assert values["proof_route_strategy_decision"]["claim_effect"] == "claim-blocked"
    assert values["proof_next_decision"]["next"]["action"] == "route-refinement-required"
    assert values["proof_next_decision"]["next"]["command"] is None
    assert values["manual_verification"]["status"] == "route-refinement-required"


def test_proof_changed_uses_available_target_makefile_targets(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n\nmaintainer-surfaces:\n\ttrue\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["make test", "make lint"]
    assert payload["next"]["command"] == "make test"
    assert payload["next"]["route_source"] == "live-adapted-target-capability"
    assert payload["next"]["why"] == "behavior-test intent selected live-adapted-target-capability."
    assert payload["proof_route_selection"]["selected_command"] == {
        "command": "make test",
        "lane": "workspace_cli",
        "route_source": "live-adapted-target-capability",
        "route_authority": "live-target-capability",
        "fallback_status": "candidate-live-confirmed",
        "authority_surface": "target repo command discovery",
        "intent_type": "behavior-test",
    }
    assert payload["proof_route_selection"]["route_source"] == "live-adapted-target-capability"
    assert payload["proof_route_selection"]["manual_fallback"] is None
    assert payload["proof_route_selection"]["explanation_field"] == "proof_route_explanation"
    assert "next_action" not in payload["proof_route_selection"]
    assert "required_commands" not in payload["proof_route_selection"]
    assert payload["proof_command_adjustments"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "replacement": "make test",
            "reason": "target Makefile does not define 'test-workspace'; using available 'test' target",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "replacement": "make lint",
            "reason": "target Makefile does not define 'lint-workspace'; using available 'lint' target",
        },
    ]
    assert payload["target_proof_capabilities"]["make"]["targets"] == ["lint", "maintainer-surfaces", "test"]


def test_proof_changed_does_not_assume_makefile_exists(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == []
    assert payload["next"]["action"] == "manual-verification"
    assert payload["next"]["command"] is None
    assert payload["proof_route_selection"]["manual_fallback"]["status"] == "required"
    assert payload["proof_route_selection"]["manual_fallback"]["unavailable_command_count"] == 0
    assert payload["proof_route_selection"]["selected_command"] is None
    assert payload["proof_route_selection"]["route_source"] == "manual-fallback"
    assert payload["manual_verification"]["status"] == "required"
    assert "no executable proof route" in payload["manual_verification"]["summary"]
    assert payload.get("unavailable_proof_commands", []) == []
    assert payload["warnings"] == []
    assert payload["manual_verification"]["status"] == "required"


def test_proof_changed_reports_manual_verification_templates(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    templates = payload["manual_verification"]["templates"]
    assert templates == [
        {
            "kind": "manual-verification-template/v1",
            "intent_type": "behavior-test",
            "title": "Behavior verification",
            "trust": "lower-than-executable-proof",
            "checklist": [
                "Identify the behavior the changed paths are expected to affect.",
                "Inspect the implementation path and the user-visible or API-facing result.",
                "Exercise the smallest available manual scenario or explain why no scenario is available.",
            ],
            "evidence_to_record": [
                "changed behavior inspected",
                "scenario or reasoning used",
                "residual risk compared with executable tests",
            ],
        }
    ]


def test_proof_verbose_exposes_manual_fallback_decision_layers(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["proof_route_selection"] == answer["proof_route_decision"]
    decision = answer["proof_route_selection"]
    assert decision["next_action"]["action"] == "manual-verification"
    assert decision["selected_command"] is None
    assert decision["manual_fallback"]["status"] == "required"
    assert decision["manual_fallback"]["unavailable_command_count"] == 0
    assert decision["critical_warnings"] == []
    explanation = answer["proof_route_explanation"]
    assert explanation["selected_commands"] == []
    assert explanation["unavailable_commands"] == []
    assert explanation["manual_verification"]["status"] == "required"
    assert explanation["manual_verification"]["templates"][0]["intent_type"] == "behavior-test"
    assert explanation["manual_verification"]["templates"][0]["trust"] == "lower-than-executable-proof"
    execution_evidence = explanation["proof_execution_evidence"]
    assert execution_evidence["kind"] == "proof-execution-evidence/v1"
    assert execution_evidence["status"] == "not-run-or-not-recorded"
    assert execution_evidence["state_model"] == ["selected", "run", "passed", "failed", "skipped", "unavailable", "waived", "missing"]
    assert execution_evidence["expected_commands"] == []
    assert execution_evidence["manual_verification_expected"] is True
    assert execution_evidence["receipt_reconciliation"]["commands"] == []
    assert execution_evidence["missing_evidence_diagnostics"]["not-run-or-not-recorded"] == (
        "no trusted receipt exists for this selected command"
    )
    explanations = answer["proof_command_explanations"]
    assert explanations["status"] == "present"
    assert explanations["required"] == []
    assert explanations["manual_or_unavailable"][0]["reason_classes"] == ["unavailable-manual"]
    assert explanations["manual_or_unavailable"][0]["blocking"] is True
    assert "optional-confidence" in explanations["reason_class_model"]


def test_proof_command_explanations_status_present_for_policy_blockers_only() -> None:
    explanations = workspace_runtime_proof._proof_command_explanations_payload(
        selected_commands=[],
        required_commands=[],
        optional_commands=[],
        unavailable_commands=[],
        host_policy_blocked_commands=[
            {
                "command": "npm test",
                "lane": "concern:no_npm_test",
                "reason": "host-configured proof profile disallows this command",
                "configured_command": "npm test",
            }
        ],
        manual_verification=None,
    )

    assert explanations["status"] == "present"
    assert explanations["required"] == []
    assert explanations["optional_confidence"] == []
    assert explanations["manual_or_unavailable"] == [
        {
            "command": "npm test",
            "lane": "concern:no_npm_test",
            "reason": "host-configured proof profile disallows this command",
            "reason_classes": ["explicit-config-policy"],
            "blocking": True,
            "configured_command": "npm test",
        }
    ]


def test_proof_changed_uses_target_package_json_scripts_without_makefile(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["npm test", "npm run lint"]
    assert payload["next"]["route_source"] == "live-adapted-target-capability"
    assert payload["target_proof_capabilities"]["package_json"]["scripts"] == ["lint", "test"]
    assert payload["proof_command_adjustments"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "replacement": "npm test",
            "reason": "target repo has no Makefile; using package.json script for 'test' proof",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "replacement": "npm run lint",
            "reason": "target repo has no Makefile; using package.json script for 'lint' proof",
        },
    ]
    assert payload["manual_verification"] is None


def test_proof_changed_uses_subrepo_makefile_for_package_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "pyproject.toml", '[tool.uv.workspace]\nmembers = ["packages/other", "packages/planning"]\n')
    _write(tmp_path / "packages" / "other" / "Makefile", "test:\n\tfalse\n\nlint:\n\tfalse\n")
    _write(
        tmp_path / "packages" / "planning" / "Makefile",
        "test:\n\tpytest\n\nlint:\n\truff check .\n\ntypecheck:\n\tmypy src\n",
    )
    _write(tmp_path / "packages" / "planning" / "src" / "repo_planning_bootstrap" / "installer.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["required_commands"] == [
        "cd packages/planning && make test",
        "cd packages/planning && make lint",
        "cd packages/planning && make typecheck",
    ]
    assert answer["target_proof_capabilities"]["make"] == {"available": False, "targets": []}
    project_roots = {project_root["path"]: project_root for project_root in answer["target_proof_capabilities"]["project_roots"]}
    assert project_roots["packages/other"]["changed_path_matched"] is False
    assert project_roots["packages/planning"]["changed_path_matched"] is True
    assert project_roots["packages/planning"]["make"]["targets"] == ["lint", "test", "typecheck"]
    assert "cd packages/planning && make test" in answer["target_proof_capabilities"]["candidate_commands"]
    assert "cd packages/planning && make typecheck" in answer["target_proof_capabilities"]["candidate_commands"]
    assert (
        answer["selected_commands"][0].items()
        >= {
            "kind": "proof-command/v1",
            "command": "cd packages/planning && make test",
            "cwd": "packages/planning",
            "run": "make test",
            "selected_from": "live-adapted-target-capability",
            "intent_type": "behavior-test",
            "lane": "planning_package",
            "required": True,
        }.items()
    )
    assert answer["selected_commands"][0]["execution_mode"] == "parallel-ok"
    assert answer["proof_route_selection"]["selected_command"] == {
        "command": "cd packages/planning && make test",
        "lane": "planning_package",
        "route_source": "live-adapted-target-capability",
        "route_authority": "live-target-capability",
        "fallback_status": "candidate-live-confirmed",
        "authority_surface": "target repo command discovery",
        "intent_type": "behavior-test",
        "cwd": "packages/planning",
        "run": "make test",
    }
    first_step = answer["validation_plan"]["required"][0]
    assert first_step["command"] == "cd packages/planning && make test"
    assert first_step["cwd"] == "packages/planning"
    assert first_step["run"] == "make test"
    assert answer["validation_plan"]["required"][2]["command"] == "cd packages/planning && make typecheck"
    assert answer.get("manual_verification") is None


def test_proof_changed_uses_subrepo_package_json_for_package_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "pyproject.toml", '[tool.uv.workspace]\nmembers = ["packages/ui"]\n')
    _write(tmp_path / "packages" / "ui" / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))
    _write(tmp_path / "packages" / "ui" / "src" / "index.ts", "export const value = 1;\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "packages/ui/src/index.ts", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["cd packages/ui && npm test", "cd packages/ui && npm run lint"]
    assert payload["next"]["command"] == "cd packages/ui && npm test"
    assert payload["next"]["cwd"] == "packages/ui"
    assert payload["next"]["run"] == "npm test"
    assert payload["proof_command_adjustments"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "replacement": "cd packages/ui && npm test",
            "replacement_cwd": "packages/ui",
            "source_path": "packages/ui/package.json",
            "reason": "target repo has no root Makefile; using subrepo package.json script for 'test' proof in packages/ui",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "replacement": "cd packages/ui && npm run lint",
            "replacement_cwd": "packages/ui",
            "source_path": "packages/ui/package.json",
            "reason": "target repo has no root Makefile; using subrepo package.json script for 'lint' proof in packages/ui",
        },
    ]
    assert payload["manual_verification"] is None


def test_proof_changed_treats_plain_python_project_as_discovery_candidate(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "pyproject.toml",
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = ["agentic-workspace"]
""",
    )
    _write(tmp_path / "uv.lock", "# lock\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "pyproject.toml", "uv.lock", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest" not in answer["required_commands"]
    assert answer["manual_verification"]["status"] == "required"
    pytest_capability = answer["target_proof_capabilities"]["python"]["pytest"]
    assert pytest_capability["status"] == "candidate"
    assert pytest_capability["authority"] == "candidate-discovery"
    assert answer["target_proof_capabilities"]["role_commands"] == {}
    learning = answer["host_repo_learning"]
    assert learning["authority_rule"].startswith("Host-repo heuristics may propose discovery candidates")
    assert learning["negative_evidence"]["status"] == "none"
    assert learning["negative_evidence"]["items"] == []
    assert answer["unavailable_commands"] == []


def test_proof_changed_uses_declared_pytest_dependency_as_confirmed_evidence(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "pyproject.toml",
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = ["pytest>=8"]
""",
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "pyproject.toml", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "uv run pytest" in payload["required_commands"]
    pytest_capability = payload["target_proof_capabilities"]["python"]["pytest"]
    assert pytest_capability["status"] == "confirmed"
    assert pytest_capability["evidence"] == [
        {"state": "confirmed", "source": "declared-dependency", "path": "pyproject.toml:project.dependencies"}
    ]


def test_proof_changed_release_version_surface_exposes_named_release_profile(capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(repo_root),
                "--changed",
                "pyproject.toml",
                "--select",
                "selected_lanes,required_commands,release_proof_profile",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    lane_ids = [lane["id"] for lane in values["selected_lanes"]]
    assert "coordinated_release_proof" in lane_ids
    assert "make test-memory" in values["required_commands"]
    assert "make test-planning" in values["required_commands"]
    assert "make test-verification" in values["required_commands"]
    assert "uv run python scripts/check/check_generated_command_packages.py" in values["required_commands"]
    assert "uv run python scripts/check/run_operation_conformance_tests.py --target all" in values["required_commands"]
    assert "uv run pytest tests/test_release_workflows.py -q" in values["required_commands"]

    profile = values["release_proof_profile"]
    assert profile["kind"] == "agentic-workspace/release-proof-profile/v1"
    assert profile["id"] == "coordinated-release-proof"
    assert profile["status"] == "required"
    assert profile["matched_paths"] == ["pyproject.toml"]
    groups = {group["id"]: group for group in profile["groups"]}
    assert groups["workspace-runtime"]["proof_purpose"] == "behavioral"
    assert groups["memory-package"]["commands"] == ["make test-memory", "make lint-memory"]
    assert groups["planning-package"]["commands"] == ["make test-planning", "make lint-planning", "make typecheck-planning"]
    assert groups["verification-package"]["commands"] == ["make test-verification", "make lint-verification"]
    assert groups["generated-command-package-freshness"]["proof_purpose"] == "freshness-parity"
    assert "uv run python scripts/check/check_generated_command_packages.py" in groups["generated-command-package-freshness"]["commands"]
    assert groups["operation-conformance"]["commands"] == ["uv run python scripts/check/run_operation_conformance_tests.py --target all"]
    assert groups["release-defaults-version-authority"]["proof_purpose"] == "release-authority"
    assert "uv run pytest tests/test_release_workflows.py -q" in groups["release-defaults-version-authority"]["commands"]


def test_proof_changed_uses_python_pytest_capability_without_makefile(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "pyproject.toml",
        """
[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 120
""",
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["uv run pytest", "uv run ruff check ."]
    assert payload["target_proof_capabilities"]["python"]["available"] is True
    assert payload["target_proof_capabilities"]["python"]["pytest"]["status"] == "confirmed"
    assert payload["target_proof_capabilities"]["python"]["pytest"]["authority"] == "confirmed-repo-evidence"
    assert payload["target_proof_capabilities"]["role_commands"] == {
        "test": ["uv run pytest"],
        "lint": ["uv run ruff check ."],
    }
    assert payload["proof_command_adjustments"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "replacement": "uv run pytest",
            "reason": "target repo has no Makefile; using detected 'test' proof capability",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "replacement": "uv run ruff check .",
            "reason": "target repo has no Makefile; using detected 'lint' proof capability",
        },
    ]
    assert payload["manual_verification"] is None


def test_proof_changed_reports_rust_go_and_java_capability_candidates(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Cargo.toml", '[package]\nname = "demo"\nversion = "0.1.0"\n')
    _write(tmp_path / "go.mod", "module example.com/demo\n")
    _write(tmp_path / "pom.xml", "<project />\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "docs/notes.md", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    capabilities = answer["target_proof_capabilities"]
    assert capabilities["rust"]["available"] is True
    assert capabilities["go"]["available"] is True
    assert capabilities["java"]["available"] is True
    assert capabilities["role_commands"]["test"] == ["cargo test", "go test ./...", "mvn test"]
    assert capabilities["role_commands"]["lint"] == ["cargo clippy --all-targets --all-features", "go vet ./..."]
    assert "cargo test" in capabilities["candidate_commands"]
    assert "go vet ./..." in capabilities["candidate_commands"]
    assert "mvn test" in capabilities["candidate_commands"]


def test_proof_changed_reports_live_confirmed_learned_route_hints(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))
    _write(
        tmp_path / ".agentic-workspace" / "proof-route-hints.json",
        json.dumps(
            {
                "kind": "agentic-workspace/proof-route-hints/v1",
                "schema_version": "proof-route-hints/v1",
                "source": "lifecycle-discovery",
                "rule": "Advisory proof route hints are not host policy; proof selection must live-confirm them before emitting commands.",
                "hints": [
                    {
                        "id": "package-json:test",
                        "intent_type": "behavior-test",
                        "candidate_command": "npm test",
                        "source": "package-json",
                        "source_path": "package.json",
                        "confidence": "medium",
                        "requires_live_confirmation": True,
                    },
                    {
                        "id": "package-json:stale",
                        "intent_type": "static-check",
                        "candidate_command": "npm run stale",
                        "source": "package-json",
                        "source_path": "package.json",
                        "confidence": "medium",
                        "requires_live_confirmation": True,
                    },
                ],
            }
        ),
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    assert hints["status"] == "loaded"
    assert hints["confirmed"][0]["candidate_command"] == "npm test"
    assert hints["confirmed"][0]["confirmation"] == "live-confirmed"
    assert hints["stale"][0]["candidate_command"] == "npm run stale"
    assert hints["stale"][0]["confirmation"] == "stale-or-unavailable"
    assert hints["lifecycle"]["state_counts"] == {
        "candidate": 2,
        "confirmed": 0,
        "invalid-authority": 0,
        "negative": 0,
        "stale": 0,
        "superseded": 0,
    }
    assert hints["lifecycle"]["bucket_counts"]["confirmed"] == 1
    assert "invalid-authority" in {state["state"] for state in hints["lifecycle"]["state_model"]}
    decision = answer["proof_route_selection"]
    assert decision["critical_warnings"] == ["1 learned route hint(s) are stale or unavailable."]
    assert decision["selected_command"]["command"] == "npm test"
    explanation = answer["proof_route_explanation"]
    assert explanation["proof_intents"][0]["kind"] == "proof-intent/v1"
    assert explanation["target_capabilities"]["package_json"]["scripts"] == ["lint", "test"]
    assert explanation["setup_adopt_route_learning"] == {
        "kind": "setup-adopt-proof-route-learning/v1",
        "status": "advisory-hints-loaded",
        "persistent_surface": ".agentic-workspace/proof-route-hints.json",
        "hint_count": 2,
        "confirmed_count": 1,
        "stale_count": 1,
        "negative_count": 0,
        "superseded_count": 0,
        "invalid_authority_count": 0,
        "lifecycle_field": "learned_route_hints.lifecycle",
        "route_map_decision": "use-advisory-hints-only",
        "reason": (
            "Setup/adopt-discovered route hints are persisted as advisory memory and must be live-confirmed before command selection."
        ),
        "separation": {
            "configured_policy": "host-owned proof profiles and disallowed commands",
            "live_target_capabilities": "current Makefile, package.json, language, and role-command discovery",
            "setup_adopt_learning": "advisory route hints from lifecycle discovery, never host policy",
        },
    }
    assert explanation["selected_commands"][0]["kind"] == "proof-command/v1"
    assert explanation["proof_execution_evidence"]["status"] == "not-run-or-not-recorded"
    assert answer["proof_next_decision"]["warnings"] == ["1 learned route hint(s) are stale or unavailable."]
    maintenance = answer["proof_route_maintenance"]
    assert maintenance["status"] == "attention"
    assert maintenance["stale_route_count"] == 1
    assert maintenance["new_capability_candidate_count"] >= 1
    reasons = {item["reason"] for item in maintenance["suggested_updates"]}
    assert "learned proof route is stale or unavailable" in reasons
    assert "new target proof capability needs route-table promotion" in reasons


def test_proof_changed_reuses_confirmed_memory_proof_route(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "app.py", "print('ok')\n")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        """
# Proof routes

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"python -m compileall src","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"src","owner":"Memory","provenance":"manual verification passed on 2026-06-02","learned_at":"2026-06-02"}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.py", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    assert hints["source_counts"]["memory"] == 1
    assert hints["confirmed"][0]["candidate_command"] == "python -m compileall src"
    assert hints["confirmed"][0]["confirmation"] == "learned-confirmed"
    assert answer["proof_route_selection"]["selected_command"]["command"] == "python -m compileall src"
    assert answer["proof_route_selection"]["selected_command"]["route_source"] == "live-adapted-target-capability"
    reliance = answer["proof_route_selection"]["learned_route_reliance"]
    assert reliance["status"] == "present"
    assert reliance["material_to_required_proof"] is True
    assert reliance["items"][0]["command"] == "python -m compileall src"
    assert reliance["items"][0]["provenance"] == "manual verification passed on 2026-06-02"
    assert answer["proof_route_selection"]["closeout_disclosure"]["status"] == "required"
    assert answer["proof_route_explanation"]["learned_route_reliance"] == reliance
    learning = answer["host_repo_learning"]
    assert learning["confirmed_evidence"]["status"] == "present"
    assert "memory capture-note" in learning["confirmed_evidence"]["items"][0]["capture"]["command_to_run"]
    assert learning["actionable_next_steps"]["memory_note_entries"][0].startswith("agentic-workspace-proof-route:")


def test_proof_changed_closeout_summary_preserves_learned_route_receipt(tmp_path: Path, capsys) -> None:
    from agentic_workspace.proof_subject import build_proof_subject

    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "app.py", "print('ok')\n")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        """
# Proof routes

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"python -m compileall src","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"src","owner":"Memory","provenance":"manual verification passed on 2026-06-02","learned_at":"2026-06-02"}
""",
    )
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "python -m compileall src",
        "result": "passed",
        "changed_paths": ["src/app.py"],
        "recorded_at": "2026-07-06T10:00:00Z",
    }
    receipt["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=receipt["changed_paths"], command=receipt["command"])
    _write(
        tmp_path / ".agentic-workspace" / "local" / "proof-receipts" / "last.json",
        json.dumps(receipt),
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.py", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    summary = answer["proof_closeout_summary"]
    assert summary["status"] == "sufficient-recorded"
    assert summary["changed_paths"] == ["src/app.py"]
    assert summary["route"]["source"] == "memory"
    assert summary["route"]["maturity"] == "learned-confirmed"
    assert summary["proof_results"] == [
        {
            "command": "python -m compileall src",
            "result": "passed",
            "receipt_state": "accepted",
            "execution_state": "missing",
            "evidence_source": "proof-receipt",
        }
    ]
    assert summary["remaining_gaps"] == []
    assert any(line.startswith("Route:") and "learned-confirmed" in line for line in summary["pr_validation_lines"])
    assert any(line == "Remaining gaps: none known." for line in summary["pr_validation_lines"])


def test_proof_closeout_treats_conservative_route_maturity_as_advisory_after_accepted_receipt() -> None:
    from agentic_workspace.workspace_runtime_proof import _proof_closeout_summary_payload

    command = "make test-workspace"
    summary = _proof_closeout_summary_payload(
        changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        selected_lanes=[{"id": "workspace_cli"}],
        proof_route_decision={
            "selected_command": {
                "command": command,
                "route_source": "live-confirmed-proof-rule",
                "route_authority": "package-seed-or-default-route",
                "fallback_status": "seed-fallback",
                "authority_surface": "package proof defaults",
            }
        },
        proof_command_explanations={"required": [{"command": command, "reason_classes": ["conservative-fallback"]}]},
        proof_execution_evidence={"commands": []},
        proof_receipt_reconciliation={"commands": [{"command": command, "evidence_state": "accepted"}]},
        proof_receipt_bridge={"status": "clear", "missing_receipt_count": 0},
        learned_route_reliance={"items": []},
        manual_verification=None,
        unavailable_commands=[],
        host_policy_blocked_commands=[],
    )

    assert summary["status"] == "sufficient-recorded"
    assert summary["remaining_gaps"] == []
    assert summary["route"]["maturity"] == "conservative-fallback"
    assert summary["route_maturity_advisories"] == [
        f"{command}: conservative fallback; narrower learned route evidence is missing or immature"
    ]
    assert summary["route_maturity_gaps"] == []
    assert summary["route_maturity"]["authority_established"] is True
    assert summary["route_maturity"]["coverage_established"] is True


def test_proof_closeout_keeps_conservative_maturity_blocking_without_route_authority() -> None:
    from agentic_workspace.workspace_runtime_proof import _proof_closeout_summary_payload

    command = "make test-workspace"
    summary = _proof_closeout_summary_payload(
        changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        selected_lanes=[{"id": "workspace_cli"}],
        proof_route_decision={"selected_command": {"command": command, "route_source": "fallback"}},
        proof_command_explanations={"required": [{"command": command, "reason_classes": ["conservative-fallback"]}]},
        proof_execution_evidence={"commands": []},
        proof_receipt_reconciliation={"commands": [{"command": command, "evidence_state": "accepted"}]},
        proof_receipt_bridge={"status": "clear", "missing_receipt_count": 0},
        learned_route_reliance={"items": []},
        manual_verification=None,
        unavailable_commands=[],
        host_policy_blocked_commands=[],
    )

    assert summary["status"] == "not-yet-sufficient"
    assert summary["route_maturity"]["status"] == "blocked"
    assert summary["route_maturity"]["authority_established"] is False
    assert summary["route_maturity_advisories"] == []
    assert summary["route_maturity_gaps"] == [f"{command}: conservative fallback; narrower learned route evidence is missing or immature"]


def test_proof_cli_accepts_covering_receipts_for_authoritative_conservative_route(tmp_path: Path, capsys) -> None:
    from agentic_workspace.proof_subject import build_proof_subject

    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n")
    _write(tmp_path / "llms.txt", "proof route fixture\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0
    first = json.loads(capsys.readouterr().out)["answer"]
    commands = first["required_commands"]
    receipts = [
        {
            "kind": "agentic-workspace/proof-receipt/v1",
            "command": command,
            "result": "passed",
            "changed_paths": ["llms.txt"],
            "recorded_at": f"2026-07-10T10:00:0{index}Z",
        }
        for index, command in enumerate(commands)
    ]
    for receipt in receipts:
        receipt["proof_subject"] = build_proof_subject(
            target_root=tmp_path, changed_paths=receipt["changed_paths"], command=receipt["command"]
        )
    _write(tmp_path / ".agentic-workspace/local/proof-receipts/history.jsonl", "\n".join(json.dumps(item) for item in receipts) + "\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)["proof_closeout_summary"]
    assert summary["status"] == "sufficient-recorded"
    assert summary["remaining_gap_count"] == 0
    assert summary["route_maturity"] == {"status": "advisory", "advisory_count": len(commands)}


def test_proof_changed_exposes_receipt_bridge_for_unrecorded_commands(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    bridge = answer["proof_receipt_bridge"]
    reconciliation = answer["proof_receipt_reconciliation"]
    assert bridge["kind"] == "agentic-workspace/proof-receipt-bridge/v1"
    assert bridge["status"] == "action-required"
    assert bridge["missing_receipt_count"] == len(reconciliation["commands"])
    assert bridge["ready_to_record_count"] >= 1
    assert bridge["template_blocked_count"] == 0
    assert bridge["next_action"] == "record the first concrete proof receipt"
    assert "--record-receipt" in bridge["next_recording_command"]
    action = next(item for item in bridge["actions"] if item["command"] == "make test-workspace")
    assert action["status"] == "ready-to-record-after-run"
    assert action["next_action"] == "record the actual proof result after this concrete command has run"
    assert action["recording_command"] == action["record_passed_command"]
    assert action["receipt_state"] in {"not-run-or-not-recorded", "run-but-not-recorded"}
    assert "--record-receipt" in action["record_passed_command"]
    assert '--receipt-command "make test-workspace"' in action["record_passed_command"]
    assert "--receipt-result passed" in action["record_passed_command"]
    assert action["result_options"] == ["passed", "failed", "skipped", "waived"]
    assert action["result_contract"]["proof_sufficient"] == ["passed"]
    summary_bridge = answer["proof_closeout_summary"]["receipt_bridge"]
    assert summary_bridge == {
        "status": "action-required",
        "missing_receipt_count": bridge["missing_receipt_count"],
        "detail_selector": "proof_receipt_bridge",
    }

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compact = json.loads(capsys.readouterr().out)
    assert compact["proof_closeout_summary"]["receipt_bridge"]["status"] == "action-required"
    assert "record_passed_command" not in json.dumps(compact)


def test_proof_receipt_bridge_marks_template_commands_unrecordable() -> None:
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_bridge_payload

    bridge = _proof_receipt_bridge_payload(
        changed_paths=["src/example.py"],
        proof_receipt_reconciliation={
            "commands": [
                {
                    "command": "uv run pytest <paths>",
                    "evidence_state": "not-run-or-not-recorded",
                    "diagnostic": "no trusted receipt exists for this selected command",
                },
                {
                    "command": "make typecheck",
                    "evidence_state": "run-but-not-recorded",
                    "diagnostic": "receipt missing for this command",
                },
            ]
        },
        cli_invoke=REPO_LOCAL_CLI_INVOKE,
    )

    assert bridge["status"] == "action-required"
    assert bridge["ready_to_record_count"] == 1
    assert bridge["template_blocked_count"] == 1
    assert "--record-receipt" in bridge["next_recording_command"]
    template = next(action for action in bridge["actions"] if action["command"] == "uv run pytest <paths>")
    assert template["status"] == "instantiate-before-recording"
    assert template["placeholders"] == ["<paths>"]
    assert template["admission_reason"] == "unresolved-command-template"
    assert "Substitute every placeholder" in template["safe_recovery"]
    assert "recording_command" not in template
    assert template["next_action"] == "instantiate placeholders, run the concrete command, then record the actual result"


def test_every_bridge_result_is_admissible_but_only_passed_satisfies_proof() -> None:
    from agentic_workspace.proof_receipt_admission import proof_receipt_admission
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_bridge_payload

    bridge = _proof_receipt_bridge_payload(
        changed_paths=["src/example.py"],
        proof_receipt_reconciliation={"commands": [{"command": "make test", "evidence_state": "missing"}]},
        cli_invoke=REPO_LOCAL_CLI_INVOKE,
    )
    for result in bridge["actions"][0]["result_options"]:
        admission = proof_receipt_admission(
            {
                "kind": "agentic-workspace/proof-receipt/v1",
                "command": "make test",
                "result": result,
                "recorded_at": "2026-07-11T10:00:00+00:00",
                "changed_paths": ["src/example.py"],
            }
        )
        assert admission["admitted"] is True
        assert admission["result_class"] == result
        assert admission["proof_sufficient"] is (result == "passed")


@pytest.mark.parametrize(
    ("result", "expected_state"),
    [("passed", "accepted"), ("failed", "recorded-failed"), ("skipped", "recorded-skipped"), ("waived", "recorded-waived")],
)
def test_every_bridge_result_reconciles_through_admission_contract(tmp_path: Path, result: str, expected_state: str) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt_path = tmp_path / ".agentic-workspace/local/proof-receipts/last.json"
    receipt_path.parent.mkdir(parents=True)
    _write(tmp_path / "src/example.py", "example\n")
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make test",
        "result": result,
        "recorded_at": "2026-07-11T10:00:00+00:00",
        "changed_paths": ["src/example.py"],
    }
    receipt["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=receipt["changed_paths"], command=receipt["command"])
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        required_commands=["make test"],
        changed_paths=["src/example.py"],
        selected_commands=[{"command": "make test", "lane": "workspace_cli"}],
    )
    state = reconciliation["commands"][0]
    assert state["evidence_state"] == expected_state
    assert state["evidence_state"] != "record-stale-untrusted"
    if result in {"skipped", "waived"}:
        assert state["proof_sufficient"] is False
        assert state["result_class"] == result


def test_proof_changed_projects_learned_route_model_for_two_route_classes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "docs" / "runbook.md", "# Runbook\n")
    _write(tmp_path / "src" / "security" / "policy.py", "ALLOW = True\n")
    _write(tmp_path / "scripts" / "check_docs.py", "print('docs ok')\n")
    _write(tmp_path / "scripts" / "check_access.py", "print('access ok')\n")
    docs_route = {
        "state": "confirmed",
        "route_class": "docs-process",
        "intent_type": "static-check",
        "candidate_command": "python scripts/check_docs.py",
        "source": "memory",
        "confidence": "high",
        "requires_live_confirmation": False,
        "scope": "docs",
        "owner": "Memory",
        "provenance": "review feedback showed docs/process changes need path-reference checks",
        "learned_at": "2026-07-06",
        "risk_markers": ["docs-link-drift"],
        "evidence": [{"source": "review", "review_ref": "#1993", "summary": "docs path-reference misses recurred"}],
        "proof_classes": {
            "required": ["python scripts/check_docs.py"],
            "recommended": ["manual changed-link spot check"],
            "not_applicable": ["full workspace typecheck"],
        },
        "override_semantics": {
            "escalate_when": ["docs generator or published output changes"],
            "repo_policy_overrides": True,
            "rule": "Docs-process learned routes may not weaken generated documentation proof.",
        },
    }
    access_route = {
        "state": "confirmed",
        "route_class": "access-audit",
        "intent_type": "behavior-test",
        "candidate_command": "python scripts/check_access.py",
        "source": "memory",
        "confidence": "high",
        "requires_live_confirmation": False,
        "scope": "src/security",
        "owner": "Memory",
        "provenance": "access-control closeout required stronger route than generic test",
        "learned_at": "2026-07-06",
        "risk_markers": ["authorization", "audit"],
        "evidence": [{"source": "dogfood", "source_path": "tests/test_access_control.py", "summary": "access paths need focused checks"}],
        "proof_classes": {
            "required": ["python scripts/check_access.py"],
            "optional_confidence": ["manual policy-diff review"],
            "unavailable_manual": ["record unavailable audit harness evidence"],
        },
        "override_semantics": {
            "escalate_when": ["auth boundary changes", "user requests high assurance"],
            "requires_human_review_when": ["legal/compliance certification is claimed"],
        },
    }
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        "\n".join(
            [
                "# Proof routes",
                "",
                f"agentic-workspace-proof-route: {json.dumps(docs_route, sort_keys=True)}",
                f"agentic-workspace-proof-route: {json.dumps(access_route, sort_keys=True)}",
            ]
        ),
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/runbook.md",
                "src/security/policy.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    compact = json.loads(capsys.readouterr().out)["learned_proof_route_model"]
    assert compact["status"] == "selected"
    assert set(compact["route_classes"]) >= {"docs-process", "access-audit"}
    assert compact["selected_route_count"] == 2
    assert compact["fallback"]["status"] == "not-needed"
    assert "Route class names are host-owned evidence fields" in compact["repo_neutrality_rule"]
    assert compact["proof_class_vocabulary"] == [
        "required",
        "recommended",
        "optional_confidence",
        "unavailable_manual",
        "not_applicable",
    ]

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/runbook.md",
                "src/security/policy.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    model = answer["learned_proof_route_model"]
    assert model["status"] == "selected"
    selected = {route["route_class"]: route for route in model["selected_routes"]}
    assert selected["docs-process"]["proof_classes"]["required"] == ["python scripts/check_docs.py"]
    assert selected["docs-process"]["proof_classes"]["recommended"] == ["manual changed-link spot check"]
    assert selected["docs-process"]["proof_classes"]["not_applicable"] == ["full workspace typecheck"]
    assert selected["access-audit"]["proof_classes"]["required"] == ["python scripts/check_access.py"]
    assert selected["access-audit"]["proof_classes"]["optional_confidence"] == ["manual policy-diff review"]
    assert selected["access-audit"]["proof_classes"]["unavailable_manual"] == ["record unavailable audit harness evidence"]
    assert selected["access-audit"]["override_semantics"]["escalate_when"] == [
        "auth boundary changes",
        "user requests high assurance",
    ]
    assert selected["docs-process"]["source"]["provenance"] == "review feedback showed docs/process changes need path-reference checks"
    assert "python scripts/check_docs.py" in answer["required_commands"]
    assert "python scripts/check_access.py" in answer["required_commands"]
    assert model["closeout_semantics"]["issue_closure"] == "learned proof route selection alone never authorizes issue or parent closure"


def test_proof_tiny_includes_closeout_summary_for_pr_validation(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    summary = payload["proof_closeout_summary"]
    assert summary["changed_paths"] == ["llms.txt"]
    assert summary["route"]["maturity"] == "conservative-fallback"
    assert summary["remaining_gap_count"] == 4
    assert summary["route_maturity"] == {"status": "blocked", "blocker_count": 2}
    assert "conservative-fallback" in summary["human_summary"]


def test_proof_changed_memory_negative_route_suppresses_candidate(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "pytest"}}))
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "proof-routes.md",
        """
# Failed proof routes

agentic-workspace-proof-route: {"state":"negative","intent_type":"behavior-test","candidate_command":"npm test","source":"memory","confidence":"high","requires_live_confirmation":true,"scope":"repo","owner":"Memory","provenance":"npm test failed because pytest is not installed","learned_at":"2026-06-02"}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["learned_route_hints"]["negative"][0]["candidate_command"] == "npm test"
    assert "npm test" not in answer["target_proof_capabilities"]["candidate_commands"]
    assert answer["required_commands"] == []
    model = answer["learned_proof_route_model"]
    assert model["fallback"]["status"] == "used"
    assert model["routes"][0]["proof_classes"]["not_applicable"] == ["npm test"]
    assert model["routes"][0]["state"] == "negative"
    assert answer["proof_route_selection"]["selected_command"] is None
    assert answer["proof_route_selection"]["critical_warnings"] == ["1 learned negative route(s) suppressed candidate proof commands."]
    learning = answer["host_repo_learning"]
    assert learning["negative_evidence"]["status"] == "present"
    assert learning["negative_evidence"]["items"][0]["command"] == "npm test"
    assert learning["actionable_next_steps"]["status"] == "present"


def test_proof_changed_reports_proof_route_lifecycle_states(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        """
# Proof route lifecycle

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"static-check","candidate_command":"npm run lint","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"repo","owner":"Memory","provenance":"lint route confirmed in prior closeout","learned_at":"2026-06-02"}
agentic-workspace-proof-route: {"state":"stale","intent_type":"behavior-test","candidate_command":"npm run old-test","source":"memory","confidence":"medium","requires_live_confirmation":true,"scope":"repo","owner":"Memory","provenance":"old route was not found during setup","learned_at":"2026-06-02"}
agentic-workspace-proof-route: {"state":"negative","intent_type":"behavior-test","candidate_command":"npm test","source":"memory","confidence":"high","requires_live_confirmation":true,"scope":"repo","owner":"Memory","provenance":"npm test invokes the wrong runner","learned_at":"2026-06-02"}
agentic-workspace-proof-route: {"state":"superseded","intent_type":"behavior-test","candidate_command":"npm run legacy-test","source":"memory","confidence":"medium","requires_live_confirmation":true,"scope":"repo","owner":"Memory","provenance":"legacy route replaced by package lint route","learned_at":"2026-06-02","superseded_by":"npm run lint"}
agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"npm run missing-owner","source":"memory","confidence":"high","requires_live_confirmation":false}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    lifecycle = hints["lifecycle"]
    assert lifecycle["state_counts"] == {
        "candidate": 0,
        "confirmed": 1,
        "invalid-authority": 1,
        "negative": 1,
        "stale": 1,
        "superseded": 1,
    }
    assert lifecycle["bucket_counts"] == {
        "confirmed": 1,
        "stale": 1,
        "negative": 1,
        "superseded": 1,
        "invalid": 1,
    }
    assert hints["confirmed"][0]["candidate_command"] == "npm run lint"
    assert hints["negative"][0]["candidate_command"] == "npm test"
    assert hints["superseded"][0]["superseded_by"] == "npm run lint"
    assert hints["invalid"][0]["state"] == "invalid-authority"
    assert hints["invalid"][0]["original_state"] == "confirmed"
    assert "npm test" not in answer["target_proof_capabilities"]["candidate_commands"]
    warnings = answer["proof_next_decision"]["warnings"]
    assert "1 learned route lesson(s) are missing authoritative provenance metadata." in warnings
    assert "1 learned route hint(s) are stale or unavailable." in warnings
    assert "1 learned negative route(s) suppressed candidate proof commands." in warnings


def test_proof_changed_incomplete_confirmed_memory_route_is_not_authoritative(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "app.py", "print('ok')\n")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        """
# Incomplete proof routes

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"python -m compileall src","source":"memory","confidence":"high","requires_live_confirmation":false}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.py", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    assert hints["confirmed"] == []
    assert hints["invalid"][0]["original_state"] == "confirmed"
    assert hints["invalid"][0]["state"] == "invalid-authority"
    assert hints["lifecycle"]["state_counts"]["invalid-authority"] == 1
    assert set(hints["invalid"][0]["missing_fields"]) == {"owner", "scope", "provenance", "learned_at"}
    assert answer["required_commands"] == []
    assert answer["proof_route_selection"]["selected_command"] is None
    learning = answer["host_repo_learning"]
    assert learning["invalid_learning_evidence"]["status"] == "present"
    assert (
        "candidate_command, state, intent_type, owner, scope, provenance, and learned_at" in learning["invalid_learning_evidence"]["rule"]
    )
    assert "recapture this proof-route lesson" in learning["invalid_learning_evidence"]["items"][0]["recovery"]


def test_proof_changed_incomplete_negative_memory_route_does_not_suppress_candidate(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run"}}))
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "proof-routes.md",
        """
# Incomplete failed proof routes

agentic-workspace-proof-route: {"state":"negative","intent_type":"behavior-test","candidate_command":"npm test","source":"memory","confidence":"high","requires_live_confirmation":true}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    assert hints["negative"] == []
    assert hints["invalid"][0]["original_state"] == "negative"
    assert hints["invalid"][0]["state"] == "invalid-authority"
    assert "npm test" in answer["target_proof_capabilities"]["candidate_commands"]
    assert answer["proof_route_selection"]["selected_command"]["command"] == "npm test"
    learning = answer["host_repo_learning"]
    assert learning["negative_evidence"]["status"] == "none"
    assert learning["invalid_learning_evidence"]["items"][0]["command"] == "npm test"


def test_proof_changed_host_policy_disallows_generic_discovered_commands(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.no_npm_test]
required_commands = []
optional_commands = []
review_aids = []
disallowed_commands = ["npm test"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "proof-route-hints.json",
        json.dumps(
            {
                "kind": "agentic-workspace/proof-route-hints/v1",
                "schema_version": "proof-route-hints/v1",
                "source": "lifecycle-discovery",
                "rule": "Advisory proof route hints are not host policy; proof selection must live-confirm them before emitting commands.",
                "hints": [
                    {
                        "id": "package-json:test",
                        "intent_type": "behavior-test",
                        "candidate_command": "npm test",
                        "source": "package-json",
                        "source_path": "package.json",
                        "confidence": "medium",
                        "requires_live_confirmation": True,
                    }
                ],
            }
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", why_now = "prove host policy precedence." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Plan Alpha",
        item_id="plan-alpha",
        status="in-progress",
        why_now="prove host policy precedence.",
        next_action="run proof selection.",
        done_when="host policy blocks disallowed command.",
    )
    record["adaptive_assurance"] = {
        "level": "medium",
        "reason": "host disallows npm test",
        "proof_profiles": ["no_npm_test"],
    }
    planning_installer._write_execplan_record(record_path=record_path, record=record)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["learned_route_hints"]["confirmed"][0]["candidate_command"] == "npm test"
    assert "npm test" not in answer["required_commands"]
    assert "npm run lint" in answer["required_commands"]
    assert answer["configured_policy"][0]["disallowed_commands"] == ["npm test"]
    blocked_commands = answer["host_policy_blocked_commands"]
    assert {item["selected_by_lane"] for item in blocked_commands} == {"workspace_cli", "learned_route:package-json:test"}
    assert all(
        {
            "lane": "concern:no_npm_test",
            "proof_profile": "no_npm_test",
            "command": "npm test",
            "configured_command": "npm test",
            "reason": "host-configured proof profile disallows this command",
        }.items()
        <= item.items()
        for item in blocked_commands
    )
    assert answer["proof_route_selection"]["critical_warnings"] == ["Host proof policy blocked one or more candidate proof commands."]
    assert answer["proof_route_explanation"]["host_policy_blocked_commands"] == answer["host_policy_blocked_commands"]
    assert answer["proof_next_decision"]["warnings"] == ["Host proof policy blocked one or more candidate proof commands."]


def test_proof_verbose_explains_live_discovery_when_no_setup_adopt_route_hints(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    learning = answer["proof_route_explanation"]["setup_adopt_route_learning"]
    assert learning["status"] == "live-discovery-sufficient"
    assert learning["hint_count"] == 0
    assert learning["route_map_decision"] == "no-persisted-route-map-needed"
    assert "live target capability discovery is sufficient" in learning["reason"]
    assert learning["separation"]["setup_adopt_learning"] == "advisory route hints from lifecycle discovery, never host policy"


def test_proof_changed_validation_plan_uses_resolved_cli_invoke(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    step = payload["answer"]["validation_plan"]["required"][0]
    expected_target = tmp_path.as_posix()
    assert step["command"] == f'uv run agentic-workspace summary --target "{expected_target}" --format json'
    assert step["run"] == f'uv run agentic-workspace summary --target "{expected_target}" --format json'


def test_proof_tiny_detail_commands_use_resolved_cli_invoke(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["detail_command"].startswith("uv run agentic-workspace proof ")
    assert payload["next"]["command"] is None or not payload["next"]["command"].startswith("agentic-workspace ")


def test_proof_changed_includes_active_assurance_concern_profiles(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(tmp_path / "tests" / "test_access_control.py", "def test_access_control_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance]
default_level = "medium"
strict_closeout = true

[assurance.proof_profiles.access_control]
required_commands = ["uv run pytest tests/test_access_control.py"]
optional_commands = ["uv run pytest tests/test_auth_integration.py"]
review_aids = [".agentic-workspace/agent-aids/access-control.md"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", why_now = "prove concern-based proof." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Plan Alpha",
        item_id="plan-alpha",
        status="in-progress",
        why_now="prove concern-based proof.",
        next_action="run proof selection.",
        done_when="concern proof appears.",
    )
    record["adaptive_assurance"] = {
        "level": "high",
        "reason": "touches access control",
        "agent_may_escalate": True,
        "agent_may_deescalate": False,
        "strict_closeout": True,
        "required_refs": ["security_refs"],
        "proof_profiles": ["access_control"],
        "required_gates": ["security-review"],
    }
    record["traceability_refs"] = {"security_refs": ["SEC-1"]}
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
    planning_installer._write_execplan_record(record_path=record_path, record=record)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/test_access_control.py" in answer["required_commands"]
    assert "uv run pytest tests/test_auth_integration.py" in answer["optional_commands"]
    assert answer["planning_assurance"]["adaptive_assurance"]["level"] == "high"
    assert answer["planning_assurance"]["missing_required_refs"] == []
    assert answer["planning_assurance"]["closeout_status"] == "blocked"
    assert answer["planning_assurance"]["trust_state"]["assurance_level"] == "high"
    assert answer["planning_assurance"]["trust_state"]["assurance_level_source"] == "explicit-slice-field"
    assert answer["planning_assurance"]["trust_state"]["gate_states"][0]["enforcement"] == "blocking"
    assert answer["planning_assurance"]["trust_state"]["ref_states"][0]["trust"] == "satisfied"
    assert answer["planning_assurance"]["trust_state"]["proof_profile_states"][0]["state"] == "selected"
    assert answer["planning_assurance"]["trust_state"]["proof_execution_evidence"]["counts"]["missing"] >= 1
    assert answer["planning_assurance"]["pending_blocking_gates"][0]["id"] == "security-review"
    concern_step = [step for step in answer["validation_plan"]["required"] if step.get("lane_id") == "concern:access_control"][0]
    assert concern_step["command"] == "uv run pytest tests/test_access_control.py"
    assert answer["selected_lanes"][-1]["id"] == "concern:access_control"
    assert answer["selected_lanes"][-1]["review_aids"] == [".agentic-workspace/agent-aids/access-control.md"]


def test_proof_changed_includes_matched_assurance_requirement_profile(tmp_path: Path, capsys) -> None:
    _write(tmp_path / "tests" / "privacy" / "test_privacy.py", "def test_privacy_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.privacy]
required_commands = ["uv run pytest tests/privacy -q"]
optional_commands = ["uv run pytest tests/privacy_integration -q"]
review_aids = ["docs/compliance/privacy.md"]

[assurance.requirements.privacy_data]
level = "high"
applies_to_paths = ["db/migrations/**"]
authority_refs = ["docs/compliance/privacy.md"]
required_evidence = ["authority_consulted"]
proof_profile = "privacy"
force = "required-before-closeout"
blocking_claims = ["claim-work-complete", "close-parent-lane"]
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "db/migrations/001_privacy.sql",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/privacy -q" in answer["required_commands"]
    assert "uv run pytest tests/privacy_integration -q" in answer["optional_commands"]
    assert answer["assurance_requirements"]["active"][0]["id"] == "privacy_data"
    lane = [item for item in answer["selected_lanes"] if item.get("requirement_id") == "privacy_data"][0]
    assert lane["proof_profile"] == "privacy"
    assert lane["applies_because"] == ["changed path matched db/migrations/**"]


def test_proof_changed_marks_missing_path_specific_proof_unavailable(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.model_harness]
required_commands = ["uv run pytest tests/test_model_cli_harness.py -q"]

[assurance.requirements.model_harness]
level = "medium"
applies_to_paths = ["scripts/model_cli_harness/**"]
authority_refs = ["docs/maintainer/test-knowledge-inventory.md"]
required_evidence = ["current harness proof selected"]
proof_profile = "model_harness"
force = "required-before-closeout"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "scripts/model_cli_harness/run_model_cli_harness.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/test_model_cli_harness.py -q" not in answer["required_commands"]
    assert answer["unavailable_proof_commands"] == [
        {
            "lane": "assurance-requirement:model_harness",
            "command": "uv run pytest tests/test_model_cli_harness.py -q",
            "reason": "selected proof command references path-like arguments absent from the target repo",
            "missing_paths": "tests/test_model_cli_harness.py",
        }
    ]
    assert answer["unavailable_commands"] == [
        {
            "kind": "proof-command-unavailable/v1",
            "command": "uv run pytest tests/test_model_cli_harness.py -q",
            "lane": "assurance-requirement:model_harness",
            "reason": "selected proof command references path-like arguments absent from the target repo",
            "missing_paths": "tests/test_model_cli_harness.py",
        }
    ]
    assert answer["manual_verification"]["status"] == "required"
    assert answer["manual_verification"]["unavailable_commands"] == answer["unavailable_commands"]


def test_proof_changed_keeps_existing_path_specific_proof_required(tmp_path: Path, capsys) -> None:
    _write(tmp_path / "tests" / "test_model_cli_harness.py", "def test_harness_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.model_harness]
required_commands = ["uv run pytest tests/test_model_cli_harness.py -q"]

[assurance.requirements.model_harness]
level = "medium"
applies_to_paths = ["scripts/model_cli_harness/**"]
authority_refs = ["docs/maintainer/test-knowledge-inventory.md"]
required_evidence = ["current harness proof selected"]
proof_profile = "model_harness"
force = "required-before-closeout"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "scripts/model_cli_harness/run_model_cli_harness.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/test_model_cli_harness.py -q" in answer["required_commands"]
    assert answer.get("unavailable_proof_commands", []) == []


def test_proof_changed_includes_matched_subsystem_assurance_profile(tmp_path: Path, capsys) -> None:
    _write(tmp_path / "tests" / "audit" / "test_audit.py", "def test_audit_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "audit-log"
paths = ["src/audit/**"]
owns = ["audit trail semantics"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.audit]
required_commands = ["uv run pytest tests/audit -q"]
optional_commands = ["uv run pytest tests/audit_integration -q"]
review_aids = ["docs/reviews/audit.md"]

[assurance.subsystem_profiles.audit-log]
assurance_level = "high"
requirement_refs = ["docs/system-requirements.md#auditability"]
required_evidence = ["requirement_grounding", "manual_review"]
proof_profile = "audit"
force = "required-before-closeout"
blocked_without_evidence = ["auditability-complete"]
claim_boundary = "subsystem-scoped"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/audit/events.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/audit -q" in answer["required_commands"]
    assert "uv run pytest tests/audit_integration -q" in answer["optional_commands"]
    subsystem = answer["assurance_requirements"]["subsystem_assurance"]
    assert subsystem["matched_subsystem_ids"] == ["audit-log"]
    assert subsystem["effective_assurance_level"] == "high"
    lane = [item for item in answer["selected_lanes"] if item.get("requirement_id") == "subsystem:audit-log"][0]
    assert lane["proof_profile"] == "audit"
    assert lane["applies_because"] == ["changed path matched subsystem audit-log"]


def test_proof_current_includes_active_planning_assurance_requirement_profile(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(tmp_path / "tests" / "privacy" / "test_privacy.py", "def test_privacy_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.privacy]
required_commands = ["uv run pytest tests/privacy -q"]
optional_commands = ["uv run pytest tests/privacy_integration -q"]
review_aids = ["docs/compliance/privacy.md"]

[assurance.requirements.privacy_data]
level = "high"
applies_to_planning_refs = ["privacy_data"]
authority_refs = ["docs/compliance/privacy.md"]
required_evidence = ["authority_consulted"]
proof_profile = "privacy"
force = "required-before-closeout"
blocking_claims = ["claim-work-complete", "close-parent-lane"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "privacy-plan", status = "in-progress", surface = ".agentic-workspace/planning/execplans/privacy-plan.plan.json", why_now = "prove privacy requirement." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Privacy Plan",
        item_id="privacy-plan",
        status="in-progress",
        why_now="prove privacy requirement.",
        next_action="run proof selection.",
        done_when="privacy proof appears.",
    )
    record["adaptive_assurance"] = {
        "level": "high",
        "requirement_refs": ["privacy_data"],
        "strict_closeout": True,
    }
    _write_json(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "privacy-plan.plan.json", record)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--current", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/privacy -q" in answer["required_commands"]
    assert "uv run pytest tests/privacy_integration -q" in answer["optional_commands"]
    assert answer["assurance_requirements"]["active"][0]["id"] == "privacy_data"
    lane = [item for item in answer["selected_lanes"] if item.get("requirement_id") == "privacy_data"][0]
    assert lane["proof_profile"] == "privacy"
    assert lane["applies_because"] == ["planning ref matched privacy_data"]


def test_proof_current_selects_active_plan_validation_commands(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / "tests" / "test_workspace_proof_cli.py",
        "def test_proof_current_selects_active_plan_validation_commands():\n    assert True\n",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "validation-plan", status = "in-progress", surface = ".agentic-workspace/planning/execplans/validation-plan.plan.json", why_now = "prove current validation routing." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Validation Plan",
        item_id="validation-plan",
        status="in-progress",
        why_now="prove current validation routing.",
        next_action="run proof selection.",
        done_when="current proof names the active validation commands.",
    )
    record["validation_commands"] = [
        "uv run pytest tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands -q"
    ]
    _write_json(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "validation-plan.plan.json", record)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--current", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["required_commands"] == [
        "uv run pytest tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands -q"
    ]
    assert answer["selected_lanes"][0]["id"] == "planning:active_validation"
    assert "manual_verification" not in answer


def test_proof_changed_reports_compact_proof_execution_evidence_states(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance]
strict_closeout = true

[assurance.proof_profiles.assurance_matrix]
required_commands = [
  "selected-command",
  "run-command",
  "pass-command",
  "fail-command",
  "skip-command",
  "unavailable-command",
  "waived-command",
]
optional_commands = []
review_aids = []
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "proof-evidence", status = "in-progress", surface = ".agentic-workspace/planning/execplans/proof-evidence.plan.json", why_now = "prove evidence states." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "proof-evidence.plan.json"
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Proof Evidence",
        item_id="proof-evidence",
        status="in-progress",
        why_now="prove evidence states.",
        next_action="run proof selection.",
        done_when="proof evidence states appear.",
    )
    record["adaptive_assurance"] = {
        "level": "critical",
        "strict_closeout": True,
        "proof_profiles": ["assurance_matrix"],
    }
    record["proof_report"] = {
        "validation proof": "synthetic assurance commands",
        "proof achieved now": "mixed",
        "proof execution evidence": json.dumps(
            [
                {"command": "selected-command", "status": "selected", "evidence_ref": "local:selected"},
                {"command": "run-command", "status": "run", "evidence_ref": "local:run"},
                {"command": "pass-command", "status": "passed", "evidence_ref": "local:pass"},
                {"command": "fail-command", "status": "failed", "evidence_ref": "local:fail"},
                {"command": "skip-command", "status": "skipped", "reason": "not applicable"},
                {"command": "unavailable-command", "status": "unavailable", "reason": "tool missing"},
                {"command": "waived-command", "status": "waived", "reason": "covered by manual review"},
            ]
        ),
    }
    planning_installer._write_execplan_record(record_path=record_path, record=record)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--format",
                "json",
            ]
        )
        == 0
    )

    evidence = json.loads(capsys.readouterr().out)["answer"]["planning_assurance"]["trust_state"]["proof_execution_evidence"]
    assert evidence["state_model"] == ["selected", "run", "passed", "failed", "skipped", "unavailable", "waived", "missing"]
    assert evidence["counts"] == {
        "selected": 1,
        "run": 1,
        "passed": 1,
        "failed": 1,
        "skipped": 1,
        "unavailable": 1,
        "waived": 1,
        "missing": 2,
    }
    assert evidence["lower_trust_required_count"] == 7
    selected = next(item for item in evidence["commands"] if item["command"] == "selected-command")
    assert selected["trust"] == "lower-trust"
    run = next(item for item in evidence["commands"] if item["command"] == "run-command")
    assert run["trust"] == "lower-trust"
    waived = next(item for item in evidence["commands"] if item["command"] == "waived-command")
    assert waived["trust"] == "satisfied"
    assert waived["waiver_state"] == "waived-with-reason"


def test_proof_changed_selector_routes_agent_aid_changes_to_manifest_lane(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json",
                ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["agent_aid_manifests"]
    assert answer["required_commands"] == ["uv run python scripts/check/check_agent_aids.py --quiet-success"]
    assert "candidate aids" in answer["selected_lanes"][0]["recovery_signal"]
    assert "uv run pytest tests -q" not in answer["required_commands"]


def test_proof_changed_selector_routes_readme_to_docs_review(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    docs_diff = "git diff -- README.md docs .agentic-workspace/docs packages/planning/README.md packages/memory/README.md"
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["selected_lanes"][0]["proof_kind"] == "diff-review"
    assert answer["required_commands"] == [docs_diff]
    assert answer["selected_lanes"][0]["non_local_references"] == ["https://github.com/rickardvh/command-generation/blob/main/README.md"]
    assert "https://github.com" not in answer["required_commands"][0]
    assert "uv run pytest tests -q" not in answer["required_commands"]
    assert answer["surface_value_review"]["reviewed_paths"][0]["surface_class"] == "adapter_or_repo_intent_surface"


def test_proof_changed_selector_applies_learned_docs_process_route(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    docs_process_command = (
        "git diff -- README.md docs .agentic-workspace/docs packages/planning/README.md packages/memory/README.md "
        ".github/pull_request_template.md .github/ISSUE_TEMPLATE"
    )
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "docs-process-proof.md",
        f"""
# Docs/process proof

agentic-workspace-proof-route: {{"state":"confirmed","intent_type":"docs-diff-review","candidate_command":"{docs_process_command}","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"repo","owner":"Memory","provenance":"docs/process route confirmed from markdown path reference, template-burden, and local-tool coupling review","learned_at":"2026-07-06"}}
""",
    )
    _write(
        tmp_path / ".github" / "pull_request_template.md",
        """
# Pull Request

## Optional high-risk evidence

- Not applicable; no high-risk lanes.
""",
    )
    _write(tmp_path / ".github" / "ISSUE_TEMPLATE" / "bug.md", "# Bug\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                ".github/pull_request_template.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "workspace_cli" not in lane_ids
    assert lane_ids[0] == "repo_docs_review"
    assert answer["docs_process_route"]["status"] == "active"
    assert answer["docs_process_route"]["route_maturity"] == "repo-learned"
    assert answer["required_commands"] == [docs_process_command]
    assert answer["proof_route_selection"]["selected_command"]["route_source"] == "repo-learned-proof-route"
    assert answer["proof_command_explanations"]["required"][0]["reason_classes"] == ["learned-repo-evidence"]
    assert answer["proof_closeout_summary"]["route"]["maturity"] == "learned-confirmed"
    assert answer["template_burden_review"]["status"] == "clear"
    assert answer["routing_reductions"][0]["from_lane"] == "workspace_cli"


def test_proof_changed_selector_reviews_markdown_repo_path_references(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(tmp_path / "docs" / "existing.md", "# Existing\n")
    _write(
        tmp_path / "docs" / "guide.md",
        """
# Guide

Concrete path: `docs/missing.md`
Valid path: [existing](docs/existing.md)
Example path: `docs/<area>/template.md`
Command snippet: `uv run python scripts/check.py`
Anchor only: [section](#local-anchor)
Remote link: [site](https://example.com/docs/missing.md)
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "docs/guide.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    review = answer["markdown_path_reference_review"]
    assert review["status"] == "attention-needed"
    assert review["changed_paths"] == ["docs/guide.md"]
    assert review["missing_count"] == 1
    assert review["valid_count"] == 1
    assert review["ambiguous_count"] == 2
    assert review["missing_references"][0]["reference"] == "docs/missing.md"
    assert review["missing_references"][0]["line"] == 4
    assert review["valid_references"][0]["reference"] == "docs/existing.md"
    assert {item["reference"] for item in review["ambiguous_references"]} == {
        "docs/<area>/template.md",
        "uv run python scripts/check.py",
    }
    route_learning = review["route_learning_evidence"]
    assert route_learning["candidate_route"] == "docs/process path-reference check"
    assert "--files docs/guide.md" in route_learning["capture_command"]
    assert route_learning["memory_note_entry"].startswith("agentic-workspace-proof-route:")
    assert '"intent_type": "static-check"' in route_learning["memory_note_entry"]


def test_proof_changed_selector_reviews_scoped_local_tool_coupling(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / "docs" / "guide.md",
        """
# Guide

This repository guidance must stay tool-neutral.
Contributors must run `agentic-workspace start` before opening a PR.
Optional local evidence may include `.agentic-workspace` proof receipts.
Agentic Workspace notes appear during local investigation.
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/guide.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    review = answer["local_tool_coupling_review"]
    assert review["status"] == "attention-needed"
    assert review["flagged_count"] == 1
    assert review["accepted_optional_count"] == 1
    assert review["ambiguous_count"] == 1
    assert review["flagged_references"][0]["line"] == 5
    assert "mandatory repository-process" in review["flagged_references"][0]["reason"]
    assert ".agentic-workspace" in review["accepted_optional_references"][0]["matched_terms"]


def test_proof_changed_selector_does_not_globally_ban_local_tool_references(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(tmp_path / "docs" / "guide.md", "Local setup can mention `agentic-workspace start`.\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "docs/guide.md", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "local_tool_coupling_review" not in answer


def test_proof_changed_selector_reviews_template_burden(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "template-burden.md",
        """
# Template burden review

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"static-check","candidate_command":"agentic-workspace proof --changed <template paths> --format json","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"docs/process template-burden","owner":"Memory","provenance":"human review asked PR templates to include low-risk answer paths","learned_at":"2026-07-06"}
""",
    )
    _write(
        tmp_path / ".github" / "pull_request_template.md",
        """
# Pull Request

## Evidence gaps

- List all missing evidence.
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".github/pull_request_template.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    review = answer["template_burden_review"]
    assert review["status"] == "attention-needed"
    assert review["activation"]["signals"][0]["source"] == "repo-learned-proof-route"
    assert review["flagged_count"] == 1
    assert review["flagged_sections"][0]["line"] == 4
    assert "low-risk answer path" in review["flagged_sections"][0]["reason"]
    assert review["route_learning_evidence"]["memory_note_entry"].startswith("agentic-workspace-proof-route:")


def test_proof_changed_selector_accepts_optional_template_burden_guidance(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "template-burden.md",
        """
# Template burden review

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"static-check","candidate_command":"agentic-workspace proof --changed <template paths> --format json","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"docs/process template-burden","owner":"Memory","provenance":"human review asked PR templates to include low-risk answer paths","learned_at":"2026-07-06"}
""",
    )
    _write(
        tmp_path / ".github" / "pull_request_template.md",
        """
# Pull Request

## Optional high-risk evidence

- Not applicable; no high-risk lanes.
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".github/pull_request_template.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    review = answer["template_burden_review"]
    assert review["status"] == "clear"
    assert review["flagged_count"] == 0
    assert review["accepted_count"] == 1


def test_proof_changed_selector_does_not_globally_require_template_burden_review(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / ".github" / "pull_request_template.md",
        """
# Pull Request

## Evidence gaps

- List missing evidence.
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".github/pull_request_template.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    review = answer["template_burden_review"]
    assert review["status"] == "not-active"
    assert review["changed_paths"] == [".github/pull_request_template.md"]
    assert review["flagged_count"] == 0


def test_proof_changed_selector_routes_package_readmes_to_docs_review(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "packages/planning/README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["selected_lanes"][0]["proof_kind"] == "diff-review"
    assert "make test-planning" not in answer["required_commands"]
    assert "git diff -- README.md docs .agentic-workspace/docs" in answer["required_commands"][0]


def test_proof_record_receipt_writes_latest_execution_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".agentic-workspace").mkdir()
    (target / ".agentic-workspace" / "config.toml").write_text("schema_version = 1\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--record-receipt",
                "--receipt-command",
                "uv run pytest tests/test_workspace_proof_cli.py -q",
                "--receipt-result",
                "passed",
                "--receipt-plan",
                "plan-alpha",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    receipt_path = target / ".agentic-workspace" / "local" / "proof-receipts" / "last.json"
    history_path = target / ".agentic-workspace" / "local" / "proof-receipts" / "history.jsonl"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    history = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines()]
    assert payload["status"] == "written"
    assert payload["path"] == ".agentic-workspace/local/proof-receipts/last.json"
    assert payload["history_path"] == ".agentic-workspace/local/proof-receipts/history.jsonl"
    assert receipt["command"] == "uv run pytest tests/test_workspace_proof_cli.py -q"
    assert receipt["result"] == "passed"
    assert receipt["changed_paths"] == ["tests/test_workspace_proof_cli.py"]
    assert receipt["plan_id"] == "plan-alpha"
    assert history == [receipt]
    assert "repair_retry_ladder" not in receipt
    assert "repair_retry_ladder" not in payload


def test_proof_record_receipt_rejects_unresolved_template_before_persistence(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_primitives import _record_proof_receipt_payload

    target = tmp_path / "repo"
    target.mkdir()

    with pytest.raises(WorkspaceUsageError, match="unresolved-command-template") as error:
        _record_proof_receipt_payload(
            target_root=target,
            command="uv run agentic-workspace implement --changed <paths>",
            result="passed",
            changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        )

    assert "Substitute every placeholder" in str(error.value)
    assert not (target / ".agentic-workspace" / "local" / "proof-receipts" / "last.json").exists()
    assert not (target / ".agentic-workspace" / "local" / "proof-receipts" / "history.jsonl").exists()


def test_proof_receipt_admission_rejects_missing_scope_and_consumers_ignore_it(tmp_path: Path) -> None:
    from agentic_workspace.proof_receipt_admission import proof_receipt_admission
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make test-workspace",
        "result": "passed",
        "recorded_at": "2026-07-11T08:00:00+00:00",
        "changed_paths": [],
    }
    admission = proof_receipt_admission(receipt)
    assert admission["status"] == "rejected"
    assert admission["reason"] == "missing-changed-path-scope"

    receipt_path = tmp_path / ".agentic-workspace" / "local" / "proof-receipts" / "last.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        required_commands=["make test-workspace"],
        selected_commands=[],
    )
    assert reconciliation["status"] == "not-recorded"
    assert "receipt" not in reconciliation
    assert reconciliation["commands"][0]["evidence_state"] == "not-run-or-not-recorded"
    assert reconciliation["rejected_latest_receipt"]["admission_reason"] == "missing-changed-path-scope"


def test_reconciliation_selects_newest_admitted_history_when_latest_file_is_rejected(tmp_path: Path) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt_dir = tmp_path / ".agentic-workspace/local/proof-receipts"
    receipt_dir.mkdir(parents=True)
    _write(tmp_path / "src/agentic_workspace/workspace_runtime_proof.py", "fixture\n")
    admitted = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make test-workspace",
        "result": "passed",
        "recorded_at": "2026-07-11T08:00:00+00:00",
        "changed_paths": ["src/agentic_workspace/workspace_runtime_proof.py"],
    }
    admitted["proof_subject"] = build_proof_subject(
        target_root=tmp_path, changed_paths=admitted["changed_paths"], command=admitted["command"]
    )
    older = {**admitted, "result": "failed", "recorded_at": "2026-07-11T07:00:00+00:00"}
    rejected = {**admitted, "command": "make <target>", "recorded_at": "2026-07-11T09:00:00+00:00"}
    (receipt_dir / "history.jsonl").write_text("\n".join(json.dumps(item) for item in (older, admitted)) + "\n", encoding="utf-8")
    (receipt_dir / "last.json").write_text(json.dumps(rejected), encoding="utf-8")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        required_commands=["make test-workspace"],
        selected_commands=[],
    )

    assert reconciliation["status"] == "accepted"
    assert reconciliation["receipt"]["recorded_at"] == admitted["recorded_at"]
    assert reconciliation["receipt"]["command"] == "make test-workspace"
    assert reconciliation["rejected_latest_receipt"]["status"] == "rejected-untrusted"
    assert reconciliation["rejected_latest_receipt"]["admission_reason"] == "unresolved-command-template"
    assert reconciliation["receipt_history"]["record_count"] == 2


@pytest.mark.parametrize(
    ("latest_text", "reason"),
    [("{broken", "latest-receipt-unreadable"), (json.dumps(["not", "an", "object"]), "latest-receipt-not-object")],
)
@pytest.mark.parametrize("with_history", [True, False])
def test_damaged_latest_receipt_does_not_poison_admitted_history(tmp_path: Path, latest_text: str, reason: str, with_history: bool) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt_dir = tmp_path / ".agentic-workspace/local/proof-receipts"
    receipt_dir.mkdir(parents=True)
    _write(tmp_path / "src/agentic_workspace/workspace_runtime_proof.py", "fixture\n")
    admitted = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make test-workspace",
        "result": "passed",
        "recorded_at": "2026-07-11T08:00:00+00:00",
        "changed_paths": ["src/agentic_workspace/workspace_runtime_proof.py"],
    }
    admitted["proof_subject"] = build_proof_subject(
        target_root=tmp_path, changed_paths=admitted["changed_paths"], command=admitted["command"]
    )
    if with_history:
        (receipt_dir / "history.jsonl").write_text(json.dumps(admitted) + "\n", encoding="utf-8")
    (receipt_dir / "last.json").write_text(latest_text, encoding="utf-8")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        required_commands=["make test-workspace"],
        selected_commands=[],
    )

    assert reconciliation["rejected_latest_receipt"]["admission_reason"] == reason
    if with_history:
        assert reconciliation["status"] == "accepted"
        assert reconciliation["receipt"]["command"] == "make test-workspace"
    else:
        assert reconciliation["status"] == "not-recorded"
        assert "receipt" not in reconciliation


def test_proof_failed_receipt_includes_repair_retry_ladder(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".agentic-workspace").mkdir()
    (target / ".agentic-workspace" / "config.toml").write_text("schema_version = 1\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--record-receipt",
                "--receipt-command",
                "make test-workspace",
                "--receipt-result",
                "failed",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    receipt_path = target / ".agentic-workspace" / "local" / "proof-receipts" / "last.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    ladder = payload["repair_retry_ladder"]
    written_ladder = receipt["repair_retry_ladder"]
    assert ladder == written_ladder
    assert ladder["kind"] == "agentic-workspace/proof-repair-retry-ladder/v1"
    assert ladder["trigger"] == "failed-proof-receipt"
    assert ladder["failed_command"] == "make test-workspace"
    assert ladder["full_selected_proof"] == "make test-workspace"
    assert ladder["full_proof_still_required"] is True
    assert ladder["full_rerun_premature"] is True
    assert ladder["focused_commands"] == ["uv run pytest tests/test_workspace_proof_cli.py -q"]
    assert ladder["steps"][0]["commands"] == ["uv run pytest tests/test_workspace_proof_cli.py -q"]
    assert ladder["steps"][1]["command_source"] == "smallest affected package or workspace subset after the focused failure passes"
    assert ladder["steps"][2]["command"] == "make test-workspace"


def test_proof_failed_receipt_clusters_supplied_log(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".agentic-workspace").mkdir()
    (target / ".agentic-workspace" / "config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    log_path = target / ".agentic-workspace" / "local" / "proof-logs" / "workspace-test.log"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        "\n".join(
            [
                "FAILED tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands - AssertionError",
                "FAILED tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands - AssertionError",
                "FAILED tests/test_workspace_proof_generated_packages_cli.py::test_proof_changed_selector_routes_generated_command_packages - AssertionError",
                "=========================== short test summary info ===========================",
            ]
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--record-receipt",
                "--receipt-command",
                "make test-workspace",
                "--receipt-result",
                "failed",
                "--receipt-log",
                ".agentic-workspace/local/proof-logs/workspace-test.log",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    receipt_path = target / ".agentic-workspace" / "local" / "proof-receipts" / "last.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    summary = payload["failure_summary"]
    assert summary == receipt["failure_summary"]
    assert summary["kind"] == "agentic-workspace/proof-failure-summary/v1"
    assert summary["failed_command"] == "make test-workspace"
    assert summary["log_source"]["path"] == ".agentic-workspace/local/proof-logs/workspace-test.log"
    assert summary["summary_trust"] == {
        "level": "higher",
        "source_kind": "repo-local-path",
        "rule": "Repo-local log references preserve audit access.",
    }
    assert summary["failure_line_count"] == 3
    assert summary["cluster_count"] == 2
    assert summary["top_root_cause_clusters"][0]["likely_root"] == "tests/test_workspace_proof_cli.py"
    assert summary["top_root_cause_clusters"][0]["occurrences"] == 2
    assert summary["focused_rerun_commands"][0] == (
        "uv run pytest tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands -q"
    )
    assert summary["full_suite_rerun_premature"] is True
    assert "Use the referenced full log" in summary["guardrails"][1]


def test_proof_failed_receipt_marks_excerpt_failure_summary_lower_trust(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--record-receipt",
                "--receipt-command",
                "uv run pytest tests/test_workspace_proof_cli.py -q",
                "--receipt-result",
                "failed",
                "--receipt-log",
                "FAILED tests/test_workspace_proof_cli.py::test_example - AssertionError",
                "--format",
                "json",
            ]
        )
        == 0
    )

    summary = json.loads(capsys.readouterr().out)["failure_summary"]
    assert summary["log_source"]["kind"] == "caller-supplied-excerpt"
    assert summary["summary_trust"] == {
        "level": "lower",
        "source_kind": "caller-supplied-excerpt",
        "rule": "Caller-supplied excerpts are useful repair hints but lower trust than repo-local logs.",
    }


def test_proof_changed_reconciles_receipt_history_without_duplicate_runs(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(tmp_path / "src/agentic_workspace/workspace_runtime_proof.py", "# proof subject fixture\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--record-receipt",
                "--receipt-command",
                "make test-workspace",
                "--receipt-result",
                "passed",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--record-receipt",
                "--receipt-command",
                "make typecheck",
                "--receipt-result",
                "passed",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    reconciliation = answer["proof_receipt_reconciliation"]
    states = {item["command"]: item for item in reconciliation["commands"]}
    assert reconciliation["status"] == "accepted"
    assert reconciliation["accepted_count"] == 2
    assert reconciliation["receipt"]["command"] == "make typecheck"
    assert reconciliation["receipt_history"]["record_count"] == 2
    assert reconciliation["receipt_history"]["accepted_record_count"] == 2
    assert states["make test-workspace"]["evidence_state"] == "accepted"
    assert states["make test-workspace"]["diagnostic"] == "passed receipt accepted"
    assert states["make typecheck"]["evidence_state"] == "accepted"
    assert states["make typecheck"]["diagnostic"] == "passed receipt accepted"
    assert answer["proof_execution_evidence"]["status"] == "recorded-and-accepted"
    assert answer["proof_receipt_bridge"]["status"] == "complete"
    assert answer["proof_receipt_bridge"]["ready_to_record_count"] == 0
    assert answer["proof_receipt_bridge"]["template_blocked_count"] == 0
    assert answer["proof_receipt_bridge"]["next_action"] == "no receipt action required"
    assert answer["proof_receipt_bridge"]["next_recording_command"] == ""
    assert answer["proof_receipt_bridge"]["actions"] == []
    assert answer["proof_closeout_summary"]["receipt_bridge"] == {
        "status": "complete",
        "missing_receipt_count": 0,
        "detail_selector": "proof_receipt_bridge",
    }
    assert "closeout review" in answer["proof_execution_evidence"]["rule"]


def test_proof_changed_accepts_aggregate_receipt_for_selected_proof_set(tmp_path: Path, capsys) -> None:
    from agentic_workspace.proof_subject import build_proof_subject

    _write_repo_local_proof_target(tmp_path)
    receipt_dir = tmp_path / ".agentic-workspace" / "local" / "proof-receipts"
    _write(tmp_path / "src/agentic_workspace/workspace_runtime_proof.py", "# aggregate fixture\n")
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "selected proof set",
        "result": "passed",
        "recorded_at": "2026-07-09T00:00:00+00:00",
        "changed_paths": ["src/agentic_workspace/workspace_runtime_proof.py"],
        "proof_commands": ["make test-workspace", "make typecheck"],
        "plan_id": "aggregate-proof",
    }
    receipt["proof_subject"] = build_proof_subject(
        target_root=tmp_path,
        changed_paths=receipt["changed_paths"],
        command=receipt["command"],
    )
    _write(receipt_dir / "last.json", json.dumps(receipt, indent=2))
    _write(receipt_dir / "history.jsonl", json.dumps(receipt, sort_keys=True) + "\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    reconciliation = answer["proof_receipt_reconciliation"]
    states = {item["command"]: item for item in reconciliation["commands"]}
    assert reconciliation["status"] == "accepted"
    assert reconciliation["accepted_count"] == 2
    assert states["make test-workspace"]["receipt_match"] == "aggregate-selected-proof"
    assert states["make typecheck"]["diagnostic"] == "aggregate proof_commands receipt accepted"
    assert answer["proof_receipt_bridge"]["status"] == "complete"
    assert answer["proof_execution_evidence"]["status"] == "recorded-and-accepted"


def test_proof_changed_rejects_stale_aggregate_subject(tmp_path: Path, capsys) -> None:
    from agentic_workspace.proof_subject import build_proof_subject

    _write_repo_local_proof_target(tmp_path)
    source = tmp_path / "src/agentic_workspace/workspace_runtime_proof.py"
    _write(source, "before\n")
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "selected proof set",
        "result": "passed",
        "recorded_at": "2026-07-09T00:00:00+00:00",
        "changed_paths": ["src/agentic_workspace/workspace_runtime_proof.py"],
        "proof_commands": ["make test-workspace", "make typecheck"],
    }
    receipt["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=receipt["changed_paths"], command=receipt["command"])
    receipt_dir = tmp_path / ".agentic-workspace" / "local" / "proof-receipts"
    _write(receipt_dir / "history.jsonl", json.dumps(receipt) + "\n")
    _write(source, "after\n")

    assert (
        cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", str(receipt["changed_paths"][0]), "--format", "json"]) == 0
    )

    states = {item["command"]: item for item in json.loads(capsys.readouterr().out)["answer"]["proof_receipt_reconciliation"]["commands"]}
    state = states["make test-workspace"]
    assert state["evidence_state"] == "subject-stale"
    assert state["receipt_match"] == "aggregate-selected-proof"
    assert state["minimum_rerun_command"] == "make test-workspace"


@pytest.mark.parametrize(
    ("subject", "changed_path", "expected_status"),
    [
        ("declared", "src/b.py", "partially-reusable"),
        ("incompatible", "src/a.py", "incompatible"),
        ("legacy", "src/a.py", "unverifiable"),
    ],
)
def test_proof_changed_reports_nonreusable_direct_subject_states(
    tmp_path: Path, capsys, subject: str, changed_path: str, expected_status: str
) -> None:
    from agentic_workspace.proof_subject import build_proof_subject

    _write_repo_local_proof_target(tmp_path)
    _write(tmp_path / "src/a.py", "a\n")
    _write(tmp_path / "src/b.py", "b\n")
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make test-workspace",
        "result": "passed",
        "recorded_at": "2026-07-09T00:00:00+00:00",
        "changed_paths": ["src/a.py"],
    }
    if subject != "legacy":
        receipt["proof_subject"] = build_proof_subject(
            target_root=tmp_path, changed_paths=receipt["changed_paths"], command=receipt["command"]
        )
    if subject == "incompatible":
        receipt["proof_subject"]["claim_classes"] = ["documentation-review"]
    receipt_dir = tmp_path / ".agentic-workspace" / "local" / "proof-receipts"
    _write(receipt_dir / "history.jsonl", json.dumps(receipt) + "\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", changed_path, "--format", "json"]) == 0

    state = {item["command"]: item for item in json.loads(capsys.readouterr().out)["answer"]["proof_receipt_reconciliation"]["commands"]}[
        "make test-workspace"
    ]
    assert state["evidence_state"] == f"subject-{expected_status}"
    assert state["minimum_rerun_command"] == "make test-workspace"


def test_reconciliation_selects_reusable_history_before_newer_stale_subject(tmp_path: Path) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    source = tmp_path / "src/app.py"
    _write(source, "reusable\n")
    older = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make test",
        "result": "passed",
        "recorded_at": "2026-07-09T00:00:00+00:00",
        "changed_paths": ["src/app.py"],
    }
    older["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=older["changed_paths"], command="make test")
    _write(source, "stale\n")
    newer = {**older, "recorded_at": "2026-07-10T00:00:00+00:00"}
    newer["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=newer["changed_paths"], command="make test")
    _write(source, "reusable\n")
    receipt_dir = tmp_path / ".agentic-workspace" / "local" / "proof-receipts"
    _write(receipt_dir / "history.jsonl", "\n".join(json.dumps(item) for item in (older, newer)) + "\n")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path, required_commands=["make test"], changed_paths=["src/app.py"]
    )

    assert reconciliation["status"] == "accepted"
    assert reconciliation["commands"][0]["receipt"]["recorded_at"] == older["recorded_at"]


def test_proof_requirement_tiers_keep_environmental_probes_non_blocking() -> None:
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload, _proof_requirement_tiers_payload

    selected_commands = [
        {"command": "make test-workspace", "lane": "workspace_cli", "intent_type": "behavior-test"},
        {"command": "docker compose run conformance", "lane": "release_conformance", "intent_type": "environment-check"},
    ]
    required_commands = ["make test-workspace", "docker compose run conformance"]

    tiers = _proof_requirement_tiers_payload(
        selected_commands=selected_commands,
        required_commands=required_commands,
        optional_commands=["agentic-workspace summary --format json"],
        manual_proof_obligations=[],
        unavailable_commands=[],
        host_policy_blocked_commands=[],
    )
    assert tiers["counts"]["selected_required"] == 1
    assert tiers["counts"]["optional_environmental"] == 1
    assert tiers["categories"]["optional_environmental"][0]["blocking"] is False

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=None,
        required_commands=required_commands,
        changed_paths=["src/app.py"],
        selected_commands=selected_commands,
    )
    assert reconciliation["required_command_count"] == 1
    assert reconciliation["non_blocking_selected_count"] == 1
    assert [item["command"] for item in reconciliation["commands"]] == ["make test-workspace"]


def test_proof_changed_marks_receipt_stale_for_changed_path_mismatch(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--record-receipt",
                "--receipt-command",
                "make test-workspace",
                "--receipt-result",
                "passed",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    states = {item["command"]: item for item in answer["proof_receipt_reconciliation"]["commands"]}
    assert states["make test-workspace"]["evidence_state"] == "subject-unverifiable"
    assert states["make test-workspace"]["subject_freshness"]["reasons"] == ["incomplete-subject-identity"]


def test_proof_changed_reports_dependency_scoped_staleness_and_minimum_rerun(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    source = tmp_path / "src/agentic_workspace/workspace_runtime_proof.py"
    _write(source, "before\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--record-receipt",
                "--receipt-command",
                "make test-workspace",
                "--receipt-result",
                "passed",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    _write(source, "after\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    states = {item["command"]: item for item in json.loads(capsys.readouterr().out)["answer"]["proof_receipt_reconciliation"]["commands"]}
    state = states["make test-workspace"]
    assert state["evidence_state"] == "subject-stale"
    assert state["subject_freshness"]["reasons"] == ["dependency-input-changed"]
    assert state["minimum_rerun_command"] == "make test-workspace"


def test_proof_changed_selector_routes_installed_docs_to_docs_review(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/docs/agent-installation.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["selected_lanes"][0]["proof_kind"] == "diff-review"
    assert ".agentic-workspace/docs" in answer["required_commands"][0]


def test_proof_changed_selector_reduces_package_docs_prefix_to_review(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "packages/planning/docs/usage.md", "--format", "json"]) == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["routing_reductions"] == [
        {
            "path": "packages/planning/docs/usage.md",
            "from_lane": "planning_package",
            "to_lane": "repo_docs_review",
            "reason": (
                "Markdown-only package documentation edits use review proof unless behavior, generated payload, install contracts, "
                "or implementation semantics also changed."
            ),
        }
    ]


def test_proof_changed_selector_does_not_escalate_review_only_cross_lane_changes(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/README.md",
                "src/agentic_workspace/contracts/proof_selection_rules.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review", "contract_tooling"]
    assert {lane["proof_kind"] for lane in answer["selected_lanes"]} == {"diff-review", "surface-check"}
    assert not answer["escalate_when"] or not answer["escalate_when"][0].startswith("changed paths span multiple validation lanes")


def test_proof_changed_selector_includes_schema_reference_docs_for_workspace_schema(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/schemas/operation_primitives.schema.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "contract_tooling" in lane_ids
    assert "schema_reference_docs" in lane_ids
    assert "make schema-reference-docs" in answer["required_commands"]
    schema_lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "schema_reference_docs")
    assert schema_lane["matched_paths"] == ["src/agentic_workspace/contracts/schemas/operation_primitives.schema.json"]
    assert "generated docs/reference" in schema_lane["when"]
    options = {option["id"]: option for option in answer["completion_options"]}
    assert tuple(options) == (
        "run-proof",
        "claim-slice-complete",
        "claim-work-complete",
        "keep-parent-open",
        "close-parent-lane",
        "route-residue",
        "request-review",
        "stop-with-status",
    )
    assert options["run-proof"]["allowed"] is True
    assert options["claim-slice-complete"]["allowed"] is False
    assert "proof selection is not proof execution" in options["claim-slice-complete"]["why"]
    assert options["claim-work-complete"]["allowed"] is False
    assert options["close-parent-lane"]["allowed"] is False
    assert options["stop-with-status"]["allowed"] is True


def test_proof_changed_surfaces_compact_intent_proof_prompt(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)
    intent_proof = answer["intent_proof"]
    assert intent_proof["status"] == "needs-agent-judgment"
    assert intent_proof["regression_only_risk"] == "possible"
    assert intent_proof["suggested_dimensions"]
    assert "question" in intent_proof
    assert "proof strength" not in json.dumps(answer["required_commands"]).lower()


def test_proof_changed_verbose_surfaces_proof_confidence(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    proof_confidence = answer["proof_confidence"]
    assert proof_confidence["confidence"] == "needs-review"
    assert proof_confidence["claim_boundary"] == "slice"
    assert proof_confidence["proven_dimensions"] == []
    assert proof_confidence["unproven_dimensions"]
    assert "Selected proof" in proof_confidence["residual_risk"]
    proof_adequacy = answer["proof_adequacy"]
    assert proof_adequacy["protocol"] == "Proof Adequacy"
    assert proof_adequacy["proof_surface_role"] == "proof selects evidence for the claim; it does not close work by itself"
    assert proof_adequacy["implement_surface_role"].startswith("implement --changed carries changed-path work context")
    assert proof_adequacy["required_evidence"]["commands"] == answer["required_commands"]
    assert proof_adequacy["confidence_evidence"]["commands"] == answer["optional_commands"]
    assert "completion permission without closeout" in proof_adequacy["claim_boundary"]["does_not_authorize"]
    assert "semantic intent satisfaction" in proof_adequacy["claim_boundary"]["does_not_authorize"]
    assert "parent issue, lane, or epic closure" in proof_adequacy["claim_boundary"]["does_not_authorize"]
    assert proof_adequacy["proof_confidence"]["claim_boundary"] == "slice"


def test_proof_changed_selector_includes_planning_schema_reference_wrapper(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/contracts/schemas/planning-execplan.schema.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "planning_package" in lane_ids
    assert "planning_schema_reference_docs" in lane_ids
    assert "make check-planning" in answer["required_commands"]


def test_proof_changed_selector_includes_planning_source_typecheck_ci_parity(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "planning_package" in lane_ids
    assert "planning_source_typecheck_ci_parity" in lane_ids
    assert "make typecheck-planning" in answer["required_commands"]
    obligations = answer["proof_obligations"]
    assert obligations["required_proof"]["commands"] == answer["required_commands"]
    assert obligations["required_proof"]["status"] == "required"
    authority = {item["command"]: item for item in obligations["required_proof"]["command_authority"]}
    assert authority["make typecheck-planning"]["lane"] == "planning_source_typecheck_ci_parity"
    assert authority["make typecheck-planning"]["authority_source"]
    assert "agent still owns proof sufficiency" in authority["make typecheck-planning"]["rule"]
    assert obligations["recommended_confidence_checks"]["commands"] == answer["optional_commands"]
    assert obligations["recommended_confidence_checks"]["commands"] != answer["required_commands"]
    assert "do not replace or relax required proof" in obligations["recommended_confidence_checks"]["rule"]
    assert "Completion claims remain blocked" in obligations["completion_claim_rule"]
    assert answer["proof_adequacy"]["claim_boundary"]["completion_rule"] == obligations["completion_claim_rule"]
    assert answer["proof_adequacy"]["selected_lane_ids"][0] == "planning_package"
    assert obligations["compatibility"]["required_commands"] == "unchanged hard-gate field for existing callers"
    typecheck_lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "planning_source_typecheck_ci_parity")
    assert typecheck_lane["matched_paths"] == ["packages/planning/src/repo_planning_bootstrap/installer.py"]
    typecheck_step = next(step for step in answer["validation_plan"]["required"] if step["command"] == "make typecheck-planning")
    assert typecheck_step["lane_id"] == "planning_source_typecheck_ci_parity"
    typecheck_command = next(command for command in answer["selected_commands"] if command["command"] == "make typecheck-planning")
    assert typecheck_command["intent_type"] == "static-check"
    explanations = answer["proof_command_explanations"]
    typecheck_explanation = next(item for item in explanations["required"] if item["command"] == "make typecheck-planning")
    assert typecheck_explanation["blocking"] is True
    assert "changed-surface-risk" in typecheck_explanation["reason_classes"]
    assert "conservative-fallback" in typecheck_explanation["reason_classes"]
    assert all(item["blocking"] is False for item in explanations["optional_confidence"])
    assert explanations["blocking_rule"].startswith("Only required commands")


def test_proof_changed_selector_includes_workspace_runtime_typecheck_ci_parity(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "domain:proof_runtime" in lane_ids
    assert "workspace_runtime_typecheck_ci_parity" in lane_ids
    assert "make typecheck" in answer["required_commands"]
    typecheck_lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "workspace_runtime_typecheck_ci_parity")
    assert typecheck_lane["matched_paths"] == ["src/agentic_workspace/workspace_runtime_proof.py"]
    assert typecheck_lane["route_authority"]["fallback_status"] == "seed-fallback"
    typecheck_command = next(command for command in answer["selected_commands"] if command["command"] == "make typecheck")
    assert typecheck_command["lane"] == "workspace_runtime_typecheck_ci_parity"
    assert typecheck_command["fallback_status"] == "seed-fallback"
    authority = {item["command"]: item for item in answer["proof_obligations"]["required_proof"]["command_authority"]}
    assert authority["make typecheck"]["route_authority"] == "package-seed-or-default-route"
    assert answer["proof_route_maintenance"]["fallback_selected_count"] >= 1
    assert answer["proof_route_maintenance"]["ci_gap_candidate_count"] >= 1
    maintenance = answer["proof_route_maintenance"]
    assert maintenance["route_hints_surface_contract"]["surface"] == ".agentic-workspace/proof-route-hints.json"
    assert maintenance["route_hints_surface_contract"]["surface_status"] == "absent"
    reasons = {item["reason"] for item in answer["proof_route_maintenance"]["suggested_updates"]}
    assert "CI-learned proof gap should be captured as repo route authority" in reasons
    route_hint_suggestions = [
        item for item in maintenance["suggested_updates"] if item.get("target_surface") == ".agentic-workspace/proof-route-hints.json"
    ]
    assert route_hint_suggestions
    assert all(item["target_surface_status"] == "absent" for item in route_hint_suggestions)
    assert all(item["target_surface_contract"]["owner"] == "repo" for item in route_hint_suggestions)


def test_proof_changed_learned_route_table_can_override_package_default_authority(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "typecheck:\n\tpython -m compileall src\n")
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "proof-route-hints.json",
        json.dumps(
            {
                "kind": "agentic-workspace/proof-route-hints/v1",
                "schema_version": "proof-route-hints/v1",
                "hints": [
                    {
                        "id": "workspace-runtime:typecheck",
                        "state": "confirmed",
                        "intent_type": "static-check",
                        "candidate_command": "make typecheck",
                        "source": "memory",
                        "source_path": ".agentic-workspace/proof-route-hints.json",
                        "confidence": "high",
                        "requires_live_confirmation": False,
                        "scope": "src/agentic_workspace",
                        "owner": "Memory",
                        "provenance": "CI failed on workspace runtime type errors; route confirmed by prior closeout.",
                        "learned_at": "2026-06-29",
                    }
                ],
            }
        ),
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "workspace_runtime_typecheck_ci_parity" in lane_ids
    assert "learned_route:workspace-runtime:typecheck" in lane_ids
    assert answer["required_commands"].count("make typecheck") == 1
    selected_typecheck = [command for command in answer["selected_commands"] if command["command"] == "make typecheck"]
    selected_authorities = {command["route_authority"] for command in selected_typecheck}
    assert "package-seed-or-default-route" in selected_authorities
    assert "repo-learned-route-table" in selected_authorities
    obligations = {item["command"]: item for item in answer["proof_obligations"]["required_proof"]["command_authority"]}
    assert obligations["make typecheck"]["route_authority"] == "repo-learned-route-table"
    precedence = answer["proof_route_precedence"]
    assert precedence["status"] == "competing-routes"
    assert precedence["cases"][0]["winner"]["route_source"] == "repo-learned-proof-route"
    overridden_authorities = {item["route_authority"] for item in precedence["cases"][0]["overridden"]}
    assert "package-seed-or-default-route" in overridden_authorities


def test_proof_changed_selector_keeps_docs_only_work_off_workspace_runtime_typecheck(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "README.md", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "make typecheck" not in answer["required_commands"]
    assert "workspace_runtime_typecheck_ci_parity" not in [lane["id"] for lane in answer["selected_lanes"]]


def test_proof_changed_selector_flags_high_impact_skill_behavior_evidence(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/skills/planning-closeout-trust/SKILL.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    review = answer["skill_behavior_impact_review"]
    assert review["status"] == "behavior-evidence-required"
    assert review["high_impact_paths"] == ["packages/planning/skills/planning-closeout-trust/SKILL.md"]
    assert "What behavior is this skill meant to steer?" in review["required_answers"]
    assert "Tests passed, so completion is claimable." in json.dumps(answer["proof_strategy"]["anti_rationalization_gates"])


def test_proof_tiny_readme_profile_keeps_docs_only_validation_light(capsys) -> None:
    assert cli.main(["proof", "--changed", "README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload)
    docs_diff = "git diff -- README.md docs .agentic-workspace/docs packages/planning/README.md packages/memory/README.md"
    assert payload["kind"] == "proof-next-decision/v1"
    assert payload["next"]["command"] == docs_diff
    assert payload["required_commands"] == [docs_diff]
    assert "uv run pytest tests -q" not in encoded
    assert len(encoded) < 3200


def test_proof_changed_selector_flags_direct_cli_edits(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "workspace_cli",
        "cli_authority",
        "generated_command_packages",
        "subsystem:workspace-cli-runtime",
        "assurance-requirement:subsystem:workspace-cli-runtime",
        "verification:closeout_intent_satisfaction",
        "verification:generated_adapter_conformance",
        "verification:requirement_grounding_delegation",
    ]
    authority_review = answer["cli_authority_review"]
    assert authority_review["status"] == "blocked-direct-edit-route-to-source"
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
    root_cli = authority_review["classifications"][0]
    assert root_cli["role"] == "projection"
    assert root_cli["direct_edit_allowed"] is False
    assert root_cli["source_contract"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert root_cli["regeneration_path"] == "uv run python scripts/generate/generate_command_packages.py"
    assert authority_review["authority_query"] == "agentic-workspace defaults --section root_cli_authority --format json"
    review = payload["answer"]["direct_cli_edit_review"]
    assert review["status"] == "review-needed"
    assert review["changed_paths"] == ["generated/workspace/python/cli.py"]
    assert "normal interface authoring belongs in command contracts" in review["rule"]
    assert "runtime primitive implementation and live workspace inspection" in review["allowed_direct_cli_work"]
    assert "route interface or generated-surface changes back" in review["recovery_signal"]
    assert answer["subsystem_ownership"]["matched_subsystems"][0]["id"] == "workspace-cli-runtime"


def test_proof_changed_selector_broadens_contract_plus_cli_changes(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/proof_selection_rules.json",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "contract_tooling",
        "workspace_cli",
        "cli_authority",
        "generated_command_packages",
        "subsystem:workspace-cli-runtime",
        "assurance-requirement:subsystem:workspace-cli-runtime",
        "verification:closeout_intent_satisfaction",
        "verification:generated_adapter_conformance",
        "verification:requirement_grounding_delegation",
    ]
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
    assert "make test-workspace" not in answer["required_commands"]
    assert "make test-workspace" in answer["optional_commands"]
    workspace_lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "workspace_cli")
    assert workspace_lane["focused_route_reduction"]["status"] == "broad-proof-withheld-for-explicit-escalation"
    assert answer["proof_narrowness"]["broad_suite_boundary"]["status"] == "explicit-escalation-required"
    assert answer["proof_route_escalation_gate"]["status"] == "blocked-explicit-escalation-required"


def test_proof_changed_selector_escalates_for_cross_lane_changes(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "planning_package",
        "workspace_cli",
        "cli_authority",
        "generated_command_packages",
        "subsystem:workspace-cli-runtime",
        "planning_source_typecheck_ci_parity",
        "assurance-requirement:subsystem:workspace-cli-runtime",
        "verification:closeout_intent_satisfaction",
        "verification:generated_adapter_conformance",
        "verification:requirement_grounding_delegation",
    ]
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
    assert "make typecheck-planning" in answer["required_commands"]
    package_step = answer["validation_plan"]["required"][0]
    assert package_step["command"] == "make test-planning"
    assert package_step["cwd"] == "."
    assert package_step["run"] == "make test-planning"
    assert package_step["lane_id"] == "planning_package"


def test_proof_changed_selector_accepts_existing_durable_surface_update(tmp_path: Path, capsys) -> None:
    contract_path = tmp_path / "src" / "agentic_workspace" / "contracts" / "report_contract.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text("{}\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/report_contract.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["answer"]["surface_value_review"]
    assert review["kind"] == "surface-value-review/v1"
    assert review["status"] == "accepted"
    assert review["accepted_count"] == 1
    assert review["flagged_count"] == 0
    assert review["reviewed_paths"][0]["surface_class"] == "workspace_contract_surface"
    assert review["reviewed_paths"][0]["result"] == "accepted"
    assert review["review_gate"]["ordinary_path"] == "agentic-workspace proof --target ./repo --changed <paths> --format json"


def test_proof_changed_selector_flags_additive_only_durable_surface(tmp_path: Path, capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/new-first-line-concept.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["answer"]["surface_value_review"]
    assert review["status"] == "attention-needed"
    assert review["accepted_count"] == 0
    assert review["flagged_count"] == 1
    assert review["reviewed_paths"][0]["result"] == "flagged"
    assert review["reviewed_paths"][0]["disposition"] == "additive-only durable surface candidate"
    assert "what repeated cost does this remove?" in review["reviewed_paths"][0]["required_answers"]


def test_proof_changed_selector_accepts_deleted_durable_surface(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=tmp_path, check=True)
    contract_path = tmp_path / "src" / "agentic_workspace" / "contracts" / "old_surface.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True)
    contract_path.unlink()
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/old_surface.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["answer"]["surface_value_review"]
    assert review["status"] == "accepted"
    assert review["accepted_count"] == 1
    assert review["flagged_count"] == 0
    assert review["reviewed_paths"][0]["result"] == "accepted"
    assert review["reviewed_paths"][0]["disposition"] == "removed durable surface"


def _write_proof_architecture_principles(target_root: Path) -> None:
    _write(
        target_root / ".agentic-workspace" / "system-intent" / "intent.toml",
        """
kind = "agentic-workspace/system-intent/v1"
summary = "Portable host-neutral operating intent."
governing_intents = []
anti_intents = []
decision_tests = []
confidence = "high"
needs_review = false

[[architecture_principles]]
id = "host-agnostic-agent-judgment"
title = "Preserve host-agnostic agent judgment"
authority = "repo-system-intent"
owner = "workspace-runtime"
summary = "AW provides infrastructure for agent judgment instead of package-owned host assumptions."
path_globs = ["src/agentic_workspace/workspace_runtime*.py"]
guardrail_refs = ["docs/maintainer/non-enum-keyword-routing-audit.json"]
derived_applications = ["non-enum-keyword-routing"]
proof_expectation = "Closeout must state whether the principle was preserved or re-scoped."
review_aids = ["Confirm proof selection did not infer from prose keywords."]
claim_boundary = "architecture-principle-preservation"
""",
    )


def test_proof_changed_selects_host_declared_domain_proof_lane(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.domain_proof_lanes.access_control]
purpose = "Access-control changes need domain proof and review evidence."
applies_to_paths = ["services/auth/**"]
commands = ["python -c \\"print('access proof')\\""]
manual_evidence = ["host:access_matrix"]
review_aids = ["Inspect role-to-permission impact."]
evidence_concepts = ["host:access_matrix"]
authority_refs = ["SECURITY.md#access-control"]
claim_boundary = "access-control-proof-required-before-full-claim"
owner = "security"
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "verification" / "manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[evidence_concepts."host:access_matrix"]
title = "Access Matrix"
meaning = "Host-owned role-to-permission review matrix."
owner = "security"
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    domain = next(lane for lane in packet["selected_lanes"] if lane["id"] == "domain:access_control")
    assert domain["domain_lane"]["source"] == ".agentic-workspace/config.toml [assurance.domain_proof_lanes]"
    assert domain["manual_evidence"] == ["host:access_matrix"]
    assert domain["evidence_concept_usage"]["used"][0]["id"] == "host:access_matrix"
    assert domain["evidence_concept_usage"]["degraded"] == []
    assert domain["claim_boundary"] == "access-control-proof-required-before-full-claim"
    assert domain["route_authority"]["authority"] == "repo-owned-domain-proof-lane"
    assert packet["safe_claim_now"]["state"] == "manual-review-required"


def test_domain_proof_lane_undeclared_host_concepts_degrade(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.domain_proof_lanes.access_control]
purpose = "Access-control changes need domain proof and review evidence."
applies_to_paths = ["services/auth/**"]
manual_evidence = ["host:access_matrix"]
evidence_concepts = ["host:access_matrix"]
owner = "security"
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    domain = next(lane for lane in packet["selected_lanes"] if lane["id"] == "domain:access_control")
    usage = domain["evidence_concept_usage"]
    assert usage["used"] == []
    assert usage["degraded"][0]["id"] == "host:access_matrix"
    assert usage["degraded"][0]["state"] == "undeclared-host-concept"
    assert "domain proof lane contains undeclared or unclassified evidence concepts" in packet["missing_or_unresolved"]["blockers"]
    assert packet["missing_or_unresolved"]["degraded_evidence_concepts"][0]["lane"] == "domain:access_control"


def test_domain_proof_lanes_compose_and_skip_non_matching_changes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.domain_proof_lanes.access_control]
purpose = "Access-control changes need access proof."
applies_to_paths = ["services/auth/**"]
commands = ["python -c \\"print('access proof')\\""]

[assurance.domain_proof_lanes.audit_events]
purpose = "Access-control changes need audit-event proof."
applies_to_paths = ["services/auth/**"]
commands = ["python -c \\"print('audit proof')\\""]
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")
    _write(tmp_path / "docs" / "readme.md", "# Docs\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    lane_ids = [lane["id"] for lane in packet["selected_lanes"]]
    assert "domain:access_control" in lane_ids
    assert "domain:audit_events" in lane_ids
    assert packet["selected_lane_count"] >= 2

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/readme.md",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    assert all(not lane["id"].startswith("domain:") for lane in packet["selected_lanes"])


def test_proof_route_strategy_decision_selects_structured_broad_escalation_for_two_domain_owners(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / "Makefile",
        (tmp_path / "Makefile").read_text(encoding="utf-8")
        + """
test-workspace-cli:
\tpython -c "print('workspace cli')"

test-workspace-proof:
\tpython -c "print('workspace proof')"

test-workspace-session-review:
\tpython -c "print('workspace session review')"

test-workspace-contracts:
\tpython -c "print('workspace contracts')"

test-workspace-generated-release:
\tpython -c "print('workspace generated release')"

test-workspace-integration:
\tpython -c "print('workspace integration')"

lint-workspace:
\tpython -c "print('workspace lint')"
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        (tmp_path / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.runtime_contract]
purpose = "Runtime contract behavior."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py"]
commands = ["python -c \\"print('runtime proof')\\""]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["cross-owner"]
claim_boundary = "runtime-contract-proof"
owner = "workspace-cli-runtime"

[assurance.domain_proof_lanes.generated_command_packages]
purpose = "Generated command package behavior."
applies_to_paths = ["generated/workspace/python/**"]
commands = ["python -c \\"print('generated proof')\\""]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["cross-owner"]
claim_boundary = "generated-adapter-proof"
owner = "generated-adapters"

[assurance.domain_proof_lanes.workspace_broad_suite]
purpose = "Explicit broad workspace validation route."
applies_to_task_markers = ["full workspace validation"]
commands = [
  "make test-workspace-cli",
  "make test-workspace-proof",
  "make test-workspace-session-review",
  "make test-workspace-contracts",
  "make test-workspace-generated-release",
  "make test-workspace-integration",
  "make lint-workspace",
]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["cross-owner", "explicit-request"]
claim_boundary = "explicit-broad-escalation-required"
owner = "workspace-cli-runtime"
""",
        encoding="utf-8",
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "generated" / "workspace" / "python" / "cli.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "generated/workspace/python/cli.py",
                "--select",
                "proof_route_strategy_decision,required_commands,selected_lanes",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    decision = values["proof_route_strategy_decision"]
    assert decision["outcome"] == "broad-escalated"
    assert decision["reason_code"] == "cross-owner"
    assert decision["broad_escalation"]["distinct_owners"] == ["generated-adapters", "workspace-cli-runtime"]
    expected_broad_commands = [
        "make test-workspace-cli",
        "make test-workspace-proof",
        "make test-workspace-session-review",
        "make test-workspace-contracts",
        "make test-workspace-generated-release",
        "make test-workspace-integration",
        "make lint-workspace",
    ]
    for command in expected_broad_commands:
        assert command in values["required_commands"]
    assert "make test-workspace" not in values["required_commands"]
    assert "domain:workspace_broad_suite" in [lane["id"] for lane in values["selected_lanes"]]


def test_proof_route_strategy_decision_ignores_untyped_escalation_prose(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        (tmp_path / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.runtime_contract]
purpose = "Runtime contract behavior."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py"]
commands = ["python -c \\"print('runtime proof')\\""]
proof_profiles = ["workspace_behavior"]
escalation = ["cross-owner generated/runtime changes require broad workspace validation"]
claim_boundary = "runtime-contract-proof"
owner = "workspace-cli-runtime"

[assurance.domain_proof_lanes.generated_command_packages]
purpose = "Generated command package behavior."
applies_to_paths = ["generated/workspace/python/**"]
commands = ["python -c \\"print('generated proof')\\""]
proof_profiles = ["workspace_behavior"]
escalation = ["cross-owner generated/runtime changes require broad workspace validation"]
claim_boundary = "generated-adapter-proof"
owner = "generated-adapters"

[assurance.domain_proof_lanes.workspace_broad_suite]
purpose = "Explicit broad workspace validation route."
applies_to_task_markers = ["full workspace validation"]
commands = ["make test-workspace"]
proof_profiles = ["workspace_behavior"]
claim_boundary = "explicit-broad-escalation-required"
owner = "workspace-cli-runtime"
""",
        encoding="utf-8",
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "generated" / "workspace" / "python" / "cli.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "generated/workspace/python/cli.py",
                "--select",
                "proof_route_strategy_decision,required_commands,selected_lanes",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assert values["proof_route_strategy_decision"]["outcome"] == "broad-escalation-required"
    assert values["proof_route_strategy_decision"]["broad_escalation"]["status"] == "missing"
    assert "make test-workspace" not in values["required_commands"]
    assert "domain:workspace_broad_suite" not in [lane["id"] for lane in values["selected_lanes"]]


def test_proof_route_strategy_decision_requires_matching_high_risk_requirement_ref(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        (tmp_path / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
        + """

[assurance.requirements.security_delta]
level = "high"
applies_to_paths = ["services/auth/**"]
authority_refs = ["docs/security.md"]
required_evidence = ["security review"]
force = "required-before-closeout"

[assurance.domain_proof_lanes.auth_runtime]
purpose = "Auth runtime behavior."
applies_to_paths = ["services/auth/**"]
commands = ["python -c \\"print('auth proof')\\""]
proof_profiles = ["workspace_behavior"]
assurance_requirement_refs = ["security_delta"]
escalation_conditions = ["high-risk-requirement"]
claim_boundary = "auth-runtime-proof"
owner = "auth"
route_role = "behavior"

[assurance.domain_proof_lanes.workspace_broad_suite]
purpose = "Explicit broad workspace validation route."
applies_to_task_markers = ["full workspace validation"]
commands = ["make test-workspace"]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["high-risk-requirement"]
claim_boundary = "explicit-broad-escalation-required"
owner = "workspace-cli-runtime"
route_role = "broad"
""",
        encoding="utf-8",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_route_strategy_decision,required_commands,selected_lanes",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    decision = values["proof_route_strategy_decision"]
    assert decision["outcome"] == "broad-escalated"
    assert decision["reason_code"] == "high-risk-requirement"
    assert decision["broad_escalation"]["matched_assurance_requirement_refs"] == ["security_delta"]
    assert "make test-workspace" in values["required_commands"]


def test_proof_route_strategy_decision_consumes_applicable_memory_validation_friction(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.generated_command_packages]
purpose = "Focused generated-component behavior."
applies_to_paths = ["src/generated_component.py"]
commands = ["python -c \\"print('generated focused proof')\\""]
claim_boundary = "generated-adapter-proof"
owner = "generated-adapters"
""",
        encoding="utf-8",
    )
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml",
        """
version = 1

[notes.".agentic-workspace/memory/repo/current/proof-route-friction.md"]
memory_role = "improvement_signal"
kind = "validation_friction"
lifecycle_state = "active"
applicable_live = true
applicable_to_current_route = true
recurrence = "repeated"
occurrence_count = 2
route_identity = "proof-route-friction:generated"
summary = "Repeated validation proof friction on generated command package checks."
routes_from = ["src/generated_component.py"]
stale_when = ["src/generated_component.py"]
preferred_remediation = "validation"
promotion_target = "proof-route-maintenance"
promotion_trigger = "Route generated-command package changes through focused proof before broad suites."
improvement_note = "Do not repeat broad/generated validation until the proof route is refined or this signal is retired."
evidence = ["session-log:slow-command:generated"]
""",
    )
    _write(tmp_path / "src" / "generated_component.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/generated_component.py",
                "--select",
                "proof_route_strategy_decision,proof_route_escalation_gate,proof_route_strategy_preservation,next",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    decision = values["proof_route_strategy_decision"]
    assert decision["outcome"] == "focused"
    assert decision["reason_code"] == "focused-route-sufficient"
    assert decision["claim_effect"] == "focused-proof-required"
    assert decision["applicable_friction_findings"][0]["note_path"].endswith("proof-route-friction.md")
    assert decision["applicable_friction_findings"][0]["route_identity"] == "proof-route-friction:generated"
    assert decision["applicable_friction_findings"][0]["recurrence"] == "repeated"
    assert values["proof_route_escalation_gate"]["friction_inputs"]["applicable_live_findings"]
    preservation = values["proof_route_strategy_preservation"]
    assert preservation["status"] == "selected"
    assert preservation["consumers"]["proof"]["decision_id"] == preservation["decision_id"]
    assert preservation["consumers"]["handoff"]["claim_effect"] == "focused-proof-required"
    assert values.get("manual_verification") is None
    assert values["next"]["action"] == "run-validation-command"


def test_proof_route_strategy_decision_ignores_non_live_memory_validation_friction(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    manifest_path = tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_template = """
version = 1

[notes.".agentic-workspace/memory/repo/current/proof-route-friction.md"]
memory_role = "improvement_signal"
lifecycle_state = "{lifecycle_state}"
kind = "validation_friction"
applicable_live = true
applicable_to_current_route = true
recurrence = "repeated"
occurrence_count = 2
summary = "Old validation proof friction on generated command package checks."
routes_from = ["generated/workspace/python/**"]
preferred_remediation = "validation"
promotion_target = "proof-route-maintenance"
promotion_trigger = "Retired after focused proof route was added."
improvement_note = "This signal is intentionally quiet."
"""
    _write(tmp_path / "generated" / "workspace" / "python" / "cli.py", "VALUE = 1\n")

    for lifecycle_state in ("stale", "mitigated", "superseded"):
        manifest_path.write_text(manifest_template.format(lifecycle_state=lifecycle_state), encoding="utf-8")
        assert (
            cli.main(
                [
                    "proof",
                    "--target",
                    str(tmp_path),
                    "--changed",
                    "generated/workspace/python/cli.py",
                    "--select",
                    "proof_route_strategy_decision",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        decision = json.loads(capsys.readouterr().out)["values"]["proof_route_strategy_decision"]
        assert decision["reason_code"] != "applicable-validation-friction"
        assert decision["applicable_friction_findings"] == []


def test_proof_route_strategy_decision_requires_typed_live_repeated_friction(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    manifest_path = tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    _write(tmp_path / "generated" / "workspace" / "python" / "cli.py", "VALUE = 1\n")
    cases = [
        'summary = "Repeated validation proof friction."',
        'kind = "validation_friction"\napplicable_live = true\napplicable_to_current_route = true\nrecurrence = "first_seen"',
        'kind = "validation_friction"\napplicable_live = false\napplicable_to_current_route = true\nrecurrence = "repeated"\noccurrence_count = 2',
    ]
    for extra_fields in cases:
        manifest_path.write_text(
            f"""
version = 1

[notes.".agentic-workspace/memory/repo/current/proof-route-friction.md"]
memory_role = "improvement_signal"
lifecycle_state = "active"
routes_from = ["generated/workspace/python/**"]
{extra_fields}
""",
            encoding="utf-8",
        )
        assert (
            cli.main(
                [
                    "proof",
                    "--target",
                    str(tmp_path),
                    "--changed",
                    "generated/workspace/python/cli.py",
                    "--select",
                    "proof_route_strategy_decision,proof_route_escalation_gate",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        values = json.loads(capsys.readouterr().out)["values"]
        assert values["proof_route_strategy_decision"]["applicable_friction_findings"] == []
        assert values["proof_route_escalation_gate"]["friction_inputs"]["applicable_live_findings"] == []


def test_domain_proof_route_inventory_reports_profile_and_command_gaps(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.proof_profiles.workspace_behavior]
required_commands = []

[assurance.proof_profiles.uncovered_profile]
required_commands = []

[assurance.domain_proof_lanes.runtime_contract]
purpose = "Runtime contract behavior."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py"]
commands = ["uv run pytest tests/missing_runtime_contract.py -q"]
proof_profiles = ["workspace_behavior"]
""",
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--select",
                "domain_proof_route_inventory_audit",
                "--format",
                "json",
            ]
        )
        == 0
    )

    audit = json.loads(capsys.readouterr().out)["values"]["domain_proof_route_inventory_audit"]
    assert audit["status"] == "attention"
    assert audit["missing_profile_coverage"] == [
        {
            "proof_profile": "uncovered_profile",
            "reason": "configured proof profile has no domain proof lane coverage",
            "refinement_owner": "repo proof-route authority",
        }
    ]
    assert any(item.get("missing_path") == "tests/missing_runtime_contract.py" for item in audit["non_executable_commands"])


def test_domain_proof_route_inventory_ignores_disjoint_shared_prefix_globs(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.domain_proof_lanes.package_tests]
purpose = "Package tests."
applies_to_paths = ["packages/**/tests/**"]
commands = ["python -c \\"print('tests')\\""]
claim_boundary = "package-test-proof"
owner = "verification"
route_role = "evidence"
precedence = "80"
allowed_composition = ["behavior"]

[assurance.domain_proof_lanes.memory_source]
purpose = "Memory source."
applies_to_paths = ["packages/memory/src/**"]
commands = ["python -c \\"print('memory')\\""]
claim_boundary = "memory-source-proof"
owner = "memory"
route_role = "behavior"
precedence = "50"
allowed_composition = ["evidence"]
""",
    )
    _write(tmp_path / "packages" / "memory" / "src" / "repo_memory_bootstrap" / "core.py", "VALUE = 1\n")
    _write(tmp_path / "packages" / "memory" / "tests" / "test_core.py", "def test_core(): pass\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/memory/src/repo_memory_bootstrap/core.py",
                "--select",
                "domain_proof_route_inventory_audit",
                "--format",
                "json",
            ]
        )
        == 0
    )

    audit = json.loads(capsys.readouterr().out)["values"]["domain_proof_route_inventory_audit"]
    assert audit["semantic_overlaps"] == []
    assert audit["contradictory_ownership"] == []


def test_route_refinement_removes_broad_commands_when_focused_command_becomes_unavailable(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / "Makefile",
        (tmp_path / "Makefile").read_text(encoding="utf-8") + "\nlint-workspace:\n\tpython -c \"print('workspace lint')\"\n",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        (tmp_path / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.runtime_contract]
purpose = "Runtime contract behavior."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py"]
commands = ["make missing-runtime-proof"]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["cross-owner"]
claim_boundary = "runtime-contract-proof"
owner = "workspace-cli-runtime"
route_role = "behavior"

[assurance.domain_proof_lanes.generated_command_packages]
purpose = "Generated command package behavior."
applies_to_paths = ["generated/workspace/python/**"]
commands = ["python -c \\"print('generated proof')\\""]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["cross-owner"]
claim_boundary = "generated-adapter-proof"
owner = "generated-adapters"
route_role = "behavior"

[assurance.domain_proof_lanes.workspace_broad_suite]
purpose = "Explicit broad workspace validation route."
applies_to_task_markers = ["full workspace validation"]
commands = ["make test-workspace", "make lint-workspace"]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["cross-owner"]
claim_boundary = "explicit-broad-escalation-required"
owner = "workspace-cli-runtime"
route_role = "broad"
""",
        encoding="utf-8",
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "generated" / "workspace" / "python" / "cli.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "generated/workspace/python/cli.py",
                "--select",
                "proof_route_strategy_decision,route_refinement_required,manual_verification,required_commands,selected_commands",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assert values["proof_route_strategy_decision"]["outcome"] == "route-refinement-required"
    assert values["route_refinement_required"]["status"] == "required"
    assert values["manual_verification"]["status"] == "route-refinement-required"
    assert "make test-workspace" not in values["required_commands"]
    assert "make lint-workspace" not in values["required_commands"]
    assert all(command["lane"] != "domain:workspace_broad_suite" for command in values["selected_commands"])


def test_domain_proof_lane_coexists_with_package_default_lane(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.domain_proof_lanes.runtime_contract]
purpose = "Runtime changes need host contract proof."
applies_to_paths = ["src/agentic_workspace/**"]
commands = ["python -c \\"print('runtime contract proof')\\""]
proof_profiles = ["runtime_contract"]
""",
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    lane_ids = [lane["id"] for lane in packet["selected_lanes"]]
    assert "domain:runtime_contract" in lane_ids


def test_local_high_risk_overlay_shapes_proof_decision_with_provenance(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        """
schema_version = 1

[local_overlay.high_risk.source_maps.auth_docs]
applies_to_paths = ["services/auth/**"]
authority_refs = ["SECURITY.md#auth", "docs/adr/auth-boundary.md"]
required_sources = ["docs/risk/auth-risk-register.md"]
manual_evidence = ["host:auth-risk-review"]
review_aids = ["Confirm auth ADR still matches changed code."]
claim_boundary = "auth-source-map-review"
impact = "human-review-only"

[local_overlay.high_risk.validation_profiles.security_sensitive]
category = "security-sensitive"
applies_to_paths = ["services/auth/**"]
required_commands = ["python -c \\"print('security validation')\\""]
manual_checks = ["Review auth threat-model delta."]
claim_boundary = "security-validation-profile"
impact = "blocking"

[local_overlay.high_risk.ci_validation.github_actions]
applies_to_paths = ["services/auth/**"]
validation_state = "ci_unavailable"
local_substitute_commands = ["python -c \\"print('local substitute')\\""]
local_substitute_policy = "human-review-only"
claim_boundary = "local-substitute-is-not-ci"

[local_overlay.high_risk.templates.security_issue]
applies_to_paths = ["services/auth/**"]
host = "github"
kind = "issue"
paths = [".github/ISSUE_TEMPLATE/security.yml"]
headings = ["Risk", "Evidence", "Reviewer"]
state = "missing"
impact = "blocking"

[local_overlay.high_risk.guardrails.synthetic_auth_data]
applies_to_paths = ["services/auth/**"]
sensitive_data = ["production tokens", "customer emails"]
synthetic_fixture_guidance = ["Use example.com addresses.", "Use placeholder credentials."]
impact = "claim-limiting"

[local_overlay.high_risk.unresolved_questions.legal_review]
applies_to_paths = ["services/auth/**"]
category = "human-review-required"
question = "Does this auth change require legal/security review before merge?"
owner = "security"
residue_route = "human-review"
reason = "local high-risk overlay declares auth changes review-sensitive"
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    overlay = packet["local_high_risk_overlay"]
    assert packet["local_overlay"]["status"] == "configured-no-match"
    assert overlay["status"] == "active"
    assert overlay["active_count"] == 6
    source_lane = next(lane for lane in packet["selected_lanes"] if lane["id"] == "local-overlay-source:auth_docs")
    assert source_lane["route_authority"]["authority"] == "local-only-high-risk-profile"
    assert source_lane["local_overlay"]["source_layer"] == "repo-local-override"
    assert "SECURITY.md#auth" in source_lane["commands"] or source_lane["manual_evidence"] == ["host:auth-risk-review"]
    validation_lane = next(lane for lane in packet["selected_lanes"] if lane["id"] == "local-overlay-validation:security_sensitive")
    assert validation_lane["validation_profile"]["category"] == "security-sensitive"
    assert "python -c \"print('security validation')\"" in validation_lane["commands"]
    unresolved = packet["missing_or_unresolved"]
    assert "validation-state:ci_unavailable" in unresolved["local_overlay_blockers"]
    assert "local-substitute-policy:human-review-only" in unresolved["local_overlay_blockers"]
    assert "template-preservation:missing" in unresolved["local_overlay_blockers"]
    assert "guardrail:claim-limiting" in unresolved["local_overlay_blockers"]
    assert "unresolved-question:human-review-required" in unresolved["local_overlay_blockers"]
    assert packet["safe_claim_now"]["state"] == "human-waiver-required"


def test_local_high_risk_overlay_no_match_stays_out_of_tiny_proof(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        """
schema_version = 1

[local_overlay.high_risk.guardrails.auth_data]
applies_to_paths = ["services/auth/**"]
sensitive_data = ["production token"]
impact = "blocking"
""",
    )
    _write(tmp_path / "docs" / "readme.md", "# Docs\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "docs/readme.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload.get("high_risk_overlay") is None


def test_high_assurance_closeout_posture_projects_missing_and_non_applicable_states(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.closeout_postures.critical_access]
purpose = "Critical access changes need explicit closeout evidence."
applies_to_paths = ["services/auth/**"]
required_evidence = ["domain_review_recorded"]
review_owner = "security"
authority_refs = ["SECURITY.md#critical-access"]
claim_boundary = "critical-access-closeout"
certification_limits = ["does not certify production authorization safety"]
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")
    _write(tmp_path / "docs" / "readme.md", "# Docs\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    posture = packet["high_assurance_closeout_posture"]
    assert posture["status"] == "missing-proof"
    assert posture["matched_count"] == 1
    assert posture["matched_postures"][0]["claim_boundary"] == "critical-access-closeout"
    assert posture["missing_evidence"] == ["domain_review_recorded"]
    assert "high-assurance closeout posture evidence is missing" in packet["missing_or_unresolved"]["blockers"]

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/readme.md",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    posture = json.loads(capsys.readouterr().out)["values"]["proof_decision"]["high_assurance_closeout_posture"]
    assert posture["status"] == "not-applicable"
    assert posture["matched_count"] == 0


def test_high_assurance_closeout_posture_projects_waiver_and_uncertainty(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.closeout_postures.access_waiver]
purpose = "Access changes with unresolved policy uncertainty need human waiver."
applies_to_paths = ["services/auth/**"]
uncertainty = "External policy owner must confirm the residual risk."
human_waiver_refs = ["SECURITY.md#waivers"]
certification_limits = ["agent output is not a policy approval"]
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    posture = packet["high_assurance_closeout_posture"]
    assert posture["status"] == "human-waiver-required"
    assert posture["human_waiver_refs"] == ["SECURITY.md#waivers"]
    assert posture["uncertainty"] == ["External policy owner must confirm the residual risk."]
    assert packet["safe_claim_now"]["state"] == "human-waiver-required"


def test_proof_decision_packet_includes_architecture_pressure(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write_proof_architecture_principles(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    assert packet["kind"] == "agentic-workspace/proof-decision-packet/v1"
    assert packet["active_pressure"]["architecture_principle_match_count"] == 1
    assert "matched architecture principle preservation claim is unresolved" in packet["missing_or_unresolved"]["blockers"]
    assert packet["safe_claim_now"]["state"] in {"proof-missing", "manual-review-required"}


def test_verification_distinguishes_host_evidence_concepts(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(tmp_path / ".agentic-workspace" / "config.toml", f'schema_version = 1\n\n[workspace]\ncli_invoke = "{REPO_LOCAL_CLI_INVOKE}"\n')
    _write(
        tmp_path / ".agentic-workspace" / "verification" / "manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[evidence_concepts."host:scenario_matrix"]
title = "Scenario Matrix"
meaning = "Host-owned scenario coverage matrix."
owner = "qa"
claim_effect = "manual-review-required"
render_as = "scenario matrix"

[protocols.access_review]
title = "Access Review"
purpose = "Access changes need declared evidence."
applies_to_paths = ["services/auth/**"]
expected_evidence = ["scenario_coverage", "host:scenario_matrix", "host:missing"]
review_owner = "security"
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "verification",
                "--format",
                "json",
            ]
        )
        == 0
    )

    verification = json.loads(capsys.readouterr().out)["values"]["verification"]
    concepts = verification["evidence_status"][0]["expected_evidence_concepts"]
    assert [item["kind"] for item in concepts["used"]] == ["core", "host-declared"]
    assert concepts["degraded"][0]["state"] == "undeclared-host-concept"
    assert verification["evidence_concepts"]["status"] == "attention"
