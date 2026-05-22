from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def _write_empty_planning_state(target_root: Path) -> None:
    _write(
        target_root / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )


def _implement_context(payload: dict[str, object]) -> dict[str, object]:
    context = payload.get("context")
    return context if isinstance(context, dict) else payload


def test_implement_command_returns_bounded_context_and_boundary_warnings(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/bootstrap/repo_planning_bootstrap/installer.py",
                "generated/workspace/python/cli.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "implementer-context/v1"
    assert payload["inspect_files"] == [
        "packages/planning/bootstrap/repo_planning_bootstrap/installer.py",
        "generated/workspace/python/cli.py",
    ]
    assert payload["required_validation_commands"] == [
        "agentic-workspace defaults --section root_cli_authority --format json",
        "uv run python scripts/check/check_generated_command_packages.py",
        "uv run python scripts/check/check_generated_command_packages.py --python-conformance",
        "uv run python scripts/check/check_generated_command_packages.py --python-docker-conformance --require-docker",
    ]
    unavailable_commands = {item["command"] for item in payload["proof"]["unavailable_commands"]}
    assert {
        "make test-planning",
        "make lint-planning",
        "make test-workspace",
        "make lint-workspace",
    } <= unavailable_commands
    assert payload["proof"]["cli_authority_review"]["classifications"][0]["role"] == "hand-owned-executable"
    assert payload["orientation"]["status"] == "changed-path-context"
    assert "preflight" in payload["orientation"]["preflight_command"]
    assert "lowers continuation and review trust" in payload["orientation"]["trust_note"]
    assert "unstated intent" in payload["inference_limits"]["rule"]
    assert payload["execution_posture"]["kind"] == "agentic-workspace/execution-posture/v1"
    assert payload["execution_posture"]["delegation_control"]["effective_mode"] in {"suggest", "auto"}
    assert payload["execution_posture"]["delegation_control"]["execution_permitted"] is (
        payload["execution_posture"]["delegation_control"]["effective_mode"] == "auto"
    )
    assert payload["delegation_decision"]["status"] == "evaluated"
    assert payload["delegation_decision"] == payload["execution_posture"]["delegation_decision"]
    assert payload["delegation_decision"]["mode"] in {"suggest", "auto"}
    assert payload["acceptance_reconciliation"]["requested_outcomes"] == []
    assert payload["acceptance"]["status"] == "unavailable"
    assert payload["objective_drift"]["status"] == "unavailable"
    assert "safer path" in payload["execution_posture"]["quality_tradeoff"].lower()
    assert "token" in payload["execution_posture"]["token_tradeoff"].lower()
    assert payload["durable_intent"]["kind"] == "agentic-workspace/durable-intent-decision/v1"
    assert payload["durable_intent"]["subsystem_intent"]["surface"] == ".agentic-workspace/system-intent/subsystems.toml"
    assert (
        "whether proof commands were actually executed unless evidence is recorded elsewhere" in payload["inference_limits"]["cannot_infer"]
    )
    assert payload["path_boundaries"][0]["authority"] == "payload"
    assert payload["path_boundaries"][0]["requires_attention"] is True
    assert payload["authority_markers"][0]["safe_to_edit"] is False
    assert payload["next_allowed_action"] == "Resolve boundary warnings before editing."
    assert payload["planning_safety_gate"]["status"] == "attention"
    assert payload["planning_safety_gate"]["decision"] == "agent-work-shape-decision-required"
    assert payload["planning_safety_gate"]["implementation_allowed"] is True
    assert payload["planning_safety_gate"]["work_shape_facts"]["hard_blockers"] == []


def test_implement_tiny_profile_returns_next_decision_without_diagnostics(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "Makefile", "test-workspace:\n\tpytest tests\n\nlint-workspace:\n\truff check src tests\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--task",
                "implement output profile policy",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    context = _implement_context(payload)
    encoded = json.dumps(payload)
    assert payload["kind"] == "implementer-context-tiny/v1"
    assert set(payload) <= {"kind", "target", "next", "proof", "reuse_pressure", "context", "drill_down"}
    adaptive = context["adaptive_routing"]
    assert adaptive["current_need"] == "changed-path-next-action"
    assert adaptive["read_budget"]["profile"] == "tiny"
    assert adaptive["detail_commands"]["task_scoped_state"].startswith("agentic-workspace summary --changed")
    assert "raw workspace files" in adaptive["not_needed_now"]
    assert payload["next"]["action"] == "Inspect only the listed files and run the required validation commands."
    assert payload["next"]["command"] == "make test-workspace"
    assert payload["next"]["run"] == payload["next"]["command"]
    assert "make lint-workspace" in payload["next"]["commands"]
    assert context["scope"]["inspect_files"] == ["generated/workspace/python/cli.py"]
    assert "make test-workspace" in payload["proof"]["required_commands"]
    assert "uv run python scripts/check/check_generated_command_packages.py" in payload["proof"]["required_commands"]
    assert payload["proof"]["acceptance_guidance"]["status"] == "present"
    assert context["routing"]["work_shape"] == "bounded"
    acknowledgement = context["intent_acknowledgement"]
    assert acknowledgement["decision"] == "proceed-with-stated-assumption"
    assert acknowledgement["fields"] == [
        "inferred_intent",
        "concrete_first_slice",
        "non_goals_or_deferred_scope",
        "correction_point",
    ]
    assert acknowledgement["proceed_unless_corrected"] is True
    assert context["delegation_decision"]["status"] == "evaluated"
    assert context["delegation_decision"]["mode"] in {"suggest", "auto"}
    assert context["acceptance_reconciliation"]["task_text_available"] is True
    assert context["acceptance"]["status"] == "inferred"
    assert context["acceptance"]["closeout_required"] is True
    assert context["objective_drift"]["status"] in {"clear", "not-enough-explicit-outcomes"}
    assert "package_boundary" not in payload
    assert "authority_markers" not in payload
    assert "durable_intent" not in payload
    assert "inference_limits" not in payload
    assert len(encoded) < 14500


def test_implement_accumulates_repeated_changed_flags(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--changed",
                "tests/test_workspace_implement_cli.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["changed_paths"] == [
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "tests/test_workspace_implement_cli.py",
    ]
    assert payload["proof"]["changed_paths"] == [
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "tests/test_workspace_implement_cli.py",
    ]


def test_implement_package_cli_edits_select_generated_command_package_gate(capsys) -> None:
    assert (
        cli.main(
            [
                "implement",
                "--changed",
                "generated/memory/python/cli.py",
                "--task",
                "change package cli runtime adapter",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "make test-memory" in payload["proof"]["required_commands"]
    assert "uv run python scripts/check/check_generated_command_packages.py" in payload["proof"]["required_commands"]


def test_implement_uses_available_target_makefile_targets(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "llms.txt",
                "--task",
                "Remove `llms.txt`",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["next"]["commands"] == ["make test", "make lint"]
    assert payload["proof"]["required_commands"] == ["make test", "make lint"]
    assert "make test-workspace" not in json.dumps(payload)


def test_cli_invoke_rewrites_package_sibling_commands_when_repo_local() -> None:
    assert (
        cli._command_with_cli_invoke(
            command="agentic-workspace planning handoff --target . --format json",
            cli_invoke="uv run agentic-workspace",
        )
        == "uv run agentic-workspace planning handoff --target . --format json"
    )


def test_implement_task_file_preserves_task_intent_for_acceptance_checks(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "sample_app" / "text.py", "def normalize_cli_text(value):\n    return value.strip()\n")
    task_file = tmp_path / ".agentic-workspace" / "local" / "scratch" / "task-intent.txt"
    _write(task_file, "Implement normalize_whitespace(text) and sentence_summary(text)\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--task-file",
                ".agentic-workspace/local/scratch/task-intent.txt",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    context = _implement_context(payload)
    assert context["acceptance"]["items"][0]["id"] == "A1"
    assert "normalize_whitespace" in context["acceptance"]["items"][0]["expectation"]
    assert payload["proof"]["acceptance_guidance"]["acceptance_item_count"] >= 2
    assert context["acceptance_reconciliation"]["task_text_available"] is True
    assert context["acceptance_reconciliation"]["requested_outcomes"] == ["normalize_whitespace", "sentence_summary"]
    assert context["acceptance_reconciliation"]["acceptance_item_count"] >= 2
    assert context["objective_drift"]["missing_from_changed_surface"] == ["normalize_whitespace", "sentence_summary"]


def test_implement_task_text_does_not_route_broad_issue_ingestion_to_planning(tmp_path: Path, capsys) -> None:
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--task",
                "ingest and implement all open GitHub issues",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "task_routing" not in payload
    assert payload["planning_safety_gate"]["status"] == "clear"
    assert payload["planning_safety_gate"]["work_shape_facts"]["agent_decision_required"] is True
    assert payload["next_allowed_action"] == "Provide --changed paths or use start/preflight before broad implementation."
    assert payload["handoff_requirements"]["stop_when"][0] != "task routing status is needs-planning for broad external-work ingestion"


def test_implement_task_allows_narrow_single_issue_context(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)

    assert cli.main(["implement", "--target", str(tmp_path), "--task", "implement issue #424", "--verbose", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "task_routing" not in payload
    assert payload["planning_safety_gate"]["status"] == "clear"
    assert payload["planning_safety_gate"]["work_shape_facts"]["scope_factors"]["issue_refs"] == ["#424"]
    assert payload["planning_safety_gate"]["work_shape_facts"]["agent_decision_required"] is True
    assert payload["next_allowed_action"] == "Provide --changed paths or use start/preflight before broad implementation."


def test_implement_with_explicit_target_ignores_checkout_active_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    active_checkout = tmp_path / "active-checkout"
    isolated_target = tmp_path / "isolated-target"
    active_checkout.mkdir()
    isolated_target.mkdir()
    _init_git_repo(active_checkout)
    _init_git_repo(isolated_target)
    _write_empty_planning_state(isolated_target)
    _write(
        active_checkout / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "live-plan", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/live-plan.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(
        active_checkout / ".agentic-workspace/planning/execplans/live-plan.plan.json",
        '{"schema_version":"execplan/v1","id":"live-plan","status":"active"}\n',
    )
    monkeypatch.chdir(active_checkout)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(isolated_target),
                "--task",
                "implement issue #424",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "task_routing" not in payload
    assert payload["planning_safety_gate"]["status"] == "clear"
    assert payload["next_allowed_action"] == "Provide --changed paths or use start/preflight before broad implementation."


def test_implement_task_specific_acceptance_warns_on_objective_drift(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "sample_app" / "text.py", "def normalize_cli_text(value):\n    return value.strip()\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--task",
                "Implement normalize_whitespace(text) and sentence_summary(text)",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    acceptance = payload["acceptance_reconciliation"]
    assert acceptance["task_text_available"] is True
    assert acceptance["requested_outcomes"] == ["normalize_whitespace", "sentence_summary"]
    assert acceptance["acceptance_items"][0]["status"] == "unchecked"
    assert "acceptance/requested" in acceptance["compact_closeout_prompt"]
    drift = payload["objective_drift"]
    assert drift["status"] == "warning"
    assert drift["missing_from_changed_surface"] == ["normalize_whitespace", "sentence_summary"]
    assert drift["acceptance_item_count"] >= 2
    assert "self-authored tests alone" in acceptance["compact_closeout_prompt"]


def test_implement_objective_drift_accepts_explicit_deleted_outcome(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "llms.txt",
                "--task",
                "Remove `llms.txt` and replace it with install docs",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    drift = _implement_context(payload)["objective_drift"]
    assert drift["status"] == "clear"
    assert drift["requested_outcomes"] == ["llms.txt"]
    assert drift["removed_or_retired_outcomes"] == ["llms.txt"]
    assert drift["missing_from_changed_surface"] == []


def test_implement_objective_drift_keeps_missing_path_without_removal_intent(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "llms.txt",
                "--task",
                "Document `llms.txt` behavior",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    drift = _implement_context(payload)["objective_drift"]
    assert drift["status"] == "warning"
    assert drift["removed_or_retired_outcomes"] == []
    assert drift["missing_from_changed_surface"] == ["llms.txt"]


def test_implement_command_surfaces_reasoning_heavy_execution_posture(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[runtime]",
                "strong_planner_available = true",
                "cheap_bounded_executor_available = true",
                "",
                "[delegation]",
                'mode = "manual"',
                "",
                "[delegation_targets.planner]",
                'strength = "strong"',
                'location = "local"',
                'capability_classes = ["boundary-shaping", "reasoning-heavy"]',
                'execution_methods = ["internal"]',
            ]
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json",
                "--task",
                "update delegation config schema",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    posture = payload["execution_posture"]
    assert posture["capability_posture"]["posture"]["execution class"] == "boundary-shaping"
    assert posture["capability_posture"]["work_shape"] == "bounded"
    assert posture["capability_posture"]["proof_burden"] == "high"
    assert "schema" in posture["capability_posture"]["risk_flags"]
    assert "proof route" in posture["capability_posture"]["inspection_evidence_required"]
    assert posture["capability_posture"]["self_assessment_authority"] == "advisory-only"
    assert posture["runtime_resolution"]["recommendation"] == "stronger-reasoning"
    assert posture["runtime_resolution"]["self_assessment"]["authority"] == "advisory-only"
    assert posture["delegation_control"]["effective_mode"] == "manual"
    assert posture["delegation_control"]["execution_permitted"] is False
    assert posture["selected_target"]["name"] == "planner"
    assert posture["capability_handoff_packets"]["packet_types"]["manual_human_clarification"]
    assert posture["ready_handoff"]["kind"] == "agentic-workspace/capability-handoff-packet/v1"
    assert posture["ready_handoff"]["mode"] == "manual"
    assert posture["ready_handoff"]["packet_type"] == "manual_human_clarification"
    assert "quality" in posture["ready_handoff"]["prompt"]
    assert posture["delegation_decision"]["decision"] == "suggest-escalation"
    assert posture["delegation_decision"]["required_next_action"] == "prepare-handoff"
    assert posture["delegation_decision"]["route_obligation"]["must"].startswith("Prepare the handoff packet")
    assert "report why" in posture["delegation_decision"]["route_obligation"]["report_if_skipped"]
    assert posture["delegation_decision"]["config_effect"]["source_path"] == ".agentic-workspace/config.local.toml"
    assert posture["delegation_decision"]["config_effect"]["delegation_mode"] == "manual"
    assert posture["delegation_decision"]["config_effect"]["execution_authority"] == "suggest-or-handoff-only"
    assert posture["delegation_decision"]["handoff_command"] == "agentic-workspace planning handoff --target . --format json"
    assert posture["delegation_decision"]["handoff_surface"]["required_packet_fields"] == [
        "intent",
        "constraints",
        "read_first_refs",
        "owned_scope",
        "proof_expectations",
        "stop_conditions",
        "return_contract",
        "target_posture",
    ]
    assert "active execplan" in posture["delegation_decision"]["handoff_surface"]["fallback_when_unavailable"]
    assert payload["delegation_decision"] == posture["delegation_decision"]


def test_implement_auto_delegation_exposes_bounded_slice_handoff(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[runtime]",
                "supports_internal_delegation = true",
                "cheap_bounded_executor_available = true",
                "",
                "[safety]",
                "safe_to_auto_run_commands = true",
                "",
                "[delegation_targets.mini]",
                'strength = "medium"',
                'location = "local"',
                "confidence = 0.8",
                'task_fit = ["bounded implementation", "validation"]',
                'capability_classes = ["mixed", "mechanical-follow-through"]',
                'execution_methods = ["cli"]',
            ]
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--task",
                "Implement bounded text helper behavior",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    decision = _implement_context(payload)["delegation_decision"]
    assert decision["decision"] == "delegate-bounded-slice"
    assert decision["target"] == "mini"
    assert decision["required_next_action"] == "execute-when-safe"
    assert decision["token_savings_expected"] == "likely"
    effort = decision["effort_recommendation"]
    assert effort["cost_posture"] == "save-tokens-where-safe"
    assert effort["orchestrator"] == "medium"
    assert effort["implementer"] == "medium delegate"
    assert decision["route_obligation"]["must"].startswith("Execute only when local auto mode")
    assert decision["config_effect"]["authority"] == "local-config"
    assert decision["config_effect"]["execution_authority"] == "auto-execution-permitted"
    assert decision["handoff_command"] == "agentic-workspace planning handoff --target . --format json"
    assert decision["delegation_next_step"]["status"] == "executable"
    assert decision["delegation_next_step"]["must_report_if_not_run"] is True
    assert decision["delegation_next_step"]["execution_methods"] == ["cli"]
    assert "bounded work" in decision["reason"]


def test_implement_epic_decomposition_prefers_reusable_worker_over_manual_relay(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[safety]",
                "safe_to_auto_run_commands = true",
                "",
                "[delegation_targets.chatgpt]",
                'strength = "strong"',
                'location = "external"',
                'capability_classes = ["boundary-shaping", "reasoning-heavy", "mixed"]',
                'execution_methods = ["manual"]',
            ]
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "decompositions" / "codegen.decomposition.json",
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Codegen epic",
                "status": "shaping",
                "larger_intended_outcome": "Use decomposed artifacts to finish an epic cheaply.",
                "non_goals": [],
                "candidate_lanes": [
                    {
                        "id": "black-box-harness",
                        "title": "Black-box harness",
                        "readiness": "needs-shaping",
                        "outcome": "Choose the next bounded conformance slice.",
                        "owner_surface": "",
                        "proof": "Report likely changed files and validation.",
                        "depends_on": [],
                        "parallel_with": [],
                    }
                ],
                "dependency_assumptions": [],
                "parallelization_assumptions": [],
                "proof_expectations": ["Focused proof remains unchanged."],
                "promotion_rule": "Promote only bounded slices.",
                "references": [],
                "notes": "",
            },
            indent=2,
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--task",
                "Continue the codegen epic and evaluate reusable-worker delegation",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    decision = _implement_context(payload)["delegation_decision"]
    assert decision["decision"] == "suggest-delegation"
    assert decision["target"] == "reusable-worker"
    assert decision["required_next_action"] == "select-or-promote-bounded-lane"
    assert decision["token_savings_expected"] == "possible"
    assert decision["config_effect"]["execution_authority"] == "auto-execution-permitted"
    assert "handoff_command" not in decision
    assert decision["delegation_next_step"]["status"] == "prepare-or-report"
    assert decision["delegation_next_step"]["action"] == "select-or-promote-bounded-lane"
    assert decision["delegation_next_step"]["command"] is None
    assert decision["delegation_next_step"]["execution_methods"] == ["internal", "cli"]
    assert decision["delegation_next_step"]["must_report_if_not_run"] is False
    assert decision["delegation_next_step"]["handoff_contract_status"] == "unavailable-without-active-planning"
    assert "proof run and result" in decision["delegation_next_step"]["return_contract"]
    assert decision["decomposition_delegation"]["status"] == "available-without-active-planning"
    assert decision["delegation_candidates"][0]["route_candidate"] == "delegate-exploration"
    assert "reuse an existing worker" in decision["reason"]
    assert "auto_delegation_audit" not in decision


def test_implement_suppresses_manual_external_relay_for_code_local_changed_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[safety]",
                "safe_to_auto_run_commands = true",
                "",
                "[delegation_targets.chatgpt]",
                'strength = "strong"',
                'location = "external"',
                'capability_classes = ["boundary-shaping", "reasoning-heavy", "mixed"]',
                'execution_methods = ["manual"]',
            ]
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/package/feature.py",
                "--task",
                "Implement schema and CLI behavior for the feature",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    decision = _implement_context(payload)["delegation_decision"]
    assert decision["decision"] == "stay-local"
    assert decision["required_next_action"] == "continue-local"
    assert decision["effort_recommendation"]["orchestrator"] == "medium"
    assert decision["effort_recommendation"]["implementer"] == "medium"
    assert decision["effort_recommendation"]["validator"] == "high"
    assert decision["effort_recommendation"]["cost_posture"] == "quality-first"
    assert "target" not in decision["effort_recommendation"]
    assert "manual_external_relay" not in decision
    assert "config_effect" not in decision
    assert "manual_prompt" not in decision
    assert "handoff_command" not in decision


def test_implement_supports_selector_drilldown(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[safety]",
                "safe_to_auto_run_commands = true",
                "",
                "[delegation_targets.mini]",
                'strength = "medium"',
                'location = "local"',
                'task_fit = ["bounded implementation"]',
                'capability_classes = ["mechanical-follow-through"]',
                'execution_methods = ["cli"]',
            ]
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--task",
                "Implement bounded text helper behavior",
                "--select",
                "context.delegation_decision.required_next_action,context.delegation_decision.delegation_next_step.must_report_if_not_run,context.delegation_decision.effort_recommendation.cost_posture",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert "missing" not in payload
    assert "available_selectors" not in payload
    assert payload["values"]["context.delegation_decision.required_next_action"] == "execute-when-safe"
    assert payload["values"]["context.delegation_decision.delegation_next_step.must_report_if_not_run"] is True
    assert payload["values"]["context.delegation_decision.effort_recommendation.cost_posture"] == "save-tokens-where-safe"


def test_implement_selector_surfaces_reuse_pressure_without_blocking_direct_work(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "helpers.py",
        "def normalize_text(value):\n    return value.strip()\n",
    )
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--task",
                "Add a text normalization helper",
                "--select",
                "reuse_pressure,context.workflow_sufficiency",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    reuse_pressure = payload["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "existing_helper_candidate"
    assert reuse_pressure["findings"][0]["symbol"] == "normalize_text"
    assert reuse_pressure["findings"][0]["candidate_paths"] == ["src/sample_app/helpers.py"]
    assert "accept-duplication-with-reason" in reuse_pressure["allowed_outcomes"]
    assert payload["values"]["context.workflow_sufficiency"]["decision"] == "enough-for-bounded-implementation"


def test_implement_reuse_pressure_ignores_dependency_cache_definitions(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )
    _write(
        tmp_path / "packages" / "planning" / ".uv-cache" / "archive-v0" / "dependency" / "text.py",
        "def normalize_text(value):\n    return value\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "none_found"
    assert reuse_pressure["findings"] == []


def test_implement_reuse_pressure_surfaces_repeated_special_case(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "legacy_a.py",
        'def route_mode(mode):\n    if mode == "legacy":\n        return "old"\n    return "new"\n',
    )
    _write(
        tmp_path / "src" / "sample_app" / "legacy_b.py",
        'def display_mode(mode):\n    if mode == "legacy":\n        return "old"\n    return "new"\n',
    )
    _write(
        tmp_path / "src" / "sample_app" / "legacy_c.py",
        'def save_mode(mode):\n    if mode == "legacy":\n        return "old"\n    return "new"\n',
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/legacy_c.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "abstraction_pressure"
    finding = reuse_pressure["findings"][0]
    assert finding["kind"] == "repeated_special_case"
    assert finding["candidate_paths"] == ["src/sample_app/legacy_a.py", "src/sample_app/legacy_b.py"]


def test_implement_reuse_pressure_exposes_recording_and_routing_options(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "helpers.py",
        "def normalize_text(value):\n    return value.strip()\n",
    )
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    options = {option["id"]: option for option in reuse_pressure["next_decision_options"]}
    assert options["record-duplication-accepted"]["resulting_state"] == "duplication_accepted_with_reason"
    assert "reason" in options["record-duplication-accepted"]["requires"]
    assert options["route-extraction-follow-up"]["resulting_state"] == "extraction_deferred_with_owner"
    assert "owner" in options["route-extraction-follow-up"]["requires"]
    recording_options = reuse_pressure["recording_options"]
    assert any("memory capture-note" in command for command in recording_options["accept_duplication"]["commands"])
    assert any("planning new-plan" in command for command in recording_options["route_extraction"]["commands"])
    assert any("memory capture-note" in command for command in recording_options["route_extraction"]["commands"])


def test_implement_reuse_pressure_surfaces_memory_boundary_notes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml",
        """
version = 1

[notes.".agentic-workspace/memory/repo/decisions/helper-boundaries.md"]
note_type = "decision"
surfaces = ["abstraction", "reuse"]
routes_from = ["src/sample_app/*.py"]
""",
    )
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert reuse_pressure["memory_signals"]["status"] == "matched"
    assert reuse_pressure["memory_signals"]["matches"][0]["path"] == ".agentic-workspace/memory/repo/decisions/helper-boundaries.md"
    assert "memory route" in reuse_pressure["memory_signals"]["route_command"]


def test_implement_reuse_pressure_keeps_small_direct_task_unblocked(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "single.py",
        "def parse_one(value):\n    return int(value)\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/single.py",
                "--select",
                "reuse_pressure,context.workflow_sufficiency",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    reuse_pressure = payload["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "none_found"
    assert reuse_pressure["findings"] == []
    options = {option["id"]: option for option in reuse_pressure["next_decision_options"]}
    assert options["continue-direct"]["allowed"] is True
    assert options["route-extraction-follow-up"]["allowed"] is False
    assert payload["values"]["context.workflow_sufficiency"]["decision"] == "enough-for-bounded-implementation"


def test_implement_reuse_pressure_demotes_generic_sibling_helpers_to_weak_hints(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "alpha.py",
        "def build_invoice(total):\n    return total\n",
    )
    _write(
        tmp_path / "src" / "sample_app" / "beta.py",
        "def render_dashboard(rows):\n    return rows\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/alpha.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "none_found"
    assert reuse_pressure["finding_count"] == 0
    assert reuse_pressure["weak_hint_count"] == 1
    assert reuse_pressure["weak_hints"][0]["kind"] == "sibling_helper_hint"
    options = {option["id"]: option for option in reuse_pressure["next_decision_options"]}
    assert options["route-extraction-follow-up"]["allowed"] is False


def test_implement_reuse_pressure_promotes_token_matched_sibling_helper(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "invoice_format.py",
        "def invoice_currency(total):\n    return f'${total}'\n",
    )
    _write(
        tmp_path / "src" / "sample_app" / "invoice_parse.py",
        "def parse_invoice_total(raw):\n    return int(raw)\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/invoice_format.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "similar_pattern_candidate"
    assert reuse_pressure["findings"][0]["kind"] == "sibling_helper_hint"
    assert "invoice" in reuse_pressure["findings"][0]["matched_tokens"]
    assert reuse_pressure["weak_hint_count"] == 0


def test_implement_selector_reports_available_fields_for_missing_selector(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "does_not_exist",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["missing"] == ["does_not_exist"]
    assert "context.delegation_decision" in payload["available_selectors"]
    assert "next" in payload["available_selectors"]
    assert "context.scope" in payload["available_selectors"]
    assert "proof" in payload["available_selectors"]
    assert "reuse_pressure" in payload["available_selectors"]
