from __future__ import annotations

# ruff: noqa: F401
import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from command_generation.generated_package_loader import load_generated_command_module_for_entrypoint
from jsonschema import Draft202012Validator

from agentic_workspace import workspace_runtime_primitives
from agentic_workspace.contract_tooling import authority_markers_manifest, cli_commands_manifest
from agentic_workspace.result_adapter import adapt_action, adapt_module_result

_generated_cli = load_generated_command_module_for_entrypoint("agentic-workspace", "cli.py")


class _WorkspaceCliTestProxy:
    def __getattr__(self, name: str):
        if hasattr(_generated_cli, name):
            return getattr(_generated_cli, name)
        return getattr(workspace_runtime_primitives, name)

    def __setattr__(self, name: str, value: object) -> None:
        if hasattr(_generated_cli, name):
            setattr(_generated_cli, name, value)
            return
        setattr(workspace_runtime_primitives, name, value)

    def __delattr__(self, name: str) -> None:
        if hasattr(_generated_cli, name):
            delattr(_generated_cli, name)
            return
        delattr(workspace_runtime_primitives, name)


cli = _WorkspaceCliTestProxy()
REPO_LOCAL_CLI_INVOKE = "uv run python scripts/run_agentic_workspace.py"

_ORIGINAL_PATH_WRITE_TEXT = Path.write_text


def _path_write_text_with_parents(self: Path, data: str, *args, **kwargs):
    self.parent.mkdir(parents=True, exist_ok=True)
    return _ORIGINAL_PATH_WRITE_TEXT(self, data, *args, **kwargs)


Path.write_text = _path_write_text_with_parents


@dataclass
class FakeAction:
    kind: str
    path: Path
    detail: str


@dataclass
class FakeResult:
    target_root: Path
    message: str
    dry_run: bool
    actions: list[FakeAction] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class SlottedAction:
    kind: str
    path: Path
    detail: str


class DictAction:
    def __init__(self, path: Path) -> None:
        self.path = path

    def to_dict(self, target_root: Path) -> dict[str, object]:
        return {
            "kind": "converted",
            "path": self.path.relative_to(target_root),
            "detail": "used to_dict",
        }


def _assert_invoked_cli_identity(payload: dict[str, object], *, target_relation: str) -> dict[str, object]:
    identity = payload["invoked_cli_identity"]
    assert isinstance(identity, dict)
    assert identity["kind"] == "agentic-workspace/invoked-cli-identity/v1"
    assert identity["package"] == "agentic-workspace"
    assert identity["version"] == cli.__version__
    assert identity["source_class"] in {"source-checkout", "installed-package", "editable-dev", "unknown"}
    if "confidence" in identity:
        assert identity["confidence"] in {"high", "medium", "low"}
    assert str(identity["module_path"]).replace("\\", "/").endswith("generated/workspace/python/cli.py")
    if "python_executable" in identity:
        assert identity["python_executable"]
    assert identity["target_relation"] == target_relation
    assert identity["compatibility"] == "not-evaluated"
    return identity


def _assert_cli_compatibility(payload: dict[str, object], *, status: str) -> dict[str, object]:
    compatibility = payload["cli_compatibility"]
    assert isinstance(compatibility, dict)
    assert compatibility["kind"] == "agentic-workspace/cli-compatibility/v1"
    assert compatibility["status"] == status
    assert compatibility["enforcement"] in {"off", "advisory", "blocking"}
    assert "failed_checks" in compatibility
    return compatibility


def _assert_installed_state_compatibility(payload: dict[str, object], *, status: str) -> dict[str, object]:
    if payload.get("kind") == "agentic-workspace/selected-output/v1":
        values = payload.get("values")
        assert isinstance(values, dict)
        compatibility = values["installed_state_compatibility"]
    else:
        compatibility = payload["installed_state_compatibility"]
    assert isinstance(compatibility, dict)
    assert compatibility["kind"] == "agentic-workspace/installed-state-compatibility/v1"
    assert compatibility["status"] == status
    assert compatibility["authority"] == "repo-state-authoritative"
    assert compatibility["executable"]["classification"]
    assert compatibility["payload"]["status"]
    assert compatibility["generated_artifacts"]["status"]
    return compatibility


def _assert_cli_compatibility_schema(payload: dict[str, object], *, schema_name: str) -> None:
    schema_path = Path(__file__).resolve().parents[1] / "src" / "agentic_workspace" / "contracts" / "schemas" / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.evolve(schema=schema["$defs"]["cli_compatibility"]).iter_errors(payload["cli_compatibility"]),
        key=lambda error: list(error.path),
    )
    assert [error.message for error in errors] == []


def _assert_installed_state_compatibility_schema(payload: dict[str, object], *, schema_name: str) -> None:
    schema_path = Path(__file__).resolve().parents[1] / "src" / "agentic_workspace" / "contracts" / "schemas" / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.evolve(schema=schema["$defs"]["installed_state_compatibility"]).iter_errors(payload["installed_state_compatibility"]),
        key=lambda error: list(error.path),
    )
    assert [error.message for error in errors] == []


def _assert_sibling_repo_aw_freshness_schema(payload: dict[str, object], *, schema_name: str) -> None:
    schema_path = Path(__file__).resolve().parents[1] / "src" / "agentic_workspace" / "contracts" / "schemas" / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.evolve(schema=schema["$defs"]["sibling_repo_aw_freshness"]).iter_errors(payload["sibling_repo_aw_freshness"]),
        key=lambda error: list(error.path),
    )
    assert [error.message for error in errors] == []


def _fake_descriptors(target_root: Path, calls: list[tuple[str, str, dict[str, object]]]) -> dict[str, cli.ModuleDescriptor]:
    def _build_handler(module_name: str, command_name: str):
        def _handler(**kwargs):
            calls.append((module_name, command_name, kwargs))
            return FakeResult(
                target_root=target_root,
                message=f"{command_name} {module_name}",
                dry_run=bool(kwargs.get("dry_run", False)),
                actions=[FakeAction(kind="created", path=target_root / module_name, detail=f"ran {command_name}")],
                warnings=[],
            )

        return _handler

    commands = ("install", "adopt", "upgrade", "uninstall", "doctor", "status")
    return {
        module_name: cli.ModuleDescriptor(
            name=module_name,
            description=f"{module_name} module",
            commands={command_name: _build_handler(module_name, command_name) for command_name in commands},
            detector=lambda detected_root, module_name=module_name: (detected_root / module_name).exists(),
            selection_rank=10 if module_name == "planning" else 20,
            include_in_full_preset=True,
            install_signals=(
                (Path("TODO.md"), Path(".agentic-workspace/planning/execplans"), Path(".agentic-workspace/planning"))
                if module_name == "planning"
                else (Path(".agentic-workspace/memory/repo/index.md"), Path("memory/current"), Path(".agentic-workspace/memory"))
            ),
            workflow_surfaces=(
                (
                    Path("AGENTS.md"),
                    Path("TODO.md"),
                    Path(".agentic-workspace/planning/state.toml"),
                    Path(".agentic-workspace/planning/execplans"),
                    Path("docs/maintainer/contributor-playbook.md"),
                    Path(".agentic-workspace/planning"),
                )
                if module_name == "planning"
                else (
                    Path("AGENTS.md"),
                    Path(".agentic-workspace/memory/repo/index.md"),
                    Path("memory/current"),
                    Path(".agentic-workspace/memory"),
                )
            ),
            generated_artifacts=((Path(".agentic-workspace/planning/agent-manifest.json"),) if module_name == "planning" else ()),
            command_args={
                "install": ("target", "dry_run", "force"),
                "adopt": ("target", "dry_run"),
                "upgrade": ("target", "dry_run"),
                "uninstall": ("target", "dry_run"),
                "doctor": ("target",),
                "status": ("target",),
            },
            startup_steps=(),
            sources_of_truth=(),
            root_agents_cleanup_blocks=(
                (
                    cli.RootAgentsCleanupBlock(
                        block=cli.MEMORY_POINTER_BLOCK,
                        start_marker=cli.MEMORY_WORKFLOW_MARKER_START,
                        end_marker=cli.MEMORY_WORKFLOW_MARKER_END,
                        label="memory workflow pointer block",
                    ),
                )
                if module_name == "memory"
                else ()
            ),
            capabilities=(
                ("active-execution-state", "execplan-routing")
                if module_name == "planning"
                else ("durable-repo-knowledge", "anti-rediscovery-memory", "runbook-routing")
            ),
            dependencies=(),
            conflicts=(),
            result_contract=cli.ModuleResultContract(
                schema_version="workspace-module-report/v1",
                guaranteed_fields=("module", "message", "target_root", "dry_run", "actions", "warnings"),
                action_fields=("kind", "path", "detail"),
                warning_fields=("path", "message"),
            ),
        )
        for module_name in ("planning", "memory")
    }


def _descriptors_with_mixed_actions(target_root: Path) -> dict[str, cli.ModuleDescriptor]:
    def _upgrade_handler(**kwargs):
        return FakeResult(
            target_root=target_root,
            message="upgrade planning",
            dry_run=bool(kwargs.get("dry_run", False)),
            actions=[
                FakeAction(
                    kind="would update",
                    path=target_root / ".agentic-workspace" / "planning" / "agent-manifest.json",
                    detail="refresh planning manifest from managed payload",
                ),
                FakeAction(kind="skipped", path=target_root / "AGENTS.md", detail="repo-owned surface left unchanged"),
                FakeAction(kind="manual review", path=target_root / "README.md", detail="inspect manually"),
            ],
            warnings=[],
        )

    return {
        "planning": cli.ModuleDescriptor(
            name="planning",
            description="planning module",
            commands={
                "install": _upgrade_handler,
                "adopt": _upgrade_handler,
                "upgrade": _upgrade_handler,
                "uninstall": _upgrade_handler,
                "doctor": _upgrade_handler,
                "status": _upgrade_handler,
            },
            detector=lambda detected_root: True,
            selection_rank=10,
            include_in_full_preset=True,
            install_signals=(Path("TODO.md"), Path(".agentic-workspace/planning/execplans"), Path(".agentic-workspace/planning")),
            workflow_surfaces=(Path("AGENTS.md"), Path(".agentic-workspace/planning/agent-manifest.json")),
            generated_artifacts=(Path(".agentic-workspace/planning/agent-manifest.json"),),
            command_args={
                "install": ("target", "dry_run", "force"),
                "adopt": ("target", "dry_run"),
                "upgrade": ("target", "dry_run"),
                "uninstall": ("target", "dry_run"),
                "doctor": ("target",),
                "status": ("target",),
            },
            startup_steps=(),
            sources_of_truth=(),
            root_agents_cleanup_blocks=(),
            capabilities=("active-execution-state",),
            dependencies=(),
            conflicts=(),
            result_contract=cli.ModuleResultContract(
                schema_version="workspace-module-report/v1",
                guaranteed_fields=("module", "message", "target_root", "dry_run", "actions", "warnings"),
                action_fields=("kind", "path", "detail"),
                warning_fields=("path", "message"),
            ),
        )
    }


def _descriptors_with_install_signals(
    target_root: Path, calls: list[tuple[str, str, dict[str, object]]]
) -> dict[str, cli.ModuleDescriptor]:
    descriptors = _fake_descriptors(target_root, calls)
    return {
        "planning": cli.ModuleDescriptor(
            name="planning",
            description=descriptors["planning"].description,
            commands=descriptors["planning"].commands,
            detector=lambda detected_root: (
                (detected_root / "TODO.md").exists()
                and (detected_root / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
            ),
            selection_rank=descriptors["planning"].selection_rank,
            include_in_full_preset=descriptors["planning"].include_in_full_preset,
            install_signals=(Path("TODO.md"), Path(".agentic-workspace/planning/execplans"), Path(".agentic-workspace/planning")),
            workflow_surfaces=descriptors["planning"].workflow_surfaces,
            generated_artifacts=descriptors["planning"].generated_artifacts,
            command_args=descriptors["planning"].command_args,
            startup_steps=descriptors["planning"].startup_steps,
            sources_of_truth=descriptors["planning"].sources_of_truth,
            root_agents_cleanup_blocks=descriptors["planning"].root_agents_cleanup_blocks,
            capabilities=descriptors["planning"].capabilities,
            dependencies=descriptors["planning"].dependencies,
            conflicts=descriptors["planning"].conflicts,
            result_contract=descriptors["planning"].result_contract,
        ),
        "memory": cli.ModuleDescriptor(
            name="memory",
            description=descriptors["memory"].description,
            commands=descriptors["memory"].commands,
            detector=lambda detected_root: (
                (detected_root / "memory" / "index.md").exists() and (detected_root / ".agentic-workspace" / "memory").exists()
            ),
            selection_rank=descriptors["memory"].selection_rank,
            include_in_full_preset=descriptors["memory"].include_in_full_preset,
            install_signals=(Path(".agentic-workspace/memory/repo/index.md"), Path("memory/current"), Path(".agentic-workspace/memory")),
            workflow_surfaces=descriptors["memory"].workflow_surfaces,
            generated_artifacts=descriptors["memory"].generated_artifacts,
            command_args=descriptors["memory"].command_args,
            startup_steps=descriptors["memory"].startup_steps,
            sources_of_truth=descriptors["memory"].sources_of_truth,
            root_agents_cleanup_blocks=descriptors["memory"].root_agents_cleanup_blocks,
            capabilities=descriptors["memory"].capabilities,
            dependencies=descriptors["memory"].dependencies,
            conflicts=descriptors["memory"].conflicts,
            result_contract=descriptors["memory"].result_contract,
        ),
    }


def _init_git_repo(target: Path) -> None:
    (target / ".git").mkdir(exist_ok=True)


def _set_git_branch(target: Path, *, current: str, default: str) -> None:
    (target / ".git" / "HEAD").write_text(f"ref: refs/heads/{current}\n", encoding="utf-8")
    (target / ".git" / "refs" / "remotes" / "origin" / "HEAD").write_text(
        f"ref: refs/remotes/origin/{default}\n",
        encoding="utf-8",
    )


def _write(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    _write(path, json.dumps(payload, indent=2) + "\n")


def _json_payload_size(value: object, *, sort_keys: bool = True) -> int:
    return len(json.dumps(value, sort_keys=sort_keys).encode("utf-8"))


def _json_payload_contributors(value: object, *, sort_keys: bool = True, limit: int = 8) -> list[tuple[str, int]]:
    contributors: list[tuple[str, int]] = []

    def walk(current: object, path: str) -> None:
        if isinstance(current, dict):
            for key, child in current.items():
                child_path = f"{path}.{key}" if path else str(key)
                contributors.append((child_path, _json_payload_size(child, sort_keys=sort_keys)))
                walk(child, child_path)
        elif isinstance(current, list):
            for index, child in enumerate(current):
                child_path = f"{path}[{index}]"
                contributors.append((child_path, _json_payload_size(child, sort_keys=sort_keys)))
                walk(child, child_path)

    walk(value, "")
    return sorted(contributors, key=lambda item: item[1], reverse=True)[:limit]


def _assert_json_payload_under(value: object, max_bytes: int, *, label: str, sort_keys: bool = True) -> None:
    actual = _json_payload_size(value, sort_keys=sort_keys)
    if actual < max_bytes:
        return
    contributors = _json_payload_contributors(value, sort_keys=sort_keys)
    contribution_lines = "\n".join(f"  - {path}: {size} bytes" for path, size in contributors)
    raise AssertionError(
        f"{label} JSON payload is {actual} bytes; budget is < {max_bytes} bytes.\nLargest JSON contributors:\n{contribution_lines}"
    )


__all__ = [name for name in globals() if not name.startswith("__")]
