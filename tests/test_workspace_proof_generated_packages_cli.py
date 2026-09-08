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
    assert (
        "uv run python scripts/check/check_generated_command_packages.py --conformance --require-node"
        in lane["focused_route_reduction"]["withheld_commands"]
    )
