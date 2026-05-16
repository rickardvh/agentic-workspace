from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_SCRIPT_ROOT = REPO_ROOT / "scripts" / "generate"
if str(GENERATOR_SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(GENERATOR_SCRIPT_ROOT))
for SOURCE_ROOT in (
    REPO_ROOT / "src",
    REPO_ROOT / "packages" / "command-generation" / "src",
    REPO_ROOT / "packages" / "planning" / "src",
    REPO_ROOT / "packages" / "memory" / "src",
):
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))

from workspace_command_generation import (  # noqa: E402
    SCHEMA_PATH,
    SOURCE_PATH,
    load_workspace_command_package_ir,
    render_workspace_command_package_outputs,
)

from agentic_workspace.contract_tooling import operation_manifest, python_runtime_projection_inventory_manifest  # noqa: E402
from command_generation.generated_package_loader import (  # noqa: E402
    load_generated_command_module_for_entrypoint,
    load_generated_command_package_for_entrypoint,
)

SelectedFields = Callable[[str], dict[str, object]]


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
REQUIRED_PORTABLE_PRIMITIVE_CONFORMANCE = {
    "path.target_root.resolve",
    "filesystem.read",
    "filesystem.glob",
    "json.parse",
    "payload.assemble",
    "output.emit",
}
PYTHON_MODULE_SOURCE_EXECUTABLE_MARKERS = {
    "parser construction": ("argparse.ArgumentParser", ".add_subparsers(", ".add_parser("),
    "command parsing": (".parse_args(",),
    "console entrypoint": ("def main(",),
    "generated runtime dispatch": ("run_generated_command", "supports_generated_command", "_GENERATED_RUNTIME_HANDLERS"),
    "runtime fallback dispatch": ("runtime_main", "_run_generated_cli_package_if_supported"),
    "generic operation executor": ("def run_operation_ir(", "run_operation_steps("),
}
PYTHON_SHIPPED_MODULE_SOURCE_ROOTS = (
    "src/agentic_workspace/",
    "packages/planning/src/repo_planning_bootstrap/",
    "packages/memory/src/repo_memory_bootstrap/",
)
PYTHON_PRODUCT_RUNTIME_SOURCE_PATTERNS = (
    "workspace_runtime_cli.py",
    "planning_runtime_cli.py",
    "memory_runtime_cli.py",
    "workspace_operation_ir_executor.py",
    "planning_operation_ir_executor.py",
    "memory_operation_ir_executor.py",
)
PYTHON_FULL_COMPLETION_BLOCKING_EXECUTABLE_PATHS = (
    "src/agentic_workspace/_runtime_cli.py",
    "packages/planning/src/repo_planning_bootstrap/_runtime_cli.py",
    "packages/memory/src/repo_memory_bootstrap/_runtime_cli.py",
    "src/agentic_workspace/generated_cli_package.py",
    "packages/planning/src/repo_planning_bootstrap/generated_cli_package.py",
    "packages/memory/src/repo_memory_bootstrap/generated_cli_package.py",
    "src/agentic_workspace/operation_ir_executor.py",
    "packages/planning/src/repo_planning_bootstrap/operation_ir_executor.py",
    "packages/memory/src/repo_memory_bootstrap/operation_ir_executor.py",
)
PYTHON_FULL_COMPLETION_BLOCKING_RUNTIME_SOURCE_PATHS = (
    "src/agentic_workspace/workspace_runtime_primitives.py",
    "src/agentic_workspace/doctor.py",
    "packages/planning/src/repo_planning_bootstrap/installer.py",
    "packages/planning/src/repo_planning_bootstrap/runtime_projection.py",
    "packages/memory/src/repo_memory_bootstrap/installer.py",
    "packages/memory/src/repo_memory_bootstrap/runtime_primitives.py",
)
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
    "packages/planning/payload-surface-classification.json": "installed private bridge compatibility inventory",
    ".agentic-workspace/planning/mutation-provenance.json": "historical planning mutation provenance",
    "packages/command-generation/src/command_generation/generated_package_loader.py": "legacy loader compatibility wrappers and legacy layout fallback",
    "src/agentic_workspace/workspace_runtime_primitives.py": "legacy parser helper compatibility wrapper",
    "scripts/check/check_generated_command_packages.py": "static compatibility allowlist and obsolete-layout guards",
    "tests/test_command_generation_artifacts.py": "obsolete target-specific runtime guard",
    "tests/test_contract_tooling.py": "legacy-layout fixture and obsolete source guard",
    "tests/test_workspace_packaging.py": "installed private bridge compatibility proof",
    "packages/planning/tests/test_packaging.py": "installed private bridge compatibility proof",
    "packages/memory/tests/test_packaging.py": "installed private bridge compatibility proof",
}
GENERATED_CLI_COMPATIBILITY_VOCABULARY_ALLOWLIST_PREFIXES = {
    ".agentic-workspace/planning/execplans/archive/": "historical planning evidence",
    "docs/reviews/": "historical review evidence",
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
}


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
        str(REPO_ROOT / "packages" / "command-generation" / "src"),
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
    }
    return entrypoints[package_id]


def _runtime_module_file_for_package(package_id: str) -> str:
    return "cli.py"


def _generated_package_for_package(package_id: str):
    return load_generated_command_package_for_entrypoint(_entrypoint_for_package(package_id))


def _generated_runtime_module_for_package(package_id: str):
    return load_generated_command_module_for_entrypoint(_entrypoint_for_package(package_id), _runtime_module_file_for_package(package_id))


def _python_command_for_package(package_id: str) -> list[str]:
    entrypoint = _entrypoint_for_package(package_id)
    return [
        _python_executable(),
        "-c",
        (
            "import sys; from command_generation.console import main_for_entrypoint; "
            f"raise SystemExit(main_for_entrypoint({entrypoint!r}, sys.argv[1:]))"
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
    return (
        f"[warn] generated {language} adapter runtime crash recovered after retry: "
        f"proof_surface={_generated_adapter_proof_surface(language=language)}; package={package_id}; "
        f"conformance_ref={case.conformance_ref}; command={command_name}; command_args={case.success_args!r}; "
        f"fixture={case.fixture_id}; adapter_entrypoint={command[0]!r}; first_exit={first_returncode}; detail={detail}"
    )


def _load_json(relative_path: str) -> dict[str, object]:
    return operation_manifest(relative_path) if relative_path.startswith("operations/") else json.loads(
        (REPO_ROOT / "src" / "agentic_workspace" / "contracts" / relative_path).read_text(encoding="utf-8")
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
                _load_generated_operation_json(generated_root, operation_path)
                if generated_root is not None
                else _load_json(operation_path)
            )
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(
                f"{package_id} {command_path} operation {operation_id} cannot be loaded for CLI input proof: {exc}"
            )
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
                    interface.get("name")
                    or (raw_command.get("name") if isinstance(raw_command, dict) else "")
                    or "<unnamed>"
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

    ir = load_workspace_command_package_ir(repo_root=REPO_ROOT)
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
                entrypoint = _entrypoint_for_package(package_id)
                shim = temp_root / f"{package_id.replace('-', '_')}_cli_shim.py"
                shim.write_text(
                    "import sys\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'command-generation' / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'planning' / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'memory' / 'src')!r})\n"
                    "from command_generation.console import main_for_entrypoint\n"
                    f"raise SystemExit(main_for_entrypoint({entrypoint!r}, sys.argv[1:]))\n",
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
                            print(
                                _format_generated_adapter_retry_recovery(
                                    language="python",
                                    package_id=package_id,
                                    case=case,
                                    command=command,
                                    first_returncode=process.returncode,
                                )
                            )
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
            and target.get("maturity_level_ref")
            in {"runnable-read-only-adapter", "weak-agent-safe-adapter", "mutation-capable-adapter"}
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
                        f"missing generated TypeScript conformance case for {package_id!r} command {command_name!r} "
                        f"ref {conformance_ref!r}"
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


def _validate_typescript_runtime_handoff_thinness(*, package: str, cli_text: str) -> list[str]:
    errors: list[str] = []
    expected_imports = {
        "import { spawnSync } from 'node:child_process';",
        "import { writeSync } from 'node:fs';",
    }
    import_lines = {line.strip() for line in cli_text.splitlines() if line.startswith("import ")}
    unexpected_imports = sorted(import_lines - expected_imports)
    if unexpected_imports:
        errors.append(
            f"generated/typescript/{package}/src/cli.mjs imports runtime-owned modules: {unexpected_imports!r}"
        )
    required_fragments = [
        "function splitRuntimeCommand(commandLine)",
        "const [runtimeExecutable, ...runtimeArgs] = splitRuntimeCommand(runtimeCommand);",
        "spawnSync(runtimeExecutable, [...runtimeArgs, ...argv], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 })",
        "if (result.stdout) writeSync(1, result.stdout);",
        "if (result.stderr) writeSync(2, result.stderr);",
        "process.exit(result.status ?? 1);",
    ]
    for fragment in required_fragments:
        if fragment not in cli_text:
            errors.append(f"generated/typescript/{package}/src/cli.mjs is missing thin runtime handoff fragment: {fragment}")
    forbidden_fragments = [
        "shell: true",
        "readFile",
        "existsSync",
        "readdir",
        "statSync",
        "JSON.stringify",
    ]
    for fragment in forbidden_fragments:
        if fragment in cli_text:
            errors.append(f"generated/typescript/{package}/src/cli.mjs contains runtime-owned behavior marker: {fragment}")
    return errors


def _validate_generated_command_projection_boundary(*, package_id: str, command: dict[str, object]) -> list[str]:
    errors: list[str] = []
    command_payload = command.get("command", {})
    command_name = (
        command_payload.get("name", "<unknown>")
        if isinstance(command_payload, dict)
        else "<unknown>"
    )
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
        errors.append("command_package_ir.json Python CLI completion finish_line must require implementation-independent artifacts and codegen-owned primitive executors")
    if current_state not in PYTHON_COMPLETION_STATES:
        errors.append(f"command_package_ir.json Python CLI completion current_state is unknown: {current_state!r}")
    if not any("runtime primitive implementation" in item for item in allowed):
        errors.append("command_package_ir.json Python CLI completion policy must allow hand-owned runtime primitive implementation")
    for required in ("command parser shape", "option and help interface semantics", "generated command dispatch selection"):
        if not any(required in item for item in must_move):
            errors.append(f"command_package_ir.json Python CLI completion policy must move {required!r} behind contracts or generation")
    if not any("generic file" in item and "json" in item.lower() and "markdown" in item.lower() for item in must_move):
        errors.append("command_package_ir.json Python CLI completion policy must move generic deterministic file/data behavior behind codegen-owned primitives")
    if not any("weak-agent-safe-adapter" in item and "full Python generated CLI completion" in item for item in proof_requirements):
        errors.append("command_package_ir.json Python CLI completion proof must distinguish adapter maturity from full generated CLI completion")
    completion_gate = policy.get("completion_gate", {})
    if isinstance(completion_gate, dict) and current_state != "full-generated-cli-complete":
        if completion_gate.get("state") == "satisfied":
            errors.append(
                "command_package_ir.json cannot mark the Python CLI completion gate satisfied while "
                f"current_state is {current_state!r}"
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
        output.path.relative_to(REPO_ROOT).as_posix()
        for output in render_workspace_command_package_outputs(ir, repo_root=REPO_ROOT)
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
        matched_categories = sorted(
            category
            for category, markers in PYTHON_MODULE_SOURCE_EXECUTABLE_MARKERS.items()
            if any(marker in text for marker in markers)
        )
        if matched_categories:
            errors.append(
                "command_package_ir.json cannot claim full Python generated CLI completion while shipped module "
                f"or product-specific command-generation source {relative_path} owns executable behavior markers: {matched_categories!r}"
            )
    existing_runtime_source = sorted(
        relative_path
        for relative_path in PYTHON_FULL_COMPLETION_BLOCKING_RUNTIME_SOURCE_PATHS
        if (REPO_ROOT / relative_path).is_file()
    )
    if existing_runtime_source:
        errors.append(
            "command_package_ir.json cannot claim full Python generated CLI completion while shipped module source "
            f"still owns generated CLI runtime/lifecycle behavior: {existing_runtime_source!r}"
        )
    runtime_imports = _generated_command_module_package_runtime_imports()
    if runtime_imports:
        errors.append(
            "command_package_ir.json cannot claim full Python generated CLI completion while generated command modules "
            f"import package-owned runtime helpers directly: {runtime_imports!r}"
        )
    generated_runtime_facade_imports = _generated_runtime_facade_package_runtime_imports()
    if generated_runtime_facade_imports:
        errors.append(
            "command_package_ir.json cannot claim full Python generated CLI completion while generated runtime facades "
            f"still delegate to package-owned runtime helpers: {generated_runtime_facade_imports!r}"
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
        "planning.list-files.report": REPO_ROOT
        / "generated"
        / "planning"
        / "python"
        / "commands"
        / "planning_list_files_report.py",
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
                    f"{path.relative_to(REPO_ROOT).as_posix()} direct generated command {operation_id} "
                    f"must not contain {fragment!r}"
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
                errors.append(
                    f"python_runtime_projection_inventory.json {relative_path} has wrong {field}: {entry.get(field)!r}"
                )
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
                "python_runtime_projection_inventory.json transitional runtime projection debt must block full completion: "
                f"{relative_path}"
            )
        if full_completion and (provenance_status != "rendered-by-command-generation" or blocking_full_completion):
            errors.append(
                "command_package_ir.json cannot claim full Python generated CLI completion while "
                f"python_runtime_projection_inventory.json tracks {relative_path} as {provenance_status!r} "
                f"with blocking_full_completion={blocking_full_completion!r}"
            )
    return errors


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
        REPO_ROOT / "packages" / "command-generation" / "src" / "command_generation",
    ]
    paths = []
    for root in roots:
        if not root.is_dir():
            continue
        paths.extend(path.relative_to(REPO_ROOT).as_posix() for path in root.rglob("*.py") if path.is_file())
    return sorted(paths)


def _validate_python_shipped_source_executable_retirement() -> list[str]:
    errors: list[str] = []
    tracked_sources = _tracked_python_source_files()
    for relative_path in tracked_sources:
        is_shipped_module_source = relative_path.startswith(PYTHON_SHIPPED_MODULE_SOURCE_ROOTS)
        is_product_command_generation_source = relative_path.startswith("packages/command-generation/src/command_generation/") and relative_path.endswith(
            PYTHON_PRODUCT_RUNTIME_SOURCE_PATTERNS
        )
        if not is_shipped_module_source and not is_product_command_generation_source:
            continue
        path = REPO_ROOT / relative_path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        matched_categories = sorted(
            category
            for category, markers in PYTHON_MODULE_SOURCE_EXECUTABLE_MARKERS.items()
            if any(marker in text for marker in markers)
        )
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
                    f"python_operation_execution_inventory.json {operation_id} domain runtime IR entry "
                    "must explain runtime_boundary_reason"
                )
            for field in ("what_would_make_portable_later", "generic_behavior_audit"):
                if not str(entry.get(field, "")).strip():
                    errors.append(
                        f"python_operation_execution_inventory.json {operation_id} domain runtime IR entry "
                        f"must include {field}"
                    )
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
                        f"python_operation_execution_inventory.json {operation_id} accepted hand-owned runtime entry "
                        f"must include {field}"
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
    }
    portable_primitive_operations = {"memory.list-files.report", "memory.list-skills.report", "planning.list-files.report"}
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
            "portable-codegen-primitive-executed"
            if operation_id in portable_primitive_operations
            else "domain-runtime-primitive-via-ir"
        )
        if entry.get("status") != expected_status:
            errors.append(f"{operation_id} must be marked {expected_status} in python_operation_execution_inventory.json")
        expected_primitive_executor = expected_primitive_executors.get(
            operation_id,
            "packages/command-generation/src/command_generation/primitive_executor.py",
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

    memory_operation_executor_text = (
        REPO_ROOT / "generated" / "memory" / "python" / "primitives" / "operation_executor.py"
    ).read_text(
        encoding="utf-8"
    )
    if "from command_generation.primitive_executor import" not in memory_operation_executor_text:
        errors.append("memory operation IR executor must import the codegen-owned primitive executor")
    if "run_operation_steps(" not in memory_operation_executor_text:
        errors.append("memory operation IR executor must execute operation plans through codegen-owned run_operation_steps")
    if "repo_memory_bootstrap._installer_paths" in memory_operation_executor_text:
        errors.append("memory operation IR executor must resolve package resources from generated target-local copies")
    for marker in (
        "generated/memory/python/_payload/AGENTS.template.md",
        "generated/memory/python/_skills/REGISTRY.json",
    ):
        if not (REPO_ROOT / marker).is_file():
            errors.append(f"memory generated Python resource copy is missing required marker: {marker}")
    for module_name in (
        "memory_doctor_report",
        "memory_promotion_report_report",
        "memory_report_report",
        "memory_route_report_report",
        "memory_status_report",
    ):
        command_text = (REPO_ROOT / "generated" / "memory" / "python" / "commands" / f"{module_name}.py").read_text(
            encoding="utf-8"
        )
        if "run_operation_ir(" not in command_text:
            errors.append(f"generated/memory/python/commands/{module_name}.py must execute operation IR through run_operation_ir")

    planning_operation_executor_text = (
        REPO_ROOT / "generated" / "planning" / "python" / "primitives" / "operation_executor.py"
    ).read_text(
        encoding="utf-8"
    )
    if "from command_generation.primitive_executor import" not in planning_operation_executor_text:
        errors.append("planning operation IR executor must import the codegen-owned primitive executor")
    if "run_operation_steps(" not in planning_operation_executor_text:
        errors.append("planning operation IR executor must execute operation plans through codegen-owned run_operation_steps")
    for module_name in ("planning_doctor_report", "planning_report_report", "planning_status_report"):
        command_text = (REPO_ROOT / "generated" / "planning" / "python" / "commands" / f"{module_name}.py").read_text(
            encoding="utf-8"
        )
        if "run_operation_ir(" not in command_text:
            errors.append(f"generated/planning/python/commands/{module_name}.py must execute operation IR through run_operation_ir")

    workspace_operation_executor_text = (
        REPO_ROOT / "generated" / "workspace" / "python" / "primitives" / "operation_executor.py"
    ).read_text(
        encoding="utf-8"
    )
    if "from command_generation.primitive_executor import" not in workspace_operation_executor_text:
        errors.append("workspace operation IR executor must import the codegen-owned primitive executor")
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
        command_text = (REPO_ROOT / "generated" / "workspace" / "python" / "commands" / f"{module_name}.py").read_text(
            encoding="utf-8"
        )
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
    for package_id in ("root-workspace", "planning-bootstrap", "memory-bootstrap"):
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


def _validate_generated_python_commands_absent_from_handwritten_parsers() -> list[str]:
    errors: list[str] = []
    for package_id in ("root-workspace", "planning-bootstrap", "memory-bootstrap"):
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
    if shutil.which("git"):
        completed = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            return [f"cannot validate generated CLI compatibility vocabulary: git ls-files failed: {completed.stderr.strip()}"]
        candidate_paths = [path.strip().replace("\\", "/") for path in completed.stdout.splitlines() if path.strip()]
    else:
        roots = (
            ".agentic-workspace",
            "docs",
            "generated",
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
                candidate_paths.extend(path.relative_to(REPO_ROOT).as_posix() for path in root_path.rglob("*") if path.is_file())
    for relative_path in sorted(candidate_paths):
        if not relative_path.endswith((".py", ".json", ".toml", ".md")):
            continue
        path = REPO_ROOT / relative_path
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if not any(token in text for token in GENERATED_CLI_COMPATIBILITY_VOCABULARY):
            continue
        reason = _generated_cli_compatibility_allowlist_reason(relative_path)
        if reason is None:
            errors.append(
                f"{relative_path} contains generated_cli_package compatibility vocabulary without an explicit allowlist reason"
            )
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
                entrypoint = _entrypoint_for_package(package_id)
                shim = temp_root / f"{package_id.replace('-', '_')}_cli_shim.py"
                shim.write_text(
                    "import sys\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'command-generation' / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'planning' / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'memory' / 'src')!r})\n"
                    "from command_generation.console import main_for_entrypoint\n"
                    f"raise SystemExit(main_for_entrypoint({entrypoint!r}, sys.argv[1:]))\n",
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
                    "adapter conformance failed before execution: "
                    f"{runnable_case.cli.relative_to(REPO_ROOT).as_posix()} is missing"
                )
                return
            case = runnable_case.case
            fixture_root = materialize_fixture(case)
            runtime = runtime_for_package(runnable_case.package_id)
            canonical_process = _capture(
                [python, str(shims[runnable_case.package_id]), *case.success_args],
                cwd=fixture_root,
                env=_conformance_env(),
            )
            if canonical_process.returncode != case.expected_exit:
                errors.append(
                    f"runtime primitive failure: canonical {runnable_case.package_id} {case.label} command exited "
                    f"{canonical_process.returncode}, expected {case.expected_exit}; "
                    f"stderr={canonical_process.stderr!r}"
                )
                return
            if canonical_process.stderr.strip() and not case.allow_stderr:
                errors.append(
                    f"runtime primitive failure: canonical {runnable_case.package_id} {case.label} emitted unexpected stderr: "
                    f"{canonical_process.stderr!r}"
                )
                return
            try:
                canonical_selected = case.selected_fields(canonical_process.stdout)
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"runtime primitive failure: canonical {runnable_case.package_id} {case.label} stdout did not satisfy selected fields: {exc}")
                return
            if case.expected_fields is not None and canonical_selected != case.expected_fields:
                errors.append(
                    f"runtime primitive failure: canonical {runnable_case.package_id} {case.label} output shape drifted; "
                    f"expected selected fields {case.expected_fields!r}, got {canonical_selected!r}"
                )
                return

            adapter_process = _capture(
                [node, str(runnable_case.cli), *case.success_args],
                cwd=fixture_root,
                env=_conformance_env(runtime=runtime),
            )
            if adapter_process.returncode != canonical_process.returncode:
                errors.append(
                    f"adapter failure: {runnable_case.package_id} {case.label} exit code drifted from canonical process; "
                    f"expected {canonical_process.returncode}, got {adapter_process.returncode}; stderr={adapter_process.stderr!r}"
                )
            else:
                try:
                    adapter_selected = case.selected_fields(adapter_process.stdout)
                except (KeyError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(
                        f"adapter failure: {runnable_case.package_id} {case.label} stdout did not satisfy selected fields: {exc}; "
                        f"stdout={adapter_process.stdout!r}"
                    )
                else:
                    if adapter_selected != canonical_selected:
                        errors.append(
                            f"adapter failure: {runnable_case.package_id} {case.label} JSON selected fields drifted from canonical process; "
                            f"expected {canonical_selected!r}, got {adapter_selected!r}"
                        )
            if adapter_process.stderr.strip() and not case.allow_stderr:
                errors.append(
                    f"adapter failure: {runnable_case.package_id} {case.label} emitted unexpected stderr: {adapter_process.stderr!r}"
                )

            invalid_args = [*case.success_args, "--definitely-invalid"]
            canonical_invalid_process = _capture(
                [python, str(shims[runnable_case.package_id]), *invalid_args],
                cwd=fixture_root,
                env=_conformance_env(),
            )
            adapter_invalid_process = _capture(
                [node, str(runnable_case.cli), *invalid_args],
                cwd=fixture_root,
                env=_conformance_env(runtime=runtime),
            )
            if canonical_invalid_process.returncode >= 0:
                if adapter_invalid_process.returncode != canonical_invalid_process.returncode:
                    errors.append(
                        f"adapter failure: {runnable_case.package_id} {case.label} invalid-option exit code drifted from canonical process; "
                        f"expected {canonical_invalid_process.returncode}, got {adapter_invalid_process.returncode}"
                    )
                if bool(adapter_invalid_process.stderr.strip()) != bool(canonical_invalid_process.stderr.strip()):
                    errors.append(
                        f"adapter failure: {runnable_case.package_id} {case.label} invalid-option stderr presence drifted from canonical process; "
                        f"canonical={canonical_invalid_process.stderr!r}, adapter={adapter_invalid_process.stderr!r}"
                    )

        for runnable_case in derived_cases:
            compare_adapter(runnable_case)
            fixture_root = materialize_fixture(runnable_case.case)
            help_result = _capture(
                [node, str(runnable_case.cli), "--help"],
                cwd=fixture_root,
                env=_conformance_env(runtime=runtime_for_package(runnable_case.package_id)),
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
            if runnable_case.weak_agent_routing in {"allowed-read-only", "allowed-mutation-with-review"}:
                handoff_failure = _capture(
                    [node, str(runnable_case.cli), *runnable_case.case.success_args],
                    cwd=fixture_root,
                    env=_conformance_env(runtime=""),
                )
                if (
                    handoff_failure.returncode != 1
                    or "Adapter runtime handoff failed:" not in handoff_failure.stderr
                    or "Recovery:" not in handoff_failure.stderr
                ):
                    errors.append(
                        f"adapter failure: {runnable_case.package_id} weak-agent-safe runtime handoff recovery drifted; "
                        f"exit={handoff_failure.returncode}, stdout={handoff_failure.stdout!r}, stderr={handoff_failure.stderr!r}"
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
        errors.append("packages/command-generation/schemas/command_package_ir.schema.json is missing")
    if errors:
        return errors
    try:
        ir = load_workspace_command_package_ir(repo_root=REPO_ROOT)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"command-package IR validation failed: {exc}")
    else:
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
        }
        for package_id, (program, generated_root) in expected_python_promotions.items():
            package = packages.get(package_id)
            if not isinstance(package, dict):
                errors.append(f"command_package_ir.json is missing package {package_id!r}")
                continue
            python_targets = [target for target in package.get("targets", []) if isinstance(target, dict) and target.get("kind") == "python"]
            if not python_targets:
                errors.append(f"command_package_ir.json package {package_id!r} is missing a Python generated target")
                continue
            python_target = python_targets[0]
            if python_target.get("maturity_level_ref") != "mutation-capable-adapter":
                errors.append(
                    f"command_package_ir.json package {package_id!r} Python target is not mutation-capable; "
                    f"got {python_target.get('maturity_level_ref')!r}"
                )
            if python_target.get("generation_status") != "mutation-capable-adapter":
                errors.append(
                    f"command_package_ir.json package {package_id!r} Python generation_status is not mutation-capable; "
                    f"got {python_target.get('generation_status')!r}"
                )
            if package.get("program") != program:
                errors.append(f"command_package_ir.json package {package_id!r} program drifted from {program!r}")
            if python_target.get("generated_root") != generated_root:
                errors.append(
                    f"command_package_ir.json package {package_id!r} Python generated_root drifted from {generated_root!r}; "
                    f"got {python_target.get('generated_root')!r}"
                )
            if not (REPO_ROOT / generated_root / "cli.py").is_file():
                errors.append(f"{generated_root}/cli.py is missing")
            else:
                generated_text = (REPO_ROOT / generated_root / "cli.py").read_text(encoding="utf-8")
                if "json.loads(\n    r\"\"\"" in generated_text:
                    errors.append(f"{generated_root}/cli.py embeds generated JSON instead of loading resources")
                if "def generated_maturity()" not in generated_text:
                    errors.append(f"{generated_root}/cli.py is missing generated_maturity")
                if "def generated_weak_agent_routing()" not in generated_text:
                    errors.append(f"{generated_root}/cli.py is missing generated_weak_agent_routing")
                if "def generated_operation_contract(" not in generated_text:
                    errors.append(f"{generated_root}/cli.py is missing generated_operation_contract")
                if "from .commands import GENERATED_COMMAND_HANDLERS" not in generated_text:
                    errors.append(f"{generated_root}/cli.py does not route through generated command modules")
                if "_GENERATED_WEAK_AGENT_ROUTING = 'allowed-mutation-with-review'" not in generated_text:
                    errors.append(
                        f"{generated_root}/cli.py does not advertise mutation review routing"
                    )
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
                        errors.append(
                            f"{generated_root}/adapter_commands.json drifted from generated adapter projection"
                        )
            for directory_name in ("commands", "operations", "primitives"):
                if not (REPO_ROOT / generated_root / directory_name).is_dir():
                    errors.append(f"{generated_root}/{directory_name} is missing")
            if not (REPO_ROOT / generated_root / "primitives" / "operation_executor.py").is_file():
                errors.append(f"{generated_root}/primitives/operation_executor.py is missing")
        generated_entrypoints = {
            "generated/workspace/python/cli.py": "from .commands import GENERATED_COMMAND_HANDLERS",
            "generated/planning/python/cli.py": "from .commands import GENERATED_COMMAND_HANDLERS",
            "generated/memory/python/cli.py": "from .commands import GENERATED_COMMAND_HANDLERS",
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
        errors.extend(_validate_direct_generated_python_command_projection())
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
        ]
        for relative_path in forbidden_generated_entrypoints:
            if (REPO_ROOT / relative_path).exists():
                errors.append(f"{relative_path} is obsolete generated-owned source layout outside generated/python")
        conformance_cases, conformance_errors = _runnable_typescript_conformance_cases()
        errors.extend(f"static conformance coverage drift: {error}" for error in conformance_errors)
        if not conformance_errors and not conformance_cases:
            errors.append("static conformance coverage drift: no runnable TypeScript conformance cases were derived from contract artifacts")
    dockerfile = REPO_ROOT / "generated" / "typescript" / "Dockerfile"
    if not dockerfile.is_file():
        errors.append("generated/typescript/Dockerfile is missing")
    python_conformance_dockerfile = REPO_ROOT / "generated" / "python" / "Dockerfile.conformance"
    if not python_conformance_dockerfile.is_file():
        errors.append("generated/python/Dockerfile.conformance is missing")
    primitive_conformance_dockerfile = REPO_ROOT / "generated" / "python" / "Dockerfile.primitive-conformance"
    if not primitive_conformance_dockerfile.is_file():
        errors.append("generated/python/Dockerfile.primitive-conformance is missing")
    primitive_conformance_script = REPO_ROOT / "packages" / "command-generation" / "tests" / "primitive_conformance.py"
    if not primitive_conformance_script.is_file():
        errors.append("packages/command-generation/tests/primitive_conformance.py is missing")
    else:
        primitive_conformance_text = primitive_conformance_script.read_text(encoding="utf-8")
        for primitive_id in sorted(REQUIRED_PORTABLE_PRIMITIVE_CONFORMANCE):
            if primitive_id not in primitive_conformance_text:
                errors.append(f"primitive conformance is missing required primitive case: {primitive_id}")
    conformance_dockerfile = REPO_ROOT / "generated" / "typescript" / "Dockerfile.conformance"
    if not conformance_dockerfile.is_file():
        errors.append("generated/typescript/Dockerfile.conformance is missing")
    for package in ("workspace-cli", "planning-cli", "memory-cli"):
        package_root = REPO_ROOT / "generated" / "typescript" / package
        for relative in ("package.json", "src/commandPackage.ts", "test/command-package.test.mjs"):
            if not (package_root / relative).is_file():
                errors.append(f"generated/typescript/{package}/{relative} is missing")
        package_json_path = package_root / "package.json"
        if package_json_path.is_file():
            payload = json.loads(package_json_path.read_text(encoding="utf-8"))
            metadata = payload.get("agenticWorkspace", {})
            maturity = metadata.get("maturity", {})
            is_runnable = maturity.get("id") in {
                "runnable-read-only-adapter",
                "weak-agent-safe-adapter",
                "mutation-capable-adapter",
            }
            is_weak_agent_safe = maturity.get("id") == "weak-agent-safe-adapter"
            is_mutation_capable = maturity.get("id") == "mutation-capable-adapter"
            if not maturity.get("summary") or not maturity.get("promotion_requires"):
                errors.append(f"generated/typescript/{package}/package.json maturity is missing summary or promotion criteria")
            if is_runnable and not (package_root / "src" / "cli.mjs").is_file():
                errors.append(f"generated/typescript/{package}/src/cli.mjs is missing for runnable target")
            if is_runnable and "bin" not in payload:
                errors.append(f"generated/typescript/{package}/package.json is missing bin entry for runnable target")
            cli_path = package_root / "src" / "cli.mjs"
            if is_runnable and cli_path.is_file():
                cli_text = cli_path.read_text(encoding="utf-8")
                errors.extend(_validate_typescript_runtime_handoff_thinness(package=package, cli_text=cli_text))
            if is_weak_agent_safe and maturity.get("weak_agent_routing") != "allowed-read-only":
                errors.append(f"generated/typescript/{package}/package.json weak-agent-safe target is missing allowed-read-only routing")
            if is_mutation_capable and maturity.get("weak_agent_routing") != "allowed-mutation-with-review":
                errors.append(
                    f"generated/typescript/{package}/package.json mutation-capable target is missing mutation review routing"
                )
            if (
                is_runnable
                and not is_weak_agent_safe
                and not is_mutation_capable
                and maturity.get("weak_agent_routing") != "review-required"
            ):
                errors.append(f"generated/typescript/{package}/package.json runnable target is missing review-required weak-agent routing")
            if not is_runnable and (maturity.get("weak_agent_routing") != "forbidden" or maturity.get("runnable") is not False):
                errors.append(f"generated/typescript/{package}/package.json maturity does not mark proof fixture as non-runnable")
            if bool(metadata.get("fixtureOnly")) == is_runnable:
                errors.append(f"generated/typescript/{package}/package.json fixtureOnly does not match maturity runnable state")
    return errors


def _run_docker(tag: str, *, dockerfile: str, proof_label: str, require_docker: bool) -> int:
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
    return _run_docker_step(
        ["docker", "run", "--rm", tag],
        proof_label=proof_label,
        phase="docker-run",
        tag=tag,
        dockerfile=dockerfile,
    )


def _run_primitive_conformance() -> int:
    return _run([_python_executable(), "packages/command-generation/tests/primitive_conformance.py"])


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check generated command package outputs.")
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
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
            dockerfile="generated/typescript/Dockerfile",
            proof_label="generated TypeScript package Docker proof",
            require_docker=bool(args.require_docker),
        )
        if docker_status:
            return docker_status
    if args.docker_conformance:
        docker_status = _run_docker(
            f"{args.tag}-conformance",
            dockerfile="generated/typescript/Dockerfile.conformance",
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
