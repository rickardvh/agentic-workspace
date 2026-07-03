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


def _write_planning_lane_schema(target: Path) -> None:
    schema = json.loads(Path(".agentic-workspace/planning/schemas/planning-lane.schema.json").read_text(encoding="utf-8"))
    _write_json(target / ".agentic-workspace" / "planning" / "schemas" / "planning-lane.schema.json", schema)


def _implement_context(payload: dict[str, object]) -> dict[str, object]:
    context = payload.get("context")
    return context if isinstance(context, dict) else payload


def test_implement_context_adapter_routes_through_implement_owner_facade() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    implement_command = (repo_root / "generated" / "workspace" / "python" / "commands" / "implement_context.py").read_text(encoding="utf-8")
    implement_facade = (repo_root / "generated" / "workspace" / "python" / "primitives" / "workspace_implement_runtime.py").read_text(
        encoding="utf-8"
    )

    assert "from ..primitives.workspace_implement_runtime import _run_implement_context_adapter" in implement_command
    assert "from agentic_workspace.workspace_runtime_implement import _run_implement_context_adapter" in implement_facade
    assert workspace_runtime_primitives._run_implement_context_adapter is workspace_runtime_implement._run_implement_context_adapter


def test_implement_tiny_surfaces_local_high_risk_overlay(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
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

[local_overlay.high_risk.validation_profiles.migration]
category = "migration"
applies_to_paths = ["db/migrations/**"]
required_commands = ["python -c \\"print('migration validation')\\""]
manual_checks = ["Confirm rollback note exists."]
impact = "blocking"
""",
    )
    _write(tmp_path / "db" / "migrations" / "001_init.sql", "select 1;\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "db/migrations/001_init.sql",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["proof"]["high_risk_overlay"]["status"] == "active"
    assert payload["proof"]["high_risk_overlay"]["active_count"] == 1
    assert "high_risk_overlay=1" in payload["action_signals"]["changed_signals"]


def test_implement_tiny_surfaces_ordinary_local_overlay_without_high_risk(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
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

[local_overlay.guidance.local_cli]
signal = "local-tool-availability"
category = "tooling"
applies_to_paths = ["tools/**"]
guidance = "Local CLI is available in this checkout."
required_commands = ["python -c \\"print('tool ok')\\""]
impact = "advisory"
""",
    )
    _write(tmp_path / "tools" / "run.py", "print('ok')\n")

    assert cli.main(["implement", "--target", str(tmp_path), "--changed", "tools/run.py", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["proof"]["local_overlay"]["status"] == "active"
    assert payload["proof"]["local_overlay"]["active_count"] == 1
    assert payload["proof"]["high_risk_overlay"] == {}
    assert "local_overlay=1" in payload["action_signals"]["changed_signals"]


def test_implement_exposes_communication_contract_for_changed_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "README.md", "# Project\n")

    assert cli.main(["implement", "--target", str(tmp_path), "--changed", "README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    contract = payload["communication_contract"]
    assert contract["kind"] == "agentic-workspace/communication-contract/v1"
    assert contract["surface"] == "implementation"
    assert contract["default_posture"] == "decision_first_state_backed"
    assert "implementation" in contract["phase_ids"]
    assert contract["cost_evaluation"]["reduce"] == [
        "low_value_narration",
        "repeated_rereads",
        "context_reconstruction",
    ]
    assert "current_decision" not in payload
    assert "message_economy" not in payload
    assert "continuation_capsule" not in payload


def _write_architecture_principles(target_root: Path) -> None:
    _write(
        target_root / ".agentic-workspace" / "system-intent" / "intent.toml",
        """
kind = "agentic-workspace/system-intent/v1"
summary = "Portable host-neutral operating intent."
governing_intents = ["Keep package contracts portable across host repos."]
anti_intents = ["Do not let this repo's current language, tooling, structure, or agent preferences become hidden universal product assumptions."]
decision_tests = ["Favor work that improves portability by reducing accidental repo assumptions."]
confidence = "high"
needs_review = false

[[architecture_principles]]
id = "host-agnostic-agent-judgment"
title = "Preserve host-agnostic agent judgment"
authority = "repo-system-intent"
owner = "workspace-runtime"
summary = "AW provides infrastructure for agent judgment instead of package-owned host assumptions."
derived_from = ["anti_intents:Do not let this repo's current language, tooling, structure, or agent preferences become hidden universal product assumptions.", "issue:#1665"]
allowed_sources = ["explicit structured facts", "AW-owned enum labels", "configuration"]
forbidden_sources = ["package-owned assumptions about prose keywords", "package-owned assumptions about file names"]
affected_decisions = ["routing", "ownership", "proof-selection"]
path_globs = ["src/agentic_workspace/workspace_runtime*.py"]
guardrail_refs = ["docs/maintainer/non-enum-keyword-routing-audit.json"]
derived_applications = ["non-enum-keyword-routing"]
proof_expectation = "Closeout must state whether the principle was preserved or re-scoped."

[[architecture_principles.guardrails]]
id = "non-enum-keyword-routing"
summary = "Do not infer workflow authority from arbitrary prose marker phrases."
guardrail_refs = ["docs/maintainer/non-enum-keyword-routing-audit.json"]
""",
    )


def test_implement_changed_surfaces_task_posture_packet(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path)]) == 0
    capsys.readouterr()
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py", "def changed():\n    return True\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Implement #1392 in full",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    packet = payload["task_posture_packet"]
    assert packet["kind"] == "agentic-workspace/task-posture-packet/v1"
    assert packet["posture_adherence"]["closeout_question"].startswith("Did the work follow the task posture packet")
    assert packet["dynamic_instruction_projection"]["provenance_preserved"] is True
    assert "knowledge_gates" not in packet


def test_implement_surfaces_memory_decision_packet_for_changed_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(tmp_path / "docs" / "package" / "knowledge-routing.md", "# Knowledge Routing\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/package/knowledge-routing.md",
                "--task",
                "Improve Memory routing guidance",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    packet = payload["memory_decision_packet"]
    assert packet["kind"] == "agentic-workspace/memory-decision-packet/v1"
    assert packet["stage"] == "implement"
    assert packet["force"] in {"recommended_before_work", "required_before_claim"}
    assert packet["pull"]["status"] == "checked_none"
    assert "--stage implement" in packet["pull"]["recommended_command"]
    assert "docs/package/knowledge-routing.md" in packet["pull"]["recommended_command"]
    assert packet["pull"]["route_count"] >= 1
    assert packet["pull"]["relevant_route_count"] == 0
    assert packet["capture"]["candidate_owner_surface_count"] >= 3
    assert "candidate_owner_surfaces" not in packet["capture"]
    assert "authority_boundary" not in packet
    assert "limits" not in packet
    assert packet["detail_visibility"] == ("full authority, limits, owner, and candidate detail stay behind verbose implement context")
    assert len(json.dumps(packet, separators=(",", ":")).encode()) < 900

    capsys.readouterr()
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/package/knowledge-routing.md",
                "--task",
                "Improve Memory routing guidance",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )
    verbose_packet = json.loads(capsys.readouterr().out)["memory_decision_packet"]
    assert "repo_memory" in verbose_packet["capture"]["candidate_owner_surfaces"]
    assert "local_memory" in verbose_packet["capture"]["candidate_owner_surfaces"]
    assert "planning" in verbose_packet["capture"]["candidate_owner_surfaces"]
    assert verbose_packet["authority_boundary"]["agent_owns"]


def test_implement_surfaces_operating_loop_with_proof_blocker(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Implement bounded runtime change",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    packet = payload["operating_loop"]
    assert packet["kind"] == "agentic-workspace/operating-loop-decision/v1"
    assert packet["verification"]["state"] == "proof_missing"
    assert packet["closeout_state"] == "blocked_missing_proof"
    assert packet["safe_claim"] == "blocked"
    assert packet["residue_owner"] == "verification"
    assert "run_or_refresh_proof" in packet["required_before_full_closure"]
    assert packet["reasons"][0]["code"] == "proof_missing"


def test_implement_does_not_require_stale_deleted_test_inventory_sweep(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "model-cli-harness"
paths = ["tools/model-cli-harness/**", "docs/maintainer/test-knowledge-inventory.md"]
owns = ["model CLI harness"]
proof = [
  "uv run pytest --collect-only -q tests packages",
  "rg -n \\"test_model_cli_harness.py\\" docs/maintainer/test-knowledge-inventory.md",
]
""",
    )
    _write(
        tmp_path / "docs" / "maintainer" / "test-knowledge-inventory.md",
        "# Test Knowledge Inventory\n\nRetired: tests/test_model_cli_harness.py\n",
    )
    _write(tmp_path / "tools" / "model-cli-harness" / "README.md", "# Harness\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "tools/model-cli-harness/README.md",
                "--task",
                "Update model CLI harness docs",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    required_commands = payload["proof"]["required_commands"]
    assert "uv run pytest --collect-only -q tests packages" in required_commands
    assert not any("test_model_cli_harness.py" in command for command in required_commands)

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "tools/model-cli-harness/README.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    proof_payload = json.loads(capsys.readouterr().out)
    unavailable = proof_payload["unavailable_proof_commands"]
    assert any(
        command["lane"] == "subsystem:model-cli-harness" and "test_model_cli_harness.py" in command.get("missing_paths", "")
        for command in unavailable
    )


def test_implement_compact_surfaces_proof_narrowness_before_validation(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    _write(
        tmp_path / "Makefile",
        "test-planning:\n\t@echo ok\nlint-planning:\n\t@echo ok\ntypecheck-planning:\n\t@echo ok\n",
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "--task",
                "Update planning package installer",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    narrowness = payload["proof"]["proof_narrowness"]
    assert narrowness["status"] == "narrow_required"


def test_implement_compact_surfaces_broad_proof_narrowness_before_validation(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    _write(tmp_path / "Makefile", "test-workspace:\n\t@echo ok\nlint-workspace:\n\t@echo ok\n")
    _write(tmp_path / "scripts" / "run_agentic_workspace.py", "print('ok')\n")
    _write(tmp_path / "scripts" / "check" / "check_generated_command_packages.py", "print('ok')\n")
    _write(tmp_path / "scripts" / "check" / "run_operation_conformance_tests.py", "print('ok')\n")
    _write(tmp_path / "tests" / "test_workspace_cli.py", "def test_ok():\n    assert True\n")
    capsys.readouterr()

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--task",
                "Update generated workspace CLI projection",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    narrowness = payload["proof"]["proof_narrowness"]
    assert narrowness["status"] == "broad_required"
    assert narrowness["broad_suite_boundary_status"] == "required_acceptance_boundary"
    assert narrowness["expansion_trigger_lane"] in {"workspace_cli", "generated_command_packages"}


def test_operating_loop_schema_rejects_unknown_enum_values() -> None:
    schema_path = Path("src/agentic_workspace/contracts/schemas/implementer_context.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    valid = cli._operating_loop_decision_payload(proof={"required_commands": ["uv run pytest tests/test_workspace_implement_cli.py -q"]})
    errors = sorted(
        validator.evolve(schema=schema["$defs"]["operating_loop"]).iter_errors(valid),
        key=lambda error: list(error.path),
    )
    assert [error.message for error in errors] == []

    invalid = {**valid, "safe_claim": "maybe"}
    errors = sorted(
        validator.evolve(schema=schema["$defs"]["operating_loop"]).iter_errors(invalid),
        key=lambda error: list(error.path),
    )
    assert any("not one of" in error.message for error in errors)


def test_implement_text_renders_bounded_operating_loop_summary(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(tmp_path / "docs" / "note.md", "# Note\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/note.md",
                "--task",
                "Update a compact doc note",
            ]
        )
        == 0
    )

    lines = capsys.readouterr().out.splitlines()
    loop_lines = [line for line in lines if line.startswith(("loop:", "closeout:"))]
    assert len(loop_lines) == 2
    assert "Memory " in loop_lines[0]
    assert "Planning " in loop_lines[0]
    assert "Verification " in loop_lines[0]
    assert "claim " in loop_lines[1]
    assert len("\n".join(loop_lines).encode("utf-8")) < 240
    assert "candidate_routes" not in "\n".join(loop_lines)
    assert any(line.startswith("next: ") for line in lines)
    assert any(line.startswith(("proof: ", "proof_detail: ")) for line in lines)
    assert any(line.startswith("selectors: ") and "operating_loop" in line for line in lines)
    assert any(line.startswith("detail: ") for line in lines)


def test_implement_compact_omits_routine_stay_local_delegation_noise(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(tmp_path / "docs" / "note.md", "# Note\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/note.md",
                "--task",
                "Update a small doc note",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    context = _implement_context(payload)

    assert "delegation_decision" not in context
    assert "context.delegation_decision" not in payload["action_signals"]["advisory_detail"]["selectors"]
    assert "context.delegation_decision" not in payload["drill_down"]["available_selectors"]


def test_implement_compact_keeps_delegation_when_route_changes_next_action(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[runtime]",
                "strong_planner_available = true",
                "",
                "[delegation]",
                'mode = "manual"',
            ]
        ),
    )
    _write(tmp_path / "src" / "agentic_workspace" / "contracts" / "schemas" / "workspace_local_override.schema.json", "{}\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json",
                "--task",
                "Update delegation config schema",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    context = _implement_context(payload)

    assert context["delegation_decision"]["recommended_route"] == "suggest-escalation"
    assert context["delegation_decision"]["required_next_action"] == "prepare-handoff"
    assert "context.delegation_decision" in payload["action_signals"]["advisory_detail"]["selectors"]
    assert "context.delegation_decision" in payload["drill_down"]["available_selectors"]


def test_implement_memory_decision_packet_reports_relevant_route_matches(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    note = tmp_path / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("# API\n", encoding="utf-8")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml",
        """
version = 1

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
routes_from = ["src/api.py"]
""",
    )
    _write(tmp_path / "src" / "api.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/api.py",
                "--task",
                "Update API behavior",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["memory_decision_packet"]

    assert packet["pull"]["status"] == "relevant_notes_found"
    assert any(route["path"] == ".agentic-workspace/memory/repo/domains/api.md" for route in packet["pull"]["candidate_routes"])


def test_implement_surfaces_pre_work_knowledge_gate_for_source_authority_task(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path)]) == 0
    capsys.readouterr()
    _write(tmp_path / "packages" / "planning" / "README.md", "# Planning\n")
    _write(tmp_path / "packages" / "memory" / "README.md", "# Memory\n")
    _write(tmp_path / "docs" / "package" / "knowledge-gates.md", "# Pre-Work Knowledge Gates\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/package/knowledge-gates.md",
                "--task",
                "Implement #1395 pre-work knowledge gates",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    packet = payload["task_posture_packet"]
    gates = {gate["gate_id"]: gate for gate in packet["knowledge_gates"]}
    assert gates["source-authority-model"]["force"] == "required_before_design"
    assert gates["source-authority-model"]["resolution_state"] == "open"
    assert "blocked_claims" not in packet
    assert all("blocked_claims" not in gate for gate in packet["knowledge_gates"])
    assert "change gate vocabulary without checking source authority" in packet["blocked_actions"]
    assert "allowed-after-proof" in packet["closeout_boundaries"]
    assert packet["gate_summary"]["blocking_count"] >= 1


def test_implement_command_returns_bounded_context_and_boundary_warnings(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json", "{}")
    _write(
        tmp_path / "tests" / "test_workspace_proof_generated_packages_cli.py",
        "def test_generated_package_fixture():\n    assert True\n",
    )
    _write(tmp_path / "scripts" / "check" / "check_generated_command_packages.py", "print('ok')\n")
    _write(tmp_path / "scripts" / "check" / "run_operation_conformance_tests.py", "print('ok')\n")

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
        "uv run python scripts/check/run_operation_conformance_tests.py --target python",
        "uv run python scripts/check/check_generated_command_packages.py --python-conformance",
        "uv run python scripts/check/check_generated_command_packages.py --python-docker-conformance --require-docker",
        "uv run pytest tests/test_workspace_proof_generated_packages_cli.py -q",
    ]
    freshness = payload["proof"]["generated_cli_freshness"]
    assert freshness["status"] == "required"
    assert freshness["obligation"] == "required"
    assert freshness["freshness_check_command"] == "uv run python scripts/generate/generate_command_packages.py --check"
    assert freshness["refresh_command"] == "uv run python scripts/generate/generate_command_packages.py"
    assert freshness["validation_command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert "uv run python scripts/check/check_generated_command_packages.py" in freshness["required_commands"]
    parity = freshness["generated_target_parity"]
    assert parity["status"] == "required"
    assert parity["target_families"] == ["python", "typescript"]
    assert "Python-only proof" in parity["claim_rule"]
    proof_tiers = {tier["id"]: tier["commands"] for tier in payload["proof"]["proof_command_tiers"]["tiers"]}
    assert proof_tiers["generated_contract"][0]["command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert any(item["command"].endswith("--require-docker") for item in proof_tiers["environmental"])
    retry = payload["proof"]["transient_validation_retry"]
    assert retry["status"] == "available"
    assert retry["retry_limit"] == 1
    assert "uv run python scripts/check/check_generated_command_packages.py --python-conformance" in retry["applies_to"]
    assert payload["proof"]["unavailable_commands"] == []
    assert payload["proof"]["cli_authority_review"]["classifications"][0]["role"] == "projection"
    trust = payload["generated_surface_trust"]
    assert trust["status"] == "present"
    assert trust["direct_edit_blocked_paths"] == ["generated/workspace/python/cli.py"]
    assert trust["items"][0]["canonical_source"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert trust["items"][0]["freshness_status"] == "validation-required"
    assert trust["items"][0]["refresh_command"] == "uv run python scripts/generate/generate_command_packages.py"
    assert trust["items"][0]["validation_command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert trust["items"][0]["direct_edit_allowed"] is False
    assert trust["items"][0]["action_effect"]["force"] == "required_before_claim"
    assert trust["items"][0]["action_effect"]["allowed_now"] == "edit-canonical-source-refresh-and-validate-generated-surface"
    assert trust["items"][0]["action_effect"]["blocked_until_reconciled"] == [
        "claim-generated-surface-fresh",
        "claim-task-complete",
    ]
    assert trust["items"][0]["action_effect"]["resolution_selector"] == "generated_surface_trust"
    assert trust["items"][0]["action_effect"]["resolution_command"] == "uv run python scripts/generate/generate_command_packages.py"
    assert trust["items"][0]["action_effect"]["resolution_commands"] == [
        "uv run python scripts/generate/generate_command_packages.py",
        "uv run python scripts/check/check_generated_command_packages.py",
    ]
    assert trust["action_effect"]["force"] == "required_before_claim"
    assert trust["action_effect"]["blocked_until_reconciled"] == ["claim-generated-surfaces-fresh", "claim-task-complete"]
    assert trust["action_effect"]["resolution_selector"] == "generated_surface_trust"
    assert trust["action_effect"]["resolution_commands"] == [
        "uv run python scripts/generate/generate_command_packages.py",
        "uv run python scripts/check/check_generated_command_packages.py",
    ]
    assert "Do not hand-edit generated/workspace/python/cli.py" in trust["items"][0]["direct_edit_policy"]
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
    assert payload["planning_safety_gate"]["gate_result"] == "agent-work-shape-decision-required"
    assert payload["planning_safety_gate"]["implementation_allowed"] is True
    assert payload["planning_safety_gate"]["work_shape_guidance"]["hard_blockers"] == []


def test_implement_selects_active_assurance_requirements_from_changed_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

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
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "db/migrations/001_privacy.sql",
                "--select",
                "assurance_requirements",
                "--format",
                "json",
            ]
        )
        == 0
    )

    selected = json.loads(capsys.readouterr().out)
    requirements = selected["values"]["assurance_requirements"]
    assert requirements["status"] == "attention"
    assert requirements["active"][0]["id"] == "privacy_data"
    assert requirements["active"][0]["applies_because"] == ["changed path matched db/migrations/**"]
    assert requirements["evidence_status"][0]["missing_evidence"] == ["authority_consulted"]


def test_implement_scopes_assurance_by_matched_subsystem(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "audit-log"
paths = ["src/audit/**"]
owns = ["audit trail semantics"]
proof = ["make audit-proof"]

[[subsystems]]
id = "docs-rendering"
paths = ["docs/**"]
owns = ["documentation rendering"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.subsystem_profiles.audit-log]
assurance_level = "high"
scope_refs = ["ownership.subsystems.audit-log"]
requirement_refs = ["docs/system-requirements.md#auditability"]
required_evidence = ["requirement_grounding", "manual_review"]
proof_profile = "audit"
force = "required-before-closeout"
blocked_without_evidence = ["auditability-complete", "requirement-grounded-completion"]
claim_boundary = "subsystem-scoped"
review_owner = "security-review"

[assurance.subsystem_profiles.docs-rendering]
assurance_level = "low"
required_evidence = ["docs_review"]
force = "recommended"
blocked_without_evidence = ["docs-rendering-complete"]
claim_boundary = "changed-scope"
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/audit/events.py",
                "--select",
                "assurance_requirements,requirement_grounding",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assurance = values["assurance_requirements"]
    subsystem = assurance["subsystem_assurance"]
    assert subsystem["status"] == "attention"
    assert subsystem["matched_subsystem_ids"] == ["audit-log"]
    assert subsystem["effective_assurance_level"] == "high"
    assert subsystem["missing_evidence"] == ["requirement_grounding", "manual_review"]
    assert assurance["active"][0]["id"] == "subsystem:audit-log"
    grounding = values["requirement_grounding"]
    assert grounding["subsystem_assurance"]["effective_assurance_level"] == "high"
    assert "matched-subsystem-assurance" in grounding["source_facts"]["sensitivity_signals"]
    assert "requirement-grounded-completion" in grounding["closeout_claims"]["blocked"]


def test_implement_does_not_inherit_unmatched_high_assurance_subsystem(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "audit-log"
paths = ["src/audit/**"]

[[subsystems]]
id = "docs-rendering"
paths = ["docs/**"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.subsystem_profiles.audit-log]
assurance_level = "high"
required_evidence = ["manual_review"]
force = "required-before-closeout"
blocked_without_evidence = ["auditability-complete"]

[assurance.subsystem_profiles.docs-rendering]
assurance_level = "low"
required_evidence = ["docs_review"]
force = "recommended"
blocked_without_evidence = ["docs-rendering-complete"]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/guide.md",
                "--select",
                "assurance_requirements",
                "--format",
                "json",
            ]
        )
        == 0
    )

    subsystem = json.loads(capsys.readouterr().out)["values"]["assurance_requirements"]["subsystem_assurance"]
    assert subsystem["matched_subsystem_ids"] == ["docs-rendering"]
    assert subsystem["effective_assurance_level"] == "low"
    assert "manual_review" not in subsystem["missing_evidence"]


def test_implement_routes_runtime_assurance_from_workspace_runtime_subsystem(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write_architecture_principles(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "workspace-cli-runtime"
paths = ["generated/workspace/python/**", "src/agentic_workspace/workspace_runtime*.py"]
owns = ["workspace command routing", "workspace runtime source boundaries"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

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
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--task",
                "Terse runtime refactor",
                "--select",
                "assurance_requirements,architecture_principles",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assurance = values["assurance_requirements"]
    subsystem = assurance["subsystem_assurance"]
    assert subsystem["matched_subsystem_ids"] == ["workspace-cli-runtime"]
    assert subsystem["matched_profiles"][0]["applies_because"] == ["changed path matched subsystem workspace-cli-runtime"]
    assert subsystem["missing_evidence"] == ["workspace_runtime_proof"]
    assert assurance["active"][0]["id"] == "subsystem:workspace-cli-runtime"
    assert assurance["active"][0]["proof_profile"] == "workspace_behavior"
    architecture = values["architecture_principles"]
    assert architecture["matched_count"] == 1
    assert architecture["matched_principles"][0]["matched_paths"] == [
        {
            "path": "src/agentic_workspace/workspace_runtime_core.py",
            "pattern": "src/agentic_workspace/workspace_runtime*.py",
        }
    ]


def test_assurance_reads_compact_evidence_records(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.runtime]
level = "high"
applies_to_paths = ["src/runtime.py"]
required_evidence = ["workspace_runtime_proof"]
force = "required-before-closeout"
blocking_claims = ["claim-work-complete"]
""",
    )
    _write(tmp_path / "src" / "runtime.py", "VALUE = 1\n")
    _write_json(
        tmp_path / ".agentic-workspace" / "verification" / "assurance-evidence-records.json",
        {
            "kind": "agentic-workspace/assurance-evidence-records/v1",
            "records": [
                {
                    "requirement_id": "runtime",
                    "evidence_label": "workspace_runtime_proof",
                    "status": "satisfied",
                    "source_kind": "command",
                    "command": "make test-workspace",
                    "changed_paths": ["src/runtime.py"],
                    "recorded_by": "agent",
                }
            ],
        },
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/runtime.py",
                "--select",
                "assurance_requirements",
                "--format",
                "json",
            ]
        )
        == 0
    )

    assurance = json.loads(capsys.readouterr().out)["values"]["assurance_requirements"]
    assert assurance["status"] == "matched"
    assert assurance["missing_required_evidence_count"] == 0
    assert assurance["evidence_status"][0]["state"] == "satisfied"
    assert assurance["evidence_status"][0]["evidence_present"] == ["workspace_runtime_proof"]
    assert assurance["evidence_records"]["status"] == "recorded"
    assert assurance["evidence_records"]["records"][0]["command"] == "make test-workspace"


def test_assurance_reports_activation_kinds_for_changed_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.mixed]
level = "medium"
applies_to_paths = ["src/**", "docs/**", "generated/**", "tests/**"]
required_evidence = ["reviewed"]
force = "recommended"
""",
    )
    _write(tmp_path / "src" / "runtime.py", "VALUE = 1\n")
    _write(tmp_path / "docs" / "runtime.md", "# Runtime\n")
    _write(tmp_path / "generated" / "workspace" / "python" / "cli.py", "# generated\n")
    _write(tmp_path / "tests" / "test_runtime.py", "def test_runtime():\n    assert True\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/runtime.py",
                "--changed",
                "docs/runtime.md",
                "--changed",
                "generated/workspace/python/cli.py",
                "--changed",
                "tests/test_runtime.py",
                "--select",
                "assurance_requirements",
                "--format",
                "json",
            ]
        )
        == 0
    )

    status = json.loads(capsys.readouterr().out)["values"]["assurance_requirements"]["evidence_status"][0]
    assert set(status["activation_kinds"]) == {
        "docs-manual-review",
        "generated-projection",
        "source-behavior",
        "test-evidence",
    }
    assert {item["path"] for item in status["activation_evidence"]} >= {
        "src/runtime.py",
        "docs/runtime.md",
        "generated/workspace/python/cli.py",
        "tests/test_runtime.py",
    }


def test_implement_ignores_subsystem_profile_not_declared_in_ownership(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "ordinary"
paths = ["src/audit/**"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.subsystem_profiles.audit-log]
assurance_level = "high"
required_evidence = ["manual_review"]
force = "required-before-closeout"
blocked_without_evidence = ["auditability-complete"]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/audit/events.py",
                "--select",
                "assurance_requirements",
                "--format",
                "json",
            ]
        )
        == 0
    )

    subsystem = json.loads(capsys.readouterr().out)["values"]["assurance_requirements"]["subsystem_assurance"]
    assert subsystem["status"] == "invalid-config"
    assert subsystem["configured_count"] == 1
    assert subsystem["active_configured_count"] == 0
    assert subsystem["invalid_profile_count"] == 1
    assert subsystem["invalid_profiles"][0]["id"] == "audit-log"
    assert subsystem["matched_count"] == 0
    assert subsystem["matched_subsystem_ids"] == []
    assert subsystem["missing_evidence"] == []
    assert "audit-log" in subsystem["warnings"][0]


def test_implement_composes_multiple_subsystem_assurance_profiles_conservatively(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "audit-log"
paths = ["src/shared/**"]

[[subsystems]]
id = "analytics"
paths = ["src/shared/**"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.subsystem_profiles.audit-log]
assurance_level = "critical"
required_evidence = ["tamper_review"]
force = "blocking"
blocked_without_evidence = ["security-complete"]

[assurance.subsystem_profiles.analytics]
assurance_level = "medium"
required_evidence = ["metric_review"]
force = "recommended"
blocked_without_evidence = ["analytics-complete"]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/shared/event.py",
                "--select",
                "assurance_requirements",
                "--format",
                "json",
            ]
        )
        == 0
    )

    subsystem = json.loads(capsys.readouterr().out)["values"]["assurance_requirements"]["subsystem_assurance"]
    assert subsystem["matched_subsystem_ids"] == ["analytics", "audit-log"]
    assert subsystem["effective_assurance_level"] == "critical"
    assert set(subsystem["missing_evidence"]) == {"metric_review", "tamper_review"}


def test_implement_reports_no_subsystem_profile_without_extra_burden(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "ordinary"
paths = ["src/ordinary/**"]
""",
    )
    _write(tmp_path / ".agentic-workspace/config.toml", "schema_version = 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/ordinary/model.py",
                "--select",
                "assurance_requirements",
                "--format",
                "json",
            ]
        )
        == 0
    )

    assurance = json.loads(capsys.readouterr().out)["values"]["assurance_requirements"]
    assert assurance["status"] == "absent"
    assert assurance["subsystem_assurance"]["status"] == "absent"


def test_implement_keeps_unmatched_assurance_requirements_out_of_tiny_output(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.privacy_data]
level = "high"
applies_to_paths = ["db/migrations/**"]
required_evidence = ["authority_consulted"]
force = "required-before-closeout"
""",
    )

    assert cli.main(["implement", "--target", str(tmp_path), "--changed", "README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "assurance_requirements" not in payload


def test_implement_routine_work_context_reports_memory_use_when_as_learned_evidence(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / ".agentic-workspace" / "memory" / "repo" / "index.md", "# Memory index\n")
    _write(tmp_path / ".agentic-workspace" / "memory" / "repo" / "domains" / "parser.md", "# Parser\n")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml",
        """
version = 1

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/parser.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/parser.md"
authority = "learned"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
use_when = ["parser refactor"]
evidence = ["Memory fixture"]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/parser.py",
                "--task",
                "Plan parser refactor safely",
                "--select",
                "routine_work_context",
                "--format",
                "json",
            ]
        )
        == 0
    )

    routine = json.loads(capsys.readouterr().out)["values"]["routine_work_context"]
    review = routine["knowledge_authority_review"]
    source = next(
        source for source in review["matched_sources"] if source["owner_surface"] == ".agentic-workspace/memory/repo/domains/parser.md"
    )
    assert source["owner_surface"] == ".agentic-workspace/memory/repo/domains/parser.md"
    assert source["authority"] == "learned"
    assert source["applies_because"] == ["task text matched parser refactor"]
    assert "Memory manifest metadata" in source["authority_boundary"]["observed_by_aw"]
    assert "semantically relevant" in source["authority_boundary"]["agent_owned_decisions"][0]
    assert "does not classify user intent" in source["authority_boundary"]["reporting_rule"]
    assert "does not make semantic task classifications" in review["authority_boundary"]["reporting_rule"]


def test_implement_verification_task_marker_reports_configured_protocol_authority(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "verification" / "manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[scenarios.privacy_walkthrough]
protocol_id = "privacy_review"
title = "Privacy walkthrough"
steps = ["Inspect privacy handling"]
expected_observations = ["Authority and evidence labels are visible"]
pass_evidence_labels = ["privacy_reviewed"]
fail_evidence_labels = ["privacy_gap"]

[protocols.privacy_review]
title = "Privacy review"
purpose = "Configured privacy verification protocol."
applies_to_task_markers = ["privacy"]
scenario_refs = ["privacy_walkthrough"]
expected_evidence = ["privacy_reviewed"]
review_owner = "privacy-review"
authority_refs = ["docs/compliance/privacy.md"]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Update privacy handling",
                "--select",
                "verification",
                "--format",
                "json",
            ]
        )
        == 0
    )

    verification = json.loads(capsys.readouterr().out)["values"]["verification"]
    protocol = verification["active_protocols"][0]
    assert protocol["id"] == "privacy_review"
    assert protocol["applies_because"] == ["task marker matched privacy"]
    assert "configured verification protocol privacy_review" in protocol["authority_boundary"]["observed_by_aw"]
    assert "semantically relevant" in protocol["authority_boundary"]["agent_owned_decisions"][0]
    assert "does not classify user intent" in protocol["authority_boundary"]["reporting_rule"]
    assert "does not decide the user's semantic intent" in verification["authority_boundary"]["reporting_rule"]


def test_implement_verification_surfaces_proof_governance_and_decision_status(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "verification" / "proof-decision.json",
        json.dumps(
            {
                "selected_decision": "prune",
                "trust_question": "Is the deleted regression knowledge preserved elsewhere?",
                "host_strategy_source": "docs/verification.md",
                "proof_owner": "verification-evidence",
                "proof_intent": "migration-residue",
                "evidence_durability": "temporary",
                "narrowest_evidence": "A retained conformance-owned scenario.",
                "prune_or_replacement_condition": "Equivalent coverage remains documented.",
                "confidence": "medium",
                "residual_risk": "Closeout still needs the agent's judgment.",
                "stale_when": ["tests/**"],
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "tests/test_removed_regression.py",
                "--task",
                "Remove legacy regression test",
                "--select",
                "verification",
                "--format",
                "json",
            ]
        )
        == 0
    )

    verification = json.loads(capsys.readouterr().out)["values"]["verification"]
    strategy = verification["evidence_strategy"]
    assert strategy["proof_governance"]["decision_authority"] == "agent"
    assert strategy["proof_decision"]["status"] == "present"
    assert strategy["proof_decision"]["lifecycle"]["state"] == "stale"
    assert strategy["regression_sprawl"]["proof_decision_status"] == "present"
    assert strategy["regression_sprawl"]["missing_or_incomplete_proof_decision"] is False
    assert strategy["regression_sprawl"]["deleted_or_missing_test_files"] == ["tests/test_removed_regression.py"]


def test_implement_matches_non_code_assurance_requirement(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.runbook_change]
level = "medium"
applies_to_paths = ["docs/runbooks/**"]
authority_refs = ["docs/ops/runbook-authority.md"]
required_evidence = ["operator_review"]
force = "recommended"
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/runbooks/restart-service.md",
                "--select",
                "assurance_requirements",
                "--format",
                "json",
            ]
        )
        == 0
    )

    requirements = json.loads(capsys.readouterr().out)["values"]["assurance_requirements"]
    assert requirements["active"][0]["id"] == "runbook_change"
    assert requirements["active"][0]["authority_refs"] == ["docs/ops/runbook-authority.md"]
    assert requirements["evidence_status"][0]["missing_evidence"] == ["operator_review"]


def test_implement_planning_source_includes_typecheck_ci_parity(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / "Makefile",
        "test-planning:\n\tpytest packages/planning/tests\n\n"
        "lint-planning:\n\truff check packages/planning\n\n"
        "typecheck-planning:\n\tmypy packages/planning/src\n",
    )

    assert (
        cli.main(
            [
                "implement",
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

    payload = json.loads(capsys.readouterr().out)
    assert payload["proof"]["required_commands"] == [
        "make test-planning",
        "make lint-planning",
        "make typecheck-planning",
    ]
    assert payload["next"]["commands"] == [
        "make test-planning",
        "make lint-planning",
        "make typecheck-planning",
    ]


def test_implement_groups_generated_reuse_pressure_under_source_owner(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "generated" / "workspace" / "python" / "command_package.json", "{}")
    _write(tmp_path / "generated" / "workspace" / "python" / "adapter_commands.json", "{}")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/command_package.json",
                "generated/workspace/python/adapter_commands.json",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    aggregation = payload["generated_artifact_aggregation"]
    assert aggregation["status"] == "present"
    assert aggregation["owner_group_count"] == 1
    finding = aggregation["findings"][0]
    assert finding["kind"] == "generated_artifact_source_owner"
    assert finding["changed_path"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert finding["generated_artifact_count"] == 2
    assert [item["kind"] for item in payload["findings"]] == ["generated_artifact_source_owner"]


def test_implement_compact_reuse_pressure_collapses_large_generated_file_sets(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    changed_paths = [f"generated/workspace/typescript/resources/operations/generated-{index}.json" for index in range(12)]

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                *changed_paths,
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    reuse_pressure = payload["values"]["reuse_pressure"]
    route_command = reuse_pressure["memory_signals"]["route_command"]
    assert "--target ." in route_command
    assert "<collapsed-changed-paths>" in route_command
    assert changed_paths[-1] not in route_command
    summary = reuse_pressure["memory_signals"]["path_argument_summary"]
    assert summary["status"] == "collapsed"
    assert summary["generated_groups"] == [{"root": "generated/workspace/typescript/resources", "count": 12}]
    assert reuse_pressure["recording_options"]["path_argument_summary"]["status"] == "collapsed"

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                *changed_paths,
                "--verbose",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )
    verbose_reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert changed_paths[-1] in verbose_reuse_pressure["memory_signals"]["route_command"]
    assert "<collapsed-changed-paths>" not in verbose_reuse_pressure["memory_signals"]["route_command"]


def test_implement_selector_surfaces_changed_path_impact_map(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        "schema_version = 1\n\n"
        "[[authority_surfaces]]\n"
        'concern = "startup-instructions"\n'
        'surface = "AGENTS.md"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "startup"\n\n'
        "[[module_roots]]\n"
        'module = "planning"\n'
        'path = ".agentic-workspace/planning/"\n'
        'ownership = "module_managed"\n'
        'uninstall_policy = "remove-managed-files-only"\n\n'
        "[[subsystems]]\n"
        'id = "workspace-runtime"\n'
        'paths = ["src/agentic_workspace/**"]\n'
        'owns = ["workspace runtime behavior"]\n'
        'does_not_own = ["planning state semantics"]\n'
        'proof = ["uv run pytest tests/test_workspace_implement_cli.py -q"]\n'
        'escalate_when = ["runtime contract changes"]\n',
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "generated/workspace/python/command_package.json",
                ".agentic-workspace/planning/state.toml",
                "scratch/unknown.adapter",
                "--select",
                "change_impact",
                "--format",
                "json",
            ]
        )
        == 0
    )

    impact = json.loads(capsys.readouterr().out)["values"]["change_impact"]
    by_path = {item["path"]: item for item in impact["paths"]}
    source = by_path["src/agentic_workspace/workspace_runtime_primitives.py"]
    assert source["owner"] == "subsystem:workspace-runtime"
    assert source["surface_origin"] == "source-authored"
    assert source["optimization_posture"]["status"] == "active"
    assert source["optimization_posture"]["exempt_from_optimization_pressure"] is False
    assert source["optimization_posture"]["audience"] == "unknown"
    assert source["optimization_posture"]["source_route"] == "direct"
    assert source["optimization_posture"]["effective_target"] == "balanced"
    assert source["optimization_posture"]["effective_optimization_bias"] == "balanced"
    assert "Subsystem-owned implementation surface" in source["optimization_posture"]["review_guidance"]
    assert source["related"]["subsystems"][0]["id"] == "workspace-runtime"
    assert "subsystem:workspace-runtime" in source["related"]["proof_lanes"]

    generated = by_path["generated/workspace/python/command_package.json"]
    assert generated["surface_origin"] == "generated"
    assert generated["optimization_posture"]["status"] == "owner-boundary"
    assert generated["optimization_posture"]["source_route"] == "source-or-owner-first"
    assert generated["signal"] == "hard_blocker"
    assert generated["safe_to_edit"] is False
    assert generated["canonical_source"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert generated["refresh_command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert "cli_authority" in generated["related"]["proof_lanes"]

    managed = by_path[".agentic-workspace/planning/state.toml"]
    assert managed["owner"] == "planning"
    assert managed["surface_origin"] == "managed"
    assert managed["matched_by"] == "module_root"
    assert managed["optimization_posture"]["status"] == "owner-boundary"
    assert managed["optimization_posture"]["source_route"] == "source-or-owner-first"
    assert managed["signal"] == "warning"
    assert managed["safe_to_edit"] is True
    assert any("command-owned mutation" in warning for warning in managed["warnings"])

    unknown = by_path["scratch/unknown.adapter"]
    assert unknown["owner"] == "unknown"
    assert unknown["ownership_matched"] is False
    assert unknown["signal"] == "warning"
    assert "No explicit ownership ledger match" in unknown["warnings"][0]
    assert unknown["optimization_posture"]["status"] == "active"
    assert unknown["optimization_posture"]["optimization_bias"] == "balanced"
    assert unknown["optimization_posture"]["audience"] == "unknown"
    assert unknown["optimization_posture"]["effective_target"] == "balanced"

    assert impact["generated_path_count"] == 1
    assert impact["managed_path_count"] == 1
    assert impact["unknown_path_count"] == 1
    assert impact["hard_blocker_count"] == 1
    assert impact["optimization_posture"]["source_routed_path_count"] == 2
    assert impact["proof_impact"]["required_commands"]


def test_implement_change_impact_routes_optimization_posture_by_audience_boundary(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[workspace]
improvement_latitude = "proactive"
optimization_bias = "agent-efficiency"
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[authority_surfaces]]
concern = "human-authored-plan"
surface = "strategy/human-plan.md"
owner = "human"
ownership = "repo_owned"
authority = "primary"
summary = "Human-owned strategy surface."

[[authority_surfaces]]
concern = "agent-runbook"
surface = "agent/runbook.md"
owner = "agent"
ownership = "repo_owned"
authority = "primary"
summary = "Agent-owned runbook surface."

[[authority_surfaces]]
concern = "machine-contract"
surface = "contracts/schema.json"
owner = "machine"
ownership = "repo_owned"
authority = "primary"
summary = "Machine-consumed contract surface."

[[authority_surfaces]]
concern = "mixed-runbook"
surface = "docs/mixed.md"
owner = "human+agent"
ownership = "repo_owned"
authority = "primary"
summary = "Mixed-audience documentation surface."

[[authority_surfaces]]
concern = "human-owned-agent-aid"
surface = "aids/agent.md"
owner = "human"
audience = "agent"
ownership = "repo_owned"
authority = "primary"
summary = "Human-owned surface intended for agent consumption."
""",
    )
    _write(tmp_path / "src" / "feature.py", "VALUE = 1\n")
    _write(tmp_path / "strategy" / "human-plan.md", "# Strategy\n")
    _write(tmp_path / "agent" / "runbook.md", "# Runbook\n")
    _write(tmp_path / "contracts" / "schema.json", "{}\n")
    _write(tmp_path / "docs" / "mixed.md", "# Mixed\n")
    _write(tmp_path / "aids" / "agent.md", "# Agent aid\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/feature.py",
                "strategy/human-plan.md",
                "agent/runbook.md",
                "contracts/schema.json",
                "docs/mixed.md",
                "aids/agent.md",
                "--select",
                "change_impact",
                "--format",
                "json",
            ]
        )
        == 0
    )

    impact = json.loads(capsys.readouterr().out)["values"]["change_impact"]
    assert impact["optimization_posture"]["status"] == "review-required"
    assert impact["optimization_posture"]["active_path_count"] == 5
    assert impact["optimization_posture"]["owner_boundary_path_count"] == 0
    assert impact["optimization_posture"]["review_required_path_count"] == 1
    assert impact["optimization_posture"]["audience_override_count"] == 5
    assert impact["optimization_posture"]["effective_target"] == "mixed"
    assert impact["optimization_posture"]["review_required"] is True
    by_path = {item["path"]: item for item in impact["paths"]}
    source_posture = by_path["src/feature.py"]["optimization_posture"]
    assert source_posture["status"] == "active"
    assert source_posture["improvement_latitude"] == "proactive"
    assert source_posture["optimization_bias"] == "agent-efficiency"
    assert source_posture["effective_optimization_bias"] == "agent-efficiency"
    assert source_posture["audience"] == "unknown"
    assert source_posture["effective_target"] == "agent-efficiency"
    assert "agent-efficiency" in source_posture["signals"]
    human_posture = by_path["strategy/human-plan.md"]["optimization_posture"]
    assert human_posture["status"] == "active"
    assert human_posture["exempt_from_optimization_pressure"] is False
    assert human_posture["owner"] == "human"
    assert human_posture["audience"] == "human"
    assert human_posture["audience_source"] == "owner-inferred"
    assert human_posture["effective_target"] == "human-readability-control-review"
    assert human_posture["effective_optimization_bias"] == "human-readability-control-review"
    assert "human-readability" in human_posture["signals"]
    agent_posture = by_path["agent/runbook.md"]["optimization_posture"]
    assert agent_posture["status"] == "active"
    assert agent_posture["exempt_from_optimization_pressure"] is False
    assert agent_posture["owner"] == "agent"
    assert agent_posture["audience"] == "agent"
    assert agent_posture["audience_source"] == "owner-inferred"
    assert agent_posture["effective_target"] == "agent-efficiency"
    assert agent_posture["effective_optimization_bias"] == "agent-efficiency"
    assert "machine-readable-structure" in agent_posture["signals"]
    machine_posture = by_path["contracts/schema.json"]["optimization_posture"]
    assert machine_posture["status"] == "active"
    assert machine_posture["audience"] == "machine"
    assert machine_posture["audience_source"] == "owner-inferred"
    assert machine_posture["effective_target"] == "stable-contract-validation"
    assert "stable-contract" in machine_posture["signals"]
    mixed_posture = by_path["docs/mixed.md"]["optimization_posture"]
    assert mixed_posture["status"] == "review-required"
    assert mixed_posture["audience"] == "mixed"
    assert mixed_posture["audience_source"] == "owner-inferred"
    assert mixed_posture["effective_target"] == "mixed-audience-review"
    assert "tradeoff-review" in mixed_posture["signals"]
    explicit_agent_posture = by_path["aids/agent.md"]["optimization_posture"]
    assert explicit_agent_posture["status"] == "active"
    assert explicit_agent_posture["owner"] == "human"
    assert explicit_agent_posture["audience"] == "agent"
    assert explicit_agent_posture["audience_source"] == "explicit"
    assert explicit_agent_posture["effective_target"] == "agent-efficiency"
    assert "agent-efficiency" in explicit_agent_posture["signals"]


def test_implement_selector_surfaces_generated_surface_trust(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json", "{}")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/command_package.json",
                "--select",
                "generated_surface_trust",
                "--format",
                "json",
            ]
        )
        == 0
    )

    trust = json.loads(capsys.readouterr().out)["values"]["generated_surface_trust"]
    assert trust["kind"] == "agentic-workspace/generated-surface-trust/v1"
    assert trust["status"] == "present"
    assert trust["changed_path_count"] == 1
    assert trust["rule"].startswith("Generated surfaces are derived artifacts")
    item = trust["items"][0]
    assert item["path"] == "generated/workspace/python/command_package.json"
    assert item["classification_id"] == "generated-command-package-output"
    assert item["role"] == "projection"
    assert item["canonical_source"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert item["canonical_source_status"] == "present"
    assert item["freshness_status"] == "validation-required"
    assert item["refresh_command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert item["validation_command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert item["direct_edit_allowed"] is False
    assert "Do not hand-edit generated command package outputs" in item["direct_edit_policy"]
    assert item["action_effect"]["force"] == "required_before_claim"
    assert item["action_effect"]["resolution_command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert item["action_effect"]["resolution_commands"] == ["uv run python scripts/check/check_generated_command_packages.py"]
    assert trust["action_effect"]["resolution_commands"] == ["uv run python scripts/check/check_generated_command_packages.py"]


def test_implement_readme_change_omits_generated_cli_freshness(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "README.md", "hello\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Update README wording",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "generated_cli_freshness" not in payload["proof"]
    assert all("generated_cli_freshness" not in signal for signal in payload["action_signals"]["changed_signals"])
    assert payload["context"]["generated_surface_trust"]["status"] == "not-applicable"
    assert payload["context"]["generated_surface_trust"]["action_effect"]["force"] == "advisory"


def test_implement_selector_surfaces_task_contract_view(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "Makefile", "test-workspace:\n\tpytest tests\n\nlint-workspace:\n\truff check src tests\n")
    _write(tmp_path / ".agentic-workspace" / "docs" / "guide.md", "# Guide\n")
    _write(tmp_path / "packages" / "planning" / "README.md", "# Planning\n")
    _write(tmp_path / "packages" / "memory" / "README.md", "# Memory\n")
    _write(tmp_path / "README.md", "hello\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Update README wording",
                "--select",
                "task_contract",
                "--format",
                "json",
            ]
        )
        == 0
    )

    contract = json.loads(capsys.readouterr().out)["values"]["task_contract"]
    assert contract["kind"] == "agentic-workspace/task-contract/v1"
    assert contract["status"] == "present"
    assert contract["authority"] == "assembled-view"
    assert contract["changed_paths"] == ["README.md"]
    assert "task_intent" in contract["source_fields"]
    assert contract["intent"]["status"] == "present"
    assert contract["intent"]["missing_fields"] == []
    assert contract["acceptance"]["closeout_required"] is True
    assert contract["acceptance"]["item_count"] == 3
    assert contract["autonomy_and_escalation"]["recommended_route"] in {
        "execute-locally",
        "stay-local",
        "suggest-delegation",
        "manual-handoff",
        "clarify-first",
    }
    assert contract["proof_expectations"]["status"] == "present"
    assert contract["proof_expectations"]["required_commands"]
    assert contract["proof_expectations"]["intent_proof_status"] in {"prompt-required", "needs-agent-judgment"}
    assert contract["stop_conditions"]["status"] == "present"
    assert "proof.escalate_when" in contract["stop_conditions"]["source_fields"]


def test_implement_task_contract_names_missing_task_inputs(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "Makefile", "test-workspace:\n\tpytest tests\n\nlint-workspace:\n\truff check src tests\n")
    _write(tmp_path / ".agentic-workspace" / "docs" / "guide.md", "# Guide\n")
    _write(tmp_path / "packages" / "planning" / "README.md", "# Planning\n")
    _write(tmp_path / "packages" / "memory" / "README.md", "# Memory\n")
    _write(tmp_path / "README.md", "hello\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--select",
                "task_contract",
                "--format",
                "json",
            ]
        )
        == 0
    )

    contract = json.loads(capsys.readouterr().out)["values"]["task_contract"]
    assert contract["status"] == "present-with-gaps"
    assert contract["intent"]["status"] == "absent"
    assert contract["intent"]["missing_fields"] == ["task_intent.task_text"]
    assert "task_intent.task_text" in contract["missing_fields"]
    assert "acceptance.items" in contract["missing_fields"]
    assert contract["proof_expectations"]["status"] == "present"
    assert contract["changed_paths"] == ["README.md"]


def test_implement_selector_surfaces_routine_work_context(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.docs_review]
level = "medium"
applies_to_paths = ["docs/**"]
required_evidence = ["reviewed_docs_authority"]
force = "required-before-closeout"
""",
    )
    _write(tmp_path / "docs" / "guide.md", "hello\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/guide.md",
                "--select",
                "routine_work_context",
                "--format",
                "json",
            ]
        )
        == 0
    )

    routine = json.loads(capsys.readouterr().out)["values"]["routine_work_context"]
    assert routine["surface"] == "implement"
    assert routine["categories"]["authority"]["signals"]["active_assurance_requirements"] == 1
    assert routine["categories"]["evidence_proof"]["signals"]["missing_required_assurance_evidence"] == 1
    assert routine["activation"]["small_work_rule"].startswith("If no category is attention")


def test_implement_separates_required_proof_from_recommended_confidence_checks(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / "Makefile",
        (
            "test-planning:\n\tpytest packages/planning/tests\n\n"
            "lint-planning:\n\truff check packages/planning\n\n"
            "typecheck-planning:\n\tpyright packages/planning\n\n"
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "--task",
                "Update planning package installer",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    proof = payload["proof"]
    obligations = proof["proof_obligations"]
    adequacy = proof["proof_adequacy"]
    assert "make test-planning" in proof["required_commands"]
    assert "make lint-planning" in proof["required_commands"]
    assert "make typecheck-planning" in proof["required_commands"]
    assert obligations["required_proof"]["commands"] == proof["required_commands"]
    assert obligations["recommended_confidence_checks"]["commands"] == proof["optional_commands"]
    assert obligations["recommended_confidence_checks"]["commands"] != proof["required_commands"]
    assert obligations["agent_selected_extra_validation"]["status"] == "agent-owned"
    assert "Completion claims remain blocked" in obligations["completion_claim_rule"]
    assert adequacy["protocol"] == "Proof Adequacy"
    assert adequacy["required_evidence"]["commands"] == proof["required_commands"]
    assert "completion permission without closeout" in adequacy["claim_boundary"]["does_not_authorize"]
    assert "semantic intent satisfaction" in adequacy["claim_boundary"]["does_not_authorize"]
    assert payload["required_validation_commands"] == proof["required_commands"]


def test_implement_routine_context_surfaces_memory_freshness_and_promotion_pressure(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / ".agentic-workspace" / "memory" / "repo" / "domains" / "token-policy.md", "# Token policy\n")
    _write(
        target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml",
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/token-policy.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/token-policy.md"
authority = "advisory"
audience = "human+agent"
canonicality = "candidate_for_promotion"
task_relevance = "required"
subsystems = ["auth"]
surfaces = ["token"]
routes_from = ["src/auth/**"]
stale_when = ["src/auth/**"]
evidence = ["docs/security/token-policy.md"]
memory_role = "improvement_signal"
promotion_target = "assurance.requirements.token_policy"
promotion_trigger = "Promote when token handling is next touched."
preferred_remediation = "validation"
improvement_note = "Create a reusable token-policy assurance gate."
elimination_target = "promote"
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(target),
                "--changed",
                "src/auth/token.py",
                "--task",
                "Update token handling",
                "--select",
                "routine_work_context",
                "--format",
                "json",
            ]
        )
        == 0
    )

    routine = json.loads(capsys.readouterr().out)["values"]["routine_work_context"]
    review = routine["knowledge_authority_review"]
    assert review["status"] == "attention"
    assert review["stale_source_count"] == 1
    assert review["promotion_candidate_count"] == 1
    assert routine["categories"]["durable_knowledge"]["status"] == "attention"
    assert routine["categories"]["promotion_residue"]["status"] == "attention"
    source = review["matched_sources"][0]
    assert source["owner_surface"] == ".agentic-workspace/memory/repo/domains/token-policy.md"
    assert source["freshness"]["status"] == "needs-review"
    assert source["promotion_pressure"]["target"] == "assurance.requirements.token_policy"
    assert "route promotion or dismissal during closeout" in source["claim_effect"]["advises"]


def test_implement_tiny_profile_does_not_compute_deferred_diagnostics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    scenarios = [
        ("change_impact", "_change_impact_payload", False, []),
        ("task_contract", "_task_contract_payload", True, ["task_contract"]),
        ("routine_work_context", "_routine_work_context_payload", False, ["routine_work_context"]),
        ("assurance_requirements", "_assurance_requirements_report_payload", True, ["assurance_requirements"]),
    ]
    for field, helper_name, include_task, expected_selectors in scenarios:
        repo = tmp_path / field
        repo.mkdir()
        _init_git_repo(repo)
        _write_empty_planning_state(repo)
        if field == "assurance_requirements":
            _write(
                repo / ".agentic-workspace/config.toml",
                """
schema_version = 1

[assurance.requirements.docs_review]
level = "high"
applies_to_paths = ["docs/**"]
required_evidence = ["review_recorded"]
force = "required-before-closeout"
blocking_claims = ["claim-work-complete"]
""",
            )
        _write(repo / "README.md", "hello\n")

        def fail_deferred_helper(**_: object) -> dict[str, object]:
            raise AssertionError(f"ordinary tiny implement output should not build {field}")

        monkeypatch.setattr(cli, helper_name, fail_deferred_helper)
        args = ["implement", "--target", str(repo), "--changed", "README.md"]
        if include_task:
            args.extend(["--task", "Update README wording"])
        args.extend(["--format", "json"])

        assert cli.main(args) == 0, field

        payload = json.loads(capsys.readouterr().out)
        assert payload["kind"] == "implementer-context-tiny/v1", field
        assert field not in payload, field
        assert field not in payload["context"], field
        for selector in expected_selectors:
            assert selector in payload["drill_down"]["available_selectors"], field


def test_implement_default_stays_under_tiny_output_budget_for_docs_task(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "Makefile", "test-workspace:\n\tpytest tests\n\nlint-workspace:\n\truff check src tests\n")
    _write(tmp_path / ".agentic-workspace" / "docs" / "guide.md", "# Guide\n")
    _write(tmp_path / "packages" / "planning" / "README.md", "# Planning\n")
    _write(tmp_path / "packages" / "memory" / "README.md", "# Memory\n")
    _write(tmp_path / "README.md", "hello\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Fix one docs typo",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    _assert_json_payload_under(payload, 13_000, label="implement tiny docs-task payload", sort_keys=False)
    assert payload["kind"] == "implementer-context-tiny/v1"
    assert payload["next"]["action"]
    assert payload["proof"]["required_commands"]
    assert payload["proof"]["proof_obligations"]["required_proof"]["status"] == "required"
    assert payload["operating_loop"]["closeout_state"] == "blocked_missing_proof"
    assert payload["operating_loop"]["verification"]["state"] == "proof_missing"
    assert payload["memory_decision_packet"]["label"] == "knowledge"
    assert payload["memory_decision_packet"]["provenance"] == "memory"
    planning_gate = payload["context"]["planning_safety_gate"]
    assert planning_gate["label"] == "work gate"
    assert planning_gate["provenance"] == "planning"
    assert planning_gate["status"] == "clear"
    assert planning_gate["required_next_action"] == "continue-direct"
    assert "changed_path_facts" not in planning_gate
    assert "reason" not in planning_gate
    assert "promotion_command" not in planning_gate
    assert "active_plan_reliance" not in planning_gate
    assert "change_impact" not in payload
    assert "routine_work_context" not in payload
    assert "generated_surface_trust" not in payload
    assert "change_impact" in payload["drill_down"]["available_selectors"]
    assert "routine_work_context" in payload["drill_down"]["available_selectors"]
    assert "generated_surface_trust" in payload["drill_down"]["available_selectors"]


def test_implement_default_stays_under_tiny_output_budget_for_code_task(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "app.py", "print('hello')\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/app.py",
                "--task",
                "Fix one code path",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    _assert_json_payload_under(payload, 12_000, label="implement tiny code-task payload", sort_keys=False)
    assert payload["kind"] == "implementer-context-tiny/v1"
    assert payload["next"]["action"]
    assert payload["proof"]["proof_obligations"]["required_proof"]["status"] == "required"
    assert payload["proof"]["proof_obligations"]["required_proof"]["manual_verification_required"] is True
    assert payload["operating_loop"]["closeout_state"] == "blocked_missing_proof"
    assert payload["operating_loop"]["verification"]["state"] == "proof_missing"
    assert payload["context"]["optimization_posture"] == {
        "status": "active",
        "effective_target": "balanced",
        "configured_posture": "conservative/balanced",
    }
    planning_gate = payload["context"]["planning_safety_gate"]
    assert planning_gate["label"] == "work gate"
    assert planning_gate["provenance"] == "planning"
    assert planning_gate["status"] == "clear"
    assert planning_gate["required_next_action"] == "continue-direct"
    assert "changed_path_facts" not in planning_gate
    assert "reason" not in planning_gate
    assert "promotion_command" not in planning_gate
    assert "active_plan_reliance" not in planning_gate
    assert "change_impact" not in payload
    assert "routine_work_context" not in payload
    assert "generated_surface_trust" not in payload
    assert "change_impact" in payload["drill_down"]["available_selectors"]
    assert "routine_work_context" in payload["drill_down"]["available_selectors"]
    assert "generated_surface_trust" in payload["drill_down"]["available_selectors"]


def test_implement_tiny_profile_surfaces_manual_verification_obligations(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/verification/manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[protocols.policy_review]
title = "Policy review"
purpose = "Manual policy proof for sensitive changes."
applies_to_paths = ["privacy/**"]
expected_evidence = ["manual_policy_review"]
review_owner = "policy-review"
authority_refs = ["docs/policy.md#rule-1"]
steps = ["Read policy rule 1", "Compare the changed output"]
review_aids = ["Record the manual policy finding."]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "privacy/export.txt",
                "--task",
                "Update the privacy export",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    required = payload["proof"]["proof_obligations"]["required_proof"]
    assert required["manual_verification_required"] is True
    assert required["manual_obligation_count"] == 1
    assert required["manual_obligations"][0]["id"] == "verification:policy_review"
    assert required["manual_obligations"][0]["missing_evidence"] == ["manual_policy_review"]
    assert required["manual_obligations"][0]["reference_material"] == ["docs/policy.md#rule-1"]
    assert payload["proof"]["proof_route_maintenance"]["status"] == "attention"


def test_implement_tiny_profile_defers_reuse_pressure_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "README.md", "hello\n")

    def fail_reuse_pressure(**_: object) -> dict[str, object]:
        raise AssertionError("ordinary tiny implement output should not scan reuse pressure")

    monkeypatch.setattr(cli, "_reuse_pressure_payload", fail_reuse_pressure)

    assert cli.main(["implement", "--target", str(tmp_path), "--changed", "README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["context"]["reuse_pressure"]["status"] == "deferred"
    assert payload["context"]["reuse_pressure"]["detail_selector"] == "reuse_pressure"
    assert "reuse_pressure" in payload["drill_down"]["available_selectors"]


def test_implement_tiny_profile_returns_next_decision_without_diagnostics(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "Makefile", "test-workspace:\n\tpytest tests\n\nlint-workspace:\n\truff check src tests\n")
    _write(tmp_path / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json", "{}")
    _write(
        tmp_path / "tests" / "test_workspace_proof_generated_packages_cli.py",
        "def test_generated_package_fixture():\n    assert True\n",
    )
    _write(tmp_path / "scripts" / "check" / "check_generated_command_packages.py", "print('ok')\n")
    _write(tmp_path / "scripts" / "check" / "run_operation_conformance_tests.py", "print('ok')\n")

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
    assert payload["kind"] == "implementer-context-tiny/v1"
    assert set(payload) <= {
        "kind",
        "target",
        "communication_contract",
        "action_signals",
        "decision_packet",
        "next",
        "proof",
        "generated_surface_trust",
        "memory_decision_packet",
        "operating_loop",
        "reuse_pressure",
        "context",
        "drill_down",
    }
    signals = payload["action_signals"]
    decision = payload["decision_packet"]
    assert decision["surface"] == "implement"
    assert decision["phase_question"] == "What narrow working set is safe to touch now?"
    assert decision["next_action"] == payload["next"]["action"]
    assert decision["absence_states"]["full_selector_inventory"] == "hidden_behind_detail_route"
    assert signals["kind"] == "agentic-workspace/action-signals/v1"
    assert signals["order"] == [
        "hard_blockers",
        "allowed_next_action",
        "proof_required",
        "changed_signals",
        "advisory_detail",
        "agent_judgment",
    ]
    assert signals["allowed_next_action"] == payload["next"]["action"]
    assert signals["proof_required"] is True
    assert signals["proof_commands"] == payload["proof"]["required_commands"]
    assert "generated_surface_trust=present" in signals["changed_signals"]
    assert "generated_cli_freshness=required" in signals["changed_signals"]
    assert "context.reuse_pressure" in signals["advisory_detail"]["selectors"]
    assert context["absence_states"]["adaptive_routing"] == "detail_omitted"
    assert context["absence_states"]["work_shape_guidance"] == "detail_omitted"
    assert "context.guidance" in payload["drill_down"]["available_selectors"]
    assert payload["next"]["action"] == "Inspect only the listed files and run the required validation commands."
    assert payload["next"]["command"] == "make test-workspace"
    assert payload["next"]["run"] == payload["next"]["command"]
    assert "make lint-workspace" in payload["next"]["commands"]
    assert context["scope"]["inspect_files"] == ["generated/workspace/python/cli.py"]
    assert "make test-workspace" in payload["proof"]["required_commands"]
    assert "uv run python scripts/check/check_generated_command_packages.py" in payload["proof"]["required_commands"]
    assert payload["proof"]["generated_cli_freshness"]["status"] == "required"
    assert payload["proof"]["generated_cli_freshness"]["refresh_command"] == "uv run python scripts/generate/generate_command_packages.py"
    assert payload["proof"]["generated_cli_freshness"]["generated_target_parity"]["target_families"] == ["python", "typescript"]
    assert "Python-only proof" in payload["proof"]["generated_cli_freshness"]["generated_target_parity"]["claim_rule"]
    obligations = payload["proof"]["proof_obligations"]
    assert obligations["required_proof"]["commands"] == payload["proof"]["required_commands"]
    assert obligations["required_proof"]["action_effect"]["force"] == "required_before_claim"
    assert obligations["required_proof"]["action_effect"]["blocked_until_reconciled"] == ["claim-task-complete"]
    assert obligations["required_proof"]["action_effect"]["resolution_selector"] == "proof.proof_obligations.required_proof"
    assert obligations["recommended_confidence_checks"]["status"] == "available"
    assert "do not replace or relax required proof" in obligations["recommended_confidence_checks"]["rule"]
    assert "Completion claims remain blocked" in obligations["completion_claim_rule"]
    trust = payload["generated_surface_trust"]
    assert trust["status"] == "present"
    assert trust["items"][0]["path"] == "generated/workspace/python/cli.py"
    assert trust["items"][0]["canonical_source"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert trust["items"][0]["direct_edit_allowed"] is False
    assert context["generated_surface_trust"] == {
        "status": "present",
        "changed_path_count": 1,
        "action_effect": trust["action_effect"],
        "detail_selector": "generated_surface_trust",
    }
    assert context["generated_surface_trust"]["action_effect"]["force"] == "required_before_claim"
    assert payload["proof"]["acceptance_guidance"]["status"] == "present"
    assert "guidance" not in context
    assert "intent_acknowledgement" not in context
    intent_evidence = context["intent_evidence"]
    assert intent_evidence["source_class"] == "direct-user-text"
    assert intent_evidence["assumption_state"] == "low-risk-direct"
    assert intent_evidence["required_next_action"] == "continue-direct"
    assert intent_evidence["proceed_without_question"] is True
    assert context["delegation_decision"]["status"] == "evaluated"
    assert context["delegation_decision"]["mode"] in {"suggest", "auto"}
    delegation_boundary = context["delegation_decision"]["authority_boundary"]
    assert delegation_boundary["surface"] == "delegation_decision"
    assert "delegation fit without lowering proof" in delegation_boundary["agent_owned_decisions"]
    assert context["acceptance_reconciliation"]["task_text_available"] is True
    assert context["acceptance"]["status"] == "inferred"
    assert context["acceptance"]["closeout_required"] is True
    assert context["objective_drift"]["status"] in {"clear", "not-enough-explicit-outcomes"}
    assert "package_boundary" not in payload
    assert "authority_markers" not in payload
    assert "durable_intent" not in payload
    assert "inference_limits" not in payload
    assert "generated_surface_trust" in payload["drill_down"]["available_selectors"]
    _assert_json_payload_under(
        payload["generated_surface_trust"],
        700,
        label="implement generated-surface trust compact projection",
        sort_keys=False,
    )
    _assert_json_payload_under(payload["operating_loop"], 1000, label="implement operating-loop compact projection", sort_keys=False)
    _assert_json_payload_under(payload, 18000, label="implement generated-surface tiny payload", sort_keys=False)


def test_implement_surfaces_runtime_source_edit_review_for_generated_cli_boundary(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "Makefile", "test-workspace:\n\tpytest tests\n\nlint-workspace:\n\truff check src tests\n")
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Fix an existing primitive bug under the generated CLI boundary.",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["proof"]["runtime_source_edit_review"]
    assert review["kind"] == "agentic-workspace/runtime-source-edit-review/v1"
    assert review["status"] == "classification-required"
    assert review["changed_paths"] == ["src/agentic_workspace/workspace_runtime_primitives.py"]
    assert review["inventory_source"] == "src/agentic_workspace/contracts/python_runtime_projection_inventory.json"
    assert review["missing_inventory_paths"] == []
    assert review["review_items"][0]["changed_path"] == "src/agentic_workspace/workspace_runtime_primitives.py"
    assert review["review_items"][0]["status"] == "inventory-backed"
    assert review["review_items"][0]["accepted_runtime_symbol_count"] > 0
    accepted_symbol = review["review_items"][0]["sample_accepted_runtime_symbols"][0]
    assert accepted_symbol["source_module"] == "agentic_workspace.workspace_runtime_primitives"
    assert accepted_symbol["source_symbol"]
    assert accepted_symbol["primitive_refs"]
    assert accepted_symbol["direct_edit_reasons_allowed"] == ["existing-primitive-bugfix", "new-primitive-implementation"]
    assert review["accepted_direct_edit_reasons"] == ["existing-primitive-bugfix", "new-primitive-implementation"]
    assert "package-domain boundary" in review["rejected_vague_reasons"]
    assert "inventory-backed symbol/primitive" in review["completion_claim_rule"]
    assert "mirror_drift_review" not in review
    assert "proof.runtime_source_edit_review" in payload["drill_down"]["available_selectors"]


_RUNTIME_MIRROR_CONTRACT_SNIPPET = """
def _planning_candidate_suggestions_from_external_items():
    return {"candidates": []}


def _external_issue_grouping_hints():
    return {"kind": "external-issue-grouping-hints/v1", "status": "present"}


def _toml_inline_string(value):
    return value


def _planning_candidate_toml_row(candidate):
    return ""


def _append_planning_candidate_rows():
    return {"status": "applied"}


def _candidate_refs(candidate):
    return set()


def _candidate_has_local_continuation(candidate):
    return False


def _stale_planning_candidate_reconciliation():
    return {"status": "no-stale-candidates"}


def _refresh_github_external_intent_evidence():
    planning_candidate_grouping = _external_issue_grouping_hints()
    return {"planning_candidate_grouping": planning_candidate_grouping}


def _open_issue_intake_payload():
    grouping = _external_issue_grouping_hints()
    return {"grouping_hints": grouping}


def _unrelated_runtime_helper():
    return "old"
"""


def _seed_runtime_mirror_contract_repo(target_root: Path) -> None:
    _write_empty_planning_state(target_root)
    _write(target_root / "src" / "agentic_workspace" / "workspace_runtime_core.py", _RUNTIME_MIRROR_CONTRACT_SNIPPET)
    _write(target_root / "src" / "agentic_workspace" / "workspace_runtime_primitives.py", _RUNTIME_MIRROR_CONTRACT_SNIPPET)
    subprocess.run(["git", "init"], cwd=target_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=target_root, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=target_root, check=True)
    subprocess.run(["git", "add", "."], cwd=target_root, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=target_root, check=True, capture_output=True, text=True)


def _replace_text(path: Path, old: str, new: str) -> None:
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


def test_implement_surfaces_runtime_mirror_warning_for_primitives_payload_helper_change(tmp_path: Path, capsys) -> None:
    _seed_runtime_mirror_contract_repo(tmp_path)
    _replace_text(
        tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py",
        '    return {"kind": "external-issue-grouping-hints/v1", "status": "present"}',
        '    return {"kind": "external-issue-grouping-hints/v1", "status": "present", "child_slice_count": 0}',
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Fix an existing primitive bug under the generated CLI boundary.",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["proof"]["runtime_source_edit_review"]
    assert review["status"] == "mirror-drift-warning"
    mirror_review = review["mirror_drift_review"]
    assert mirror_review["status"] == "warning"
    mirror_record = mirror_review["records"][0]
    assert mirror_record["status"] == "warning-asymmetric-mirror-change"
    assert mirror_record["changed_paths"] == ["src/agentic_workspace/workspace_runtime_primitives.py"]
    assert mirror_record["likely_paired_file"] == "src/agentic_workspace/workspace_runtime_core.py"
    assert mirror_record["paired_file_changed"] is False
    assert mirror_record["region_id"] == "external-issue-intake-helper-region"
    assert (
        "declared_region:src/agentic_workspace/workspace_runtime_primitives.py:external-issue-intake-helper-region"
        in mirror_record["trigger_evidence"]
    )
    assert mirror_record["changed_regions"][0]["kind"] == "declared-region"
    assert mirror_record["paired_regions"][0]["path"] == "src/agentic_workspace/workspace_runtime_core.py"
    assert "external_intent_refresh_applies_stale_candidate_reconciliation" in mirror_record["smallest_parity_proof_command"]
    assert "--aw-primitive-ownership" in mirror_record["maintainer_check_command"]
    assert "#1802-style" in mirror_record["represented_regression"]


def test_implement_surfaces_runtime_mirror_warning_for_core_only_payload_helper_change(tmp_path: Path, capsys) -> None:
    _seed_runtime_mirror_contract_repo(tmp_path)
    _replace_text(
        tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py",
        '    return {"planning_candidate_grouping": planning_candidate_grouping}',
        '    return {"planning_candidate_grouping": planning_candidate_grouping, "source": "refresh"}',
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--task",
                "Terse runtime refactor.",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["proof"]["runtime_source_edit_review"]
    assert review["status"] == "mirror-drift-warning"
    assert review["changed_paths"] == ["src/agentic_workspace/workspace_runtime_core.py"]
    assert "review_items" not in review
    mirror_review = review["mirror_drift_review"]
    assert mirror_review["kind"] == "agentic-workspace/runtime-mirror-drift-review/v1"
    assert mirror_review["status"] == "warning"
    record = mirror_review["records"][0]
    assert record["mirror_pair_id"] == "workspace-runtime-core-primitives-payload-helpers"
    assert record["region_id"] == "external-intent-refresh-payload"
    assert record["likely_paired_file"] == "src/agentic_workspace/workspace_runtime_primitives.py"
    assert record["paired_paths"] == ["src/agentic_workspace/workspace_runtime_primitives.py"]
    assert record["changed_regions"][0]["symbol"] == "_refresh_github_external_intent_evidence"
    assert "mirror the payload/helper change" in record["expected_action"]
    assert "external_intent_refresh_applies_stale_candidate_reconciliation" in record["smallest_parity_proof_command"]


def test_implement_runtime_mirror_review_accepts_paired_core_and_primitives_changes(tmp_path: Path, capsys) -> None:
    _seed_runtime_mirror_contract_repo(tmp_path)
    for runtime_path in (
        tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py",
        tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py",
    ):
        _replace_text(
            runtime_path,
            '    return {"grouping_hints": grouping}',
            '    return {"grouping_hints": grouping, "source": "intake"}',
        )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Terse runtime refactor.",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["proof"]["runtime_source_edit_review"]
    assert review["status"] == "classification-required"
    assert review["changed_paths"] == [
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "src/agentic_workspace/workspace_runtime_core.py",
    ]
    record = review["mirror_drift_review"]["records"][0]
    assert record["status"] == "paired-change-requires-parity-proof"
    assert record["region_id"] == "open-issue-intake-payload"
    assert record["paired_file_changed"] is True
    assert record["likely_paired_file"] == ""
    assert "--aw-primitive-ownership" in record["maintainer_check_command"]


def test_implement_runtime_mirror_review_stays_off_for_unrelated_core_file_changes(tmp_path: Path, capsys) -> None:
    _seed_runtime_mirror_contract_repo(tmp_path)
    _replace_text(
        tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py",
        '    return "old"',
        '    return "new"',
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--task",
                "Terse runtime refactor.",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "runtime_source_edit_review" not in payload["proof"]
    assert "proof.runtime_source_edit_review" not in payload["drill_down"]["available_selectors"]


def test_implement_surfaces_runtime_symbol_working_set_for_large_runtime_change(tmp_path: Path, capsys) -> None:
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py",
        """
def _run_external_intent_refresh_github_adapter(args):
    return {"status": "old"}


def _unrelated_runtime_helper():
    return "same"
""",
    )
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True, text=True)
    _replace_text(
        tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py",
        '    return {"status": "old"}',
        '    return {"status": "new"}',
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Fix external intent refresh behavior.",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    working_set = payload["proof"]["runtime_symbol_working_set"]
    assert working_set["kind"] == "agentic-workspace/runtime-symbol-working-set/v1"
    assert working_set["status"] == "present"
    assert working_set["files"][0]["path"] == "src/agentic_workspace/workspace_runtime_primitives.py"
    symbol = working_set["files"][0]["symbols"][0]
    assert symbol["name"] == "_run_external_intent_refresh_github_adapter"
    assert symbol["inventory_status"] == "inventory-backed"
    assert symbol["runtime_boundary_class"] == "provider-integration"
    assert "external_intent_refresh_applies_stale_candidate_reconciliation" in symbol["smallest_focused_proof"]
    assert "proof.runtime_symbol_working_set" in payload["drill_down"]["available_selectors"]
    assert any("runtime_symbol_working_set=1" == signal for signal in payload["action_signals"]["changed_signals"])


def test_implement_keeps_active_intent_packets_selector_only(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py", "VALUE = 1\n")

    task = (
        "Previously convert some tests, but now replace most existing tests with contract-owned tests; "
        "do not claim the parent lane complete unless the replacement is representative."
    )
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                task,
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    context = _implement_context(payload)
    assert "active_intent_contract" not in context
    assert "intent_satisfaction_matrix" not in context
    assert "active_intent_contract" in payload["drill_down"]["available_selectors"]
    assert "intent_satisfaction_matrix" in payload["drill_down"]["available_selectors"]

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                task,
                "--select",
                "active_intent_contract,intent_satisfaction_matrix",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected = json.loads(capsys.readouterr().out)
    contract = selected["values"]["active_intent_contract"]
    assert contract["kind"] == "agentic-workspace/active-intent-contract/v1"
    assert contract["status"] == "present"
    assert contract["source_count"] == 1
    assert "supersede" in contract["update_relationship_options"]
    matrix = selected["values"]["intent_satisfaction_matrix"]
    assert matrix["kind"] == "agentic-workspace/intent-satisfaction-matrix/v1"
    assert matrix["status"] == "required-before-completion-claim"
    assert "full-intent-complete" in matrix["claim_levels"]


def test_implement_detail_commands_use_resolved_cli_invoke(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "Makefile", "test-workspace:\n\tpytest tests\n\nlint-workspace:\n\truff check src tests\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Update README wording",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    detail_commands = payload["drill_down"]["detail_commands"]
    assert detail_commands["full_context"].startswith("uv run agentic-workspace implement ")
    assert detail_commands["proof_detail"].startswith("uv run agentic-workspace proof ")
    assert detail_commands["task_scoped_state"].startswith("uv run agentic-workspace summary ")
    assert detail_commands["takeover_or_recovery"].startswith("uv run agentic-workspace preflight ")
    assert payload["proof"]["detail_command"].startswith("uv run agentic-workspace proof ")
    assert payload["context"]["reuse_pressure"]["status"] == "deferred"
    assert payload["context"]["reuse_pressure"]["detail_selector"] == "reuse_pressure"


def test_implement_active_plan_proof_selection_does_not_build_full_planning_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    _init_git_repo(tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-plan.plan.json"
    _write_json(
        plan_path,
        {
            "kind": "planning-execplan/v1",
            "title": "Active Plan",
            "canonical_core": {"proof_expectations": ["uv run pytest tests/test_workspace_implement_cli.py -q"]},
            "validation_commands": ["uv run pytest tests/test_workspace_implement_cli.py -q"],
        },
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Active Plan", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(tmp_path / "README.md", "hello\n")

    import repo_planning_bootstrap.installer as planning_installer

    def fail_summary(**_: object) -> dict[str, object]:
        raise AssertionError("implement proof selection should not build the broad planning summary")

    monkeypatch.setattr(planning_installer, "planning_summary", fail_summary)

    assert cli.main(["implement", "--target", str(tmp_path), "--changed", "README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "implementer-context-tiny/v1"


def test_implement_generic_continuation_task_does_not_link_active_plan(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-plan.plan.json",
        {
            "kind": "planning-execplan/v1",
            "id": "active-plan",
            "title": "Active Plan",
            "post_decomposition_delegation": {"status": "required"},
        },
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Active Plan", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(tmp_path / "README.md", "hello\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "continue resume finish follow up",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["context"]["planning_safety_gate"]
    assert "active_plan_reliance" not in gate
    assert gate["delegation_decision_required"] is False
    assert gate["detail_selector"] == "planning_safety_gate"


def test_implement_active_plan_continuation_blocks_edits_until_decision_recorded(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-plan.plan.json",
        {
            "kind": "planning-execplan/v1",
            "id": "active-plan",
            "title": "Active Plan",
            "post_decomposition_delegation": {"status": "required"},
        },
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Active Plan", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(tmp_path / "README.md", "hello\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Continue active plan",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["context"]["planning_safety_gate"]
    reliance = gate["active_plan_reliance"]
    assert gate["status"] == "blocked"
    assert gate["implementation_allowed"] is False
    assert gate["delegation_decision_required"] is True
    assert reliance["status"] == "blocked"
    assert reliance["permission_claim"] == "blocked-until-active-plan-decision-recorded"
    assert "action_effect" not in reliance
    assert "active_execplan" not in reliance


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
    compatibility_review = payload["proof"]["tiny_surface_compatibility_review"]
    assert compatibility_review["status"] == "required"
    assert compatibility_review["changed_paths"] == [
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "tests/test_workspace_implement_cli.py",
    ]
    assert "focused tiny/default payload shape tests" in compatibility_review["expected_proof"]


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
    assert payload["proof"]["generated_cli_freshness"]["generated_target_parity"]["target_families"] == ["python", "typescript"]


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
    assert context["objective_drift"]["action_effect"]["force"] == "required_before_claim"
    assert context["objective_drift"]["action_effect"]["allowed_now"] == "continue-implementation-or-inspect-changed-surface"
    assert context["objective_drift"]["action_effect"]["blocked_until_reconciled"] == ["claim-task-complete"]
    assert context["objective_drift"]["action_effect"]["resolution_selector"] == "context.objective_drift"
    intent_proof = payload["proof"]["intent_proof"]
    assert intent_proof["status"] == "needs-agent-judgment"
    assert intent_proof["regression_only_risk"] == "possible"
    assert {"normalize_whitespace", "sentence_summary"} <= set(intent_proof["intended_behavior"])


def test_implement_objective_drift_understands_replacement_and_removal_terms(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "api.py", "params = {'embed': 'children'}\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/api.py",
                "--task",
                "Use `embed=children` instead of `include_children=true`. Remove `include_children`.",
                "--format",
                "json",
            ]
        )
        == 0
    )

    drift = _implement_context(json.loads(capsys.readouterr().out))["objective_drift"]
    assert drift["status"] == "clear"
    assert "include_children=true" not in drift["missing_from_changed_surface"]
    assert "include_children=true" in drift["removed_or_retired_outcomes"]
    assert drift["replacement_checks"][0]["replacement"] == "embed=children"
    assert drift["replacement_checks"][0]["replacement_present"] is True
    assert drift["action_effect"]["force"] == "advisory"
    assert drift["action_effect"]["blocked_until_reconciled"] == []


def test_implement_objective_drift_warns_when_replacement_target_is_absent(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "api.py", "params = {}\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/api.py",
                "--task",
                "Replace `include_children=true` with `embed=children`.",
                "--format",
                "json",
            ]
        )
        == 0
    )

    drift = _implement_context(json.loads(capsys.readouterr().out))["objective_drift"]
    assert drift["status"] == "warning"
    assert "include_children=true" not in drift["missing_from_changed_surface"]
    assert "embed=children" in drift["missing_from_changed_surface"]
    assert drift["replacement_checks"][0]["replacement_present"] is False
    assert drift["action_effect"]["claim_boundary"].startswith("do-not-claim-complete")


def test_implement_objective_drift_handles_rename_and_ordinary_missing_terms(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "api.py", "def new_name():\n    return True\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/api.py",
                "--task",
                "Rename `old_name` to `new_name` and keep `audit_marker`.",
                "--format",
                "json",
            ]
        )
        == 0
    )

    drift = _implement_context(json.loads(capsys.readouterr().out))["objective_drift"]
    assert "old_name" in drift["removed_or_retired_outcomes"]
    assert "audit_marker" in drift["missing_from_changed_surface"]


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
    assert payload["planning_safety_gate"]["work_shape_guidance"]["agent_decision_required"] is True
    assert payload["next_allowed_action"] == "Provide --changed paths or use start/preflight before broad implementation."
    assert payload["handoff_requirements"]["stop_when"][0] != "task routing status is needs-planning for broad external-work ingestion"


def test_implement_task_allows_narrow_single_issue_context(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)

    assert cli.main(["implement", "--target", str(tmp_path), "--task", "implement issue #424", "--verbose", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "task_routing" not in payload
    assert payload["workflow_sufficiency"]["decision_maturity"]["level"] == "evidence_seeking"
    assert payload["workflow_sufficiency"]["decision_maturity"]["missing_evidence"] == ["changed paths"]
    assert payload["planning_safety_gate"]["status"] == "attention"
    assert payload["planning_safety_gate"]["gate_result"] == "external-issue-scope-unknown"
    assert payload["planning_safety_gate"]["decision_maturity"]["level"] == "evidence_seeking"
    assert payload["planning_safety_gate"]["decision_maturity"]["missing_evidence"] == ["external issue intent evidence"]
    assert payload["planning_safety_gate"]["implementation_allowed"] is True
    assert payload["planning_safety_gate"]["issue_scope_evidence"]["missing_issue_refs"] == ["#424"]
    assert payload["planning_safety_gate"]["work_shape_guidance"]["scope_factors"]["issue_refs"] == ["#424"]
    assert payload["planning_safety_gate"]["work_shape_guidance"]["agent_decision_required"] is True
    assert payload["next_allowed_action"] == "Provide --changed paths or use start/preflight before broad implementation."


def test_implement_allows_completed_archived_plan_residue_with_continuation_evidence(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    scenarios = [
        (
            "completed-slice",
            ".agentic-workspace/planning/execplans/archive/completed-slice.plan.json",
            {
                "schema_version": "execplan/v1",
                "id": "completed-slice",
                "machine_readable_contract": {"execution": {"status": "completed"}},
                "active_milestone": {"status": "completed"},
                "execution_run": {"run status": "completed"},
                "intent_satisfaction": {"was original intent fully satisfied?": "yes"},
                "closure_check": {
                    "larger-intent status": "satisfied",
                    "closure decision": "archive-and-close",
                },
            },
            {"larger_intent_status": None, "closure_decision": None},
        ),
        (
            "routed-continuation",
            ".agentic-workspace/planning/execplans/archive/partial-slice.plan.json",
            {
                "schema_version": "execplan/v1",
                "id": "partial-slice",
                "machine_readable_contract": {"execution": {"status": "completed"}},
                "canonical_core": {"continuation_owner": "GitHub #1278"},
                "required_continuation": {
                    "required follow-on for the larger intended outcome": "yes",
                    "owner surface": "GitHub #1278",
                    "activation trigger": "implement the next bounded slice",
                },
                "intent_satisfaction": {"was original intent fully satisfied?": "no"},
                "closure_check": {
                    "closeout scope": "slice",
                    "larger-intent status": "open",
                    "closure decision": "archive-but-keep-lane-open",
                },
            },
            {"larger_intent_status": "open", "closure_decision": "archive-but-keep-lane-open"},
        ),
        (
            "archived-slice-with-routed-parent",
            ".agentic-workspace/planning/execplans/archive/routed-parent-slice.plan.json",
            {
                "schema_version": "execplan/v1",
                "id": "routed-parent-slice",
                "machine_readable_contract": {"execution": {"status": "completed"}},
                "intent_continuity": {
                    "this slice completes the larger intended outcome": "no",
                    "continuation surface": "GitHub #1556",
                },
                "required_continuation": {
                    "required follow-on for the larger intended outcome": "Complete the parent lane.",
                    "owner surface": "GitHub #1556",
                },
                "intent_satisfaction": {"was original intent fully satisfied?": "no for parent lane; yes for slice"},
                "closure_check": {
                    "closeout scope": "slice",
                    "larger-intent status": "open-routed-to-#1556",
                    "closure decision": "archive-and-close",
                },
            },
            {"larger_intent_status": "open-routed-to-#1556", "closure_decision": "archive-and-close"},
        ),
    ]
    for label, archive_path, record, expected_record_fields in scenarios:
        _write(tmp_path / archive_path, json.dumps(record))

        assert (
            cli.main(
                [
                    "implement",
                    "--target",
                    str(tmp_path),
                    "--changed",
                    "src/agentic_workspace/runtime.py",
                    archive_path,
                    "--task",
                    "Publish the completed slice.",
                    "--verbose",
                    "--format",
                    "json",
                ]
            )
            == 0
        ), label

        payload = json.loads(capsys.readouterr().out)
        gate = payload["planning_safety_gate"]
        assert gate["status"] == "clear", label
        assert gate["gate_result"] == "direct-work-allowed", label
        assert gate["implementation_allowed"] is True, label
        facts = gate["changed_path_facts"]
        assert facts["dirty_shape"] == "implementation-with-archived-planning-residue", label
        assert facts["planning_paths"] == [], label
        assert facts["archived_planning_residue"]["status"] == "completed-closeout-residue", label
        assert facts["archived_planning_residue_paths"] == [archive_path], label
        assert facts["archived_planning_residue"]["records"][0]["eligible"] is True, label
        assert facts["archived_planning_residue"]["records"][0]["status"] == "completed", label
        assert gate["work_shape_guidance"]["scope_factors"]["ancillary_paths"] == [archive_path], label
        assert any("archived closeout residue" in reason for reason in gate["work_shape_guidance"]["direct_work_is_reasonable_when"])
        for key, expected in expected_record_fields.items():
            if expected is not None:
                assert facts["archived_planning_residue"]["records"][0][key] == expected, label


def test_implement_context_surfaces_parent_intent_for_active_slice(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    plan = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "generated-runtime-boundary.plan.json"
    _write(
        plan,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "title": "Generated Runtime Boundary",
                "active_milestone": {
                    "id": "generated-runtime-boundary",
                    "status": "active",
                    "scope": "Refresh one generated adapter.",
                },
                "delegated_judgment": {"requested outcome": "Refresh one generated adapter."},
                "parent_acceptance": {
                    "original_intent": "all runtime code should be generated from IR representations as a single source of truth",
                    "parent_acceptance": "runtime behavior cannot be changed outside generated IR or declared primitive implementation boundaries",
                    "current_slice": "generated parser adapter freshness",
                    "residual_parent_intent": "runtime behavior can still be changed outside generated IR/primitive implementation boundaries",
                    "proof_boundary": "slice-only",
                },
                "intent_continuity": {
                    "larger intended outcome": "all runtime code should be generated from IR representations as a single source of truth",
                    "this slice completes the larger intended outcome": "no",
                    "continuation surface": "#1318",
                },
                "required_continuation": {
                    "required follow-on for the larger intended outcome": "yes",
                    "owner surface": "#1318",
                },
                "proof_report": {
                    "validation proof": "pending",
                    "intent_proof": {"status": "needs_review", "claim_boundary": "slice"},
                },
            },
            indent=2,
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        "[todo]\n"
        "active_items = [\n"
        "  { id = 'generated-runtime-boundary', title = 'Generated runtime boundary', surface = '.agentic-workspace/planning/execplans/generated-runtime-boundary.plan.json' },\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\nlanes = []\ncandidates = []\n",
    )
    _write(tmp_path / "generated" / "workspace" / "python" / "parser_adapter.py", "# generated\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/parser_adapter.py",
                "--task",
                "Refresh the generated parser adapter without closing the full runtime-generation boundary.",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    parent = payload["parent_intent_status"]
    assert parent["status"] == "open"
    assert parent["original_intent"] == "all runtime code should be generated from IR representations as a single source of truth"
    assert parent["current_slice"] == "generated parser adapter freshness"
    assert parent["proof_is_slice_only"] is True
    assert "runtime behavior can still be changed outside generated IR" in parent["residual_parent_intent"]


def test_implement_preserves_unplanned_parent_intent_for_generated_surface_slice(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json", "{}\n")
    _write(tmp_path / "generated" / "workspace" / "python" / "parser_adapter.py", "# generated\n")
    task = "all runtime code should be generated from IR representations as a single source of truth"

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/parser_adapter.py",
                "--task",
                task,
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    parent = payload["parent_intent_status"]
    assert parent["status"] == "needs-planning"
    assert parent["original_intent"] == task
    assert parent["parent_acceptance_target"] == task
    assert parent["current_slice"] == "changed generated surface(s): generated/workspace/python/parser_adapter.py"
    assert parent["proof_boundary"] == "changed-path/generated-surface proof only"
    assert parent["proof_is_slice_only"] is True
    assert parent["larger_intent_status"] == "not-recorded"
    assert parent["closure_decision"] == "not-recorded"
    assert parent["required_next_action"].startswith("Preserve the raw task")
    assert "generated-surface freshness" in parent["must_not_claim"][0]
    assert parent["source_fields"] == [
        "task_intent.task_excerpt",
        "changed_paths",
        "generated_surface_trust",
        "planning.active.planning_record.parent_acceptance",
    ]
    authority = parent["authority_boundary"]
    assert authority["surface"] == "parent_intent_status"
    assert "active_parent_acceptance=False" in authority["observed_by_aw"]
    assert "semantic work-shape judgment" in parent["rule"]
    assert "does not semantically classify the prompt" in authority["reporting_rule"]
    assert payload["generated_surface_trust"]["status"] == "present"


def test_implement_rejects_archived_plan_residue_with_only_activation_trigger(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    archive_path = ".agentic-workspace/planning/execplans/archive/trigger-only.plan.json"
    _write(
        tmp_path / archive_path,
        json.dumps(
            {
                "schema_version": "execplan/v1",
                "id": "trigger-only",
                "machine_readable_contract": {"execution": {"status": "completed"}},
                "required_continuation": {
                    "required follow-on for the larger intended outcome": "yes",
                    "activation trigger": "when the next slice starts",
                },
                "intent_satisfaction": {"was original intent fully satisfied?": "no"},
                "closure_check": {
                    "closeout scope": "slice",
                    "larger-intent status": "open",
                    "closure decision": "archive-but-keep-lane-open",
                },
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                archive_path,
                "--task",
                "Publish the completed slice.",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["planning_safety_gate"]
    assert gate["status"] == "violation"
    facts = gate["changed_path_facts"]
    assert facts["archived_planning_residue"]["status"] == "incomplete-or-stale"
    record = facts["archived_planning_residue"]["records"][0]
    assert record["eligible"] is False
    assert record["closure_decision"] == "archive-but-keep-lane-open"
    assert "closure decision is not archive-and-close or routed continuation" in record["reason"]
    assert "larger intent remains open without routed continuation" in record["reason"]
    assert "intent satisfaction is incomplete" in record["reason"]


def test_implement_allows_closeout_evidence_and_state_cleanup_publication_residue(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    state_path = ".agentic-workspace/planning/state.toml"
    closeout_path = ".agentic-workspace/planning/closeout-evidence/partial-slice.closeout.json"
    _write(
        tmp_path / closeout_path,
        json.dumps(
            {
                "kind": "planning-closeout-evidence/v1",
                "active_milestone": {"status": "completed"},
                "execution_run": {"run status": "completed"},
                "intent_satisfaction": {"was original intent fully satisfied?": "no"},
                "closure_check": {
                    "closeout scope": "slice",
                    "slice status": "completed",
                    "larger-intent status": "open",
                    "closure decision": "archive-but-keep-lane-open",
                },
                "durable_residue": {"canonical owner now": "GitHub #1278"},
                "execution_summary": {"follow-on routed to": "GitHub #1278"},
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                closeout_path,
                state_path,
                "--task",
                "Publish the completed slice.",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["planning_safety_gate"]
    assert gate["status"] == "clear"
    assert gate["gate_result"] == "direct-work-allowed"
    facts = gate["changed_path_facts"]
    assert facts["planning_paths"] == []
    assert facts["archived_planning_residue"]["status"] == "completed-closeout-residue"
    assert facts["archived_planning_residue_paths"] == [closeout_path]
    assert facts["archived_planning_residue"]["records"][0]["eligible"] is True
    assert set(gate["work_shape_guidance"]["scope_factors"]["ancillary_paths"]) == {closeout_path, state_path}


def test_implement_closeout_publication_residue_suppresses_unrelated_candidate_pressure(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
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
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "decompositions" / "deferred.decomposition.json",
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Deferred lane",
                "status": "partially-promoted",
                "lanes": [
                    {
                        "lane_id": "future-lane",
                        "title": "Future lane",
                        "readiness": "deferred",
                        "owner_surface": "later",
                        "proof": "later",
                        "candidate_route": "delegate-exploration",
                    }
                ],
            }
        ),
    )
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    closeout_path = ".agentic-workspace/planning/closeout-evidence/partial-slice.closeout.json"
    _write(
        tmp_path / closeout_path,
        json.dumps(
            {
                "kind": "planning-closeout-evidence/v1",
                "active_milestone": {"status": "completed"},
                "execution_run": {"run status": "completed"},
                "intent_satisfaction": {"was original intent fully satisfied?": "no"},
                "closure_check": {
                    "closeout scope": "slice",
                    "slice status": "completed",
                    "larger-intent status": "open",
                    "closure decision": "archive-but-keep-lane-open",
                },
                "durable_residue": {"canonical owner now": "GitHub #1278"},
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                closeout_path,
                "--task",
                "Implement issue #1278",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["planning_safety_gate"]
    assert gate["status"] in {"clear", "attention"}
    assert gate["gate_result"] != "candidate-lane-promotion-required"
    assert gate["implementation_allowed"] is True
    assert gate["changed_path_facts"]["archived_planning_residue"]["status"] == "completed-closeout-residue"


def test_implement_keeps_planning_gate_for_unfinished_archived_plan_residue(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    archive_path = ".agentic-workspace/planning/execplans/archive/open-slice.plan.json"
    _write(
        tmp_path / archive_path,
        json.dumps(
            {
                "schema_version": "execplan/v1",
                "id": "open-slice",
                "status": "completed",
                "intent_satisfaction": {"was original intent fully satisfied?": "no"},
                "closure_check": {
                    "larger-intent status": "open",
                    "closure decision": "archive-but-keep-lane-open",
                },
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                archive_path,
                "--task",
                "Publish the completed slice.",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["planning_safety_gate"]
    assert gate["status"] == "violation"
    assert gate["gate_result"] == "implementation-owner-missing"
    assert gate["implementation_allowed"] is False
    assert gate["repair_route"]["status"] == "available"
    assert gate["repair_route"]["route"] == "retrofit-active-owner-then-closeout"
    assert gate["repair_route"]["work_context"] == "already-started-continuation-or-review-repair"
    assert "planning new-plan" in gate["repair_route"]["claim_current_slice_command"]
    assert "planning closeout" in gate["repair_route"]["closeout_command"]
    assert "planning archive-plan" in gate["repair_route"]["archive_cleanup_command"]
    assert "--prepare-closeout" in gate["repair_route"]["archive_cleanup_command"]
    assert "--retain-archive" in gate["repair_route"]["archive_cleanup_command"]
    assert "--apply-cleanup" in gate["repair_route"]["archive_cleanup_command"]
    assert [step["stage"] for step in gate["repair_route"]["workflow"]] == [
        "claim-current-slice",
        "tighten-owner",
        "record-closeout-evidence",
        "remove-active-residue",
    ]
    assert "Mixed planning plus implementation changes still need an owner" in gate["repair_route"]["safety_rule"]
    facts = gate["changed_path_facts"]
    assert facts["dirty_shape"] == "planning-plus-implementation"
    assert facts["archived_planning_residue"]["status"] == "incomplete-or-stale"
    assert facts["archived_planning_residue"]["records"][0]["eligible"] is False


def test_start_uses_retrofit_repair_command_for_missing_implementation_owner(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    archive_path = ".agentic-workspace/planning/execplans/archive/open-slice.plan.json"
    _write(
        tmp_path / archive_path,
        json.dumps(
            {
                "schema_version": "execplan/v1",
                "id": "open-slice",
                "status": "completed",
                "intent_satisfaction": {"was original intent fully satisfied?": "no"},
                "closure_check": {
                    "larger-intent status": "open",
                    "closure decision": "archive-but-keep-lane-open",
                },
            }
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                archive_path,
                "--task",
                "Continue the already-started slice repair.",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    action = payload["next_safe_action"]
    repair_route = payload["context"]["planning"]["planning_safety_gate"]["repair_route"]
    assert action["next_safe_action"] == "checkpoint-planning-before-implementation"
    assert "planning new-plan" in action["preferred_cli"]
    assert repair_route["after_claim_command"] == "agentic-workspace summary --target . --format json"
    assert repair_route["work_context"] == "already-started-continuation-or-review-repair"


def test_implement_blocks_epic_work_with_multiple_roadmap_candidates(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1201-command-package", maturity = "candidate", status = "next", priority = "P1", refs = "GitHub #1201", title = "Command package extraction", outcome = "Extract the command package.", reason = "Open issue.", promotion_signal = "Promote before implementation.", suggested_first_slice = "Shape a bounded lane." },
  { id = "github-1202-runtime-parity", maturity = "candidate", status = "next", priority = "P1", refs = "GitHub #1202", title = "Runtime parity", outcome = "Prove generated runtime parity.", reason = "Open issue.", promotion_signal = "Promote before implementation.", suggested_first_slice = "Shape a bounded lane." },
]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Implement the command package extraction and runtime parity epic",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["context"]["planning_safety_gate"]
    assert gate["status"] == "blocked"
    assert gate["gate_result"] == "candidate-lane-promotion-required"
    assert gate["implementation_allowed"] is False
    assert gate["candidate_pressure"]["candidate_ids"] == [
        "github-1201-command-package",
        "github-1202-runtime-parity",
    ]
    assert payload["context"]["workflow_sufficiency"]["sufficiency_result"] == "candidate-lane-promotion-required"


def test_implement_keeps_unrelated_roadmap_candidates_advisory(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1522-packaging-tests", maturity = "candidate", status = "next", refs = "GitHub #1522", title = "Packaging test restructuring", outcome = "Reduce package build cost." },
  { id = "github-1523-generated-proof-tests", maturity = "candidate", status = "next", refs = "GitHub #1523", title = "Generated proof test pruning", outcome = "Prune generated proof tests." },
]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Implement #1556 #1559 #1560 requirement grounded delegation support",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["context"]["planning_safety_gate"]
    assert gate["status"] == "clear"
    assert gate["implementation_allowed"] is True
    assert "candidate_pressure" not in gate

    capsys.readouterr()
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Implement #1556 #1559 #1560 requirement grounded delegation support",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )
    verbose_payload = json.loads(capsys.readouterr().out)
    verbose_pressure = verbose_payload["planning_safety_gate"]["candidate_pressure"]
    assert verbose_pressure["advisory_backlog"]["unmatched_candidate_ids"] == [
        "github-1522-packaging-tests",
        "github-1523-generated-proof-tests",
    ]


def test_implement_keeps_generic_github_issue_filing_terms_as_weak_hints(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1501-memory-routing", maturity = "candidate", status = "next", refs = "GitHub #1501", title = "Memory routing lane", outcome = "Improve routing." },
  { id = "github-1502-delegation", maturity = "candidate", status = "next", refs = "GitHub #1502", title = "Delegation lane", outcome = "Improve delegation." },
]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--task",
                "File dogfooding friction findings as GitHub issues",
                "--format",
                "json",
            ]
        )
        == 0
    )

    gate = json.loads(capsys.readouterr().out)["context"]["planning_safety_gate"]
    assert gate["status"] == "clear"
    assert "candidate_pressure" not in gate


def test_implement_keeps_generic_ci_refresh_terms_as_weak_hints(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "generated-command-refresh", maturity = "candidate", status = "next", refs = "GitHub #1503", title = "Generated command cleanup after refresh", outcome = "Clean generated command tests." },
  { id = "testing-inventory-refresh", maturity = "candidate", status = "next", refs = "GitHub #1504", title = "Testing inventory refresh", outcome = "Refresh testing inventory." },
]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/memory/src/repo_memory_bootstrap/installer.py",
                "--task",
                "Fix CI memory typecheck failure after dependency refresh",
                "--format",
                "json",
            ]
        )
        == 0
    )

    gate = json.loads(capsys.readouterr().out)["context"]["planning_safety_gate"]
    assert gate["status"] == "clear"
    assert "candidate_pressure" not in gate


def test_implement_ignores_closed_external_intent_candidate_pressure(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json",
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {"id": "#1201", "status": "closed", "title": "Old lane"},
                    {"id": "#1202", "status": "closed", "title": "Old lane 2"},
                ],
            }
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1201-old", maturity = "candidate", status = "next", refs = "GitHub #1201", title = "Old lane one", outcome = "Closed upstream." },
  { id = "github-1202-old", maturity = "candidate", status = "next", refs = "GitHub #1202", title = "Old lane two", outcome = "Closed upstream." },
]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Implement unrelated bounded runtime support",
                "--format",
                "json",
            ]
        )
        == 0
    )

    gate = json.loads(capsys.readouterr().out)["context"]["planning_safety_gate"]
    assert gate["status"] == "clear"
    assert "candidate_pressure" not in gate


def test_start_surfaces_custody_only_planning_for_parent_lane_without_blocking_direct_work(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    _write(
        tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json",
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "id": "#2200",
                        "system": "github",
                        "status": "open",
                        "kind": "parent-lane",
                        "title": "Parent lane: API migration",
                    }
                ],
            }
        ),
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement issue #2200",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["values"]["planning_safety_gate"]
    custody = gate["custody_planning"]
    assert gate["implementation_allowed"] is True
    assert custody["status"] == "recommended"
    assert custody["planning_roles"]["implementation_gate"] == "not-required"
    assert custody["planning_roles"]["sequencing_aid"] == "not-required-for-current-slice"
    assert custody["planning_roles"]["intent_custody"] == "recommended"
    assert "parent-lane" in custody["reason_codes"]
    assert "shared lane intent" in custody["purpose"]
    assert custody["slice_boundary"]["full_parent_satisfaction"] == "requires-custody-or-equivalent-reconciliation"
    assert custody["follow_up_route"]["refs"] == ["#1706"]


def test_start_default_output_surfaces_custody_only_planning_for_parent_lane(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    _write(
        tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json",
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "id": "#2200",
                        "system": "github",
                        "status": "open",
                        "kind": "parent-lane",
                        "title": "Parent lane: API migration",
                    }
                ],
            }
        ),
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement issue #2200",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["context"]["planning"]["planning_safety_gate"]
    custody = gate["custody_planning"]
    assert gate["implementation_allowed"] is True
    assert custody["status"] == "recommended"
    assert custody["planning_roles"]["intent_custody"] == "recommended"
    assert "parent-lane" in custody["reason_codes"]


def test_implement_custody_only_planning_blocks_parent_closure_claims_not_edits(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    _write(tmp_path / "docs" / "note.md", "# Note\n")
    _write(
        tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json",
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "id": "#2200",
                        "system": "github",
                        "status": "open",
                        "kind": "parent-lane",
                        "title": "Parent lane: API migration",
                    }
                ],
            }
        ),
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/note.md",
                "--task",
                "Implement issue #2200 and close parent issue",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["context"]["planning_safety_gate"]
    custody = gate["custody_planning"]
    assert gate["implementation_allowed"] is True
    assert custody["status"] == "required-reconciliation"
    assert custody["action_effect"]["force"] == "required_before_claim"
    assert "use-pr-closing-keywords" in custody["action_effect"]["blocked_until_reconciled"]
    assert custody["slice_boundary"]["useful_slice_completion"] == "allowed-after-normal-proof"
    assert custody["slice_boundary"]["full_parent_satisfaction"] == "requires-custody-or-equivalent-reconciliation"
    assert payload["operating_loop"]["planning"]["state"] == "closeout_required"


def test_start_keeps_narrow_direct_issue_quiet_without_custody_noise(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    _write(
        tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json",
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "id": "#2201",
                        "system": "github",
                        "status": "open",
                        "kind": "issue",
                        "title": "Fix typo in README",
                    }
                ],
            }
        ),
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement issue #2201",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["next_safe_action"]["implementation_allowed"] is True
    assert "planning_safety_gate" not in payload["context"]["planning"]


def test_start_surfaces_lane_shaping_prompt_for_broad_unshaped_work(tmp_path: Path, capsys) -> None:
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
                'safe_task_classes = ["boundary-shaping", "reasoning-heavy"]',
                'execution_methods = ["manual"]',
            ]
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "lane-one", maturity = "candidate", status = "next", priority = "P1", title = "First broad lane", outcome = "Shape the first lane.", reason = "Open lane.", promotion_signal = "Promote before implementation.", suggested_first_slice = "Ask shaping questions." },
  { id = "lane-two", maturity = "candidate", status = "next", priority = "P1", title = "Second broad lane", outcome = "Shape the second lane.", reason = "Open lane.", promotion_signal = "Promote before implementation.", suggested_first_slice = "Ask shaping questions." },
]
""",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape the first broad lane and second broad lane before implementation",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["next_safe_action"]["next_safe_action"] == "present-lane-shaping-prompt"
    assert payload["next_safe_action"]["implementation_allowed"] is False
    assert "begin implementation" in payload["next_safe_action"]["forbidden_actions"]
    assert payload["action_signals"]["allowed_next_action"] == "present-lane-shaping-prompt"
    assert payload["context"]["planning"]["workflow_sufficiency"]["sufficiency_result"] == "lane-shaping-required"
    gate = payload["context"]["lane_shaping_gate"]
    assert gate["status"] == "required"
    assert gate["target"]["target_kind"] == "manual-external"
    assert gate["target"]["name"] == "chatgpt"
    assert gate["candidate_ids"] == ["lane-one", "lane-two"]
    prompt = gate["ready_to_forward_prompt"]["copy_paste"]
    assert "What is the larger intended outcome" in prompt
    assert "External refs mentioned in task" not in prompt
    assert "GitHub" not in prompt


def test_start_keeps_candidate_promotion_without_manual_external_shaping_target(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "lane-one", maturity = "candidate", status = "next", priority = "P1", title = "First broad lane", outcome = "Shape the first lane.", reason = "Open lane.", promotion_signal = "Promote before implementation.", suggested_first_slice = "Ask shaping questions." },
  { id = "lane-two", maturity = "candidate", status = "next", priority = "P1", title = "Second broad lane", outcome = "Shape the second lane.", reason = "Open lane.", promotion_signal = "Promote before implementation.", suggested_first_slice = "Ask shaping questions." },
]
""",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape the first broad lane and second broad lane before implementation",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["next_safe_action"]["next_safe_action"] == "select-or-promote-candidate-lane"
    assert payload["action_signals"]["allowed_next_action"] == "select-or-promote-candidate-lane"
    assert payload["context"]["planning"]["workflow_sufficiency"]["sufficiency_result"] == "candidate-lane-promotion-required"
    assert "lane_shaping_gate" not in payload["context"]


def test_start_does_not_promote_roadmap_candidates_from_generic_jumpstart_terms(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1601-workspace-cleanup", maturity = "candidate", status = "next", priority = "P2", refs = "GitHub #1601", title = "Workspace cleanup", outcome = "Improve repo maintenance surfaces.", reason = "Open issue.", promotion_signal = "Promote before implementation.", suggested_first_slice = "Shape cleanup." },
  { id = "github-1602-setup-followup", maturity = "candidate", status = "next", priority = "P2", refs = "GitHub #1602", title = "Setup follow-up", outcome = "Review jumpstart residue in this repo.", reason = "Open issue.", promotion_signal = "Promote before implementation.", suggested_first_slice = "Shape setup." },
]
""",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Run workspace setup jumpstart on this repo for dogfooding",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["next_safe_action"]["implementation_allowed"] is True
    assert payload["action_signals"]["allowed_next_action"] != "select-or-promote-candidate-lane"
    assert payload["context"]["planning"]["workflow_sufficiency"]["sufficiency_result"] != "candidate-lane-promotion-required"
    assert "planning_safety_gate" not in payload["context"]["planning"]
    assert "lane_shaping_gate" not in payload["context"]


def test_implement_surfaces_requirement_grounding_chain(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "runtime.py", "VALUE = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json",
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "id": "#1556",
                        "system": "tracker",
                        "status": "open",
                        "kind": "capability-lane",
                        "title": "Support requirement-grounded agent work end to end",
                    }
                ],
            }
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "requirement-grounding", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/requirement-grounding.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "requirement-grounding.plan.json",
        {
            "kind": "planning-execplan/v1",
            "title": "Requirement grounding",
            "traceability_refs": {"requirement_refs": ["docs/requirements.md#trace"]},
            "requirement_grounding": {"design_effects": ["Requirement refs must remain distinct from agent interpretation."]},
            "intent_interpretation": {"chosen concrete what": "Carry requirement refs through planning and closeout."},
            "canonical_core": {
                "hard_constraints": "Keep observed source separate from agent interpretation.",
                "touched_scope": ["src/runtime.py"],
                "proof_expectations": ["uv run pytest tests/test_workspace_implement_cli.py -q"],
                "completion_criteria": ["Requirement grounding packet is visible."],
            },
            "validation_commands": ["uv run pytest tests/test_workspace_implement_cli.py -q"],
            "completion_criteria": ["Requirement grounding packet is visible."],
        },
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/runtime.py",
                "--task",
                "Implement #1556",
                "--select",
                "requirement_grounding",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["payload_locations"]["primary_payload_field"] == "values"
    assert payload["payload_locations"]["selected_payload_paths"]["requirement_grounding"] == "values.requirement_grounding"
    grounding = payload["values"]["requirement_grounding"]
    assert grounding["kind"] == "agentic-workspace/requirement-grounding/v1"
    assert grounding["status"] in {"ready", "attention"}
    assert {item["ref"] for item in grounding["requirement_refs"]} >= {"#1556", "docs/requirements.md#trace"}
    assert grounding["requirement_refs"][0]["source_metadata"]["trust_note"].startswith("routing/index metadata only")
    assert grounding["source_inventory_policy"]["not_a_requirement_corpus"] is True
    assert grounding["agent_interpretation"]["status"] == "present"
    assert grounding["design_effects"] == ["Requirement refs must remain distinct from agent interpretation."]
    assert grounding["planning_context_fallback"]["items"] == ["Keep observed source separate from agent interpretation."]
    assert grounding["authority_boundary"]["agent_owned_decisions"]


def test_proof_surfaces_requirement_grounding_chain(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "runtime.py", "VALUE = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "proof-grounding", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/proof-grounding.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "proof-grounding.plan.json",
        {
            "kind": "planning-execplan/v1",
            "title": "Proof grounding",
            "traceability_refs": {"requirement_refs": ["docs/requirements.md#trace"]},
        },
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/runtime.py",
                "--select",
                "requirement_grounding",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["payload_locations"]["primary_payload_field"] == "values"
    grounding = payload["values"]["requirement_grounding"]
    assert grounding["kind"] == "agentic-workspace/requirement-grounding/v1"
    assert grounding["requirement_refs"][0]["ref"] == "docs/requirements.md#trace"
    assert grounding["requirement_refs"][0]["source_metadata"]["freshness"] in {"repo-current", "external-or-unverified"}
    assert grounding["closeout_claims"]["blocked"] == ["requirement-grounded-completion"]


def test_implement_routes_configured_architecture_principle_for_runtime_path(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write_architecture_principles(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--task",
                "Refactor runtime routing",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "architecture_principles=1" in payload["action_signals"]["changed_signals"]
    assert payload["context"]["absence_states"]["architecture_principles"] == "present"
    compact_packet = payload["context"]["architecture_principles"]
    assert compact_packet["matched_count"] == 1
    compact_principle = compact_packet["matched_principles"][0]
    assert compact_principle["guardrails"][0]["id"] == "non-enum-keyword-routing"
    assert "explicit structured facts" in compact_principle["allowed_sources"]
    assert "package-owned assumptions about prose keywords" in compact_principle["forbidden_sources"]
    assert "routing" in compact_principle["affected_decisions"]
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--task",
                "Refactor runtime routing",
                "--select",
                "architecture_principles",
                "--format",
                "json",
            ]
        )
        == 0
    )
    packet = json.loads(capsys.readouterr().out)["values"]["architecture_principles"]
    assert packet["kind"] == "agentic-workspace/architecture-principles-status/v1"
    assert packet["status"] == "attention"
    assert packet["source"] == ".agentic-workspace/system-intent/intent.toml"
    assert packet["source_kind"] == "agentic-workspace/system-intent/v1"
    assert packet["matched_principles"][0]["id"] == "host-agnostic-agent-judgment"
    assert packet["matched_principles"][0]["derived_applications"] == ["non-enum-keyword-routing"]
    assert packet["matched_principles"][0]["guardrails"][0]["id"] == "non-enum-keyword-routing"
    assert packet["matched_principles"][0]["matched_paths"] == [
        {
            "path": "src/agentic_workspace/workspace_runtime_core.py",
            "pattern": "src/agentic_workspace/workspace_runtime*.py",
        }
    ]
    assert packet["matched_principles"][0]["guardrail_refs"] == ["docs/maintainer/non-enum-keyword-routing-audit.json"]
    assert packet["closeout"]["required_claim"] == "preserved|re-scoped-by-human|unresolved"


def test_implement_architecture_principle_uses_structured_path_not_task_keywords(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write_architecture_principles(tmp_path)
    _write(tmp_path / "README.md", "# Keyword trap\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Avoid keyword routing and non-enum marker phrases in workflow ownership",
                "--select",
                "architecture_principles",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["architecture_principles"]
    assert packet["status"] == "clear"
    assert packet["matched_count"] == 0
    assert packet["matched_principles"] == []

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Avoid keyword routing and non-enum marker phrases in workflow ownership",
                "--format",
                "json",
            ]
        )
        == 0
    )

    tiny_payload = json.loads(capsys.readouterr().out)
    assert "architecture_principles" not in tiny_payload["context"]
    assert tiny_payload["context"]["absence_states"]["architecture_principles"] == "hidden_behind_detail_route"


def test_implement_architecture_principle_selector_reports_multiple_matches(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "system-intent" / "intent.toml",
        """
kind = "agentic-workspace/system-intent/v1"
summary = "Portable host-neutral operating intent."
governing_intents = []
anti_intents = []
decision_tests = []
confidence = "high"
needs_review = false

[[architecture_principles]]
id = "runtime-portability"
title = "Preserve runtime portability"
owner = "workspace-runtime"
summary = "Runtime behavior must remain host-neutral."
path_globs = ["src/agentic_workspace/workspace_runtime*.py"]

[[architecture_principles]]
id = "runtime-claim-boundary"
title = "Preserve runtime claim boundary"
owner = "workspace-runtime"
summary = "Runtime reports must not overstate claim safety."
path_globs = ["src/agentic_workspace/workspace_runtime*.py"]
""",
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--task",
                "Refactor runtime routing",
                "--select",
                "architecture_principles",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["architecture_principles"]
    assert packet["status"] == "attention"
    assert packet["matched_count"] == 2
    assert [item["id"] for item in packet["matched_principles"]] == ["runtime-portability", "runtime-claim-boundary"]
    assert packet["closeout"]["required_claim"] == "preserved|re-scoped-by-human|unresolved"


def test_proof_architecture_principle_selector_degrades_malformed_state(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "system-intent" / "intent.toml",
        """
kind = "agentic-workspace/system-intent/v1"
[[architecture_principles]
id = "broken"
""",
    )
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
                "architecture_principles",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["architecture_principles"]
    assert packet["status"] == "unavailable"
    assert packet["matched_count"] == 0
    assert packet["source"] == ".agentic-workspace/system-intent/intent.toml"
    assert packet["error"]


def test_proof_surfaces_architecture_principle_closeout_claim(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write_architecture_principles(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--select",
                "architecture_principles",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["architecture_principles"]
    assert packet["status"] == "attention"
    assert packet["matched_principles"][0]["id"] == "host-agnostic-agent-judgment"
    assert packet["matched_principles"][0]["derived_applications"] == ["non-enum-keyword-routing"]
    assert packet["matched_principles"][0]["closeout_question"].startswith("Was this principle preserved")
    assert packet["closeout"]["required_claim"] == "preserved|re-scoped-by-human|unresolved"


def test_requirement_grounding_reports_missing_sensitive_refs(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "runtime.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/runtime.py",
                "--task",
                "Update privacy policy handling",
                "--select",
                "requirement_grounding",
                "--format",
                "json",
            ]
        )
        == 0
    )

    grounding = json.loads(capsys.readouterr().out)["values"]["requirement_grounding"]
    assert grounding["status"] == "attention"
    assert grounding["source_facts"]["sensitivity_signals"] == ["task-text-requirement-sensitive"]
    assert grounding["known_gaps"][0]["gap"] == "task appears requirement-sensitive but no applicable requirement refs were selected"


def test_report_section_surfaces_requirement_grounding_chain(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path)]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "report-grounding", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/report-grounding.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "report-grounding.plan.json",
        {
            "kind": "planning-execplan/v1",
            "title": "Report grounding",
            "traceability_refs": {"requirement_refs": ["docs/requirements.md#report"]},
            "intent_interpretation": {"chosen concrete what": "Report the requirement grounding chain."},
            "canonical_core": {"hard_constraints": "Keep report facts separate from agent decisions."},
        },
    )

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "requirement_grounding",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["payload_locations"]["primary_payload_field"] == "answer"
    assert payload["payload_locations"]["selected_payload_paths"]["answer"] == "answer"
    grounding = payload["answer"]
    assert grounding["kind"] == "agentic-workspace/requirement-grounding/v1"
    assert grounding["status"] == "ready"
    assert grounding["requirement_refs"][0]["ref"] == "docs/requirements.md#report"
    assert grounding["source_inventory_policy"]["role"] == "compact-routing-index"
    assert grounding["agent_interpretation"]["summary"] == "Report the requirement grounding chain."


def test_report_section_scopes_subsystem_assurance_from_active_plan(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path)]) == 0
    capsys.readouterr()
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

[assurance.subsystem_profiles.audit-log]
assurance_level = "high"
requirement_refs = ["docs/system-requirements.md#auditability"]
required_evidence = ["requirement_grounding"]
force = "required-before-closeout"
blocked_without_evidence = ["requirement-grounded-completion"]
claim_boundary = "subsystem-scoped"
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "audit-plan", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/audit-plan.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "audit-plan.plan.json",
        {
            "kind": "planning-execplan/v1",
            "title": "Audit plan",
            "canonical_core": {"touched_scope": ["subsystem:audit-log"]},
            "traceability_refs": {"requirement_refs": ["docs/system-requirements.md#auditability"]},
        },
    )

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "assurance_requirements",
                "--format",
                "json",
            ]
        )
        == 0
    )
    assurance = json.loads(capsys.readouterr().out)["answer"]
    assert assurance["status"] == "attention"
    assert assurance["active"][0]["id"] == "subsystem:audit-log"
    assert assurance["subsystem_assurance"]["matched_subsystem_ids"] == ["audit-log"]

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "requirement_grounding",
                "--format",
                "json",
            ]
        )
        == 0
    )
    grounding = json.loads(capsys.readouterr().out)["answer"]
    assert grounding["subsystem_assurance"]["effective_assurance_level"] == "high"
    assert grounding["applicability"][0]["ref"] == "subsystem:audit-log"
    assert "requirement-grounded-completion" in grounding["closeout_claims"]["blocked"]


def test_report_section_ignores_active_plan_scope_for_unknown_subsystem_profile(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path)]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "ordinary"
paths = ["src/ordinary/**"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.subsystem_profiles.audit-log]
assurance_level = "high"
required_evidence = ["requirement_grounding"]
force = "required-before-closeout"
blocked_without_evidence = ["requirement-grounded-completion"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "audit-plan", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/audit-plan.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "audit-plan.plan.json",
        {
            "kind": "planning-execplan/v1",
            "title": "Audit plan",
            "canonical_core": {"touched_scope": ["subsystem:audit-log"]},
        },
    )

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "assurance_requirements",
                "--format",
                "json",
            ]
        )
        == 0
    )

    assurance = json.loads(capsys.readouterr().out)["answer"]
    subsystem = assurance["subsystem_assurance"]
    assert assurance["status"] == "configured"
    assert assurance["active"] == []
    assert subsystem["status"] == "invalid-config"
    assert subsystem["invalid_profiles"][0]["id"] == "audit-log"
    assert subsystem["matched_count"] == 0
    assert subsystem["matched_subsystem_ids"] == []
    assert subsystem["missing_evidence"] == []


def test_implement_projects_ready_plan_delegation_packet(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "runtime.py", "VALUE = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "delegate-ready", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/delegate-ready.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "delegate-ready.plan.json",
        {
            "kind": "planning-execplan/v1",
            "title": "Delegate ready slice",
            "canonical_core": {
                "requested_outcome": "Implement a bounded runtime packet.",
                "touched_scope": ["src/runtime.py"],
                "proof_expectations": ["uv run pytest tests/test_workspace_implement_cli.py -q"],
                "completion_criteria": ["Packet is projected."],
            },
            "execution_bounds": {"allowed paths": "src/runtime.py", "stop before touching": "generated files"},
            "stop_conditions": {"stop when": "proof fails"},
            "validation_commands": ["uv run pytest tests/test_workspace_implement_cli.py -q"],
            "completion_criteria": ["Packet is projected."],
            "references": [{"target": "docs/design.md", "label": "Design"}],
        },
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/runtime.py",
                "--task",
                "Continue delegate-ready",
                "--select",
                "plan_delegation_packet",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["plan_delegation_packet"]
    assert packet["kind"] == "agentic-workspace/plan-delegation-packet/v1"
    assert packet["delegation_ready"] is True
    assert packet["guided_tightening"]["status"] == "not-needed"
    assert packet["delegation_recommended"] is True
    assert packet["freshness_guard"]["delegate_return_must_cite_revision"] is True
    assert packet["missing_fields"] == []
    assert packet["recommended_route"] == "implementation-delegate"
    assert "Allowed write scope: src/runtime.py" in packet["handoff_prompt"]
    assert packet["return_contract"]["required_fields"] == [
        "changed_files",
        "changed_surfaces",
        "proof_run",
        "proof_result",
        "result",
        "uncertainty",
        "stop_condition_hits",
        "residue",
        "allowed_claims",
        "planning_revision",
    ]


def test_implement_keeps_exact_semicolon_scope_delegation_ready(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "runtime.py", "VALUE = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "delegate-semicolon", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/delegate-semicolon.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "delegate-semicolon.plan.json",
        {
            "kind": "planning-execplan/v1",
            "title": "Delegate semicolon slice",
            "canonical_core": {
                "requested_outcome": "Implement a bounded runtime packet.",
                "touched_scope": ["src/runtime.py; tests/test_runtime.py"],
                "proof_expectations": ["uv run pytest tests/test_runtime.py -q"],
                "completion_criteria": ["Packet is projected."],
            },
            "stop_conditions": {"stop when": "proof fails"},
        },
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/runtime.py",
                "--task",
                "Continue delegate-semicolon",
                "--select",
                "plan_delegation_packet",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["plan_delegation_packet"]
    assert packet["delegation_ready"] is True
    assert packet["ambiguous_fields"] == []
    assert packet["allowed_write_scope"] == ["src/runtime.py", "tests/test_runtime.py"]


def test_implement_refuses_ambiguous_plan_delegation_packet(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "runtime.py", "VALUE = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "delegate-ambiguous", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/delegate-ambiguous.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "delegate-ambiguous.plan.json",
        {
            "kind": "planning-execplan/v1",
            "title": "Ambiguous delegate slice",
            "canonical_core": {
                "requested_outcome": "Implement a bounded runtime packet.",
                "touched_scope": ["src/runtime.py; tests as needed"],
                "proof_expectations": ["Fill in proof later."],
                "completion_criteria": ["Packet is projected."],
            },
            "stop_conditions": {"stop when": "proof fails"},
        },
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/runtime.py",
                "--task",
                "Continue delegate-ambiguous",
                "--select",
                "plan_delegation_packet",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["plan_delegation_packet"]
    assert packet["status"] == "ambiguous-fields"
    assert packet["delegation_ready"] is False
    assert packet["delegation_recommended"] is False
    assert set(packet["ambiguous_fields"]) >= {"allowed_write_scope", "proof_commands"}
    assert "execution_bounds.allowed paths" in packet["ambiguous_field_paths"]
    tightening = packet["guided_tightening"]
    assert tightening["status"] == "available"
    assert tightening["suggested_updates"]["allowed_write_scope"] == ["src/runtime.py"]
    assert "proof_commands" in tightening["blocking_fields"]
    assert "Rerun implement --select plan_delegation_packet before delegating." in tightening["apply_guidance"]


def test_implement_projects_validation_delegation_route(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "runtime.py", "VALUE = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "delegate-validation", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/delegate-validation.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "delegate-validation.plan.json",
        {
            "kind": "planning-execplan/v1",
            "title": "Delegate validation slice",
            "canonical_core": {
                "requested_outcome": "Validate the bounded runtime packet.",
                "touched_scope": ["src/runtime.py"],
                "proof_expectations": ["uv run pytest tests/test_workspace_implement_cli.py -q"],
                "completion_criteria": ["Validation result is reported."],
            },
            "stop_conditions": {"stop when": "proof fails"},
        },
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/runtime.py",
                "--task",
                "Continue delegate-validation",
                "--select",
                "plan_delegation_packet",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["plan_delegation_packet"]
    assert packet["delegation_ready"] is True
    assert packet["recommended_route"] == "validation-delegate"


def _write_python_test_evidence_config(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[workspace]
cli_invoke = "uv run python scripts/run_agentic_workspace.py"

[assurance.requirements.test_evidence_change_decision]
level = "high"
applies_to_paths = ["tests/**"]
required_evidence = ["verification_proof_decision_review"]
proof_profile = "test_evidence_change"
review_owner = "maintainer"
force = "required-before-closeout"
""",
    )


def _write_test_suite_budget(tmp_path: Path) -> None:
    _write_json(
        tmp_path / ".agentic-workspace" / "verification" / "test-suite-budget.json",
        {
            "kind": "agentic-workspace/test-suite-budget/v1",
            "source": "test fixture",
            "provenance": {
                "measurement_command": "pytest --collect-only",
                "recorded_at": "2026-06-29",
            },
            "scopes": [
                {
                    "scope": "root",
                    "baseline": {"date": "2026-06-15", "collected_count": 613},
                    "current": {
                        "observed_at": "2026-06-29",
                        "collected_count": 884,
                        "source": "fixture",
                        "max_age_days": 99999,
                    },
                    "target": {"min": 500, "max": 700},
                },
                {
                    "scope": "all",
                    "baseline": {"date": "2026-06-15", "collected_count": 1118},
                    "current": {
                        "observed_at": "2026-06-29",
                        "collected_count": 1426,
                        "source": "fixture",
                        "max_age_days": 99999,
                    },
                },
            ],
        },
    )


def test_implement_surfaces_test_strategy_check_for_hotspot_tests(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write_python_test_evidence_config(tmp_path)
    _write_test_suite_budget(tmp_path)
    _write(
        tmp_path / "tests" / "test_runtime.py",
        """
import pytest


@pytest.mark.parametrize("case", ["a", "b"])
def test_runtime_matrix_case(case):
    assert case


def test_runtime_warning_alpha(): assert True
def test_runtime_warning_beta(): assert True
def test_runtime_warning_gamma(): assert True
def test_runtime_warning_delta(): assert True
def test_runtime_warning_epsilon(): assert True
def test_runtime_warning_zeta(): assert True
def test_runtime_warning_eta(): assert True
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "tests/test_runtime.py",
                "--task",
                "Address review feedback by adding regression coverage",
                "--select",
                "test_strategy_check",
                "--format",
                "json",
            ]
        )
        == 0
    )

    check = json.loads(capsys.readouterr().out)["values"]["test_strategy_check"]
    assert check["kind"] == "agentic-workspace/test-strategy-check/v1"
    assert check["status"] == "advisory"
    assert check["blocking"] is False
    assert check["hotspot_file_count"] == 1
    assert check["scenario_matrix_candidate_count"] == 1
    assert check["reviewer_requested_coverage"] is True
    assert check["disposition_required_before_closeout"] is True
    budget = check["budget_drift"]
    assert budget["status"] == "attention"
    assert budget["root"]["current_collected_count"] == 884
    assert budget["root"]["baseline_collected_count"] == 613
    assert budget["root"]["over_target_by"] == 184
    assert budget["root"]["freshness"]["status"] == "fresh"
    assert budget["budget_source"]["source"] == "test fixture"
    assert budget["budget_source"]["provenance"]["measurement_command"] == "pytest --collect-only"
    assert budget["changed_hotspot_files"] == ["tests/test_runtime.py"]
    assert budget["over_budget_hotspot_files_requiring_disposition"] == ["tests/test_runtime.py"]
    assert any("contract or conformance" in option for option in budget["placement_alternatives"])
    assert check["verification_evidence_surfaces"]["proof_decision_status"]
    assert check["pre_test_evidence_guardrail"]["status"] == "advisory"
    assert check["pre_test_evidence_guardrail"]["blocking"] is False
    assert check["pre_test_evidence_guardrail"]["source_boundary"]["no_universal_task_keyword_policy"] is True
    assert check["pre_test_evidence_guardrail"]["source_boundary"]["no_universal_filename_policy"] is True
    assert check["pre_test_evidence_guardrail"]["evidence_path_classifications"][0]["source"] == (
        "assurance.requirements.test_evidence_change_decision"
    )
    assert "package-local-behavior" in check["evidence_owner_options"]
    assert "convert-to-conformance" in check["proof_decision_options"]
    assert any("trust question" in question for question in check["pre_test_decision_questions"])
    assert any("scenario matrix" in question for question in check["regression_sprawl_review_questions"])
    assert "standalone-durable-contract-proof" in check["record_disposition_options"]
    assert check["files"][0]["parametrized_test_count"] == 1


def test_implement_classifies_declared_non_python_evidence_path(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[workspace]
cli_invoke = "uv run python scripts/run_agentic_workspace.py"

[assurance.requirements.frontend_evidence_change]
level = "high"
applies_to_paths = ["web/specs/*.spec.ts"]
required_evidence = ["verification_proof_decision_review"]
proof_profile = "test_evidence_change"
review_owner = "maintainer"
force = "required-before-closeout"
""",
    )
    _write(tmp_path / "web" / "specs" / "checkout.spec.ts", "test('checkout flow', () => expect(true).toBe(true));\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "web/specs/checkout.spec.ts",
                "--task",
                "Adjust frontend evidence",
                "--select",
                "test_strategy_check",
                "--format",
                "json",
            ]
        )
        == 0
    )

    check = json.loads(capsys.readouterr().out)["values"]["test_strategy_check"]
    assert check["status"] == "advisory"
    assert check["changed_test_paths"] == ["web/specs/checkout.spec.ts"]
    guardrail = check["pre_test_evidence_guardrail"]
    assert guardrail["status"] == "advisory"
    assert guardrail["source_boundary"]["no_universal_filename_policy"] is True
    assert guardrail["evidence_path_classifications"] == [
        {
            "path": "web/specs/checkout.spec.ts",
            "source": "assurance.requirements.frontend_evidence_change",
            "matched_by": "assurance.applies_to_paths",
            "pattern": "web/specs/*.spec.ts",
            "authority_refs": [],
        }
    ]
    assert check["files"][0]["path"] == "web/specs/checkout.spec.ts"
    assert check["files"][0]["test_function_count"] == 0


def test_implement_tiny_omits_not_applicable_test_strategy_advisory(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "runtime.py", "def runtime_value():\n    return 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/runtime.py",
                "--task",
                "Adjust runtime behavior",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "test_strategy_check" not in payload["action_signals"]["advisory_detail"]["selectors"]
    assert "test_strategy_check" not in payload["drill_down"]["available_selectors"]
    assert "context.test_strategy_check" not in payload["drill_down"]["available_selectors"]
    assert "test_strategy_check" not in payload["context"]


def test_test_strategy_check_degrades_without_target_suite_budget(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write_python_test_evidence_config(tmp_path)
    _write(
        tmp_path / "tests" / "test_runtime.py",
        """
def test_runtime_alpha(): assert True
def test_runtime_beta(): assert True
def test_runtime_gamma(): assert True
def test_runtime_delta(): assert True
def test_runtime_epsilon(): assert True
def test_runtime_zeta(): assert True
def test_runtime_eta(): assert True
def test_runtime_theta(): assert True
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "tests/test_runtime.py",
                "--select",
                "test_strategy_check",
                "--format",
                "json",
            ]
        )
        == 0
    )

    check = json.loads(capsys.readouterr().out)["values"]["test_strategy_check"]
    assert check["budget_drift"]["status"] == "not-configured"
    assert check["budget_drift"]["budget_source"]["path"] == ".agentic-workspace/verification/test-suite-budget.json"
    assert check["budget_drift"]["root"]["status"] == "not-configured"
    assert check["budget_drift"]["over_budget_hotspot_files_requiring_disposition"] == []


def test_test_strategy_check_reads_recorded_disposition(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write_python_test_evidence_config(tmp_path)
    _write_test_suite_budget(tmp_path)
    _write(
        tmp_path / "tests" / "test_runtime.py",
        """
def test_runtime_alpha(): assert True
def test_runtime_beta(): assert True
def test_runtime_gamma(): assert True
def test_runtime_delta(): assert True
def test_runtime_epsilon(): assert True
def test_runtime_zeta(): assert True
def test_runtime_eta(): assert True
def test_runtime_theta(): assert True
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "verification" / "test-strategy-dispositions.json",
        {
            "kind": "agentic-workspace/test-strategy-dispositions/v1",
            "items": [
                {
                    "id": "runtime-matrix",
                    "disposition": "matrix-merge",
                    "changed_test_paths": ["tests/test_runtime.py"],
                    "reason": "The change keeps related behavior cases in one scenario matrix.",
                    "proof_owner": "root-orchestration",
                    "replacement_or_follow_up_evidence": ["scenario labels retained"],
                    "reviewer_requested_coverage": True,
                }
            ],
        },
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "tests/test_runtime.py",
                "--task",
                "Address reviewer requested coverage",
                "--select",
                "test_strategy_check",
                "--format",
                "json",
            ]
        )
        == 0
    )

    check = json.loads(capsys.readouterr().out)["values"]["test_strategy_check"]
    assert check["disposition_record"]["status"] == "recorded"
    assert check["disposition_record"]["matched_count"] == 1
    assert check["recorded_disposition"]["id"] == "runtime-matrix"
    assert check["missing_disposition_paths"] == []
    assert check["budget_drift"]["status"] == "attention"
    assert check["budget_drift"]["changed_hotspot_files"] == ["tests/test_runtime.py"]
    assert check["budget_drift"]["disposition_paths"] == ["tests/test_runtime.py"]
    assert check["budget_drift"]["over_budget_hotspot_files_requiring_disposition"] == []
    assert check["disposition_required_before_closeout"] is False


def test_test_strategy_check_distinguishes_non_material_retained_test_edit(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=tmp_path, check=True)
    _write_empty_planning_state(tmp_path)
    _write_python_test_evidence_config(tmp_path)
    _write_test_suite_budget(tmp_path)
    _write(tmp_path / "tests" / "test_runtime.py", "def test_runtime_case():\n    assert True\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True, text=True)
    _write(tmp_path / "tests" / "test_runtime.py", "def test_runtime_case():\n    assert 1 == 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "tests/test_runtime.py",
                "--select",
                "test_strategy_check",
                "--format",
                "json",
            ]
        )
        == 0
    )

    check = json.loads(capsys.readouterr().out)["values"]["test_strategy_check"]
    materiality = check["files"][0]["materiality"]
    assert materiality["change_state"] == "modified"
    assert materiality["test_function_count_delta"] == 0
    assert materiality["material_evidence_change"] is False
    assert materiality["route_pressure"] == "ordinary-test-edit"
    assert check["material_evidence_change_count"] == 0
    assert check["budget_drift"]["status"] == "context"
    assert check["budget_drift"]["changed_root_test_paths"] == ["tests/test_runtime.py"]
    assert check["budget_drift"]["changed_hotspot_files"] == []
    assert check["budget_drift"]["over_budget_hotspot_files_requiring_disposition"] == []
    assert check["disposition_required_before_closeout"] is False


def test_test_strategy_check_marks_package_local_budget_context(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=tmp_path, check=True)
    _write_empty_planning_state(tmp_path)
    _write_test_suite_budget(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[workspace]
cli_invoke = "uv run python scripts/run_agentic_workspace.py"

[assurance.requirements.package_test_evidence_change_decision]
level = "high"
applies_to_paths = ["packages/memory/tests/**"]
required_evidence = ["verification_proof_decision_review"]
proof_profile = "test_evidence_change"
review_owner = "maintainer"
force = "required-before-closeout"
""",
    )
    _write(tmp_path / "packages" / "memory" / "tests" / "test_runtime.py", "def test_runtime_case():\n    assert True\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True, text=True)
    _write(tmp_path / "packages" / "memory" / "tests" / "test_runtime.py", "def test_runtime_case():\n    assert 1 == 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/memory/tests/test_runtime.py",
                "--select",
                "test_strategy_check",
                "--format",
                "json",
            ]
        )
        == 0
    )

    check = json.loads(capsys.readouterr().out)["values"]["test_strategy_check"]
    assert check["budget_drift"]["status"] == "package-local"
    assert check["budget_drift"]["changed_package_local_test_paths"] == ["packages/memory/tests/test_runtime.py"]
    assert check["budget_drift"]["changed_root_test_paths"] == []
    assert check["budget_drift"]["changed_hotspot_files"] == []
    assert check["disposition_required_before_closeout"] is False


def test_test_strategy_check_marks_added_test_as_material(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=tmp_path, check=True)
    _write_empty_planning_state(tmp_path)
    _write_python_test_evidence_config(tmp_path)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True, text=True)
    _write(tmp_path / "tests" / "test_runtime.py", "def test_runtime_case():\n    assert True\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "tests/test_runtime.py",
                "--select",
                "test_strategy_check",
                "--format",
                "json",
            ]
        )
        == 0
    )

    check = json.loads(capsys.readouterr().out)["values"]["test_strategy_check"]
    materiality = check["files"][0]["materiality"]
    assert materiality["change_state"] == "added"
    assert materiality["material_evidence_change"] is True
    assert materiality["route_pressure"] == "proof-decision"
    assert check["material_evidence_change_count"] == 1
    assert check["disposition_required_before_closeout"] is True


def test_test_strategy_check_marks_deleted_test_as_material(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=tmp_path, check=True)
    _write_empty_planning_state(tmp_path)
    _write_python_test_evidence_config(tmp_path)
    _write(tmp_path / "tests" / "test_runtime.py", "def test_runtime_case():\n    assert True\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True, text=True)
    (tmp_path / "tests" / "test_runtime.py").unlink()

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "tests/test_runtime.py",
                "--select",
                "test_strategy_check",
                "--format",
                "json",
            ]
        )
        == 0
    )

    materiality = json.loads(capsys.readouterr().out)["values"]["test_strategy_check"]["files"][0]["materiality"]
    assert materiality["change_state"] == "deleted"
    assert materiality["material_evidence_change"] is True
    assert materiality["route_pressure"] == "proof-decision"


def test_test_strategy_check_marks_count_change_as_material(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=tmp_path, check=True)
    _write_empty_planning_state(tmp_path)
    _write_python_test_evidence_config(tmp_path)
    _write(tmp_path / "tests" / "test_runtime.py", "def test_runtime_case():\n    assert True\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True, text=True)
    _write(
        tmp_path / "tests" / "test_runtime.py",
        "def test_runtime_case():\n    assert True\n\n\ndef test_runtime_other():\n    assert True\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "tests/test_runtime.py",
                "--select",
                "test_strategy_check",
                "--format",
                "json",
            ]
        )
        == 0
    )

    materiality = json.loads(capsys.readouterr().out)["values"]["test_strategy_check"]["files"][0]["materiality"]
    assert materiality["change_state"] == "modified"
    assert materiality["test_function_count_delta"] == 1
    assert materiality["material_evidence_change"] is True


def test_test_strategy_check_marks_renamed_test_as_material(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=tmp_path, check=True)
    _write_empty_planning_state(tmp_path)
    _write_python_test_evidence_config(tmp_path)
    _write(tmp_path / "tests" / "test_runtime.py", "def test_runtime_case():\n    assert True\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "mv", "tests/test_runtime.py", "tests/test_runtime_new.py"], cwd=tmp_path, check=True)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "tests/test_runtime_new.py",
                "--select",
                "test_strategy_check",
                "--format",
                "json",
            ]
        )
        == 0
    )

    materiality = json.loads(capsys.readouterr().out)["values"]["test_strategy_check"]["files"][0]["materiality"]
    assert materiality["change_state"] == "renamed"
    assert materiality["material_evidence_change"] is True


def test_test_strategy_check_requires_temporary_follow_up_evidence(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write_python_test_evidence_config(tmp_path)
    _write(tmp_path / "tests" / "test_runtime.py", "def test_runtime_case():\n    assert True\n")
    _write_json(
        tmp_path / ".agentic-workspace" / "verification" / "test-strategy-dispositions.json",
        {
            "kind": "agentic-workspace/test-strategy-dispositions/v1",
            "items": [
                {
                    "id": "temporary-runtime",
                    "disposition": "temporary-with-follow-up-consolidation",
                    "changed_test_paths": ["tests/test_runtime.py"],
                    "reason": "Reviewer requested temporary coverage before consolidation.",
                    "proof_owner": "root-orchestration",
                    "reviewer_requested_coverage": True,
                }
            ],
        },
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "tests/test_runtime.py",
                "--select",
                "test_strategy_check",
                "--format",
                "json",
            ]
        )
        == 0
    )

    check = json.loads(capsys.readouterr().out)["values"]["test_strategy_check"]
    assert check["temporary_dispositions_missing_follow_up"] == ["temporary-runtime"]
    assert check["disposition_required_before_closeout"] is True


def test_proof_surfaces_test_strategy_check_for_closeout_visibility(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write_python_test_evidence_config(tmp_path)
    _write(tmp_path / "tests" / "test_runtime.py", "def test_runtime_contract():\n    assert True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "tests/test_runtime.py",
                "--select",
                "test_strategy_check",
                "--format",
                "json",
            ]
        )
        == 0
    )

    check = json.loads(capsys.readouterr().out)["values"]["test_strategy_check"]
    assert check["kind"] == "agentic-workspace/test-strategy-check/v1"
    assert check["status"] == "advisory"
    assert check["closeout_visibility"]["missing_disposition_blocks_claim"] == "test-sustainability-reviewed"

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "tests/test_runtime.py",
                "--select",
                "completion_options",
                "--format",
                "json",
            ]
        )
        == 0
    )
    options = json.loads(capsys.readouterr().out)["values"]["completion_options"]
    route_residue = next(option for option in options if option["id"] == "route-residue")
    assert route_residue["blocking_fields"] == ["test_strategy_check.recorded_disposition"]


def test_implement_blocks_parent_lane_slice_without_lane_owner_artifact(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "slice-one", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/slice-one.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "slice-one.plan.json",
        json.dumps(
            {
                "schema_version": "execplan/v1",
                "id": "slice-one",
                "status": "active",
                "parent_lane": {"id": "parent-lane", "label": "Parent lane"},
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                "--task",
                "Continue the active planning work",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["context"]["planning_safety_gate"]
    assert gate["status"] == "blocked"
    assert gate["gate_result"] == "lane-owner-artifact-required"
    assert gate["implementation_allowed"] is False
    owner = gate["hierarchy_owner_requirement"]
    assert owner["status"] == "missing-lane-owner-artifact"
    assert owner["lane_id"] == "parent-lane"
    assert ".agentic-workspace/planning/lanes/parent-lane.lane.json" in owner["required_before_implementation"][0]
    assert "planning lane-create --id parent-lane --target ." in owner["command"]


def test_implement_blocks_active_parent_lane_slice_with_invalid_lane_owner_artifact(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_planning_lane_schema(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "slice-one", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/slice-one.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "lanes" / "parent-lane.lane.json",
        {
            "kind": "planning-lane/v1",
            "id": "parent-lane",
            "title": "Malformed parent lane",
            "status": "active",
            "parent_close_permission": "not-allowed",
        },
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "slice-one.plan.json",
        json.dumps(
            {
                "schema_version": "execplan/v1",
                "id": "slice-one",
                "status": "active",
                "parent_lane": {"id": "parent-lane", "label": "Parent lane"},
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                "--task",
                "Continue the active planning work",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["context"]["planning_safety_gate"]
    assert gate["status"] == "blocked"
    assert gate["gate_result"] == "lane-owner-artifact-required"
    assert gate["implementation_allowed"] is False
    owner = gate["hierarchy_owner_requirement"]
    assert owner["status"] == "missing-or-invalid-lane-owner-artifact"
    assert owner["lane_id"] == "parent-lane"
    assert owner["invalid_lane_record"] == ".agentic-workspace/planning/lanes/parent-lane.lane.json"
    assert owner["validation_errors"]
    assert any("parent_close_permission" in error for error in owner["validation_errors"])
    assert "planning lane-create --id parent-lane --target ." in owner["command"]


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
    assert payload["planning_safety_gate"]["status"] == "attention"
    assert payload["planning_safety_gate"]["gate_result"] == "external-issue-scope-unknown"
    assert payload["planning_safety_gate"]["implementation_allowed"] is True
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


def test_implement_objective_drift_does_not_accept_deleted_outcome_from_prompt_keywords(tmp_path: Path, capsys) -> None:
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
    assert drift["status"] == "warning"
    assert drift["requested_outcomes"] == ["llms.txt"]
    assert drift["removed_or_retired_outcomes"] == []
    assert drift["missing_from_changed_surface"] == ["llms.txt"]
    assert "does not infer removal or retirement intent from prompt keywords" in drift["heuristic"]
    assert "whether a missing requested outcome was intentionally removed" in drift["agent_owned_decisions"][0]


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
    assert posture["capability_posture"]["scope_evidence"]["scope_signal"] == "bounded"
    assert posture["capability_posture"]["scope_evidence"]["agent_decision_required"] is True
    assert posture["capability_posture"]["proof_factors"]["proof_pressure"] == "high"
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
    assert posture["delegation_decision"]["recommended_route"] == "suggest-escalation"
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
    assert "work_shape_hint" not in json.dumps(posture["delegation_decision"])
    assert "quality_factors" not in posture["delegation_decision"]
    assert posture["delegation_decision"]["route_evidence"]["scope_signal"] == "bounded"
    assert "semantic task classification" in posture["delegation_decision"]["route_evidence"]["rule"]


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
    assert decision["recommended_route"] == "delegate-bounded-slice"
    assert decision["target"] == "mini"
    assert decision["required_next_action"] == "execute-when-safe"
    assert decision["token_savings_guidance"]["signal"] == "likely"
    assert decision["route_evidence"]["scope_signal"] == "bounded"
    assert decision["route_evidence"]["agent_judgment_required"] is True
    effort = decision["effort_guidance"]
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
    assert decision["recommended_route"] == "suggest-delegation"
    assert decision["target"] == "reusable-worker"
    assert decision["required_next_action"] == "select-or-promote-bounded-lane"
    assert decision["token_savings_guidance"]["signal"] == "possible"
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
    assert decision["delegation_candidates"][0]["candidate_route"] == "delegate-exploration"
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
    context = _implement_context(payload)
    assert "delegation_decision" not in context
    payload_text = json.dumps(payload)
    assert "manual_external_relay" not in payload_text
    assert "manual_prompt" not in payload_text
    assert "handoff_command" not in payload_text


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
                "context.delegation_decision.required_next_action,context.delegation_decision.delegation_next_step.must_report_if_not_run,context.delegation_decision.effort_guidance.cost_posture",
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
    assert (
        payload["payload_locations"]["selected_payload_paths"]["context.delegation_decision.required_next_action"]
        == 'values["context.delegation_decision.required_next_action"]'
    )
    assert payload["values"]["context.delegation_decision.required_next_action"] == "execute-when-safe"
    assert payload["values"]["context.delegation_decision.delegation_next_step.must_report_if_not_run"] is True
    assert payload["values"]["context.delegation_decision.effort_guidance.cost_posture"] == "save-tokens-where-safe"


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
    assert payload["values"]["context.workflow_sufficiency"]["sufficiency_result"] == "enough-for-bounded-implementation"


def test_implement_reuse_pressure_ignores_dependency_cache_definitions(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )
    _write(
        tmp_path / "packages" / "planning" / ".uv-cache" / "archive-v0" / "dependency" / "text.py",
        "def normalize_text(value):\n    return value\n",
    )
    _write(
        tmp_path / ".venv" / "Lib" / "site-packages" / "dependency" / "text.py",
        "def normalize_text(value):\n    return value\n",
    )

    original_is_file = Path.is_file

    def fail_if_dependency_tree_is_inspected(path: Path) -> bool:
        relative_parts = path.relative_to(tmp_path).parts if path.is_relative_to(tmp_path) else path.parts
        assert ".venv" not in relative_parts
        assert ".uv-cache" not in relative_parts
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", fail_if_dependency_tree_is_inspected)

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


def test_implement_reuse_pressure_honors_gitignore_for_ordinary_scan(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    _write(tmp_path / ".gitignore", "src/sample_app/ignored_helper.py\n")
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )
    _write(
        tmp_path / "src" / "sample_app" / "ignored_helper.py",
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
    assert reuse_pressure["weak_hints"] == []


def test_implement_reuse_pressure_skips_workspace_local_scratch(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )
    _write(
        tmp_path / ".agentic-workspace" / "local" / "scratch" / "external-repo" / "helpers.py",
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
    assert reuse_pressure["state"] == "similar_pattern_candidate"
    finding = next(item for item in reuse_pressure["findings"] if item["kind"] == "repeated_special_case")
    assert finding["evidence_confidence"] == "medium"
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
    assert "--target ." in reuse_pressure["memory_signals"]["route_command"]


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
    assert payload["values"]["context.workflow_sufficiency"]["sufficiency_result"] == "enough-for-bounded-implementation"


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
    inventory = payload["selector_inventory"]
    assert inventory["status"] == "omitted-from-compact-default"
    assert inventory["available_count"] > len(inventory["sample"])
    assert len(inventory["sample"]) <= 8
    assert "available_selectors" not in payload
