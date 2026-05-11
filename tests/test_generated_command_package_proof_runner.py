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
