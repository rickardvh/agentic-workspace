from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Callable, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_SCRIPT_ROOT = REPO_ROOT / "scripts" / "generate"
if str(GENERATOR_SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(GENERATOR_SCRIPT_ROOT))
for SOURCE_ROOT in (
    REPO_ROOT / "src",
    REPO_ROOT / "internal" / "command-generation" / "src",
    REPO_ROOT / "packages" / "planning" / "src",
    REPO_ROOT / "packages" / "memory" / "src",
    REPO_ROOT / "packages" / "verification" / "src",
):
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))

from jsonschema import Draft202012Validator  # noqa: E402
from workspace_command_generation import (  # noqa: E402
    SCHEMA_PATH,
    SOURCE_PATH,
    load_workspace_command_package_ir,
    render_workspace_command_package_outputs,
)

from agentic_workspace.contract_tooling import (  # noqa: E402
    command_package_ir_manifest,
    load_contract_json,
    operation_manifest,
    python_runtime_projection_inventory_manifest,
)
from command_generation.generated_package_loader import (  # noqa: E402
    load_generated_command_module_for_entrypoint,
    load_generated_command_package_for_entrypoint,
)

SelectedFields = Callable[[str], dict[str, object]]


def _repo_relative(path: Path) -> str:
    return os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")


class AdapterConformanceCase(NamedTuple):
    conformance_ref: str
    label: str
    success_args: list[str]
    selected_fields: SelectedFields
    expected_fields: dict[str, object] | None
    fixture_id: str
    fixture_files: dict[str, str]
    expected_exit: int
    allow_stderr: bool


class RunnableTypescriptConformanceCase(NamedTuple):
    package_id: str
    program: str
    cli: Path
    weak_agent_routing: str
    case: AdapterConformanceCase


CONFORMANCE_PLACEHOLDER_BY_PACKAGE = {
    "root-workspace": "agentic_workspace_cli",
    "planning-bootstrap": "agentic_planning_cli",
    "memory-bootstrap": "agentic_memory_cli",
    "verification-cli": "agentic_verification_cli",
}
PYTHON_COMPLETION_STATES = {
    "adapter-layer-proven-not-full-generated-cli",
    "codegen-owned-primitive-migration-incomplete",
    "product-runtime-source-generation-incomplete",
    "full-generated-cli-complete",
}
PYTHON_COMPLETION_REQUIRED_EVIDENCE_IDS = {
    "parser-shape-generated",
    "dispatch-selection-generated",
    "interface-behavior-contract-backed",
    "future-interface-change-proof-gated",
    "python-black-box-conformance",
    "python-docker-conformance",
    "runtime-handlers-thin",
    "representative-operation-ir-runtime-consumed",
    "operation-execution-inventory-exhaustive",
    "root-console-generated-command-smoke",
    "product-specific-runtime-generated-output-owned",
}
PYTHON_COMPLETION_EXPECTED_PROOF_SUBSTRINGS = {
    "parser-shape-generated": "_validate_generated_python_commands_absent_from_handwritten_parsers",
    "dispatch-selection-generated": "generated_entrypoints order check",
    "interface-behavior-contract-backed": "check_generated_command_packages.py",
    "future-interface-change-proof-gated": "proof_selection_rules.json",
    "python-black-box-conformance": "--python-conformance",
    "python-docker-conformance": "--python-docker-conformance --require-docker",
    "runtime-handlers-thin": "_validate_python_runtime_handler_boundary",
    "representative-operation-ir-runtime-consumed": "_validate_python_operation_execution_inventory",
    "operation-execution-inventory-exhaustive": "_validate_python_operation_execution_inventory",
    "root-console-generated-command-smoke": (
        "test_workspace_cli_blackbox.py::test_blackbox_root_generated_command_executes_primitive_ir_through_console_script"
    ),
    "product-specific-runtime-generated-output-owned": "_validate_full_python_completion_executable_ownership",
}
PYTHON_OPERATION_EXECUTION_FINAL_STATUSES = {
    "portable-codegen-primitive-executed",
    "domain-runtime-primitive-via-ir",
    "accepted-hand-owned-runtime-primitive",
}
PYTHON_OPERATION_ACCEPTED_BOUNDARY_CLASSES = {
    "front-door-dispatch",
    "generic-deterministic-runtime-debt",
    "live-workspace-inspection",
    "mutation-orchestration",
    "package-specific-judgment",
    "provider-integration",
}
PYTHON_OPERATION_FULL_COMPLETION_BLOCKING_BOUNDARY_CLASSES = {"generic-deterministic-runtime-debt"}
PYTHON_OUTPUT_BOUNDARY_AUDIT_REQUIRED_PHRASES = (
    "generated-owned output coverage:",
    "accepted source fallback:",
    "not accepted as generic output",
)
REQUIRED_PORTABLE_PRIMITIVE_CONFORMANCE = {
    "path.target_root.resolve",
    "filesystem.read",
    "filesystem.glob",
    "json.parse",
    "payload.assemble",
    "payload.status",
    "payload.verify",
    "output.emit",
    "output.emit.install-result",
}
PYTHON_EXECUTABLE_DISPATCH_NAMES = {
    "run_generated_command": "generated runtime dispatch",
    "supports_generated_command": "generated runtime dispatch",
    "_GENERATED_RUNTIME_HANDLERS": "generated runtime dispatch",
    "runtime_main": "runtime fallback dispatch",
    "_run_generated_cli_package_if_supported": "runtime fallback dispatch",
    "run_operation_steps": "generic operation executor",
}
PYTHON_SHIPPED_MODULE_SOURCE_ROOTS = (
    "src/agentic_workspace/",
    "packages/planning/src/repo_planning_bootstrap/",
    "packages/memory/src/repo_memory_bootstrap/",
    "packages/verification/src/repo_verification_bootstrap/",
)
PYTHON_PRODUCT_RUNTIME_SOURCE_PATTERNS = (
    "workspace_runtime_cli.py",
    "planning_runtime_cli.py",
    "memory_runtime_cli.py",
    "verification_runtime_cli.py",
    "workspace_operation_ir_executor.py",
    "planning_operation_ir_executor.py",
    "memory_operation_ir_executor.py",
    "verification_operation_ir_executor.py",
)
PYTHON_FULL_COMPLETION_BLOCKING_EXECUTABLE_PATHS = (
    "src/agentic_workspace/_runtime_cli.py",
    "packages/planning/src/repo_planning_bootstrap/_runtime_cli.py",
    "packages/memory/src/repo_memory_bootstrap/_runtime_cli.py",
    "packages/verification/src/repo_verification_bootstrap/_runtime_cli.py",
    "src/agentic_workspace/generated_cli_package.py",
    "packages/planning/src/repo_planning_bootstrap/generated_cli_package.py",
    "packages/memory/src/repo_memory_bootstrap/generated_cli_package.py",
    "packages/verification/src/repo_verification_bootstrap/generated_cli_package.py",
    "src/agentic_workspace/operation_ir_executor.py",
    "packages/planning/src/repo_planning_bootstrap/operation_ir_executor.py",
    "packages/memory/src/repo_memory_bootstrap/operation_ir_executor.py",
    "packages/verification/src/repo_verification_bootstrap/operation_ir_executor.py",
)
PYTHON_FULL_COMPLETION_BLOCKING_RUNTIME_SOURCE_PATHS = (
    "src/agentic_workspace/workspace_runtime_primitives.py",
    "packages/planning/src/repo_planning_bootstrap/installer.py",
    "packages/planning/src/repo_planning_bootstrap/runtime_projection.py",
    "packages/memory/src/repo_memory_bootstrap/installer.py",
    "packages/memory/src/repo_memory_bootstrap/runtime_search.py",
    "packages/memory/src/repo_memory_bootstrap/runtime_primitives.py",
    "packages/verification/src/repo_verification_bootstrap/runtime_primitives.py",
)
PYTHON_FULL_COMPLETION_ACCEPTED_RUNTIME_FACADE_PATHS = (
    "generated/workspace/python/primitives/workspace_runtime.py",
    "generated/planning/python/primitives/planning_installer.py",
    "generated/planning/python/primitives/planning_runtime.py",
    "generated/memory/python/primitives/memory_runtime.py",
)
PYTHON_ACCEPTED_RUNTIME_BOUNDARY_PERMANENCE_STATUS = "accepted-permanent-package-domain-boundary"
GENERATED_CLI_COMPATIBILITY_VOCABULARY = (
    "generated_cli_package",
    "load_generated_cli_",
    "build_generated_cli_package_parser",
    "generated_cli_package_command_names",
)
GENERATED_CLI_COMPATIBILITY_VOCABULARY_ALLOWLIST = {
    "pyproject.toml": "installed private bridge compatibility",
    "packages/planning/pyproject.toml": "installed private bridge compatibility",
    "packages/memory/pyproject.toml": "installed private bridge compatibility",
    "packages/verification/pyproject.toml": "installed private bridge compatibility",
    "packages/planning/payload-surface-classification.json": "installed private bridge compatibility inventory",
    ".agentic-workspace/planning/decompositions/python-generated-cli.decomposition.json": (
        "historical generated target-layout migration context"
    ),
    "internal/command-generation/src/command_generation/generated_package_loader.py": "legacy loader compatibility wrappers and legacy layout fallback",
    "src/agentic_workspace/cli.py": "source-checkout fallback to checked-in generated workspace CLI package",
    "packages/planning/src/repo_planning_bootstrap/cli.py": "source-checkout fallback to checked-in generated planning CLI package",
    "packages/memory/src/repo_memory_bootstrap/cli.py": "source-checkout fallback to checked-in generated memory CLI package",
    "packages/verification/src/repo_verification_bootstrap/cli.py": "source-checkout fallback to checked-in generated verification CLI package",
    "src/agentic_workspace/workspace_runtime_primitives.py": "legacy parser helper compatibility wrapper",
    "scripts/check/check_generated_command_packages.py": "static compatibility allowlist and obsolete-layout guards",
    "tests/test_command_generation_artifacts.py": "obsolete target-specific runtime guard",
    "tests/test_contract_tooling.py": "legacy-layout fixture and obsolete source guard",
    "tests/test_workspace_packaging.py": "installed private bridge compatibility proof",
    "packages/planning/tests/test_packaging.py": "installed private bridge compatibility proof",
    "packages/memory/tests/test_packaging.py": "installed private bridge compatibility proof",
    "packages/planning/hatch_build.py": "sdist wheel rebuild bridge to embedded generated package payload",
    "packages/memory/hatch_build.py": "sdist wheel rebuild bridge to embedded generated package payload",
}
GENERATED_CLI_COMPATIBILITY_VOCABULARY_ALLOWLIST_PREFIXES = {
    ".agentic-workspace/planning/execplans/archive/": "historical planning evidence",
    "docs/reviews/": "historical review evidence",
}
COMMAND_GENERATION_SOURCE_ROOT = "internal/command-generation/src/command_generation"
COMMAND_GENERATION_FORBIDDEN_PRODUCT_IMPORT_ROOTS = (
    "agentic_workspace",
    "repo_planning_bootstrap",
    "repo_memory_bootstrap",
    "repo_verification_bootstrap",
)
COMMAND_GENERATION_PRODUCT_LITERAL_TOKENS = (
    "agentic-workspace",
    "agentic-planning",
    "agentic-memory",
    "agentic-verification",
    ".agentic-workspace",
    "workspace.",
    "planning.",
    "memory.",
    "verification.",
)
DOMAIN_RUNTIME_PRIMITIVE_SOURCE_CALLS = {
    "memory.promotion_report.load": {
        "import_module": "repo_memory_bootstrap.installer",
        "function": "promotion_report",
    }
}
PYTHON_REQUIRED_RUNTIME_PROJECTION_OUTPUTS = {
    "generated/workspace/python/cli.py": (
        "root-workspace",
        "agentic-workspace",
        "cli-entrypoint",
    ),
    "generated/workspace/python/primitives/operation_executor.py": (
        "root-workspace",
        "agentic-workspace",
        "operation-ir-executor",
    ),
    "generated/planning/python/cli.py": (
        "planning-bootstrap",
        "agentic-planning",
        "cli-entrypoint",
    ),
    "generated/planning/python/primitives/operation_executor.py": (
        "planning-bootstrap",
        "agentic-planning",
        "operation-ir-executor",
    ),
    "generated/memory/python/cli.py": (
        "memory-bootstrap",
        "agentic-memory",
        "cli-entrypoint",
    ),
    "generated/memory/python/primitives/operation_executor.py": (
        "memory-bootstrap",
        "agentic-memory",
        "operation-ir-executor",
    ),
    "generated/verification/python/cli.py": (
        "verification-cli",
        "agentic-verification",
        "cli-entrypoint",
    ),
    "generated/verification/python/primitives/operation_executor.py": (
        "verification-cli",
        "agentic-verification",
        "operation-ir-executor",
    ),
}
RECOVERED_CONFORMANCE_RETRIES: list[dict[str, object]] = []


def _run(command: list[str]) -> int:
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return int(completed.returncode)


def _tail_text(text: str | None, *, max_lines: int = 20) -> str:
    if not text:
        return "<empty>"
    lines = text.splitlines()
    tail = lines[-max_lines:]
    return "\\n".join(tail) if tail else "<empty>"


def _docker_output_contains_adapter_failure(output: str) -> bool:
    adapter_markers = (
        "classification=adapter-contract-failure",
        "generated python adapter failure:",
        "generated typescript adapter failure:",
        "adapter failure:",
        "selected fields drifted",
        "exit code drifted",
        "unexpected stderr",
    )
    return any(marker in output for marker in adapter_markers)


def _docker_failure_guidance(output: str) -> str:
    lowered = output.lower()
    transient_markers = (
        "file has already been closed",
        "dockerdesktoplinuxengine",
        "attempting to create pycfunction",
        "systemerror",
        "segmentation fault",
        "signal 11",
        "exit code 139",
        "connection reset by peer",
    )
    if any(marker in lowered for marker in transient_markers):
        return "retry the Docker proof and inspect host/container runtime health before treating this as deterministic generated-code drift"
    return "inspect Docker setup/build/runtime output before treating this as adapter contract drift"


def _format_docker_proof_environment_failure(
    *,
    proof_label: str,
    phase: str,
    tag: str,
    dockerfile: str,
    command: list[str],
    returncode: int,
    stdout: str | None,
    stderr: str | None,
) -> str:
    output = "\n".join(part for part in (stdout or "", stderr or "") if part)
    return (
        "generated Docker conformance failure: "
        "classification=proof-environment/setup-failure; "
        f"proof_surface={proof_label}; phase={phase}; image={tag}; dockerfile={dockerfile}; "
        f"command={command!r}; exit={returncode}; guidance={_docker_failure_guidance(output)}; "
        f"stdout_tail={_tail_text(stdout)!r}; stderr_tail={_tail_text(stderr)!r}"
    )


def _run_docker_step(command: list[str], *, proof_label: str, phase: str, tag: str, dockerfile: str) -> int:
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False, text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    returncode = int(completed.returncode)
    if returncode:
        combined_output = "\n".join(part for part in (completed.stdout or "", completed.stderr or "") if part)
        if phase != "docker-run" or not _docker_output_contains_adapter_failure(combined_output):
            print(
                _format_docker_proof_environment_failure(
                    proof_label=proof_label,
                    phase=phase,
                    tag=tag,
                    dockerfile=dockerfile,
                    command=command,
                    returncode=returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                )
            )
    return returncode


def _python_executable() -> str:
    return sys.executable or "python"


def _conformance_env(*, runtime: str | None = None) -> dict[str, str]:
    env = os.environ.copy()
    paths = [
        str(REPO_ROOT / "src"),
        str(REPO_ROOT / "packages" / "planning" / "src"),
        str(REPO_ROOT / "packages" / "memory" / "src"),
        str(REPO_ROOT / "packages" / "verification" / "src"),
        str(REPO_ROOT / "internal" / "command-generation" / "src"),
    ]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    env["COLUMNS"] = "80"
    env["LINES"] = "24"
    if runtime is not None:
        env["AGENTIC_WORKSPACE_RUNTIME"] = runtime
    return env


def _entrypoint_for_package(package_id: str) -> str:
    entrypoints = {
        "root-workspace": "agentic-workspace",
        "planning-bootstrap": "agentic-planning",
        "memory-bootstrap": "agentic-memory",
        "verification-cli": "agentic-verification",
    }
    return entrypoints[package_id]


def _runtime_module_file_for_package(package_id: str) -> str:
    return "cli.py"


def _generated_package_for_package(package_id: str):
    return load_generated_command_package_for_entrypoint(_entrypoint_for_package(package_id))


def _generated_runtime_module_for_package(package_id: str):
    return load_generated_command_module_for_entrypoint(_entrypoint_for_package(package_id), _runtime_module_file_for_package(package_id))


def _python_command_for_package(package_id: str) -> list[str]:
    module_by_package = {
        "root-workspace": "agentic_workspace.cli",
        "planning-bootstrap": "repo_planning_bootstrap.cli",
        "memory-bootstrap": "repo_memory_bootstrap.cli",
        "verification-cli": "repo_verification_bootstrap.cli",
    }
    module = module_by_package[package_id]
    return [
        _python_executable(),
        "-c",
        (
            f"import sys; from {module} import main; "
            "raise SystemExit(main(sys.argv[1:]))"
        ),
    ]


def _capture(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def _generated_adapter_proof_surface(*, language: str) -> str:
    container = os.environ.get("AGENTIC_GENERATED_CONFORMANCE_CONTAINER")
    if container:
        return f"generated-{container}-docker-conformance"
    return f"generated-{language}-adapter-conformance"


def _exit_failure_classification(returncode: int) -> tuple[str, str]:
    if returncode < 0:
        signal_number = abs(returncode)
        return (
            "runtime-crash-or-proof-environment-residue",
            f"native process terminated by signal {signal_number}",
        )
    if returncode > 128:
        return (
            "runtime-crash-or-proof-environment-residue",
            f"process exit may encode signal {returncode - 128}",
        )
    return ("adapter-contract-failure", "process exited without the expected contract status")


def _is_runtime_crash_exit(returncode: int) -> bool:
    classification, _detail = _exit_failure_classification(returncode)
    return classification == "runtime-crash-or-proof-environment-residue"


def _format_generated_adapter_exit_failure(
    *,
    language: str,
    package_id: str,
    case: AdapterConformanceCase,
    command: list[str],
    returncode: int,
    expected_exit: int,
    stderr: str,
) -> str:
    classification, detail = _exit_failure_classification(returncode)
    command_name = case.success_args[0] if case.success_args else "<entrypoint>"
    rerun_guidance = (
        "rerun this package/case or the Docker conformance proof before treating it as deterministic"
        if classification == "runtime-crash-or-proof-environment-residue"
        else "compare adapter output with the contract-backed runtime expectation"
    )
    return (
        f"generated {language} adapter failure: classification={classification}; "
        f"proof_surface={_generated_adapter_proof_surface(language=language)}; package={package_id}; "
        f"conformance_ref={case.conformance_ref}; command={command_name}; command_args={case.success_args!r}; "
        f"fixture={case.fixture_id}; adapter_entrypoint={command[0]!r}; exit={returncode}; "
        f"expected={expected_exit}; detail={detail}; guidance={rerun_guidance}; stderr={stderr!r}"
    )


def _format_generated_adapter_retry_recovery(
    *,
    language: str,
    package_id: str,
    case: AdapterConformanceCase,
    command: list[str],
    first_returncode: int,
) -> str:
    _classification, detail = _exit_failure_classification(first_returncode)
    command_name = case.success_args[0] if case.success_args else "<entrypoint>"
    record = {
        "kind": "generated-adapter-retry-recovery/v1",
        "status": "recovered",
        "classification": "runtime-crash-or-proof-environment-residue",
        "proof_surface": _generated_adapter_proof_surface(language=language),
        "package": package_id,
        "conformance_ref": case.conformance_ref,
        "command": command_name,
        "command_args": case.success_args,
        "fixture": case.fixture_id,
        "adapter_entrypoint": command[0],
        "first_exit": first_returncode,
        "detail": detail,
        "strict_fail": _strict_retry_recovery_enabled(),
    }
    RECOVERED_CONFORMANCE_RETRIES.append(record)
    return (
        f"[warn] generated {language} adapter runtime crash recovered after retry: "
        f"proof_surface={_generated_adapter_proof_surface(language=language)}; package={package_id}; "
        f"conformance_ref={case.conformance_ref}; command={command_name}; command_args={case.success_args!r}; "
        f"fixture={case.fixture_id}; adapter_entrypoint={command[0]!r}; first_exit={first_returncode}; detail={detail}; "
        f"recovery_record={json.dumps(record, sort_keys=True)}"
    )


def _strict_retry_recovery_enabled() -> bool:
    value = os.environ.get("AGENTIC_GENERATED_STRICT_RETRY_RECOVERY", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_json(relative_path: str) -> dict[str, object]:
    return (
        operation_manifest(relative_path)
        if relative_path.startswith("operations/")
        else load_contract_json(relative_path)
    )


def _load_generated_operation_json(generated_root: Path, relative_path: str) -> dict[str, object]:
    generated_path = generated_root / relative_path
    if generated_path.is_file():
        return json.loads(generated_path.read_text(encoding="utf-8"))
    return _load_json(relative_path)


def _interface_operation_refs(interface: dict[str, object], inherited_operation_ref: dict[str, object]) -> list[dict[str, object]]:
    operation_ref = interface.get("operation_ref", inherited_operation_ref)
    current_operation_ref = operation_ref if isinstance(operation_ref, dict) else inherited_operation_ref
    refs = [current_operation_ref]
    subcommands = interface.get("subcommands", [])
    if isinstance(subcommands, list):
        for subcommand in subcommands:
            if isinstance(subcommand, dict):
                refs.extend(_interface_operation_refs(subcommand, current_operation_ref))
    return refs


def _command_operation_refs(command: dict[str, object]) -> list[dict[str, object]]:
    operation_ref = command.get("operation_ref", {})
    interface = command.get("interface", {})
    if not isinstance(operation_ref, dict):
        return []
    if not isinstance(interface, dict):
        return [operation_ref]
    return _interface_operation_refs(interface, operation_ref)


def _command_conformance_ref_for_operation(command: dict[str, object], operation_id: str) -> object:
    refs = command.get("conformance_refs") or []
    if not isinstance(refs, list):
        return None
    exact = f"{operation_id}.process"
    if exact in refs:
        return exact
    prefix = f"{operation_id}."
    for ref in refs:
        if isinstance(ref, str) and ref.startswith(prefix):
            return ref
    return refs[0] if refs else None


def _operation_input_is_command_visible(input_record: dict[str, object]) -> bool:
    if input_record.get("source") != "cli-option":
        return False
    if input_record.get("command_visible") is False:
        return False
    visibility = input_record.get("command_visibility") or input_record.get("cli_visibility")
    return str(visibility or "").strip() not in {"runtime-only", "non-command-visible"}


def _interface_parameter_names(interface: dict[str, object]) -> set[str]:
    names: set[str] = set()
    for key in ("arguments", "options"):
        raw_items = interface.get(key, [])
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if name:
                names.add(name)
    return names


def _operation_input_matches_interface(input_name: str, parameter_names: set[str]) -> bool:
    if input_name in parameter_names:
        return True
    if input_name.endswith("y") and f"{input_name[:-1]}ies" in parameter_names:
        return True
    return f"{input_name}s" in parameter_names


def _validate_operation_cli_inputs_for_interface(
    *,
    package_id: str,
    command_path: str,
    interface: dict[str, object],
    inherited_operation_ref: dict[str, object],
    inherited_option_names: set[str],
    generated_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    option_names = set(inherited_option_names) | _interface_parameter_names(interface)
    operation_ref = interface.get("operation_ref", inherited_operation_ref)
    current_operation_ref = operation_ref if isinstance(operation_ref, dict) else inherited_operation_ref
    operation_id = str(current_operation_ref.get("id", "")).strip()
    operation_path = str(current_operation_ref.get("path", "")).strip()
    subcommands = interface.get("subcommands", [])
    has_subcommands = isinstance(subcommands, list) and any(isinstance(subcommand, dict) for subcommand in subcommands)
    if operation_id and operation_path and (option_names or not has_subcommands):
        try:
            operation = (
                _load_generated_operation_json(generated_root, operation_path) if generated_root is not None else _load_json(operation_path)
            )
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{package_id} {command_path} operation {operation_id} cannot be loaded for CLI input proof: {exc}")
        else:
            inputs = operation.get("inputs", [])
            if isinstance(inputs, list):
                for input_record in inputs:
                    if not isinstance(input_record, dict) or not _operation_input_is_command_visible(input_record):
                        continue
                    input_name = str(input_record.get("name", "")).strip()
                    if input_name and not _operation_input_matches_interface(input_name, option_names):
                        errors.append(
                            f"{package_id} {command_path} operation {operation_id} declares cli-option input "
                            f"{input_name!r} but generated command options are {sorted(option_names)!r}; "
                            "add the option to the command interface or mark the input command_visibility='runtime-only' "
                            "or command_visibility='non-command-visible'"
                        )
    if isinstance(subcommands, list):
        for subcommand in subcommands:
            if not isinstance(subcommand, dict):
                continue
            subcommand_name = str(subcommand.get("name", "")).strip() or "<unnamed>"
            errors.extend(
                _validate_operation_cli_inputs_for_interface(
                    package_id=package_id,
                    command_path=f"{command_path} {subcommand_name}",
                    interface=subcommand,
                    inherited_operation_ref=current_operation_ref,
                    inherited_option_names=option_names,
                    generated_root=generated_root,
                )
            )
    return errors


def _validate_generated_operation_cli_inputs(ir: dict[str, object]) -> list[str]:
    errors: list[str] = []
    for package in ir.get("packages", []):
        if not isinstance(package, dict):
            continue
        package_id = str(package.get("id", "")).strip() or "<unknown-package>"
        python_targets = [
            target
            for target in package.get("targets", [])
            if isinstance(target, dict) and target.get("kind") == "python" and target.get("generated_root")
        ]
        for target in python_targets:
            generated_root = REPO_ROOT / str(target.get("generated_root"))
            try:
                command_package = json.loads((generated_root / "command_package.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{package_id} generated Python command package cannot be loaded for CLI input proof: {exc}")
                continue
            for command in command_package.get("commands", []):
                if not isinstance(command, dict) or command.get("status") != "generated":
                    continue
                interface = command.get("interface", {})
                operation_ref = command.get("operation_ref", {})
                if not isinstance(interface, dict) or not isinstance(operation_ref, dict):
                    continue
                raw_command = command.get("command", {})
                command_name = str(
                    interface.get("name") or (raw_command.get("name") if isinstance(raw_command, dict) else "") or "<unnamed>"
                ).strip()
                errors.extend(
                    _validate_operation_cli_inputs_for_interface(
                        package_id=package_id,
                        command_path=command_name,
                        interface=interface,
                        inherited_operation_ref=operation_ref,
                        inherited_option_names=set(),
                        generated_root=generated_root,
                    )
                )
    return errors


def _field_value(payload: object, path: list[str]) -> object:
    current = payload
    for part in path:
        if not isinstance(current, dict) or part not in current:
            raise KeyError(".".join(path))
        current = current[part]
    return current


def _selected_contract_fields(stdout: str, assertions: list[dict[str, object]]) -> dict[str, object]:
    if not assertions:
        return {}
    payload = json.loads(stdout)
    selected: dict[str, object] = {}
    for assertion in assertions:
        path = assertion.get("path", [])
        if not isinstance(path, list) or not all(isinstance(part, str) for part in path):
            raise ValueError(f"conformance assertion path is malformed: {path!r}")
        selected[".".join(path)] = _field_value(payload, path)
    return selected


def _expected_contract_fields(assertions: list[dict[str, object]]) -> dict[str, object]:
    expected: dict[str, object] = {}
    for assertion in assertions:
        path = assertion.get("path", [])
        if not isinstance(path, list) or not all(isinstance(part, str) for part in path):
            raise ValueError(f"conformance assertion path is malformed: {path!r}")
        expected[".".join(path)] = assertion.get("equals")
    return expected


def _success_args_from_contract(*, contract: dict[str, object], package_id: str) -> list[str]:
    adapter = contract.get("adapter", {})
    if not isinstance(adapter, dict):
        raise ValueError(f"conformance contract {contract.get('id')!r} has malformed adapter")
    template = adapter.get("command_template", [])
    if not isinstance(template, list) or not all(isinstance(token, str) for token in template):
        raise ValueError(f"conformance contract {contract.get('id')!r} has malformed command_template")
    expected_placeholder = "{" + CONFORMANCE_PLACEHOLDER_BY_PACKAGE[package_id] + "}"
    if not template or template[0] != expected_placeholder:
        raise ValueError(
            f"conformance contract {contract.get('id')!r} starts with {template[0] if template else None!r}, "
            f"expected {expected_placeholder!r} for package {package_id!r}"
        )
    return template[1:]


def _fixture_from_contract(contract: dict[str, object]) -> tuple[str, dict[str, str]]:
    fixtures = contract.get("fixtures", [])
    if not isinstance(fixtures, list) or not fixtures or not isinstance(fixtures[0], dict):
        raise ValueError(f"conformance contract {contract.get('id')!r} has no usable fixture")
    fixture = fixtures[0]
    fixture_id = fixture.get("id")
    files = fixture.get("files")
    if not isinstance(fixture_id, str) or not isinstance(files, dict) or not all(isinstance(key, str) for key in files):
        raise ValueError(f"conformance contract {contract.get('id')!r} fixture is malformed")
    return fixture_id, {path: str(contents) for path, contents in files.items()}


def _expected_exit_from_contract(contract: dict[str, object]) -> int:
    expectations = contract.get("expectations", {})
    exit_expectation = expectations.get("exit", {}) if isinstance(expectations, dict) else {}
    code = exit_expectation.get("code", 0) if isinstance(exit_expectation, dict) else 0
    return int(code) if isinstance(code, int) else 0


def _allow_stderr_from_contract(contract: dict[str, object]) -> bool:
    expectations = contract.get("expectations", {})
    stderr = expectations.get("stderr", {}) if isinstance(expectations, dict) else {}
    allow_non_empty = stderr.get("allow_non_empty", False) if isinstance(stderr, dict) else False
    return bool(allow_non_empty)


def _case_from_conformance_contract(*, contract: dict[str, object], package_id: str) -> AdapterConformanceCase:
    expectations = contract.get("expectations", {})
    stdout = expectations.get("stdout", {}) if isinstance(expectations, dict) else {}
    assertions = stdout.get("field_assertions", []) if isinstance(stdout, dict) else []
    if not isinstance(assertions, list) or not all(isinstance(assertion, dict) for assertion in assertions):
        raise ValueError(f"conformance contract {contract.get('id')!r} has malformed field_assertions")
    fixture_id, fixture_files = _fixture_from_contract(contract)
    contract_id = str(contract.get("id", ""))
    return AdapterConformanceCase(
        conformance_ref=contract_id,
        label=contract_id.removesuffix(".process").replace(".", " "),
        success_args=_success_args_from_contract(contract=contract, package_id=package_id),
        selected_fields=lambda stdout_text, contract_assertions=assertions: _selected_contract_fields(
            stdout_text,
            contract_assertions,
        ),
        expected_fields=_expected_contract_fields(assertions),
        fixture_id=fixture_id,
        fixture_files=fixture_files,
        expected_exit=_expected_exit_from_contract(contract),
        allow_stderr=_allow_stderr_from_contract(contract),
    )


def _adapter_conformance_cases_by_package() -> tuple[dict[str, dict[str, AdapterConformanceCase]], list[str]]:
    registry = _load_json("conformance_contracts.json")
    contracts_by_id: dict[str, dict[str, object]] = {}
    errors: list[str] = []
    for entry in registry.get("contracts", []):
        if not isinstance(entry, dict):
            continue
        contract_id = str(entry.get("id", ""))
        path = entry.get("path")
        if not isinstance(path, str):
            errors.append(f"conformance registry entry {contract_id!r} is missing path")
            continue
        contracts_by_id[contract_id] = _load_json(path)

    ir = _load_json("command_package_ir.json")
    cases_by_package: dict[str, dict[str, AdapterConformanceCase]] = {}
    for package in ir.get("packages", []):
        if not isinstance(package, dict):
            continue
        package_id = str(package.get("id", ""))
        if package_id not in CONFORMANCE_PLACEHOLDER_BY_PACKAGE:
            continue
        package_cases: dict[str, AdapterConformanceCase] = {}
        for command in package.get("commands", []):
            if not isinstance(command, dict):
                continue
            for conformance_ref in command.get("conformance_refs", []):
                contract = contracts_by_id.get(str(conformance_ref))
                if contract is None:
                    errors.append(f"conformance ref {conformance_ref!r} is not registered")
                    continue
                try:
                    package_cases[str(conformance_ref)] = _case_from_conformance_contract(
                        contract=contract,
                        package_id=package_id,
                    )
                except ValueError as exc:
                    errors.append(str(exc))
        cases_by_package[package_id] = package_cases
    return cases_by_package, errors


def _run_python_adapter_conformance() -> list[str]:
    RECOVERED_CONFORMANCE_RETRIES.clear()
    registries, registry_errors = _adapter_conformance_cases_by_package()
    if registry_errors:
        return registry_errors
    errors: list[str] = []
    env = _conformance_env()
    with tempfile.TemporaryDirectory(prefix="agentic-workspace-generated-python-adapter-") as tmp:
        temp_root = Path(tmp)
        shims: dict[str, Path] = {}

        def command_for_package(package_id: str) -> list[str]:
            shim = shims.get(package_id)
            if shim is None:
                module_by_package = {
                    "root-workspace": "agentic_workspace.cli",
                    "planning-bootstrap": "repo_planning_bootstrap.cli",
                    "memory-bootstrap": "repo_memory_bootstrap.cli",
                    "verification-cli": "repo_verification_bootstrap.cli",
                }
                shim = temp_root / f"{package_id.replace('-', '_')}_cli_shim.py"
                shim.write_text(
                    "import sys\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'planning' / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'memory' / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'verification' / 'src')!r})\n"
                    f"from {module_by_package[package_id]} import main\n"
                    "raise SystemExit(main(sys.argv[1:]))\n",
                    encoding="utf-8",
                )
                shims[package_id] = shim
            return [_python_executable(), str(shim)]

        for package_id, registry in registries.items():
            command = command_for_package(package_id)
            for case in registry.values():
                fixture_root = temp_root / package_id / case.fixture_id / case.conformance_ref.replace(".", "-")
                if fixture_root.exists():
                    shutil.rmtree(fixture_root)
                for relative_path, contents in case.fixture_files.items():
                    path = fixture_root / relative_path
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(contents, encoding="utf-8")
                process = _capture([*command, *case.success_args], cwd=fixture_root, env=env)
                if process.returncode != case.expected_exit:
                    if _is_runtime_crash_exit(process.returncode):
                        retry_process = _capture([*command, *case.success_args], cwd=fixture_root, env=env)
                        if retry_process.returncode == case.expected_exit:
                            recovery_message = _format_generated_adapter_retry_recovery(
                                language="python",
                                package_id=package_id,
                                case=case,
                                command=command,
                                first_returncode=process.returncode,
                            )
                            print(recovery_message)
                            if _strict_retry_recovery_enabled():
                                errors.append(recovery_message)
                                continue
                            process = retry_process
                        else:
                            errors.append(
                                _format_generated_adapter_exit_failure(
                                    language="python",
                                    package_id=package_id,
                                    case=case,
                                    command=command,
                                    returncode=process.returncode,
                                    expected_exit=case.expected_exit,
                                    stderr=process.stderr,
                                )
                                + f"; retry_exit={retry_process.returncode}; retry_stderr={retry_process.stderr!r}"
                            )
                            continue
                    if process.returncode != case.expected_exit:
                        errors.append(
                            _format_generated_adapter_exit_failure(
                                language="python",
                                package_id=package_id,
                                case=case,
                                command=command,
                                returncode=process.returncode,
                                expected_exit=case.expected_exit,
                                stderr=process.stderr,
                            )
                        )
                        continue
                if process.stderr.strip() and not case.allow_stderr:
                    errors.append(
                        f"generated Python adapter failure: {package_id} {case.label} emitted unexpected stderr: {process.stderr!r}"
                    )
                    continue
                if case.expected_fields is None:
                    continue
                try:
                    selected = case.selected_fields(process.stdout)
                except (KeyError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(
                        f"generated Python adapter failure: {package_id} {case.label} stdout did not satisfy selected fields: {exc}; "
                        f"stdout={process.stdout!r}"
                    )
                    continue
                if selected != case.expected_fields:
                    errors.append(
                        f"generated Python adapter failure: {package_id} {case.label} output shape drifted; "
                        f"expected selected fields {case.expected_fields!r}, got {selected!r}"
                    )
    return errors


def _runnable_typescript_conformance_cases() -> tuple[list[RunnableTypescriptConformanceCase], list[str]]:
    try:
        ir = load_workspace_command_package_ir(repo_root=REPO_ROOT)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [], [f"adapter conformance failed before execution: command-package IR validation failed: {exc}"]
    maturity_levels = {
        str(level["id"]): level
        for level in ir.get("generation_policy", {}).get("generated_package_maturity", {}).get("levels", [])
        if isinstance(level, dict) and "id" in level
    }

    registries, registry_errors = _adapter_conformance_cases_by_package()
    if registry_errors:
        return [], registry_errors
    selected: list[RunnableTypescriptConformanceCase] = []
    errors: list[str] = []
    for package in ir.get("packages", []):
        if not isinstance(package, dict):
            continue
        package_id = str(package.get("id", ""))
        registry = registries.get(package_id, {})
        runnable_typescript_targets = [
            target
            for target in package.get("targets", [])
            if isinstance(target, dict)
            and target.get("kind") == "typescript"
            and target.get("maturity_level_ref") in {"runnable-read-only-adapter", "weak-agent-safe-adapter", "mutation-capable-adapter"}
        ]
        if not runnable_typescript_targets:
            continue
        if not registry:
            errors.append(f"adapter conformance cannot run TypeScript package {package_id!r}; no conformance registry is defined")
            continue
        target = runnable_typescript_targets[0]
        cli = REPO_ROOT / str(target.get("generated_root", "")) / "src" / "cli.mjs"
        for command in package.get("commands", []):
            if not isinstance(command, dict):
                continue
            command_name = command.get("command", {}).get("name") if isinstance(command.get("command"), dict) else "<unknown>"
            for conformance_ref in command.get("conformance_refs", []):
                case = registry.get(str(conformance_ref))
                if case is None:
                    errors.append(
                        f"missing generated TypeScript conformance case for {package_id!r} command {command_name!r} ref {conformance_ref!r}"
                    )
                    continue
                selected.append(
                    RunnableTypescriptConformanceCase(
                        package_id=package_id,
                        program=str(package.get("program", "")),
                        cli=cli,
                        weak_agent_routing=str(maturity_levels[str(target.get("maturity_level_ref"))]["weak_agent_routing"]),
                        case=case,
                    )
                )
    return selected, errors


def _validate_typescript_runtime_handoff_thinness(*, package: str, cli_text: str, runtime_text: str) -> list[str]:
    errors: list[str] = []
    expected_imports = {"import { writeSync } from 'node:fs';", "import { runGeneratedOperation } from './runtime.mjs';"}
    import_lines = {line.strip() for line in cli_text.splitlines() if line.startswith("import ")}
    unexpected_imports = sorted(import_lines - expected_imports)
    if unexpected_imports:
        errors.append(f"{package}/src/cli.mjs imports non-native runtime modules: {unexpected_imports!r}")
    required_fragments = [
        "const nativeOperationIds = new Set(",
        "function runNativeOperation(operationId, operationPath, values)",
        "runGeneratedOperation({ operationId, operationPath, values })",
        "maybeRunNativeOperation();",
        "TypeScript CLI boundary: generated parser, validation, and command execution are Node/TypeScript only.",
    ]
    for fragment in required_fragments:
        if fragment not in cli_text:
            errors.append(f"{package}/src/cli.mjs is missing native TypeScript runtime fragment: {fragment}")
    forbidden_fragments = [
        "AGENTIC_WORKSPACE_RUNTIME",
        "Adapter runtime handoff failed",
        "canonical Python CLI",
        "node:child_process",
        "spawnSync",
        "shell: true",
        "nativeContractCases",
        "genericNativePayload",
        "frontDoorPayload",
        "contractProjection",
        "contract-projection",
        "fieldAssertions",
        "selectedFields",
        "expectedFields",
    ]
    for source_label, source_text in (("src/cli.mjs", cli_text), ("src/runtime.mjs", runtime_text)):
        for fragment in forbidden_fragments:
            if fragment in source_text:
                errors.append(f"{package}/{source_label} contains Python/runtime-handoff marker: {fragment}")
    runtime_required_fragments = [
        "export function runGeneratedOperation({ operationId, operationPath, values })",
        "function runSteps(operation, values)",
        "function executePrimitive(primitive, values, args, operationId)",
        "function executeTypescriptDomainOperation(operationId, values)",
        "typescript.domain.execute",
        "unsupported native TypeScript primitive",
    ]
    for fragment in runtime_required_fragments:
        if fragment not in runtime_text:
            errors.append(f"{package}/src/runtime.mjs is missing native operation executor fragment: {fragment}")
    return errors


TYPESCRIPT_SUPPORTED_EXACT_PRIMITIVES = {
    "typescript.domain.execute",
    "path.target_root.resolve",
    "workspace.root.resolve",
    "filesystem.exists",
    "filesystem.read",
    "filesystem.glob",
    "json.parse",
    "toml.table.counts",
    "payload.assemble",
    "payload.status",
    "payload.lifecycle-plan",
    "payload.current-memory",
    "payload.verify",
    "output.emit",
    "output.emit.install-result",
    "output.emit.current-memory",
    "workspace.defaults.load",
    "workspace.defaults.select",
    "workspace.config.load",
    "output.fields.select",
    "workspace.config.emit",
    "python.function.call",
    "planning.closeout.apply",
    "planning.reconcile.load",
    "planning.summary.load",
    "planning.report.load",
    "memory.report.load",
    "memory.route_report.load",
    "memory.bootstrap.doctor.load",
    "memory.current.load",
    "memory.promotion_report.load",
    "memory.prompt.render",
    "planning.prompt.render",
    "prompt.render",
    "delegation.outcome.append",
    "workspace.selection.resolve",
}


def _typescript_primitive_supported(primitive: str) -> bool:
    return (
        primitive in TYPESCRIPT_SUPPORTED_EXACT_PRIMITIVES
        or (primitive.startswith("planning.") and primitive.endswith(".apply"))
        or primitive.startswith("system_intent.")
    )


def _validate_typescript_native_operation_execution(
    *,
    package: str,
    package_root: Path,
    command_package: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    checked_paths: set[str] = set()
    for command in command_package.get("commands", []):
        if not isinstance(command, dict) or command.get("status") != "generated":
            continue
        for operation_ref in _command_operation_refs(command):
            operation_id = str(operation_ref.get("id", "")).strip()
            operation_path = str(operation_ref.get("path", "")).strip()
            if not operation_id or not operation_path or operation_path in checked_paths:
                continue
            checked_paths.add(operation_path)
            resource_path = package_root / "resources" / operation_path
            if not resource_path.is_file():
                errors.append(f"{package} operation {operation_id!r} is native but resource {operation_path!r} is missing")
                continue
            try:
                operation = json.loads(resource_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{package} operation {operation_id!r} resource {operation_path!r} is unreadable: {exc}")
                continue
            ir_plan = operation.get("ir_plan", {})
            steps = ir_plan.get("steps", []) if isinstance(ir_plan, dict) else []
            if not isinstance(steps, list) or not steps:
                errors.append(f"{package} operation {operation_id!r} is native but has no executable ir_plan.steps")
                continue
            for step in steps:
                if not isinstance(step, dict):
                    errors.append(f"{package} operation {operation_id!r} has malformed ir_plan step")
                    continue
                primitive = str(step.get("uses", "")).strip()
                if not primitive:
                    errors.append(f"{package} operation {operation_id!r} has an ir_plan step without a primitive")
                elif not _typescript_primitive_supported(primitive):
                    errors.append(
                        f"{package} operation {operation_id!r} uses TypeScript primitive {primitive!r} without runtime support"
                    )
    return errors


def _validate_generated_command_projection_boundary(*, package_id: str, command: dict[str, object]) -> list[str]:
    errors: list[str] = []
    command_payload = command.get("command", {})
    command_name = command_payload.get("name", "<unknown>") if isinstance(command_payload, dict) else "<unknown>"
    location = f"command_package_ir.json package {package_id!r} command {command_name!r}"
    conformance_refs = command.get("conformance_refs", [])
    if not isinstance(conformance_refs, list) or not conformance_refs:
        errors.append(f"{location} must declare at least one conformance ref")
    projection_boundary = command.get("projection_boundary", {})
    if not isinstance(projection_boundary, dict):
        return [*errors, f"{location} projection_boundary is malformed"]
    expected_sections = {
        "universal": ["command identity", "operation reference", "runtime primitive reference", "effect hints", "conformance refs"],
        "target_specific": ["parser library", "package entrypoint wiring", "help text layout"],
        "runtime_owned": [],
    }
    for section, required_terms in expected_sections.items():
        values = projection_boundary.get(section, [])
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values) or not values:
            errors.append(f"{location} projection_boundary.{section} must be a non-empty string list")
            continue
        joined = " | ".join(values)
        for term in required_terms:
            if term not in joined:
                errors.append(f"{location} projection_boundary.{section} is missing {term!r}")
    target_specific = projection_boundary.get("target_specific", [])
    if isinstance(target_specific, list):
        target_text = " | ".join(str(value) for value in target_specific)
        for runtime_term in ("live workspace inspection", "payload assembly", "runtime primitive", "output emission"):
            if runtime_term in target_text:
                errors.append(f"{location} projection_boundary.target_specific contains runtime-owned term {runtime_term!r}")
    return errors


def _validate_python_cli_completion_policy(policy: dict[str, object]) -> list[str]:
    errors: list[str] = []
    finish_line = str(policy.get("finish_line", ""))
    current_state = str(policy.get("current_state", ""))
    allowed = [str(item) for item in policy.get("allowed_hand_owned_cli_responsibilities", []) if isinstance(item, str)]
    must_move = [str(item) for item in policy.get("must_move_behind_contracts_or_generation", []) if isinstance(item, str)]
    proof_requirements = [str(item) for item in policy.get("proof_requirements", []) if isinstance(item, str)]
    finish_line_lower = finish_line.lower()
    if "implementation-independent" not in finish_line_lower or "codegen-owned primitive executors" not in finish_line_lower:
        errors.append(
            "command_package_ir.json Python CLI completion finish_line must require implementation-independent artifacts and codegen-owned primitive executors"
        )
    if current_state not in PYTHON_COMPLETION_STATES:
        errors.append(f"command_package_ir.json Python CLI completion current_state is unknown: {current_state!r}")
    if not any("runtime primitive implementation" in item for item in allowed):
        errors.append("command_package_ir.json Python CLI completion policy must allow hand-owned runtime primitive implementation")
    for required in ("command parser shape", "option and help interface semantics", "generated command dispatch selection"):
        if not any(required in item for item in must_move):
            errors.append(f"command_package_ir.json Python CLI completion policy must move {required!r} behind contracts or generation")
    if not any("generic file" in item and "json" in item.lower() and "markdown" in item.lower() for item in must_move):
        errors.append(
            "command_package_ir.json Python CLI completion policy must move generic deterministic file/data behavior behind codegen-owned primitives"
        )
    if not any("weak-agent-safe-adapter" in item and "full Python generated CLI completion" in item for item in proof_requirements):
        errors.append(
            "command_package_ir.json Python CLI completion proof must distinguish adapter maturity from full generated CLI completion"
        )
    completion_gate = policy.get("completion_gate", {})
    if isinstance(completion_gate, dict) and current_state != "full-generated-cli-complete":
        if completion_gate.get("state") == "satisfied":
            errors.append(
                f"command_package_ir.json cannot mark the Python CLI completion gate satisfied while current_state is {current_state!r}"
            )
    if current_state == "full-generated-cli-complete":
        if not isinstance(completion_gate, dict):
            errors.append("command_package_ir.json full Python CLI completion requires a completion_gate object")
            return errors
        if completion_gate.get("state") != "satisfied":
            errors.append("command_package_ir.json full Python CLI completion requires completion_gate.state='satisfied'")
        if completion_gate.get("scope") != "python-only":
            errors.append("command_package_ir.json full Python CLI completion gate must be scoped to python-only")
        satisfied_by = completion_gate.get("satisfied_by", [])
        if not isinstance(satisfied_by, list) or not all(isinstance(item, dict) for item in satisfied_by):
            errors.append("command_package_ir.json full Python CLI completion gate satisfied_by entries are malformed")
            return errors
        evidence_ids = {str(item.get("id", "")) for item in satisfied_by}
        missing_evidence = sorted(PYTHON_COMPLETION_REQUIRED_EVIDENCE_IDS - evidence_ids)
        if missing_evidence:
            errors.append(f"command_package_ir.json full Python CLI completion gate is missing evidence ids: {missing_evidence!r}")
        for item in satisfied_by:
            evidence_id = str(item.get("id", ""))
            proof = str(item.get("proof", ""))
            evidence = str(item.get("evidence", ""))
            if not evidence.strip() or not proof.strip():
                errors.append(f"command_package_ir.json Python completion evidence {evidence_id!r} must name evidence and proof")
            expected_proof = PYTHON_COMPLETION_EXPECTED_PROOF_SUBSTRINGS.get(evidence_id)
            if expected_proof and expected_proof not in proof:
                errors.append(
                    f"command_package_ir.json Python completion evidence {evidence_id!r} must reference "
                    f"expected proof surface {expected_proof!r}; got {proof!r}"
                )
    return errors


def _validate_full_python_completion_runtime_ownership(ir: dict[str, object]) -> list[str]:
    python_completion = ir.get("generation_policy", {}).get("python_cli_completion", {})
    if not isinstance(python_completion, dict) or python_completion.get("current_state") != "full-generated-cli-complete":
        return []

    errors: list[str] = []
    generated_runtime_adapters = {
        "generated/workspace/python/cli.py": "workspace",
        "generated/planning/python/cli.py": "planning",
        "generated/memory/python/cli.py": "memory",
        "generated/verification/python/cli.py": "verification",
    }
    for relative_path in generated_runtime_adapters:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        required_fragments = [
            "def _run_command_module(",
            "from .commands import GENERATED_COMMAND_HANDLERS",
            "if argv_list and argv_list[0] in {'-h', '--help', '--version'}:",
            "build_generated_parser().parse_args(argv_list)",
            "if supports_generated_command(argv_list):",
            "return run_generated_command(argv_list, _run_command_module)",
        ]
        for fragment in required_fragments:
            if fragment not in text:
                errors.append(
                    "command_package_ir.json cannot claim full Python generated CLI completion while "
                    f"{relative_path} is missing generated-main boundary fragment {fragment!r}"
                )
        if "return runtime_main(argv_list)" in text:
            errors.append(
                "command_package_ir.json cannot claim full Python generated CLI completion while "
                f"{relative_path} contains compatibility runtime fallback dispatch"
            )
    return errors


def _validate_full_python_completion_executable_ownership(ir: dict[str, object]) -> list[str]:
    python_completion = ir.get("generation_policy", {}).get("python_cli_completion", {})
    if not isinstance(python_completion, dict) or python_completion.get("current_state") != "full-generated-cli-complete":
        return []

    errors: list[str] = []
    rendered_outputs = {
        output.path.relative_to(REPO_ROOT).as_posix() for output in render_workspace_command_package_outputs(ir, repo_root=REPO_ROOT)
    }
    required_generated_runtime_outputs = set(PYTHON_REQUIRED_RUNTIME_PROJECTION_OUTPUTS)
    missing_generated_runtime_outputs = sorted(required_generated_runtime_outputs - rendered_outputs)
    if missing_generated_runtime_outputs:
        errors.append(
            "command_package_ir.json cannot claim full Python generated CLI completion while generated/python runtime "
            "or operation executor files are not produced by command-generation render_outputs(): "
            f"{missing_generated_runtime_outputs!r}"
        )
    for relative_path in PYTHON_FULL_COMPLETION_BLOCKING_EXECUTABLE_PATHS:
        path = REPO_ROOT / relative_path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        matched_categories = _python_executable_behavior_categories(text)
        if matched_categories:
            errors.append(
                "command_package_ir.json cannot claim full Python generated CLI completion while shipped module "
                f"or product-specific command-generation source {relative_path} owns executable behavior markers: {matched_categories!r}"
            )
    boundary_errors, accepted_boundary_paths = _validate_python_completion_accepted_runtime_boundaries()
    errors.extend(boundary_errors)
    existing_runtime_source = sorted(
        relative_path
        for relative_path in PYTHON_FULL_COMPLETION_BLOCKING_RUNTIME_SOURCE_PATHS
        if (REPO_ROOT / relative_path).is_file() and relative_path not in accepted_boundary_paths
    )
    if existing_runtime_source:
        errors.append(
            "Tier 6 final Python completion promotion remains blocked while unaccepted package-domain runtime/lifecycle "
            "source is still present and must be proven permanent or retired: "
            f"{existing_runtime_source!r}"
        )
    runtime_imports = _generated_command_module_package_runtime_imports()
    if runtime_imports:
        errors.append(
            "command_package_ir.json cannot claim full Python generated CLI completion while generated command modules "
            f"import package-owned runtime helpers directly: {runtime_imports!r}"
        )
    generated_runtime_facade_imports = [
        relative_path
        for relative_path in _generated_runtime_facade_package_runtime_imports()
        if relative_path not in accepted_boundary_paths
    ]
    if generated_runtime_facade_imports:
        errors.append(
            "Tier 6 final Python completion promotion remains blocked while generated runtime facades still bridge to "
            f"unaccepted package-owned runtime helpers: {generated_runtime_facade_imports!r}"
        )
    return errors


def _generated_runtime_facade_package_runtime_imports() -> list[str]:
    forbidden_imports = (
        "from agentic_workspace.workspace_runtime_primitives import",
        "from repo_planning_bootstrap.runtime_projection import",
        "from repo_memory_bootstrap.runtime_primitives import",
        "from repo_planning_bootstrap.installer import",
        "from repo_memory_bootstrap.installer import",
    )
    findings: list[str] = []
    for primitives_dir in (
        REPO_ROOT / "generated" / "workspace" / "python" / "primitives",
        REPO_ROOT / "generated" / "planning" / "python" / "primitives",
        REPO_ROOT / "generated" / "memory" / "python" / "primitives",
    ):
        if not primitives_dir.is_dir():
            continue
        for path in sorted(primitives_dir.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            if any(import_text in text for import_text in forbidden_imports):
                findings.append(path.relative_to(REPO_ROOT).as_posix())
    return findings


def _generated_command_module_package_runtime_imports() -> list[str]:
    forbidden_imports = (
        "from agentic_workspace.workspace_runtime_primitives import",
        "from repo_planning_bootstrap.runtime_projection import",
        "from repo_memory_bootstrap.runtime_primitives import",
        "from repo_planning_bootstrap.installer import",
        "from repo_memory_bootstrap.installer import",
    )
    findings: list[str] = []
    for commands_dir in (
        REPO_ROOT / "generated" / "workspace" / "python" / "commands",
        REPO_ROOT / "generated" / "planning" / "python" / "commands",
        REPO_ROOT / "generated" / "memory" / "python" / "commands",
    ):
        if not commands_dir.is_dir():
            continue
        for path in sorted(commands_dir.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            if any(import_text in text for import_text in forbidden_imports):
                findings.append(path.relative_to(REPO_ROOT).as_posix())
    return findings


def _validate_direct_generated_python_command_projection() -> list[str]:
    errors: list[str] = []
    direct_commands = {
        "memory.list-files.report": REPO_ROOT / "generated" / "memory" / "python" / "commands" / "memory_list_files_report.py",
        "memory.list-skills.report": REPO_ROOT / "generated" / "memory" / "python" / "commands" / "memory_list_skills_report.py",
        "planning.list-files.report": REPO_ROOT / "generated" / "planning" / "python" / "commands" / "planning_list_files_report.py",
    }
    forbidden_fragments = (
        "generated_operation_contract",
        "run_operation_ir",
        "command_generation.primitive_executor",
        "repo_memory_bootstrap.runtime_primitives",
        "repo_planning_bootstrap.runtime_projection",
    )
    required_fragments_by_operation = {
        "memory.list-files.report": (
            "from ..primitives.resources import (",
            "project_payload_entries(",
            "resolve_repo_target_root(getattr(args, 'target', None), PROJECT_MARKERS)",
            "def _assemble_payload(",
            "emit_action_report(payload, str(getattr(args, 'format', 'text') or 'text'))",
        ),
        "memory.list-skills.report": (
            "from ..primitives.resources import find_resource_root, read_json_object",
            "def _assemble_payload(",
            "def _emit_output(",
            "registry = read_json_object(skills_root, 'REGISTRY.json')",
        ),
        "planning.list-files.report": (
            "from ..primitives.resources import emit_json_or_lines, find_resource_root, list_resource_files",
            "payload_root = find_resource_root(__file__, PAYLOAD_ROOT_CANDIDATES)",
            "skills_root = find_resource_root(__file__, SKILLS_ROOT_CANDIDATES)",
            "def _assemble_payload(",
            "list_resource_files(payload_root)",
            "emit_json_or_lines(payload, str(getattr(args, 'format', 'text') or 'text'), line_field='files')",
        ),
    }
    for operation_id, path in direct_commands.items():
        if not path.is_file():
            errors.append(f"{path.relative_to(REPO_ROOT).as_posix()} is missing for direct generated command {operation_id}")
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            if fragment in text:
                errors.append(
                    f"{path.relative_to(REPO_ROOT).as_posix()} direct generated command {operation_id} must not contain {fragment!r}"
                )
        for fragment in required_fragments_by_operation[operation_id]:
            if fragment not in text:
                errors.append(
                    f"{path.relative_to(REPO_ROOT).as_posix()} direct generated command {operation_id} "
                    f"must contain concrete primitive fragment {fragment!r}"
                )
    return errors


def _validate_python_runtime_projection_inventory(*, full_completion: bool) -> list[str]:
    errors: list[str] = []
    try:
        inventory = python_runtime_projection_inventory_manifest()
    except Exception as exc:  # noqa: BLE001
        return [f"python_runtime_projection_inventory.json is missing or invalid: {exc}"]

    entries = inventory.get("entries", [])
    if not isinstance(entries, list):
        return ["python_runtime_projection_inventory.json entries must be a list"]
    by_path = {str(entry.get("path")): entry for entry in entries if isinstance(entry, dict)}
    missing_paths = sorted(set(PYTHON_REQUIRED_RUNTIME_PROJECTION_OUTPUTS) - set(by_path))
    extra_paths = sorted(set(by_path) - set(PYTHON_REQUIRED_RUNTIME_PROJECTION_OUTPUTS))
    if missing_paths:
        errors.append(f"python_runtime_projection_inventory.json missing runtime projection entries: {missing_paths!r}")
    if extra_paths:
        errors.append(f"python_runtime_projection_inventory.json contains unexpected runtime projection entries: {extra_paths!r}")

    rendered_outputs = {
        output.path.relative_to(REPO_ROOT).as_posix()
        for output in render_workspace_command_package_outputs(load_workspace_command_package_ir(repo_root=REPO_ROOT), repo_root=REPO_ROOT)
    }
    for relative_path, expected in sorted(PYTHON_REQUIRED_RUNTIME_PROJECTION_OUTPUTS.items()):
        entry = by_path.get(relative_path)
        if not isinstance(entry, dict):
            continue
        package_id, program, artifact_kind = expected
        for field, expected_value in {
            "package_id": package_id,
            "program": program,
            "artifact_kind": artifact_kind,
        }.items():
            if entry.get(field) != expected_value:
                errors.append(f"python_runtime_projection_inventory.json {relative_path} has wrong {field}: {entry.get(field)!r}")
        path = REPO_ROOT / relative_path
        if not path.is_file():
            errors.append(f"python_runtime_projection_inventory.json {relative_path} does not exist in generated/python")
        provenance_status = entry.get("provenance_status")
        blocking_full_completion = bool(entry.get("blocking_full_completion"))
        if provenance_status == "rendered-by-command-generation" and relative_path not in rendered_outputs:
            errors.append(
                "python_runtime_projection_inventory.json cannot mark "
                f"{relative_path} rendered-by-command-generation because render_outputs() does not produce it"
            )
        if provenance_status == "transitional-generated-output-debt" and not blocking_full_completion:
            errors.append(
                f"python_runtime_projection_inventory.json transitional runtime projection debt must block full completion: {relative_path}"
            )
        if full_completion and (provenance_status != "rendered-by-command-generation" or blocking_full_completion):
            errors.append(
                "command_package_ir.json cannot claim full Python generated CLI completion while "
                f"python_runtime_projection_inventory.json tracks {relative_path} as {provenance_status!r} "
                f"with blocking_full_completion={blocking_full_completion!r}"
            )
    return errors


def _validate_python_completion_accepted_runtime_boundaries(*, require_exact: bool = True) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    try:
        inventory = python_runtime_projection_inventory_manifest()
    except Exception as exc:  # noqa: BLE001
        return [f"python_runtime_projection_inventory.json is missing or invalid: {exc}"], set()

    accepted = inventory.get("accepted_runtime_boundaries", {})
    if not isinstance(accepted, dict):
        return ["python_runtime_projection_inventory.json accepted_runtime_boundaries must be an object"], set()
    entries = accepted.get("entries", [])
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        return ["python_runtime_projection_inventory.json accepted_runtime_boundaries.entries must be a list of objects"], set()

    if str(accepted.get("required_granularity", "")) != "source-symbol":
        errors.append("python_runtime_projection_inventory.json accepted_runtime_boundaries must require source-symbol granularity")

    facade_bindings = _generated_runtime_facade_package_runtime_bindings()
    operation_bindings = _generated_operation_package_runtime_bindings()
    expected_keys = {
        (
            "runtime-facade-call",
            binding["facade_path"],
            binding["facade_symbol"],
            binding["source_module"],
            binding["source_symbol"],
        )
        for binding in facade_bindings
    }
    expected_keys.update(
        {
            (
                "operation-function-call",
                binding["operation_path"],
                binding["operation_id"],
                binding["source_module"],
                binding["source_symbol"],
            )
            for binding in operation_bindings
        }
    )
    expected_by_key = {
        (
            "runtime-facade-call",
            binding["facade_path"],
            binding["facade_symbol"],
            binding["source_module"],
            binding["source_symbol"],
        ): binding
        for binding in facade_bindings
    }
    expected_by_key.update(
        {
            (
                "operation-function-call",
                binding["operation_path"],
                binding["operation_id"],
                binding["source_module"],
                binding["source_symbol"],
            ): binding
            for binding in operation_bindings
        }
    )
    accepted_keys: set[tuple[str, str, str, str, str]] = set()
    source_path_by_module = {
        "agentic_workspace.workspace_runtime_primitives": "src/agentic_workspace/workspace_runtime_primitives.py",
        "agentic_workspace.doctor": "src/agentic_workspace/doctor.py",
        "repo_planning_bootstrap.installer": "packages/planning/src/repo_planning_bootstrap/installer.py",
        "repo_planning_bootstrap.runtime_projection": "packages/planning/src/repo_planning_bootstrap/runtime_projection.py",
        "repo_memory_bootstrap.installer": "packages/memory/src/repo_memory_bootstrap/installer.py",
        "repo_memory_bootstrap.runtime_search": "packages/memory/src/repo_memory_bootstrap/runtime_search.py",
        "repo_memory_bootstrap.runtime_primitives": "packages/memory/src/repo_memory_bootstrap/runtime_primitives.py",
        "repo_verification_bootstrap.runtime_primitives": "packages/verification/src/repo_verification_bootstrap/runtime_primitives.py",
    }
    source_path_keys: dict[str, set[tuple[str, str, str, str, str]]] = {path: set() for path in source_path_by_module.values()}
    for key in expected_keys:
        source_path = source_path_by_module.get(key[3])
        if source_path:
            source_path_keys[source_path].add(key)

    for index, entry in enumerate(entries):
        location = f"python_runtime_projection_inventory.json accepted_runtime_boundaries.entries[{index}]"
        if "path" in entry or entry.get("boundary_kind") in {"package-runtime-source", "generated-runtime-facade-bridge"}:
            errors.append(f"{location} uses whole-file runtime boundary acceptance; exact source-symbol entries are required")
            continue
        binding_kind = str(entry.get("binding_kind", "runtime-facade-call"))
        if binding_kind == "runtime-facade-call":
            key = (
                binding_kind,
                str(entry.get("facade_path", "")),
                str(entry.get("facade_symbol", "")),
                str(entry.get("source_module", "")),
                str(entry.get("source_symbol", "")),
            )
        elif binding_kind == "operation-function-call":
            key = (
                binding_kind,
                str(entry.get("operation_path", "")),
                str(entry.get("operation_id", "")),
                str(entry.get("source_module", "")),
                str(entry.get("source_symbol", "")),
            )
        else:
            errors.append(f"{location} has unsupported binding_kind {binding_kind!r}")
            continue
        if key not in expected_keys:
            errors.append(f"{location} does not match a generated exact package-runtime call: {key!r}")
        else:
            expected = expected_by_key[key]
            declared_operation_ids = set(entry.get("operation_ids", []))
            expected_operation_ids = set(expected.get("operation_ids", []))
            if declared_operation_ids != expected_operation_ids:
                errors.append(
                    f"{location} must declare operation_ids {sorted(expected_operation_ids)!r}; got {sorted(declared_operation_ids)!r}"
                )
            declared_primitive_refs = set(entry.get("primitive_refs", []))
            expected_primitive_refs = set(expected.get("primitive_refs", []))
            if declared_primitive_refs != expected_primitive_refs:
                errors.append(
                    f"{location} must declare primitive_refs {sorted(expected_primitive_refs)!r}; got {sorted(declared_primitive_refs)!r}"
                )
        for field in (
            "owner_package",
            "operation_ids",
            "primitive_refs",
            "runtime_boundary_class",
            "why_not_generic_deterministic",
            "conformance_ref",
            "status",
            "generic_behavior_audit",
        ):
            value = entry.get(field)
            if isinstance(value, list):
                missing = not value or not all(isinstance(item, str) and item.strip() for item in value)
            else:
                missing = not str(value or "").strip()
            if missing:
                errors.append(f"{location} must include non-empty {field}")
        boundary_class = str(entry.get("runtime_boundary_class", ""))
        if boundary_class in PYTHON_OPERATION_FULL_COMPLETION_BLOCKING_BOUNDARY_CLASSES:
            errors.append(f"{location} cannot accept generic deterministic runtime debt")
        if str(entry.get("status", "")) != PYTHON_ACCEPTED_RUNTIME_BOUNDARY_PERMANENCE_STATUS:
            errors.append(
                f"{location} must declare status={PYTHON_ACCEPTED_RUNTIME_BOUNDARY_PERMANENCE_STATUS!r} "
                "before full Python completion can be claimed"
            )
        errors.extend(_validate_python_completion_output_boundary_audit(entry, location=location))
        accepted_keys.add(key)

    missing_keys = sorted(expected_keys - accepted_keys)
    if require_exact and missing_keys:
        errors.append(
            "Tier 6 final Python completion promotion remains blocked until generated runtime facade "
            f"package-runtime calls have exact accepted source-symbol boundary entries: {missing_keys!r}"
        )

    accepted_nonblocking_paths: set[str] = set()
    if require_exact and not errors:
        for facade_path in PYTHON_FULL_COMPLETION_ACCEPTED_RUNTIME_FACADE_PATHS:
            facade_keys = {key for key in expected_keys if key[0] == "runtime-facade-call" and key[1] == facade_path}
            if facade_keys and facade_keys <= accepted_keys:
                accepted_nonblocking_paths.add(facade_path)
        for source_path, keys in source_path_keys.items():
            if keys and keys <= accepted_keys:
                accepted_nonblocking_paths.add(source_path)
    return errors, accepted_nonblocking_paths


def _validate_python_completion_output_boundary_audit(entry: dict[str, object], *, location: str) -> list[str]:
    source_symbol = str(entry.get("source_symbol", ""))
    if "emit" not in source_symbol:
        return []
    errors: list[str] = []
    if str(entry.get("runtime_boundary_class", "")) != "package-specific-judgment":
        errors.append(f"{location} output-emission boundary must use runtime_boundary_class='package-specific-judgment'")
    why = str(entry.get("why_not_generic_deterministic", ""))
    audit = str(entry.get("generic_behavior_audit", ""))
    if "remaining package-specific output judgment" not in why:
        errors.append(f"{location} output-emission boundary must explain the remaining package-specific output judgment")
    for phrase in PYTHON_OUTPUT_BOUNDARY_AUDIT_REQUIRED_PHRASES:
        if phrase not in audit:
            errors.append(f"{location} output-emission boundary audit must include {phrase!r}")
    return errors


def _python_runtime_boundary_metrics() -> dict[str, object]:
    try:
        inventory = python_runtime_projection_inventory_manifest()
    except Exception as exc:  # noqa: BLE001
        return {"status": "unavailable", "error": str(exc)}
    accepted = inventory.get("accepted_runtime_boundaries", {})
    entries = accepted.get("entries", []) if isinstance(accepted, dict) else []
    if not isinstance(entries, list):
        return {"status": "unavailable", "error": "accepted_runtime_boundaries.entries is not a list"}
    class_counts: dict[str, int] = {}
    package_counts: dict[str, int] = {}
    binding_kind_counts: dict[str, int] = {}
    output_emission_symbols: list[dict[str, str]] = []
    python_bridge_symbols: list[dict[str, str]] = []
    generic_debt_symbols: list[dict[str, str]] = []
    current_symbol_ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        current_symbol_ids.add(_accepted_runtime_symbol_id(entry))
        boundary_class = str(entry.get("runtime_boundary_class", "unknown") or "unknown")
        class_counts[boundary_class] = class_counts.get(boundary_class, 0) + 1
        owner_package = str(entry.get("owner_package", "unknown") or "unknown")
        package_counts[owner_package] = package_counts.get(owner_package, 0) + 1
        binding_kind = str(entry.get("binding_kind", "unknown") or "unknown")
        binding_kind_counts[binding_kind] = binding_kind_counts.get(binding_kind, 0) + 1
        source_symbol = str(entry.get("source_symbol", ""))
        operation_id = str(entry.get("operation_id", ""))
        source_module = str(entry.get("source_module", ""))
        primitive_refs = entry.get("primitive_refs", [])
        primitive_ref_strings = [str(ref) for ref in primitive_refs] if isinstance(primitive_refs, list) else []
        if "emit" in source_symbol:
            output_emission_symbols.append(
                {
                    "binding_kind": binding_kind,
                    "facade_path": str(entry.get("facade_path", "")),
                    "facade_symbol": str(entry.get("facade_symbol", "")),
                    "source_symbol": source_symbol,
                    "runtime_boundary_class": boundary_class,
                }
            )
        if "python.function.call" in primitive_ref_strings:
            python_bridge_symbols.append(
                {
                    "operation_id": operation_id,
                    "source_module": source_module,
                    "source_symbol": source_symbol,
                    "runtime_boundary_class": boundary_class,
                }
            )
        if boundary_class in PYTHON_OPERATION_FULL_COMPLETION_BLOCKING_BOUNDARY_CLASSES:
            generic_debt_symbols.append(
                {
                    "operation_id": operation_id,
                    "source_module": source_module,
                    "source_symbol": source_symbol,
                    "runtime_boundary_class": boundary_class,
                }
            )
    baseline_obj = accepted.get("baseline_symbols", []) if isinstance(accepted, dict) else []
    baseline_symbol_ids = {str(item) for item in baseline_obj} if isinstance(baseline_obj, list) else set()
    return {
        "status": "available",
        "accepted_runtime_symbol_count": sum(class_counts.values()),
        "accepted_runtime_symbol_count_by_package": dict(sorted(package_counts.items())),
        "accepted_runtime_symbol_count_by_class": dict(sorted(class_counts.items())),
        "accepted_runtime_symbol_count_by_binding_kind": dict(sorted(binding_kind_counts.items())),
        "output_fallback_symbol_count": len(output_emission_symbols),
        "python_bridge_step_count": len(python_bridge_symbols),
        "generic_debt_symbol_count": len(generic_debt_symbols),
        "baseline_symbol_count": len(baseline_symbol_ids),
        "new_symbols_since_baseline": sorted(current_symbol_ids - baseline_symbol_ids),
        "removed_symbols_since_baseline": sorted(baseline_symbol_ids - current_symbol_ids),
        "accepted_output_emission_symbol_count": len(output_emission_symbols),
        "accepted_output_emission_symbols": output_emission_symbols,
        "python_bridge_symbols": python_bridge_symbols,
        "generic_debt_symbols": generic_debt_symbols,
    }


def _accepted_runtime_symbol_id(entry: dict[str, object]) -> str:
    binding_kind = str(entry.get("binding_kind", "runtime-facade-call"))
    if binding_kind == "operation-function-call":
        return "|".join(
            (
                binding_kind,
                str(entry.get("operation_path", "")),
                str(entry.get("operation_id", "")),
                str(entry.get("source_module", "")),
                str(entry.get("source_symbol", "")),
            )
        )
    return "|".join(
        (
            binding_kind,
            str(entry.get("facade_path", "")),
            str(entry.get("facade_symbol", "")),
            str(entry.get("source_module", "")),
            str(entry.get("source_symbol", "")),
        )
    )


def _condition_requires_value(condition: object, *, value_name: str, expected: object) -> bool:
    if not isinstance(condition, dict):
        return False
    keys = set(condition)
    if keys == {"value", "equals"}:
        return condition.get("value") == value_name and condition.get("equals") == expected
    if keys == {"all"}:
        items = condition.get("all")
        return isinstance(items, list) and any(_condition_requires_value(item, value_name=value_name, expected=expected) for item in items)
    if keys == {"any"}:
        items = condition.get("any")
        return (
            isinstance(items, list)
            and bool(items)
            and all(_condition_requires_value(item, value_name=value_name, expected=expected) for item in items)
        )
    if keys == {"not"}:
        return _condition_requires_value(condition.get("not"), value_name=value_name, expected=not bool(expected))
    return False


def _operation_lifecycle_dry_run_profile(*, operation_path: Path) -> dict[str, object] | None:
    operation = json.loads(operation_path.read_text(encoding="utf-8"))
    operation_id = str(operation.get("id", ""))
    if not operation_id.endswith(".lifecycle"):
        return None
    inputs = operation.get("inputs", [])
    has_dry_run_input = (
        any(isinstance(item, dict) and item.get("name") == "dry_run" for item in inputs) if isinstance(inputs, list) else False
    )
    if not has_dry_run_input:
        return None
    steps = operation.get("ir_plan", {}).get("steps", [])
    if not isinstance(steps, list):
        steps = []
    codegen_dry_run_steps: list[str] = []
    package_runtime_dry_run_steps: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        primitive = str(step.get("uses", ""))
        condition = step.get("when")
        if primitive == "payload.lifecycle-plan" and _condition_requires_value(condition, value_name="dry_run", expected=True):
            codegen_dry_run_steps.append(str(step.get("id", primitive)))
        if primitive == "python.function.call":
            if condition is None or not _condition_requires_value(condition, value_name="dry_run", expected=False):
                package_runtime_dry_run_steps.append(str(step.get("id", primitive)))
    default_dry_run_owner = (
        "codegen" if codegen_dry_run_steps else "package-runtime" if package_runtime_dry_run_steps else "operation-runtime"
    )
    return {
        "operation_id": operation_id,
        "operation_path": operation_path.relative_to(REPO_ROOT).as_posix(),
        "default_dry_run_owner": default_dry_run_owner,
        "codegen_dry_run_steps": codegen_dry_run_steps,
        "package_runtime_dry_run_steps": package_runtime_dry_run_steps,
    }


def _lifecycle_dry_run_metrics() -> dict[str, object]:
    operation_roots = [
        REPO_ROOT / "generated" / "memory" / "python" / "operations",
        REPO_ROOT / "generated" / "planning" / "python" / "operations",
    ]
    profiles: list[dict[str, object]] = []
    for operation_root in operation_roots:
        if not operation_root.is_dir():
            continue
        for operation_path in sorted(operation_root.glob("*.json")):
            profile = _operation_lifecycle_dry_run_profile(operation_path=operation_path)
            if profile is not None:
                profiles.append(profile)
    codegen_owned = [profile for profile in profiles if profile["default_dry_run_owner"] == "codegen"]
    package_owned = [profile for profile in profiles if profile["default_dry_run_owner"] == "package-runtime"]
    operation_runtime_owned = [profile for profile in profiles if profile["default_dry_run_owner"] == "operation-runtime"]
    return {
        "status": "available",
        "lifecycle_dry_run_operation_count": len(profiles),
        "codegen_default_dry_run_operation_count": len(codegen_owned),
        "package_runtime_default_dry_run_operation_count": len(package_owned),
        "operation_runtime_default_dry_run_operation_count": len(operation_runtime_owned),
        "codegen_default_dry_run_operations": codegen_owned,
        "package_runtime_default_dry_run_operations": package_owned,
        "operation_runtime_default_dry_run_operations": operation_runtime_owned,
    }


def _validate_declarative_view_specs() -> list[str]:
    errors: list[str] = []
    schema_path = REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "schemas" / "view_spec.schema.json"
    view_spec_root = REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "view_specs"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"view spec schema is missing or invalid: {exc}"]
    for spec_path in sorted(view_spec_root.glob("*.json")):
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            Draft202012Validator(schema).validate(spec)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{spec_path.relative_to(REPO_ROOT).as_posix()} is not a valid view spec: {exc}")
            continue
        operation_id = str(spec.get("operation_id", ""))
        generated_operation = (
            REPO_ROOT / "generated" / "memory" / "python" / "operations" / f"{operation_id}.json"
        )
        if not generated_operation.is_file():
            errors.append(f"{spec_path.relative_to(REPO_ROOT).as_posix()} references missing generated operation {operation_id!r}")
            continue
        operation_text = generated_operation.read_text(encoding="utf-8")
        for primitive_ref in spec.get("primitive_refs", []):
            if f'"uses": "{primitive_ref}"' not in operation_text:
                errors.append(
                    f"{spec_path.relative_to(REPO_ROOT).as_posix()} primitive {primitive_ref!r} is not present in generated operation {operation_id}"
                )
    return errors


def _validate_lifecycle_dry_run_generation() -> list[str]:
    errors: list[str] = []
    try:
        inventory = python_runtime_projection_inventory_manifest()
    except Exception as exc:  # noqa: BLE001
        return [f"python_runtime_projection_inventory.json is missing or invalid for lifecycle dry-run proof: {exc}"]
    accepted = inventory.get("accepted_runtime_boundaries", {})
    entries = accepted.get("entries", []) if isinstance(accepted, dict) else []
    if not isinstance(entries, list):
        return ["python_runtime_projection_inventory.json accepted_runtime_boundaries.entries must be a list for lifecycle dry-run proof"]
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        primitive_refs = set(entry.get("primitive_refs", []))
        audit = str(entry.get("generic_behavior_audit", ""))
        if (
            "payload.lifecycle-plan" not in primitive_refs
            and "Default dry-run behavior is no longer generic deterministic runtime debt" not in audit
        ):
            continue
        operation_path = REPO_ROOT / str(entry.get("operation_path", ""))
        location = f"python_runtime_projection_inventory.json accepted_runtime_boundaries.entries[{index}]"
        if not operation_path.is_file():
            errors.append(f"{location} lifecycle dry-run proof operation_path does not exist: {operation_path}")
            continue
        profile = _operation_lifecycle_dry_run_profile(operation_path=operation_path)
        if not profile or profile["default_dry_run_owner"] != "codegen":
            errors.append(
                f"{location} claims generated default dry-run planning but {operation_path.relative_to(REPO_ROOT).as_posix()} "
                "does not route the default dry-run branch through payload.lifecycle-plan"
            )
    return errors


def _generated_runtime_facade_package_runtime_bindings() -> list[dict[str, str]]:
    allowed_modules = {
        "agentic_workspace.workspace_runtime_primitives",
        "agentic_workspace.doctor",
        "repo_planning_bootstrap.installer",
        "repo_planning_bootstrap.runtime_projection",
        "repo_memory_bootstrap.installer",
        "repo_memory_bootstrap.runtime_search",
        "repo_memory_bootstrap.runtime_primitives",
        "repo_verification_bootstrap.runtime_primitives",
    }
    metadata = _python_runtime_boundary_metadata()
    bindings: list[dict[str, str]] = []
    for relative_path in PYTHON_FULL_COMPLETION_ACCEPTED_RUNTIME_FACADE_PATHS:
        path = REPO_ROOT / relative_path
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative_path)
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.ImportFrom) and child.module in allowed_modules:
                    for alias in child.names:
                        if alias.name == "*":
                            continue
                        bindings.append(
                            {
                                "facade_path": relative_path,
                                "facade_symbol": node.name,
                                "source_module": child.module,
                                "source_symbol": alias.name,
                                "operation_ids": metadata.get((child.module, alias.name), {}).get("operation_ids", []),
                                "primitive_refs": metadata.get((child.module, alias.name), {}).get("primitive_refs", []),
                            }
                        )
    return sorted(bindings, key=lambda item: (item["facade_path"], item["facade_symbol"], item["source_module"], item["source_symbol"]))


def _generated_operation_package_runtime_bindings() -> list[dict[str, object]]:
    allowed_modules = {
        "agentic_workspace.workspace_runtime_primitives",
        "agentic_workspace.doctor",
        "repo_planning_bootstrap.installer",
        "repo_planning_bootstrap.runtime_projection",
        "repo_memory_bootstrap.installer",
        "repo_memory_bootstrap.runtime_search",
        "repo_memory_bootstrap.runtime_primitives",
        "repo_verification_bootstrap.runtime_primitives",
    }
    metadata = _python_runtime_boundary_metadata()
    operation_inventory_refs = _python_operation_inventory_domain_refs()
    bindings: list[dict[str, object]] = []
    for operations_dir in (
        REPO_ROOT / "generated" / "workspace" / "python" / "operations",
        REPO_ROOT / "generated" / "planning" / "python" / "operations",
        REPO_ROOT / "generated" / "memory" / "python" / "operations",
        REPO_ROOT / "generated" / "verification" / "python" / "operations",
    ):
        if not operations_dir.is_dir():
            continue
        for path in sorted(operations_dir.glob("*.json")):
            operation = json.loads(path.read_text(encoding="utf-8"))
            operation_id = str(operation.get("operation_id") or operation.get("id") or "")
            relative_path = path.relative_to(REPO_ROOT).as_posix()
            for call in _operation_python_function_calls(operation):
                source_module = str(call.get("import_module") or "")
                source_symbol = str(call.get("function") or "")
                if source_module not in allowed_modules or not source_symbol:
                    continue
                binding_metadata = metadata.get((source_module, source_symbol), {})
                bindings.append(
                    {
                        "operation_path": relative_path,
                        "operation_id": operation_id,
                        "source_module": source_module,
                        "source_symbol": source_symbol,
                        "operation_ids": [operation_id],
                        "primitive_refs": operation_inventory_refs.get(operation_id)
                        or binding_metadata.get("primitive_refs", ["python.function.call"]),
                    }
                )
    return sorted(
        bindings,
        key=lambda item: (
            str(item["operation_path"]),
            str(item["operation_id"]),
            str(item["source_module"]),
            str(item["source_symbol"]),
        ),
    )


def _operation_python_function_calls(value: object) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []
    if isinstance(value, dict):
        if value.get("import_module") and value.get("function"):
            calls.append(value)
        primitive_source_call = DOMAIN_RUNTIME_PRIMITIVE_SOURCE_CALLS.get(str(value.get("uses", "")))
        if primitive_source_call is not None:
            calls.append(primitive_source_call)
        for nested in value.values():
            calls.extend(_operation_python_function_calls(nested))
    elif isinstance(value, list):
        for item in value:
            calls.extend(_operation_python_function_calls(item))
    return calls


def _python_operation_inventory_domain_refs() -> dict[str, list[str]]:
    try:
        operation_inventory = json.loads(
            (REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "python_operation_execution_inventory.json").read_text(
                encoding="utf-8"
            )
        )
    except Exception:  # noqa: BLE001
        return {}
    refs_by_operation: dict[str, list[str]] = {}
    for entry in operation_inventory.get("entries", []):
        if not isinstance(entry, dict):
            continue
        operation_id = str(entry.get("operation_id") or "")
        refs = entry.get("domain_runtime_primitive_refs")
        if operation_id and isinstance(refs, list):
            refs_by_operation[operation_id] = sorted(str(ref) for ref in refs if isinstance(ref, str) and ref.strip())
    return refs_by_operation


def _python_runtime_boundary_metadata() -> dict[tuple[str, str], dict[str, list[str]]]:
    try:
        ir = command_package_ir_manifest()
    except Exception:  # noqa: BLE001
        return {}
    try:
        operation_inventory = json.loads(
            (REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "python_operation_execution_inventory.json").read_text(
                encoding="utf-8"
            )
        )
    except Exception:  # noqa: BLE001
        operation_inventory = {}
    operation_ids_by_package_primitive: dict[tuple[str, str], set[str]] = {}
    generated_operation_dirs = (
        ("root-workspace", REPO_ROOT / "generated" / "workspace" / "python" / "operations"),
        ("planning-bootstrap", REPO_ROOT / "generated" / "planning" / "python" / "operations"),
        ("memory-bootstrap", REPO_ROOT / "generated" / "memory" / "python" / "operations"),
        ("verification-cli", REPO_ROOT / "generated" / "verification" / "python" / "operations"),
    )
    for entry in operation_inventory.get("entries", []):
        if not isinstance(entry, dict):
            continue
        operation_id = str(entry.get("operation_id") or "")
        program = str(entry.get("program") or "")
        package_id = {
            "agentic-workspace": "root-workspace",
            "agentic-planning": "planning-bootstrap",
            "agentic-memory": "memory-bootstrap",
            "agentic-verification": "verification-cli",
        }.get(program, "")
        if not operation_id:
            continue
        for primitive_ref in entry.get("domain_runtime_primitive_refs", []):
            if isinstance(primitive_ref, str) and primitive_ref.strip():
                operation_ids_by_package_primitive.setdefault((package_id, primitive_ref), set()).add(operation_id)
    for package_id, operations_dir in generated_operation_dirs:
        if not operations_dir.is_dir():
            continue
        for path in sorted(operations_dir.glob("*.json")):
            operation = json.loads(path.read_text(encoding="utf-8"))
            operation_id = str(operation.get("operation_id") or operation.get("id") or "")
            if not operation_id:
                continue
            for primitive_ref in _operation_uses(operation):
                operation_ids_by_package_primitive.setdefault((package_id, primitive_ref), set()).add(operation_id)
    metadata: dict[tuple[str, str], dict[str, set[str]]] = {}

    def record(source_module: str, source_symbol: str, *, operation_id: str | None = None, primitive_ref: str | None = None) -> None:
        if not source_module or not source_symbol:
            return
        bucket = metadata.setdefault((source_module, source_symbol), {"operation_ids": set(), "primitive_refs": set()})
        if operation_id:
            bucket["operation_ids"].add(operation_id)
        if primitive_ref:
            bucket["primitive_refs"].add(primitive_ref)

    def collect_handler(handler: dict[str, object], *, package_id: str, primitive_ref: str | None) -> None:
        source_module = str(handler.get("import_module") or "")
        source_symbol = str(handler.get("function") or "")
        operation_id = handler.get("operation_id")
        record(source_module, source_symbol, operation_id=str(operation_id) if operation_id else None, primitive_ref=primitive_ref)
        if primitive_ref:
            for caller_operation_id in operation_ids_by_package_primitive.get((package_id, primitive_ref), set()):
                record(source_module, source_symbol, operation_id=caller_operation_id, primitive_ref=primitive_ref)
        for branch in ("if_true", "if_false"):
            nested = handler.get(branch)
            if isinstance(nested, dict):
                collect_handler(nested, package_id=package_id, primitive_ref=primitive_ref)

    for package in ir.get("packages", []):
        if not isinstance(package, dict):
            continue
        binding = package.get("python_runtime_binding", {})
        if not isinstance(binding, dict):
            continue
        package_id = str(package.get("id") or "")
        operation_executor = binding.get("operation_executor", {})
        if isinstance(operation_executor, dict):
            for handler in operation_executor.get("handlers", []):
                if isinstance(handler, dict):
                    collect_handler(handler, package_id=package_id, primitive_ref=str(handler.get("primitive") or ""))
        for handler in binding.get("runtime_module_handlers", []):
            if isinstance(handler, dict):
                collect_handler(
                    handler,
                    package_id=package_id,
                    primitive_ref=f"runtime_module_handler:{handler.get('operation_id')}",
                )
    return {key: {field: sorted(values) for field, values in value.items()} for key, value in metadata.items()}


def _operation_uses(value: object) -> set[str]:
    uses: set[str] = set()
    if isinstance(value, dict):
        primitive_ref = value.get("uses")
        if isinstance(primitive_ref, str) and primitive_ref.strip():
            uses.add(primitive_ref)
        for nested in value.values():
            uses.update(_operation_uses(nested))
    elif isinstance(value, list):
        for item in value:
            uses.update(_operation_uses(item))
    return uses


def _tracked_python_source_files() -> list[str]:
    if shutil.which("git") is None:
        return _source_tree_python_files()
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        return _source_tree_python_files()
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def _source_tree_python_files() -> list[str]:
    roots = [
        REPO_ROOT / "src" / "agentic_workspace",
        REPO_ROOT / "packages" / "planning" / "src" / "repo_planning_bootstrap",
        REPO_ROOT / "packages" / "memory" / "src" / "repo_memory_bootstrap",
        REPO_ROOT / "packages" / "verification" / "src" / "repo_verification_bootstrap",
        REPO_ROOT / "internal" / "command-generation" / "src" / "command_generation",
    ]
    paths = []
    for root in roots:
        if not root.is_dir():
            continue
        paths.extend(path.relative_to(REPO_ROOT).as_posix() for path in root.rglob("*.py") if path.is_file())
    return sorted(paths)


def _attribute_name(node: ast.AST) -> str:
    parts: list[str] = []
    current: ast.AST | None = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def _python_executable_behavior_categories(text: str) -> list[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ["unparseable-python-source"]

    categories: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name == "main":
                categories.add("console entrypoint")
            if node.name == "run_operation_ir":
                categories.add("generic operation executor")
            continue
        if isinstance(node, ast.Call):
            function_name = _attribute_name(node.func)
            if function_name == "argparse.ArgumentParser":
                categories.add("parser construction")
            elif function_name.endswith(".add_subparsers") or function_name.endswith(".add_parser"):
                categories.add("subparser ownership")
            elif function_name.endswith(".parse_args"):
                categories.add("command parsing")
            elif function_name in PYTHON_EXECUTABLE_DISPATCH_NAMES:
                categories.add(PYTHON_EXECUTABLE_DISPATCH_NAMES[function_name])
            continue
        if isinstance(node, ast.Name) and node.id in PYTHON_EXECUTABLE_DISPATCH_NAMES:
            categories.add(PYTHON_EXECUTABLE_DISPATCH_NAMES[node.id])
        elif isinstance(node, ast.Attribute):
            attribute_name = _attribute_name(node)
            short_name = attribute_name.rsplit(".", 1)[-1]
            if short_name in PYTHON_EXECUTABLE_DISPATCH_NAMES:
                categories.add(PYTHON_EXECUTABLE_DISPATCH_NAMES[short_name])
    return sorted(categories)


def _validate_python_shipped_source_executable_retirement() -> list[str]:
    errors: list[str] = []
    tracked_sources = _tracked_python_source_files()
    for relative_path in tracked_sources:
        is_shipped_module_source = relative_path.startswith(PYTHON_SHIPPED_MODULE_SOURCE_ROOTS)
        is_product_command_generation_source = relative_path.startswith(
            "internal/command-generation/src/command_generation/"
        ) and relative_path.endswith(PYTHON_PRODUCT_RUNTIME_SOURCE_PATTERNS)
        if not is_shipped_module_source and not is_product_command_generation_source:
            continue
        path = REPO_ROOT / relative_path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        matched_categories = _python_executable_behavior_categories(text)
        if matched_categories:
            errors.append(
                "tracked shipped Python source must stay retired from generated CLI executable ownership; "
                f"{relative_path} contains retired executable markers: {matched_categories!r}"
            )
    return errors


def _validate_python_operation_execution_inventory(ir: dict[str, object]) -> list[str]:
    errors: list[str] = []
    try:
        inventory = _load_json("python_operation_execution_inventory.json")
    except (OSError, json.JSONDecodeError) as exc:
        return [f"python_operation_execution_inventory.json is missing or invalid: {exc}"]

    if inventory.get("schema_version") != "agentic-workspace/python-operation-execution-inventory/v1":
        errors.append("python_operation_execution_inventory.json has an unknown schema_version")
    entries = inventory.get("entries", [])
    if not isinstance(entries, list):
        return errors + ["python_operation_execution_inventory.json entries must be a list"]
    by_operation = {str(entry.get("operation_id")): entry for entry in entries if isinstance(entry, dict)}
    generated_operations: dict[str, dict[str, object]] = {}
    for package in ir.get("packages", []):
        if not isinstance(package, dict):
            continue
        package_id = str(package.get("id", ""))
        generated_transport = {
            "root-workspace": "generated/workspace/python/cli.py",
            "planning-bootstrap": "generated/planning/python/cli.py",
            "memory-bootstrap": "generated/memory/python/cli.py",
            "verification-cli": "generated/verification/python/cli.py",
        }.get(package_id)
        for command in package.get("commands", []):
            if not isinstance(command, dict):
                continue
            interface = command.get("interface", {})
            if not isinstance(interface, dict):
                continue
            for operation_ref in _command_operation_refs(command):
                operation_id = str(operation_ref.get("id", ""))
                if not operation_id:
                    continue
                generated_operations[operation_id] = {
                    "program": package.get("program"),
                    "command": interface.get("name"),
                    "operation_contract": operation_ref.get("path"),
                    "generated_transport": generated_transport,
                    "conformance_ref": _command_conformance_ref_for_operation(command, operation_id),
                }
    missing_inventory = sorted(set(generated_operations) - set(by_operation))
    extra_inventory = sorted(set(by_operation) - set(generated_operations))
    if missing_inventory:
        errors.append(f"python_operation_execution_inventory.json missing generated operation ids: {missing_inventory!r}")
    if extra_inventory:
        errors.append(f"python_operation_execution_inventory.json contains entries outside generated operation ids: {extra_inventory!r}")
    for operation_id, expected in sorted(generated_operations.items()):
        entry = by_operation.get(operation_id)
        if not isinstance(entry, dict):
            continue
        for field in ("program", "command", "generated_transport", "operation_contract", "conformance_ref"):
            if entry.get(field) != expected.get(field):
                errors.append(f"python_operation_execution_inventory.json {operation_id} has wrong {field}: {entry.get(field)!r}")
        status = str(entry.get("status", ""))
        if status not in PYTHON_OPERATION_EXECUTION_FINAL_STATUSES and status != "compatibility-runtime-handler":
            errors.append(f"python_operation_execution_inventory.json {operation_id} has unknown status: {status!r}")
        hand_owned = entry.get("hand_owned_runtime_code")
        if not isinstance(hand_owned, list) or not all(isinstance(item, str) and item.strip() for item in hand_owned):
            errors.append(f"python_operation_execution_inventory.json {operation_id} must name hand_owned_runtime_code entries")
        if status == "portable-codegen-primitive-executed":
            primitive_refs = entry.get("portable_primitive_refs")
            if not isinstance(primitive_refs, list) or not primitive_refs:
                errors.append(
                    f"python_operation_execution_inventory.json {operation_id} portable primitive entry "
                    "must declare portable_primitive_refs"
                )
            elif any(ref not in REQUIRED_PORTABLE_PRIMITIVE_CONFORMANCE for ref in primitive_refs):
                errors.append(
                    f"python_operation_execution_inventory.json {operation_id} portable primitive entry "
                    f"contains non-portable primitive refs: {primitive_refs!r}"
                )
        if status == "domain-runtime-primitive-via-ir":
            primitive_refs = entry.get("domain_runtime_primitive_refs")
            if not isinstance(primitive_refs, list) or not primitive_refs:
                errors.append(
                    f"python_operation_execution_inventory.json {operation_id} domain runtime IR entry "
                    "must declare domain_runtime_primitive_refs"
                )
            boundary_class = str(entry.get("runtime_boundary_class", ""))
            if boundary_class not in PYTHON_OPERATION_ACCEPTED_BOUNDARY_CLASSES:
                errors.append(
                    f"python_operation_execution_inventory.json {operation_id} domain runtime IR entry "
                    f"must declare runtime_boundary_class in {sorted(PYTHON_OPERATION_ACCEPTED_BOUNDARY_CLASSES)!r}"
                )
            boundary_reason = str(entry.get("runtime_boundary_reason", "")).strip()
            if not boundary_reason:
                errors.append(
                    f"python_operation_execution_inventory.json {operation_id} domain runtime IR entry must explain runtime_boundary_reason"
                )
            for field in ("what_would_make_portable_later", "generic_behavior_audit"):
                if not str(entry.get(field, "")).strip():
                    errors.append(f"python_operation_execution_inventory.json {operation_id} domain runtime IR entry must include {field}")
            if "python.function.call" in primitive_refs and not str(entry.get("external_adapter_note", "")).strip():
                errors.append(
                    f"python_operation_execution_inventory.json {operation_id} domain runtime IR entry "
                    "using python.function.call must state that it is external-adapter debt, not portable primitive coverage"
                )
        if status == "accepted-hand-owned-runtime-primitive":
            boundary_class = str(entry.get("runtime_boundary_class", ""))
            if boundary_class not in PYTHON_OPERATION_ACCEPTED_BOUNDARY_CLASSES:
                errors.append(
                    f"python_operation_execution_inventory.json {operation_id} accepted hand-owned runtime entry "
                    f"must declare runtime_boundary_class in {sorted(PYTHON_OPERATION_ACCEPTED_BOUNDARY_CLASSES)!r}"
                )
            boundary_reason = str(entry.get("runtime_boundary_reason", "")).strip()
            if not boundary_reason:
                errors.append(
                    f"python_operation_execution_inventory.json {operation_id} accepted hand-owned runtime entry "
                    "must explain runtime_boundary_reason"
                )
            for field in ("what_would_make_portable_later", "generic_behavior_audit"):
                if not str(entry.get(field, "")).strip():
                    errors.append(
                        f"python_operation_execution_inventory.json {operation_id} accepted hand-owned runtime entry must include {field}"
                    )

    ir_consumed_operations = {
        "config.report",
        "delegation-outcome.append",
        "defaults.report",
        "memory.doctor.report",
        "memory.list-files.report",
        "memory.list-skills.report",
        "memory.promotion-report.report",
        "memory.report.report",
        "memory.route-report.report",
        "memory.status.report",
        "memory.verify-payload.report",
        "planning.doctor.report",
        "planning.close-item.lifecycle",
        "planning.create-review.lifecycle",
        "planning.report.report",
        "planning.handoff.report",
        "planning.list-files.report",
        "planning.prompt.render",
        "planning.status.report",
        "planning.verify-payload.report",
        "prompt.init",
        "prompt.uninstall",
        "prompt.upgrade",
        "system-intent.sync",
        "verification.report.report",
    }
    portable_primitive_operations = {
        "memory.list-files.report",
        "memory.list-skills.report",
        "memory.status.report",
        "memory.verify-payload.report",
        "planning.list-files.report",
    }
    expected_primitive_executors = {
        "memory.list-files.report": "generated/memory/python/commands/memory_list_files_report.py",
        "memory.list-skills.report": "generated/memory/python/commands/memory_list_skills_report.py",
        "planning.list-files.report": "generated/planning/python/commands/planning_list_files_report.py",
    }
    for operation_id in sorted(ir_consumed_operations):
        entry = by_operation.get(operation_id)
        if not isinstance(entry, dict):
            errors.append(f"python_operation_execution_inventory.json must track {operation_id} as generated-operation-IR executed")
            continue
        operation_contract = f"operations/{operation_id}.json"
        expected_status = (
            "portable-codegen-primitive-executed" if operation_id in portable_primitive_operations else "domain-runtime-primitive-via-ir"
        )
        if entry.get("status") != expected_status:
            errors.append(f"{operation_id} must be marked {expected_status} in python_operation_execution_inventory.json")
        expected_primitive_executor = expected_primitive_executors.get(
            operation_id,
            "internal/command-generation/src/command_generation/primitive_executor.py",
        )
        if entry.get("primitive_executor") != expected_primitive_executor:
            errors.append(f"{operation_id} must point at {expected_primitive_executor}")
        if entry.get("operation_contract") != operation_contract:
            errors.append(f"{operation_id} must point at {operation_contract}")

    operations_by_id = {operation_id: _load_json(f"operations/{operation_id}.json") for operation_id in ir_consumed_operations}
    for operation_id, operation in operations_by_id.items():
        if operation.get("migration_status") != "runtime-consumed":
            errors.append(f"operations/{operation_id}.json must be marked runtime-consumed")
        ir_plan = operation.get("ir_plan", {})
        if not isinstance(ir_plan, dict) or ir_plan.get("status") not in {"representative", "complete"}:
            errors.append(f"{operation_id} must keep a representative or complete ir_plan")

    generated_operation_packages = {
        "config.report": "root-workspace",
        "delegation-outcome.append": "root-workspace",
        "defaults.report": "root-workspace",
        "memory.doctor.report": "memory-bootstrap",
        "memory.list-files.report": "memory-bootstrap",
        "memory.list-skills.report": "memory-bootstrap",
        "memory.promotion-report.report": "memory-bootstrap",
        "memory.report.report": "memory-bootstrap",
        "memory.route-report.report": "memory-bootstrap",
        "memory.status.report": "memory-bootstrap",
        "memory.verify-payload.report": "memory-bootstrap",
        "planning.doctor.report": "planning-bootstrap",
        "planning.close-item.lifecycle": "planning-bootstrap",
        "planning.create-review.lifecycle": "planning-bootstrap",
        "planning.handoff.report": "planning-bootstrap",
        "planning.list-files.report": "planning-bootstrap",
        "planning.prompt.render": "planning-bootstrap",
        "planning.report.report": "planning-bootstrap",
        "planning.verify-payload.report": "planning-bootstrap",
        "planning.status.report": "planning-bootstrap",
        "prompt.init": "root-workspace",
        "prompt.uninstall": "root-workspace",
        "prompt.upgrade": "root-workspace",
        "system-intent.sync": "root-workspace",
        "verification.report.report": "verification-cli",
    }
    for operation_id, package_id in sorted(generated_operation_packages.items()):
        try:
            generated_module = _generated_package_for_package(package_id)
            generated_operation_contract = getattr(generated_module, "generated_operation_contract", None)
            if not callable(generated_operation_contract):
                errors.append(f"{package_id} generated package must expose generated_operation_contract()")
                continue
            if generated_operation_contract(operation_id) != operations_by_id[operation_id]:
                errors.append(f"generated operation contract drifted from source operation contract: {operation_id}")
        except (ImportError, KeyError, FileNotFoundError, json.JSONDecodeError) as exc:
            errors.append(f"generated operation contract could not be loaded for {operation_id}: {exc}")

    memory_operation_executor_text = (REPO_ROOT / "generated" / "memory" / "python" / "primitives" / "operation_executor.py").read_text(
        encoding="utf-8"
    )
    if "from .primitive_executor import" not in memory_operation_executor_text:
        errors.append("memory operation IR executor must import the target-local codegen-owned primitive executor")
    if "run_operation_steps(" not in memory_operation_executor_text:
        errors.append("memory operation IR executor must execute operation plans through codegen-owned run_operation_steps")
    if "from repo_memory_bootstrap.runtime_primitives import" in memory_operation_executor_text:
        errors.append("memory operation IR executor must route live runtime delegates through generated memory_runtime facade")
    memory_runtime_facade = REPO_ROOT / "generated" / "memory" / "python" / "primitives" / "memory_runtime.py"
    if not memory_runtime_facade.is_file():
        errors.append("generated memory runtime facade is missing")
    else:
        memory_runtime_text = memory_runtime_facade.read_text(encoding="utf-8")
        if (
            "isinstance(result, dict)" not in memory_runtime_text
            or "json.dumps(_serialise_value(values['result']), indent=2)" not in memory_runtime_text
        ):
            errors.append("generated memory runtime facade must emit dict JSON through generated-local code before source fallback")
        for function_name in ("_load_memory_bootstrap_doctor",):
            function_marker = f"def {function_name}(*args: Any, **kwargs: Any) -> Any:"
            if function_marker not in memory_runtime_text:
                errors.append(f"generated memory runtime facade must retain {function_name} source fallback for verbose/text behavior")
                continue
            function_text = memory_runtime_text.split(function_marker, 1)[1].split("\ndef ", 1)[0]
            if "_tiny_lifecycle_payload_from_toml_table_counts(" in function_text:
                errors.append(f"{function_name} JSON fast path must live in portable operation IR, not the generated memory runtime facade")
        if "_load_memory_bootstrap_status" in memory_runtime_text:
            errors.append("generated memory runtime facade must not retain retired memory status source fallback")
    if "_load_memory_promotion_report" in memory_runtime_text:
        errors.append("generated memory runtime facade must not keep the retired promotion-report runtime delegate")
    report_function_marker = "def _load_memory_report(*args: Any, **kwargs: Any) -> Any:"
    if report_function_marker not in memory_runtime_text:
        errors.append("generated memory runtime facade must retain _load_memory_report source fallback for verbose/text behavior")
    else:
        report_function_text = memory_runtime_text.split(report_function_marker, 1)[1].split("\ndef ", 1)[0]
        if "_tiny_memory_report_payload_from_toml_table_counts(" in report_function_text:
            errors.append("_load_memory_report JSON fast path must live in portable operation IR, not the generated memory runtime facade")
    if "_tiny_memory_report_payload_from_toml_table_counts" in memory_runtime_text:
        errors.append(
            "generated memory runtime facade must not own memory report JSON projection helpers; memory report JSON uses portable operation IR primitives"
        )
    if "_tiny_memory_report_fast" in memory_runtime_text:
        errors.append("generated memory runtime facade must not import the source tiny memory report fast path")
    if "_tiny_route_report_payload" in memory_runtime_text:
        errors.append(
            "generated memory runtime facade must not own route-report JSON projection helpers; route-report JSON uses portable operation IR primitives"
        )
    route_report_operation = REPO_ROOT / "generated" / "memory" / "python" / "operations" / "memory.route-report.report.json"
    if route_report_operation.is_file():
        route_report_text = route_report_operation.read_text(encoding="utf-8")
        for fragment in (
            '"uses": "filesystem.exists"',
            '"uses": "filesystem.glob"',
            '"uses": "payload.assemble"',
            '"uses": "memory.route_report.load"',
        ):
            if fragment not in route_report_text:
                errors.append(
                    "generated memory route-report operation must retain portable JSON primitives plus explicit verbose/text fallback"
                )
    report_operation = REPO_ROOT / "generated" / "memory" / "python" / "operations" / "memory.report.report.json"
    if report_operation.is_file():
        report_text = report_operation.read_text(encoding="utf-8")
        for fragment in (
            '"uses": "path.target_root.resolve"',
            '"uses": "toml.table.counts"',
            '"uses": "payload.assemble"',
            '"uses": "memory.report.load"',
        ):
            if fragment not in report_text:
                errors.append("generated memory report operation must retain portable JSON primitives plus explicit verbose/text fallback")
    verify_payload_operation = REPO_ROOT / "generated" / "memory" / "python" / "operations" / "memory.verify-payload.report.json"
    if verify_payload_operation.is_file():
        verify_payload_text = verify_payload_operation.read_text(encoding="utf-8")
        for fragment in (
            '"uses": "path.target_root.resolve"',
            '"uses": "payload.verify"',
            '"uses": "output.emit.install-result"',
            '"policy_root": "memory.contracts"',
            '"payload_root": "memory.package-payload"',
        ):
            if fragment not in verify_payload_text:
                errors.append("generated memory verify-payload operation must retain portable payload verification primitives")
        if '"uses": "python.function.call"' in verify_payload_text:
            errors.append("generated memory verify-payload operation must not retain a text runtime fallback")
    else:
        errors.append("generated memory verify-payload operation is missing")
    if "repo_memory_bootstrap._installer_paths" in memory_operation_executor_text:
        errors.append("memory operation IR executor must resolve package resources from generated target-local copies")
    if "_resolve_memory_target_root" in memory_operation_executor_text:
        errors.append("memory operation IR executor must use the generated target-root primitive instead of memory runtime")
    if "resolve_repo_target_root(values.get('target')" not in memory_operation_executor_text:
        errors.append("memory operation IR executor must render target-root resolution through target-local resource primitives")
    for direct_operation_id in ("memory.list-files.report", "memory.list-skills.report"):
        if direct_operation_id in memory_operation_executor_text:
            errors.append(f"{direct_operation_id} must be executed by its direct generated command module, not memory run_operation_ir")
    if "_handle_memory_promotion_report_load" in memory_operation_executor_text:
        errors.append("memory promotion-report must execute through declared memory.promotion_report.load, not a runtime facade handler")
    if "_assemble_memory_operation_payload" in memory_operation_executor_text:
        errors.append("memory operation IR executor must not keep the dead payload.assemble runtime bridge for direct commands")
    for marker in (
        "generated/memory/python/_payload/AGENTS.template.md",
        "generated/memory/python/_skills/REGISTRY.json",
        "generated/memory/python/_contracts/payload_verification.memory.json",
    ):
        if not (REPO_ROOT / marker).is_file():
            errors.append(f"memory generated Python resource copy is missing required marker: {marker}")
    for module_name in (
        "memory_doctor_report",
        "memory_promotion_report_report",
        "memory_report_report",
        "memory_route_report_report",
        "memory_status_report",
        "memory_verify_payload_report",
    ):
        command_text = (REPO_ROOT / "generated" / "memory" / "python" / "commands" / f"{module_name}.py").read_text(encoding="utf-8")
        if "run_operation_ir(" not in command_text:
            errors.append(f"generated/memory/python/commands/{module_name}.py must execute operation IR through run_operation_ir")

    planning_operation_executor_text = (REPO_ROOT / "generated" / "planning" / "python" / "primitives" / "operation_executor.py").read_text(
        encoding="utf-8"
    )
    if "from .primitive_executor import" not in planning_operation_executor_text:
        errors.append("planning operation IR executor must import the target-local codegen-owned primitive executor")
    if "run_operation_steps(" not in planning_operation_executor_text:
        errors.append("planning operation IR executor must execute operation plans through codegen-owned run_operation_steps")
    for forbidden_import in (
        "from repo_planning_bootstrap.installer import",
        "from repo_planning_bootstrap.runtime_projection import",
    ):
        if forbidden_import in planning_operation_executor_text:
            errors.append("planning operation IR executor must route live runtime delegates through generated planning facades")
    for facade_name in ("planning_installer.py", "planning_runtime.py"):
        facade_path = REPO_ROOT / "generated" / "planning" / "python" / "primitives" / facade_name
        if not facade_path.is_file():
            errors.append(f"generated planning runtime facade is missing: {facade_path.relative_to(REPO_ROOT).as_posix()}")
    if "planning.list-files.report" in planning_operation_executor_text:
        errors.append("planning.list-files.report must be executed by its direct generated command module, not planning run_operation_ir")
    if "planning.list-files.load" in planning_operation_executor_text:
        errors.append("planning.list-files.load must not remain as dead handler wiring in planning run_operation_ir")
    planning_runtime_text = (REPO_ROOT / "generated" / "planning" / "python" / "primitives" / "planning_runtime.py").read_text(
        encoding="utf-8"
    )
    if "load_planning_list_files_operation" in planning_runtime_text:
        errors.append("planning runtime facade must not keep the dead planning.list-files source delegate")
    if "def emit_planning_operation_output" not in planning_runtime_text or "isinstance(result, dict)" not in planning_runtime_text:
        errors.append("generated planning runtime facade must emit dict JSON through generated-local code before source fallback")
    for module_name in ("planning_doctor_report", "planning_report_report", "planning_status_report"):
        command_text = (REPO_ROOT / "generated" / "planning" / "python" / "commands" / f"{module_name}.py").read_text(encoding="utf-8")
        if "run_operation_ir(" not in command_text:
            errors.append(f"generated/planning/python/commands/{module_name}.py must execute operation IR through run_operation_ir")

    workspace_operation_executor_text = (
        REPO_ROOT / "generated" / "workspace" / "python" / "primitives" / "operation_executor.py"
    ).read_text(encoding="utf-8")
    if "from .primitive_executor import" not in workspace_operation_executor_text:
        errors.append("workspace operation IR executor must import the target-local codegen-owned primitive executor")
    if "run_operation_steps(" not in workspace_operation_executor_text:
        errors.append("workspace operation IR executor must execute operation plans through codegen-owned run_operation_steps")
    for module_name in (
        "config_report",
        "defaults_report",
        "delegation_outcome_append",
        "prompt_init",
        "prompt_uninstall",
        "prompt_upgrade",
        "system_intent_sync",
    ):
        command_text = (REPO_ROOT / "generated" / "workspace" / "python" / "commands" / f"{module_name}.py").read_text(encoding="utf-8")
        if "run_operation_ir(" not in command_text:
            errors.append(f"generated/workspace/python/commands/{module_name}.py must execute operation IR through run_operation_ir")

    python_completion = ir.get("generation_policy", {}).get("python_cli_completion", {})
    if isinstance(python_completion, dict) and python_completion.get("current_state") == "full-generated-cli-complete":
        incomplete = sorted(
            operation_id
            for operation_id, entry in by_operation.items()
            if isinstance(entry, dict) and entry.get("status") not in PYTHON_OPERATION_EXECUTION_FINAL_STATUSES
        )
        if incomplete:
            incomplete_statuses = sorted(
                f"{operation_id}:{by_operation[operation_id].get('status')}"
                for operation_id in incomplete
                if isinstance(by_operation.get(operation_id), dict)
            )
            errors.append(
                "command_package_ir.json cannot claim full Python generated CLI completion while "
                f"inventory entries remain outside accepted operation execution statuses: {incomplete_statuses!r}"
            )
        blocking_runtime_debt = sorted(
            operation_id
            for operation_id, entry in by_operation.items()
            if isinstance(entry, dict)
            and entry.get("status") in {"domain-runtime-primitive-via-ir", "accepted-hand-owned-runtime-primitive"}
            and entry.get("runtime_boundary_class") in PYTHON_OPERATION_FULL_COMPLETION_BLOCKING_BOUNDARY_CLASSES
        )
        if blocking_runtime_debt:
            errors.append(
                "command_package_ir.json cannot claim full Python generated CLI completion while accepted hand-owned "
                f"runtime entries still classify generic deterministic behavior as runtime debt: {blocking_runtime_debt!r}"
            )
    return errors


def _validate_python_runtime_handler_boundary() -> list[str]:
    errors: list[str] = []
    for package_id in ("root-workspace", "planning-bootstrap", "memory-bootstrap", "verification-cli"):
        runtime_module_name = f"{_entrypoint_for_package(package_id)}:commands"
        try:
            generated_module = _generated_package_for_package(package_id)
            commands_module = importlib.import_module(f"{generated_module.__name__}.commands")
        except ImportError as exc:
            errors.append(f"Python command module boundary import failed for {package_id}: {exc}")
            continue
        generated_operation_ids = getattr(generated_module, "generated_operation_ids", None)
        if not callable(generated_operation_ids):
            errors.append(f"{package_id} generated package must expose generated_operation_ids() from generated command-package IR")
            continue
        operation_ids = set(generated_operation_ids())
        handler_map = getattr(commands_module, "GENERATED_COMMAND_HANDLERS", None)
        if not isinstance(handler_map, dict):
            errors.append(f"{runtime_module_name} must expose GENERATED_COMMAND_HANDLERS as a command module binding map")
            continue
        handler_ids = {str(operation_id) for operation_id in handler_map}
        missing = sorted(operation_ids - handler_ids)
        extra = sorted(handler_ids - operation_ids)
        if missing:
            errors.append(f"{runtime_module_name} missing runtime adapter handlers for generated operations: {missing!r}")
        if extra:
            errors.append(f"{runtime_module_name} contains runtime adapter handlers outside generated operation ids: {extra!r}")
        for operation_id, handler in handler_map.items():
            handler_name = getattr(handler, "__name__", "")
            if not callable(handler):
                errors.append(f"{runtime_module_name} handler for {operation_id!r} is not callable")
                continue
            if handler_name != "run":
                errors.append(
                    f"{runtime_module_name} handler for {operation_id!r} must be a generated command module run function; "
                    f"got {handler_name!r}"
                )
    return errors


def _validate_no_legacy_generated_adapter_runtime_import(*, relative_path: str, text: str) -> list[str]:
    errors: list[str] = []
    legacy_import = "generated_command_adapters import GENERATED_COMMAND_ADAPTERS_BY_COMMAND"
    if legacy_import in text:
        errors.append(
            f"{relative_path} must route generated Python commands through generated command modules, "
            "not legacy generated_command_adapters runtime dispatch"
        )
    forbidden_entrypoint_fragments = (
        "_RUNTIME_EXPORT_SOURCES",
        "_sync_runtime_export_patches",
        "from agentic_workspace.workspace_runtime_primitives import",
        "from repo_planning_bootstrap.runtime_projection import",
        "from repo_memory_bootstrap.runtime_primitives import",
    )
    for fragment in forbidden_entrypoint_fragments:
        if fragment in text:
            errors.append(
                f"{relative_path} must not import package-owned runtime modules or patch-forward runtime exports "
                f"from generated Python entrypoints; found {fragment!r}"
            )
    return errors


def _validate_generated_python_target_layout() -> list[str]:
    errors: list[str] = []
    generated_python_root = REPO_ROOT / "generated" / "python"
    if generated_python_root.is_dir():
        legacy_dirs = sorted(path.name for path in generated_python_root.iterdir() if path.is_dir())
        if legacy_dirs:
            errors.append(
                "generated/python must contain only shared Python proof support files; legacy generated Python "
                "package directories must live under generated/<package>/python: " + ", ".join(legacy_dirs)
            )
    for package_name in ("workspace", "planning", "memory", "verification"):
        package_root = REPO_ROOT / "generated" / package_name / "python"
        if not package_root.is_dir():
            errors.append(f"generated/{package_name}/python is missing")
            continue
        for directory_name in ("commands", "operations", "primitives"):
            if not (package_root / directory_name).is_dir():
                errors.append(f"generated/{package_name}/python/{directory_name} is missing")
        if not (package_root / "cli.py").is_file():
            errors.append(f"generated/{package_name}/python/cli.py is missing")
    return errors


def _validate_generated_python_commands_absent_from_handwritten_parsers() -> list[str]:
    errors: list[str] = []
    for package_id in ("root-workspace", "planning-bootstrap", "memory-bootstrap", "verification-cli"):
        runtime_module_name = f"{_entrypoint_for_package(package_id)}:{_runtime_module_file_for_package(package_id)}"
        generated_module = _generated_package_for_package(package_id)
        runtime_module = _generated_runtime_module_for_package(package_id)
        generated_command_names = getattr(generated_module, "generated_command_names", None)
        build_parser = getattr(runtime_module, "build_parser", None)
        if not callable(generated_command_names) or not callable(build_parser):
            errors.append(f"{package_id} cannot prove generated command parser retirement")
            continue
        parser = build_parser()
        if "Weak-agent routing:" in str(getattr(parser, "epilog", "")):
            continue
        for command_name in generated_command_names():
            with contextlib.redirect_stderr(io.StringIO()):
                try:
                    parser.parse_args([str(command_name)])
                except SystemExit as exc:
                    if int(exc.code or 0) != 0:
                        continue
                else:
                    errors.append(
                        f"{runtime_module_name} handwritten parser still accepts generated command {command_name!r}; "
                        "generated command package metadata must own parser shape"
                    )
    return errors


def _generated_cli_compatibility_allowlist_reason(relative_path: str) -> str | None:
    if relative_path in GENERATED_CLI_COMPATIBILITY_VOCABULARY_ALLOWLIST:
        return GENERATED_CLI_COMPATIBILITY_VOCABULARY_ALLOWLIST[relative_path]
    for prefix, reason in GENERATED_CLI_COMPATIBILITY_VOCABULARY_ALLOWLIST_PREFIXES.items():
        if relative_path.startswith(prefix):
            return reason
    return None


def _validate_generated_cli_compatibility_vocabulary() -> list[str]:
    errors: list[str] = []
    candidate_paths: list[str] = []
    if shutil.which("git"):
        completed = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode == 0:
            candidate_paths = [path.strip().replace("\\", "/") for path in completed.stdout.splitlines() if path.strip()]
    if not candidate_paths:
        roots = (
            ".agentic-workspace",
            "docs",
            "generated",
            "internal",
            "packages",
            "scripts",
            "src",
            "tests",
            "pyproject.toml",
        )
        candidate_paths = []
        for root in roots:
            root_path = REPO_ROOT / root
            if root_path.is_file():
                candidate_paths.append(root)
            elif root_path.is_dir():
                candidate_paths.extend(_repo_relative(path) for path in root_path.rglob("*") if path.is_file())
    for relative_path in sorted(candidate_paths):
        if not relative_path.endswith((".py", ".json", ".toml", ".md")):
            continue
        path = REPO_ROOT / relative_path
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if not any(token in text for token in GENERATED_CLI_COMPATIBILITY_VOCABULARY):
            continue
        reason = _generated_cli_compatibility_allowlist_reason(relative_path)
        if reason is None:
            errors.append(f"{relative_path} contains generated_cli_package compatibility vocabulary without an explicit allowlist reason")
    return errors


def _planning_payload_surface_classification() -> dict[str, object]:
    path = REPO_ROOT / "packages" / "planning" / "payload-surface-classification.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _planning_wheel_force_include_entries() -> dict[str, str]:
    pyproject_path = REPO_ROOT / "packages" / "planning" / "pyproject.toml"
    payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    current: object = payload
    for key in ("tool", "hatch", "build", "targets", "wheel", "force-include"):
        if not isinstance(current, dict):
            return {}
        current = current.get(key, {})
    if not isinstance(current, dict):
        return {}
    return {str(source): str(destination) for source, destination in current.items()}


def _planning_generated_force_include_sources() -> tuple[set[str], list[str]]:
    errors: list[str] = []
    package_root = REPO_ROOT / "packages" / "planning"
    sources: set[str] = set()

    def should_count(path: Path) -> bool:
        return "__pycache__" not in path.parts and path.suffix != ".pyc"

    for source in _planning_wheel_force_include_entries():
        source_path = (package_root / source).resolve()
        try:
            relative_source = source_path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            continue
        if not relative_source.startswith("generated/planning/python/"):
            continue
        if source_path.is_dir():
            sources.update(_repo_relative(path) for path in source_path.rglob("*") if path.is_file() and should_count(path))
        elif source_path.is_file() and should_count(source_path):
            sources.add(relative_source)
        else:
            errors.append(f"planning wheel generated force-include source does not exist: {relative_source}")
    return sources, errors


def _validate_planning_generated_force_include_classification() -> list[str]:
    expected, errors = _planning_generated_force_include_sources()
    payload = _planning_payload_surface_classification()
    surfaces = payload.get("surfaces", [])
    if not isinstance(surfaces, list):
        return errors + ["packages/planning/payload-surface-classification.json surfaces must be a list"]
    classified = {str(surface.get("source_path", "")) for surface in surfaces if isinstance(surface, dict)}
    missing = sorted(expected - classified)
    if missing:
        errors.append(
            "packages/planning/payload-surface-classification.json is missing generated wheel force-include surfaces: "
            + ", ".join(missing[:12])
            + (" ..." if len(missing) > 12 else "")
        )
    return errors


def _source_import_roots(text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {"<unparseable>"}
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def _command_generation_source_files() -> list[Path]:
    source_root = REPO_ROOT / COMMAND_GENERATION_SOURCE_ROOT
    return sorted(path for path in source_root.rglob("*.py") if path.is_file())


def _accepted_extraction_coupling_paths(ir: dict[str, object]) -> tuple[set[str], list[str]]:
    errors: list[str] = []
    policy = ir.get("generation_policy", {})
    if not isinstance(policy, dict):
        return set(), ["command_package_ir generation_policy must be an object"]
    readiness = policy.get("extraction_readiness", {})
    if not isinstance(readiness, dict):
        return set(), ["command_package_ir generation_policy.extraction_readiness must be an object"]
    if str(readiness.get("owner", "")).strip() != "#1100":
        errors.append("command-generation extraction_readiness owner must be #1100")
    if str(readiness.get("status", "")).strip() not in {"ready", "ready-with-inventoried-product-coupling"}:
        errors.append("command-generation extraction_readiness status must not be blocked")
    couplings = readiness.get("accepted_couplings", [])
    if not isinstance(couplings, list):
        return set(), errors + ["command-generation extraction_readiness.accepted_couplings must be a list"]
    accepted_paths: set[str] = set()
    for index, coupling in enumerate(couplings):
        if not isinstance(coupling, dict):
            errors.append(f"command-generation extraction coupling {index} must be an object")
            continue
        location = f"command-generation extraction coupling {coupling.get('id', index)!r}"
        for field in ("id", "kind", "owner", "reason", "migration_path"):
            if not str(coupling.get(field, "")).strip():
                errors.append(f"{location} must declare {field}")
        paths = coupling.get("paths", [])
        if not isinstance(paths, list) or not paths:
            errors.append(f"{location} must declare at least one path")
            continue
        for raw_path in paths:
            relative_path = str(raw_path)
            if not relative_path.startswith(f"{COMMAND_GENERATION_SOURCE_ROOT}/"):
                errors.append(f"{location} path is outside command-generation source: {relative_path}")
                continue
            if not (REPO_ROOT / relative_path).is_file():
                errors.append(f"{location} path does not exist: {relative_path}")
                continue
            accepted_paths.add(relative_path)
    return accepted_paths, errors


def _validate_command_generation_extraction_readiness(ir: dict[str, object]) -> list[str]:
    accepted_paths, errors = _accepted_extraction_coupling_paths(ir)
    product_literal_paths: set[str] = set()
    for source_path in _command_generation_source_files():
        relative_path = _repo_relative(source_path)
        text = source_path.read_text(encoding="utf-8")
        forbidden_imports = sorted(set(COMMAND_GENERATION_FORBIDDEN_PRODUCT_IMPORT_ROOTS) & _source_import_roots(text))
        if forbidden_imports:
            errors.append(f"{relative_path} imports product modules inside reusable command-generation source: {forbidden_imports!r}")
        if any(token in text for token in COMMAND_GENERATION_PRODUCT_LITERAL_TOKENS):
            product_literal_paths.add(relative_path)
    missing_inventory = sorted(product_literal_paths - accepted_paths)
    if missing_inventory:
        errors.append(
            "command-generation source contains product-specific literals without extraction-readiness inventory: "
            f"{missing_inventory!r}"
        )
    stale_inventory = sorted(accepted_paths - product_literal_paths)
    if stale_inventory:
        errors.append(f"command-generation extraction-readiness inventory is stale for paths without product literals: {stale_inventory!r}")
    return errors


def _run_adapter_conformance(*, require_node: bool) -> list[str]:
    errors: list[str] = []
    node = shutil.which("node")
    if node is None:
        message = "adapter conformance skipped: node is not available"
        if require_node:
            return [message]
        print(message)
        return []

    python = _python_executable()
    with tempfile.TemporaryDirectory(prefix="agentic-workspace-generated-adapter-") as tmp:
        temp_root = Path(tmp)

        derived_cases, derived_errors = _runnable_typescript_conformance_cases()
        if derived_errors:
            return derived_errors

        shims: dict[str, Path] = {}

        def runtime_for_package(package_id: str) -> str:
            shim = shims.get(package_id)
            if shim is None:
                module_by_package = {
                    "root-workspace": "agentic_workspace.cli",
                    "planning-bootstrap": "repo_planning_bootstrap.cli",
                    "memory-bootstrap": "repo_memory_bootstrap.cli",
                    "verification-cli": "repo_verification_bootstrap.cli",
                }
                shim = temp_root / f"{package_id.replace('-', '_')}_cli_shim.py"
                shim.write_text(
                    "import sys\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'planning' / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'memory' / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'verification' / 'src')!r})\n"
                    f"from {module_by_package[package_id]} import main\n"
                    "raise SystemExit(main(sys.argv[1:]))\n",
                    encoding="utf-8",
                )
                shims[package_id] = shim
            return f'"{python}" "{shim}"'

        def materialize_fixture(case: AdapterConformanceCase) -> Path:
            fixture_root = temp_root / case.fixture_id
            if fixture_root.exists():
                shutil.rmtree(fixture_root)
            for relative_path, contents in case.fixture_files.items():
                path = fixture_root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents, encoding="utf-8")
            return fixture_root

        def compare_adapter(runnable_case: RunnableTypescriptConformanceCase) -> None:
            if not runnable_case.cli.is_file():
                errors.append(
                    f"adapter conformance failed before execution: {runnable_case.cli.relative_to(REPO_ROOT).as_posix()} is missing"
                )
                return
            case = runnable_case.case
            fixture_root = materialize_fixture(case)
            adapter_process = _capture(
                [node, str(runnable_case.cli), *case.success_args],
                cwd=fixture_root,
                env=_conformance_env(runtime=""),
            )
            if adapter_process.returncode != case.expected_exit:
                errors.append(
                    f"adapter failure: {runnable_case.package_id} {case.label} exit code drifted from contract; "
                    f"expected {case.expected_exit}, got {adapter_process.returncode}; stderr={adapter_process.stderr!r}"
                )
            else:
                if case.expected_fields is not None:
                    try:
                        adapter_selected = case.selected_fields(adapter_process.stdout)
                    except (KeyError, ValueError, json.JSONDecodeError) as exc:
                        errors.append(
                            f"adapter failure: {runnable_case.package_id} {case.label} stdout did not satisfy selected fields: {exc}; "
                            f"stdout={adapter_process.stdout!r}"
                        )
                    else:
                        if adapter_selected != case.expected_fields:
                            errors.append(
                                f"adapter failure: {runnable_case.package_id} {case.label} JSON selected fields drifted from contract; "
                                f"expected {case.expected_fields!r}, got {adapter_selected!r}"
                            )
            if adapter_process.stderr.strip() and not case.allow_stderr:
                errors.append(
                    f"adapter failure: {runnable_case.package_id} {case.label} emitted unexpected stderr: {adapter_process.stderr!r}"
                )

            if "--help" not in case.success_args:
                invalid_args = [*case.success_args, "--definitely-invalid"]
                adapter_invalid_process = _capture(
                    [node, str(runnable_case.cli), *invalid_args],
                    cwd=fixture_root,
                    env=_conformance_env(runtime=""),
                )
                if adapter_invalid_process.returncode == 0 or not adapter_invalid_process.stderr.strip():
                    errors.append(
                        f"adapter failure: {runnable_case.package_id} {case.label} invalid-option was not rejected by native TypeScript parser"
                    )

        for runnable_case in derived_cases:
            compare_adapter(runnable_case)
            fixture_root = materialize_fixture(runnable_case.case)
            help_result = _capture(
                [node, str(runnable_case.cli), "--help"],
                cwd=fixture_root,
                env=_conformance_env(runtime=""),
            )
            expected_routing = runnable_case.weak_agent_routing
            if (
                help_result.returncode != 0
                or "Supported generated commands:" not in help_result.stdout
                or f"Weak-agent routing: {expected_routing}" not in help_result.stdout
                or "Recovery:" not in help_result.stdout
            ):
                errors.append(
                    f"adapter failure: {runnable_case.package_id} help guidance drifted; "
                    f"exit={help_result.returncode}, stdout={help_result.stdout!r}, stderr={help_result.stderr!r}"
                )
            unsupported = _capture(
                [node, str(runnable_case.cli), "__unsupported__", "--format", "json"],
                cwd=fixture_root,
                env=_conformance_env(runtime=runtime_for_package(runnable_case.package_id)),
            )
            if (
                unsupported.returncode != 2
                or "Unsupported generated command" not in unsupported.stderr
                or "Recovery:" not in unsupported.stderr
                or unsupported.stdout.strip()
            ):
                errors.append(
                    f"adapter failure: {runnable_case.package_id} unsupported command refusal drifted; "
                    f"exit={unsupported.returncode}, stdout={unsupported.stdout!r}, stderr={unsupported.stderr!r}"
                )
            exercises_runtime = "--help" not in runnable_case.case.success_args
            if runnable_case.weak_agent_routing in {"allowed-read-only", "allowed-mutation-with-review"} and exercises_runtime:
                no_python_result = _capture(
                    [node, str(runnable_case.cli), *runnable_case.case.success_args],
                    cwd=fixture_root,
                    env=_conformance_env(runtime=""),
                )
                if no_python_result.returncode != runnable_case.case.expected_exit:
                    errors.append(
                        f"adapter failure: {runnable_case.package_id} native TypeScript execution drifted without Python runtime; "
                        f"exit={no_python_result.returncode}, stderr={no_python_result.stderr!r}"
                    )
                elif runnable_case.case.expected_fields is not None:
                    try:
                        native_selected = runnable_case.case.selected_fields(no_python_result.stdout)
                    except (KeyError, ValueError, json.JSONDecodeError) as exc:
                        errors.append(
                            f"adapter failure: {runnable_case.package_id} native TypeScript operation stdout did not satisfy "
                            f"selected fields without Python runtime: {exc}; stdout={no_python_result.stdout!r}"
                        )
                    else:
                        if native_selected != runnable_case.case.expected_fields:
                            errors.append(
                                f"adapter failure: {runnable_case.package_id} native TypeScript operation drifted without Python runtime; "
                                f"selected={native_selected!r}, stderr={no_python_result.stderr!r}"
                            )

    return errors


def _validate_static_surfaces() -> list[str]:
    errors: list[str] = []
    expected_levels = {
        "metadata-proof-fixture",
        "parser-help-proof",
        "runnable-read-only-adapter",
        "runtime-backed-read-only-adapter",
        "weak-agent-safe-adapter",
        "mutation-capable-adapter",
        "deferred",
    }
    ir_path = REPO_ROOT / SOURCE_PATH
    schema_path = REPO_ROOT / SCHEMA_PATH
    if not ir_path.is_file():
        errors.append("src/agentic_workspace/contracts/command_package_ir.json is missing")
    if not schema_path.is_file():
        errors.append("internal/command-generation/schemas/command_package_ir.schema.json is missing")
    if errors:
        return errors
    try:
        ir = load_workspace_command_package_ir(repo_root=REPO_ROOT)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"command-package IR validation failed: {exc}")
    else:
        errors.extend(_validate_command_generation_extraction_readiness(ir))
        errors.extend(_validate_generated_operation_cli_inputs(ir))
        maturity_policy = ir.get("generation_policy", {}).get("generated_package_maturity", {})
        level_ids = {level.get("id") for level in maturity_policy.get("levels", []) if isinstance(level, dict)}
        missing = expected_levels - level_ids
        if missing:
            errors.append(f"command_package_ir.json missing generated package maturity levels: {sorted(missing)!r}")
        routing_rule = str(maturity_policy.get("routing_rule", ""))
        if "Weak agents may use only generated targets" not in routing_rule:
            errors.append("command_package_ir.json maturity routing rule does not protect weak-agent routing")
        python_cli_completion = ir.get("generation_policy", {}).get("python_cli_completion", {})
        if not isinstance(python_cli_completion, dict):
            errors.append("command_package_ir.json generation_policy.python_cli_completion is missing or malformed")
        else:
            errors.extend(_validate_python_cli_completion_policy(python_cli_completion))
            errors.extend(_validate_full_python_completion_runtime_ownership(ir))
            errors.extend(_validate_full_python_completion_executable_ownership(ir))
            errors.extend(
                _validate_python_runtime_projection_inventory(
                    full_completion=python_cli_completion.get("current_state") == "full-generated-cli-complete",
                )
            )
        errors.extend(_validate_python_operation_execution_inventory(ir))
        shell_policy = str(ir.get("generation_policy", {}).get("shell_adapter_policy", ""))
        if "Issue #909 evaluation selects Bash as the first additional generated command transport candidate" not in shell_policy:
            errors.append("command_package_ir.json shell adapter policy does not record the #909 first transport evaluation")
        if "black-box conformance for runtime handoff" not in shell_policy:
            errors.append("command_package_ir.json shell adapter policy does not name the deferred conformance route")
        packages = {package.get("id"): package for package in ir.get("packages", []) if isinstance(package, dict)}
        workspace_package = packages.get("root-workspace")
        if isinstance(workspace_package, dict):
            workspace_targets = [target for target in workspace_package.get("targets", []) if isinstance(target, dict)]
            bash_targets = [target for target in workspace_targets if target.get("kind") == "bash"]
            powershell_targets = [target for target in workspace_targets if target.get("kind") == "powershell"]
            if not bash_targets or bash_targets[0].get("maturity_level_ref") != "deferred":
                errors.append("command_package_ir.json root Bash transport candidate must remain explicit and deferred")
            if not powershell_targets or powershell_targets[0].get("maturity_level_ref") != "deferred":
                errors.append("command_package_ir.json root PowerShell transport candidate must remain explicit and deferred")
        for package_id, package in packages.items():
            has_mutating_generated_command = any(
                isinstance(command, dict)
                and command.get("status") == "generated"
                and isinstance(command.get("effect_hints"), dict)
                and (
                    command["effect_hints"].get("writes_repo_state") is True
                    or command["effect_hints"].get("destructive") is True
                    or command["effect_hints"].get("requires_preflight_gate") is True
                )
                for command in package.get("commands", [])
            )
            for target in package.get("targets", []):
                if not isinstance(target, dict) or target.get("kind") not in {"python", "typescript"}:
                    continue
                if has_mutating_generated_command and target.get("maturity_level_ref") == "weak-agent-safe-adapter":
                    errors.append(
                        f"command_package_ir.json package {package_id!r} {target.get('kind')} target advertises "
                        "weak-agent-safe-adapter while generated commands include mutation-capable effects"
                    )
            for command in package.get("commands", []):
                if isinstance(command, dict) and command.get("status") == "generated":
                    errors.extend(_validate_generated_command_projection_boundary(package_id=str(package_id), command=command))
        expected_python_promotions = {
            "root-workspace": ("agentic-workspace", "generated/workspace/python"),
            "planning-bootstrap": ("agentic-planning", "generated/planning/python"),
            "memory-bootstrap": ("agentic-memory", "generated/memory/python"),
            "verification-cli": ("agentic-verification", "generated/verification/python"),
        }
        for package_id, (program, generated_root) in expected_python_promotions.items():
            package = packages.get(package_id)
            if not isinstance(package, dict):
                errors.append(f"command_package_ir.json is missing package {package_id!r}")
                continue
            python_targets = [
                target for target in package.get("targets", []) if isinstance(target, dict) and target.get("kind") == "python"
            ]
            if not python_targets:
                errors.append(f"command_package_ir.json package {package_id!r} is missing a Python generated target")
                continue
            python_target = python_targets[0]
            expected_maturity = (
                "runtime-backed-read-only-adapter" if package_id == "verification-cli" else "mutation-capable-adapter"
            )
            if python_target.get("maturity_level_ref") != expected_maturity:
                errors.append(
                    f"command_package_ir.json package {package_id!r} Python target maturity drifted; "
                    f"got {python_target.get('maturity_level_ref')!r}"
                )
            if python_target.get("generation_status") != expected_maturity:
                errors.append(
                    f"command_package_ir.json package {package_id!r} Python generation_status drifted; "
                    f"got {python_target.get('generation_status')!r}"
                )
            if package.get("program") != program:
                errors.append(f"command_package_ir.json package {package_id!r} program drifted from {program!r}")
            version_metadata = package.get("version_metadata", {})
            if not isinstance(version_metadata, dict):
                errors.append(f"command_package_ir.json package {package_id!r} is missing version_metadata")
            else:
                if version_metadata.get("source") != "python-package-metadata":
                    errors.append(f"command_package_ir.json package {package_id!r} version_metadata source is not python-package-metadata")
                if version_metadata.get("distribution") != program:
                    errors.append(
                        f"command_package_ir.json package {package_id!r} version_metadata distribution drifted from {program!r}"
                    )
                if not str(version_metadata.get("fallback_version", "")).strip():
                    errors.append(f"command_package_ir.json package {package_id!r} version_metadata fallback_version is missing")
            if python_target.get("generated_root") != generated_root:
                errors.append(
                    f"command_package_ir.json package {package_id!r} Python generated_root drifted from {generated_root!r}; "
                    f"got {python_target.get('generated_root')!r}"
                )
            if not (REPO_ROOT / generated_root / "cli.py").is_file():
                errors.append(f"{generated_root}/cli.py is missing")
            else:
                generated_text = (REPO_ROOT / generated_root / "cli.py").read_text(encoding="utf-8")
                if 'json.loads(\n    r"""' in generated_text:
                    errors.append(f"{generated_root}/cli.py embeds generated JSON instead of loading resources")
                if "def generated_maturity()" not in generated_text:
                    errors.append(f"{generated_root}/cli.py is missing generated_maturity")
                if "def generated_weak_agent_routing()" not in generated_text:
                    errors.append(f"{generated_root}/cli.py is missing generated_weak_agent_routing")
                if "def generated_operation_contract(" not in generated_text:
                    errors.append(f"{generated_root}/cli.py is missing generated_operation_contract")
                if "from .commands import GENERATED_COMMAND_HANDLERS" not in generated_text:
                    errors.append(f"{generated_root}/cli.py does not route through generated command modules")
                expected_routing = "review-required" if package_id == "verification-cli" else "allowed-mutation-with-review"
                if f"_GENERATED_WEAK_AGENT_ROUTING = {expected_routing!r}" not in generated_text:
                    errors.append(f"{generated_root}/cli.py does not advertise expected weak-agent routing {expected_routing!r}")
                if "0.0.0-generated" in generated_text:
                    errors.append(f"{generated_root}/cli.py hardcodes generated placeholder version output")
                if "def generated_package_version()" not in generated_text or "package_version(distribution)" not in generated_text:
                    errors.append(f"{generated_root}/cli.py does not derive --version from package metadata")
            for resource_name in ("command_package.json", "adapter_commands.json"):
                resource_path = REPO_ROOT / generated_root / resource_name
                if not resource_path.is_file():
                    errors.append(f"{generated_root}/{resource_name} is missing")
                    continue
                try:
                    payload = json.loads(resource_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    errors.append(f"{generated_root}/{resource_name} is invalid JSON: {exc}")
                    continue
                if resource_name == "command_package.json" and payload != package:
                    errors.append(f"{generated_root}/command_package.json drifted from command_package_ir.json package {package_id!r}")
                if resource_name == "adapter_commands.json":
                    expected_adapter_commands = []
                    for command in package.get("commands", []):
                        if not (
                            isinstance(command, dict)
                            and command.get("status") == "generated"
                            and isinstance(command.get("interface"), dict)
                            and isinstance(command.get("operation_ref"), dict)
                        ):
                            continue
                        operation_ref = command["operation_ref"]
                        expected_adapter_commands.append(
                            {
                                "adapter_id": command["adapter_id"],
                                "operation_id": operation_ref["id"],
                                "operation_path": operation_ref["path"],
                                "interface": dict(command["interface"]),
                            }
                        )
                    if payload != expected_adapter_commands:
                        errors.append(f"{generated_root}/adapter_commands.json drifted from generated adapter projection")
            for directory_name in ("commands", "operations", "primitives"):
                if not (REPO_ROOT / generated_root / directory_name).is_dir():
                    errors.append(f"{generated_root}/{directory_name} is missing")
            if not (REPO_ROOT / generated_root / "primitives" / "operation_executor.py").is_file():
                errors.append(f"{generated_root}/primitives/operation_executor.py is missing")
        generated_entrypoints = {
            "generated/workspace/python/cli.py": "from .commands import GENERATED_COMMAND_HANDLERS",
            "generated/planning/python/cli.py": "from .commands import GENERATED_COMMAND_HANDLERS",
            "generated/memory/python/cli.py": "from .commands import GENERATED_COMMAND_HANDLERS",
            "generated/verification/python/cli.py": "from .commands import GENERATED_COMMAND_HANDLERS",
        }
        for relative_path, command_import in generated_entrypoints.items():
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            main_index = text.find("def main(")
            generated_index = text.find("return run_generated_command(argv_list, _run_command_module)", main_index)
            errors.extend(_validate_no_legacy_generated_adapter_runtime_import(relative_path=relative_path, text=text))
            if command_import not in text:
                errors.append(f"{relative_path} does not import its generated Python command module registry")
            if "return runtime_main(argv_list)" in text:
                errors.append(f"{relative_path} still contains runtime fallback dispatch")
            if main_index == -1 or generated_index == -1:
                errors.append(f"{relative_path} does not route generated Python adapters through generated command modules")
        errors.extend(_validate_python_shipped_source_executable_retirement())
        errors.extend(_validate_python_runtime_handler_boundary())
        errors.extend(_validate_generated_python_target_layout())
        errors.extend(_validate_direct_generated_python_command_projection())
        errors.extend(_validate_planning_generated_force_include_classification())
        errors.extend(_validate_generated_python_commands_absent_from_handwritten_parsers())
        errors.extend(_validate_generated_cli_compatibility_vocabulary())
        forbidden_generated_entrypoints = [
            "src/agentic_workspace/generated_cli_package.py",
            "src/agentic_workspace/generated_cli_entrypoint.py",
            "src/agentic_workspace/generated_cli_package/__init__.py",
            "packages/planning/src/repo_planning_bootstrap/generated_cli_package.py",
            "packages/planning/src/repo_planning_bootstrap/generated_cli_entrypoint.py",
            "packages/planning/src/repo_planning_bootstrap/generated_cli_package/__init__.py",
            "packages/memory/src/repo_memory_bootstrap/generated_cli_package.py",
            "packages/memory/src/repo_memory_bootstrap/generated_cli_entrypoint.py",
            "packages/memory/src/repo_memory_bootstrap/generated_cli_package/__init__.py",
            "packages/verification/src/repo_verification_bootstrap/generated_cli_package.py",
            "packages/verification/src/repo_verification_bootstrap/generated_cli_entrypoint.py",
            "packages/verification/src/repo_verification_bootstrap/generated_cli_package/__init__.py",
        ]
        for relative_path in forbidden_generated_entrypoints:
            if (REPO_ROOT / relative_path).exists():
                errors.append(f"{relative_path} is obsolete generated-owned source layout outside generated/python")
        conformance_cases, conformance_errors = _runnable_typescript_conformance_cases()
        errors.extend(f"static conformance coverage drift: {error}" for error in conformance_errors)
        if not conformance_errors and not conformance_cases:
            errors.append(
                "static conformance coverage drift: no runnable TypeScript conformance cases were derived from contract artifacts"
            )
    dockerfile = REPO_ROOT / "generated" / "typescript.Dockerfile"
    if not dockerfile.is_file():
        errors.append("generated/typescript.Dockerfile is missing")
    python_conformance_dockerfile = REPO_ROOT / "generated" / "python" / "Dockerfile.conformance"
    if not python_conformance_dockerfile.is_file():
        errors.append("generated/python/Dockerfile.conformance is missing")
    primitive_conformance_dockerfile = REPO_ROOT / "generated" / "python" / "Dockerfile.primitive-conformance"
    if not primitive_conformance_dockerfile.is_file():
        errors.append("generated/python/Dockerfile.primitive-conformance is missing")
    primitive_conformance_script = REPO_ROOT / "internal" / "command-generation" / "tests" / "primitive_conformance.py"
    if not primitive_conformance_script.is_file():
        errors.append("internal/command-generation/tests/primitive_conformance.py is missing")
    else:
        primitive_conformance_text = primitive_conformance_script.read_text(encoding="utf-8")
        for primitive_id in sorted(REQUIRED_PORTABLE_PRIMITIVE_CONFORMANCE):
            if primitive_id not in primitive_conformance_text:
                errors.append(f"primitive conformance is missing required primitive case: {primitive_id}")
    conformance_dockerfile = REPO_ROOT / "generated" / "typescript.conformance.Dockerfile"
    if not conformance_dockerfile.is_file():
        errors.append("generated/typescript.conformance.Dockerfile is missing")
    ir = load_workspace_command_package_ir(repo_root=REPO_ROOT)
    typescript_targets = [
        (package, target)
        for package in ir.get("packages", [])
        if isinstance(package, dict)
        for target in package.get("targets", [])
        if isinstance(target, dict) and target.get("kind") == "typescript"
    ]
    for expected_package, target in typescript_targets:
        package_root = REPO_ROOT / str(target.get("generated_root", ""))
        package_label = package_root.relative_to(REPO_ROOT).as_posix()
        for relative in ("package.json", "src/commandPackage.ts", "resources/command_package.json", "test/command-package.test.mjs"):
            if not (package_root / relative).is_file():
                errors.append(f"{package_label}/{relative} is missing")
        package_json_path = package_root / "package.json"
        command_package_resource_path = package_root / "resources" / "command_package.json"
        command_package_resource: dict[str, object] | None = None
        if command_package_resource_path.is_file():
            try:
                command_package_resource = json.loads(command_package_resource_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{package_label}/resources/command_package.json is invalid JSON: {exc}")
        command_package_source_path = package_root / "src" / "commandPackage.ts"
        if command_package_source_path.is_file():
            source_text = command_package_source_path.read_text(encoding="utf-8")
            if "resources/command_package.json" not in source_text:
                errors.append(f"{package_label}/src/commandPackage.ts does not load generated resource JSON")
            if '"commands": [' in source_text or "adapter_id" in source_text:
                errors.append(f"{package_label}/src/commandPackage.ts embeds command-package payload instead of loading resources")
        if package_json_path.is_file():
            payload = json.loads(package_json_path.read_text(encoding="utf-8"))
            metadata = payload.get("agenticWorkspace", {})
            maturity = metadata.get("maturity", {})
            if command_package_resource is not None and expected_package is not None and command_package_resource != expected_package:
                errors.append(f"{package_label}/resources/command_package.json drifted from command_package_ir.json")
            if payload.get("files") != ["src", "resources"]:
                errors.append(f"{package_label}/package.json does not include generated resources")
            is_runnable = maturity.get("id") in {
                "runnable-read-only-adapter",
                "runtime-backed-read-only-adapter",
                "weak-agent-safe-adapter",
                "mutation-capable-adapter",
            }
            is_weak_agent_safe = maturity.get("id") == "weak-agent-safe-adapter"
            is_mutation_capable = maturity.get("id") == "mutation-capable-adapter"
            if not maturity.get("summary") or not maturity.get("promotion_requires"):
                errors.append(f"{package_label}/package.json maturity is missing summary or promotion criteria")
            if is_runnable and not (package_root / "src" / "cli.mjs").is_file():
                errors.append(f"{package_label}/src/cli.mjs is missing for runnable target")
            if is_runnable and "bin" not in payload:
                errors.append(f"{package_label}/package.json is missing bin entry for runnable target")
            cli_path = package_root / "src" / "cli.mjs"
            if is_runnable and cli_path.is_file():
                cli_text = cli_path.read_text(encoding="utf-8")
                runtime_path = package_root / "src" / "runtime.mjs"
                if not runtime_path.is_file():
                    errors.append(f"{package_label}/src/runtime.mjs is missing for runnable TypeScript target")
                else:
                    runtime_text = runtime_path.read_text(encoding="utf-8")
                    errors.extend(
                        _validate_typescript_runtime_handoff_thinness(
                            package=package_label,
                            cli_text=cli_text,
                            runtime_text=runtime_text,
                        )
                    )
                    if command_package_resource is not None:
                        errors.extend(
                            _validate_typescript_native_operation_execution(
                                package=package_label,
                                package_root=package_root,
                                command_package=command_package_resource,
                            )
                        )
            if is_weak_agent_safe and maturity.get("weak_agent_routing") != "allowed-read-only":
                errors.append(f"{package_label}/package.json weak-agent-safe target is missing allowed-read-only routing")
            if is_mutation_capable and maturity.get("weak_agent_routing") != "allowed-mutation-with-review":
                errors.append(f"{package_label}/package.json mutation-capable target is missing mutation review routing")
            if (
                is_runnable
                and not is_weak_agent_safe
                and not is_mutation_capable
                and maturity.get("weak_agent_routing") != "review-required"
            ):
                errors.append(f"{package_label}/package.json runnable target is missing review-required weak-agent routing")
            if not is_runnable and (maturity.get("weak_agent_routing") != "forbidden" or maturity.get("runnable") is not False):
                errors.append(f"{package_label}/package.json maturity does not mark proof fixture as non-runnable")
            if bool(metadata.get("fixtureOnly")) == is_runnable:
                errors.append(f"{package_label}/package.json fixtureOnly does not match maturity runnable state")
    return errors


def _run_docker(
    tag: str,
    *,
    dockerfile: str,
    proof_label: str,
    require_docker: bool,
    strict_retry_recovery: bool = False,
) -> int:
    if shutil.which("docker") is None:
        print(
            _format_docker_proof_environment_failure(
                proof_label=proof_label,
                phase="docker-cli",
                tag=tag,
                dockerfile=dockerfile,
                command=["docker"],
                returncode=127,
                stdout="",
                stderr="docker is not available",
            )
        )
        return 1 if require_docker else 0
    info = subprocess.run(["docker", "info"], cwd=REPO_ROOT, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if info.returncode:
        detail = info.stderr.strip().splitlines()
        suffix = f": {detail[0]}" if detail else ""
        print(f"docker daemon is not available; skipped {proof_label}{suffix}")
        print(
            _format_docker_proof_environment_failure(
                proof_label=proof_label,
                phase="docker-daemon",
                tag=tag,
                dockerfile=dockerfile,
                command=["docker", "info"],
                returncode=int(info.returncode),
                stdout="",
                stderr=info.stderr,
            )
        )
        return 1 if require_docker else 0
    build = _run_docker_step(
        ["docker", "build", "-f", dockerfile, "-t", tag, "."],
        proof_label=proof_label,
        phase="docker-build",
        tag=tag,
        dockerfile=dockerfile,
    )
    if build:
        return build
    run_command = ["docker", "run", "--rm"]
    if strict_retry_recovery:
        run_command.extend(["-e", "AGENTIC_GENERATED_STRICT_RETRY_RECOVERY=1"])
    run_command.append(tag)
    return _run_docker_step(
        run_command,
        proof_label=proof_label,
        phase="docker-run",
        tag=tag,
        dockerfile=dockerfile,
    )


def _run_primitive_conformance() -> int:
    return _run([_python_executable(), "internal/command-generation/tests/primitive_conformance.py"])


def _python_completion_blockers_report(ir: dict[str, object]) -> dict[str, object]:
    policy = ir.get("generation_policy", {}).get("python_cli_completion", {})
    if not isinstance(policy, dict):
        return {
            "kind": "python-completion-blockers/v1",
            "current_state": "missing",
            "completion_gate_state": "missing",
            "completion_claim_allowed": False,
            "false_completion_claim_would_fail": True,
            "blockers": ["command_package_ir.json generation_policy.python_cli_completion is missing or malformed"],
            "blocker_count": 1,
            "next_owner": "command_package_ir.json",
        }

    forced_full_ir = copy.deepcopy(ir)
    forced_policy = forced_full_ir["generation_policy"]["python_cli_completion"]
    forced_policy["current_state"] = "full-generated-cli-complete"
    forced_policy.setdefault("completion_gate", {})["state"] = "satisfied"

    blockers: list[str] = []
    blockers.extend(_validate_python_cli_completion_policy(forced_policy))
    blockers.extend(_validate_full_python_completion_runtime_ownership(forced_full_ir))
    blockers.extend(_validate_full_python_completion_executable_ownership(forced_full_ir))
    blockers.extend(_validate_python_runtime_projection_inventory(full_completion=True))
    blockers.extend(_validate_python_operation_execution_inventory(forced_full_ir))
    blockers.extend(_validate_lifecycle_dry_run_generation())
    blockers.extend(_validate_declarative_view_specs())

    current_state = str(policy.get("current_state", ""))
    gate = policy.get("completion_gate", {})
    gate_state = str(gate.get("state", "")) if isinstance(gate, dict) else "malformed"
    completion_claim_allowed = current_state == "full-generated-cli-complete" and gate_state == "satisfied" and not blockers
    return {
        "kind": "python-completion-blockers/v1",
        "current_state": current_state,
        "completion_gate_state": gate_state,
        "completion_claim_allowed": completion_claim_allowed,
        "false_completion_claim_would_fail": bool(blockers),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "accepted_runtime_boundary_metrics": _python_runtime_boundary_metrics(),
        "lifecycle_dry_run_metrics": _lifecycle_dry_run_metrics(),
        "remaining_scope": "tier-6-final-python-completion-promotion" if blockers else "none",
        "next_owner": ("#892 / tier-6-final-python-completion-promotion" if blockers else "none"),
    }


def _print_python_completion_blockers_report(report: dict[str, object], *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
        return

    print(f"Python completion state: {report['current_state']} (gate: {report['completion_gate_state']})")
    print(f"Completion claim allowed: {str(report['completion_claim_allowed']).lower()}")
    metrics = report.get("accepted_runtime_boundary_metrics", {})
    if isinstance(metrics, dict) and metrics.get("status") == "available":
        print(f"Accepted runtime symbols: {metrics.get('accepted_runtime_symbol_count')}")
        print(f"Accepted runtime symbols by package: {metrics.get('accepted_runtime_symbol_count_by_package')}")
        print(f"Accepted runtime symbols by class: {metrics.get('accepted_runtime_symbol_count_by_class')}")
        print(f"Accepted output-emission symbols: {metrics.get('accepted_output_emission_symbol_count')}")
        print(f"Python bridge steps: {metrics.get('python_bridge_step_count')}")
        print(f"Generic debt symbols: {metrics.get('generic_debt_symbol_count')}")
    lifecycle_metrics = report.get("lifecycle_dry_run_metrics", {})
    if isinstance(lifecycle_metrics, dict) and lifecycle_metrics.get("status") == "available":
        print(f"Lifecycle dry-run operations: {lifecycle_metrics.get('lifecycle_dry_run_operation_count')}")
        print(f"Codegen-owned default dry-run operations: {lifecycle_metrics.get('codegen_default_dry_run_operation_count')}")
        print(f"Package-runtime default dry-run operations: {lifecycle_metrics.get('package_runtime_default_dry_run_operation_count')}")
        print(f"Operation-runtime default dry-run operations: {lifecycle_metrics.get('operation_runtime_default_dry_run_operation_count')}")
    blockers = report.get("blockers", [])
    if not isinstance(blockers, list) or not blockers:
        print("Blockers: none")
        return
    print("Blockers:")
    for blocker in blockers:
        print(f"- {blocker}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check generated command package outputs.")
    parser.add_argument(
        "--python-completion-blockers",
        action="store_true",
        help="Print the compact blocker report for Python full generated CLI completion.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for report modes.",
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Run generated TypeScript package tests inside Docker.",
    )
    parser.add_argument(
        "--docker-conformance",
        action="store_true",
        help="Run runnable generated adapter canonical-runtime conformance inside Docker.",
    )
    parser.add_argument(
        "--conformance",
        action="store_true",
        help="Run black-box conformance for runnable generated adapters using local Node and the canonical Python CLI.",
    )
    parser.add_argument(
        "--python-conformance",
        action="store_true",
        help="Run black-box conformance for generated Python adapters using checked-in conformance contracts.",
    )
    parser.add_argument(
        "--python-docker-conformance",
        action="store_true",
        help="Run generated Python adapter conformance inside Docker.",
    )
    parser.add_argument(
        "--primitive-conformance",
        action="store_true",
        help="Run command-generation owned primitive executor conformance locally.",
    )
    parser.add_argument(
        "--primitive-docker-conformance",
        action="store_true",
        help="Run command-generation owned primitive executor conformance inside Docker.",
    )
    parser.add_argument(
        "--require-node",
        action="store_true",
        help="Fail instead of skipping adapter conformance when Node is unavailable.",
    )
    parser.add_argument(
        "--tag",
        default="agentic-workspace-generated-typescript-cli-test",
        help="Docker image tag used for generated TypeScript package tests.",
    )
    parser.add_argument(
        "--python-tag",
        default="agentic-workspace-generated-python-cli-test",
        help="Docker image tag used for generated Python package conformance.",
    )
    parser.add_argument(
        "--primitive-tag",
        default="agentic-workspace-generated-python-primitive-test",
        help="Docker image tag used for generated primitive executor conformance.",
    )
    parser.add_argument(
        "--require-docker",
        action="store_true",
        help="Fail instead of skipping when Docker is unavailable.",
    )
    parser.add_argument(
        "--strict-retry-recovery",
        action="store_true",
        help="Fail when generated adapter conformance recovers after a native/runtime crash retry.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.strict_retry_recovery:
        os.environ["AGENTIC_GENERATED_STRICT_RETRY_RECOVERY"] = "1"
    if args.python_completion_blockers:
        ir = load_workspace_command_package_ir(repo_root=REPO_ROOT)
        _print_python_completion_blockers_report(
            _python_completion_blockers_report(ir),
            output_format=str(args.format),
        )
        return 0

    generator = REPO_ROOT / "scripts" / "generate" / "generate_command_packages.py"
    freshness = _run([_python_executable(), str(generator), "--check"])
    if freshness:
        return freshness
    errors = _validate_static_surfaces()
    if errors:
        for error in errors:
            print(error)
        return 1
    if args.python_conformance:
        python_conformance_errors = _run_python_adapter_conformance()
        if python_conformance_errors:
            for error in python_conformance_errors:
                print(error)
            return 1
        print("[ok] generated Python command package adapter conformance")
    if args.primitive_conformance:
        primitive_status = _run_primitive_conformance()
        if primitive_status:
            return primitive_status
    if args.conformance:
        conformance_errors = _run_adapter_conformance(require_node=bool(args.require_node))
        if conformance_errors:
            for error in conformance_errors:
                print(error)
            return 1
        print("[ok] generated command package adapter conformance")
        print("[ok] weak-agent-safe generated adapter routing checks passed")
    docker_status = 0
    if args.python_docker_conformance:
        docker_status = _run_docker(
            f"{args.python_tag}-conformance",
            dockerfile="generated/python/Dockerfile.conformance",
            proof_label="generated Python package Docker conformance proof",
            require_docker=bool(args.require_docker),
            strict_retry_recovery=bool(args.strict_retry_recovery),
        )
        if docker_status:
            return docker_status
    if args.primitive_docker_conformance:
        docker_status = _run_docker(
            f"{args.primitive_tag}-conformance",
            dockerfile="generated/python/Dockerfile.primitive-conformance",
            proof_label="generated primitive executor Docker conformance proof",
            require_docker=bool(args.require_docker),
        )
        if docker_status:
            return docker_status
    if args.docker:
        docker_status = _run_docker(
            str(args.tag),
            dockerfile="generated/typescript.Dockerfile",
            proof_label="generated TypeScript package Docker proof",
            require_docker=bool(args.require_docker),
        )
        if docker_status:
            return docker_status
    if args.docker_conformance:
        docker_status = _run_docker(
            f"{args.tag}-conformance",
            dockerfile="generated/typescript.conformance.Dockerfile",
            proof_label="generated TypeScript package Docker conformance proof",
            require_docker=bool(args.require_docker),
        )
        if docker_status:
            return docker_status
    if args.docker or args.docker_conformance or args.primitive_docker_conformance:
        print("[ok] generated command package Docker proof")
        return 0
    print("[ok] generated command package static proof")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
