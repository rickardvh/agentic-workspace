from __future__ import annotations

import argparse
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

from workspace_command_generation import SCHEMA_PATH, SOURCE_PATH, load_workspace_command_package_ir  # noqa: E402

SelectedFields = Callable[[str], dict[str, object]]


class AdapterConformanceCase(NamedTuple):
    conformance_ref: str
    label: str
    success_args: list[str]
    selected_fields: SelectedFields
    expected_fields: dict[str, object] | None


class RunnableTypescriptConformanceCase(NamedTuple):
    package_id: str
    program: str
    cli: Path
    weak_agent_safe: bool
    case: AdapterConformanceCase


def _run(command: list[str]) -> int:
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return int(completed.returncode)


def _python_executable() -> str:
    return sys.executable or "python"


def _conformance_env(*, runtime: str | None = None) -> dict[str, str]:
    env = os.environ.copy()
    paths = [
        str(REPO_ROOT / "src"),
        str(REPO_ROOT / "packages" / "planning" / "src"),
        str(REPO_ROOT / "packages" / "memory" / "src"),
    ]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    if runtime is not None:
        env["AGENTIC_WORKSPACE_RUNTIME"] = runtime
    return env


def _runtime_module_for_package(package_id: str) -> str:
    modules = {
        "root-workspace": "agentic_workspace.cli",
        "planning-bootstrap": "repo_planning_bootstrap.cli",
        "memory-bootstrap": "repo_memory_bootstrap.cli",
    }
    return modules[package_id]


def _capture(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def _selected_defaults_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    return {
        "profile": payload.get("profile"),
        "surface": payload.get("surface"),
        "section": payload.get("selector", {}).get("section") if isinstance(payload.get("selector"), dict) else None,
        "matched": payload.get("matched"),
        "default_canonical_agent_instructions_file": (
            payload.get("answer", {}).get("default_canonical_agent_instructions_file") if isinstance(payload.get("answer"), dict) else None
        ),
    }


def _selected_config_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    workspace = payload.get("workspace", {}) if isinstance(payload.get("workspace"), dict) else {}
    return {
        "kind": payload.get("kind"),
        "profile": payload.get("profile"),
        "exists": payload.get("exists"),
        "agent_instructions_file": workspace.get("agent_instructions_file"),
        "improvement_latitude": workspace.get("improvement_latitude"),
        "optimization_bias": workspace.get("optimization_bias"),
    }


def _selected_modules_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    active_modules = payload.get("active_modules", [])
    return {
        "kind": payload.get("kind"),
        "profile": payload.get("profile"),
        "active_module_count": payload.get("active_module_count"),
        "active_modules": active_modules,
    }


def _selected_start_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    next_action = (
        payload.get("immediate_next_allowed_action", {})
        if isinstance(payload.get("immediate_next_allowed_action"), dict)
        else {}
    )
    proof = payload.get("proof", {}) if isinstance(payload.get("proof"), dict) else {}
    return {
        "kind": payload.get("kind"),
        "next_action": next_action.get("action"),
        "proof_kind": proof.get("kind"),
        "changed_paths": proof.get("changed_paths"),
    }


def _selected_summary_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    machine_first = payload.get("machine_first_planning", {}) if isinstance(payload.get("machine_first_planning"), dict) else {}
    execplans = payload.get("execplans", {}) if isinstance(payload.get("execplans"), dict) else {}
    return {
        "kind": payload.get("kind"),
        "profile": payload.get("profile"),
        "machine_first_status": machine_first.get("status"),
        "active_count": execplans.get("active_count"),
    }


def _selected_implement_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    proof = payload.get("proof", {}) if isinstance(payload.get("proof"), dict) else {}
    return {
        "kind": payload.get("kind"),
        "proof_kind": proof.get("kind"),
    }


def _selected_preflight_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    return {
        "kind": payload.get("kind"),
        "mode": payload.get("mode"),
    }


def _selected_proof_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    next_action = payload.get("next", {}) if isinstance(payload.get("next"), dict) else {}
    return {
        "kind": payload.get("kind"),
        "next_action": next_action.get("action"),
        "detail_command": payload.get("detail_command"),
    }


def _selected_ownership_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    return {
        "profile": payload.get("profile"),
        "surface": payload.get("surface"),
        "matched": payload.get("matched"),
    }


def _selected_skills_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    return {
        "task": payload.get("task"),
    }


def _selected_report_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    return {
        "kind": payload.get("kind"),
        "command": payload.get("command"),
    }


def _selected_reconcile_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    return {
        "kind": payload.get("kind"),
        "status": payload.get("status"),
    }


def _selected_setup_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    return {
        "kind": payload.get("kind"),
        "command": payload.get("command"),
    }


def _selected_lifecycle_report_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    return {
        "command": payload.get("command"),
        "health": payload.get("health"),
    }


def _selected_doctor_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    repair_plan = payload.get("repair_plan", {}) if isinstance(payload.get("repair_plan"), dict) else {}
    return {
        "command": payload.get("command"),
        "health": payload.get("health"),
        "repair_plan_kind": repair_plan.get("kind"),
    }


def _selected_package_result_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    status = payload.get("status")
    return {
        "kind": payload.get("kind"),
        "module": payload.get("module"),
        "message": payload.get("message"),
        "health": payload.get("health"),
        "profile": payload.get("profile"),
        "status": status if isinstance(status, str) else None,
        "status_keys": sorted(status) if isinstance(status, dict) else [],
    }


def _root_workspace_adapter_conformance_cases() -> dict[str, AdapterConformanceCase]:
    cases = [
        AdapterConformanceCase(
            conformance_ref="defaults.report.process",
            label="defaults",
            success_args=["defaults", "--section", "startup", "--format", "json"],
            selected_fields=_selected_defaults_fields,
            expected_fields={
                "profile": "compact-contract-answer/v1",
                "surface": "defaults",
                "section": "startup",
                "matched": True,
                "default_canonical_agent_instructions_file": "AGENTS.md",
            },
        ),
        AdapterConformanceCase(
            conformance_ref="config.report.process",
            label="config",
            success_args=["config", "--target", ".", "--format", "json"],
            selected_fields=_selected_config_fields,
            expected_fields={
                "kind": "agentic-workspace/config-tiny/v1",
                "profile": "tiny",
                "exists": False,
                "agent_instructions_file": "AGENTS.md",
                "improvement_latitude": "conservative",
                "optimization_bias": "balanced",
            },
        ),
        AdapterConformanceCase(
            conformance_ref="modules.report.process",
            label="modules",
            success_args=["modules", "--target", ".", "--format", "json"],
            selected_fields=_selected_modules_fields,
            expected_fields={
                "kind": "agentic-workspace/modules-router/v1",
                "profile": "tiny",
                "active_module_count": 0,
                "active_modules": [],
            },
        ),
        AdapterConformanceCase(
            conformance_ref="start.context.process",
            label="start",
            success_args=["start", "--target", ".", "--changed", "README.md", "--format", "json"],
            selected_fields=_selected_start_fields,
            expected_fields={
                "kind": "startup-context/v1",
                "next_action": "choose-smallest-workflow-shape",
                "proof_kind": "proof-selection/v1",
                "changed_paths": ["README.md"],
            },
        ),
        AdapterConformanceCase(
            conformance_ref="summary.report.process",
            label="summary",
            success_args=["summary", "--target", ".", "--profile", "compact", "--format", "json"],
            selected_fields=_selected_summary_fields,
            expected_fields={
                "kind": "planning-summary/v1",
                "profile": "compact",
                "machine_first_status": "no-active-execplan",
                "active_count": 0,
            },
        ),
        AdapterConformanceCase(
            conformance_ref="implement.context.process",
            label="implement",
            success_args=["implement", "--target", ".", "--changed", "README.md", "--task", "generated-adapter-proof", "--format", "json"],
            selected_fields=_selected_implement_fields,
            expected_fields={
                "kind": "implementer-context-tiny/v1",
                "proof_kind": "proof-selection/v1",
            },
        ),
        AdapterConformanceCase(
            conformance_ref="preflight.report.process",
            label="preflight",
            success_args=["preflight", "--target", ".", "--active-only", "--format", "json"],
            selected_fields=_selected_preflight_fields,
            expected_fields={
                "kind": "preflight-response/v1",
                "mode": "active-state-only",
            },
        ),
        AdapterConformanceCase(
            conformance_ref="proof.report.process",
            label="proof",
            success_args=["proof", "--target", ".", "--changed", "README.md", "--format", "json"],
            selected_fields=_selected_proof_fields,
            expected_fields={
                "kind": "proof-next-decision/v1",
                "next_action": "run-validation-command",
                "detail_command": "agentic-workspace proof --verbose --changed <paths> --format json",
            },
        ),
        AdapterConformanceCase(
            conformance_ref="ownership.report.process",
            label="ownership",
            success_args=["ownership", "--target", ".", "--concern", "startup", "--format", "json"],
            selected_fields=_selected_ownership_fields,
            expected_fields={
                "profile": "compact-contract-answer/v1",
                "surface": "ownership",
                "matched": False,
            },
        ),
        AdapterConformanceCase(
            conformance_ref="skills.report.process",
            label="skills",
            success_args=["skills", "--target", ".", "--task", "proof", "--format", "json"],
            selected_fields=_selected_skills_fields,
            expected_fields={
                "task": "proof",
            },
        ),
        AdapterConformanceCase(
            conformance_ref="report.combined.process",
            label="report",
            success_args=["report", "--target", ".", "--profile", "router", "--format", "json"],
            selected_fields=_selected_report_fields,
            expected_fields={
                "kind": "workspace-report-router/v1",
                "command": "report",
            },
        ),
        AdapterConformanceCase(
            conformance_ref="reconcile.report.process",
            label="reconcile",
            success_args=["reconcile", "--target", ".", "--format", "json"],
            selected_fields=_selected_reconcile_fields,
            expected_fields={
                "kind": "planning-reconcile/v1",
                "status": "clean",
            },
        ),
        AdapterConformanceCase(
            conformance_ref="setup.guidance.process",
            label="setup",
            success_args=["setup", "--target", ".", "--modules", "planning", "--format", "json"],
            selected_fields=_selected_setup_fields,
            expected_fields={
                "kind": "workspace-setup/v1",
                "command": "setup",
            },
        ),
        AdapterConformanceCase(
            conformance_ref="status.report.process",
            label="status",
            success_args=["status", "--target", ".", "--modules", "planning", "--format", "json"],
            selected_fields=_selected_lifecycle_report_fields,
            expected_fields={
                "command": "status",
                "health": "attention-needed",
            },
        ),
        AdapterConformanceCase(
            conformance_ref="doctor.report.process",
            label="doctor",
            success_args=["doctor", "--target", ".", "--modules", "planning", "--format", "json"],
            selected_fields=_selected_doctor_fields,
            expected_fields={
                "command": "doctor",
                "health": "attention-needed",
                "repair_plan_kind": "workspace-repair-plan/v1",
            },
        ),
    ]
    return {case.conformance_ref: case for case in cases}


def _planning_adapter_conformance_cases() -> dict[str, AdapterConformanceCase]:
    cases = [
        AdapterConformanceCase(
            conformance_ref="planning.status.process",
            label="planning status",
            success_args=["status", "--target", ".", "--format", "json"],
            selected_fields=_selected_package_result_fields,
            expected_fields=None,
        ),
        AdapterConformanceCase(
            conformance_ref="planning.doctor.process",
            label="planning doctor",
            success_args=["doctor", "--target", ".", "--format", "json"],
            selected_fields=_selected_package_result_fields,
            expected_fields=None,
        ),
        AdapterConformanceCase(
            conformance_ref="planning.summary.process",
            label="planning summary",
            success_args=["summary", "--target", ".", "--profile", "compact", "--format", "json"],
            selected_fields=_selected_summary_fields,
            expected_fields=None,
        ),
        AdapterConformanceCase(
            conformance_ref="planning.report.process",
            label="planning report",
            success_args=["report", "--target", ".", "--format", "json"],
            selected_fields=_selected_package_result_fields,
            expected_fields=None,
        ),
        AdapterConformanceCase(
            conformance_ref="planning.reconcile.process",
            label="planning reconcile",
            success_args=["reconcile", "--target", ".", "--format", "json"],
            selected_fields=_selected_reconcile_fields,
            expected_fields=None,
        ),
    ]
    return {case.conformance_ref: case for case in cases}


def _memory_adapter_conformance_cases() -> dict[str, AdapterConformanceCase]:
    cases = [
        AdapterConformanceCase(
            conformance_ref="memory.status.process",
            label="memory status",
            success_args=["status", "--target", ".", "--format", "json"],
            selected_fields=_selected_package_result_fields,
            expected_fields=None,
        ),
        AdapterConformanceCase(
            conformance_ref="memory.doctor.process",
            label="memory doctor",
            success_args=["doctor", "--target", ".", "--format", "json"],
            selected_fields=_selected_package_result_fields,
            expected_fields=None,
        ),
        AdapterConformanceCase(
            conformance_ref="memory.report.process",
            label="memory report",
            success_args=["report", "--target", ".", "--format", "json"],
            selected_fields=_selected_package_result_fields,
            expected_fields=None,
        ),
        AdapterConformanceCase(
            conformance_ref="memory.route-report.process",
            label="memory route-report",
            success_args=["route-report", "--target", ".", "--format", "json"],
            selected_fields=_selected_package_result_fields,
            expected_fields=None,
        ),
        AdapterConformanceCase(
            conformance_ref="memory.promotion-report.process",
            label="memory promotion-report",
            success_args=["promotion-report", "--target", ".", "--format", "json"],
            selected_fields=_selected_package_result_fields,
            expected_fields=None,
        ),
        AdapterConformanceCase(
            conformance_ref="memory.list-files.process",
            label="memory list-files",
            success_args=["list-files", "--target", ".", "--format", "json"],
            selected_fields=_selected_package_result_fields,
            expected_fields=None,
        ),
        AdapterConformanceCase(
            conformance_ref="memory.list-skills.process",
            label="memory list-skills",
            success_args=["list-skills", "--format", "json"],
            selected_fields=_selected_package_result_fields,
            expected_fields=None,
        ),
    ]
    return {case.conformance_ref: case for case in cases}


def _adapter_conformance_cases_by_package() -> dict[str, dict[str, AdapterConformanceCase]]:
    return {
        "root-workspace": _root_workspace_adapter_conformance_cases(),
        "planning-bootstrap": _planning_adapter_conformance_cases(),
        "memory-bootstrap": _memory_adapter_conformance_cases(),
    }


def _runnable_typescript_conformance_cases() -> tuple[list[RunnableTypescriptConformanceCase], list[str]]:
    try:
        ir = load_workspace_command_package_ir(repo_root=REPO_ROOT)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [], [f"adapter conformance failed before execution: command-package IR validation failed: {exc}"]

    registries = _adapter_conformance_cases_by_package()
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
            and target.get("maturity_level_ref") in {"runnable-read-only-adapter", "weak-agent-safe-adapter"}
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
                        weak_agent_safe=target.get("maturity_level_ref") == "weak-agent-safe-adapter",
                        case=case,
                    )
                )
    return selected, errors


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
        fixture_root = temp_root / "minimal-repo"
        (fixture_root / ".git").mkdir(parents=True)
        (fixture_root / ".git" / ".keep").write_text("", encoding="utf-8")
        (fixture_root / "README.md").write_text("# Fixture\n", encoding="utf-8")

        derived_cases, derived_errors = _runnable_typescript_conformance_cases()
        if derived_errors:
            return derived_errors

        shims: dict[str, Path] = {}

        def runtime_for_package(package_id: str) -> str:
            shim = shims.get(package_id)
            if shim is None:
                module = _runtime_module_for_package(package_id)
                shim = temp_root / f"{package_id.replace('-', '_')}_cli_shim.py"
                shim.write_text(
                    "import sys\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'planning' / 'src')!r})\n"
                    f"sys.path.insert(0, {str(REPO_ROOT / 'packages' / 'memory' / 'src')!r})\n"
                    f"from {module} import main\n"
                    "raise SystemExit(main(sys.argv[1:]))\n",
                    encoding="utf-8",
                )
                shims[package_id] = shim
            return f'"{python}" "{shim}"'

        def compare_adapter(runnable_case: RunnableTypescriptConformanceCase) -> None:
            if not runnable_case.cli.is_file():
                errors.append(
                    "adapter conformance failed before execution: "
                    f"{runnable_case.cli.relative_to(REPO_ROOT).as_posix()} is missing"
                )
                return
            case = runnable_case.case
            runtime = runtime_for_package(runnable_case.package_id)
            canonical_process = _capture(
                [python, str(shims[runnable_case.package_id]), *case.success_args],
                cwd=fixture_root,
                env=_conformance_env(),
            )
            if canonical_process.returncode != 0:
                errors.append(
                    f"runtime primitive failure: canonical {runnable_case.package_id} {case.label} command exited "
                    f"{canonical_process.returncode}; "
                    f"stderr={canonical_process.stderr!r}"
                )
                return
            try:
                canonical_selected = case.selected_fields(canonical_process.stdout)
            except json.JSONDecodeError as exc:
                errors.append(f"runtime primitive failure: canonical {runnable_case.package_id} {case.label} stdout was not JSON: {exc}")
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
                except json.JSONDecodeError as exc:
                    errors.append(
                        f"adapter failure: {runnable_case.package_id} {case.label} stdout was not JSON: {exc}; "
                        f"stdout={adapter_process.stdout!r}"
                    )
                else:
                    if adapter_selected != canonical_selected:
                        errors.append(
                            f"adapter failure: {runnable_case.package_id} {case.label} JSON selected fields drifted from canonical process; "
                            f"expected {canonical_selected!r}, got {adapter_selected!r}"
                        )
            if adapter_process.stderr.strip():
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
            help_result = _capture(
                [node, str(runnable_case.cli), "--help"],
                cwd=fixture_root,
                env=_conformance_env(runtime=runtime_for_package(runnable_case.package_id)),
            )
            expected_routing = "allowed-read-only" if runnable_case.weak_agent_safe else "review-required"
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
            if runnable_case.weak_agent_safe:
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
        maturity_policy = ir.get("generation_policy", {}).get("generated_package_maturity", {})
        level_ids = {level.get("id") for level in maturity_policy.get("levels", []) if isinstance(level, dict)}
        missing = expected_levels - level_ids
        if missing:
            errors.append(f"command_package_ir.json missing generated package maturity levels: {sorted(missing)!r}")
        routing_rule = str(maturity_policy.get("routing_rule", ""))
        if "Weak agents may use only generated targets" not in routing_rule:
            errors.append("command_package_ir.json maturity routing rule does not protect weak-agent routing")
        packages = {package.get("id"): package for package in ir.get("packages", []) if isinstance(package, dict)}
        expected_python_promotions = {
            "root-workspace": ("agentic-workspace", "generated/python/workspace-cli"),
            "planning-bootstrap": ("agentic-planning", "generated/python/planning-cli"),
            "memory-bootstrap": ("agentic-memory", "generated/python/memory-cli"),
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
            if python_target.get("maturity_level_ref") != "runtime-backed-read-only-adapter":
                errors.append(
                    f"command_package_ir.json package {package_id!r} Python target is not runtime-backed; "
                    f"got {python_target.get('maturity_level_ref')!r}"
                )
            if python_target.get("generation_status") != "runtime-backed-read-only-adapter":
                errors.append(
                    f"command_package_ir.json package {package_id!r} Python generation_status is not runtime-backed; "
                    f"got {python_target.get('generation_status')!r}"
                )
            if package.get("program") != program:
                errors.append(f"command_package_ir.json package {package_id!r} program drifted from {program!r}")
            if python_target.get("generated_root") != generated_root:
                errors.append(
                    f"command_package_ir.json package {package_id!r} Python generated_root drifted from {generated_root!r}; "
                    f"got {python_target.get('generated_root')!r}"
                )
            if not (REPO_ROOT / generated_root / "generated_cli_package" / "__init__.py").is_file():
                errors.append(f"{generated_root}/generated_cli_package/__init__.py is missing")
        generated_entrypoints = {
            "src/agentic_workspace/cli.py": "agentic_workspace.generated_cli_package",
            "packages/planning/src/repo_planning_bootstrap/cli.py": "repo_planning_bootstrap.generated_cli_package",
            "packages/memory/src/repo_memory_bootstrap/cli.py": "repo_memory_bootstrap.generated_cli_package",
        }
        for relative_path, import_name in generated_entrypoints.items():
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            main_index = text.find("def main(")
            generated_index = text.find("_run_generated_cli_package_if_supported", main_index)
            parser_index = text.find("build_parser()", main_index)
            if import_name not in text:
                errors.append(f"{relative_path} does not import the generated Python CLI package")
            if main_index == -1 or generated_index == -1 or parser_index == -1 or generated_index > parser_index:
                errors.append(f"{relative_path} does not route generated Python adapters before the handwritten parser")
        durable_source_roots = {
            "src/agentic_workspace/generated_cli_package/__init__.py": "generated/python/workspace-cli",
            "packages/planning/src/repo_planning_bootstrap/generated_cli_package/__init__.py": "generated/python/planning-cli",
            "packages/memory/src/repo_memory_bootstrap/generated_cli_package/__init__.py": "generated/python/memory-cli",
        }
        for relative_path, generated_root in durable_source_roots.items():
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            if "Generated runtime-backed Python command adapter" in text or "DO NOT EDIT DIRECTLY." in text:
                errors.append(f"{relative_path} still contains durable generated Python output instead of package-local glue")
            if generated_root not in text:
                errors.append(f"{relative_path} does not bridge to {generated_root}")
    dockerfile = REPO_ROOT / "generated" / "typescript" / "Dockerfile"
    if not dockerfile.is_file():
        errors.append("generated/typescript/Dockerfile is missing")
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
            is_runnable = maturity.get("id") in {"runnable-read-only-adapter", "weak-agent-safe-adapter"}
            is_weak_agent_safe = maturity.get("id") == "weak-agent-safe-adapter"
            if not maturity.get("summary") or not maturity.get("promotion_requires"):
                errors.append(f"generated/typescript/{package}/package.json maturity is missing summary or promotion criteria")
            if is_runnable and not (package_root / "src" / "cli.mjs").is_file():
                errors.append(f"generated/typescript/{package}/src/cli.mjs is missing for runnable target")
            if is_runnable and "bin" not in payload:
                errors.append(f"generated/typescript/{package}/package.json is missing bin entry for runnable target")
            if is_weak_agent_safe and maturity.get("weak_agent_routing") != "allowed-read-only":
                errors.append(f"generated/typescript/{package}/package.json weak-agent-safe target is missing allowed-read-only routing")
            if is_runnable and not is_weak_agent_safe and maturity.get("weak_agent_routing") != "review-required":
                errors.append(f"generated/typescript/{package}/package.json runnable target is missing review-required weak-agent routing")
            if not is_runnable and (maturity.get("weak_agent_routing") != "forbidden" or maturity.get("runnable") is not False):
                errors.append(f"generated/typescript/{package}/package.json maturity does not mark proof fixture as non-runnable")
            if bool(metadata.get("fixtureOnly")) == is_runnable:
                errors.append(f"generated/typescript/{package}/package.json fixtureOnly does not match maturity runnable state")
    return errors


def _run_docker(tag: str, *, dockerfile: str, require_docker: bool) -> int:
    if shutil.which("docker") is None:
        print("docker is not available; cannot run generated TypeScript package container proof")
        return 1 if require_docker else 0
    info = subprocess.run(["docker", "info"], cwd=REPO_ROOT, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if info.returncode:
        detail = info.stderr.strip().splitlines()
        suffix = f": {detail[0]}" if detail else ""
        print(f"docker daemon is not available; skipped generated TypeScript package container proof{suffix}")
        return 1 if require_docker else 0
    build = _run(["docker", "build", "-f", dockerfile, "-t", tag, "."])
    if build:
        return build
    return _run(["docker", "run", "--rm", tag])


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
    if args.conformance:
        conformance_errors = _run_adapter_conformance(require_node=bool(args.require_node))
        if conformance_errors:
            for error in conformance_errors:
                print(error)
            return 1
        print("[ok] generated command package adapter conformance")
        print("[ok] weak-agent-safe generated adapter routing checks passed")
    docker_status = 0
    if args.docker:
        docker_status = _run_docker(
            str(args.tag),
            dockerfile="generated/typescript/Dockerfile",
            require_docker=bool(args.require_docker),
        )
        if docker_status:
            return docker_status
    if args.docker_conformance:
        docker_status = _run_docker(
            f"{args.tag}-conformance",
            dockerfile="generated/typescript/Dockerfile.conformance",
            require_docker=bool(args.require_docker),
        )
        if docker_status:
            return docker_status
    if args.docker or args.docker_conformance:
        print("[ok] generated command package Docker proof")
        return 0
    print("[ok] generated command package static proof")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
