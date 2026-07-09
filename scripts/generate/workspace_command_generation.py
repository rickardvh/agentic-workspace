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
PYTHON_PRIMITIVE_SUPPORT_PATH = "src/agentic_workspace/contracts/python_primitive_support.py"
TYPESCRIPT_PRIMITIVE_SUPPORT_PATH = "src/agentic_workspace/contracts/typescript_primitive_support.mjs"
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
        python_primitive_support_path=repo_root / PYTHON_PRIMITIVE_SUPPORT_PATH,
        typescript_primitive_support_path=repo_root / TYPESCRIPT_PRIMITIVE_SUPPORT_PATH,
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
        f'[{json.dumps(sample_command)}, "--format", "json"]',
        f"[...{rendered_sample_path}, \"--format\", \"json\"]",
    )
    content = content.replace(
        f'[{json.dumps(sample_command)}, "--target", "__SPACED_TARGET__"]',
        f"[...{rendered_sample_path}, \"--target\", \"__SPACED_TARGET__\"]",
    )
    if not subcommands_required:
        return GeneratedOutput(output.path, content)
    anchor = (
        "test('generated runnable adapter preserves spaced argv values during native execution', () => {\n"
        "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
        "  const spacedTarget = fileURLToPath(new URL('../tmp target with spaces', import.meta.url));\n"
        "  mkdirSync(spacedTarget, { recursive: true });\n"
        "  try {\n"
        f"    const args = [...{rendered_sample_path}, \"--target\", \"__SPACED_TARGET__\"].map((token) => token === '__SPACED_TARGET__' ? spacedTarget : token);\n"
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
        + f"  const result = spawnSync(process.execPath, [cli, ...{rendered_root_path}, \"--format\", \"json\"], {{ encoding: 'utf8' }});\n"
        + "  assert.equal(result.status, 2);\n"
        + "  assert.equal(result.stdout, '');\n"
        + f"  assert.match(result.stderr, /missing subcommand for {sample_command}/);\n"
        + "  assert.doesNotMatch(result.stderr, /runtime handoff/i);\n"
        + "});\n"
    )
    if anchor in content and "rejects command without required subcommand" not in content:
        content = content.replace(anchor, inserted)
    return GeneratedOutput(output.path, content)


def _patch_typescript_strict_preflight_gate(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    relative = path.relative_to(repo_root).as_posix()
    if not relative.startswith("generated/") or not relative.endswith("/typescript/src/cli.mjs"):
        return output
    if "Strict preflight gate is enabled." in output.content:
        return output
    anchor = (
        "function maybeRunNativeOperation() {\n"
        "  const invocation = parseInvocation(commandDefinitionByName.get(command), argv.slice(1), [command]);\n"
        "  const operationId = invocation.operationRef?.id;\n"
        "  const operationPath = invocation.operationRef?.path;\n"
        "  try {\n"
    )
    inserted = (
        "function maybeRunNativeOperation() {\n"
        "  const invocation = parseInvocation(commandDefinitionByName.get(command), argv.slice(1), [command]);\n"
        "  const operationId = invocation.operationRef?.id;\n"
        "  const operationPath = invocation.operationRef?.path;\n"
        "  if (invocation.values.strict_preflight && !invocation.values.preflight_token) {\n"
        "    console.error(\"Strict preflight gate is enabled. Provide --preflight-token from 'agentic-workspace preflight --format json'.\");\n"
        "    process.exit(2);\n"
        "  }\n"
        "  try {\n"
    )
    if anchor not in output.content:
        return output
    return GeneratedOutput(output.path, output.content.replace(anchor, inserted))


def _patch_typescript_runtime_template_ops(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    relative = path.relative_to(repo_root).as_posix()
    if not relative.startswith("generated/") or not relative.endswith("/typescript/src/runtime.mjs"):
        return output
    if "$exists_status" in output.content:
        return output
    anchor = (
        "function resolveTemplate(template, values) {\n"
        "  if (Array.isArray(template)) return template.map((item) => resolveTemplate(item, values));\n"
        "  if (!isObject(template)) return template;\n"
        "  const keys = Object.keys(template);\n"
        "  if (keys.length === 1 && keys[0] === '$value') return values[String(template.$value)];\n"
        "  if (keys.length === 1 && keys[0] === '$count') return Array.isArray(values[String(template.$count)]) ? values[String(template.$count)].length : 0;\n"
        "  return Object.fromEntries(Object.entries(template).map(([key, value]) => [key, resolveTemplate(value, values)]));\n"
        "}\n"
    )
    inserted = (
        "function resolveTemplate(template, values) {\n"
        "  if (Array.isArray(template)) return template.map((item) => resolveTemplate(item, values));\n"
        "  if (!isObject(template)) return template;\n"
        "  const keys = Object.keys(template);\n"
        "  if (keys.length === 1 && keys[0] === '$value') return values[String(template.$value)];\n"
        "  if (Object.prototype.hasOwnProperty.call(template, '$field')) {\n"
        "    const spec = template.$field;\n"
        "    const parts = Array.isArray(spec.path) ? spec.path.map(String) : String(spec.path ?? '').split('.').filter(Boolean);\n"
        "    let value = values[String(spec.value ?? '')];\n"
        "    for (const part of parts) {\n"
        "      if (!isObject(value) || !Object.prototype.hasOwnProperty.call(value, part)) throw new RuntimeError(`template $field cannot resolve ${spec.value}.${parts.join('.')}`);\n"
        "      value = value[part];\n"
        "    }\n"
        "    return value;\n"
        "  }\n"
        "  if (keys.length === 1 && keys[0] === '$count') return Array.isArray(values[String(template.$count)]) ? values[String(template.$count)].length : 0;\n"
        "  if (Object.prototype.hasOwnProperty.call(template, '$exists_status')) {\n"
        "    const spec = template.$exists_status;\n"
        "    return Boolean(values[String(spec.value ?? '')]) ? spec.present : spec.missing;\n"
        "  }\n"
        "  if (Object.prototype.hasOwnProperty.call(template, '$count_status')) {\n"
        "    const spec = template.$count_status;\n"
        "    const counted = values[String(spec.value ?? '')];\n"
        "    return Array.isArray(counted) && counted.length ? spec.present : spec.missing;\n"
        "  }\n"
        "  if (Object.prototype.hasOwnProperty.call(template, '$join_path')) {\n"
        "    const spec = template.$join_path;\n"
        "    return join(String(values[String(spec.base ?? '')] ?? ''), String(spec.path ?? '')).replace(/\\\\/g, '/');\n"
        "  }\n"
        "  return Object.fromEntries(Object.entries(template).map(([key, value]) => [key, resolveTemplate(value, values)]));\n"
        "}\n"
    )
    if anchor not in output.content:
        return output
    return GeneratedOutput(output.path, output.content.replace(anchor, inserted))


def _patch_python_structured_usage_errors(output: GeneratedOutput, *, repo_root: Path) -> GeneratedOutput:
    path = output.path if output.path.is_absolute() else repo_root / output.path
    relative = path.relative_to(repo_root).as_posix()
    if not relative.startswith("generated/") or not relative.endswith("/python/cli.py"):
        return output
    content = output.content
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
            suggestions = difflib.get_close_matches(unknown, generated_command_names(), n=1, cutoff=0.55)
            if suggestions:
                message = f"{message}\\nDid you mean: {', '.join(suggestions)}?"
                suggested_command = _command_with_replaced_token(self.prog, argv, unknown, suggestions[0])
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
    return [f"{prog} {shlex.join(without_verbose)}", f"{prog} {shlex.join(without_section)}"]


def _retryable_cli_error_payload(
    *, prog: str, argv: list[str], message: str, suggested_command: str, alternatives: list[str]
) -> dict[str, Any]:
    failure_class = 'selector-conflict' if _is_selector_conflict(argv, message) else 'invalid-command' if 'invalid choice' in message and 'command' in message else 'usage-error'
    return {
        'kind': 'agentic-workspace/retryable-cli-error/v1',
        'exit_status': 2,
        'input_command': f"{prog} {shlex.join(argv)}",
        'failure_class': failure_class,
        'safe_to_retry': True,
        'message': message,
        'suggested_command': suggested_command,
        'alternatives': alternatives,
    }


def _argv_contains_sequence(argv: list[str], sequence: Any) -> bool:
"""
    if old_helpers not in content:
        return output
    return GeneratedOutput(output.path, content.replace(old_helpers, new_helpers))


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
        _patch_typescript_runtime_template_ops(
            _patch_typescript_strict_preflight_gate(
                _patch_workspace_typescript_sample_command_test(
                    _patch_python_structured_usage_errors(
                        _normalize_releaseable_typescript_package_json(output, release_metadata=release_metadata, repo_root=repo_root),
                        repo_root=repo_root,
                    ),
                    repo_root=repo_root,
                    manifest=effective_manifest,
                ),
                repo_root=repo_root,
            ),
            repo_root=repo_root,
        )
        for output in outputs
    ]



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
