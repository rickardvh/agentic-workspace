from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_json(relative: str, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    return json.loads((repo_root / relative).read_text(encoding="utf-8"))


def _operation_refs_from_interface(interface: dict[str, Any], inherited: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    current = interface.get("operation_ref", inherited or {})
    operation_ref = current if isinstance(current, dict) else inherited or {}
    refs = [operation_ref] if operation_ref else []
    for subcommand in interface.get("subcommands", []):
        if isinstance(subcommand, dict):
            refs.extend(_operation_refs_from_interface(subcommand, operation_ref))
    return refs


def _ids(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item.get("id", "")).strip() for item in items if isinstance(item, dict) and str(item.get("id", "")).strip()}


def _operation_inventory_entries(payload: dict[str, Any], operation_id: str) -> list[dict[str, Any]]:
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict) and entry.get("operation_id") == operation_id]


def _runtime_projection_entries(payload: dict[str, Any], operation_id: str) -> list[dict[str, Any]]:
    boundary = payload.get("accepted_runtime_boundaries", {})
    entries = boundary.get("entries", []) if isinstance(boundary, dict) else []
    matched: list[dict[str, Any]] = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        operation_ids = entry.get("operation_ids", [])
        if entry.get("operation_id") == operation_id or (isinstance(operation_ids, list) and operation_id in operation_ids):
            matched.append(entry)
    return matched


def command_surface_bundle_report(operation_id: str, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    operation_path = f"operations/{operation_id}.json"
    conformance_prefix = f"{operation_id}."
    operation_file = repo_root / "src/agentic_workspace/contracts" / operation_path
    conformance_dir = repo_root / "src/agentic_workspace/contracts/conformance"
    conformance_files = sorted(path.name for path in conformance_dir.glob(f"{operation_id}.*.json"))

    operation_contracts = _load_json("src/agentic_workspace/contracts/operation_contracts.json", repo_root=repo_root)
    operation_primitives = _load_json("src/agentic_workspace/contracts/operation_primitives.json", repo_root=repo_root)
    conformance_contracts = _load_json("src/agentic_workspace/contracts/conformance_contracts.json", repo_root=repo_root)
    adapter_generation = _load_json("src/agentic_workspace/contracts/command_adapter_generation.json", repo_root=repo_root)
    package_ir = _load_json("src/agentic_workspace/contracts/command_package_ir.json", repo_root=repo_root)
    operation_execution_inventory = _load_json(
        "src/agentic_workspace/contracts/python_operation_execution_inventory.json",
        repo_root=repo_root,
    )
    runtime_projection_inventory = _load_json(
        "src/agentic_workspace/contracts/python_runtime_projection_inventory.json",
        repo_root=repo_root,
    )
    operation_inventory_entries = _operation_inventory_entries(operation_execution_inventory, operation_id)
    runtime_projection_entries = _runtime_projection_entries(runtime_projection_inventory, operation_id)

    primitive_uses: set[str] = set()
    output_schema_refs: set[str] = set()
    if operation_file.is_file():
        operation = json.loads(operation_file.read_text(encoding="utf-8"))
        for step in operation.get("steps", []):
            if isinstance(step, dict) and step.get("uses"):
                primitive_uses.add(str(step["uses"]))
        output = operation.get("output", {})
        if isinstance(output, dict) and output.get("schema_ref"):
            output_schema_refs.add(str(output["schema_ref"]).removeprefix("schemas/"))

    primitive_ids = _ids(operation_primitives.get("primitives"))
    missing_primitives = sorted(primitive for primitive in primitive_uses if primitive not in primitive_ids and primitive != "output.emit")

    adapter_refs = []
    for adapter in adapter_generation.get("adapters", []):
        if not isinstance(adapter, dict):
            continue
        ref = adapter.get("operation_ref", {})
        if isinstance(ref, dict) and ref.get("id") == operation_id:
            adapter_refs.append(str(adapter.get("id", "")))

    package_refs = []
    package_output_schemas: set[str] = set()
    package_conformance_refs: set[str] = set()
    for package in package_ir.get("packages", []):
        if not isinstance(package, dict):
            continue
        for command in package.get("commands", []):
            if not isinstance(command, dict):
                continue
            refs = []
            command_ref = command.get("operation_ref", {})
            if isinstance(command_ref, dict):
                refs.append(command_ref)
            interface = command.get("interface", {})
            if isinstance(interface, dict):
                refs.extend(_operation_refs_from_interface(interface, command_ref if isinstance(command_ref, dict) else None))
            if any(ref.get("id") == operation_id for ref in refs if isinstance(ref, dict)):
                package_refs.append(str(command.get("adapter_id", "")))
                schemas = command.get("schemas", {})
                if isinstance(schemas, dict):
                    for schema in schemas.get("output", []):
                        package_output_schemas.add(str(schema))
                for ref in command.get("conformance_refs", []):
                    package_conformance_refs.add(str(ref))

    generated_python = _load_json("generated/workspace/python/command_package.json", repo_root=repo_root)
    generated_refs = []
    for command in generated_python.get("commands", []):
        if isinstance(command, dict) and any(
            isinstance(ref, dict) and ref.get("id") == operation_id
            for ref in _operation_refs_from_interface(command.get("interface", {}) if isinstance(command.get("interface"), dict) else {}, command.get("operation_ref", {}))
        ):
            generated_refs.append(str(command.get("adapter_id", "")))

    checks = {
        "operation_file": operation_file.is_file(),
        "operation_contract_registry": operation_id in _ids(operation_contracts.get("operations")),
        "operation_primitives": not missing_primitives,
        "conformance_file": bool(conformance_files),
        "conformance_registry": any(
            str(item.get("id", "")).startswith(conformance_prefix)
            for item in conformance_contracts.get("contracts", [])
            if isinstance(item, dict)
        ),
        "command_adapter_generation": bool(adapter_refs),
        "command_package_ir": bool(package_refs),
        "generated_python_command_package": bool(generated_refs),
        "python_operation_execution_inventory": bool(operation_inventory_entries),
        "python_runtime_projection_inventory": bool(runtime_projection_entries),
        "output_schema_refs": output_schema_refs <= package_output_schemas if output_schema_refs else True,
        "conformance_refs": any(ref.startswith(conformance_prefix) for ref in package_conformance_refs),
    }
    missing = [name for name, ok in checks.items() if not ok]
    return {
        "kind": "agentic-workspace/command-surface-bundle-check/v1",
        "operation_id": operation_id,
        "status": "ok" if not missing else "missing-companion-surfaces",
        "missing": missing,
        "checks": checks,
        "details": {
            "operation_path": operation_path,
            "conformance_files": conformance_files,
            "missing_primitives": missing_primitives,
            "adapter_refs": adapter_refs,
            "package_refs": package_refs,
            "generated_refs": generated_refs,
            "python_operation_execution_inventory": [
                {
                    "operation_contract": entry.get("operation_contract", ""),
                    "status": entry.get("status", ""),
                    "runtime_boundary_class": entry.get("runtime_boundary_class", ""),
                    "conformance_ref": entry.get("conformance_ref", ""),
                }
                for entry in operation_inventory_entries
            ],
            "python_runtime_projection_inventory": [
                {
                    "binding_kind": entry.get("binding_kind", ""),
                    "facade_path": entry.get("facade_path", ""),
                    "facade_symbol": entry.get("facade_symbol", ""),
                    "operation_path": entry.get("operation_path", ""),
                    "source_module": entry.get("source_module", ""),
                    "source_symbol": entry.get("source_symbol", ""),
                    "status": entry.get("status", ""),
                    "conformance_ref": entry.get("conformance_ref", ""),
                }
                for entry in runtime_projection_entries
            ],
            "output_schema_refs": sorted(output_schema_refs),
            "package_output_schemas": sorted(package_output_schemas),
            "package_conformance_refs": sorted(package_conformance_refs),
        },
        "remediation": "Declare the missing companion surfaces, run uv run python scripts/generate/refresh_command_surfaces.py, then rerun this check and check_generated_command_packages.py.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the complete registry bundle for a generated command operation.")
    parser.add_argument("--operation-id", required=True, help="Operation id such as checkpoint.write.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    report = command_surface_bundle_report(args.operation_id)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["status"] == "ok":
        print(f"[ok] command surface bundle {args.operation_id}")
    else:
        print(f"[fail] command surface bundle {args.operation_id}: missing {', '.join(report['missing'])}")
        print(report["remediation"])
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
