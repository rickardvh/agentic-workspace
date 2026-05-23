from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import subprocess
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
        "generated packages primitive docker conformance",
        "generated packages docker",
        "generated packages docker conformance",
    ]
    assert [step.args for step in steps] == [
        ["--python-docker-conformance", "--require-docker"],
        ["--primitive-docker-conformance", "--require-docker"],
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
        ("generated packages primitive conformance", ["--primitive-conformance"], 12.0, 7),
        ("generated packages primitive docker conformance", ["--primitive-docker-conformance", "--require-docker"], 12.0, 7),
        ("generated packages conformance", ["--conformance", "--require-node"], 12.0, 7),
        ("generated packages docker", ["--docker", "--require-docker"], 12.0, 7),
        ("generated packages docker conformance", ["--docker-conformance", "--require-docker"], 12.0, 7),
    ]
    assert "[ok] generated command package proof (8 steps," in capsys.readouterr().out


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

    assert "main_for_entrypoint('agentic-workspace'" in checker._python_command_for_package("root-workspace")[-1]
    assert "main_for_entrypoint('agentic-planning'" in checker._python_command_for_package("planning-bootstrap")[-1]
    assert "main_for_entrypoint('agentic-memory'" in checker._python_command_for_package("memory-bootstrap")[-1]
    assert defaults.success_args == ["defaults", "--section", "startup", "--format", "json"]
    assert defaults.expected_exit == 0
    assert defaults.allow_stderr is False
    assert defaults.expected_fields["answer.default_canonical_agent_instructions_file"] == "AGENTS.md"
    assert planning_status.expected_fields == {"dry_run": False}
    assert memory_skills.expected_fields == {"mode": "skills"}


def test_full_python_completion_rejects_whole_file_runtime_boundary_acceptance(monkeypatch) -> None:
    checker = _load_checker()
    ir = copy.deepcopy(checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT))
    ir["generation_policy"]["python_cli_completion"]["current_state"] = "full-generated-cli-complete"
    ir["generation_policy"]["python_cli_completion"]["completion_gate"]["state"] = "satisfied"
    original_manifest = checker.python_runtime_projection_inventory_manifest

    def fake_manifest() -> dict[str, object]:
        payload = copy.deepcopy(original_manifest())
        payload["accepted_runtime_boundaries"]["entries"] = [
            {
                "path": "src/agentic_workspace/workspace_runtime_primitives.py",
                "boundary_kind": "package-runtime-source",
                "runtime_boundary_class": "package-specific-judgment",
                "status": "accepted-permanent-package-domain-boundary",
            }
        ]
        return payload

    monkeypatch.setattr(checker, "python_runtime_projection_inventory_manifest", fake_manifest)

    errors = checker._validate_full_python_completion_executable_ownership(ir)

    assert any("whole-file runtime boundary acceptance" in error for error in errors)
    assert any("unaccepted package-domain runtime/lifecycle source is still present" in error for error in errors)
    assert any("generated runtime facades still bridge to unaccepted package-owned runtime helpers" in error for error in errors)


def test_full_python_completion_rejects_wrong_operation_function_call_metadata(monkeypatch) -> None:
    checker = _load_checker()
    inventory = copy.deepcopy(checker.python_runtime_projection_inventory_manifest())
    entry = next(item for item in inventory["accepted_runtime_boundaries"]["entries"] if item["binding_kind"] == "operation-function-call")
    entry["operation_ids"] = ["wrong.operation"]
    monkeypatch.setattr(checker, "python_runtime_projection_inventory_manifest", lambda: inventory)

    errors = checker._validate_python_completion_accepted_runtime_boundaries()[0]

    assert any("must declare operation_ids" in error for error in errors)


def test_full_python_completion_rejects_weak_output_boundary_audit(monkeypatch) -> None:
    checker = _load_checker()
    inventory = copy.deepcopy(checker.python_runtime_projection_inventory_manifest())
    entry = next(
        item for item in inventory["accepted_runtime_boundaries"]["entries"] if item.get("source_symbol") == "_emit_memory_operation_output"
    )
    entry["runtime_boundary_class"] = "mutation-orchestration"
    entry["why_not_generic_deterministic"] = "package output"
    entry["generic_behavior_audit"] = "package output"
    monkeypatch.setattr(checker, "python_runtime_projection_inventory_manifest", lambda: inventory)

    errors = checker._validate_python_completion_accepted_runtime_boundaries()[0]

    assert any("output-emission boundary must use runtime_boundary_class='package-specific-judgment'" in error for error in errors)
    assert any("output-emission boundary must explain the remaining package-specific output judgment" in error for error in errors)
    assert any("output-emission boundary audit must include 'generated-owned output coverage:'" in error for error in errors)


def test_current_python_completion_state_is_satisfied_by_exact_symbol_proof() -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)

    assert ir["generation_policy"]["python_cli_completion"]["current_state"] == "full-generated-cli-complete"
    assert ir["generation_policy"]["python_cli_completion"]["completion_gate"]["state"] == "satisfied"


def test_command_generation_extraction_readiness_is_inventory_backed() -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)

    assert checker._validate_command_generation_extraction_readiness(ir) == []


def test_command_generation_extraction_readiness_rejects_uninventoried_product_literals() -> None:
    checker = _load_checker()
    ir = copy.deepcopy(checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT))
    ir["generation_policy"]["extraction_readiness"]["accepted_couplings"] = []

    errors = checker._validate_command_generation_extraction_readiness(ir)

    assert any("product-specific literals without extraction-readiness inventory" in error for error in errors)


def test_generated_python_version_output_is_contract_backed() -> None:
    checker = _load_checker()
    root = checker.REPO_ROOT
    generated_roots = [
        root / "generated" / "workspace" / "python",
        root / "generated" / "planning" / "python",
        root / "generated" / "memory" / "python",
    ]

    for generated_root in generated_roots:
        cli_text = (generated_root / "cli.py").read_text(encoding="utf-8")
        package_payload = json.loads((generated_root / "command_package.json").read_text(encoding="utf-8"))
        assert "0.0.0-generated" not in cli_text
        assert "def generated_package_version()" in cli_text
        assert "package_version(distribution)" in cli_text
        assert package_payload["version_metadata"]["source"] == "python-package-metadata"


def test_python_completion_blocker_report_accepts_exact_symbol_runtime_boundaries() -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)

    report = checker._python_completion_blockers_report(ir)

    assert report["kind"] == "python-completion-blockers/v1"
    assert report["current_state"] == "full-generated-cli-complete"
    assert report["completion_gate_state"] == "satisfied"
    assert report["completion_claim_allowed"] is True
    assert report["false_completion_claim_would_fail"] is False
    assert report["blockers"] == []
    assert report["remaining_scope"] == "none"
    runtime_metrics = report["accepted_runtime_boundary_metrics"]
    assert runtime_metrics["status"] == "available"
    assert runtime_metrics["accepted_runtime_symbol_count"] == sum(runtime_metrics["accepted_runtime_symbol_count_by_package"].values())
    assert runtime_metrics["accepted_runtime_symbol_count"] == sum(runtime_metrics["accepted_runtime_symbol_count_by_class"].values())
    assert runtime_metrics["python_bridge_step_count"] == 0
    assert runtime_metrics["python_bridge_symbols"] == []
    assert runtime_metrics["generic_debt_symbol_count"] == 0
    assert runtime_metrics["baseline_symbol_count"] == runtime_metrics["accepted_runtime_symbol_count"]
    assert runtime_metrics["new_symbols_since_baseline"] == [
        "operation-function-call|generated/memory/python/operations/memory.search.report.json|memory.search.report|"
        "repo_memory_bootstrap.runtime_search|search_memory"
    ]
    assert runtime_metrics["removed_symbols_since_baseline"] == [
        "operation-function-call|generated/memory/python/operations/memory.search.report.json|memory.search.report|"
        "repo_memory_bootstrap.installer|search_memory"
    ]
    lifecycle_metrics = report["lifecycle_dry_run_metrics"]
    assert lifecycle_metrics["status"] == "available"
    assert lifecycle_metrics["codegen_default_dry_run_operation_count"] >= 3
    assert "memory.install.lifecycle" in {
        operation["operation_id"] for operation in lifecycle_metrics["codegen_default_dry_run_operations"]
    }


def test_lifecycle_dry_run_generation_regression_is_blocked(monkeypatch) -> None:
    checker = _load_checker()
    inventory = copy.deepcopy(checker.python_runtime_projection_inventory_manifest())
    entry = next(
        item for item in inventory["accepted_runtime_boundaries"]["entries"] if item.get("operation_id") == "memory.install.lifecycle"
    )
    entry["operation_path"] = "generated/planning/python/operations/planning.install.lifecycle.json"
    monkeypatch.setattr(checker, "python_runtime_projection_inventory_manifest", lambda: inventory)

    errors = checker._validate_lifecycle_dry_run_generation()

    assert any("does not route the default dry-run branch through payload.lifecycle-plan" in error for error in errors)


def test_runtime_budget_metrics_compare_against_recorded_baseline(monkeypatch) -> None:
    checker = _load_checker()
    inventory = copy.deepcopy(checker.python_runtime_projection_inventory_manifest())
    accepted = inventory["accepted_runtime_boundaries"]
    current_symbols = [checker._accepted_runtime_symbol_id(entry) for entry in accepted["entries"] if isinstance(entry, dict)]
    accepted["baseline_symbols"] = current_symbols[:-1] + [
        "operation-function-call|generated/memory/python/operations/retired.report.json|retired.report|"
        "repo_memory_bootstrap.installer|retired_runtime_symbol"
    ]
    monkeypatch.setattr(checker, "python_runtime_projection_inventory_manifest", lambda: inventory)

    runtime_metrics = checker._python_runtime_boundary_metrics()

    assert runtime_metrics["new_symbols_since_baseline"] == [current_symbols[-1]]
    assert runtime_metrics["removed_symbols_since_baseline"] == [
        "operation-function-call|generated/memory/python/operations/retired.report.json|retired.report|"
        "repo_memory_bootstrap.installer|retired_runtime_symbol"
    ]


def test_declarative_view_specs_match_generated_operations() -> None:
    checker = _load_checker()

    assert checker._validate_declarative_view_specs() == []


def test_python_function_call_stays_out_of_portable_completion_coverage() -> None:
    checker = _load_checker()

    assert "python.function.call" not in checker.REQUIRED_PORTABLE_PRIMITIVE_CONFORMANCE


def test_python_completion_blocker_report_has_json_cli_mode(capsys) -> None:
    checker = _load_checker()

    status = checker.main(["--python-completion-blockers", "--format", "json"])

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "python-completion-blockers/v1"
    assert payload["completion_claim_allowed"] is True
    assert payload["blocker_count"] == len(payload["blockers"])
    assert payload["remaining_scope"] == "none"
    assert payload["next_owner"] == "none"
    runtime_metrics = payload["accepted_runtime_boundary_metrics"]
    assert runtime_metrics["accepted_runtime_symbol_count_by_package"]
    assert runtime_metrics["output_fallback_symbol_count"] == runtime_metrics["accepted_output_emission_symbol_count"]
    assert runtime_metrics["python_bridge_step_count"] == 0
    assert runtime_metrics["python_bridge_symbols"] == []
    assert runtime_metrics["generic_debt_symbol_count"] == 0
    assert payload["lifecycle_dry_run_metrics"]["codegen_default_dry_run_operation_count"] >= 3


def test_memory_list_commands_are_direct_generated_python_projections() -> None:
    checker = _load_checker()

    errors = checker._validate_direct_generated_python_command_projection()

    assert errors == []
    list_files = (checker.REPO_ROOT / "generated/memory/python/commands/memory_list_files_report.py").read_text(encoding="utf-8")
    list_skills = (checker.REPO_ROOT / "generated/memory/python/commands/memory_list_skills_report.py").read_text(encoding="utf-8")
    assert "packages/memory/bootstrap" not in list_files
    assert "packages/memory/skills" not in list_skills
    assert "PAYLOAD_ROOT_CANDIDATES = (('_payload', 'AGENTS.template.md'),)" in list_files
    assert "SKILLS_ROOT_CANDIDATES = (('_skills', 'REGISTRY.json'),)" in list_skills


def test_memory_status_has_no_source_runtime_status_fallback() -> None:
    checker = _load_checker()
    command_package = json.loads((checker.REPO_ROOT / "generated/memory/python/command_package.json").read_text(encoding="utf-8"))
    status_command = next(command for command in command_package["commands"] if command["adapter_id"] == "memory.status.cli")

    assert "memory.bootstrap.status.load" not in status_command["runtime_binding"]["primitive_refs"]

    operation = json.loads((checker.REPO_ROOT / "generated/memory/python/operations/memory.status.report.json").read_text(encoding="utf-8"))
    assert "memory.bootstrap.status.load" not in json.dumps(operation)

    runtime = (checker.REPO_ROOT / "generated/memory/python/primitives/memory_runtime.py").read_text(encoding="utf-8")
    executor = (checker.REPO_ROOT / "generated/memory/python/primitives/operation_executor.py").read_text(encoding="utf-8")
    assert "_load_memory_bootstrap_status" not in runtime
    assert "_handle_memory_bootstrap_status_load" not in executor


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


def test_docker_proof_environment_failure_preserves_context() -> None:
    checker = _load_checker()

    message = checker._format_docker_proof_environment_failure(
        proof_label="generated Python package Docker conformance proof",
        phase="docker-run",
        tag="generated-python-test",
        dockerfile="generated/python/Dockerfile.conformance",
        command=["docker", "run", "--rm", "generated-python-test"],
        returncode=1,
        stdout="loading jsonschema\nSystemError: attempting to create PyCFunction with class but no METH_METHOD flag\n",
        stderr="",
    )

    assert "classification=proof-environment/setup-failure" in message
    assert "proof_surface=generated Python package Docker conformance proof" in message
    assert "phase=docker-run" in message
    assert "image=generated-python-test" in message
    assert "dockerfile=generated/python/Dockerfile.conformance" in message
    assert "command=['docker', 'run', '--rm', 'generated-python-test']" in message
    assert "attempting to create PyCFunction" in message
    assert "retry the Docker proof" in message


def test_run_docker_classifies_build_failures_before_adapter_execution(monkeypatch, capsys) -> None:
    checker = _load_checker()
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command == ["docker", "info"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command[:2] == ["docker", "build"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="jsonschema setup failed")
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.setattr(checker.shutil, "which", lambda name: "docker" if name == "docker" else None)
    monkeypatch.setattr(checker.subprocess, "run", fake_run)

    status = checker._run_docker(
        "generated-python-test",
        dockerfile="generated/python/Dockerfile.conformance",
        proof_label="generated Python package Docker conformance proof",
        require_docker=True,
    )

    captured = capsys.readouterr()
    assert status == 1
    assert ["docker", "run", "--rm", "generated-python-test"] not in calls
    assert "classification=proof-environment/setup-failure" in captured.out
    assert "phase=docker-build" in captured.out
    assert "jsonschema setup failed" in captured.err


def test_run_docker_does_not_reclassify_explicit_adapter_failures(monkeypatch, capsys) -> None:
    checker = _load_checker()

    def fake_run(command, **kwargs):
        if command == ["docker", "info"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command[:2] == ["docker", "build"]:
            return subprocess.CompletedProcess(command, 0, stdout="build ok\n", stderr="")
        if command[:2] == ["docker", "run"]:
            return subprocess.CompletedProcess(
                command,
                1,
                stdout="generated python adapter failure: classification=adapter-contract-failure; package=root-workspace\n",
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.setattr(checker.shutil, "which", lambda name: "docker" if name == "docker" else None)
    monkeypatch.setattr(checker.subprocess, "run", fake_run)

    status = checker._run_docker(
        "generated-python-test",
        dockerfile="generated/python/Dockerfile.conformance",
        proof_label="generated Python package Docker conformance proof",
        require_docker=True,
    )

    captured = capsys.readouterr()
    assert status == 1
    assert "classification=adapter-contract-failure" in captured.out
    assert "classification=proof-environment/setup-failure" not in captured.out


def test_static_generated_package_proof_fails_when_conformance_coverage_drifts(monkeypatch) -> None:
    checker = _load_checker()

    monkeypatch.setattr(checker, "_runnable_typescript_conformance_cases", lambda: ([], ["missing contract-backed case"]))

    errors = checker._validate_static_surfaces()

    assert "static conformance coverage drift: missing contract-backed case" in errors


def test_generated_operation_cli_input_proof_accepts_current_interfaces() -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)

    errors = checker._validate_generated_operation_cli_inputs(ir)

    assert errors == []


def test_generated_operation_cli_input_proof_rejects_missing_visible_option() -> None:
    checker = _load_checker()
    generated_root = checker.REPO_ROOT / "generated" / "memory" / "python"
    command_package = checker.json.loads((generated_root / "command_package.json").read_text(encoding="utf-8"))
    route_command = copy.deepcopy(
        next(command for command in command_package["commands"] if command["adapter_id"] == "memory.route-report.cli")
    )
    route_command["interface"]["options"] = [option for option in route_command["interface"]["options"] if option.get("name") != "verbose"]

    errors = checker._validate_operation_cli_inputs_for_interface(
        package_id="memory-bootstrap",
        command_path="route-report",
        interface=route_command["interface"],
        inherited_operation_ref=route_command["operation_ref"],
        inherited_option_names=set(),
        generated_root=generated_root,
    )

    assert any(
        "memory-bootstrap route-report operation memory.route-report.report declares cli-option input 'verbose'" in error
        for error in errors
    )


def test_generated_operation_cli_input_proof_allows_explicit_runtime_only_input(monkeypatch) -> None:
    checker = _load_checker()
    interface = {"name": "example", "options": [{"name": "format"}]}
    operation_ref = {"id": "example.report", "path": "operations/example.report.json"}
    operation = {
        "inputs": [
            {"name": "format", "source": "cli-option"},
            {"name": "adapter_only", "source": "cli-option", "command_visibility": "runtime-only"},
        ]
    }
    monkeypatch.setattr(checker, "_load_json", lambda path: operation)

    errors = checker._validate_operation_cli_inputs_for_interface(
        package_id="example-package",
        command_path="example",
        interface=interface,
        inherited_operation_ref=operation_ref,
        inherited_option_names=set(),
    )

    assert errors == []


def test_command_package_ir_records_deferred_shell_transport_evaluation() -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)

    shell_policy = ir["generation_policy"]["shell_adapter_policy"]
    root_targets = {target["kind"]: target for target in ir["packages"][0]["targets"]}

    assert "Issue #909 evaluation selects Bash as the first additional generated command transport candidate" in shell_policy
    assert "black-box conformance for runtime handoff" in shell_policy
    assert root_targets["bash"]["maturity_level_ref"] == "deferred"
    assert root_targets["powershell"]["maturity_level_ref"] == "deferred"


def test_static_generated_package_proof_rejects_read_only_routing_for_mutating_targets(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
    memory_package = next(package for package in ir["packages"] if package["id"] == "memory-bootstrap")
    python_target = next(target for target in memory_package["targets"] if target["kind"] == "python")
    python_target["maturity_level_ref"] = "weak-agent-safe-adapter"
    python_target["generation_status"] = "weak-agent-safe-adapter"
    monkeypatch.setattr(checker, "load_workspace_command_package_ir", lambda *, repo_root: ir)

    errors = checker._validate_static_surfaces()

    assert any("weak-agent-safe-adapter while generated commands include mutation-capable effects" in error for error in errors)


def test_static_generated_package_proof_requires_python_completion_gate_evidence(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
    ir["generation_policy"]["python_cli_completion"]["current_state"] = "full-generated-cli-complete"
    ir["generation_policy"]["python_cli_completion"]["completion_gate"]["satisfied_by"] = [
        item
        for item in ir["generation_policy"]["python_cli_completion"]["completion_gate"]["satisfied_by"]
        if item["id"] != "python-docker-conformance"
    ]
    monkeypatch.setattr(checker, "load_workspace_command_package_ir", lambda *, repo_root: ir)

    errors = checker._validate_static_surfaces()

    assert any("python-docker-conformance" in error for error in errors)


def test_static_generated_package_proof_requires_operation_ir_runtime_consumption_evidence(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
    ir["generation_policy"]["python_cli_completion"]["current_state"] = "full-generated-cli-complete"
    ir["generation_policy"]["python_cli_completion"]["completion_gate"]["satisfied_by"] = [
        item
        for item in ir["generation_policy"]["python_cli_completion"]["completion_gate"]["satisfied_by"]
        if item["id"] != "representative-operation-ir-runtime-consumed"
    ]
    monkeypatch.setattr(checker, "load_workspace_command_package_ir", lambda *, repo_root: ir)

    errors = checker._validate_static_surfaces()

    assert any("representative-operation-ir-runtime-consumed" in error for error in errors)


def test_static_generated_package_proof_requires_exhaustive_operation_inventory_evidence(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
    ir["generation_policy"]["python_cli_completion"]["current_state"] = "full-generated-cli-complete"
    ir["generation_policy"]["python_cli_completion"]["completion_gate"]["satisfied_by"] = [
        item
        for item in ir["generation_policy"]["python_cli_completion"]["completion_gate"]["satisfied_by"]
        if item["id"] != "operation-execution-inventory-exhaustive"
    ]
    monkeypatch.setattr(checker, "load_workspace_command_package_ir", lambda *, repo_root: ir)

    errors = checker._validate_static_surfaces()

    assert any("operation-execution-inventory-exhaustive" in error for error in errors)


def test_static_generated_package_proof_rejects_python_completion_proof_surface_drift(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
    ir["generation_policy"]["python_cli_completion"]["current_state"] = "full-generated-cli-complete"
    for item in ir["generation_policy"]["python_cli_completion"]["completion_gate"]["satisfied_by"]:
        if item["id"] == "python-docker-conformance":
            item["proof"] = "uv run python scripts/check/check_generated_command_packages.py"
            break
    monkeypatch.setattr(checker, "load_workspace_command_package_ir", lambda *, repo_root: ir)

    errors = checker._validate_static_surfaces()

    assert any("--python-docker-conformance --require-docker" in error for error in errors)


def test_static_generated_package_proof_rejects_full_completion_with_compatibility_handlers(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
    ir["generation_policy"]["python_cli_completion"]["current_state"] = "full-generated-cli-complete"
    ir["generation_policy"]["python_cli_completion"]["completion_gate"]["state"] = "satisfied"
    original_load_json = checker._load_json

    def fake_load_json(path: str) -> dict[str, object]:
        payload = original_load_json(path)
        if path == "python_operation_execution_inventory.json":
            payload = dict(payload)
            entries = [dict(entry) for entry in payload["entries"]]
            entries[0]["status"] = "compatibility-runtime-handler"
            payload["entries"] = entries
        return payload

    monkeypatch.setattr(checker, "load_workspace_command_package_ir", lambda *, repo_root: ir)
    monkeypatch.setattr(checker, "_load_json", fake_load_json)

    errors = checker._validate_static_surfaces()

    assert any("compatibility-runtime-handler" in error for error in errors)


def test_static_generated_package_proof_rejects_full_completion_with_generic_runtime_debt(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
    ir["generation_policy"]["python_cli_completion"]["current_state"] = "full-generated-cli-complete"
    ir["generation_policy"]["python_cli_completion"]["completion_gate"]["state"] = "satisfied"
    original_load_json = checker._load_json

    def fake_load_json(path: str) -> dict[str, object]:
        payload = original_load_json(path)
        if path == "python_operation_execution_inventory.json":
            payload = dict(payload)
            entries = [dict(entry) for entry in payload["entries"]]
            entries[0]["status"] = "accepted-hand-owned-runtime-primitive"
            entries[0]["runtime_boundary_class"] = "generic-deterministic-runtime-debt"
            entries[0]["runtime_boundary_reason"] = "still generic runtime debt"
            payload["entries"] = entries
        return payload

    monkeypatch.setattr(checker, "load_workspace_command_package_ir", lambda *, repo_root: ir)
    monkeypatch.setattr(checker, "_load_json", fake_load_json)

    errors = checker._validate_static_surfaces()

    assert any("generic deterministic behavior as runtime debt" in error for error in errors)


def test_static_generated_package_proof_rejects_full_completion_when_generated_main_delegates_first(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
    ir["generation_policy"]["python_cli_completion"]["current_state"] = "full-generated-cli-complete"
    ir["generation_policy"]["python_cli_completion"]["completion_gate"]["state"] = "satisfied"
    original_read_text = checker.Path.read_text

    def fake_read_text(self, *args, **kwargs):
        text = original_read_text(self, *args, **kwargs)
        if self.as_posix().endswith("generated/workspace/python/cli.py"):
            return text.replace(
                "    if supports_generated_command(argv_list):\n"
                "        try:\n"
                "            return run_generated_command(argv_list, _run_command_module)\n"
                "        except Exception as exc:\n"
                "            if exc.__class__.__name__.endswith('UsageError') or exc.__class__.__name__ == 'RepoDetectionError':\n"
                "                build_generated_parser().error(str(exc))\n"
                "            raise\n\n"
                "    build_generated_parser().parse_args(argv_list)\n"
                "    return 0\n",
                "    return 2\n",
            )
        return text

    monkeypatch.setattr(checker, "load_workspace_command_package_ir", lambda *, repo_root: ir)
    monkeypatch.setattr(checker.Path, "read_text", fake_read_text)

    errors = checker._validate_static_surfaces()

    assert any("missing generated-main boundary fragment" in error for error in errors)


def test_static_generated_package_proof_rejects_full_completion_with_product_runtime_source(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
    ir["generation_policy"]["python_cli_completion"]["current_state"] = "full-generated-cli-complete"
    ir["generation_policy"]["python_cli_completion"]["completion_gate"]["state"] = "satisfied"
    original_read_text = checker.Path.read_text
    original_is_file = checker.Path.is_file
    product_runtime_source = "scratch/product_runtime.py"

    def fake_read_text(self, *args, **kwargs):
        if self.as_posix().endswith(product_runtime_source):
            return "import argparse\n\ndef main(argv=None):\n    parser = argparse.ArgumentParser()\n    parser.add_subparsers()\n"
        return original_read_text(self, *args, **kwargs)

    def fake_is_file(self):
        if self.as_posix().endswith(product_runtime_source):
            return True
        return original_is_file(self)

    monkeypatch.setattr(checker, "load_workspace_command_package_ir", lambda *, repo_root: ir)
    monkeypatch.setattr(checker, "PYTHON_FULL_COMPLETION_BLOCKING_EXECUTABLE_PATHS", (product_runtime_source,))
    monkeypatch.setattr(checker.Path, "read_text", fake_read_text)
    monkeypatch.setattr(checker.Path, "is_file", fake_is_file)

    errors = checker._validate_static_surfaces()

    assert any(
        "scratch/product_runtime.py owns executable behavior markers" in error and "parser construction" in error for error in errors
    )


def test_generated_workspace_defaults_loader_uses_generated_resource() -> None:
    checker = _load_checker()
    runtime_path = checker.REPO_ROOT / "generated" / "workspace" / "python" / "primitives" / "workspace_runtime.py"
    text = runtime_path.read_text(encoding="utf-8")
    start = text.index("def _load_workspace_operation_defaults")
    end = text.index("\ndef _load_workspace_operation_system_intent_config", start)
    loader = text[start:end]

    assert "read_json_object(resource_root, 'payload.json')" in loader
    assert "agentic_workspace.workspace_runtime_primitives import _load_workspace_operation_defaults" not in loader
    assert (checker.REPO_ROOT / "generated" / "workspace" / "python" / "_contracts" / "payload.json").is_file()


def test_static_generated_package_proof_rejects_full_completion_when_runtime_outputs_are_not_rendered(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
    completion = ir["generation_policy"]["python_cli_completion"]
    completion["current_state"] = "full-generated-cli-complete"
    completion["completion_gate"]["state"] = "satisfied"
    completion["completion_gate"]["satisfied_by"].append(
        {
            "id": "product-specific-runtime-generated-output-owned",
            "evidence": "test fixture claims product runtime files are generated outputs",
            "proof": "scripts/check/check_generated_command_packages.py::_validate_full_python_completion_executable_ownership",
        }
    )

    original_render_outputs = checker.render_workspace_command_package_outputs

    def fake_render_outputs(manifest, *, repo_root):
        return [
            output
            for output in original_render_outputs(manifest, repo_root=repo_root)
            if output.path.relative_to(checker.REPO_ROOT).as_posix() != "generated/workspace/python/cli.py"
        ]

    monkeypatch.setattr(checker, "load_workspace_command_package_ir", lambda *, repo_root: ir)
    monkeypatch.setattr(checker, "render_workspace_command_package_outputs", fake_render_outputs)

    errors = checker._validate_static_surfaces()

    assert any("not produced by command-generation render_outputs()" in error for error in errors)


def test_static_generated_package_proof_rejects_missing_runtime_projection_inventory_entry(monkeypatch) -> None:
    checker = _load_checker()
    original_manifest = checker.python_runtime_projection_inventory_manifest

    def fake_manifest() -> dict[str, object]:
        payload = original_manifest()
        payload = dict(payload)
        payload["entries"] = list(payload["entries"][:-1])
        return payload

    monkeypatch.setattr(checker, "python_runtime_projection_inventory_manifest", fake_manifest)

    errors = checker._validate_python_runtime_projection_inventory(full_completion=False)

    assert any("missing runtime projection entries" in error for error in errors)


def test_static_generated_package_proof_rejects_legacy_generated_python_package_dirs(monkeypatch, tmp_path: Path) -> None:
    checker = _load_checker()
    generated_python = tmp_path / "generated" / "python" / "workspace-cli" / "legacy_package"
    generated_python.mkdir(parents=True)
    for package in ("workspace", "planning", "memory"):
        package_root = tmp_path / "generated" / package / "python"
        package_root.mkdir(parents=True)
        (package_root / "cli.py").write_text("", encoding="utf-8")
        for directory in ("commands", "operations", "primitives"):
            (package_root / directory).mkdir()
    monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)

    errors = checker._validate_generated_python_target_layout()

    assert any("legacy generated Python package directories" in error for error in errors)


def test_static_generated_package_proof_rejects_full_completion_with_transitional_runtime_projection_debt(monkeypatch) -> None:
    checker = _load_checker()
    original_manifest = checker.python_runtime_projection_inventory_manifest

    def fake_manifest() -> dict[str, object]:
        payload = original_manifest()
        payload = dict(payload)
        entries = [dict(entry) for entry in payload["entries"]]
        entries[0]["provenance_status"] = "transitional-generated-output-debt"
        entries[0]["blocking_full_completion"] = True
        payload["entries"] = entries
        return payload

    monkeypatch.setattr(checker, "python_runtime_projection_inventory_manifest", fake_manifest)

    errors = checker._validate_python_runtime_projection_inventory(full_completion=True)

    assert any("transitional-generated-output-debt" in error for error in errors)


def test_static_generated_package_proof_accepts_current_runtime_projection_inventory_for_partial_completion() -> None:
    checker = _load_checker()

    errors = checker._validate_python_runtime_projection_inventory(full_completion=False)

    assert errors == []


def test_static_generated_package_proof_rejects_shipped_source_cli_backslide(monkeypatch) -> None:
    checker = _load_checker()
    backslid_source = "src/agentic_workspace/cli_backslide.py"
    original_read_text = checker.Path.read_text
    original_is_file = checker.Path.is_file

    def fake_read_text(self, *args, **kwargs):
        if self.as_posix().endswith(backslid_source):
            return "import argparse\n\ndef main(argv=None):\n    parser = argparse.ArgumentParser()\n    parser.add_subparsers()\n"
        return original_read_text(self, *args, **kwargs)

    def fake_is_file(self):
        if self.as_posix().endswith(backslid_source):
            return True
        return original_is_file(self)

    monkeypatch.setattr(checker, "_tracked_python_source_files", lambda: [backslid_source])
    monkeypatch.setattr(checker.Path, "read_text", fake_read_text)
    monkeypatch.setattr(checker.Path, "is_file", fake_is_file)

    errors = checker._validate_python_shipped_source_executable_retirement()

    assert any(backslid_source in error and "parser construction" in error for error in errors)


def test_static_generated_package_proof_uses_behavior_detection_not_plain_keywords(monkeypatch) -> None:
    checker = _load_checker()
    harmless_source = "src/agentic_workspace/harmless_notes.py"
    original_read_text = checker.Path.read_text
    original_is_file = checker.Path.is_file

    def fake_read_text(self, *args, **kwargs):
        if self.as_posix().endswith(harmless_source):
            return 'TEXT = "argparse.ArgumentParser and def main are only prose here"\n'
        return original_read_text(self, *args, **kwargs)

    def fake_is_file(self):
        if self.as_posix().endswith(harmless_source):
            return True
        return original_is_file(self)

    monkeypatch.setattr(checker, "_tracked_python_source_files", lambda: [harmless_source])
    monkeypatch.setattr(checker.Path, "read_text", fake_read_text)
    monkeypatch.setattr(checker.Path, "is_file", fake_is_file)

    errors = checker._validate_python_shipped_source_executable_retirement()

    assert errors == []


def test_static_generated_package_proof_accepts_current_shipped_source_retirement() -> None:
    checker = _load_checker()

    errors = checker._validate_python_shipped_source_executable_retirement()

    assert errors == []


def test_tracked_python_source_files_falls_back_without_git(monkeypatch) -> None:
    checker = _load_checker()

    monkeypatch.setattr(checker.shutil, "which", lambda command: None if command == "git" else checker.shutil.which(command))

    sources = checker._tracked_python_source_files()

    assert "src/agentic_workspace/contract_tooling.py" in sources
    assert "packages/command-generation/src/command_generation/generator.py" in sources


def test_static_generated_package_proof_rejects_satisfied_gate_for_non_full_state(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
    ir["generation_policy"]["python_cli_completion"]["current_state"] = "adapter-layer-proven-not-full-generated-cli"
    ir["generation_policy"]["python_cli_completion"]["completion_gate"]["state"] = "satisfied"
    monkeypatch.setattr(checker, "load_workspace_command_package_ir", lambda *, repo_root: ir)

    errors = checker._validate_static_surfaces()

    assert any("cannot mark the Python CLI completion gate satisfied" in error for error in errors)


def test_static_generated_package_proof_accepts_current_python_completion_gate() -> None:
    checker = _load_checker()

    errors = checker._validate_static_surfaces()

    assert not [error for error in errors if "Python CLI completion" in error or "Python completion" in error]


def test_static_generated_package_proof_rejects_missing_primitive_conformance_case(monkeypatch) -> None:
    checker = _load_checker()
    monkeypatch.setattr(checker, "REQUIRED_PORTABLE_PRIMITIVE_CONFORMANCE", {"missing.primitive"})

    errors = checker._validate_static_surfaces()

    assert "primitive conformance is missing required primitive case: missing.primitive" in errors


def test_python_runtime_handler_boundary_rejects_non_adapter_handlers(monkeypatch) -> None:
    checker = _load_checker()
    memory_generated = checker._generated_package_for_package("memory-bootstrap")
    commands = checker.importlib.import_module(f"{memory_generated.__name__}.commands")
    drifted_handlers = dict(commands.GENERATED_COMMAND_HANDLERS)
    drifted_handlers["memory.status.report"] = memory_generated.build_parser
    monkeypatch.setattr(commands, "GENERATED_COMMAND_HANDLERS", drifted_handlers)

    errors = checker._validate_python_runtime_handler_boundary()

    assert any("memory.status.report" in error and "generated command module run function" in error for error in errors)


def test_python_runtime_import_boundary_rejects_legacy_generated_adapter_dispatch() -> None:
    checker = _load_checker()
    errors = checker._validate_no_legacy_generated_adapter_runtime_import(
        relative_path="generated/workspace/python/cli.py",
        text="from agentic_workspace.generated_command_adapters import GENERATED_COMMAND_ADAPTERS_BY_COMMAND\n",
    )

    assert errors == [
        "generated/workspace/python/cli.py must route generated Python commands through generated command modules, "
        "not legacy generated_command_adapters runtime dispatch"
    ]


def test_python_runtime_import_boundary_rejects_entrypoint_runtime_export_forwarding() -> None:
    checker = _load_checker()
    errors = checker._validate_no_legacy_generated_adapter_runtime_import(
        relative_path="generated/planning/python/cli.py",
        text=(
            "from repo_planning_bootstrap.runtime_projection import _print_summary as _print_summary\n"
            "_RUNTIME_EXPORT_SOURCES = ()\n"
            "def _sync_runtime_export_patches(): pass\n"
        ),
    )

    assert any("repo_planning_bootstrap.runtime_projection" in error for error in errors)
    assert any("_RUNTIME_EXPORT_SOURCES" in error for error in errors)
    assert any("_sync_runtime_export_patches" in error for error in errors)


def test_python_parser_retirement_rejects_generated_command_in_handwritten_parser(monkeypatch) -> None:
    checker = _load_checker()
    root_cli = checker._generated_runtime_module_for_package("root-workspace")

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
