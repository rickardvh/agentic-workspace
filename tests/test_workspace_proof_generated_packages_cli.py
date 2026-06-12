from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def _proof_select(capsys, *args: str, select: str) -> dict[str, object]:
    assert cli.main(["proof", *args, "--select", select, "--format", "json"]) == 0
    return json.loads(capsys.readouterr().out)["values"]


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
    assert "uv run python scripts/check/check_generated_command_packages.py --conformance --require-node" in lane["required_commands"]


def test_proof_changed_selector_routes_generated_command_packages(capsys) -> None:
    answer = _proof_select(
        capsys,
        "--changed",
        "generated/workspace/typescript/src/commandPackage.ts",
        select="selected_lanes,required_commands,validation_plan,generated_cli_freshness,selected_commands,cli_authority_review",
    )

    assert answer["selected_lanes"][0]["id"] == "generated_command_packages"
    assert answer["selected_lanes"][0]["proof_responsibility"] == "local-serial"
    assert answer["selected_lanes"][0]["execution_mode"] == "serial"
    weak_agent_routing = answer["selected_lanes"][0]["weak_agent_safe_routing"]
    assert weak_agent_routing["status"] == "proof-gated"
    assert "generated-package static plus conformance proof pass" in weak_agent_routing["rule"]
    assert "serially" in answer["selected_lanes"][0]["ci_relationship"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "generated_command_packages",
        "cli_authority",
        "verification:generated_adapter_conformance",
    ]
    assert "route back through command-package checks" in answer["selected_lanes"][0]["recovery_signal"]
    freshness = answer["generated_cli_freshness"]
    assert freshness["status"] == "required"
    assert freshness["freshness_check_command"] == "uv run python scripts/generate/generate_command_packages.py --check"
    assert freshness["refresh_command"] == "uv run python scripts/generate/generate_command_packages.py"
    assert freshness["validation_command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert "uv run python scripts/check/check_generated_command_packages.py" in freshness["required_commands"]
    assert "refresh only when the check reports stale output" in freshness["rule"]
    focused_proof = "uv run pytest tests/test_workspace_proof_generated_packages_cli.py -q"
    assert answer["required_commands"] == [
        "uv run python scripts/check/check_generated_command_packages.py",
        "uv run python scripts/check/run_operation_conformance_tests.py --target all",
        "uv run python scripts/check/check_generated_command_packages.py --conformance --require-node",
        "uv run python scripts/check/check_generated_command_packages.py --docker --require-docker",
        "uv run python scripts/check/check_generated_command_packages.py --docker-conformance --require-docker",
        focused_proof,
        f"{REPO_LOCAL_CLI_INVOKE} defaults --section root_cli_authority --format json",
        "uv run python scripts/generate/generate_command_packages.py --check",
        "uv run python scripts/check/check_generated_command_packages.py --require-node",
    ]
    assert [step["lane_id"] for step in answer["validation_plan"]["required"]] == [
        "generated_command_packages",
        "generated_command_packages",
        "generated_command_packages",
        "generated_command_packages",
        "generated_command_packages",
        "generated_command_packages",
        "cli_authority",
        "verification:generated_adapter_conformance",
        "verification:generated_adapter_conformance",
    ]
    generated_steps = [step for step in answer["validation_plan"]["required"] if step["lane_id"] == "generated_command_packages"]
    assert {step["execution_mode"] for step in generated_steps} == {"serial"}
    assert {step["proof_responsibility"] for step in generated_steps} == {"local-serial"}
    assert all("serially" in step["ci_relationship"] for step in generated_steps)
    generated_commands = [command for command in answer["selected_commands"] if command["lane"] == "generated_command_packages"]
    assert {command["execution_mode"] for command in generated_commands} == {"serial"}
    assert {command["proof_responsibility"] for command in generated_commands} == {"local-serial"}
    assert focused_proof in [command["command"] for command in generated_commands]
    assert "tests/test_workspace_proof_cli.py" not in " ".join(answer["required_commands"])
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

    focused_proof = "uv run pytest tests/test_workspace_proof_generated_packages_cli.py -q"
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "generated_command_packages",
        "cli_authority",
        "subsystem:workspace-cli-runtime",
        "verification:generated_adapter_conformance",
    ]
    assert answer["required_commands"] == [
        "uv run python scripts/check/check_generated_command_packages.py",
        "uv run python scripts/check/run_operation_conformance_tests.py --target python",
        "uv run python scripts/check/check_generated_command_packages.py --python-conformance",
        "uv run python scripts/check/check_generated_command_packages.py --python-docker-conformance --require-docker",
        focused_proof,
        f"{REPO_LOCAL_CLI_INVOKE} defaults --section root_cli_authority --format json",
        "uv run pytest tests/test_workspace_cli.py -q",
        "uv run python scripts/generate/generate_command_packages.py --check",
        "uv run python scripts/check/check_generated_command_packages.py --require-node",
        "uv run python scripts/check/check_generated_command_packages.py --conformance --require-node",
        "uv run python scripts/check/check_generated_command_packages.py --docker --require-docker",
        "uv run python scripts/check/check_generated_command_packages.py --docker-conformance --require-docker",
    ]
    assert (
        "uv run python scripts/check/check_generated_command_packages.py --python-docker-conformance --require-docker"
        in answer["required_commands"]
    )
    assert focused_proof in answer["required_commands"]
    assert "tests/test_workspace_proof_cli.py" not in " ".join(answer["required_commands"])
    assert "CI may repeat generated-package proof" in answer["selected_lanes"][0]["ci_relationship"]
    generated_steps = [step for step in answer["validation_plan"]["required"] if step["lane_id"] == "generated_command_packages"]
    assert generated_steps
    assert {step["execution_mode"] for step in generated_steps} == {"serial"}
    assert all("serially" in step["ci_relationship"] for step in generated_steps)


def test_proof_changed_selector_routes_contract_only_changes_to_focused_lane(capsys) -> None:
    answer = _proof_select(
        capsys,
        "--changed",
        "src/agentic_workspace/contracts/structured_file_inventory.json",
        "scripts/check/check_structured_file_inventory.py",
        "tests/test_structured_file_inventory.py",
        select="selected_lanes,required_commands",
    )

    assert [lane["id"] for lane in answer["selected_lanes"]] == ["contract_tooling"]
    assert answer["required_commands"] == [
        "uv run python scripts/check/check_contract_tooling_surfaces.py --quiet-success",
        "uv run python scripts/check/check_structured_file_inventory.py --quiet-success",
        "uv run ruff check src/agentic_workspace/contracts scripts/check tests/test_structured_file_inventory.py",
    ]
    assert "generated_cli_freshness" not in answer
    assert "uv run pytest tests -q" not in answer["required_commands"]
