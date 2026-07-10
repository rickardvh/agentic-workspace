from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

from repo_planning_bootstrap.installer import planning_record_schema_findings, planning_revision

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "run_generated_command_package_proof.py"
CHECK_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_generated_command_packages.py"
TEST_IR_RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "run_operation_conformance_tests.py"
_CHECKER_CASE_PREFIX = "__checker_case_result__="


def test_generated_typescript_mutation_outcome_classifier_covers_contract_enum() -> None:
    support = (REPO_ROOT / "generated/planning/typescript/src/hostPrimitiveSupport.mjs").as_uri()
    script = f"""
import {{ finalizeMutationOutcome }} from {json.dumps(support)};
const cases = [
  [{{dry_run: false, actions: [{{kind: 'created'}}]}}, ['applied', true, 'mutation-applied']],
  [{{dry_run: false, actions: [{{kind: 'current'}}]}}, ['noop', false, 'already-satisfied']],
  [{{dry_run: false, actions: [{{kind: 'manual review'}}]}}, ['blocked', false, 'manual-review-required']],
  [{{dry_run: false, actions: [{{kind: 'failed'}}]}}, ['failed', false, 'mutation-failed']],
];
for (const [input, expected] of cases) {{
  const result = finalizeMutationOutcome(input);
  const actual = [result.outcome, result.mutation_applied, result.reason_code];
  if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(JSON.stringify({{actual, expected}}));
}}
"""

    completed = subprocess.run(["node", "--input-type=module", "--eval", script], capture_output=True, text=True, check=False)

    assert completed.returncode == 0, completed.stderr


def test_generated_typescript_planning_install_reports_real_apply(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    cli_path = REPO_ROOT / "generated/planning/typescript/src/cli.mjs"

    completed = subprocess.run(
        ["node", str(cli_path), "install", "--target", str(tmp_path), "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["outcome"] == "applied"
    assert payload["mutation_applied"] is True
    assert payload["reason_code"] == "mutation-applied"
    assert (tmp_path / ".agentic-workspace/planning/agent-manifest.json").is_file()


def test_generated_typescript_planning_new_plan_reports_real_apply(tmp_path: Path) -> None:
    cli_path = REPO_ROOT / "generated/planning/typescript/src/cli.mjs"

    completed = subprocess.run(
        [
            "node",
            str(cli_path),
            "new-plan",
            "--id",
            "typescript-plan",
            "--title",
            "TypeScript Plan",
            "--target",
            str(tmp_path),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    record_path = tmp_path / ".agentic-workspace/planning/execplans/typescript-plan.plan.json"
    assert payload["outcome"] == "applied"
    assert payload["mutation_applied"] is True
    assert payload["reason_code"] == "mutation-applied"
    assert record_path.is_file()
    assert planning_record_schema_findings(record_path) == []


def test_generated_typescript_planning_new_plan_applies_activation_source_and_prep_only(tmp_path: Path) -> None:
    cli_path = REPO_ROOT / "generated/planning/typescript/src/cli.mjs"
    completed = subprocess.run(
        [
            "node",
            str(cli_path),
            "new-plan",
            "--id",
            "active-plan",
            "--title",
            "Active Plan",
            "--source",
            "#2168",
            "--activate",
            "--prep-only",
            "--target",
            str(tmp_path),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["outcome"] == "applied"
    record_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))
    assert state["todo"]["active_items"][0]["id"] == "active-plan"
    assert state["todo"]["active_items"][0]["refs"] == ["#2168"]
    assert record["active_milestone"]["status"] == "active"
    assert record["machine_readable_contract"]["planning_mode"]["prep_only"] is True
    assert planning_record_schema_findings(record_path) == []


def test_generated_typescript_planning_new_plan_enforces_revision_guard(tmp_path: Path) -> None:
    cli_path = REPO_ROOT / "generated/planning/typescript/src/cli.mjs"
    subprocess.run(
        [
            "node",
            str(cli_path),
            "new-plan",
            "--id",
            "first",
            "--title",
            "First",
            "--activate",
            "--target",
            str(tmp_path),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    current_revision = planning_revision(tmp_path)["revision_id"]
    completed = subprocess.run(
        [
            "node",
            str(cli_path),
            "new-plan",
            "--id",
            "second",
            "--title",
            "Second",
            "--queue",
            "--expect-planning-revision",
            "stale",
            "--target",
            str(tmp_path),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(completed.stdout)
    assert payload["outcome"] == "blocked"
    assert payload["reason_code"] == "planning-revision-mismatch"
    assert payload["current_planning_revision"] == current_revision
    assert not (tmp_path / ".agentic-workspace/planning/execplans/second.plan.json").exists()


def test_generated_typescript_workspace_new_plan_attaches_active_lane_and_blocks_invalid_owner(tmp_path: Path) -> None:
    cli_path = REPO_ROOT / "generated/workspace/typescript/src/cli.mjs"
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        'kind = "agentic-planning-state"\nschema_version = "planning-state/v1"\nwork_items = []\n\n[active]\nexecplans = []\n\n[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = [{ id = "lane-one", title = "Lane One", status = "active" }]\ncandidates = []\n',
        encoding="utf-8",
    )
    applied = subprocess.run(
        [
            "node",
            str(cli_path),
            "planning",
            "new-plan",
            "--id",
            "lane-plan",
            "--title",
            "Lane Plan",
            "--activate",
            "--lane",
            "lane-one",
            "--target",
            str(tmp_path),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert applied.returncode == 0, applied.stderr
    assert json.loads(applied.stdout)["outcome"] == "applied"
    state = tomllib.loads(state_path.read_text(encoding="utf-8"))
    assert state["roadmap"]["lanes"][0]["execplan"] == ".agentic-workspace/planning/execplans/lane-plan.plan.json"

    blocked = subprocess.run(
        [
            "node",
            str(cli_path),
            "planning",
            "new-plan",
            "--id",
            "missing-lane-plan",
            "--title",
            "Missing Lane",
            "--activate",
            "--switch-active",
            "--lane",
            "missing",
            "--target",
            str(tmp_path),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(blocked.stdout)
    assert payload["outcome"] == "blocked"
    assert payload["reason_code"] == "lane-owner-conflict"
    assert not (tmp_path / ".agentic-workspace/planning/execplans/missing-lane-plan.plan.json").exists()


def test_generated_typescript_unimplemented_mutation_blocks_instead_of_claiming_noop(tmp_path: Path) -> None:
    cli_path = REPO_ROOT / "generated/planning/typescript/src/cli.mjs"

    completed = subprocess.run(
        [
            "node",
            str(cli_path),
            "lane-create",
            "--id",
            "lane-one",
            "--title",
            "Lane One",
            "--target",
            str(tmp_path),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["outcome"] == "blocked"
    assert payload["mutation_applied"] is False
    assert payload["reason_code"] == "native-apply-unavailable"


def test_generated_typescript_root_lifecycle_blocks_unimplemented_apply_truthfully(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    cli_path = REPO_ROOT / "generated/workspace/typescript/src/cli.mjs"

    completed = subprocess.run(
        ["node", str(cli_path), "install", "--target", str(tmp_path), "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["outcome"] == "blocked"
    assert payload["mutation_applied"] is False
    assert payload["reason_code"] == "native-apply-unavailable"


def test_generated_typescript_system_intent_sync_blocks_unimplemented_apply_truthfully(tmp_path: Path) -> None:
    cli_path = REPO_ROOT / "generated/workspace/typescript/src/cli.mjs"

    completed = subprocess.run(
        ["node", str(cli_path), "system-intent", "--target", str(tmp_path), "--sync", "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["kind"] == "workspace-system-intent/v1"
    assert payload["outcome"] == "blocked"
    assert payload["mutation_applied"] is False
    assert payload["reason_code"] == "native-apply-unavailable"


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


def _load_test_ir_runner():
    spec = importlib.util.spec_from_file_location("run_operation_conformance_tests", TEST_IR_RUNNER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run_checker_case(source: str) -> dict[str, object]:
    return _run_checker_cases([source])[0]


def _run_checker_cases(sources: list[str]) -> list[dict[str, object]]:
    script = f"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import textwrap
import traceback
from pathlib import Path

CHECK_SCRIPT_PATH = Path({str(CHECK_SCRIPT_PATH)!r})
SOURCES = json.loads({json.dumps(json.dumps(sources))})


def _load_checker(index):
    spec = importlib.util.spec_from_file_location(f"check_generated_command_packages_case_{{index}}", CHECK_SCRIPT_PATH)
    assert spec is not None
    checker = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = checker
    spec.loader.exec_module(checker)
    return checker


results = []
for index, source in enumerate(SOURCES):
    emitted = []

    def _emit(payload):
        emitted.append(payload)

    namespace = {{
        "checker": _load_checker(index),
        "copy": copy,
        "json": json,
        "Path": Path,
        "subprocess": subprocess,
        "_emit": _emit,
    }}
    try:
        exec(textwrap.dedent(source).strip(), namespace)
    except BaseException as exc:
        results.append({{"__error__": str(exc), "__traceback__": traceback.format_exc()}})
    else:
        if not emitted:
            results.append({{"__error__": "checker case did not emit a result"}})
        else:
            results.append(emitted[-1])

print({str(_CHECKER_CASE_PREFIX)!r} + json.dumps(results, sort_keys=True))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise AssertionError(
            f"checker subprocess failed\nreturncode={completed.returncode}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith(_CHECKER_CASE_PREFIX):
            payloads = json.loads(line[len(_CHECKER_CASE_PREFIX) :])
            assert isinstance(payloads, list)
            results: list[dict[str, object]] = []
            for payload in payloads:
                assert isinstance(payload, dict)
                if "__error__" in payload:
                    raise AssertionError(
                        f"checker case failed\nerror={payload['__error__']}\ntraceback:\n{payload.get('__traceback__', '')}"
                    )
                results.append(payload)
            return results
    raise AssertionError(f"checker subprocess did not emit a result\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")


def _checker_payload_errors(payload: dict[str, object]) -> list[str]:
    errors = payload.get("errors")
    assert isinstance(errors, list)
    return [str(error) for error in errors]


def _checker_case_errors(source: str) -> list[str]:
    return _checker_payload_errors(_run_checker_case(source))


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


def test_operation_conformance_runner_executes_python_cases(capsys) -> None:
    runner = _load_test_ir_runner()

    payload = runner.run_ir_cases(target_selection="python", case_filter=set(), require_node=False)

    assert payload["kind"] == "operation-conformance-proof/v1"
    assert payload["artifact_registry"] == "operation_artifact_registry.json"
    assert payload["summary"]["state"] == "pass"
    assert payload["summary"]["fail_count"] == 0
    assert payload["summary"]["pass_count"] == 10
    cases = {(case["case_id"], case["target"]): case for case in payload["cases"]}
    assert cases[("defaults.selected-output.success", "python")]["state"] == "pass"
    assert cases[("defaults.selected-output.success", "python")]["adapter_id"] == "python.function"
    assert cases[("defaults.root-cli-authority.success", "python")]["state"] == "pass"
    assert "Kind: agentic-workspace/selected-output/v1" not in capsys.readouterr().out
    assert cases[("config.invalid-format.error", "python")]["exit_code"] == 2
    assert cases[("config.selected-output.success", "python")]["exit_code"] == 0
    assert cases[("defaults.tiny-router-text.success", "python")]["exit_code"] == 0
    assert cases[("modules.report-router.success", "python")]["state"] == "pass"
    assert cases[("session-log.manage-status.boundary", "python")]["selected_fields"]["enabled"] is False
    assert cases[("delegation-outcome.append-write.boundary", "python")]["selected_fields"]["recorded.outcome"] == "success"
    assert cases[("memory.list-skills.parity", "python")]["selected_fields"] == {"mode": "skills"}


def test_operation_conformance_runner_reports_typescript_unavailable(monkeypatch) -> None:
    runner = _load_test_ir_runner()
    monkeypatch.setattr(runner.shutil, "which", lambda _command: None)

    soft = runner.run_ir_cases(target_selection="typescript", case_filter=set(), require_node=False)
    strict = runner.run_ir_cases(target_selection="typescript", case_filter=set(), require_node=True)

    assert soft["summary"]["state"] == "pass"
    assert soft["summary"]["unavailable_count"] == 8
    assert strict["summary"]["state"] == "fail"
    assert strict["summary"]["fail_count"] == 8


def test_operation_conformance_runner_compares_parity(monkeypatch) -> None:
    runner = _load_test_ir_runner()

    def fake_run_case_target(*, case, artifact_registry, target_kind, temp_root, require_node):
        return {
            "case_id": case["id"],
            "behavioral_class": case["behavioral_class"],
            "operation_id": case["operation_ref"]["operation_id"],
            "artifact_id": f"{target_kind}.artifact",
            "adapter_id": f"{target_kind}.function",
            "conformance_ref": case["operation_ref"].get("conformance_ref", ""),
            "target": target_kind,
            "state": "pass",
            "exit_code": 0,
            "selected_fields": {"mode": "skills"},
            "message": "",
        }

    monkeypatch.setattr(runner, "_run_case_target", fake_run_case_target)

    payload = runner.run_ir_cases(
        target_selection="parity",
        case_filter={"memory.list-skills.parity"},
        require_node=True,
    )

    parity_result = next(case for case in payload["cases"] if case["target"] == "parity")
    assert payload["summary"]["state"] == "pass"
    assert parity_result["state"] == "pass"


def test_operation_conformance_runner_reports_missing_python_function_symbol() -> None:
    runner = _load_test_ir_runner()
    case = {
        "id": "todo.list.operation",
        "behavioral_class": "success",
        "operation_ref": {"operation_id": "todo.list.report"},
        "input": {"json": {}},
        "expected": {"result": {"selected_fields": {}}},
    }
    artifact = {"artifact_id": "todo.list.python", "adapter_id": "python.function"}

    result = runner._run_python_function_case(case=case, artifact=artifact)

    assert result["state"] == "unavailable"
    assert result["message"] == "python.function artifact has no importable symbol"


def test_generated_typescript_conformance_cases_come_from_contract_artifacts() -> None:
    checker = _load_checker()

    cases, errors = checker._runnable_typescript_conformance_cases()

    assert errors == []
    by_ref = {case.case.conformance_ref: case.case for case in cases}
    defaults = by_ref["defaults.report.process"]
    planning_status = by_ref["planning.status.process"]
    memory_skills = by_ref["memory.list-skills.process"]

    assert list(defaults.success_args) == ["defaults", "--section", "startup", "--format", "json"]
    assert defaults.expected_fields["answer.default_canonical_agent_instructions_file"] == "AGENTS.md"
    assert defaults.fixture_id == "minimal-repo"
    assert defaults.fixture_files["README.md"] == "# Fixture\n"
    assert list(planning_status.success_args) == ["status", "--format", "json"]
    assert planning_status.expected_fields == {"dry_run": False}
    assert list(memory_skills.success_args) == ["list-skills", "--format", "json"]
    assert memory_skills.expected_fields == {"mode": "skills"}


def test_generated_python_conformance_uses_contract_artifacts() -> None:
    checker = _load_checker()

    registries, errors = checker._adapter_conformance_cases_by_package()

    assert errors == []
    assert set(registries) == {"root-workspace", "planning-bootstrap", "memory-bootstrap", "verification-cli"}
    defaults = registries["root-workspace"]["defaults.report.process"]
    planning_status = registries["planning-bootstrap"]["planning.status.process"]
    memory_skills = registries["memory-bootstrap"]["memory.list-skills.process"]
    verification_report = registries["verification-cli"]["verification.report.process"]

    assert "from agentic_workspace.cli import main" in checker._python_command_for_package("root-workspace")[-1]
    assert "from repo_planning_bootstrap.cli import main" in checker._python_command_for_package("planning-bootstrap")[-1]
    assert "from repo_memory_bootstrap.cli import main" in checker._python_command_for_package("memory-bootstrap")[-1]
    assert "from repo_verification_bootstrap.cli import main" in checker._python_command_for_package("verification-cli")[-1]
    assert list(defaults.success_args) == ["defaults", "--section", "startup", "--format", "json"]
    assert defaults.expected_exit == 0
    assert defaults.allow_stderr is False
    assert defaults.expected_fields["answer.default_canonical_agent_instructions_file"] == "AGENTS.md"
    assert planning_status.expected_fields == {"dry_run": False}
    assert memory_skills.expected_fields == {"mode": "skills"}
    assert list(verification_report.success_args) == ["report", "--target", ".", "--format", "json"]
    assert verification_report.expected_fields == {"status": "absent", "configured": False}


def test_full_python_completion_rejects_whole_file_runtime_boundary_acceptance() -> None:
    errors = _checker_case_errors(
        """
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

        checker.python_runtime_projection_inventory_manifest = fake_manifest
        _emit({"errors": checker._validate_full_python_completion_executable_ownership(ir)})
        """
    )

    assert any("whole-file runtime boundary acceptance" in error for error in errors)
    assert any("unaccepted package-domain runtime/lifecycle source is still present" in error for error in errors)
    assert any("generated runtime facades still bridge to unaccepted package-owned runtime helpers" in error for error in errors)


def test_full_python_completion_rejects_wrong_operation_function_call_metadata() -> None:
    errors = _checker_case_errors(
        """
        inventory = copy.deepcopy(checker.python_runtime_projection_inventory_manifest())
        entry = next(item for item in inventory["accepted_runtime_boundaries"]["entries"] if item["binding_kind"] == "operation-function-call")
        entry["operation_ids"] = ["wrong.operation"]
        checker.python_runtime_projection_inventory_manifest = lambda: inventory
        _emit({"errors": checker._validate_python_completion_accepted_runtime_boundaries()[0]})
        """
    )

    assert any("must declare operation_ids" in error for error in errors)


def test_full_python_completion_proves_generated_runtime_handler_command_boundary() -> None:
    checker = _load_checker()

    bindings = checker._generated_runtime_facade_package_runtime_bindings()
    session_log_binding = next(
        binding for binding in bindings if binding["facade_path"] == "generated/workspace/python/commands/session_log_manage.py"
    )

    assert session_log_binding == {
        "facade_path": "generated/workspace/python/commands/session_log_manage.py",
        "facade_symbol": "run",
        "source_module": "agentic_workspace.session_logging",
        "source_symbol": "_run_session_log_adapter",
        "operation_ids": ["session-log.manage"],
        "primitive_refs": ["runtime_module_handler:session-log.manage"],
    }
    assert checker._validate_python_completion_accepted_runtime_boundaries()[0] == []


def test_full_python_completion_rejects_weak_runtime_boundary_minimization_metadata() -> None:
    errors = _checker_case_errors(
        """
        inventory = copy.deepcopy(checker.python_runtime_projection_inventory_manifest())
        entry = next(item for item in inventory["accepted_runtime_boundaries"]["entries"] if item["binding_kind"] == "operation-function-call")
        entry["minimization_route"] = "move-to-command-generation-or-ir"
        entry["direct_edit_reasons_allowed"] = ["implementation detail"]
        entry.pop("stale_when", None)
        checker.python_runtime_projection_inventory_manifest = lambda: inventory
        _emit({"errors": checker._validate_python_completion_accepted_runtime_boundaries()[0]})
        """
    )

    assert any("must declare minimization_route=" in error for error in errors)
    assert any("direct_edit_reasons_allowed must be" in error for error in errors)
    assert any("must include non-empty stale_when" in error for error in errors)


def test_full_python_completion_rejects_weak_output_boundary_audit() -> None:
    errors = _checker_case_errors(
        """
        inventory = copy.deepcopy(checker.python_runtime_projection_inventory_manifest())
        entry = next(
            item for item in inventory["accepted_runtime_boundaries"]["entries"] if item.get("source_symbol") == "_emit_workspace_operation_output"
        )
        entry["runtime_boundary_class"] = "mutation-orchestration"
        entry["why_not_generic_deterministic"] = "package output"
        entry["generic_behavior_audit"] = "package output"
        checker.python_runtime_projection_inventory_manifest = lambda: inventory
        _emit({"errors": checker._validate_python_completion_accepted_runtime_boundaries()[0]})
        """
    )

    assert any("output-emission boundary must use runtime_boundary_class='package-specific-judgment'" in error for error in errors)
    assert any("output-emission boundary must explain the remaining package-specific output judgment" in error for error in errors)
    assert any("output-emission boundary audit must include 'generated-owned output coverage:'" in error for error in errors)


def test_ordinary_command_migration_inventory_is_current() -> None:
    checker = _load_checker()

    assert checker._validate_ordinary_command_migration_inventory() == []


def test_ordinary_command_migration_inventory_fails_closed_when_generated_command_missing() -> None:
    errors = _checker_case_errors(
        """
        inventory = copy.deepcopy(checker.python_runtime_projection_inventory_manifest())
        migration = inventory["ordinary_command_migration"]["representative_migrations"][0]
        migration["generated_command_module"] = "generated/planning/python/commands/missing_closeout.py"
        checker.python_runtime_projection_inventory_manifest = lambda: inventory
        _emit({"errors": checker._validate_ordinary_command_migration_inventory()})
        """
    )

    assert any("generated_command_module" in error and "does not exist" in error for error in errors)


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


def test_generated_cli_compatibility_allowlist_rejects_missing_exact_paths() -> None:
    errors = _checker_case_errors(
        """
        checker.GENERATED_CLI_COMPATIBILITY_VOCABULARY_ALLOWLIST = {
            **checker.GENERATED_CLI_COMPATIBILITY_VOCABULARY_ALLOWLIST,
            "internal/command-generation/src/command_generation/generated_package_loader.py": "stale internalization residue",
        }
        _emit({"errors": checker._validate_generated_cli_compatibility_vocabulary()})
        """
    )

    assert any("is listed in GENERATED_CLI_COMPATIBILITY_VOCABULARY_ALLOWLIST but does not exist" in error for error in errors)


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


def test_planning_generated_force_includes_are_payload_classified() -> None:
    checker = _load_checker()

    assert checker._validate_planning_generated_force_include_classification() == []


def test_planning_generated_force_include_classification_names_missing_surface(monkeypatch) -> None:
    checker = _load_checker()
    expected, source_errors = checker._planning_generated_force_include_sources()
    assert source_errors == []
    missing_path = sorted(expected)[0]
    payload = copy.deepcopy(checker._planning_payload_surface_classification())
    payload["surfaces"] = [surface for surface in payload["surfaces"] if surface.get("source_path") != missing_path]
    monkeypatch.setattr(checker, "_planning_payload_surface_classification", lambda: payload)

    errors = checker._validate_planning_generated_force_include_classification()

    assert any(missing_path in error for error in errors)


def test_python_completion_blocker_report_accepts_exact_symbol_runtime_boundaries() -> None:
    payload = _run_checker_case(
        """
        ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
        _emit({"report": checker._python_completion_blockers_report(ir)})
        """
    )
    report = payload["report"]
    assert isinstance(report, dict)

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
    assert runtime_metrics["accepted_runtime_symbol_count"] == sum(
        runtime_metrics["accepted_runtime_symbol_count_by_minimization_category"].values()
    )
    assert runtime_metrics["accepted_runtime_symbol_count"] == sum(
        runtime_metrics["accepted_runtime_symbol_count_by_minimization_route"].values()
    )
    assert runtime_metrics["accepted_runtime_symbol_count_by_minimization_route"]["keep-as-hand-owned-primitive"] > 0
    assert runtime_metrics["accepted_runtime_symbol_count_by_minimization_tracking_issue"]["#1364"] > 0
    assert runtime_metrics["python_bridge_step_count"] == 0
    assert runtime_metrics["python_bridge_symbols"] == []
    assert runtime_metrics["generic_debt_symbol_count"] == 0
    assert runtime_metrics["baseline_symbol_count"] == runtime_metrics["accepted_runtime_symbol_count"]
    assert runtime_metrics["new_symbols_since_baseline"] == []
    assert runtime_metrics["removed_symbols_since_baseline"] == []
    minimization = report["runtime_boundary_minimization"]
    assert minimization["kind"] == "python-runtime-boundary-minimization/v1"
    assert minimization["status"] == "not-minimized-hand-owned-boundaries-remain"
    assert minimization["minimization_claim_allowed"] is False
    assert minimization["whole_category_acceptance_allowed"] is False
    assert minimization["accepted_symbol_count"] == runtime_metrics["accepted_runtime_symbol_count"]
    assert minimization["remaining_hand_owned_symbol_count"] == runtime_metrics["accepted_runtime_symbol_count"]
    assert minimization["remaining_by_minimization_route"]["keep-as-hand-owned-primitive"] > 0
    assert minimization["remaining_by_minimization_tracking_issue"]["#1364"] > 0
    assert minimization["contract_stable_extraction_candidate_count"] == runtime_metrics[
        "accepted_runtime_symbol_count_by_minimization_route"
    ].get("candidate-extract-when-contract-stable", 0)
    assert minimization["contract_stable_extraction_candidate_count"] == 0
    assert minimization["exact_runtime_boundary_inventory"]
    exact_entry = minimization["exact_runtime_boundary_inventory"][0]
    assert {
        "symbol_id",
        "minimization_category",
        "minimization_route",
        "minimization_owner",
        "minimization_tracking_issue",
        "stale_when",
    } <= set(exact_entry)
    assert "not a claim that runtime boundaries are minimized" in minimization["freshness_claim_boundary"]
    assert "generic-deterministic-runtime-debt" in minimization["route_by_runtime_boundary_class"]
    assert "agent_owns" in minimization["authority_boundary"]
    assert "accepted_symbol_count is non-zero" in minimization["claim_rule"]
    target_freshness = report["generated_target_freshness"]
    assert target_freshness["kind"] == "generated-target-freshness/v1"
    assert target_freshness["status"] == "fresh"
    provenance = target_freshness["command_generation_package"]
    assert provenance["kind"] == "command-generation/package-provenance/v1"
    assert provenance["source"] in {"released-wheel", "immutable-git-ref"}
    assert provenance["declared_version"] == provenance["installed_version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:rc\d+)?", provenance["declared_version"])
    assert provenance["compatible"] is True
    if provenance["source"] == "released-wheel":
        assert provenance["dependency_url"].startswith(
            f"https://github.com/rickardvh/command-generation/releases/download/v{provenance['declared_version']}/"
        )
        assert f"command_generation-{provenance['declared_version']}-py3-none-any.whl" in provenance["dependency_url"]
        assert "#sha256=" in provenance["dependency_url"]
    else:
        assert re.fullmatch(r"[0-9a-f]{40}", provenance["git_ref"])
    metadata = target_freshness["generation_metadata"]
    assert metadata["kind"] == "command-generation/generated-artifact-metadata-proof/v1"
    assert metadata["status"] == "fresh"
    assert metadata["expected_generator"] == {"package": "command-generation", "version": provenance["declared_version"]}
    assert metadata["expected_source_ir_schema_version"] == "command-generation/command-package-ir/v1"
    assert metadata["expected_target_layout_versions"]["python"] == "command-generation/python-target-layout/v1"
    assert metadata["expected_target_layout_versions"]["typescript"] == "command-generation/typescript-target-layout/v1"
    assert metadata["errors"] == []
    assert target_freshness["target_families"] == ["python", "typescript"]
    assert target_freshness["rendered_output_count_by_family"]["python"] > 0
    assert target_freshness["rendered_output_count_by_family"]["typescript"] > 0
    assert target_freshness["stale_output_count_by_family"] == {}
    assert target_freshness["missing_target_families"] == []
    assert "do not rewrite generated files" in target_freshness["cheap_check_rule"]
    assert "Python-only evidence" in target_freshness["claim_rule"]
    edit_policy = report["runtime_source_edit_policy"]
    assert edit_policy["kind"] == "generated-cli-runtime-source-edit-policy/v1"
    assert "src/agentic_workspace/workspace_runtime_primitives.py" in edit_policy["watched_runtime_source_paths"]
    assert edit_policy["accepted_direct_edit_reasons"] == ["existing-primitive-bugfix", "new-primitive-implementation"]
    assert "package-domain boundary" in edit_policy["rejected_vague_reasons"]
    assert "source_symbol_or_primitive" in edit_policy["required_evidence"]
    assert "vague package-domain boundary wording is insufficient" in edit_policy["rule"]
    migration = report["generated_command_migration_completion"]
    assert migration["kind"] == "generated-command-migration-completion/v1"
    assert migration["milestone"] == "Generated command migration completion"
    assert migration["status"] == "satisfied"
    assert migration["blocked_issues"] == []
    assert migration["issue_statuses"]["#1356"]["status"] == "satisfied"
    assert migration["issue_statuses"]["#1358"]["status"] == "satisfied"
    assert migration["issue_statuses"]["#1442"]["status"] == "satisfied"
    assert migration["hand_owned_runtime_inventory"]["accepted_runtime_symbol_count"] == runtime_metrics["accepted_runtime_symbol_count"]
    assert migration["hand_owned_runtime_inventory"]["generic_debt_symbol_count"] == 0
    assert "parent #1441" in migration["hand_owned_runtime_inventory"]["claim_boundary"]
    assert "src/agentic_workspace/contracts/command_package_ir.json" in migration["command_generation_owner_surfaces"]
    assert "IR-defined schema-coupled generated command tests" in migration["remaining_parent_scope"][0]
    lifecycle_metrics = report["lifecycle_dry_run_metrics"]
    assert lifecycle_metrics["status"] == "available"
    assert lifecycle_metrics["memory_payload_default_dry_run_operation_count"] >= 3
    assert "memory.install.lifecycle" in {
        operation["operation_id"] for operation in lifecycle_metrics["memory_payload_default_dry_run_operations"]
    }
    retired_usage = report["retired_command_generation_primitive_usage"]
    assert retired_usage["status"] == "absent-from-ordinary-source"
    assert retired_usage["ordinary_source_operation_usage_count"] == 0
    assert retired_usage["guard_reference_count"] > 0
    assert retired_usage["guard_reference_paths"] == [
        "scripts/check/check_generated_command_packages.py",
        "tests/test_generated_command_package_proof_runner.py",
    ]
    ownership = report["aw_primitive_ownership"]
    assert ownership["kind"] == "agentic-workspace/aw-primitive-ownership/v1"
    assert ownership["status"] == "satisfied"
    assert ownership["ordinary_source_operation_ir"]["retired_primitive_usage_count"] == 0
    assert ownership["ordinary_source_operation_ir"]["aw_owned_usage_count"] > 0
    assert ownership["primitive_declarations"]["status"] == "satisfied"
    assert ownership["primitive_declarations"]["source"] == "src/agentic_workspace/contracts/workspace_runtime_primitive_families.json"
    assert ownership["primitive_declarations"]["definition_source"] == "src/agentic_workspace/contracts/operation_primitives.json"
    assert ownership["runtime_bindings"]["status"] == "satisfied"
    assert ownership["retired_command_generation_primitive_usage"]["guard_reference_paths"] == [
        "scripts/check/check_generated_command_packages.py",
        "tests/test_generated_command_package_proof_runner.py",
    ]
    assert "--aw-primitive-ownership --format json" in ownership["downstream_proof_command"]


def test_generated_artifact_metadata_rejects_unexpected_generator_version() -> None:
    errors = _checker_case_errors(
        """
        ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
        original = checker.json.loads
        def fake_loads(text):
            payload = original(text)
            if isinstance(payload, dict) and isinstance(payload.get("generation_metadata"), dict):
                payload = copy.deepcopy(payload)
                payload["generation_metadata"]["generator"]["version"] = "0.0.0"
            return payload
        checker.json.loads = fake_loads
        _emit({"errors": checker._validate_generated_artifact_generation_metadata(ir)})
        """
    )

    assert any("generation metadata has unexpected generator" in error for error in errors)


def test_generated_artifact_metadata_rejects_unsupported_target_layout() -> None:
    errors = _checker_case_errors(
        """
        ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
        original = checker.json.loads
        def fake_loads(text):
            payload = original(text)
            if isinstance(payload, dict) and isinstance(payload.get("generation_metadata"), dict):
                payload = copy.deepcopy(payload)
                payload["generation_metadata"]["target"]["layout_version"] = "command-generation/python-target-layout/v0"
            return payload
        checker.json.loads = fake_loads
        _emit({"errors": checker._validate_generated_artifact_generation_metadata(ir)})
        """
    )

    assert any("generation metadata has unexpected target layout" in error for error in errors)


def test_generated_artifact_metadata_expectations_come_from_family_inventory() -> None:
    errors = _checker_case_errors(
        """
        ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
        original = checker.workspace_runtime_primitive_families_manifest

        def fake_inventory() -> dict[str, object]:
            payload = copy.deepcopy(original())
            family = next(item for item in payload["families"] if item.get("id") == "generated-command-package-proof-metadata")
            expectations = dict(family["generated_artifact_metadata_expectations"])
            expectations["source_ir_schema_version"] = "command-generation/command-package-ir/v0"
            family["generated_artifact_metadata_expectations"] = expectations
            return payload

        checker.workspace_runtime_primitive_families_manifest = fake_inventory
        _emit({"errors": checker._validate_generated_artifact_generation_metadata(ir)})
        """
    )

    assert any("canonical command package IR schema mismatch" in error for error in errors)


def test_generated_output_git_dirtiness_classifies_line_ending_only_changes() -> None:
    errors = _checker_case_errors(
        """
        relative_path = "generated/workspace/python/line-ending-fixture.txt"
        path = checker.REPO_ROOT / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)

        class Output:
            def __init__(self, path, content):
                self.path = path
                self.content = content

        def fake_render_outputs(ir, *, repo_root):
            return [Output(path, "alpha\\nbeta\\n")]

        def fake_git_output(args):
            if args == ["status", "--porcelain=v1", "--", "generated"]:
                return f" M {relative_path}\\n"
            if args == ["diff", "--numstat", "HEAD", "--", relative_path]:
                return ""
            return ""

        try:
            path.write_bytes(b"alpha\\r\\nbeta\\r\\n")
            checker.render_workspace_command_package_outputs = fake_render_outputs
            checker._run_git_output = fake_git_output
            _emit({"errors": checker._validate_generated_output_git_dirtiness({})})
        finally:
            path.unlink(missing_ok=True)
        """
    )

    assert errors == [
        "generated/workspace/python/line-ending-fixture.txt is line-ending-only generated output dirtiness; "
        "run git restore -- generated/workspace/python/line-ending-fixture.txt or regenerate packages to normalize LF output."
    ]


def test_lifecycle_dry_run_generation_regression_is_blocked() -> None:
    errors = _checker_case_errors(
        """
        inventory = copy.deepcopy(checker.python_runtime_projection_inventory_manifest())
        entry = next(
            item for item in inventory["accepted_runtime_boundaries"]["entries"] if item.get("operation_id") == "memory.install.lifecycle"
        )
        entry["operation_path"] = "generated/planning/python/operations/planning.install.lifecycle.json"
        checker.python_runtime_projection_inventory_manifest = lambda: inventory
        _emit({"errors": checker._validate_lifecycle_dry_run_generation()})
        """
    )

    assert any("does not route the default dry-run branch through memory.payload.lifecycle-plan" in error for error in errors)


def test_retired_command_generation_primitive_source_operation_usage_is_blocked() -> None:
    errors = _checker_case_errors(
        """
        temp_root = checker.REPO_ROOT / ".tmp-checker-case"
        temp_root.mkdir(exist_ok=True)
        operation_path = temp_root / "operation.json"
        operation_path.write_text(json.dumps({
            "id": "example.report",
            "ir_plan": {"steps": [{"id": "resolve", "uses": "workspace.root.resolve"}]},
        }), encoding="utf-8")
        checker._source_operation_contract_paths = lambda: [operation_path]
        try:
            _emit({"errors": checker._validate_retired_command_generation_primitive_usage_inventory()})
        finally:
            operation_path.unlink(missing_ok=True)
            temp_root.rmdir()
        """
    )

    assert any(
        "retired command-generation transitional primitive IDs are present in ordinary source operation contracts" in error
        for error in errors
    )


def test_aw_primitive_ownership_report_is_a_stable_downstream_proof(capsys) -> None:
    checker = _load_checker()

    status = checker.main(["--aw-primitive-ownership", "--format", "json"])

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/aw-primitive-ownership/v1"
    assert payload["status"] == "satisfied"
    assert payload["ordinary_source_operation_ir"]["retired_primitive_usage_count"] == 0
    assert payload["ordinary_source_operation_ir"]["aw_owned_usage_count_by_primitive"]["workspace.target-root.resolve"] > 0
    declarations = payload["primitive_declarations"]
    assert declarations["status"] == "satisfied"
    assert declarations["source"] == "src/agentic_workspace/contracts/workspace_runtime_primitive_families.json"
    declared_ids = {item["aw_owned_id"] for item in declarations["declarations"]}
    assert "workspace.target-root.resolve" in declared_ids
    assert "memory.payload.verify" in declared_ids
    runtime = payload["runtime_bindings"]
    assert runtime["generated_package_runtime_ref_count_by_primitive"]["workspace.target-root.resolve"] > 0
    assert runtime["support_modules"] == {
        "python_support_path": "src/agentic_workspace/contracts/python_primitive_support.py",
        "typescript_support_path": "src/agentic_workspace/contracts/typescript_primitive_support.mjs",
    }
    assert payload["retired_command_generation_primitive_usage"]["status"] == "absent-from-ordinary-source"
    assert payload["coordination"]["command_generation_issue_refs"] == ["rickardvh/command-generation#55"]


def test_aw_primitive_ownership_report_blocks_missing_aw_declaration() -> None:
    errors = _checker_case_errors(
        """
        ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
        original = checker._primitive_definition_by_id
        definitions = original()
        definitions.pop("workspace.target-root.resolve", None)
        checker._primitive_definition_by_id = lambda: definitions
        _emit({"errors": checker._validate_aw_primitive_ownership_report(ir)})
        """
    )

    assert "AW-owned primitive declarations are missing or invalid" in errors


def test_aw_primitive_ownership_report_reads_required_ids_from_family_inventory() -> None:
    errors = _checker_case_errors(
        """
        ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
        original = checker.workspace_runtime_primitive_families_manifest

        def fake_inventory() -> dict[str, object]:
            payload = copy.deepcopy(original())
            family = next(item for item in payload["families"] if item.get("id") == "aw-owned-primitive-ids")
            family["aw_owned_primitive_ids"] = list(family["aw_owned_primitive_ids"]) + ["workspace.missing-primitive"]
            return payload

        checker.workspace_runtime_primitive_families_manifest = fake_inventory
        _emit({"errors": checker._validate_aw_primitive_ownership_report(ir)})
        """
    )

    assert "AW-owned primitive declarations are missing or invalid" in errors


def test_aw_primitive_ownership_report_fails_closed_when_family_inventory_cannot_load() -> None:
    payload = _run_checker_case(
        """
        def broken_inventory() -> dict[str, object]:
            raise RuntimeError("family inventory unavailable")

        checker.workspace_runtime_primitive_families_manifest = broken_inventory
        try:
            checker._aw_owned_primitives()
        except RuntimeError as exc:
            _emit({"message": str(exc)})
        else:
            _emit({"message": "unexpected success"})
        """
    )

    assert payload["message"] == "family inventory unavailable"


def test_runtime_budget_metrics_compare_against_recorded_baseline() -> None:
    payload = _run_checker_case(
        """
        inventory = copy.deepcopy(checker.python_runtime_projection_inventory_manifest())
        accepted = inventory["accepted_runtime_boundaries"]
        current_symbols = [checker._accepted_runtime_symbol_id(entry) for entry in accepted["entries"] if isinstance(entry, dict)]
        accepted["baseline_symbols"] = current_symbols[:-1] + [
            "operation-function-call|generated/memory/python/operations/retired.report.json|retired.report|"
            "repo_memory_bootstrap.installer|retired_runtime_symbol"
        ]
        checker.python_runtime_projection_inventory_manifest = lambda: inventory
        _emit({"runtime_metrics": checker._python_runtime_boundary_metrics(), "current_symbols": current_symbols})
        """
    )
    runtime_metrics = payload["runtime_metrics"]
    current_symbols = payload["current_symbols"]
    assert isinstance(runtime_metrics, dict)
    assert isinstance(current_symbols, list)

    assert runtime_metrics["new_symbols_since_baseline"] == [current_symbols[-1]]
    assert runtime_metrics["removed_symbols_since_baseline"] == [
        "operation-function-call|generated/memory/python/operations/retired.report.json|retired.report|"
        "repo_memory_bootstrap.installer|retired_runtime_symbol"
    ]


def test_runtime_boundary_minimization_routes_generic_debt_to_command_generation() -> None:
    payload = _run_checker_case(
        """
        metrics = checker._python_runtime_boundary_metrics()
        metrics["accepted_runtime_symbol_count"] += 1
        metrics["accepted_runtime_symbol_count_by_class"]["generic-deterministic-runtime-debt"] = 1
        metrics["generic_debt_symbols"] = [
            {
                "operation_id": "workspace.example.report",
                "source_module": "agentic_workspace.workspace_runtime_primitives",
                "source_symbol": "_example_generated_command_behavior",
                "runtime_boundary_class": "generic-deterministic-runtime-debt",
            }
        ]
        _emit({"minimization": checker._runtime_boundary_minimization_report(metrics)})
        """
    )
    minimization = payload["minimization"]

    assert minimization["minimization_claim_allowed"] is False
    assert minimization["move_to_command_generation_candidate_count"] == 1
    assert minimization["move_to_command_generation_candidates"] == [
        {
            "operation_id": "workspace.example.report",
            "source_module": "agentic_workspace.workspace_runtime_primitives",
            "source_symbol": "_example_generated_command_behavior",
            "runtime_boundary_class": "generic-deterministic-runtime-debt",
        }
    ]
    assert minimization["route_by_runtime_boundary_class"]["generic-deterministic-runtime-debt"].startswith("move-to-command-generation:")


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
    assert runtime_metrics["accepted_runtime_symbol_count_by_minimization_category"]
    assert runtime_metrics["accepted_runtime_symbol_count_by_minimization_route"]["keep-as-hand-owned-primitive"] > 0
    assert runtime_metrics["output_fallback_symbol_count"] == runtime_metrics["accepted_output_emission_symbol_count"]
    assert runtime_metrics["python_bridge_step_count"] == 0
    assert runtime_metrics["python_bridge_symbols"] == []
    assert runtime_metrics["generic_debt_symbol_count"] == 0
    minimization = payload["runtime_boundary_minimization"]
    assert minimization["status"] == "not-minimized-hand-owned-boundaries-remain"
    assert minimization["minimization_claim_allowed"] is False
    assert minimization["remaining_hand_owned_symbol_count"] == runtime_metrics["accepted_runtime_symbol_count"]
    assert minimization["exact_runtime_boundary_inventory"]
    assert minimization["remaining_by_minimization_tracking_issue"]["#1364"] > 0
    target_freshness = payload["generated_target_freshness"]
    assert target_freshness["status"] == "fresh"
    assert target_freshness["target_families"] == ["python", "typescript"]
    assert target_freshness["rendered_output_count_by_family"]["python"] > 0
    assert target_freshness["rendered_output_count_by_family"]["typescript"] > 0
    assert payload["runtime_source_edit_policy"]["status"] == "available"
    assert "new-primitive-implementation" in payload["runtime_source_edit_policy"]["accepted_direct_edit_reasons"]
    assert "package-domain boundary" in payload["runtime_source_edit_policy"]["rejected_vague_reasons"]
    assert payload["lifecycle_dry_run_metrics"]["memory_payload_default_dry_run_operation_count"] >= 3
    assert payload["retired_command_generation_primitive_usage"]["ordinary_source_operation_usage_count"] == 0
    assert payload["retired_command_generation_primitive_usage"]["guard_reference_count"] > 0
    check_inventory = payload["generated_command_check_inventory"]
    assert check_inventory["generic_baseline_owner"] == "command-generation"
    assert "generated-output-freshness" in check_inventory["aw_kept_checks"]
    assert "primitive-executor-baseline" in check_inventory["delegated_or_removed_checks"]
    assert (
        "tests/test_workspace_defaults_cli.py::test_defaults_tiny_text_uses_generated_output" in check_inventory["removed_aw_owned_checks"]
    )
    assert "remove-from-aw entries must name exact retired ordinary check symbols" in check_inventory["remove_from_aw_rule"]


def test_python_completion_blocker_report_surfaces_command_generation_package_posture(capsys) -> None:
    checker = _load_checker()

    status = checker.main(["--python-completion-blockers"])

    assert status == 0
    output = capsys.readouterr().out
    match = re.search(
        r"Command-generation package: declared=(?P<declared>\d+\.\d+\.\d+(?:rc\d+)?) "
        r"installed=(?P<installed>\d+\.\d+\.\d+(?:rc\d+)?) source=(released-wheel|immutable-git-ref) compatible=true",
        output,
    )
    assert match is not None
    assert match.group("declared") == match.group("installed")


def test_memory_list_commands_are_portable_resource_python_projections() -> None:
    checker = _load_checker()

    errors = checker._validate_portable_resource_python_command_projection()

    assert errors == []
    list_files = (checker.REPO_ROOT / "generated/memory/python/commands/memory_list_files_report.py").read_text(encoding="utf-8")
    list_skills = (checker.REPO_ROOT / "generated/memory/python/commands/memory_list_skills_report.py").read_text(encoding="utf-8")
    planning_list_files = (checker.REPO_ROOT / "generated/planning/python/commands/planning_list_files_report.py").read_text(
        encoding="utf-8"
    )
    assert "packages/memory/bootstrap" not in list_files
    assert "packages/memory/skills" not in list_skills
    assert "packages/planning/bootstrap" not in planning_list_files
    assert "run_operation_ir(generated_operation_contract('memory.list-files.report'), args)" in list_files
    assert "run_operation_ir(generated_operation_contract('memory.list-skills.report'), args)" in list_skills
    assert "run_operation_ir(generated_operation_contract('planning.list-files.report'), args)" in planning_list_files


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
    checker.RECOVERED_CONFORMANCE_RETRIES.clear()
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
    assert "recovery_record=" in message
    assert checker.RECOVERED_CONFORMANCE_RETRIES[-1]["conformance_ref"] == "doctor.report.process"


def test_generated_python_conformance_strict_retry_recovery_fails(monkeypatch) -> None:
    checker = _load_checker()
    registries, errors = checker._adapter_conformance_cases_by_package()
    assert errors == []
    case = registries["root-workspace"]["doctor.report.process"]
    calls = []

    def fake_cases():
        return {"root-workspace": {"doctor.report.process": case}}, []

    def fake_run_cli_conformance_case(*, case, target, fixture_root):
        command = [*target.command, *case.success_args]
        calls.append(command)
        if len(calls) == 1:
            return checker.command_generation.CliConformanceResult(
                target=target.label,
                conformance_ref=case.conformance_ref,
                command=tuple(command),
                returncode=-11,
                stdout="",
                stderr="",
            ), []
        return checker.command_generation.CliConformanceResult(
            target=target.label,
            conformance_ref=case.conformance_ref,
            command=tuple(command),
            returncode=0,
            stdout='{"status": "ok"}\n',
            stderr="",
        ), []

    monkeypatch.setattr(checker, "_adapter_conformance_cases_by_package", fake_cases)
    monkeypatch.setattr(checker, "run_cli_conformance_case", fake_run_cli_conformance_case)
    monkeypatch.setenv("AGENTIC_GENERATED_STRICT_RETRY_RECOVERY", "1")

    errors = checker._run_python_adapter_conformance()

    assert any("runtime crash recovered after retry" in error for error in errors)
    assert len(calls) == 2


def test_python_docker_conformance_strict_retry_recovery_sets_container_env(monkeypatch) -> None:
    checker = _load_checker()
    calls: list[list[str]] = []

    def fake_run_step(command, **kwargs):
        calls.append(command)
        return 0

    monkeypatch.setattr(checker.shutil, "which", lambda name: "docker" if name == "docker" else None)
    monkeypatch.setattr(checker.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""))
    monkeypatch.setattr(checker, "_run_docker_step", fake_run_step)

    status = checker._run_docker(
        "generated-python-test",
        dockerfile="generated/python/Dockerfile.conformance",
        proof_label="generated Python package Docker conformance proof",
        require_docker=True,
        strict_retry_recovery=True,
    )

    assert status == 0
    assert ["docker", "run", "--rm", "-e", "AGENTIC_GENERATED_STRICT_RETRY_RECOVERY=1", "generated-python-test"] in calls


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


def test_static_generated_package_proof_fails_when_conformance_coverage_drifts() -> None:
    errors = _checker_case_errors(
        """
        checker._runnable_typescript_conformance_cases = lambda: ([], ["missing contract-backed case"])
        _emit({"errors": checker._validate_static_surfaces()})
        """
    )

    assert "static conformance coverage drift: missing contract-backed case" in errors


def test_generated_operation_cli_input_proof_scenarios(monkeypatch) -> None:
    checker = _load_checker()
    ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)

    errors = checker._validate_generated_operation_cli_inputs(ir)

    assert errors == []

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
        command_source_id="memory.route-report.cli",
        operation_contract_root="packages/memory/src/repo_memory_bootstrap/contracts",
        sibling_option_owners=checker._generated_command_option_owners(command_package["commands"]),
        generated_root=generated_root,
    )

    assert any(
        "memory-bootstrap route-report operation memory.route-report.report declares cli-option input 'verbose'" in error
        for error in errors
    )
    assert any(
        "source interface: src/agentic_workspace/contracts/command_package_ir.json "
        "$.packages[id=memory-bootstrap].commands[adapter_id=memory.route-report.cli].interface.options" in error
        for error in errors
    )
    assert any(
        "source operation: packages/memory/src/repo_memory_bootstrap/contracts/operations/memory.route-report.report.json" in error
        for error in errors
    )
    assert any("generated artifact: generated/memory/python/command_package.json" in error for error in errors)

    route_command = copy.deepcopy(next(command for command in command_package["commands"] if command["adapter_id"] == "memory.route.cli"))
    route_command["interface"]["options"] = [
        option for option in route_command["interface"]["options"] if option.get("name") != "pending_command"
    ]
    wrong_neighbor_option_owners = {"pending_command": ["memory.capture-note.cli"]}

    errors = checker._validate_operation_cli_inputs_for_interface(
        package_id="memory-bootstrap",
        command_path="route",
        interface=route_command["interface"],
        inherited_operation_ref=route_command["operation_ref"],
        inherited_option_names=set(),
        command_source_id="memory.route.cli",
        operation_contract_root="packages/memory/src/repo_memory_bootstrap/contracts",
        sibling_option_owners=wrong_neighbor_option_owners,
        generated_root=generated_root,
    )

    assert any(
        "option 'pending_command' appears on sibling command interface(s) ['memory.capture-note.cli'], "
        "but expected command interface is 'memory.route.cli'" in error
        for error in errors
    )

    nested_operation = {
        "inputs": [
            {"name": "format", "source": "cli-option"},
            {"name": "misplaced", "source": "cli-option"},
        ]
    }
    monkeypatch.setattr(checker, "_load_json", lambda path: nested_operation)
    nested_interface = {
        "name": "parent",
        "options": [{"name": "format"}],
        "subcommands": [
            {
                "name": "expected",
                "options": [],
                "operation_ref": {"id": "example.expected", "path": "operations/example.expected.json"},
            },
            {
                "name": "wrong",
                "options": [{"name": "misplaced"}],
                "operation_ref": {"id": "example.wrong", "path": "operations/example.wrong.json"},
            },
        ],
    }
    nested_option_owners = checker._generated_command_option_owners(
        [{"status": "generated", "adapter_id": "example.parent.cli", "interface": nested_interface}]
    )

    errors = checker._validate_operation_cli_inputs_for_interface(
        package_id="example-package",
        command_path="parent",
        interface=nested_interface,
        inherited_operation_ref={"id": "example.parent", "path": "operations/example.parent.json"},
        inherited_option_names=set(),
        command_source_id="example.parent.cli",
        operation_contract_root="packages/example/contracts",
        sibling_option_owners=nested_option_owners,
    )

    assert any(
        "option 'misplaced' appears on sibling command interface(s) ['example.parent.cli wrong'], "
        "but expected command interface is 'example.parent.cli expected'" in error
        for error in errors
    )

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


def test_operation_cli_input_visibility_uses_required_subcommand_interface(monkeypatch) -> None:
    checker = _load_checker()

    parent_interface = {
        "name": "checkpoint",
        "options": [{"name": "target"}, {"name": "format"}],
        "subcommands_required": True,
        "subcommands": [
            {
                "name": "write",
                "options": [
                    {"name": "target"},
                    {"name": "task"},
                    {"name": "issue"},
                    {"name": "durable_source"},
                    {"name": "replace"},
                    {"name": "format"},
                ],
                "operation_ref": {"id": "checkpoint.write", "path": "operations/checkpoint.write.json"},
            }
        ],
    }
    operation = {
        "inputs": [
            {"name": "target", "source": "cli-option"},
            {"name": "task", "source": "cli-option"},
            {"name": "issue", "source": "cli-option"},
            {"name": "durable_source", "source": "cli-option"},
            {"name": "replace", "source": "cli-option"},
            {"name": "format", "source": "cli-option"},
        ]
    }
    monkeypatch.setattr(checker, "_load_json", lambda path: operation)

    errors = checker._validate_operation_cli_inputs_for_interface(
        package_id="root-workspace",
        command_path="checkpoint",
        interface=parent_interface,
        inherited_operation_ref={"id": "checkpoint.write", "path": "operations/checkpoint.write.json"},
        inherited_option_names=set(),
        command_source_id="checkpoint.write.cli",
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


def test_static_generated_package_proof_rejects_static_surface_regressions() -> None:
    scenarios = [
        (
            "read-only-routing-for-mutating-targets",
            """
            ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
            memory_package = next(package for package in ir["packages"] if package["id"] == "memory-bootstrap")
            python_target = next(target for target in memory_package["targets"] if target["kind"] == "python")
            python_target["maturity_level_ref"] = "weak-agent-safe-adapter"
            python_target["generation_status"] = "weak-agent-safe-adapter"
            checker.load_workspace_command_package_ir = lambda *, repo_root: ir
            _emit({"errors": checker._validate_generated_mutation_target_routing(ir)})
            """,
            "weak-agent-safe-adapter while generated commands include mutation-capable effects",
        ),
        (
            "python-completion-proof-surface-drift",
            """
            ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
            ir["generation_policy"]["python_cli_completion"]["current_state"] = "full-generated-cli-complete"
            for item in ir["generation_policy"]["python_cli_completion"]["completion_gate"]["satisfied_by"]:
                if item["id"] == "python-docker-conformance":
                    item["proof"] = "uv run python scripts/check/check_generated_command_packages.py"
                    break
            checker.load_workspace_command_package_ir = lambda *, repo_root: ir
            _emit({"errors": checker._validate_python_cli_completion_policy(ir["generation_policy"]["python_cli_completion"])})
            """,
            "--python-docker-conformance --require-docker",
        ),
        (
            "missing-runtime-projection-inventory-entry",
            """
            original_manifest = checker.python_runtime_projection_inventory_manifest

            def fake_manifest() -> dict[str, object]:
                payload = original_manifest()
                payload = dict(payload)
                payload["entries"] = list(payload["entries"][:-1])
                return payload

            checker.python_runtime_projection_inventory_manifest = fake_manifest
            _emit({"errors": checker._validate_python_runtime_projection_inventory(full_completion=False)})
            """,
            "missing runtime projection entries",
        ),
        (
            "shipped-source-cli-backslide",
            r"""
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

            checker._tracked_python_source_files = lambda: [backslid_source]
            checker.Path.read_text = fake_read_text
            checker.Path.is_file = fake_is_file
            _emit({"errors": checker._validate_python_shipped_source_executable_retirement()})
            """,
            "parser construction",
        ),
        (
            "satisfied-gate-for-non-full-state",
            """
            ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
            ir["generation_policy"]["python_cli_completion"]["current_state"] = "adapter-layer-proven-not-full-generated-cli"
            ir["generation_policy"]["python_cli_completion"]["completion_gate"]["state"] = "satisfied"
            checker.load_workspace_command_package_ir = lambda *, repo_root: ir
            _emit({"errors": checker._validate_python_cli_completion_policy(ir["generation_policy"]["python_cli_completion"])})
            """,
            "cannot mark the Python CLI completion gate satisfied",
        ),
        (
            "missing-primitive-conformance-case",
            """
            checker.REQUIRED_PORTABLE_PRIMITIVE_CONFORMANCE = {"missing.primitive"}
            _emit({"errors": checker._validate_primitive_conformance_surface()})
            """,
            "primitive conformance is missing required primitive case: missing.primitive",
        ),
        (
            "remove-from-aw-ordinary-check-reappeared",
            """
            original_paths = checker._aw_owned_ordinary_python_check_paths
            original_symbols = checker._python_function_symbols
            retired_path = checker.REPO_ROOT / "tests" / "test_workspace_defaults_cli.py"

            checker._aw_owned_ordinary_python_check_paths = lambda: [retired_path]
            checker._python_function_symbols = lambda path: {"test_defaults_tiny_text_uses_generated_output"}
            _emit({"errors": checker._validate_generated_command_check_inventory_removals()})

            checker._aw_owned_ordinary_python_check_paths = original_paths
            checker._python_function_symbols = original_symbols
            """,
            "remove-from-aw retired check remains active",
        ),
    ]
    payloads = _run_checker_cases([source for _, source, _ in scenarios])
    for (label, _, expected_fragment), payload in zip(scenarios, payloads, strict=True):
        errors = _checker_payload_errors(payload)

        assert any(expected_fragment in error for error in errors), label


def test_static_generated_package_proof_requires_completion_gate_evidence() -> None:
    required_gate_items = [
        "python-docker-conformance",
        "representative-operation-ir-runtime-consumed",
        "operation-execution-inventory-exhaustive",
    ]
    sources = [
        f"""
            ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
            ir["generation_policy"]["python_cli_completion"]["current_state"] = "full-generated-cli-complete"
            ir["generation_policy"]["python_cli_completion"]["completion_gate"]["satisfied_by"] = [
                item
                for item in ir["generation_policy"]["python_cli_completion"]["completion_gate"]["satisfied_by"]
                if item["id"] != {item_id!r}
            ]
            checker.load_workspace_command_package_ir = lambda *, repo_root: ir
            _emit({{"errors": checker._validate_python_cli_completion_policy(ir["generation_policy"]["python_cli_completion"])}})
            """
        for item_id in required_gate_items
    ]
    payloads = _run_checker_cases(sources)
    for item_id, payload in zip(required_gate_items, payloads, strict=True):
        errors = _checker_payload_errors(payload)

        assert any(item_id in error for error in errors), item_id


def test_static_generated_package_proof_rejects_full_completion_with_runtime_debt() -> None:
    scenarios = [
        (
            "compatibility-handlers",
            """
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

            checker.load_workspace_command_package_ir = lambda *, repo_root: ir
            checker._load_json = fake_load_json
            _emit({"errors": checker._validate_python_operation_execution_inventory(ir)})
            """,
            "compatibility-runtime-handler",
        ),
        (
            "generic-runtime-debt",
            """
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

            checker.load_workspace_command_package_ir = lambda *, repo_root: ir
            checker._load_json = fake_load_json
            _emit({"errors": checker._validate_python_operation_execution_inventory(ir)})
            """,
            "generic deterministic behavior as runtime debt",
        ),
        (
            "generated-main-delegates-first",
            r"""
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

            checker.load_workspace_command_package_ir = lambda *, repo_root: ir
            checker.Path.read_text = fake_read_text
            _emit({"errors": checker._validate_full_python_completion_runtime_ownership(ir)})
            """,
            "missing generated-main boundary fragment",
        ),
        (
            "product-runtime-source",
            r"""
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

            checker.load_workspace_command_package_ir = lambda *, repo_root: ir
            checker.PYTHON_FULL_COMPLETION_BLOCKING_EXECUTABLE_PATHS = (product_runtime_source,)
            checker.Path.read_text = fake_read_text
            checker.Path.is_file = fake_is_file
            _emit({"errors": checker._validate_full_python_completion_executable_ownership(ir)})
            """,
            "scratch/product_runtime.py owns executable behavior markers",
        ),
        (
            "runtime-outputs-not-rendered",
            """
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

            checker.load_workspace_command_package_ir = lambda *, repo_root: ir
            checker.render_workspace_command_package_outputs = fake_render_outputs
            _emit({"errors": checker._validate_full_python_completion_executable_ownership(ir)})
            """,
            "not produced by command-generation render_outputs()",
        ),
        (
            "transitional-runtime-projection-debt",
            """
            original_manifest = checker.python_runtime_projection_inventory_manifest

            def fake_manifest() -> dict[str, object]:
                payload = original_manifest()
                payload = dict(payload)
                entries = [dict(entry) for entry in payload["entries"]]
                entries[0]["provenance_status"] = "transitional-generated-output-debt"
                entries[0]["blocking_full_completion"] = True
                payload["entries"] = entries
                return payload

            checker.python_runtime_projection_inventory_manifest = fake_manifest
            _emit({"errors": checker._validate_python_runtime_projection_inventory(full_completion=True)})
            """,
            "transitional-generated-output-debt",
        ),
    ]
    payloads = _run_checker_cases([code for _, code, _ in scenarios])
    for (label, _, expected_fragment), payload in zip(scenarios, payloads, strict=True):
        errors = _checker_payload_errors(payload)

        assert any(expected_fragment in error for error in errors), label


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


def test_static_generated_package_proof_accepts_current_static_surfaces() -> None:
    scenarios = [
        (
            "runtime-projection-inventory",
            """
            _emit({"errors": checker._validate_python_runtime_projection_inventory(full_completion=False)})
            """,
            lambda errors: errors == [],
        ),
        (
            "shipped-source-retirement",
            """
            _emit({"errors": checker._validate_python_shipped_source_executable_retirement()})
            """,
            lambda errors: errors == [],
        ),
        (
            "python-completion-gate",
            """
            ir = checker.load_workspace_command_package_ir(repo_root=checker.REPO_ROOT)
            _emit({"errors": checker._validate_python_cli_completion_policy(ir["generation_policy"]["python_cli_completion"])})
            """,
            lambda errors: not [error for error in errors if "Python CLI completion" in error or "Python completion" in error],
        ),
    ]
    payloads = _run_checker_cases([script for _, script, _ in scenarios])
    for (label, _, assertion), payload in zip(scenarios, payloads, strict=True):
        errors = _checker_payload_errors(payload)

        assert assertion(errors), label


def test_static_generated_package_proof_uses_behavior_detection_not_plain_keywords() -> None:
    errors = _checker_case_errors(
        r"""
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

        checker._tracked_python_source_files = lambda: [harmless_source]
        checker.Path.read_text = fake_read_text
        checker.Path.is_file = fake_is_file
        _emit({"errors": checker._validate_python_shipped_source_executable_retirement()})
        """
    )

    assert errors == []


def test_tracked_python_source_files_falls_back_without_git(monkeypatch) -> None:
    checker = _load_checker()

    monkeypatch.setattr(checker.shutil, "which", lambda command: None if command == "git" else checker.shutil.which(command))

    sources = checker._tracked_python_source_files()

    assert "src/agentic_workspace/contract_tooling.py" in sources
    assert "scripts/check/check_generated_command_packages.py" in sources


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


def test_typescript_runtime_check_rejects_python_handoff_behavior() -> None:
    checker = _load_checker()
    cli_text = "\n".join(
        [
            "import { spawnSync } from 'node:child_process';",
            "const nativeOperationIds = new Set([]);",
            "import { readFileSync, writeSync } from 'node:fs';",
            "const nativeContractCases = {};",
            "const selectedFields = {};",
            "const expectedFields = {};",
            "function contractProjection() { return fieldAssertions; }",
            "function splitRuntimeCommand(commandLine) { return [commandLine]; }",
            "const [runtimeExecutable, ...runtimeArgs] = splitRuntimeCommand(runtimeCommand);",
            "result = spawnSync(runtimeExecutable, [...runtimeArgs, ...argv], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });",
            "console.error('Adapter runtime handoff failed');",
        ]
    )
    runtime_text = "\n".join(
        [
            "export function runGeneratedOperation({ operationId, operationPath, values }) {}",
            "function runSteps(operation, values) {}",
            "function executePrimitive(primitive, values, args, operationId) {}",
            "if (primitive === 'typescript.domain.execute') return executeTypescriptDomainOperation(String(args.operation_id ?? operationId), values);",
            "throw new Error('unsupported native TypeScript primitive');",
        ]
    )
    host_support_text = "\n".join(
        [
            "export function executeHostPrimitive(primitive, values, args, operationId) {}",
            "function executeTypescriptDomainOperation(operationId, values) {}",
            "globalThis.hostDomainOperation = executeTypescriptDomainOperation",
        ]
    )

    errors = checker._validate_typescript_runtime_handoff_thinness(
        package="workspace-cli",
        cli_text=cli_text,
        runtime_text=runtime_text,
        host_support_text=host_support_text,
    )

    assert any("imports non-native runtime modules" in error for error in errors)
    assert any("Python/runtime-handoff marker: node:child_process" in error for error in errors)
    assert any("Python/runtime-handoff marker: Adapter runtime handoff failed" in error for error in errors)
    assert any("Python/runtime-handoff marker: nativeContractCases" in error for error in errors)
    assert any("Python/runtime-handoff marker: contractProjection" in error for error in errors)
    assert any("Python/runtime-handoff marker: selectedFields" in error for error in errors)
    assert any("Python/runtime-handoff marker: expectedFields" in error for error in errors)
    assert any("Python/runtime-handoff marker: fieldAssertions" in error for error in errors)


def test_typescript_native_execution_check_rejects_missing_ir_steps(tmp_path: Path) -> None:
    checker = _load_checker()
    package_root = tmp_path / "package"
    operation_path = package_root / "resources" / "operations" / "summary.report.json"
    operation_path.parent.mkdir(parents=True)
    operation_path.write_text(
        checker.json.dumps({"id": "summary.report", "ir_plan": {"status": "draft", "steps": []}}),
        encoding="utf-8",
    )
    command_package = {
        "commands": [
            {
                "status": "generated",
                "command": {"name": "summary"},
                "operation_ref": {"id": "summary.report", "path": "operations/summary.report.json"},
                "interface": {"name": "summary"},
            }
        ]
    }

    errors = checker._validate_typescript_native_operation_execution(
        package="workspace-cli",
        package_root=package_root,
        command_package=command_package,
    )

    assert errors == ["workspace-cli operation 'summary.report' is native but has no executable ir_plan.steps"]


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
