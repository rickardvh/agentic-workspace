from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def _proof_select(capsys, *args: str, select: str) -> dict[str, object]:
    assert cli.main(["proof", *args, "--select", select, "--format", "json"]) == 0
    return json.loads(capsys.readouterr().out)["values"]


def _stable_lane_ids(answer: dict[str, object]) -> list[str]:
    return [lane["id"] for lane in answer["selected_lanes"] if not lane["id"].startswith(("concern:", "assurance-requirement:"))]


def test_proof_routes_generated_adapter_path_to_repo_verification_protocol(capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    answer = _proof_select(
        capsys,
        "--target",
        str(repo_root),
        "--changed",
        "src/agentic_workspace/contracts/command_package_ir.json",
        select="verification,selected_lanes",
    )

    assert answer["verification"]["active_protocols"][0]["id"] == "generated_adapter_conformance"
    lanes = {lane["id"]: lane for lane in answer["selected_lanes"]}
    assert "verification:generated_adapter_conformance" in lanes
    lane = lanes["verification:generated_adapter_conformance"]
    assert lane["verification_proof_route_ids"] == ["generated_adapter_conformance"]
    assert (
        "uv run python scripts/check/check_generated_command_packages.py --conformance --require-node"
        in lane["focused_route_reduction"]["withheld_commands"]
    )


def test_proof_changed_selector_routes_generated_command_packages(capsys) -> None:
    answer = _proof_select(
        capsys,
        "--changed",
        "generated/workspace/typescript/src/commandPackage.ts",
        select="selected_lanes,required_commands,validation_plan,generated_cli_freshness,selected_commands,cli_authority_review,proof_command_tiers,proof_next_decision",
    )

    assert answer["selected_lanes"][0]["id"] == "generated_command_packages"
    assert answer["selected_lanes"][0]["proof_responsibility"] == "local-serial"
    assert answer["selected_lanes"][0]["execution_mode"] == "serial"
    weak_agent_routing = answer["selected_lanes"][0]["weak_agent_safe_routing"]
    assert weak_agent_routing["status"] == "proof-gated"
    assert "generated-package static plus conformance proof pass" in weak_agent_routing["rule"]
    assert "serially" in answer["selected_lanes"][0]["ci_relationship"]
    assert _stable_lane_ids(answer) == [
        "generated_command_packages",
        "cli_authority",
        "verification:generated_adapter_conformance",
        "domain:generated_command_packages",
    ]
    assert "route back through command-package checks" in answer["selected_lanes"][0]["recovery_signal"]
    freshness = answer["generated_cli_freshness"]
    assert freshness["status"] == "required"
    assert freshness["freshness_check_command"] == "uv run python scripts/generate/generate_command_packages.py --check"
    assert freshness["refresh_command"] == "uv run python scripts/generate/generate_command_packages.py"
    assert freshness["validation_command"] == "uv run --active python scripts/check/check_generated_command_packages.py --require-node"
    assert "uv run --active python scripts/check/check_generated_command_packages.py --require-node" in freshness["required_commands"]
    assert "refresh only when the check reports stale output" in freshness["rule"]
    assert answer["required_commands"] == [
        "uv run --frozen --active --no-sync python scripts/run_agentic_workspace.py defaults --section root_cli_authority --format json",
        "uv run --active python scripts/check/check_generated_command_packages.py --require-node",
        "uv run --active python scripts/check/check_generated_command_packages.py --conformance --require-node",
    ]
    assert [step["lane_id"] for step in answer["validation_plan"]["required"]] == [
        "cli_authority",
        "domain:generated_command_packages",
        "domain:generated_command_packages",
    ]
    domain_lane = answer["selected_lanes"][-1]
    assert domain_lane["route_authority"]["authority"] == "repo-owned-domain-proof-lane"
    assert domain_lane["domain_lane"]["source"] == ".agentic-workspace/config.toml [assurance.domain_proof_lanes]"
    domain_commands = [command for command in answer["selected_commands"] if command["lane"] == "domain:generated_command_packages"]
    assert [command["command"] for command in domain_commands] == [
        "uv run --active python scripts/check/check_generated_command_packages.py --require-node",
        "uv run --active python scripts/check/check_generated_command_packages.py --conformance --require-node",
    ]
    assert {command["execution_mode"] for command in domain_commands} == {"serial-recommended"}
    assert {command["proof_responsibility"] for command in domain_commands} == {"local-closeout"}
    assert all("--changed <paths> --verbose" in command["detail_route"] for command in domain_commands)
    assert all(
        set(command).isdisjoint({"subject_contract", "receipt_contract", "progress_contract", "route_provenance"})
        for command in domain_commands
    )
    withheld = answer["selected_lanes"][0]["focused_route_reduction"]["withheld_commands"]
    assert "uv run pytest tests/test_workspace_proof_generated_packages_cli.py -q" in withheld
    assert "uv run python scripts/check/check_generated_command_packages.py --docker --require-docker" in withheld
    assert "tests/test_workspace_proof_cli.py" not in " ".join(answer["required_commands"])
    tier_commands = [item for tier in answer["proof_command_tiers"]["tiers"] for item in tier["commands"]]
    focused = next(item for item in tier_commands if item["command"] == domain_commands[0]["command"])
    assert (focused["execution_class"], focused["posture"]) == ("focused-local", "required")
    ci_owned = [item for item in tier_commands if item["execution_class"] == "exhaustive-CI-owned"]
    assert ci_owned and all(item["posture"] == "optional" and item["execution_owner"] == "CI" for item in ci_owned)
    assert answer["proof_next_decision"]["next"]["command"] not in {item["command"] for item in ci_owned}
    assert answer["validation_plan"]["required_count"] == len(answer["required_commands"])
    assert answer["validation_plan"]["optional"][0]["required"] is False
    review = answer["cli_authority_review"]
    assert review["status"] == "blocked-direct-edit-route-to-source"
    assert review["blocked_direct_edit_paths"] == ["generated/workspace/typescript/src/commandPackage.ts"]
    generated = review["classifications"][0]
    assert generated["role"] == "projection"
    assert generated["direct_edit_allowed"] is False
    assert generated["source_contract"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert generated["regeneration_path"] == "uv run python scripts/check/check_generated_command_packages.py"


def test_proof_changed_selector_routes_python_generated_packages_to_python_docker(capsys) -> None:
    answer = _proof_select(
        capsys,
        "--changed",
        "generated/workspace/python/__init__.py",
        "scripts/check/check_generated_command_packages.py",
        select="selected_lanes,required_commands,validation_plan,selected_commands",
    )

    assert _stable_lane_ids(answer) == [
        "generated_command_packages",
        "cli_authority",
        "subsystem:workspace-cli-runtime",
        "verification:closeout_intent_satisfaction",
        "verification:generated_adapter_conformance",
        "verification:repo_acceptance_policy",
        "verification:requirement_grounding_delegation",
        "domain:generated_command_packages",
    ]
    assert answer["required_commands"] == [
        "uv run --frozen --active --no-sync python scripts/run_agentic_workspace.py defaults --section root_cli_authority --format json",
        "uv run --active python scripts/run_agentic_workspace.py report --target . --section closeout_trust --format json",
        "uv run --active python scripts/run_agentic_workspace.py implement --target . --changed <paths> --select assurance_requirements --format json",
        "uv run --active pytest tests/test_workspace_cli.py tests/test_workspace_proof_cli.py tests/test_workspace_session_logging.py -k 'upgrade_unknown_selector or upgrade_selector_inventory or process_status_matches_typed_selected_execution_failure or lifecycle_typed_selector_failure_and_session_process_status_agree' -q",
        "uv run --active pytest tests/test_summary_exact_selector_performance.py tests/test_workspace_proof_cli.py -k 'exact_summary_selectors_are_clean_process_history_independent or leaves_tracked_receipt_store_unchanged' -q",
        "uv run --active pytest tests/test_instruction_clause_ir.py tests/test_scoped_instructions.py tests/test_workspace_config_cli.py -q",
        "uv run --active python scripts/run_agentic_workspace.py implement --changed <paths> --select requirement_grounding,context.delegation_decision,context.plan_delegation_packet --format json",
        "uv run --active python scripts/check/check_generated_command_packages.py --require-node",
        "uv run --active python scripts/check/check_generated_command_packages.py --conformance --require-node",
    ]
    withheld = answer["selected_lanes"][0]["focused_route_reduction"]["withheld_commands"]
    assert "uv run python scripts/check/check_generated_command_packages.py --python-docker-conformance --require-docker" in withheld
    assert "uv run pytest tests/test_workspace_proof_generated_packages_cli.py -q" in withheld
    assert "uv run pytest tests/test_workspace_cli.py -q" not in answer["required_commands"]
    subsystem_lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "subsystem:workspace-cli-runtime")
    assert subsystem_lane["focused_route_reduction"]["status"] == "broad-proof-withheld-for-explicit-escalation"
    assert "uv run pytest tests/test_workspace_cli.py -q" in subsystem_lane["focused_route_reduction"]["withheld_commands"]
    assert "CI may repeat generated-package proof" in answer["selected_lanes"][0]["ci_relationship"]
    domain_commands = [command for command in answer["selected_commands"] if command["lane"] == "domain:generated_command_packages"]
    assert [command["command"] for command in domain_commands] == [
        "uv run --active python scripts/check/check_generated_command_packages.py --require-node",
        "uv run --active python scripts/check/check_generated_command_packages.py --conformance --require-node",
    ]
    assert {command["execution_mode"] for command in domain_commands} == {"serial-recommended"}
    assert "make test-workspace" not in answer["required_commands"]
    assert "make lint-workspace" not in answer["required_commands"]


def test_proof_changed_selector_routes_contract_only_changes_to_focused_lane(capsys) -> None:
    answer = _proof_select(
        capsys,
        "--changed",
        "src/agentic_workspace/contracts/structured_file_inventory.json",
        "scripts/check/check_structured_file_inventory.py",
        "tests/test_structured_file_inventory.py",
        select="selected_lanes,required_commands,selected_commands",
    )

    assert _stable_lane_ids(answer) == [
        "contract_tooling",
        "verification:aw_context_consistency",
        "verification:test_evidence_decision",
        "domain:compact_output_contract",
        "domain:test_evidence_decision",
    ]
    assert answer["required_commands"] == [
        "uv run --active python scripts/check/check_contract_tooling_surfaces.py --quiet-success",
        "uv run --active python scripts/check/check_structured_file_inventory.py --quiet-success",
        "uv run --active ruff check src/agentic_workspace/contracts scripts/check tests/test_structured_file_inventory.py",
        "uv run --active python scripts/run_agentic_workspace.py report --target . --section verification --format json",
        "uv run --active python scripts/check/check_memory_freshness.py --strict",
        "uv run --active pytest tests/test_output_profile_budgets.py -q",
        "uv run --active python scripts/generate/generate_command_packages.py --check",
    ]
    domain_commands = [command for command in answer["selected_commands"] if command["lane"] == "domain:test_evidence_decision"]
    assert [command["command"] for command in domain_commands] == [
        "uv run --active python scripts/run_agentic_workspace.py report --target . --section verification --format json",
    ]
    assert "generated_cli_freshness" not in answer
    assert "uv run pytest tests -q" not in answer["required_commands"]
