from __future__ import annotations

import json
from pathlib import Path

from command_generation import (
    BUILTIN_PORTABLE_PRIMITIVES,
    CommandGenerationHostManifest,
    GeneratedOutput,
    PrimitiveRegistry,
    command_package_schema_path,
    generate_command_packages,
    load_command_package_ir,
    render_outputs,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = "src/agentic_workspace/contracts/command_package_ir.json"
SCHEMA_PATH = "command_generation:schemas/command_package_ir.schema.json"
REGENERATE_COMMAND = "uv run python scripts/generate/generate_command_packages.py"
TYPESCRIPT_RUNTIME_SUPPORT_PATH = "src/agentic_workspace/contracts/typescript_runtime_support.mjs"


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


def _host_primitive_definitions(manifest: dict[str, object], *, repo_root: Path) -> list[dict[str, object]]:
    builtin_ids = BUILTIN_PORTABLE_PRIMITIVES.ids()
    primitive_ids: set[str] = {
        "workspace.config.load",
        "workspace.config.emit",
        "workspace.defaults.load",
        "workspace.defaults.select",
        "output.fields.select",
        "typescript.domain.execute",
    }
    for package in manifest.get("packages", []):
        if not isinstance(package, dict):
            continue
        operation_contract_root = repo_root / str(package.get("operation_contract_root", ""))
        for command in package.get("commands", []):
            if not isinstance(command, dict):
                continue
            for operation_ref in _operation_refs(command):
                operation_path = str(operation_ref.get("path", ""))
                source = operation_contract_root / operation_path
                if not source.is_file():
                    continue
                operation = json.loads(source.read_text(encoding="utf-8"))
                steps = operation.get("ir_plan", {}).get("steps", [])
                if not isinstance(steps, list):
                    continue
                for step in steps:
                    if isinstance(step, dict):
                        primitive = str(step.get("uses", "")).strip()
                        if primitive and primitive not in builtin_ids:
                            primitive_ids.add(primitive)
    return [
        {
            "id": primitive_id,
            "kind": "host",
            "target_support": {"python": "host-implemented", "typescript": "host-implemented"},
            "owner": "agentic-workspace",
        }
        for primitive_id in sorted(primitive_ids)
    ]


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
    )


def load_workspace_command_package_ir(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    return load_command_package_ir(repo_root / SOURCE_PATH, command_package_schema_path())


def render_workspace_command_package_outputs(
    manifest: dict[str, object] | None = None,
    *,
    repo_root: Path = REPO_ROOT,
) -> list[GeneratedOutput]:
    effective_manifest = manifest if manifest is not None else load_workspace_command_package_ir(repo_root=repo_root)
    return render_outputs(
        effective_manifest,
        repo_root=repo_root,
        source_path=SOURCE_PATH,
        regenerate_command=REGENERATE_COMMAND,
        host_manifest=workspace_command_generation_host_manifest(repo_root=repo_root),
    )


def generate_workspace_command_packages(*, repo_root: Path = REPO_ROOT, check: bool) -> list[str]:
    return generate_command_packages(
        load_workspace_command_package_ir(repo_root=repo_root),
        repo_root=repo_root,
        source_path=SOURCE_PATH,
        regenerate_command=REGENERATE_COMMAND,
        check=check,
        host_manifest=workspace_command_generation_host_manifest(repo_root=repo_root),
    )
