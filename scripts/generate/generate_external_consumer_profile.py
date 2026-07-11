from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IR_PATH = REPO_ROOT / "src/agentic_workspace/contracts/command_package_ir.json"
OUTPUTS = (
    REPO_ROOT / "src/agentic_workspace/contracts/external_consumer_profile.json",
    REPO_ROOT / "generated/workspace/python/external_consumer_profile.json",
    REPO_ROOT / "generated/workspace/typescript/external_consumer_profile.json",
)
SCHEMA_RESOURCE_OUTPUTS = {
    REPO_ROOT / "generated/workspace/python/_contracts/config_report_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/config_report_input.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/workspace_config.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/workspace_config.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/config_report_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/config_report_input.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/workspace_config.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/workspace_config.schema.json",
}


def _commands(command: dict[str, object], inherited: dict[str, object] | None = None):
    current = dict(inherited or {})
    if "operation_ref" not in command:
        current.pop("operation_ref", None)
    current.update(command)
    yield current
    interface = command.get("interface", {})
    if isinstance(interface, dict):
        for child in interface.get("subcommands", []):
            if isinstance(child, dict):
                yield from _commands(child, current)


def _operation_resource_path(target_id: str, target: dict[str, object], operation_path: str) -> Path:
    resource_root = "resources/operations" if target_id == "typescript" else "operations"
    return Path(str(target.get("generated_root", ""))) / resource_root / Path(operation_path).name


def build_profile(ir: dict[str, object], *, repo_root: Path | None = None) -> dict[str, object]:
    conformance_by_id: dict[str, dict[str, object]] = {}
    if repo_root is not None:
        registry = json.loads((repo_root / "src/agentic_workspace/contracts/conformance_contracts.json").read_text(encoding="utf-8"))
        conformance_by_id = {str(item["id"]): item for item in registry["contracts"]}
    operations: list[dict[str, object]] = []
    for package in ir.get("packages", []):
        if not isinstance(package, dict):
            continue
        targets = {
            str(target.get("kind")): {
                "package": target.get("package_name"),
                "status": target.get("generation_status"),
                "maturity": target.get("maturity_level_ref"),
                "generated_root": target.get("generated_root"),
            }
            for target in package.get("targets", [])
            if isinstance(target, dict)
        }
        usable_targets = {
            target_id
            for target_id, target in targets.items()
            if target.get("status") not in {"deferred", "unsupported", "metadata-proof-fixture", "parser-help-proof"}
        }
        for root in package.get("commands", []):
            if not isinstance(root, dict):
                continue
            for command in _commands(root):
                ref = command.get("operation_ref", {})
                if not isinstance(ref, dict) or not ref.get("id") or not ref.get("path"):
                    continue
                effects = command.get("effect_hints", {})
                schemas = command.get("schemas", {"input": [], "output": []})
                schema_refs = [
                    str(value)
                    for values in schemas.values()
                    for value in values
                    if isinstance(schemas, dict) and isinstance(values, list) and isinstance(value, str)
                ]
                conformance = [value for value in command.get("conformance_refs", []) if isinstance(value, str)]
                contract_path = f"{package.get('operation_contract_root')}/{ref['path']}"
                contract_exists = repo_root is None or (repo_root / contract_path).is_file()
                contract_payload = (
                    json.loads((repo_root / contract_path).read_text(encoding="utf-8")) if repo_root is not None and contract_exists else {}
                )
                contract_fingerprint = hashlib.sha256(
                    json.dumps(contract_payload, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                resolved_conformance = [
                    value
                    for value in conformance
                    if repo_root is None
                    or (
                        value in conformance_by_id
                        and not str(conformance_by_id[value].get("id", "")).endswith(".help.process")
                        and (repo_root / "src/agentic_workspace/contracts" / str(conformance_by_id[value]["path"])).is_file()
                    )
                ]
                boundary = command.get("projection_boundary", {})
                runtime_owned = boundary.get("runtime_owned", []) if isinstance(boundary, dict) else []
                resources_exist = repo_root is None or all(
                    (repo_root / _operation_resource_path(target_id, targets[target_id], str(ref["path"]))).is_file()
                    for target_id in usable_targets & {"python", "typescript"}
                )
                schemas_exist = repo_root is None or all(
                    all(
                        (
                            repo_root
                            / str(targets[target_id].get("generated_root", ""))
                            / ("resources/_contracts" if target_id == "typescript" else "_contracts")
                            / schema_ref
                        ).is_file()
                        for target_id in usable_targets & {"python", "typescript"}
                    )
                    for schema_ref in schema_refs
                )
                required = (
                    bool(effects)
                    and bool(conformance)
                    and len(resolved_conformance) == len(conformance)
                    and contract_exists
                    and resources_exist
                    and schemas_exist
                    and isinstance(schemas, dict)
                    and bool(schemas.get("input"))
                    and bool(schemas.get("output"))
                )
                if command.get("status") != "generated" or not required or not usable_targets:
                    maturity = "internal"
                elif not {"python", "typescript"}.issubset(usable_targets):
                    maturity = "target-specific"
                elif runtime_owned:
                    maturity = "runtime-backed"
                else:
                    maturity = "supported"
                entry = {
                    "id": ref["id"],
                    "owner": package.get("id"),
                    "operation_contract": contract_path,
                    "operation_compatibility": {
                        "schema_version": contract_payload.get("schema_version"),
                        "fingerprint": f"sha256:{contract_fingerprint}",
                    },
                    "operation_resources": {
                        target_id: {
                            "package": target["package"],
                            "path": _operation_resource_path(target_id, target, str(ref["path"])).relative_to(
                                Path(str(target.get("generated_root", "")))
                            ).as_posix(),
                            "exists": repo_root is None
                            or (repo_root / _operation_resource_path(target_id, target, str(ref["path"]))).is_file(),
                        }
                        for target_id, target in targets.items()
                        if target_id in {"python", "typescript"}
                    },
                    "schemas": schemas,
                    "effects": effects,
                    "targets": targets,
                    "conformance": resolved_conformance,
                    "external_consumption": {
                        "status": maturity,
                        "runtime_exceptions": [
                                {
                                    "owner": package.get("id"),
                                    "scope": scope,
                                    "reason": "Operation behavior still crosses an explicitly declared runtime-owned projection boundary.",
                                    "proof": resolved_conformance,
                                    "migration_dependency": "#2044",
                                }
                                for scope in runtime_owned
                        ],
                        "dependency": "#2044" if runtime_owned else None,
                    },
                }
                operations.append(entry)
    unique: dict[str, dict[str, object]] = {}
    for entry in operations:
        operation_id = str(entry["id"])
        previous = unique.get(operation_id)
        if previous is not None and previous["operation_contract"] != entry["operation_contract"]:
            raise ValueError(f"conflicting explicit operation id: {operation_id}")
        unique.setdefault(operation_id, entry)
    operations = sorted(unique.values(), key=lambda item: str(item["id"]))
    fingerprint_input = json.dumps(operations, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema_version": "agentic-workspace/external-consumer-profile/v1",
        "authority": "command_package_ir.json",
        "compatibility": {
            "protocol": "1.0.0",
            "fingerprint": f"sha256:{hashlib.sha256(fingerprint_input).hexdigest()}",
            "additive_fields": "allowed",
        },
        "support_rule": "Operations fail closed unless generated status, effects, conformance, and Python/TypeScript target accounting are present.",
        "operations": operations,
    }


def render() -> str:
    return json.dumps(build_profile(json.loads(IR_PATH.read_text(encoding="utf-8")), repo_root=REPO_ROOT), indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    rendered = {**{path: expected for path in OUTPUTS}, **{output: source.read_text(encoding="utf-8") for output, source in SCHEMA_RESOURCE_OUTPUTS.items()}}
    stale = [path for path, content in rendered.items() if not path.is_file() or path.read_text(encoding="utf-8") != content]
    if args.check:
        for path in stale:
            print(f"{path.relative_to(REPO_ROOT).as_posix()} is stale")
        return int(bool(stale))
    for path, content in rendered.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
