from __future__ import annotations

import json
from pathlib import Path

from command_generation import (
    BUILTIN_PORTABLE_PRIMITIVES,
    CommandGenerationHostManifest,
    GeneratedOutput,
    PrimitiveRegistry,
    command_package_schema_path,
    load_command_package_ir,
    render_outputs,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = "src/agentic_workspace/contracts/command_package_ir.json"
SCHEMA_PATH = "command_generation:schemas/command_package_ir.schema.json"
REGENERATE_COMMAND = "uv run python scripts/generate/generate_command_packages.py"
TYPESCRIPT_RUNTIME_SUPPORT_PATH = "src/agentic_workspace/contracts/typescript_runtime_support.mjs"
OPERATION_PRIMITIVES_PATH = "src/agentic_workspace/contracts/operation_primitives.json"
RELEASE_OWNERSHIP_PATH = ".github/release-ownership.json"


def _operation_refs(command: dict[str, object], inherited: dict[str, object] | None = None) -> list[dict[str, object]]:
    operation_ref = command.get("operation_ref", inherited or {})
    current = operation_ref if isinstance(operation_ref, dict) else inherited or {}
    refs = [current]
    interface = command.get("interface", {})
    if isinstance(interface, dict):
        for subcommand in interface.get("subcommands", []):
            if isinstance(subcommand, dict):
                refs.extend(_operation_refs(subcommand, current))
    return refs


def _operation_primitives_manifest(*, repo_root: Path) -> dict[str, object]:
    return json.loads((repo_root / OPERATION_PRIMITIVES_PATH).read_text(encoding="utf-8"))


def _primitive_target_support(
    primitive_id: str,
    primitive: dict[str, object],
    primitives_manifest: dict[str, object],
) -> tuple[dict[str, str], dict[str, str]]:
    if primitive_id == "typescript.domain.execute":
        return (
            {"python": "unsupported", "typescript": "host-implemented"},
            {"python": "TypeScript domain execution is only available in generated Node runtimes."},
        )
    extension = primitives_manifest.get("primitive_extension_boundary", {})
    matrix = extension.get("target_support_matrix", []) if isinstance(extension, dict) else []
    support: dict[str, str] = {}
    unsupported: dict[str, str] = {}
    portability = str(primitive.get("portability", "domain-runtime"))
    for item in matrix if isinstance(matrix, list) else []:
        if not isinstance(item, dict):
            continue
        target = str(item.get("target", "")).strip()
        if target not in {"python", "typescript"}:
            continue
        status = str(item.get("status", "unsupported"))
        implemented = {str(value) for value in item.get("implemented_shared_primitives", []) if isinstance(value, str)}
        if portability == "target-executor":
            if primitive_id in implemented:
                support[target] = "implemented"
            else:
                support[target] = "unsupported"
                unsupported[target] = str(item.get("unsupported_behavior", "Primitive is not implemented by this target."))
        elif status == "implemented":
            support[target] = "host-implemented"
        else:
            support[target] = "unsupported"
            unsupported[target] = str(item.get("unsupported_behavior", "Primitive is not implemented by this target."))
    return support or {"python": "host-implemented", "typescript": "host-implemented"}, unsupported


def _merge_effects(current: dict[str, object], incoming: dict[str, object]) -> dict[str, object]:
    if not current:
        return dict(incoming)
    merged = dict(current)
    for field in ("destructive", "writes_repo_state", "requires_preflight_gate"):
        merged[field] = bool(merged.get(field)) or bool(incoming.get(field))
    for field in ("read_only", "idempotent"):
        merged[field] = bool(merged.get(field, True)) and bool(incoming.get(field, True))
    return merged


def _operation_ir_steps(operation: dict[str, object]) -> list[tuple[dict[str, object], str]]:
    ir_plan = operation.get("ir_plan", {})
    if not isinstance(ir_plan, dict):
        return []
    collected: list[tuple[dict[str, object], str]] = []
    top_steps = ir_plan.get("steps", [])
    if isinstance(top_steps, list):
        for index, step in enumerate(top_steps):
            if isinstance(step, dict):
                collected.append((step, f"steps/{index}"))
    fragments = ir_plan.get("fragments", [])
    if isinstance(fragments, list):
        for fragment_index, fragment in enumerate(fragments):
            if not isinstance(fragment, dict):
                continue
            fragment_steps = fragment.get("steps", [])
            if not isinstance(fragment_steps, list):
                continue
            for step_index, step in enumerate(fragment_steps):
                if isinstance(step, dict):
                    collected.append((step, f"fragments/{fragment_index}/steps/{step_index}"))
    return collected


def _host_primitive_definitions(manifest: dict[str, object], *, repo_root: Path) -> list[dict[str, object]]:
    builtin_ids = BUILTIN_PORTABLE_PRIMITIVES.ids()
    primitives_manifest = _operation_primitives_manifest(repo_root=repo_root)
    primitive_entries = {
        str(primitive.get("id")): (index, primitive)
        for index, primitive in enumerate(primitives_manifest.get("primitives", []))
        if isinstance(primitive, dict) and primitive.get("id")
    }
    primitive_ids: set[str] = {
        "workspace.config.load",
        "workspace.config.emit",
        "workspace.defaults.load",
        "workspace.defaults.select",
        "output.fields.select",
        "typescript.domain.execute",
    }
    primitive_usage: dict[str, dict[str, object]] = {}
    for package in manifest.get("packages", []):
        if not isinstance(package, dict):
            continue
        operation_contract_root = repo_root / str(package.get("operation_contract_root", ""))
        for command in package.get("commands", []):
            if not isinstance(command, dict):
                continue
            effect_hints = command.get("effect_hints", {})
            effects = dict(effect_hints) if isinstance(effect_hints, dict) else {}
            conformance_refs = [
                str(ref)
                for ref in command.get("conformance_refs", [])
                if isinstance(ref, str) and ref.strip()
            ]
            for operation_ref in _operation_refs(command):
                operation_path = str(operation_ref.get("path", ""))
                source = operation_contract_root / operation_path
                if not source.is_file():
                    continue
                operation = json.loads(source.read_text(encoding="utf-8"))
                for step, step_pointer in _operation_ir_steps(operation):
                    primitive = str(step.get("uses", "")).strip()
                    if primitive and primitive not in builtin_ids:
                        primitive_ids.add(primitive)
                        usage = primitive_usage.setdefault(
                            primitive,
                            {
                                "effects": {},
                                "conformance_refs": [],
                                "operation_refs": [],
                                "input_schema_ref": "",
                                "output_schema_ref": "",
                            },
                        )
                        usage["effects"] = _merge_effects(dict(usage.get("effects", {})), effects)
                        refs = usage.get("conformance_refs", [])
                        if isinstance(refs, list):
                            for ref in conformance_refs:
                                if ref not in refs:
                                    refs.append(ref)
                        operation_refs = usage.get("operation_refs", [])
                        if isinstance(operation_refs, list):
                            operation_ref_path = f"{package.get('operation_contract_root')}/{operation_path}"
                            if operation_ref_path not in operation_refs:
                                operation_refs.append(operation_ref_path)
                        if not usage.get("input_schema_ref"):
                            usage["input_schema_ref"] = (
                                f"{package.get('operation_contract_root')}/{operation_path}#/ir_plan/{step_pointer}/arguments"
                            )
                        if not usage.get("output_schema_ref"):
                            usage["output_schema_ref"] = (
                                f"{package.get('operation_contract_root')}/{operation_path}#/ir_plan/{step_pointer}/outputs"
                            )
    definitions: list[dict[str, object]] = []
    for primitive_id in sorted(primitive_ids):
        primitive_index, primitive = primitive_entries.get(primitive_id, (-1, {}))
        usage = primitive_usage.get(primitive_id, {})
        support, unsupported = _primitive_target_support(primitive_id, primitive, primitives_manifest)
        conformance_refs = list(usage.get("conformance_refs", [])) if isinstance(usage.get("conformance_refs"), list) else []
        primitive_conformance = str(primitive.get("conformance_ref", "")).strip()
        if primitive_conformance and primitive_conformance not in conformance_refs:
            conformance_refs.append(primitive_conformance)
        primitive_schema_ref = (
            f"{OPERATION_PRIMITIVES_PATH}#/primitives/{primitive_index}" if primitive_index >= 0 else OPERATION_PRIMITIVES_PATH
        )
        input_schema_ref = str(usage.get("input_schema_ref") or f"{primitive_schema_ref}/input_schema")
        output_schema_ref = str(usage.get("output_schema_ref") or f"{primitive_schema_ref}/output_schema")
        definitions.append(
            {
                "id": primitive_id,
                "kind": str(primitive.get("portability") or primitive.get("kind") or "host"),
                "description": str(primitive.get("summary") or f"{primitive_id} host primitive"),
                "input_schema": {"$ref": input_schema_ref},
                "input_schema_ref": input_schema_ref,
                "output_schema": {"$ref": output_schema_ref},
                "output_schema_ref": output_schema_ref,
                "effects": usage.get("effects", {}),
                "target_support": support,
                "unsupported_targets": unsupported,
                "unsupported_behavior": str(
                    primitive.get("unsupported_behavior")
                    or primitives_manifest.get("primitive_extension_boundary", {}).get(
                        "target_support_rule",
                        "Unsupported primitive ids fail instead of falling back silently.",
                    )
                ),
                "owner": str(primitive.get("tier_owner") or "agentic-workspace"),
                "conformance_refs": conformance_refs,
            }
        )
    return definitions


def workspace_command_generation_host_manifest(*, repo_root: Path = REPO_ROOT) -> CommandGenerationHostManifest:
    manifest = load_workspace_command_package_ir(repo_root=repo_root)
    return CommandGenerationHostManifest(
        generated_root=repo_root / "generated",
        package_ids=tuple(str(package["id"]) for package in manifest.get("packages", []) if isinstance(package, dict)),
        contract_roots={
            str(package["id"]): repo_root / str(package["operation_contract_root"])
            for package in manifest.get("packages", [])
            if isinstance(package, dict) and package.get("id") and package.get("operation_contract_root")
        },
        primitive_registry=PrimitiveRegistry.from_definitions(_host_primitive_definitions(manifest, repo_root=repo_root)),
        typescript_runtime_support_path=repo_root / TYPESCRIPT_RUNTIME_SUPPORT_PATH,
        operation_schema_version="agentic-workspace/operation/v1",
    )


def load_workspace_command_package_ir(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    return load_command_package_ir(repo_root / SOURCE_PATH, command_package_schema_path())


def _typescript_release_package_metadata(*, repo_root: Path) -> dict[str, dict[str, object]]:
    ownership_path = repo_root / RELEASE_OWNERSHIP_PATH
    if not ownership_path.is_file():
        return {}
    ownership = json.loads(ownership_path.read_text(encoding="utf-8"))
    packages = ownership.get("typescript_packages", [])
    return {
        str(package["package_json"]): package
        for package in packages
        if isinstance(package, dict) and isinstance(package.get("package_json"), str)
    }


def _normalize_releaseable_typescript_package_json(
    output: GeneratedOutput,
    *,
    release_metadata: dict[str, dict[str, object]],
    repo_root: Path,
) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    relative = path.relative_to(repo_root).as_posix()
    metadata = release_metadata.get(relative)
    if metadata is None:
        return output
    payload = json.loads(output.content)
    existing_version = None
    if path.is_file():
        existing_payload = json.loads(path.read_text(encoding="utf-8"))
        existing_version = existing_payload.get("version")
    if isinstance(existing_version, str) and existing_version:
        # The coordinated release workflow owns package versions; generation owns
        # the publishable package shape around that checked-in release value.
        payload["version"] = existing_version
    payload["private"] = False
    payload["engines"] = {"node": str(metadata.get("runtime_requirement", "node>=20")).removeprefix("node")}
    payload["publishConfig"] = {"access": "public"}
    return GeneratedOutput(output.path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def render_workspace_command_package_outputs(
    manifest: dict[str, object] | None = None,
    *,
    repo_root: Path = REPO_ROOT,
) -> list[GeneratedOutput]:
    effective_manifest = manifest if manifest is not None else load_workspace_command_package_ir(repo_root=repo_root)
    outputs = render_outputs(
        effective_manifest,
        repo_root=repo_root,
        source_path=SOURCE_PATH,
        regenerate_command=REGENERATE_COMMAND,
        host_manifest=workspace_command_generation_host_manifest(repo_root=repo_root),
    )
    release_metadata = _typescript_release_package_metadata(repo_root=repo_root)
    return [
        _normalize_releaseable_typescript_package_json(output, release_metadata=release_metadata, repo_root=repo_root)
        for output in outputs
    ]



def generate_workspace_command_packages(*, repo_root: Path = REPO_ROOT, check: bool) -> list[str]:
    stale: list[str] = []
    for output in render_workspace_command_package_outputs(repo_root=repo_root):
        path = output.path if output.path.is_absolute() else repo_root / output.path
        relative = path.relative_to(repo_root).as_posix()
        if path.exists() and path.read_text(encoding="utf-8") == output.content:
            continue
        stale.append(relative)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output.content, encoding="utf-8", newline="\n")
            print(f"[ok] wrote {relative}")
    return stale
