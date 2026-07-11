from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

from agentic_workspace.conformance import materialize_fixture, run_process_conformance
from agentic_workspace.contract_tooling import conformance_contract_manifest, conformance_contracts_manifest

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
MEMORY_CLI_SHIM = (
    "import sys; "
    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'memory' / 'src')!r}); "
    "from repo_memory_bootstrap.cli import main; "
    "raise SystemExit(main(sys.argv[1:]))"
)


def _generated_adapters_by_command(path: str) -> dict[str, dict[str, object]]:
    payload = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))
    return dict(payload["adapters_by_command"])


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
            "agentic_memory_cli": [sys.executable, "-c", MEMORY_CLI_SHIM],
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


def test_process_conformance_setup_steps_define_baseline(tmp_path: Path) -> None:
    contract = copy.deepcopy(conformance_contract_manifest("conformance/defaults.report.process.json"))
    contract["adapter"]["command_template"] = [
        "{python}",
        "-c",
        (
            "from pathlib import Path; "
            "assert Path('prepared.txt').read_text() == 'ready'; "
            'print(\'{"profile":"compact-contract-answer/v1","surface":"defaults",'
            '"selector":{"section":"startup"},"matched":true,'
            '"answer":{"default_canonical_agent_instructions_file":"AGENTS.md"},"refs":[]}\')'
        ),
    ]
    contract["expectations"]["stdout"].pop("schema")
    contract["fixtures"][0]["setup_steps"] = [
        {
            "id": "prepare-installed-state",
            "command_template": ["{python}", "-c", "from pathlib import Path; Path('prepared.txt').write_text('ready')"],
            "cwd": "fixture_root",
            "allowed_write_paths": ["prepared.txt"],
        }
    ]
    fixture_root = tmp_path / contract["fixtures"][0]["id"]
    materialize_fixture(fixture=contract["fixtures"][0], fixture_root=fixture_root)

    run_process_conformance(contract=contract, fixture_root=fixture_root, repo_root=fixture_root)


def test_process_conformance_setup_steps_reject_unlisted_writes(tmp_path: Path) -> None:
    contract = copy.deepcopy(conformance_contract_manifest("conformance/defaults.report.process.json"))
    contract["fixtures"][0]["setup_steps"] = [
        {
            "id": "bad-setup",
            "command_template": ["{python}", "-c", "from pathlib import Path; Path('unexpected.txt').write_text('bad')"],
            "cwd": "fixture_root",
            "allowed_write_paths": ["prepared.txt"],
        }
    ]
    fixture_root = tmp_path / contract["fixtures"][0]["id"]
    materialize_fixture(fixture=contract["fixtures"][0], fixture_root=fixture_root)

    with pytest.raises(AssertionError, match="forbidden fixture path"):
        run_process_conformance(contract=contract, fixture_root=fixture_root, repo_root=fixture_root)


def test_process_conformance_allows_writes_below_allowed_directory(tmp_path: Path) -> None:
    contract = copy.deepcopy(conformance_contract_manifest("conformance/defaults.report.process.json"))
    contract["adapter"]["command_template"] = [
        "{python}",
        "-c",
        (
            "from pathlib import Path; "
            "Path('output/nested').mkdir(parents=True, exist_ok=True); "
            "Path('output/nested/result.txt').write_text('ready'); "
            'print(\'{"profile":"compact-contract-answer/v1","surface":"defaults",'
            '"selector":{"section":"startup"},"matched":true,'
            '"answer":{"default_canonical_agent_instructions_file":"AGENTS.md"},"refs":[]}\')'
        ),
    ]
    contract["expectations"]["stdout"].pop("schema")
    contract["expectations"]["filesystem"]["allowed_write_directories"] = ["output"]
    fixture_root = tmp_path / "directory-write-fixture"
    materialize_fixture(fixture=contract["fixtures"][0], fixture_root=fixture_root)

    run_process_conformance(contract=contract, fixture_root=fixture_root, repo_root=fixture_root)


def test_process_conformance_rejects_descendant_of_exact_allowed_file(tmp_path: Path) -> None:
    contract = copy.deepcopy(conformance_contract_manifest("conformance/defaults.report.process.json"))
    contract["adapter"]["command_template"] = [
        "{python}",
        "-c",
        (
            "from pathlib import Path; Path('result/nested').mkdir(parents=True, exist_ok=True); "
            "Path('result/nested/file').write_text('unexpected')"
        ),
    ]
    contract["expectations"]["stdout"]["allow_empty"] = True
    contract["expectations"]["stdout"].pop("schema")
    contract["expectations"]["stdout"]["format"] = "text"
    contract["expectations"]["filesystem"]["allowed_write_paths"] = ["result"]
    fixture_root = tmp_path / "exact-file-write-fixture"
    materialize_fixture(fixture=contract["fixtures"][0], fixture_root=fixture_root)

    with pytest.raises(AssertionError, match="forbidden fixture path"):
        run_process_conformance(contract=contract, fixture_root=fixture_root, repo_root=fixture_root)


def test_process_conformance_setup_step_uses_recursive_directory_scope(tmp_path: Path) -> None:
    contract = copy.deepcopy(conformance_contract_manifest("conformance/defaults.report.process.json"))
    contract["fixtures"][0]["setup_steps"] = [
        {
            "id": "prepare-directory",
            "command_template": [
                "{python}",
                "-c",
                "from pathlib import Path; Path('prepared/nested').mkdir(parents=True); Path('prepared/nested/file').write_text('ok')",
            ],
            "cwd": "fixture_root",
            "allowed_write_paths": [],
            "allowed_write_directories": ["prepared"],
        }
    ]
    fixture_root = tmp_path / "setup-directory-write-fixture"
    materialize_fixture(fixture=contract["fixtures"][0], fixture_root=fixture_root)

    run_process_conformance(contract=contract, fixture_root=fixture_root, repo_root=fixture_root)


def test_conformance_registry_points_at_schema_valid_contracts() -> None:
    registry = conformance_contracts_manifest()

    assert registry["schema_version"] == "agentic-workspace/conformance-contracts/v1"
    defaults_ref = next(contract for contract in registry["contracts"] if contract["operation_id"] == "defaults.report")
    assert conformance_contract_manifest(defaults_ref["path"])["adapter"]["kind"] == "process"


def test_generated_adapters_are_backed_by_black_box_conformance_contracts() -> None:
    registry = conformance_contracts_manifest()
    contracts_by_id = {contract["id"]: contract for contract in registry["contracts"]}

    generated_adapters_by_command = {
        **_generated_adapters_by_command("generated/workspace/python/generated_command_adapters.json"),
        **_generated_adapters_by_command("generated/planning/python/generated_command_adapters.json"),
        **_generated_adapters_by_command("generated/memory/python/generated_command_adapters.json"),
    }
    for command_name, adapter in generated_adapters_by_command.items():
        for conformance_ref in adapter["conformance_refs"]:
            registry_ref = contracts_by_id[conformance_ref]
            contract = conformance_contract_manifest(registry_ref["path"])
            command_template = contract["adapter"]["command_template"]

            assert contract["operation_id"] == registry_ref["operation_id"]
            assert registry_ref["operation_id"] == adapter["operation_id"] or conformance_ref.startswith(f"{registry_ref['operation_id']}.")
            placeholders_by_program = {
                "agentic-workspace": "{agentic_workspace_cli}",
                "agentic-planning": "{agentic_planning_cli}",
                "agentic-memory": "{agentic_memory_cli}",
                "agentic-verification": "{agentic_verification_cli}",
            }
            expected_placeholder = placeholders_by_program[adapter["command"]["program"]]
            assert command_template[0] == expected_placeholder
            assert command_template[1] == command_name
