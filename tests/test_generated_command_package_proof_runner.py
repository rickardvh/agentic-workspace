from __future__ import annotations

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
        "generated packages docker",
        "generated packages docker conformance",
    ]
    assert [step.args for step in steps] == [
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
        ("generated packages conformance", ["--conformance", "--require-node"], 12.0, 7),
        ("generated packages docker", ["--docker", "--require-docker"], 12.0, 7),
        ("generated packages docker conformance", ["--docker-conformance", "--require-docker"], 12.0, 7),
    ]
    assert "[ok] generated command package proof (4 steps," in capsys.readouterr().out


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
