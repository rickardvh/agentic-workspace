from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IR_PATH = REPO_ROOT / "src/agentic_workspace/contracts/command_package_ir.json"
OUTPUTS = (
    REPO_ROOT / "src/agentic_workspace/contracts/external_consumer_profile.json",
    REPO_ROOT / "generated/workspace/python/external_consumer_profile.json",
    REPO_ROOT / "generated/workspace/typescript/external_consumer_profile.json",
)
PYTHON_CLIENT = REPO_ROOT / "generated/workspace/python/client.py"
TYPESCRIPT_CLIENT = REPO_ROOT / "generated/workspace/typescript/src/client.mjs"
BUNDLE_OUTPUTS = (
    REPO_ROOT / "generated/workspace/python/external_contract_bundle.json",
    REPO_ROOT / "generated/workspace/typescript/external_contract_bundle.json",
)
PYTHON_TYPED_OPERATIONS = REPO_ROOT / "src/agentic_workspace/generated_operations.py"
SCHEMA_RESOURCE_OUTPUTS = {
    REPO_ROOT / "generated/workspace/python/_contracts/delegation_outcome_append_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/delegation_outcome_append_input.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/delegation_outcome_append_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/delegation_outcome_append_result.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/config_report_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/config_report_input.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/workspace_config.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/workspace_config.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/config_report_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/config_report_result.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/config_report_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/config_report_input.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/workspace_config.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/workspace_config.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/config_report_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/config_report_result.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/delegation_outcome_append_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/delegation_outcome_append_input.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/delegation_outcome_append_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/delegation_outcome_append_result.schema.json",
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


def resolve_schema_reference(name: str, *, repo_root: Path = REPO_ROOT) -> Path:
    reference = name.split("#", 1)[0]
    candidates = [
        path
        for root in (repo_root / "src", repo_root / "packages")
        if root.exists()
        for path in root.rglob(Path(reference).name)
        if "generated" not in path.parts
    ]
    if not candidates:
        raise ValueError(f"missing transitive schema: {name}")
    suffix_matches = [path for path in candidates if path.as_posix().endswith(reference)]
    selected = suffix_matches or candidates
    if len(selected) != 1:
        raise ValueError(f"ambiguous transitive schema reference: {name}: {[path.as_posix() for path in selected]}")
    return selected[0]


def render_bundle(profile: dict[str, object]) -> str:
    def schema_refs(value: object) -> set[str]:
        refs: set[str] = set()
        if isinstance(value, dict):
            for item in value.values():
                refs.update(schema_refs(item))
        elif isinstance(value, list):
            for item in value:
                refs.update(schema_refs(item))
        elif isinstance(value, str) and ".schema.json" in value and not any(character.isspace() for character in value):
            reference = value.split("#", 1)[0]
            if reference.endswith(".schema.json"):
                refs.add(reference)
        return refs

    operations: dict[str, object] = {}
    schemas: dict[str, object] = {}
    pending_schemas: set[str] = set()
    for entry in profile["operations"]:
        if not isinstance(entry, dict) or entry.get("external_consumption", {}).get("status") == "internal":
            continue
        contract = json.loads((REPO_ROOT / str(entry["operation_contract"])).read_text(encoding="utf-8"))
        pending_schemas.update(schema_refs(contract))
        identity_input = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
        compatibility_contract = {
            key: contract.get(key)
            for key in ("schema_version", "id", "classification", "inputs", "output", "effects", "guards")
        }
        compatibility_input = json.dumps(compatibility_contract, sort_keys=True, separators=(",", ":")).encode()
        operations[str(entry["id"])] = {
            "identity": str(entry["id"]),
            "version": contract.get("schema_version"),
            "fingerprint": f"sha256:{hashlib.sha256(identity_input).hexdigest()}",
            "compatibility_fingerprint": f"sha256:{hashlib.sha256(compatibility_input).hexdigest()}",
            "contract": contract,
            "schemas": sorted(schema_refs(contract)),
            "targets": entry["targets"],
            "external_consumption": entry["external_consumption"],
        }
    while pending_schemas:
        name = pending_schemas.pop()
        if name in schemas:
            continue
        schema_path = resolve_schema_reference(name)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schemas[name] = {"source": schema_path.relative_to(REPO_ROOT).as_posix(), "schema": schema}
        pending_schemas.update(schema_refs(schema) - set(schemas))
    payload = {
        "schema_version": "agentic-workspace/external-contract-bundle/v1",
        "protocol": profile["compatibility"]["protocol"],
        "profile_fingerprint": profile["compatibility"]["fingerprint"],
        "profile": "external_consumer_profile.json",
        "versions": {
            "command_ir_schema": json.loads(IR_PATH.read_text(encoding="utf-8"))["schema_version"],
            "client_package": tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"],
            "runtime_protocol": profile["compatibility"]["protocol"],
            "python_package": "agentic-workspace",
            "typescript_package": "@agentic-workspace/workspace-cli",
        },
        "operations": operations,
        "schemas": dict(sorted(schemas.items())),
        "requirement_states": ["compatible", "incompatible", "missing", "runtime-backed", "unsupported"],
        "compatibility_rule": "Protocol major versions must match; fingerprint changes require requirement negotiation.",
    }
    return json.dumps(payload, indent=2) + "\n"


def render_python_client() -> str:
    return '''# Generated from command_package_ir.json. Do not edit.\nfrom __future__ import annotations\n\nimport json\nimport subprocess\nfrom importlib.resources import files\nfrom pathlib import Path\nfrom typing import Any, Sequence\n\n\ndef external_consumer_profile() -> dict[str, Any]:\n    resource = files("agentic_workspace._generated_cli_package_impl").joinpath("external_consumer_profile.json")\n    return json.loads(resource.read_text(encoding="utf-8"))\n\n\ndef require_operations(operation_ids: Sequence[str], *, allow_runtime_backed: bool = False) -> None:\n    entries = {entry["id"]: entry for entry in external_consumer_profile()["operations"]}\n    failures = []\n    for operation_id in operation_ids:\n        entry = entries.get(operation_id)\n        status = entry and entry["external_consumption"]["status"]\n        if entry is None or status == "internal" or (status == "runtime-backed" and not allow_runtime_backed):\n            failures.append(f"{operation_id}: {status or 'unknown'}")\n    if failures:\n        raise ValueError("incompatible operation requirements: " + ", ".join(failures))\n\n\ndef invoke_json(argv: Sequence[str], *, target: str | Path | None = None, executable: Sequence[str] = ("agentic-workspace",)) -> dict[str, Any]:\n    command = [*executable, *argv]\n    if target is not None and "--target" not in command:\n        command.extend(["--target", str(target)])\n    if "--format" not in command:\n        command.extend(["--format", "json"])\n    completed = subprocess.run(command, text=True, capture_output=True, check=False)\n    stream = completed.stdout or completed.stderr\n    try:\n        payload = json.loads(stream)\n    except json.JSONDecodeError as exc:\n        raise RuntimeError(f"AW returned non-JSON output (exit {completed.returncode})") from exc\n    if completed.returncode:\n        raise RuntimeError(json.dumps({"exit_code": completed.returncode, "error": payload}))\n    return payload\n'''


def render_typescript_client() -> str:
    template = REPO_ROOT / "scripts/generate/templates/external_client.mjs"
    if template.is_file():
        return template.read_text(encoding="utf-8")
    return '''// Generated from command_package_ir.json. Do not edit.\nimport { readFileSync } from 'node:fs';\nimport { spawnSync } from 'node:child_process';\n\nconst profileUrl = new URL('../external_consumer_profile.json', import.meta.url);\nexport function externalConsumerProfile() { return JSON.parse(readFileSync(profileUrl, 'utf8')); }\nexport function requireOperations(operationIds, { allowRuntimeBacked = false } = {}) {\n  const entries = new Map(externalConsumerProfile().operations.map((entry) => [entry.id, entry]));\n  const failures = operationIds.flatMap((id) => {\n    const status = entries.get(id)?.external_consumption?.status ?? 'unknown';\n    return status === 'internal' || status === 'unknown' || (status === 'runtime-backed' && !allowRuntimeBacked) ? [`${id}: ${status}`] : [];\n  });\n  if (failures.length) throw new Error(`incompatible operation requirements: ${failures.join(', ')}`);\n}\nexport function invokeJson(argv, { target, executable = 'agentic-workspace' } = {}) {\n  const args = [...argv];\n  if (target !== undefined && !args.includes('--target')) args.push('--target', String(target));\n  if (!args.includes('--format')) args.push('--format', 'json');\n  const result = spawnSync(executable, args, { encoding: 'utf8' });\n  const text = result.stdout || result.stderr;\n  let payload;\n  try { payload = JSON.parse(text); } catch (error) { throw new Error(`AW returned non-JSON output (exit ${result.status})`, { cause: error }); }\n  if (result.status !== 0) throw new Error(JSON.stringify({ exit_code: result.status, error: payload }));\n  return payload;\n}\n'''


def render_python_typed_operations(profile: dict[str, object]) -> str:
    lines = [
        "# Generated from the external consumer profile. Do not edit.",
        "from __future__ import annotations",
        "",
        "from pathlib import Path",
        "from typing import Any, Mapping, Sequence",
        "",
        "from .client import invoke_operation",
        "",
        "",
    ]
    for entry in profile["operations"]:
        if entry["external_consumption"]["status"] == "internal":
            continue
        function_name = str(entry["id"]).replace(".", "_").replace("-", "_")
        lines.extend(
            [
                f"def {function_name}(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:",
                f'    return invoke_operation("{entry["id"]}", values, target=target, invocation=invocation, allow_runtime_backed=True)',
                "",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    profile = build_profile(json.loads(IR_PATH.read_text(encoding="utf-8")), repo_root=REPO_ROOT)
    expected = json.dumps(profile, indent=2) + "\n"
    bundle = render_bundle(profile)
    rendered = {
        **{path: expected for path in OUTPUTS},
        **{path: bundle for path in BUNDLE_OUTPUTS},
        **{output: source.read_text(encoding="utf-8") for output, source in SCHEMA_RESOURCE_OUTPUTS.items()},
        PYTHON_CLIENT: render_python_client(),
        TYPESCRIPT_CLIENT: render_typescript_client(),
        PYTHON_TYPED_OPERATIONS: render_python_typed_operations(profile),
    }
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
