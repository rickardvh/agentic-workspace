from __future__ import annotations

import ast
import copy
import json
import re
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
PYTHON_PRIMITIVE_SUPPORT_PATH = "src/agentic_workspace/contracts/python_primitive_support.py"
TYPESCRIPT_PRIMITIVE_SUPPORT_PATH = "src/agentic_workspace/contracts/typescript_primitive_support.mjs"
OPERATION_PRIMITIVES_PATH = "src/agentic_workspace/contracts/operation_primitives.json"
RELEASE_OWNERSHIP_PATH = ".github/release-ownership.json"
SELECTOR_AUTHORITY_PATH = "src/agentic_workspace/workspace_selector_validation.py"


def _canonical_selector_descriptors(*, repo_root: Path) -> dict[str, list[str]]:
    tree = ast.parse((repo_root / SELECTOR_AUTHORITY_PATH).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "_SELECTOR_DESCRIPTORS_BY_COMMAND":
            value = ast.literal_eval(node.value)
            return {str(command): [str(selector) for selector in selectors] for command, selectors in value.items()}
    raise RuntimeError(f"selector authority missing from {SELECTOR_AUTHORITY_PATH}")


def _patch_typescript_selector_descriptors(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    if path.relative_to(repo_root).as_posix() != "generated/workspace/typescript/src/hostPrimitiveSupport.mjs":
        return output
    descriptors = _canonical_selector_descriptors(repo_root=repo_root)
    supported = {command: descriptors[command] for command in ("config", "defaults", "summary", "proof")}
    replacement = (
        "const WORKSPACE_SELECTOR_DESCRIPTORS = "
        + json.dumps(supported, indent=2, ensure_ascii=False)
        + ";\n\nconst WORKSPACE_DEPRECATED_SELECTOR_REPLACEMENTS"
    )
    content, count = re.subn(
        r"const WORKSPACE_SELECTOR_DESCRIPTORS = \{.*?\};\r?\n\r?\nconst WORKSPACE_DEPRECATED_SELECTOR_REPLACEMENTS",
        replacement,
        output.content,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("generated TypeScript selector descriptor block was not found")
    return GeneratedOutput(path=output.path, content=content)


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
            conformance_refs = [str(ref) for ref in command.get("conformance_refs", []) if isinstance(ref, str) and ref.strip()]
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
        python_primitive_support_path=repo_root / PYTHON_PRIMITIVE_SUPPORT_PATH,
        typescript_primitive_support_path=repo_root / TYPESCRIPT_PRIMITIVE_SUPPORT_PATH,
        operation_schema_version="agentic-workspace/operation/v1",
    )


def load_workspace_command_package_ir(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    manifest = load_command_package_ir(repo_root / SOURCE_PATH, command_package_schema_path())
    return _resolve_interface_projections(manifest)


def _resolve_interface_projections(manifest: dict[str, object]) -> dict[str, object]:
    """Expand module front doors from their canonical package command interfaces.

    A front door opts in by suffixing the module manifest reference with
    ``#projected:<command>[,<command>]``. Named nested commands then inherit
    the complete canonical interface, so option additions and removals cannot
    drift while unrelated front-door commands retain their target-specific UI.
    """

    resolved = copy.deepcopy(manifest)
    commands_by_ref: dict[tuple[str, str], list[dict[str, object]]] = {}
    for package in resolved.get("packages", []):
        if not isinstance(package, dict):
            continue
        for command in package.get("commands", []):
            if not isinstance(command, dict):
                continue
            command_ref = command.get("command")
            if not isinstance(command_ref, dict):
                continue
            manifest_ref = str(command_ref.get("manifest_ref") or "")
            name = str(command_ref.get("name") or "")
            if manifest_ref.startswith("package:") and name:
                commands_by_ref.setdefault((manifest_ref, name), []).append(command)

    for package in resolved.get("packages", []):
        if not isinstance(package, dict):
            continue
        for command in package.get("commands", []):
            if not isinstance(command, dict) or not isinstance(command.get("interface"), dict):
                continue
            command_ref = command.get("command")
            if not isinstance(command_ref, dict):
                continue
            projection_ref = str(command_ref.get("manifest_ref") or "")
            interface = command["interface"]
            subcommands = interface.get("subcommands")
            marker = "#projected:"
            if marker not in projection_ref or not isinstance(subcommands, list):
                continue
            manifest_ref, projected_names_text = projection_ref.rsplit(marker, 1)
            projected_names = {item.strip() for item in projected_names_text.split(",") if item.strip()}
            projected: list[object] = []
            for subcommand in subcommands:
                name = str(subcommand.get("name") or "") if isinstance(subcommand, dict) else ""
                if name not in projected_names:
                    projected.append(subcommand)
                    continue
                authorities = [candidate for candidate in commands_by_ref.get((manifest_ref, name), []) if candidate is not command]
                if len(authorities) > 1:
                    raise ValueError(f"ambiguous command interface projection: {manifest_ref}:{name}")
                authority = authorities[0] if authorities else None
                if authority and isinstance(authority.get("interface"), dict):
                    projected_interface = copy.deepcopy(authority["interface"])
                    if isinstance(subcommand, dict) and isinstance(subcommand.get("usage_error_hints"), list):
                        projected_interface["usage_error_hints"] = copy.deepcopy(subcommand["usage_error_hints"])
                    projected.append(projected_interface)
                else:
                    projected.append(subcommand)
            interface["subcommands"] = projected
    return resolved


def _typescript_release_package_metadata(*, repo_root: Path) -> dict[str, dict[str, object]]:
    ownership_path = repo_root / RELEASE_OWNERSHIP_PATH
    if not ownership_path.is_file():
        return {}
    ownership = json.loads(ownership_path.read_text(encoding="utf-8"))
    packages = ownership.get("typescript_packages", [])
    project_identity = ownership.get("project_identity", {})
    return {
        str(package["package_json"]): {**package, "project_identity": project_identity}
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
    identity = metadata.get("project_identity", {})
    if not isinstance(identity, dict):
        identity = {}
    release_asset_only = metadata.get("release_policy") == "release-asset-only"
    payload["private"] = release_asset_only
    payload["engines"] = {"node": str(metadata.get("runtime_requirement", "node>=20")).removeprefix("node")}
    if release_asset_only:
        payload.pop("publishConfig", None)
    else:
        payload["publishConfig"] = {"access": "public"}
    payload["license"] = str(identity.get("license_spdx", ""))
    payload["author"] = str(identity.get("author", ""))
    payload["homepage"] = str(identity.get("homepage", ""))
    payload["repository"] = {"type": "git", "url": str(identity.get("repository", ""))}
    payload["bugs"] = {"url": str(identity.get("issues", ""))}
    payload["description"] = "Generated Agentic Workspace command adapter distributed as an exact GitHub release asset."
    files = [str(item) for item in payload.get("files", []) if str(item) != "LICENSE"]
    files.append("LICENSE")
    payload["files"] = files
    return GeneratedOutput(output.path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _typescript_license_outputs(*, release_metadata: dict[str, dict[str, object]], repo_root: Path) -> list[GeneratedOutput]:
    license_text = (repo_root / "LICENSE").read_text(encoding="utf-8")
    return [GeneratedOutput(repo_root / Path(package_json).parent / "LICENSE", license_text) for package_json in sorted(release_metadata)]


def _typescript_sample_command_path(manifest: dict[str, object]) -> tuple[list[str], bool]:
    for package in manifest.get("packages", []):
        if not isinstance(package, dict) or package.get("id") != "root-workspace":
            continue
        commands = [command for command in package.get("commands", []) if isinstance(command, dict)]
        if not commands:
            break
        command = sorted(commands, key=lambda item: str(_as_dict(item.get("command")).get("name", "")))[0]
        command_name = str(_as_dict(command.get("command")).get("name", "")).strip()
        interface = _as_dict(command.get("interface"))
        subcommands = [item for item in interface.get("subcommands", []) if isinstance(item, dict)]
        subcommands_required = bool(subcommands and interface.get("subcommands_required") is not False)
        if command_name and subcommands_required:
            first_subcommand = sorted(subcommands, key=lambda item: str(item.get("name", "")))[0]
            subcommand_name = str(first_subcommand.get("name", "")).strip()
            if subcommand_name:
                return [command_name, subcommand_name], True
        if command_name:
            return [command_name], False
    return [], False


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _patch_workspace_typescript_sample_command_test(
    output: GeneratedOutput,
    *,
    repo_root: Path,
    manifest: dict[str, object],
) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    if path.relative_to(repo_root).as_posix() != "generated/workspace/typescript/test/command-package.test.mjs":
        return output
    sample_path, subcommands_required = _typescript_sample_command_path(manifest)
    if not sample_path:
        return output
    sample_command = sample_path[0]
    rendered_sample_path = json.dumps(sample_path)
    rendered_root_path = json.dumps([sample_command])
    content = output.content
    content = content.replace(
        "assert.deepEqual(packageJson.files, ['src', 'resources']);",
        "assert.deepEqual(packageJson.files, ['src', 'resources', 'external_consumer_profile.json', 'external_contract_bundle.json', 'external_operation_conformance_receipts.json', 'LICENSE']);",
    )
    content = content.replace(
        "assert.match(result.stderr, /Unsupported generated command: __unsupported__/);",
        "assert.match(result.stderr, /TypeScript CLI validation failed: unknown command __unsupported__/);",
    )
    content = content.replace(
        f'[{json.dumps(sample_command)}, "--format", "json"]',
        f'[...{rendered_sample_path}, "--format", "json"]',
    )
    content = content.replace(
        f'[{json.dumps(sample_command)}, "--target", "__SPACED_TARGET__"]',
        f'[...{rendered_sample_path}, "--target", "__SPACED_TARGET__"]',
    )
    if not subcommands_required:
        return GeneratedOutput(output.path, content)
    anchor = (
        "test('generated runnable adapter preserves spaced argv values during native execution', () => {\n"
        "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
        "  const spacedTarget = fileURLToPath(new URL('../tmp target with spaces', import.meta.url));\n"
        "  mkdirSync(spacedTarget, { recursive: true });\n"
        "  try {\n"
        f'    const args = [...{rendered_sample_path}, "--target", "__SPACED_TARGET__"].map((token) => token === \'__SPACED_TARGET__\' ? spacedTarget : token);\n'
        "    const result = spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8' });\n"
        "    assert.equal(result.status, 0);\n"
        "    assert.doesNotMatch(result.stderr, /runtime handoff/i);\n"
        "  } finally {\n"
        "    rmSync(spacedTarget, { recursive: true, force: true });\n"
        "  }\n"
        "});\n"
    )
    inserted = (
        anchor
        + "\n"
        + "test('generated runnable adapter rejects command without required subcommand', () => {\n"
        + "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
        + f'  const result = spawnSync(process.execPath, [cli, ...{rendered_root_path}, "--format", "json"], {{ encoding: \'utf8\' }});\n'
        + "  assert.equal(result.status, 2);\n"
        + "  assert.equal(result.stdout, '');\n"
        + f"  assert.match(result.stderr, /missing subcommand for {sample_command}/);\n"
        + "  assert.doesNotMatch(result.stderr, /runtime handoff/i);\n"
        + "});\n"
    )
    if anchor in content and "rejects command without required subcommand" not in content:
        content = content.replace(anchor, inserted)
    return GeneratedOutput(output.path, content)


def _patch_typescript_license_test(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    relative = path.relative_to(repo_root).as_posix()
    if not relative.startswith("generated/") or not relative.endswith("/typescript/test/command-package.test.mjs"):
        return output
    return GeneratedOutput(
        output.path,
        output.content.replace(
            "assert.deepEqual(packageJson.files, ['src', 'resources']);",
            "assert.deepEqual(packageJson.files, ['src', 'resources', 'LICENSE']);",
        ),
    )


def _patch_typescript_strict_preflight_gate(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    relative = path.relative_to(repo_root).as_posix()
    if not relative.startswith("generated/") or not relative.endswith("/typescript/src/cli.mjs"):
        return output
    if "Strict preflight gate is enabled." in output.content:
        return output
    invocation = "  const invocation = parseInvocation(commandDefinitionByName.get(command), argv.slice(1), [command]);\n"
    normalized_invocation = "  const invocation = parseInvocation(commandDefinitionByName.get(command), normalizedCommandTokens(argv.slice(1), [command]), [command]);\n"
    selected_invocation = normalized_invocation if normalized_invocation in output.content else invocation
    anchor = (
        selected_invocation
        + "  const operationId = invocation.operationRef?.id;\n"
        + "  const operationPath = invocation.operationRef?.path;\n"
    )
    inserted = (
        anchor + "  if (invocation.values.strict_preflight && !invocation.values.preflight_token) {\n"
        "    console.error(\"Strict preflight gate is enabled. Provide --preflight-token from 'agentic-workspace preflight --format json'.\");\n"
        "    process.exit(2);\n"
        "  }\n"
    )
    if anchor not in output.content:
        return output
    return GeneratedOutput(output.path, output.content.replace(anchor, inserted))


def _patch_typescript_runtime_template_ops(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    relative = path.relative_to(repo_root).as_posix()
    if not relative.startswith("generated/") or not relative.endswith("/typescript/src/runtime.mjs"):
        return output
    content = output.content
    count_anchor = "  if (keys.length === 1 && keys[0] === '$count') return Array.isArray(values[String(template.$count)]) ? values[String(template.$count)].length : 0;\n"
    if "Object.prototype.hasOwnProperty.call(template, '$exists_status')" not in content and count_anchor in content:
        content = content.replace(
            count_anchor,
            count_anchor
            + "  if (Object.prototype.hasOwnProperty.call(template, '$field')) {\n"
            + "    const spec = template.$field;\n"
            + "    const parts = Array.isArray(spec.path) ? spec.path.map(String) : String(spec.path ?? '').split('.').filter(Boolean);\n"
            + "    let value = values[String(spec.value ?? '')];\n"
            + "    for (const part of parts) {\n"
            + "      if (!isObject(value) || !Object.prototype.hasOwnProperty.call(value, part)) throw new RuntimeError(`template $field cannot resolve ${spec.value}.${parts.join('.')}`);\n"
            + "      value = value[part];\n"
            + "    }\n"
            + "    return value;\n"
            + "  }\n"
            + "  if (Object.prototype.hasOwnProperty.call(template, '$exists_status')) {\n"
            + "    const spec = template.$exists_status;\n"
            + "    return Boolean(values[String(spec.value ?? '')]) ? spec.present : spec.missing;\n"
            + "  }\n"
            + "  if (Object.prototype.hasOwnProperty.call(template, '$count_status')) {\n"
            + "    const spec = template.$count_status;\n"
            + "    const counted = values[String(spec.value ?? '')];\n"
            + "    return Array.isArray(counted) && counted.length ? spec.present : spec.missing;\n"
            + "  }\n"
            + "  if (Object.prototype.hasOwnProperty.call(template, '$join_path')) {\n"
            + "    const spec = template.$join_path;\n"
            + "    return join(String(values[String(spec.base ?? '')] ?? ''), String(spec.path ?? '')).replace(/\\\\/g, '/');\n"
            + "  }\n",
            1,
        )
    content = content.replace(
        "    storeStepResult(values, step.outputs ?? [], result);\n",
        "    storeStepResult(values, step.outputs ?? [], result);\n"
        "    if ((!Array.isArray(step.outputs) || step.outputs.length === 0) && String(step.uses ?? '') !== 'output.emit') values.result = result;\n",
    )
    content = content.replace(
        "  writeSync(1, output);\n  return 0;\n}\n",
        "  writeSync(1, output);\n"
        "  const exitStatus = finalValues.exit_status ?? finalValues.result?.exit_status;\n"
        "  return Number.isInteger(exitStatus) ? exitStatus : 0;\n}\n",
    )
    return GeneratedOutput(output.path, content)


def _patch_python_structured_usage_errors(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    relative = path.relative_to(repo_root).as_posix()
    if not relative.startswith("generated/") or not relative.endswith("/python/cli.py"):
        return output
    content = output.content
    content = content.replace("import difflib\n", "", 1)
    content = content.replace("import json\n", "import json\nimport shlex\n", 1)
    old_error = """    def error(self, message: str) -> None:
        for hint in getattr(self, '_generated_usage_error_hints', []):
            contains = hint.get('when_message_contains', [])
            argv_contains = hint.get('when_argv_contains', [])
            argv = self.__class__._generated_current_argv
            if all(str(fragment) in message for fragment in contains) and _argv_contains_sequence(argv, argv_contains):
                hint_text = str(hint.get('message', '')).strip()
                if hint_text:
                    message = f"{message}\\n{hint_text}"
        if 'invalid choice' in message and 'command' in message:
            unknown = _extract_unknown_command(message)
            suggestions = difflib.get_close_matches(unknown, generated_command_names(), n=1, cutoff=0.55)
            if suggestions:
                message = f"{message}\\nDid you mean: {', '.join(suggestions)}?"
            if 'start' in _GENERATED_COMMANDS_BY_NAME and 'preflight' in _GENERATED_COMMANDS_BY_NAME:
                message = (
                    f"{message}\\nStartup tip: run '{self.prog} start --task \\"<task>\\" --format json' "
                    f"for normal startup or '{self.prog} preflight --format json' to recover a compact takeover context."
                )
        super().error(message)
"""
    new_error = """    def error(self, message: str) -> None:
        argv = self.__class__._generated_current_argv
        suggested_command = ''
        alternatives: list[str] = []
        for hint in getattr(self, '_generated_usage_error_hints', []):
            contains = hint.get('when_message_contains', [])
            argv_contains = hint.get('when_argv_contains', [])
            if all(str(fragment) in message for fragment in contains) and _argv_contains_sequence(argv, argv_contains):
                hint_text = str(hint.get('message', '')).strip()
                if hint_text:
                    message = f"{message}\\n{hint_text}"
        if 'invalid choice' in message and 'command' in message:
            unknown = _extract_unknown_command(message)
            authority = _authoritative_command_authority(argv)
            recovery_token = _recovery_token(argv, authority, unknown)
            suggestion = _closest_authoritative_choice(recovery_token, _authoritative_command_choices(authority))
            if suggestion:
                message = f"{message}\\nDid you mean: {suggestion}?"
                suggested_command = _canonical_recovery_command(argv, authority, recovery_token, suggestion)
            elif unknown in authority:
                suggested_command = _canonical_recovery_command(argv, authority, unknown, unknown)
            if 'start' in _GENERATED_COMMANDS_BY_NAME and 'preflight' in _GENERATED_COMMANDS_BY_NAME:
                message = (
                    f"{message}\\nStartup tip: run '{self.prog} start --task \\"<task>\\" --format json' "
                    f"for normal startup or '{self.prog} preflight --format json' to recover a compact takeover context."
                )
        if _is_selector_conflict(argv, message):
            alternatives = _selector_conflict_alternatives(self.prog, argv)
            if alternatives and not suggested_command:
                suggested_command = alternatives[0]
        structured_error = ('invalid choice' in message and 'command' in message) or _is_selector_conflict(argv, message)
        if _json_requested(argv) and structured_error:
            print(json.dumps(_retryable_cli_error_payload(
                prog=self.prog,
                argv=argv,
                message=message,
                suggested_command=suggested_command,
                alternatives=alternatives,
            ), indent=2))
            raise SystemExit(2)
        super().error(message)
"""
    if old_error not in content:
        return output
    content = content.replace(old_error, new_error)
    old_helpers = """def _extract_unknown_command(message: str) -> str:
    prefix = "invalid choice: '"
    if prefix not in message:
        return ''
    return message.split(prefix, 1)[1].split("'", 1)[0]


def _argv_contains_sequence(argv: list[str], sequence: Any) -> bool:
"""
    new_helpers = """def _extract_unknown_command(message: str) -> str:
    prefix = "invalid choice: '"
    if prefix not in message:
        return ''
    return message.split(prefix, 1)[1].split("'", 1)[0]


def _json_requested(argv: list[str]) -> bool:
    for index, token in enumerate(argv):
        if token == '--format' and index + 1 < len(argv) and argv[index + 1] == 'json':
            return True
        if token == '--format=json':
            return True
    return False


def _command_with_replaced_token(prog: str, argv: list[str], old: str, new: str) -> str:
    replaced = [new if token == old else token for token in argv]
    return f"{prog} {shlex.join(replaced)}"


def _recovery_token(argv: list[str], authority: list[str], unknown: str) -> str:
    remaining = list(argv)
    while authority and remaining[:len(authority)] == authority:
        remaining = remaining[len(authority):]
    if unknown in authority and remaining:
        return remaining[0]
    return unknown


def _authoritative_command_authority(argv: list[str]) -> list[str]:
    current: dict[str, Any] | None = None
    authority: list[str] = []
    for token in argv:
        choices = [command.get('interface', {}) for command in _GENERATED_ADAPTER_COMMANDS] if current is None else current.get('subcommands', [])
        next_interface = next(
            (item for item in choices if isinstance(item, dict) and str(item.get('name', '')) == token),
            None,
        )
        if next_interface is None:
            break
        authority.append(token)
        current = next_interface
    return authority


def _authoritative_command_choices(authority: list[str]) -> list[str]:
    # Read the active command surface from generated command IR, never parser prose.
    interfaces = [command.get('interface', {}) for command in _GENERATED_ADAPTER_COMMANDS]
    current: dict[str, Any] | None = None
    for token in authority:
        choices = interfaces if current is None else current.get('subcommands', [])
        current = next(
            (item for item in choices if isinstance(item, dict) and str(item.get('name', '')) == token),
            None,
        )
        if current is None:
            return []
    choices = interfaces if current is None else current.get('subcommands', [])
    return [str(item.get('name', '')) for item in choices if isinstance(item, dict) and str(item.get('name', '')).strip()]


def _authoritative_command_interface(authority: list[str]) -> dict[str, Any] | None:
    interfaces = [command.get('interface', {}) for command in _GENERATED_ADAPTER_COMMANDS]
    current: dict[str, Any] | None = None
    for token in authority:
        choices = interfaces if current is None else current.get('subcommands', [])
        current = next(
            (item for item in choices if isinstance(item, dict) and str(item.get('name', '')) == token),
            None,
        )
        if current is None:
            return None
    return current


def _interface_requires_help(interface: dict[str, Any] | None) -> bool:
    if not isinstance(interface, dict):
        return False
    subcommands = interface.get('subcommands', [])
    if isinstance(subcommands, list) and subcommands and interface.get('subcommands_required') is not False:
        return True
    arguments = interface.get('arguments', [])
    if isinstance(arguments, list) and any(isinstance(argument, dict) and argument.get('nargs') != '?' and 'default' not in argument for argument in arguments):
        return True
    options = interface.get('options', [])
    return isinstance(options, list) and any(isinstance(option, dict) and option.get('required') is True for option in options)


def _closest_authoritative_choice(token: str, choices: list[str]) -> str:
    if not token or not choices:
        return ''
    def distance(left: str, right: str) -> int:
        rows = list(range(len(right) + 1))
        for left_index, left_character in enumerate(left, start=1):
            next_rows = [left_index]
            for right_index, right_character in enumerate(right, start=1):
                next_rows.append(min(rows[right_index] + 1, next_rows[right_index - 1] + 1, rows[right_index - 1] + (left_character != right_character)))
            rows = next_rows
        return rows[-1]
    def subsequence(left: str, right: str) -> int:
        rows = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
        for left_index, left_character in enumerate(left, start=1):
            for right_index, right_character in enumerate(right, start=1):
                rows[left_index][right_index] = rows[left_index - 1][right_index - 1] + 1 if left_character == right_character else max(rows[left_index - 1][right_index], rows[left_index][right_index - 1])
        return rows[-1][-1]
    best = min(choices, key=lambda candidate: (distance(token, candidate), -subsequence(token, candidate)))
    similarity = 1 - distance(token, best) / max(len(token), len(best), 1)
    return best if similarity >= 0.55 else ''


def _canonical_recovery_command(argv: list[str], authority: list[str], old: str, new: str) -> str:
    root = str(GENERATED_COMMAND_PACKAGE.get('program') or 'agentic-workspace')
    candidate_authority = [*authority, new]
    if _interface_requires_help(_authoritative_command_interface(candidate_authority)):
        return shlex.join([root, *candidate_authority, '--help'])
    remaining = list(argv)
    while authority and remaining[:len(authority)] == authority:
        remaining = remaining[len(authority):]
    replaced = [new if token == old else token for token in remaining]
    return shlex.join([root, *authority, *replaced])


def _is_selector_conflict(argv: list[str], message: str) -> bool:
    return (
        ('--verbose' in argv and '--section' in argv)
        or 'not allowed with argument' in message
        or 'mutually exclusive' in message
    )


def _selector_conflict_alternatives(prog: str, argv: list[str]) -> list[str]:
    if not argv:
        return []
    without_verbose = [token for token in argv if token != '--verbose']
    without_section: list[str] = []
    skip_next = False
    for token in argv:
        if skip_next:
            skip_next = False
            continue
        if token == '--section':
            skip_next = True
            continue
        without_section.append(token)
    root_prog = prog.split()[0]
    return [f"{root_prog} {shlex.join(without_verbose)}", f"{root_prog} {shlex.join(without_section)}"]


def _retryable_cli_error_payload(
    *, prog: str, argv: list[str], message: str, suggested_command: str, alternatives: list[str]
) -> dict[str, Any]:
    failure_class = 'selector-conflict' if _is_selector_conflict(argv, message) else 'invalid-command' if 'invalid choice' in message and 'command' in message else 'usage-error'
    return {
        'kind': _retryable_cli_error_kind(prog),
        'exit_status': 2,
        'input_command': f"{prog.split()[0]} {shlex.join(argv)}",
        'failure_class': failure_class,
        'safe_to_retry': bool(suggested_command) or failure_class != 'invalid-command',
        'message': message,
        'suggested_command': suggested_command,
        'alternatives': alternatives,
    }


def _retryable_cli_error_kind(prog: str) -> str:
    root_prog = prog.split()[0]
    namespace = root_prog if root_prog.startswith('agentic-') else 'agentic-workspace'
    return f"{namespace}/retryable-cli-error/v1"


def _argv_contains_sequence(argv: list[str], sequence: Any) -> bool:
"""
    if old_helpers not in content:
        return output
    return GeneratedOutput(output.path, content.replace(old_helpers, new_helpers))


def _patch_python_operation_exit_status(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    relative = path.relative_to(repo_root).as_posix()
    if relative != "generated/workspace/python/primitives/operation_executor.py":
        return output
    old_return = """    if isinstance(emitted, str):
        print(emitted, end='')
    return 0
"""
    new_return = """    if isinstance(emitted, str):
        print(emitted, end='')
    exit_status = values.get('exit_status')
    if not isinstance(exit_status, int) and isinstance(values.get('result'), Mapping):
        exit_status = values['result'].get('exit_status')
    return exit_status if isinstance(exit_status, int) else 0
"""
    if old_return not in output.content:
        return output
    return GeneratedOutput(output.path, output.content.replace(old_return, new_return, 1))


def _patch_workspace_python_operation_inputs(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    """Preserve every parser/callable input instead of a generated allowlist.

    The command and operation contracts already own the accepted interface. A
    second hand-maintained projection in the Python executor may not silently
    discard a newly supported option.
    """

    path = output.path if output.path.is_absolute() else repo_root / output.path
    if path.relative_to(repo_root).as_posix() != "generated/workspace/python/primitives/operation_executor.py":
        return output
    content = output.content
    args_anchor = "                'lifecycle_action': getattr(args, 'lifecycle_action', None),\n"
    args_insert = args_anchor + "                **{name: value for name, value in vars(args).items() if not name.startswith('_')},\n"
    if args_anchor in content and "value in vars(args).items()" not in content:
        content = content.replace(args_anchor, args_insert, 1)
    values_anchor = "                'lifecycle_action': values.get('lifecycle_action', None),\n"
    values_insert = values_anchor + "                **dict(values),\n"
    if values_anchor in content and "                **dict(values),\n" not in content:
        content = content.replace(values_anchor, values_insert, 1)
    return GeneratedOutput(output.path, content)


def _patch_planning_python_runtime_values(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    """Preserve contract-declared Planning inputs through parser and callable dispatch."""

    path = output.path if output.path.is_absolute() else repo_root / output.path
    relative = path.relative_to(repo_root).as_posix()
    if relative != "generated/planning/python/primitives/operation_executor.py":
        return output
    content = output.content
    args_anchor = "                'expect_planning_revision': getattr(args, 'expect_planning_revision', ''),\n"
    args_insert = (
        args_anchor
        + "                'preflight_token': getattr(args, 'preflight_token', ''),\n"
        + "                'preflight_max_age_seconds': getattr(args, 'preflight_max_age_seconds', 900),\n"
        + "                **{name: value for name, value in vars(args).items() if not name.startswith('_')},\n"
    )
    if args_anchor in content and "'preflight_token': getattr(args, 'preflight_token', '')," not in content:
        content = content.replace(args_anchor, args_insert, 1)
    if args_anchor in content and "value in vars(args).items()" not in content:
        content = content.replace(
            args_anchor,
            args_anchor + "                **{name: value for name, value in vars(args).items() if not name.startswith('_')},\n",
            1,
        )
    values_anchor = "                'expect_planning_revision': values.get('expect_planning_revision', ''),\n"
    values_insert = (
        values_anchor
        + "                'preflight_token': values.get('preflight_token', ''),\n"
        + "                'preflight_max_age_seconds': values.get('preflight_max_age_seconds', 900),\n"
        + "                **dict(values),\n"
    )
    if values_anchor in content and "'preflight_token': values.get('preflight_token', '')," not in content:
        content = content.replace(values_anchor, values_insert, 1)
    if values_anchor in content and "                **dict(values),\n" not in content:
        content = content.replace(values_anchor, values_anchor + "                **dict(values),\n", 1)
    reconcile_values = (
        ("apply_lane_current_slice_reconcile", "False"),
        ("owner_surface", "''"),
        ("relation_identity", "''"),
        ("subject", "''"),
        ("expected_lane_revision", "''"),
        ("transition", "''"),
        ("expected_execplan", "''"),
        ("apply_issue_relation_reconcile", "False"),
        ("apply_issue_relation_migration", "False"),
        ("apply_pending_integrations", "False"),
        ("preview", "False"),
    )
    args_reconcile_anchor = "                'apply_lane_reconcile': getattr(args, 'apply_lane_reconcile', False),\n"
    values_reconcile_anchor = "                'apply_lane_reconcile': values.get('apply_lane_reconcile', False),\n"
    args_reconcile_insert = args_reconcile_anchor + "".join(
        f"                '{name}': getattr(args, '{name}', {default}),\n" for name, default in reconcile_values
    )
    values_reconcile_insert = values_reconcile_anchor + "".join(
        f"                '{name}': values.get('{name}', {default}),\n" for name, default in reconcile_values
    )
    if args_reconcile_anchor in content and "'apply_pending_integrations': getattr(args" not in content:
        content = content.replace(args_reconcile_anchor, args_reconcile_insert, 1)
    if values_reconcile_anchor in content and "'apply_pending_integrations': values.get(" not in content:
        content = content.replace(values_reconcile_anchor, values_reconcile_insert, 1)
    return GeneratedOutput(output.path, content)


def _patch_typescript_structured_usage_errors(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    relative = path.relative_to(repo_root).as_posix()
    if not relative.startswith("generated/") or not relative.endswith("/typescript/src/cli.mjs"):
        return output
    program_marker = "// Program: "
    if program_marker not in output.content:
        return output
    program = output.content.split(program_marker, 1)[1].split("\n", 1)[0].strip()
    old_validation = """function failValidation(message) {
  console.error(`TypeScript CLI validation failed: ${message}`);
  console.error('Recovery: run agentic-workspace --help and choose a supported generated command or valid option.');
  process.exit(2);
}
"""
    new_validation = f"""const generatedProgram = {json.dumps(program)};

function authoritativeInterface(path) {{
  let current = commandDefinitionByName.get(path[0])?.interface;
  for (const token of path.slice(1)) {{
    current = interfaceSubcommands(current).find((candidate) => candidate.name === token);
  }}
  return current;
}}

function canonicalRecovery(path, unknown, replacement) {{
  const candidatePath = [...path, replacement];
  if (interfaceRequiresHelp(authoritativeInterface(candidatePath))) return [generatedProgram, ...candidatePath, '--help'].map(shellQuote).join(' ');
  let remaining = argv.slice(path.length);
  while (path.length && path.every((token, index) => remaining[index] === token)) remaining = remaining.slice(path.length);
  remaining = remaining.map((token) => token === unknown ? replacement : token);
  return [generatedProgram, ...path, ...remaining].map(shellQuote).join(' ');
}}

function shellQuote(token) {{
  const value = String(token);
  return /^[A-Za-z0-9_@%+=:,./-]+$/.test(value) ? value : `'${{value.replace(/'/g, `'"'"'`)}}'`;
}}

function normalizedCommandTokens(tokens, path) {{
  let remaining = [...tokens];
  while (path.length && path.every((token, index) => remaining[index] === token)) remaining = remaining.slice(path.length);
  return remaining;
}}

function interfaceRequiresHelp(iface) {{
  if (!iface) return false;
  if (interfaceSubcommands(iface).length && iface.subcommands_required !== false) return true;
  if (interfaceArguments(iface).some((argument) => argument.nargs !== '?' && !Object.prototype.hasOwnProperty.call(argument, 'default'))) return true;
  return interfaceOptions(iface).some((option) => option.required === true);
}}

function closestAuthoritativeChoice(token, choices) {{
  if (!token || !choices.length) return '';
  const distance = (left, right) => {{
    const rows = Array.from({{ length: left.length + 1 }}, (_, index) => [index]);
    for (let column = 0; column <= right.length; column += 1) rows[0][column] = column;
    for (let row = 1; row <= left.length; row += 1) {{
      for (let column = 1; column <= right.length; column += 1) {{
        rows[row][column] = left[row - 1] === right[column - 1]
          ? rows[row - 1][column - 1]
          : 1 + Math.min(rows[row - 1][column], rows[row][column - 1], rows[row - 1][column - 1]);
      }}
    }}
    return rows[left.length][right.length];
  }};
  const subsequence = (left, right) => {{
    const rows = Array.from({{ length: left.length + 1 }}, () => Array(right.length + 1).fill(0));
    for (let row = 1; row <= left.length; row += 1) {{
      for (let column = 1; column <= right.length; column += 1) {{
        rows[row][column] = left[row - 1] === right[column - 1]
          ? rows[row - 1][column - 1] + 1
          : Math.max(rows[row - 1][column], rows[row][column - 1]);
      }}
    }}
    return rows[left.length][right.length];
  }};
  const best = choices.reduce((current, candidate) => {{
    const candidateDistance = distance(token, candidate);
    const currentDistance = distance(token, current);
    return candidateDistance < currentDistance || (candidateDistance === currentDistance && subsequence(token, candidate) > subsequence(token, current)) ? candidate : current;
  }}, choices[0]);
  const similarity = 1 - distance(token, best) / Math.max(token.length, best.length, 1);
  return similarity >= 0.55 ? best : '';
}}

function failValidation(message, path = []) {{
  const unknown = /^unknown command ([^ ]+)/.exec(message)?.[1] ?? '';
  const choices = path.length
    ? interfaceSubcommands(authoritativeInterface(path)).map((candidate) => candidate.name)
    : commandDefinitions.map((definition) => definition.name);
  const suggestion = unknown ? closestAuthoritativeChoice(unknown, choices) : '';
  const suggestedCommand = suggestion ? canonicalRecovery(path, unknown, suggestion) : '';
  const payload = {{
    kind: `${{generatedProgram}}/retryable-cli-error/v1`,
    exit_status: 2,
    failure_class: unknown ? 'invalid-command' : 'usage-error',
    safe_to_retry: Boolean(suggestedCommand) || !unknown,
    message,
    suggested_command: suggestedCommand,
    alternatives: [],
  }};
  if (argv.includes('--format') && argv[argv.indexOf('--format') + 1] === 'json') {{
    console.log(JSON.stringify(payload, null, 2));
  }} else {{
    console.error(`TypeScript CLI validation failed: ${{message}}`);
    if (suggestedCommand) console.error(`Did you mean: ${{suggestedCommand}}`);
    console.error(`Recovery: run ${{generatedProgram}} --help and choose a supported generated command or valid option.`);
  }}
  process.exit(2);
}}
"""
    if old_validation not in output.content:
        return output
    content = output.content.replace(old_validation, new_validation)
    content = content.replace(
        "    positional.push(token);\n    index += 1;",
        "    if (interfaceSubcommands(iface).length) failValidation(`unknown command ${token} for ${path.join(' ')}`, path);\n    positional.push(token);\n    index += 1;",
    )
    content = content.replace(
        "  console.error(`Unsupported generated command: ${command}`);\n  console.error('Recovery: run agentic-workspace --help and choose one of the supported generated commands.');\n  process.exit(2);",
        "  failValidation(`unknown command ${command}`, []);",
    )
    content = content.replace(
        "parseInvocation(commandDefinitionByName.get(command), argv.slice(1), [command])",
        "parseInvocation(commandDefinitionByName.get(command), normalizedCommandTokens(argv.slice(1), [command]), [command])",
    )
    content = content.replace(
        "validateInterface(commandByName.get(command), argv.slice(1), [command]);",
        "validateInterface(commandByName.get(command), normalizedCommandTokens(argv.slice(1), [command]), [command]);",
    )
    content = content.replace(
        "      if (iface.subcommand_dest) nested.values[iface.subcommand_dest] = token;\n      return nested;",
        "      const parentDefaults = initialValues(iface);\n"
        "      for (const [name, value] of Object.entries(values)) {\n"
        "        if (JSON.stringify(value) !== JSON.stringify(parentDefaults[name])) nested.values[name] = value;\n"
        "      }\n"
        "      if (iface.subcommand_dest) nested.values[iface.subcommand_dest] = token;\n"
        "      return nested;",
    )
    return GeneratedOutput(output.path, content)


def render_workspace_command_package_outputs(
    manifest: dict[str, object] | None = None,
    *,
    repo_root: Path = REPO_ROOT,
) -> list[GeneratedOutput]:
    effective_manifest = (
        _resolve_interface_projections(manifest) if manifest is not None else load_workspace_command_package_ir(repo_root=repo_root)
    )
    outputs = render_outputs(
        effective_manifest,
        repo_root=repo_root,
        source_path=SOURCE_PATH,
        regenerate_command=REGENERATE_COMMAND,
        host_manifest=workspace_command_generation_host_manifest(repo_root=repo_root),
    )
    release_metadata = _typescript_release_package_metadata(repo_root=repo_root)
    normalized_outputs = [
        _patch_typescript_selector_descriptors(
            _patch_typescript_license_test(
                _patch_external_consumer_exports(
                    _patch_typescript_runtime_template_ops(
                        _patch_typescript_strict_preflight_gate(
                            _patch_workspace_typescript_sample_command_test(
                                _patch_python_operation_exit_status(
                                    _patch_workspace_python_operation_inputs(
                                        _patch_python_structured_usage_errors(
                                        _patch_planning_python_runtime_values(
                                            _patch_typescript_structured_usage_errors(
                                                _normalize_releaseable_typescript_package_json(
                                                    output, release_metadata=release_metadata, repo_root=repo_root
                                                ),
                                                repo_root=repo_root,
                                            ),
                                            repo_root=repo_root,
                                        ),
                                        repo_root=repo_root,
                                        ),
                                        repo_root=repo_root,
                                    ),
                                    repo_root=repo_root,
                                ),
                                repo_root=repo_root,
                                manifest=effective_manifest,
                            ),
                            repo_root=repo_root,
                        ),
                        repo_root=repo_root,
                    ),
                    repo_root=repo_root,
                ),
                repo_root=repo_root,
            ),
            repo_root=repo_root,
        )
        for output in outputs
    ]
    return [*normalized_outputs, *_typescript_license_outputs(release_metadata=release_metadata, repo_root=repo_root)]


def _patch_external_consumer_exports(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    relative = path.relative_to(repo_root).as_posix()
    if relative == "generated/workspace/python/commands/planning_front_door.py":
        content = output.content.replace(
            """import argparse

from typing import Any
from collections.abc import Mapping

# DO NOT EDIT DIRECTLY.
# Command behavior changes belong in src/agentic_workspace/contracts/command_package_ir.json and the referenced operation contract.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

import contextlib
import io
import json
from ..cli import build_generated_parser
""",
            """import argparse
import contextlib
import io
import json
from collections.abc import Mapping
from typing import Any

from ..cli import build_generated_parser

# DO NOT EDIT DIRECTLY.
# Command behavior changes belong in src/agentic_workspace/contracts/command_package_ir.json and the referenced operation contract.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py
""",
        )
        old = """def invoke(_values: Mapping[str, Any]) -> object:
    raise RuntimeError('planning.front-door' + ' has no generated operation callable')
"""
        new = """def invoke(_values: Mapping[str, Any]) -> object:
    from agentic_workspace.workspace_runtime_planning import execute_planning_front_door_route_action

    return execute_planning_front_door_route_action(_values)
"""
        if old in content:
            content = content.replace(old, new)
        proposal_anchor = "('--proposal-id', 'proposal_id', '', 'value'),"
        if proposal_anchor in content and "('--proposal', 'proposal', '', 'value')," not in content:
            content = content.replace(
                proposal_anchor,
                proposal_anchor + " ('--proposal', 'proposal', '', 'value'),",
                1,
            )
        return GeneratedOutput(output.path, content)
    if relative != "generated/workspace/typescript/package.json":
        return output
    payload = json.loads(output.content)
    payload["exports"] = {
        ".": "./src/client.mjs",
        "./contracts": "./external_contract_bundle.json",
        "./profile": "./external_consumer_profile.json",
        "./conformance-receipts": "./external_operation_conformance_receipts.json",
    }
    files = [str(item) for item in payload.get("files", []) if str(item) != "LICENSE"]
    if "external_consumer_profile.json" not in files:
        files.append("external_consumer_profile.json")
    if "external_contract_bundle.json" not in files:
        files.append("external_contract_bundle.json")
    if "external_operation_conformance_receipts.json" not in files:
        files.append("external_operation_conformance_receipts.json")
    files.append("LICENSE")
    payload["files"] = files
    return GeneratedOutput(output.path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def generate_workspace_command_packages(*, repo_root: Path = REPO_ROOT, check: bool) -> list[str]:
    stale: list[str] = []
    for output in render_workspace_command_package_outputs(repo_root=repo_root):
        path = output.path if output.path.is_absolute() else repo_root / output.path
        relative = path.relative_to(repo_root).as_posix()
        if path.exists() and path.read_bytes() == output.content.encode("utf-8"):
            continue
        stale.append(relative)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output.content, encoding="utf-8", newline="\n")
            print(f"[ok] wrote {relative}")
    return stale
