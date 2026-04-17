from __future__ import annotations

import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workspace import cli
from agentic_workspace.contract_tooling import (
    compact_contract_manifest,
    contract_inventory_manifest,
    contract_schema,
    proof_routes_manifest,
    report_contract_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _validator(schema_name: str) -> Draft202012Validator:
    schema = contract_schema(schema_name)
    return Draft202012Validator(schema)


def _validate(instance: object, schema_name: str) -> list[str]:
    validator = _validator(schema_name)
    return [error.message for error in validator.iter_errors(instance)]


def _sample_compact_answer() -> dict[str, object]:
    return cli._compact_contract_answer(  # type: ignore[attr-defined]
        surface="defaults",
        selector={"section": "proof_selection"},
        answer={"id": "workspace_proof"},
        refs=["docs/compact-contract-profile.md", "agentic-workspace defaults --format json"],
    )


def _sample_report_payload() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "repo"
        target.mkdir()
        (target / ".git").mkdir(exist_ok=True)
        descriptors = cli._module_operations()  # type: ignore[attr-defined]
        config = cli._load_workspace_config(target_root=target, descriptors=descriptors)  # type: ignore[attr-defined]
        selected_modules, resolved_preset = cli._selected_modules(  # type: ignore[attr-defined]
            command_name="report",
            preset_name=None,
            module_arg=None,
            target_root=target,
            descriptors=descriptors,
            config=config,
        )
        return cli._run_report_command(  # type: ignore[attr-defined]
            target_root=target,
            selected_modules=selected_modules,
            resolved_preset=resolved_preset,
            descriptors=descriptors,
            config=config,
        )


def main() -> int:
    checks: list[tuple[str, list[str]]] = [
        ("compact_contract_profile.json", _validate(compact_contract_manifest(), "selector_contracts_manifest.schema.json")),
        ("proof_routes.json", _validate(proof_routes_manifest(), "proof_routes_manifest.schema.json")),
        ("report_contract.json", _validate(report_contract_manifest(), "report_contract_manifest.schema.json")),
        ("contract_inventory.json", _validate(contract_inventory_manifest(), "contract_inventory.schema.json")),
        ("compact answer sample", _validate(_sample_compact_answer(), "compact_contract_answer.schema.json")),
        ("workspace report sample", _validate(_sample_report_payload(), "workspace_report.schema.json")),
    ]

    defaults_payload = cli._defaults_payload()  # type: ignore[attr-defined]
    if defaults_payload["compact_contract_profile"]["answer_shape"] != compact_contract_manifest()["answer_shape"]:
        checks.append(("defaults compact profile parity", ["defaults payload answer_shape drifted from compact_contract_profile.json"]))
    if defaults_payload["proof_surfaces"]["default_routes"] != proof_routes_manifest()["default_routes"]:
        checks.append(("proof routes parity", ["defaults payload proof routes drifted from proof_routes.json"]))
    if cli._reporting_schema_payload() != report_contract_manifest():  # type: ignore[attr-defined]
        checks.append(("report contract parity", ["reporting schema payload drifted from report_contract.json"]))

    failures = [(name, errors) for name, errors in checks if errors]
    if failures:
        print("Contract tooling health report")
        for name, errors in failures:
            for error in errors:
                print(f"- [{name}] {error}")
        return 1
    print("Contract tooling health report")
    print("- No contract-tooling drift warnings detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
