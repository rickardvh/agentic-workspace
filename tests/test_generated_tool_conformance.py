from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
from repo_planning_bootstrap.generated_command_adapters import (
    GENERATED_COMMAND_ADAPTERS_BY_COMMAND as GENERATED_PLANNING_COMMAND_ADAPTERS_BY_COMMAND,
)

from agentic_workspace.conformance import materialize_fixture, run_process_conformance
from agentic_workspace.contract_tooling import conformance_contract_manifest, conformance_contracts_manifest
from agentic_workspace.generated_command_adapters import GENERATED_COMMAND_ADAPTERS_BY_COMMAND

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_SHIM = (
    "import sys; "
    f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r}); "
    "from agentic_workspace.cli import main; "
    "raise SystemExit(main(sys.argv[1:]))"
)
PLANNING_CLI_SHIM = (
    "import sys; "
    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'planning' / 'src')!r}); "
    "from repo_planning_bootstrap.cli import main; "
    "raise SystemExit(main(sys.argv[1:]))"
)


def _contract_refs() -> list[dict[str, str]]:
    return [dict(item) for item in conformance_contracts_manifest()["contracts"]]


@pytest.mark.parametrize("contract_ref", _contract_refs(), ids=lambda item: item["id"])
def test_generated_tool_process_conformance_contracts(contract_ref: dict[str, str], tmp_path: Path) -> None:
    contract = conformance_contract_manifest(contract_ref["path"])
    fixture_root = tmp_path / contract["fixtures"][0]["id"]
    materialize_fixture(fixture=contract["fixtures"][0], fixture_root=fixture_root)

    run_process_conformance(
        contract=contract,
        fixture_root=fixture_root,
        repo_root=fixture_root,
        command_overrides={
            "agentic_workspace_cli": [sys.executable, "-c", CLI_SHIM],
            "agentic_planning_cli": [sys.executable, "-c", PLANNING_CLI_SHIM],
        },
    )


def test_process_conformance_harness_catches_forbidden_writes(tmp_path: Path) -> None:
    contract = copy.deepcopy(conformance_contract_manifest("conformance/defaults.report.process.json"))
    contract["adapter"]["command_template"] = [
        "{python}",
        "-c",
        (
            "from pathlib import Path; "
            "Path('.agentic-workspace').mkdir(); "
            'print(\'{"profile":"compact-contract-answer/v1","surface":"defaults",'
            '"selector":{"section":"startup"},"matched":true,'
            '"answer":{"default_canonical_agent_instructions_file":"AGENTS.md"},"refs":[]}\')'
        ),
    ]
    contract["expectations"]["stdout"].pop("schema")
    fixture_root = tmp_path / "drift-fixture"
    materialize_fixture(fixture=contract["fixtures"][0], fixture_root=fixture_root)

    with pytest.raises(AssertionError, match="forbidden fixture path"):
        run_process_conformance(contract=contract, fixture_root=fixture_root, repo_root=fixture_root)


def test_conformance_registry_points_at_schema_valid_contracts() -> None:
    registry = conformance_contracts_manifest()

    assert registry["schema_version"] == "agentic-workspace/conformance-contracts/v1"
    assert registry["contracts"][0]["operation_id"] == "defaults.report"
    assert conformance_contract_manifest(registry["contracts"][0]["path"])["adapter"]["kind"] == "process"


def test_generated_adapters_are_backed_by_black_box_conformance_contracts() -> None:
    registry = conformance_contracts_manifest()
    contracts_by_id = {contract["id"]: contract for contract in registry["contracts"]}

    generated_adapters_by_command = {
        **GENERATED_COMMAND_ADAPTERS_BY_COMMAND,
        **GENERATED_PLANNING_COMMAND_ADAPTERS_BY_COMMAND,
    }
    for command_name, adapter in generated_adapters_by_command.items():
        for conformance_ref in adapter["conformance_refs"]:
            registry_ref = contracts_by_id[conformance_ref]
            contract = conformance_contract_manifest(registry_ref["path"])
            command_template = contract["adapter"]["command_template"]

            assert registry_ref["operation_id"] == adapter["operation_id"]
            assert contract["operation_id"] == adapter["operation_id"]
            expected_placeholder = (
                "{agentic_workspace_cli}" if adapter["command"]["program"] == "agentic-workspace" else "{agentic_planning_cli}"
            )
            assert command_template[0] == expected_placeholder
            assert command_template[1] == command_name
