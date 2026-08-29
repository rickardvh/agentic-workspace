from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(GENERATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(GENERATOR_ROOT))

from scripts.check.run_operation_conformance_tests import build_external_operation_conformance_receipts  # noqa: E402
from workspace_command_generation import (  # noqa: E402
    load_workspace_command_package_ir,
    render_workspace_command_package_outputs,
)

IR_PATH = REPO_ROOT / "src/agentic_workspace/contracts/command_package_ir.json"
OPERATION_CONFORMANCE_IR_PATH = REPO_ROOT / "src/agentic_workspace/contracts/operation_conformance_test_ir.json"
OUTPUTS = (
    REPO_ROOT / "src/agentic_workspace/contracts/external_consumer_profile.json",
    REPO_ROOT / "generated/workspace/python/external_consumer_profile.json",
    REPO_ROOT / "generated/workspace/typescript/external_consumer_profile.json",
)
CONFORMANCE_RECEIPT_OUTPUTS = (
    REPO_ROOT / "src/agentic_workspace/contracts/external_operation_conformance_receipts.json",
    REPO_ROOT / "generated/workspace/python/external_operation_conformance_receipts.json",
    REPO_ROOT / "generated/workspace/typescript/external_operation_conformance_receipts.json",
)
USABLE_MATURITY_LEVELS = {"runnable-read-only-adapter", "weak-agent-safe-adapter", "mutation-capable-adapter"}
READINESS_TRANSPORTS = ("cli-json", "python", "typescript", "vendor-neutral")
READINESS_EXECUTORS = {
    "cli-json": "direct-cli-json",
    "python": "generated-python-client",
    "typescript": "generated-typescript-client",
    "vendor-neutral": "packed-typescript-client",
}
READINESS_CASES = (
    "absent",
    "disabled",
    "incompatible",
    "malformed",
    "retryable",
    "additive-field",
    "mutation-applied",
    "mutation-noop",
    "mutation-rejected",
    "mutation-failed",
)
PYTHON_CLIENT = REPO_ROOT / "generated/workspace/python/client.py"
TYPESCRIPT_CLIENT = REPO_ROOT / "generated/workspace/typescript/src/client.mjs"
BUNDLE_OUTPUTS = (
    REPO_ROOT / "generated/workspace/python/external_contract_bundle.json",
    REPO_ROOT / "generated/workspace/typescript/external_contract_bundle.json",
)
PYTHON_TYPED_OPERATIONS = REPO_ROOT / "src/agentic_workspace/generated_operations.py"
ASSIGNMENT_OPERATION_IDS = (
    "assignment.admit",
    "assignment.cleanup",
    "assignment.close",
    "assignment.dispatch",
    "assignment.export",
    "assignment.import",
    "assignment.integrate",
    "assignment.override",
    "assignment.reassign",
    "assignment.reject",
    "assignment.repair",
)

CORRECTION_OPERATION_IDS = (
    "correction-event.correct-dispute",
    "correction-event.prune-compact",
    "correction-event.query",
    "correction-event.submit",
    "correction-event.withdraw-supersede",
)
EVALUATION_OPERATION_IDS = (
    "evaluation.report-preview",
    "evaluation.local-delivery",
    "evaluation.external-request",
    "evaluation.external-host-result-import",
    "evaluation.external-adapter-receipt",
    "evaluation.external-delivery",
    "evaluation.delivery-status",
    "evaluation.retry",
)
ASSURANCE_OPERATION_IDS = (
    "external-evidence.submit",
    "external-evidence.query",
)
GUIDANCE_OPERATION_IDS = (
    "agent-guidance.delete",
    "agent-guidance.edit",
    "agent-guidance.merge",
    "agent-guidance.promote",
    "agent-guidance.retire",
    "agent-guidance.revalidate",
    "agent-guidance.split",
    "agent-guidance.supersede",
    "agent-guidance.suppress",
    "agent-guidance.weaken",
)
PYTHON_OPERATION_RESOURCE_ROOT = REPO_ROOT / "generated/workspace/python/operations"
SCHEMA_RESOURCE_OUTPUTS = {
    REPO_ROOT / "generated/workspace/python/_contracts/scoped_instruction_operation_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/scoped_instruction_operation_input.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/scoped_instruction_operation_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/scoped_instruction_operation_result.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/scoped_instruction_operation_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/scoped_instruction_operation_input.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/scoped_instruction_operation_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/scoped_instruction_operation_result.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/external_evidence_operation_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/external_evidence_operation_input.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/external_evidence_operation_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/external_evidence_operation_result.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/external_evidence_host_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/external_evidence_host_result.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/external_evidence_operation_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/external_evidence_operation_input.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/external_evidence_operation_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/external_evidence_operation_result.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/external_evidence_host_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/external_evidence_host_result.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/evaluation_authority_refresh_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/evaluation_authority_refresh_input.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/evaluation_authority_refresh_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/evaluation_authority_refresh_result.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/evaluation_authority_refresh_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/evaluation_authority_refresh_input.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/evaluation_authority_refresh_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/evaluation_authority_refresh_result.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/operation_failure.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/operation_failure.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/operation_failure.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/operation_failure.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/delegation_outcome_append_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/delegation_outcome_append_input.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/delegation_outcome_append_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/delegation_outcome_append_result.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/assignment_lifecycle_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/assignment_lifecycle_input.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/assignment_lifecycle_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/assignment_lifecycle_result.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/correction_event_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/correction_event_input.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/correction_event_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/correction_event_result.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/guidance_lifecycle_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/guidance_lifecycle_input.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/guidance_lifecycle_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/guidance_lifecycle_result.schema.json",
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
    REPO_ROOT / "generated/workspace/python/_contracts/evaluation_observation_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/evaluation_observation_input.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/evaluation_observe_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/evaluation_observe_result.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/evaluation_observation_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/evaluation_observation_input.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/evaluation_observe_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/evaluation_observe_result.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/evaluation_report_delivery_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/evaluation_report_delivery_input.schema.json",
    REPO_ROOT / "generated/workspace/python/_contracts/evaluation_report_delivery_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/evaluation_report_delivery_result.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/evaluation_report_delivery_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/evaluation_report_delivery_input.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/evaluation_report_delivery_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/evaluation_report_delivery_result.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/delegation_outcome_append_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/delegation_outcome_append_input.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/delegation_outcome_append_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/delegation_outcome_append_result.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/assignment_lifecycle_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/assignment_lifecycle_input.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/assignment_lifecycle_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/assignment_lifecycle_result.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/correction_event_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/correction_event_input.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/correction_event_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/correction_event_result.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/guidance_lifecycle_input.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/guidance_lifecycle_input.schema.json",
    REPO_ROOT / "generated/workspace/typescript/resources/_contracts/guidance_lifecycle_result.schema.json": REPO_ROOT
    / "src/agentic_workspace/contracts/schemas/guidance_lifecycle_result.schema.json",
}

USABLE_MATURITY_LEVELS = {
    "runnable-read-only-adapter",
    "weak-agent-safe-adapter",
    "mutation-capable-adapter",
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


def expected_canonical_operation_resources() -> dict[Path, str]:
    """Read shared operation resources from the command-package rendering authority."""

    manifest = load_workspace_command_package_ir(repo_root=REPO_ROOT)
    resources: dict[Path, str] = {}
    for output in render_workspace_command_package_outputs(manifest, repo_root=REPO_ROOT):
        path = output.path if output.path.is_absolute() else REPO_ROOT / output.path
        if path.parent == PYTHON_OPERATION_RESOURCE_ROOT:
            resources[path] = output.content
    return resources


def _artifact_revision(repo_root: Path, relative_path: str) -> str:
    path = repo_root / relative_path
    if not path.is_file():
        return ""
    return f"{relative_path}@sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _readiness_authority(repo_root: Path | None) -> dict[str, object]:
    if repo_root is None:
        return {
            "kind": "agentic-workspace/external-readiness-authority/v1",
            "status": "unbound",
            "runner_revision": "",
            "client_semantics_revision": "",
            "client_artifact_revisions": {},
        }
    paths = {
        "runner": "scripts/check/run_operation_conformance_tests.py",
        "public_python_client": "src/agentic_workspace/client.py",
        "generated_client_generator": "scripts/generate/generate_external_consumer_profile.py",
        "typescript_client_template": "scripts/generate/templates/external_client.mjs",
    }
    revisions = {name: _artifact_revision(repo_root, path) for name, path in paths.items()}
    client_revisions = {name: revision for name, revision in revisions.items() if name != "runner"}
    client_semantics_revision = (
        "sha256:" + hashlib.sha256(json.dumps(client_revisions, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    )
    return {
        "kind": "agentic-workspace/external-readiness-authority/v1",
        "status": "current" if all(revisions.values()) else "incomplete",
        "runner_revision": revisions["runner"],
        "client_semantics_revision": client_semantics_revision,
        "client_artifact_revisions": client_revisions,
    }


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
            and target.get("maturity") in USABLE_MATURITY_LEVELS
        }
        for root in package.get("commands", []):
            if not isinstance(root, dict):
                continue
            for command in _commands(root):
                ref = command.get("operation_ref", {})
                if not isinstance(ref, dict) or not ref.get("id") or not ref.get("path"):
                    continue
                effects = command.get("effect_hints", {})
                conformance = [value for value in command.get("conformance_refs", []) if isinstance(value, str)]
                contract_path = f"{package.get('operation_contract_root')}/{ref['path']}"
                contract_exists = repo_root is None or (repo_root / contract_path).is_file()
                contract_payload = (
                    json.loads((repo_root / contract_path).read_text(encoding="utf-8")) if repo_root is not None and contract_exists else {}
                )
                contract_effects = contract_payload.get("effects", {})
                if isinstance(contract_effects, dict) and contract_effects:
                    effects = contract_effects
                operation_conformance = [
                    conformance_id
                    for conformance_id in conformance
                    if conformance_id in conformance_by_id and conformance_by_id[conformance_id].get("operation_id") == ref["id"]
                ]
                if operation_conformance:
                    conformance = operation_conformance
                declared_schemas = command.get("schemas", {"input": [], "output": []})
                schemas = {
                    "input": list(declared_schemas.get("input", [])) if isinstance(declared_schemas, dict) else [],
                    "output": list(declared_schemas.get("output", [])) if isinstance(declared_schemas, dict) else [],
                }
                contract_input_refs = [
                    Path(str(item.get("schema_ref"))).name
                    for item in contract_payload.get("inputs", [])
                    if isinstance(item, dict) and item.get("schema_ref")
                ]
                contract_output_ref = (
                    str(contract_payload.get("output", {}).get("schema_ref", ""))
                    if isinstance(contract_payload.get("output"), dict)
                    else ""
                )
                if contract_input_refs:
                    schemas["input"] = sorted(set(contract_input_refs))
                if contract_output_ref:
                    schemas["output"] = [Path(contract_output_ref).name]
                schema_refs = [
                    str(value) for values in schemas.values() for value in values if isinstance(values, list) and isinstance(value, str)
                ]
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
                            "path": _operation_resource_path(target_id, target, str(ref["path"]))
                            .relative_to(Path(str(target.get("generated_root", ""))))
                            .as_posix(),
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
    readiness_authority = _readiness_authority(repo_root)
    fingerprint_input = json.dumps(
        {"operations": operations, "readiness_authority": readiness_authority}, sort_keys=True, separators=(",", ":")
    ).encode()
    return {
        "schema_version": "agentic-workspace/external-consumer-profile/v1",
        "authority": "command_package_ir.json",
        "compatibility": {
            "protocol": "1.0.0",
            "fingerprint": f"sha256:{hashlib.sha256(fingerprint_input).hexdigest()}",
            "additive_fields": "allowed",
        },
        "support_rule": "Operations fail closed unless generated status, effects, conformance, and Python/TypeScript target accounting are present.",
        "readiness_authority": readiness_authority,
        "readiness_executors": dict(READINESS_EXECUTORS),
        "operations": operations,
    }


def render() -> str:
    return json.dumps(build_profile(json.loads(IR_PATH.read_text(encoding="utf-8")), repo_root=REPO_ROOT), indent=2) + "\n"


def resolve_schema_reference(name: str, *, repo_root: Path = REPO_ROOT, base_path: Path | None = None) -> Path:
    reference = name.split("#", 1)[0]
    fragment = name.partition("#")[2]
    if base_path is not None and reference and (base_path.parent / reference).is_file():
        selected_path = (base_path.parent / reference).resolve()
    else:
        selected_path = None
    basename = Path(reference).name
    candidate_names = {basename, basename.replace("-", "_")}
    candidates = [
        path
        for root in (repo_root / "src", repo_root / "packages")
        if root.exists()
        for candidate_name in candidate_names
        for path in root.rglob(candidate_name)
        if "generated" not in path.parts
    ]
    if selected_path is None and not candidates:
        raise ValueError(f"missing transitive schema: {name}")
    suffix_matches = [path for path in candidates if path.as_posix().endswith(reference)]
    selected = suffix_matches or candidates
    if selected_path is None and len(selected) != 1:
        raise ValueError(f"ambiguous transitive schema reference: {name}: {[path.as_posix() for path in selected]}")
    selected_path = selected_path or selected[0]
    if fragment:
        node: object = json.loads(selected_path.read_text(encoding="utf-8"))
        for token in fragment.removeprefix("/").split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or token not in node:
                raise ValueError(f"missing schema fragment: {name}")
            node = node[token]
    return selected_path


def schema_references(value: object) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str) and (reference.startswith("#") or reference.split("#", 1)[0].endswith(".schema.json")):
            refs.add(reference)
        for key, item in value.items():
            if key != "$ref":
                refs.update(schema_references(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(schema_references(item))
    return refs


def collect_schema_graph(initial: set[str], *, repo_root: Path = REPO_ROOT) -> tuple[set[str], dict[str, object]]:
    closure: set[str] = set()
    graph: dict[str, object] = {}
    pending: list[tuple[str, Path | None, str | None]] = [(ref, None, None) for ref in sorted(initial)]
    while pending:
        reference, base_path, preferred_key = pending.pop()
        schema_path = (
            base_path
            if reference.startswith("#") and base_path is not None
            else resolve_schema_reference(reference, repo_root=repo_root, base_path=base_path)
        )
        if reference.startswith("#"):
            resolve_schema_reference(schema_path.name + reference, repo_root=repo_root, base_path=schema_path)
        key = preferred_key or reference.split("#", 1)[0]
        if key in closure:
            continue
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        graph[key] = {"source": schema_path.relative_to(repo_root).as_posix(), "schema": schema}
        closure.add(key)
        for nested in schema_references(schema):
            nested_path = (
                schema_path if nested.startswith("#") else resolve_schema_reference(nested, repo_root=repo_root, base_path=schema_path)
            )
            pending.append((nested, schema_path, nested_path.relative_to(repo_root).as_posix()))
    return closure, graph


def render_bundle(profile: dict[str, object]) -> str:
    def schema_refs(value: object) -> set[str]:
        return schema_references(value)

    def compatibility_schema(value: object) -> object:
        if isinstance(value, list):
            return [compatibility_schema(item) for item in value]
        if not isinstance(value, dict):
            return value
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if key in {"description", "title", "$id", "$comment", "examples", "default"}:
                continue
            normalized[key] = compatibility_schema(item)
        return normalized

    def schema_closure(initial: set[str]) -> set[str]:
        closure, graph = collect_schema_graph(initial)
        schemas.update(graph)
        return closure

    operations: dict[str, object] = {}
    schemas: dict[str, object] = {}
    for entry in profile["operations"]:
        if not isinstance(entry, dict) or entry.get("external_consumption", {}).get("status") == "internal":
            continue
        contract = json.loads((REPO_ROOT / str(entry["operation_contract"])).read_text(encoding="utf-8"))
        input_refs = {str(item) for item in entry.get("schemas", {}).get("input", [])}
        output_refs = {str(item) for item in entry.get("schemas", {}).get("output", [])}
        failure_refs = {"operation_failure.schema.json"}
        input_closure = schema_closure(input_refs | schema_refs(contract))
        output_closure = schema_closure(output_refs)
        failure_closure = schema_closure(failure_refs)
        closure = input_closure | output_closure | failure_closure
        operations[str(entry["id"])] = {
            "identity": str(entry["id"]),
            "version": contract.get("schema_version"),
            "fingerprint": "pending",
            "compatibility_fingerprint": "pending",
            "contract": contract,
            "schemas": sorted(closure),
            "targets": entry["targets"],
            "external_consumption": entry["external_consumption"],
            "schema_roles": {
                "input": sorted(input_closure),
                "output": sorted(output_closure),
                "failure": sorted(failure_closure),
            },
        }
    for operation in operations.values():
        closure = {name: schemas[name]["schema"] for name in operation["schemas"]}
        exact = {"contract": operation["contract"], "schemas": closure}
        compatible = {
            "contract": {
                key: operation["contract"].get(key)
                for key in ("schema_version", "id", "classification", "inputs", "output", "effects", "guards")
            },
            "schemas": {
                role: compatibility_schema({name: closure[name] for name in names}) for role, names in operation["schema_roles"].items()
            },
        }
        operation["compatibility_surface"] = compatible
        operation["fingerprint"] = "sha256:" + hashlib.sha256(json.dumps(exact, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        operation["compatibility_fingerprint"] = (
            "sha256:" + hashlib.sha256(json.dumps(compatible, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        )
    conformance_ir = json.loads(OPERATION_CONFORMANCE_IR_PATH.read_text(encoding="utf-8"))
    payload = {
        "schema_version": "agentic-workspace/external-contract-bundle/v1",
        "protocol": profile["compatibility"]["protocol"],
        "profile_fingerprint": profile["compatibility"]["fingerprint"],
        "profile": "external_consumer_profile.json",
        "versions": {
            "command_ir_schema": json.loads(IR_PATH.read_text(encoding="utf-8"))["schema_version"],
            "client_package": tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"],
            "runtime_protocol": profile["compatibility"]["protocol"],
            "python_package": {
                "name": "agentic-workspace",
                "version": tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"],
            },
            "typescript_package": {
                "name": "@agentic-workspace/workspace-cli",
                "version": json.loads((REPO_ROOT / "generated/workspace/typescript/package.json").read_text(encoding="utf-8"))["version"],
            },
        },
        "operations": operations,
        "schemas": dict(sorted(schemas.items())),
        "external_conformance": {
            "kind": "agentic-workspace/packaged-external-conformance-profile/v1",
            "source": "operation_conformance_test_ir.json#external_readiness",
            "readiness_cases": list(READINESS_CASES),
            "transport_matrix": list(READINESS_TRANSPORTS),
            "executor_matrix": dict(READINESS_EXECUTORS),
            "operations": conformance_ir.get("external_readiness", {}).get("operations", []),
            "rule": conformance_ir.get("external_readiness", {}).get("rule", ""),
        },
        "requirement_states": ["compatible", "incompatible", "missing", "runtime-backed", "unsupported"],
        "compatibility_rule": "Protocol major versions must match; fingerprint changes require requirement negotiation.",
    }
    return json.dumps(payload, indent=2) + "\n"


def render_conformance_receipts(profile: dict[str, object]) -> str:
    return json.dumps(build_external_operation_conformance_receipts(profile), indent=2) + "\n"


def _legacy_render_python_client() -> str:
    return """# Generated from command_package_ir.json. Do not edit.\nfrom __future__ import annotations\n\nimport json\nimport subprocess\nfrom importlib.resources import files\nfrom pathlib import Path\nfrom typing import Any, Sequence\n\n\ndef external_consumer_profile() -> dict[str, Any]:\n    resource = files("agentic_workspace._generated_cli_package_impl").joinpath("external_consumer_profile.json")\n    return json.loads(resource.read_text(encoding="utf-8"))\n\n\ndef require_operations(operation_ids: Sequence[str], *, allow_runtime_backed: bool = False) -> None:\n    entries = {entry["id"]: entry for entry in external_consumer_profile()["operations"]}\n    failures = []\n    for operation_id in operation_ids:\n        entry = entries.get(operation_id)\n        status = entry and entry["external_consumption"]["status"]\n        if entry is None or status == "internal" or (status == "runtime-backed" and not allow_runtime_backed):\n            failures.append(f"{operation_id}: {status or 'unknown'}")\n    if failures:\n        raise ValueError("incompatible operation requirements: " + ", ".join(failures))\n\n\ndef invoke_json(argv: Sequence[str], *, target: str | Path | None = None, executable: Sequence[str] = ("agentic-workspace",)) -> dict[str, Any]:\n    command = [*executable, *argv]\n    if target is not None and "--target" not in command:\n        command.extend(["--target", str(target)])\n    if "--format" not in command:\n        command.extend(["--format", "json"])\n    completed = subprocess.run(command, text=True, capture_output=True, check=False)\n    stream = completed.stdout or completed.stderr\n    try:\n        payload = json.loads(stream)\n    except json.JSONDecodeError as exc:\n        raise RuntimeError(f"AW returned non-JSON output (exit {completed.returncode})") from exc\n    if completed.returncode:\n        raise RuntimeError(json.dumps({"exit_code": completed.returncode, "error": payload}))\n    return payload\n"""


def render_python_client() -> str:
    return """# Generated from command_package_ir.json. Do not edit.
from __future__ import annotations

import json
import shlex
import subprocess
import tomllib
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any, Sequence

READINESS_TRANSPORTS = ("cli-json", "python", "typescript", "vendor-neutral")
READINESS_EXECUTORS = {"cli-json": "direct-cli-json", "python": "generated-python-client", "typescript": "generated-typescript-client", "vendor-neutral": "packed-typescript-client"}
READINESS_CASES = ("absent", "disabled", "incompatible", "malformed", "retryable", "additive-field", "mutation-applied", "mutation-noop", "mutation-rejected", "mutation-failed")


def external_consumer_profile() -> dict[str, Any]:
    return json.loads(files("agentic_workspace._generated_cli_package_impl").joinpath("external_consumer_profile.json").read_text(encoding="utf-8"))


def external_operation_conformance_receipts() -> dict[str, Any]:
    resource = files("agentic_workspace._generated_cli_package_impl").joinpath("external_operation_conformance_receipts.json")
    if not resource.is_file():
        return {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": []}
    payload = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("kind") != "agentic-workspace/external-operation-conformance-receipt-store/v1":
        return {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": []}
    return payload if _valid_receipt_publication(payload) else {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": [], "status": "invalid-publication"}


def _receipt_publication_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "mirror_publication"}


def _valid_receipt_publication(payload: dict[str, Any]) -> bool:
    publication = payload.get("mirror_publication", {})
    if not isinstance(publication, dict) or publication.get("status") != "published":
        return False
    digest = __import__("hashlib").sha256(json.dumps(_receipt_publication_payload(payload), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return publication.get("payload_digest") == f"sha256:{digest}"


def _receipt_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _conformance_receipt(entry: dict[str, Any], profile: dict[str, Any], receipt_store: dict[str, Any]) -> dict[str, Any] | None:
    operation_fingerprint = entry.get("operation_compatibility", {}).get("fingerprint", "")
    profile_fingerprint = profile.get("compatibility", {}).get("fingerprint", "")
    candidates = []
    for receipt in receipt_store.get("receipts", []):
        if not isinstance(receipt, dict): continue
        custody = receipt.get("custody", {}) if isinstance(receipt.get("custody"), dict) else {}
        if receipt.get("kind") != "agentic-workspace/external-operation-conformance-receipt/v1": continue
        if custody.get("producer") != "agentic-workspace.operation-conformance-runner": continue
        if receipt.get("operation_id") != entry.get("id"): continue
        if receipt.get("operation_fingerprint") != operation_fingerprint: continue
        if receipt.get("profile_fingerprint") != profile_fingerprint: continue
        if receipt.get("status") in {"revoked", "superseded", "stale"}: continue
        if receipt.get("revoked_at") or receipt.get("superseded_by"): continue
        expires_at = _receipt_time(receipt.get("expires_at"))
        if expires_at is not None and datetime.now(UTC) >= expires_at: continue
        candidates.append(receipt)
    return sorted(candidates, key=lambda item: str(item.get("executed_at") or item.get("receipt_ref") or ""))[-1] if candidates else None


def _conformance_readiness(entry: dict[str, Any], profile: dict[str, Any], receipt_store: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    evidence = _conformance_receipt(entry, profile, receipt_store)
    if not isinstance(evidence, dict): return ["executed-conformance-receipt"], {}
    missing = []
    operation_fingerprint = entry.get("operation_compatibility", {}).get("fingerprint", "")
    profile_fingerprint = profile.get("compatibility", {}).get("fingerprint", "")
    if evidence.get("status") != "passed": missing.append("executed-conformance-passed")
    if evidence.get("operation_fingerprint") != operation_fingerprint: missing.append("current-operation-fingerprint")
    if evidence.get("profile_fingerprint") != profile_fingerprint: missing.append("current-profile-fingerprint")
    authority = profile.get("readiness_authority", {}) if isinstance(profile.get("readiness_authority"), dict) else {}
    result_identity = evidence.get("result_identity", {}) if isinstance(evidence.get("result_identity"), dict) else {}
    if result_identity.get("runner_revision") != authority.get("runner_revision"): missing.append("current-runner-revision")
    if result_identity.get("client_semantics_revision") != authority.get("client_semantics_revision"): missing.append("current-client-semantics-revision")
    transports = evidence.get("transports", {})
    executors = evidence.get("executors", {})
    cases = evidence.get("cases", {})
    for transport in READINESS_TRANSPORTS:
        if not isinstance(transports.get(transport), dict) or transports[transport].get("status") != "passed": missing.append(f"transport-{transport}")
        if not isinstance(executors.get(transport), dict) or executors[transport].get("status") != "passed" or executors[transport].get("executor_id") != READINESS_EXECUTORS[transport]: missing.append(f"executor-{transport}")
    for case in READINESS_CASES:
        if not isinstance(cases.get(case), dict) or cases[case].get("status") != "passed": missing.append(f"case-{case}")
    matrix = evidence.get("case_transport_matrix", {})
    footprints = evidence.get("footprints", {})
    for case in READINESS_CASES:
        cells = matrix.get(case, {}) if isinstance(matrix, dict) else {}
        for transport in READINESS_TRANSPORTS:
            if not isinstance(cells.get(transport), dict) or cells[transport].get("status") != "passed": missing.append(f"case-{case}-transport-{transport}")
    for footprint in ("necessary-surfaces", "full-mirror"):
        if not isinstance(footprints.get(footprint), dict) or footprints[footprint].get("status") != "passed": missing.append(f"footprint-{footprint}")
    if not isinstance(footprints.get("semantic-parity"), dict) or footprints["semantic-parity"].get("status") != "passed": missing.append("footprint-semantic-parity")
    if entry.get("external_consumption", {}).get("runtime_exceptions") and not evidence.get("runtime_exception_revision"): missing.append("runtime-exception-current-revision")
    custody = evidence.get("custody", {}) if isinstance(evidence.get("custody"), dict) else {}
    return missing, {"status": evidence.get("status", ""), "operation_fingerprint": evidence.get("operation_fingerprint", ""), "profile_fingerprint": evidence.get("profile_fingerprint", ""), "runner_revision": result_identity.get("runner_revision", ""), "client_semantics_revision": result_identity.get("client_semantics_revision", ""), "runtime_exception_revision": evidence.get("runtime_exception_revision", ""), "transports": transports if isinstance(transports, dict) else {}, "executors": executors if isinstance(executors, dict) else {}, "cases": cases if isinstance(cases, dict) else {}, "case_transport_matrix": matrix if isinstance(matrix, dict) else {}, "footprints": footprints if isinstance(footprints, dict) else {}, "receipt_ref": evidence.get("receipt_ref", ""), "producer": custody.get("producer", "")}


def external_readiness_report(operation_ids: Sequence[str], *, allow_runtime_backed: bool = False) -> dict[str, Any]:
    profile = external_consumer_profile()
    receipt_store = external_operation_conformance_receipts()
    entries = {entry["id"]: entry for entry in profile["operations"]}
    supported, supported_evidence, excluded = [], [], []
    for operation_id in operation_ids:
        entry = entries.get(operation_id, {})
        consumption = entry.get("external_consumption", {})
        resources, targets = entry.get("operation_resources", {}), entry.get("targets", {})
        schemas, conformance = entry.get("schemas", {}), entry.get("conformance", [])
        missing = []
        for language in ("python", "typescript"):
            if not resources.get(language, {}).get("exists"): missing.append(f"released-{language}-resource")
            if targets.get(language, {}).get("status") not in {"adapter", "mutation-capable-adapter"}: missing.append(f"released-{language}-adapter")
        if not schemas.get("input") or not schemas.get("output"): missing.append("input-output-schema-coverage")
        if not conformance: missing.append("conformance-reference")
        conformance_missing, conformance_result = _conformance_readiness(entry, profile, receipt_store)
        missing.extend(conformance_missing)
        status = consumption.get("status", "unavailable")
        if status == "runtime-backed" and not consumption.get("runtime_exceptions"): missing.append("runtime-exception-disposition")
        allowed_statuses = {"supported"} | ({"runtime-backed"} if allow_runtime_backed else set())
        if status in allowed_statuses and not missing:
            supported.append(operation_id)
            supported_evidence.append({"id": operation_id, "status": "ready", "support_status": status, "conformance_refs": conformance, "conformance_result": conformance_result, "receipt_ref": conformance_result.get("receipt_ref", "")})
        else: excluded.append({"id": operation_id, "status": status, "missing_evidence": missing, "conformance_refs": conformance, "conformance_result": conformance_result})
    not_advertised = [{"id": operation_id, "status": entry.get("external_consumption", {}).get("status", "unavailable"), "reason": "runtime-backed opt-in required" if entry.get("external_consumption", {}).get("status") == "runtime-backed" else "operation is not declared externally supported"} for operation_id, entry in sorted(entries.items()) if entry.get("external_consumption", {}).get("status", "unavailable") != "supported"]
    return {"kind": "agentic-workspace/external-readiness-report/v1", "status": "ready" if not excluded else "subset-only" if supported else "not-ready", "supported_operations": supported, "supported_operation_evidence": supported_evidence, "excluded_operations": excluded, "operation_accounting": {"profile_operation_count": len(entries), "requested_operation_count": len(operation_ids), "ready_requested_count": len(supported), "excluded_requested_count": len(excluded), "not_advertised_count": len(not_advertised), "not_advertised_sample": not_advertised[:32], "sample_limit": 32}}


def require_operations(operation_ids: Sequence[str], *, allow_runtime_backed: bool = False) -> None:
    report = external_readiness_report(operation_ids, allow_runtime_backed=allow_runtime_backed)
    failures = report["excluded_operations"]
    if failures: raise ValueError("operation requirements lack current external-readiness evidence: " + json.dumps(failures, sort_keys=True))


def resolve_invocation(target: str | Path, override: Sequence[str] | None = None) -> list[str]:
    if override:
        return [str(item) for item in override]
    root = Path(target).resolve()
    for name in ("config.local.toml", "config.toml"):
        path = root / ".agentic-workspace" / name
        if not path.is_file():
            continue
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        workspace = payload.get("workspace", {}) if isinstance(payload, dict) else {}
        command = workspace.get("cli_invoke") if isinstance(workspace, dict) else None
        if isinstance(command, str) and command.strip():
            return shlex.split(command, posix=False)
    return ["agentic-workspace"]


def invoke_json(
    argv: Sequence[str], *, target: str | Path | None = None, executable: Sequence[str] | None = None
) -> dict[str, Any]:
    command = [*(resolve_invocation(target or ".", executable)), *argv]
    if target is not None and "--target" not in command: command.extend(["--target", str(target)])
    if "--format" not in command: command.extend(["--format", "json"])
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    try: payload = json.loads(completed.stdout or completed.stderr)
    except json.JSONDecodeError as exc: raise RuntimeError(f"AW returned non-JSON output (exit {completed.returncode})") from exc
    if completed.returncode: raise RuntimeError(json.dumps({"exit_code": completed.returncode, "error": payload}))
    return payload
"""


def render_typescript_client() -> str:
    template = REPO_ROOT / "scripts/generate/templates/external_client.mjs"
    if template.is_file():
        return template.read_text(encoding="utf-8")
    return """// Generated from command_package_ir.json. Do not edit.\nimport { readFileSync } from 'node:fs';\nimport { spawnSync } from 'node:child_process';\n\nconst profileUrl = new URL('../external_consumer_profile.json', import.meta.url);\nexport function externalConsumerProfile() { return JSON.parse(readFileSync(profileUrl, 'utf8')); }\nexport function requireOperations(operationIds, { allowRuntimeBacked = false } = {}) {\n  const entries = new Map(externalConsumerProfile().operations.map((entry) => [entry.id, entry]));\n  const failures = operationIds.flatMap((id) => {\n    const status = entries.get(id)?.external_consumption?.status ?? 'unknown';\n    return status === 'internal' || status === 'unknown' || (status === 'runtime-backed' && !allowRuntimeBacked) ? [`${id}: ${status}`] : [];\n  });\n  if (failures.length) throw new Error(`incompatible operation requirements: ${failures.join(', ')}`);\n}\nexport function invokeJson(argv, { target, executable = 'agentic-workspace' } = {}) {\n  const args = [...argv];\n  if (target !== undefined && !args.includes('--target')) args.push('--target', String(target));\n  if (!args.includes('--format')) args.push('--format', 'json');\n  const result = spawnSync(executable, args, { encoding: 'utf8' });\n  const text = result.stdout || result.stderr;\n  let payload;\n  try { payload = JSON.parse(text); } catch (error) { throw new Error(`AW returned non-JSON output (exit ${result.status})`, { cause: error }); }\n  if (result.status !== 0) throw new Error(JSON.stringify({ exit_code: result.status, error: payload }));\n  return payload;\n}\n"""


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
        signature = (
            f"def {function_name}(values: Mapping[str, Any], *, target: str | Path, "
            "invocation: Sequence[str] | None = None) -> dict[str, Any]:"
        )
        signature_lines = (
            [signature]
            if len(signature) <= 140
            else [
                f"def {function_name}(",
                "    values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None",
                ") -> dict[str, Any]:",
            ]
        )
        lines.extend(
            [
                *signature_lines,
                "    return invoke_operation(",
                f'        "{entry["id"]}",',
                "        values,",
                "        target=target,",
                "        invocation=invocation,",
                "        allow_runtime_backed=True,",
                "    )",
                "",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    profile = build_profile(json.loads(IR_PATH.read_text(encoding="utf-8")), repo_root=REPO_ROOT)
    expected = json.dumps(profile, indent=2) + "\n"
    bundle = render_bundle(profile)
    operation_resources = expected_canonical_operation_resources()
    rendered = {
        **{path: expected for path in OUTPUTS},
        **{path: bundle for path in BUNDLE_OUTPUTS},
        **{output: source.read_text(encoding="utf-8") for output, source in SCHEMA_RESOURCE_OUTPUTS.items()},
        PYTHON_CLIENT: render_python_client(),
        TYPESCRIPT_CLIENT: render_typescript_client(),
        PYTHON_TYPED_OPERATIONS: render_python_typed_operations(profile),
    }
    stale = [
        path
        for path, content in {**rendered, **operation_resources}.items()
        if not path.is_file() or path.read_text(encoding="utf-8") != content
    ]
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
