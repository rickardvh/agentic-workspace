from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "run_generated_command_package_proof.py"
CHECK_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_generated_command_packages.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_generated_command_package_proof", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_generated_command_packages", CHECK_SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_generated_command_package_proof_defaults_to_docker_steps() -> None:
    runner = _load_runner()

    steps = runner._proof_steps(runner.parse_args([]))

    assert [step.label for step in steps] == [
        "generated packages python docker conformance",
        "generated packages docker",
        "generated packages docker conformance",
    ]
    assert [step.args for step in steps] == [
        ["--python-docker-conformance", "--require-docker"],
        ["--docker", "--require-docker"],
        ["--docker-conformance", "--require-docker"],
    ]


def test_generated_command_package_proof_all_runs_every_step(monkeypatch, capsys) -> None:
    runner = _load_runner()
    calls = []

    def fake_run_step(step, *, timeout_seconds, failure_tail_lines):
        calls.append((step.label, step.args, timeout_seconds, failure_tail_lines))
        return 0

    monkeypatch.setattr(runner, "_run_step", fake_run_step)

    status = runner.main(["--all", "--timeout-seconds", "12", "--failure-tail-lines", "7"])

    assert status == 0
    assert calls == [
        ("generated packages static", [], 12.0, 7),
        ("generated packages python conformance", ["--python-conformance"], 12.0, 7),
        ("generated packages python docker conformance", ["--python-docker-conformance", "--require-docker"], 12.0, 7),
        ("generated packages conformance", ["--conformance", "--require-node"], 12.0, 7),
        ("generated packages docker", ["--docker", "--require-docker"], 12.0, 7),
        ("generated packages docker conformance", ["--docker-conformance", "--require-docker"], 12.0, 7),
    ]
    assert "[ok] generated command package proof (6 steps," in capsys.readouterr().out


def test_generated_typescript_conformance_cases_come_from_contract_artifacts() -> None:
    checker = _load_checker()

    cases, errors = checker._runnable_typescript_conformance_cases()

    assert errors == []
    by_ref = {case.case.conformance_ref: case.case for case in cases}
    defaults = by_ref["defaults.report.process"]
    planning_status = by_ref["planning.status.process"]
    memory_skills = by_ref["memory.list-skills.process"]

    assert defaults.success_args == ["defaults", "--section", "startup", "--format", "json"]
    assert defaults.expected_fields["answer.default_canonical_agent_instructions_file"] == "AGENTS.md"
    assert defaults.fixture_id == "minimal-repo"
    assert defaults.fixture_files["README.md"] == "# Fixture\n"
    assert planning_status.success_args == ["status", "--format", "json"]
    assert planning_status.expected_fields == {"dry_run": False}
    assert memory_skills.success_args == ["list-skills", "--format", "json"]
    assert memory_skills.expected_fields == {"mode": "skills"}


def test_generated_python_conformance_uses_contract_artifacts() -> None:
    checker = _load_checker()

    registries, errors = checker._adapter_conformance_cases_by_package()

    assert errors == []
    assert set(registries) == {"root-workspace", "planning-bootstrap", "memory-bootstrap"}
    defaults = registries["root-workspace"]["defaults.report.process"]
    planning_status = registries["planning-bootstrap"]["planning.status.process"]
    memory_skills = registries["memory-bootstrap"]["memory.list-skills.process"]

    assert checker._python_command_for_package("root-workspace")[-1] == "agentic_workspace.cli"
    assert checker._python_command_for_package("planning-bootstrap")[-1] == "repo_planning_bootstrap.cli"
    assert checker._python_command_for_package("memory-bootstrap")[-1] == "repo_memory_bootstrap.cli"
    assert defaults.success_args == ["defaults", "--section", "startup", "--format", "json"]
    assert defaults.expected_exit == 0
    assert defaults.allow_stderr is False
    assert defaults.expected_fields["answer.default_canonical_agent_instructions_file"] == "AGENTS.md"
    assert planning_status.expected_fields == {"dry_run": False}
    assert memory_skills.expected_fields == {"mode": "skills"}


def test_generated_python_conformance_classifies_native_crashes(monkeypatch) -> None:
    checker = _load_checker()
    registries, errors = checker._adapter_conformance_cases_by_package()
    assert errors == []
    monkeypatch.setenv("AGENTIC_GENERATED_CONFORMANCE_CONTAINER", "python")

    message = checker._format_generated_adapter_exit_failure(
        language="python",
        package_id="root-workspace",
        case=registries["root-workspace"]["setup.guidance.process"],
        command=["python", "shim.py"],
        returncode=-11,
        expected_exit=0,
        stderr="",
    )

    assert "classification=runtime-crash-or-proof-environment-residue" in message
    assert "proof_surface=generated-python-docker-conformance" in message
    assert "package=root-workspace" in message
    assert "conformance_ref=setup.guidance.process" in message
    assert "command=setup" in message
    assert "fixture=minimal-repo" in message
    assert "exit=-11" in message
    assert "signal 11" in message
    assert "rerun this package/case or the Docker conformance proof" in message


def test_generated_python_conformance_classifies_contract_failures() -> None:
    checker = _load_checker()
    registries, errors = checker._adapter_conformance_cases_by_package()
    assert errors == []

    message = checker._format_generated_adapter_exit_failure(
        language="python",
        package_id="root-workspace",
        case=registries["root-workspace"]["setup.guidance.process"],
        command=["python", "shim.py"],
        returncode=2,
        expected_exit=0,
        stderr="bad option",
    )

    assert "classification=adapter-contract-failure" in message
    assert "proof_surface=generated-python-adapter-conformance" in message
    assert "compare adapter output with the contract-backed runtime expectation" in message


def test_generated_python_conformance_reports_crash_retry_recovery(monkeypatch) -> None:
    checker = _load_checker()
    registries, errors = checker._adapter_conformance_cases_by_package()
    assert errors == []
    monkeypatch.setenv("AGENTIC_GENERATED_CONFORMANCE_CONTAINER", "python")

    message = checker._format_generated_adapter_retry_recovery(
        language="python",
        package_id="root-workspace",
        case=registries["root-workspace"]["doctor.report.process"],
        command=["python", "shim.py"],
        first_returncode=-11,
    )

    assert "runtime crash recovered after retry" in message
    assert "proof_surface=generated-python-docker-conformance" in message
    assert "conformance_ref=doctor.report.process" in message
    assert "first_exit=-11" in message


def test_static_generated_package_proof_fails_when_conformance_coverage_drifts(monkeypatch) -> None:
    checker = _load_checker()

    monkeypatch.setattr(checker, "_runnable_typescript_conformance_cases", lambda: ([], ["missing contract-backed case"]))

    errors = checker._validate_static_surfaces()

    assert "static conformance coverage drift: missing contract-backed case" in errors


def test_command_package_ir_records_deferred_shell_transport_evaluation() -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)

    shell_policy = ir["generation_policy"]["shell_adapter_policy"]
    root_targets = {target["kind"]: target for target in ir["packages"][0]["targets"]}

    assert "Issue #909 evaluation selects Bash as the first additional generated command transport candidate" in shell_policy
    assert "black-box conformance for runtime handoff" in shell_policy
    assert root_targets["bash"]["maturity_level_ref"] == "deferred"
    assert root_targets["powershell"]["maturity_level_ref"] == "deferred"


def test_static_generated_package_proof_rejects_python_completion_drift(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
    ir["generation_policy"]["python_cli_completion"]["current_state"] = "full-generated-cli-complete"
    monkeypatch.setattr(checker, "load_workspace_command_package_ir", lambda *, repo_root: ir)

    errors = checker._validate_static_surfaces()

    assert any("adapter-layer-proven-not-full-generated-cli" in error for error in errors)


def test_python_runtime_handler_boundary_rejects_non_adapter_handlers(monkeypatch) -> None:
    checker = _load_checker()
    memory_cli = checker.importlib.import_module("repo_memory_bootstrap.cli")
    drifted_handlers = dict(memory_cli._GENERATED_RUNTIME_HANDLERS)
    drifted_handlers["memory.status.report"] = memory_cli._handle_status
    monkeypatch.setattr(memory_cli, "_GENERATED_RUNTIME_HANDLERS", drifted_handlers)

    errors = checker._validate_python_runtime_handler_boundary()

    assert any("memory.status.report" in error and "thin _run_*_adapter binding" in error for error in errors)


def test_python_runtime_import_boundary_rejects_legacy_generated_adapter_dispatch() -> None:
    checker = _load_checker()
    errors = checker._validate_no_legacy_generated_adapter_runtime_import(
        relative_path="src/agentic_workspace/cli.py",
        text="from agentic_workspace.generated_command_adapters import GENERATED_COMMAND_ADAPTERS_BY_COMMAND\n",
    )

    assert errors == [
        "src/agentic_workspace/cli.py must route generated Python commands through generated_cli_package, "
        "not legacy generated_command_adapters runtime dispatch"
    ]


def test_python_parser_retirement_rejects_generated_command_in_handwritten_parser(monkeypatch) -> None:
    checker = _load_checker()
    root_cli = checker.importlib.import_module("agentic_workspace.cli")

    def build_drifted_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        subparsers.add_parser("defaults")
        return parser

    monkeypatch.setattr(root_cli, "build_parser", build_drifted_parser)

    errors = checker._validate_generated_python_commands_absent_from_handwritten_parsers()

    assert any("handwritten parser still accepts generated command 'defaults'" in error for error in errors)


def test_typescript_runtime_handoff_thinness_rejects_runtime_owned_behavior() -> None:
    checker = _load_checker()
    cli_text = "\n".join(
        [
            "import { spawnSync } from 'node:child_process';",
            "import { readFileSync, writeSync } from 'node:fs';",
            "function splitRuntimeCommand(commandLine) { return [commandLine]; }",
            "const [runtimeExecutable, ...runtimeArgs] = splitRuntimeCommand(runtimeCommand);",
            "result = spawnSync(runtimeExecutable, [...runtimeArgs, ...argv], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });",
            "JSON.stringify(readFileSync('AGENTS.md'));",
        ]
    )

    errors = checker._validate_typescript_runtime_handoff_thinness(package="workspace-cli", cli_text=cli_text)

    assert any("imports runtime-owned modules" in error for error in errors)
    assert any("runtime-owned behavior marker: readFile" in error for error in errors)
    assert any("runtime-owned behavior marker: JSON.stringify" in error for error in errors)


def test_generated_command_projection_boundary_rejects_target_owned_runtime_behavior() -> None:
    checker = _load_checker()
    command = {
        "status": "generated",
        "command": {"name": "report"},
        "conformance_refs": [],
        "projection_boundary": {
            "universal": ["command identity", "operation reference", "effect hints"],
            "target_specific": ["parser library", "payload assembly"],
            "runtime_owned": ["output emission"],
        },
    }

    errors = checker._validate_generated_command_projection_boundary(package_id="root-workspace", command=command)

    assert any("must declare at least one conformance ref" in error for error in errors)
    assert any("runtime primitive reference" in error for error in errors)
    assert any("conformance refs" in error for error in errors)
    assert any("package entrypoint wiring" in error for error in errors)
    assert any("runtime-owned term 'payload assembly'" in error for error in errors)
