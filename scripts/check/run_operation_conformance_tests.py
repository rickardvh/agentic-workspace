#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import check_contract_tooling_surfaces as contract_tooling_check  # noqa: E402
import check_generated_command_packages as generated_package_check  # noqa: E402
from command_generation import (  # noqa: E402
    FunctionConformanceTarget,
    OperationConformanceCase,
    TypescriptFunctionConformanceTarget,
    materialize_case_fixture,
    run_function_conformance_case,
    run_typescript_function_conformance_case,
)
from command_generation.conformance import ProcessConformanceCase  # noqa: E402

from agentic_workspace.contract_tooling import (  # noqa: E402
    contract_schema,
    operation_artifact_registry_manifest,
    operation_conformance_test_ir_manifest,
)


def _selected_field(payload: object, field_path: str) -> object:
    current = payload
    for part in field_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise KeyError(field_path)
        current = current[part]
    return current


def _case_process_fixture(case: Mapping[str, object]) -> ProcessConformanceCase:
    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        raise ValueError(f"case {case.get('id')} has malformed operation_ref")
    expected = case.get("expected", {})
    if not isinstance(expected, Mapping):
        raise ValueError(f"case {case.get('id')} has malformed expected block")
    stdout = expected.get("stdout", {})
    stderr = expected.get("stderr", {})
    case_input = case.get("input", {})
    if not isinstance(case_input, Mapping):
        raise ValueError(f"case {case.get('id')} has malformed input block")
    fixture_files = case_input.get("fixture_files", {})
    if not isinstance(fixture_files, Mapping):
        raise ValueError(f"case {case.get('id')} fixture_files must be an object")
    stdout_fields = stdout.get("selected_fields", {}) if isinstance(stdout, Mapping) else {}
    stdout_contains = stdout.get("contains", []) if isinstance(stdout, Mapping) else []
    allow_stderr = bool(stderr.get("allow_non_empty", False)) if isinstance(stderr, Mapping) else False
    return ProcessConformanceCase(
        conformance_ref=str(operation_ref.get("conformance_ref") or case.get("id", "")),
        label=str(case.get("title", case.get("id", ""))),
        success_args=tuple(str(item) for item in case_input.get("argv", []) if isinstance(item, str)),
        selected_fields=lambda stdout_text, expected_fields=stdout_fields: _select_expected_fields(stdout_text, expected_fields),
        expected_fields=dict(stdout_fields) if isinstance(stdout_fields, Mapping) else {},
        stdout_contains=tuple(str(item) for item in stdout_contains if isinstance(item, str)),
        fixture_id=str(case_input.get("fixture_id", case.get("id", ""))),
        fixture_files={str(path): str(contents) for path, contents in fixture_files.items()},
        expected_exit=int(expected.get("exit_code", 0)),
        allow_stderr=allow_stderr,
    )


def _case_function_fixture(case: Mapping[str, object]) -> OperationConformanceCase:
    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        raise ValueError(f"case {case.get('id')} has malformed operation_ref")
    expected = case.get("expected", {})
    if not isinstance(expected, Mapping):
        raise ValueError(f"case {case.get('id')} has malformed expected block")
    result = expected.get("result", {})
    case_input = case.get("input", {})
    if not isinstance(case_input, Mapping):
        raise ValueError(f"case {case.get('id')} has malformed input block")
    result_fields = result.get("selected_fields", {}) if isinstance(result, Mapping) else {}
    error = expected.get("error", {})
    error_contains = error.get("contains", []) if isinstance(error, Mapping) else []
    return OperationConformanceCase(
        conformance_ref=str(operation_ref.get("conformance_ref") or case.get("id", "")),
        label=str(case.get("title", case.get("id", ""))),
        input_values=dict(case_input.get("json", {})) if isinstance(case_input.get("json", {}), Mapping) else {},
        selected_fields=lambda output, expected_fields=result_fields: _select_expected_result_fields(output, expected_fields),
        expected_fields=dict(result_fields) if isinstance(result_fields, Mapping) else {},
        expected_error_contains=tuple(str(item) for item in error_contains if isinstance(item, str)),
    )


def _select_expected_fields(stdout_text: str, expected_fields: object) -> dict[str, object]:
    if not isinstance(expected_fields, Mapping) or not expected_fields:
        return {}
    payload = json.loads(stdout_text)
    return {str(field): _selected_field(payload, str(field)) for field in expected_fields}


def _select_expected_result_fields(output: object, expected_fields: object) -> dict[str, object]:
    if not isinstance(expected_fields, Mapping) or not expected_fields:
        return {}
    return {str(field): _selected_field(output, str(field)) for field in expected_fields}


def _package_by_id(manifest: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    packages = manifest.get("packages", [])
    if not isinstance(packages, list):
        return {}
    return {str(package.get("id", "")): package for package in packages if isinstance(package, Mapping)}


def _typescript_command_for_package(package: Mapping[str, object]) -> tuple[str, list[str] | None]:
    node = shutil.which("node")
    if node is None:
        return "node-unavailable", None
    for target in package.get("targets", []):
        if isinstance(target, Mapping) and target.get("kind") == "typescript":
            cli = REPO_ROOT / str(target.get("generated_root", "")) / "src" / "cli.mjs"
            return "available", [node, str(cli)]
    return "target-unavailable", None


def _run_case_target(
    *,
    case: Mapping[str, object],
    artifact_registry: Mapping[str, Mapping[str, object]],
    target_kind: str,
    temp_root: Path,
    require_node: bool,
) -> dict[str, object]:
    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        return _result(case=case, target_kind=target_kind, state="fail", message="malformed operation_ref")
    artifact = _artifact_for_target(case, target_kind, artifact_registry)
    if artifact is None:
        return _result(case=case, artifact_registry=artifact_registry, target_kind=target_kind, state="fail", message="no registry artifact for target")
    package_id = str(artifact.get("package_id", operation_ref.get("package_id", "")))
    command_package_ir = generated_package_check.load_workspace_command_package_ir(repo_root=REPO_ROOT)
    package = _package_by_id(command_package_ir).get(package_id)
    if package is None:
        return _result(case=case, artifact_registry=artifact_registry, target_kind=target_kind, state="fail", message=f"unknown package {package_id!r}")
    adapter_id = str(artifact.get("adapter_id", "cli.process"))
    if target_kind == "python" and adapter_id == "python.function":
        return _run_python_function_case(case=case, artifact=artifact)
    if target_kind == "typescript" and adapter_id == "typescript.function":
        return _run_typescript_function_case(case=case, artifact=artifact, temp_root=temp_root, require_node=require_node)
    process_case = _case_process_fixture(case)
    fixture_root = materialize_case_fixture(
        case=process_case,
        root=temp_root / str(case.get("id", "case")).replace(".", "-") / target_kind,
    )
    if target_kind == "python":
        command = generated_package_check._python_command_for_package(package_id)
        env = generated_package_check._conformance_env()
    elif target_kind == "typescript":
        status, command = _typescript_command_for_package(package)
        if command is None:
            state = "fail" if require_node else "unavailable"
            return _result(case=case, artifact_registry=artifact_registry, target_kind=target_kind, state=state, message=status)
        env = generated_package_check._conformance_env(runtime="")
    else:
        return _result(case=case, artifact_registry=artifact_registry, target_kind=target_kind, state="skipped", message="target not selected")
    completed = subprocess.run(
        [*command, *process_case.success_args],
        cwd=fixture_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    failures = _evaluate_process_result(case=case, process_case=process_case, completed=completed, fixture_root=fixture_root)
    return {
        "case_id": str(case.get("id", "")),
        "behavioral_class": str(case.get("behavioral_class", "")),
        "operation_id": str(operation_ref.get("operation_id", "")),
        "artifact_id": str(artifact.get("artifact_id", "")) if isinstance(artifact, Mapping) else "",
        "adapter_id": str(artifact.get("adapter_id", "cli.process")) if isinstance(artifact, Mapping) else "cli.process",
        "conformance_ref": str(operation_ref.get("conformance_ref", "")),
        "target": target_kind,
        "state": "fail" if failures else "pass",
        "exit_code": completed.returncode,
        "selected_fields": _selected_fields_or_empty(process_case, completed.stdout) if not failures else {},
        "message": "; ".join(failures) if failures else "",
    }


def _run_python_function_case(*, case: Mapping[str, object], artifact: Mapping[str, object]) -> dict[str, object]:
    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        return _function_result(case=case, artifact=artifact, state="fail", message="malformed operation_ref")
    function_target = _python_function_target_for_artifact(artifact)
    if function_target is None:
        return _function_result(case=case, artifact=artifact, state="unavailable", message="python.function artifact has no importable symbol")
    function_case = _case_function_fixture(case)
    result, failures = run_function_conformance_case(case=function_case, target=function_target)
    return {
        "case_id": str(case.get("id", "")),
        "behavioral_class": str(case.get("behavioral_class", "")),
        "operation_id": str(operation_ref.get("operation_id", "")),
        "artifact_id": str(artifact.get("artifact_id", "")),
        "adapter_id": str(artifact.get("adapter_id", "python.function")),
        "conformance_ref": str(operation_ref.get("conformance_ref", "")),
        "target": "python",
        "state": "fail" if failures else "pass",
        "selected_fields": result.selected_fields if result is not None and result.selected_fields is not None else {},
        "message": "; ".join(failure.message for failure in failures),
    }


def _python_function_target_for_artifact(artifact: Mapping[str, object]) -> FunctionConformanceTarget | None:
    symbol = str(artifact.get("symbol", ""))
    if ":" not in symbol:
        return None
    module_name, function_name = symbol.rsplit(":", 1)
    if not module_name or not function_name:
        return None

    def invoke(values: Mapping[str, object]) -> object:
        module = __import__(module_name, fromlist=[function_name])
        function = getattr(module, function_name)
        return function(dict(values))

    return FunctionConformanceTarget(label=str(artifact.get("artifact_id", "python.function")), invoke=invoke)


def _typescript_runtime_symbol(artifact: Mapping[str, object]) -> tuple[Path, str] | None:
    symbol = str(artifact.get("symbol", ""))
    if ":" not in symbol:
        return None
    runtime_path, function_name = symbol.rsplit(":", 1)
    if not runtime_path or not function_name:
        return None
    return REPO_ROOT / runtime_path, function_name


def _run_typescript_function_case(
    *,
    case: Mapping[str, object],
    artifact: Mapping[str, object],
    temp_root: Path,
    require_node: bool,
) -> dict[str, object]:
    node = shutil.which("node")
    if node is None:
        state = "fail" if require_node else "unavailable"
        return _function_result(case=case, artifact=artifact, state=state, message="node-unavailable")
    runtime_symbol = _typescript_runtime_symbol(artifact)
    if runtime_symbol is None:
        return _function_result(case=case, artifact=artifact, state="unavailable", message="typescript.function artifact has no runtime symbol")
    runtime_path, function_name = runtime_symbol
    if not runtime_path.is_file():
        return _function_result(
            case=case,
            artifact=artifact,
            state="unavailable",
            message=f"typescript.function runtime is missing: {runtime_path.relative_to(REPO_ROOT).as_posix()}",
        )

    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        return _function_result(case=case, artifact=artifact, state="fail", message="malformed operation_ref")
    case_input = case.get("input", {})
    if not isinstance(case_input, Mapping):
        return _function_result(case=case, artifact=artifact, state="fail", message="malformed input block")
    process_case = _case_process_fixture(case)
    fixture_root = materialize_case_fixture(
        case=process_case,
        root=temp_root / str(case.get("id", "case")).replace(".", "-") / "typescript-function",
    )
    function_case = _case_function_fixture(case)
    result, failures = run_typescript_function_conformance_case(
        case=function_case,
        target=TypescriptFunctionConformanceTarget(
            label=str(artifact.get("artifact_id", "typescript.function")),
            runtime_path=runtime_path,
            operation_id=str(operation_ref.get("operation_id", "")),
            operation_path=str(operation_ref.get("operation_path", "")),
            cwd=fixture_root,
            node_command=node,
            function_name=function_name,
            env=generated_package_check._conformance_env(runtime=""),
        ),
    )
    return {
        "case_id": str(case.get("id", "")),
        "behavioral_class": str(case.get("behavioral_class", "")),
        "operation_id": str(operation_ref.get("operation_id", "")),
        "artifact_id": str(artifact.get("artifact_id", "")),
        "adapter_id": str(artifact.get("adapter_id", "typescript.function")),
        "conformance_ref": str(operation_ref.get("conformance_ref", "")),
        "target": "typescript",
        "state": "fail" if failures else "pass",
        "selected_fields": result.selected_fields if result is not None and result.selected_fields is not None else {},
        "message": "; ".join(failure.message for failure in failures),
    }


def _function_result(
    *,
    case: Mapping[str, object],
    artifact: Mapping[str, object],
    state: str,
    message: str,
) -> dict[str, object]:
    operation_ref = case.get("operation_ref", {})
    operation_id = operation_ref.get("operation_id", "") if isinstance(operation_ref, Mapping) else ""
    conformance_ref = operation_ref.get("conformance_ref", "") if isinstance(operation_ref, Mapping) else ""
    adapter_id = str(artifact.get("adapter_id", "python.function"))
    target = adapter_id.split(".", 1)[0] if "." in adapter_id else "python"
    return {
        "case_id": str(case.get("id", "")),
        "behavioral_class": str(case.get("behavioral_class", "")),
        "operation_id": str(operation_id),
        "artifact_id": str(artifact.get("artifact_id", "")),
        "adapter_id": adapter_id,
        "conformance_ref": str(conformance_ref),
        "target": target,
        "state": state,
        "message": message,
    }


def _artifact_by_id(registry: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    return {
        str(artifact.get("artifact_id", "")): artifact
        for artifact in registry.get("artifacts", [])
        if isinstance(artifact, Mapping)
    }


def _artifact_for_target(
    case: Mapping[str, object],
    target_kind: str,
    artifact_registry: Mapping[str, Mapping[str, object]],
) -> Mapping[str, object] | None:
    for artifact in case.get("artifacts", []):
        if isinstance(artifact, Mapping) and artifact.get("target") == target_kind:
            return artifact_registry.get(str(artifact.get("artifact_id", "")))
    return None

def _evaluate_process_result(
    *,
    case: Mapping[str, object],
    process_case: ProcessConformanceCase,
    completed: subprocess.CompletedProcess[str],
    fixture_root: Path,
) -> list[str]:
    failures: list[str] = []
    if completed.returncode != process_case.expected_exit:
        failures.append(f"expected exit {process_case.expected_exit}, got {completed.returncode}; stderr={completed.stderr!r}")
    expected = case.get("expected", {})
    stderr = expected.get("stderr", {}) if isinstance(expected, Mapping) else {}
    if completed.stderr.strip() and not process_case.allow_stderr:
        failures.append(f"unexpected stderr: {completed.stderr!r}")
    if isinstance(stderr, Mapping):
        missing_stderr = [str(item) for item in stderr.get("contains", []) if str(item) not in completed.stderr]
        if missing_stderr:
            failures.append(f"stderr missing substrings {missing_stderr!r}; stderr={completed.stderr!r}")
    missing_stdout = [item for item in process_case.stdout_contains if item not in completed.stdout]
    if missing_stdout:
        failures.append(f"stdout missing substrings {missing_stdout!r}; stdout={completed.stdout!r}")
    if process_case.expected_fields:
        try:
            selected = process_case.selected_fields(completed.stdout)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            failures.append(f"stdout selected fields unavailable: {exc}; stdout={completed.stdout!r}")
        else:
            if selected != process_case.expected_fields:
                failures.append(f"expected selected fields {process_case.expected_fields!r}, got {selected!r}")
    filesystem = expected.get("filesystem", {}) if isinstance(expected, Mapping) else {}
    if isinstance(filesystem, Mapping):
        for rel_path in filesystem.get("required_paths", []):
            if isinstance(rel_path, str) and not (fixture_root / rel_path).exists():
                failures.append(f"required path missing: {rel_path}")
        for rel_path in filesystem.get("forbidden_paths", []):
            if isinstance(rel_path, str) and (fixture_root / rel_path).exists():
                failures.append(f"forbidden path exists: {rel_path}")
    return failures


def _selected_fields_or_empty(process_case: ProcessConformanceCase, stdout: str) -> dict[str, object]:
    if not process_case.expected_fields:
        return {}
    try:
        return process_case.selected_fields(stdout)
    except (json.JSONDecodeError, KeyError, ValueError):
        return {}


def _result(
    *,
    case: Mapping[str, object],
    artifact_registry: Mapping[str, Mapping[str, object]],
    target_kind: str,
    state: str,
    message: str,
) -> dict[str, object]:
    operation_ref = case.get("operation_ref", {})
    operation_id = operation_ref.get("operation_id", "") if isinstance(operation_ref, Mapping) else ""
    conformance_ref = operation_ref.get("conformance_ref", "") if isinstance(operation_ref, Mapping) else ""
    artifact = _artifact_for_target(case, target_kind, artifact_registry)
    return {
        "case_id": str(case.get("id", "")),
        "behavioral_class": str(case.get("behavioral_class", "")),
        "operation_id": str(operation_id),
        "artifact_id": str(artifact.get("artifact_id", "")) if isinstance(artifact, Mapping) else "",
        "adapter_id": str(artifact.get("adapter_id", "")) if isinstance(artifact, Mapping) else "",
        "conformance_ref": str(conformance_ref),
        "target": target_kind,
        "state": state,
        "message": message,
    }


def _case_targets(case: Mapping[str, object], target_selection: str) -> list[str]:
    declared = [str(target.get("kind", "")) for target in case.get("targets", []) if isinstance(target, Mapping)]
    if target_selection == "all":
        return declared
    if target_selection == "parity":
        return declared if case.get("behavioral_class") == "cross-target-parity" else []
    return [target_selection] if target_selection in declared else []


def _append_parity_results(
    results: list[dict[str, object]],
    case: Mapping[str, object],
    selected_targets: list[str],
    artifact_registry: Mapping[str, Mapping[str, object]],
) -> None:
    if case.get("behavioral_class") != "cross-target-parity" or len(selected_targets) < 2:
        return
    case_id = str(case.get("id", ""))
    target_results = [result for result in results if result.get("case_id") == case_id and result.get("target") in selected_targets]
    if any(result.get("state") == "fail" for result in target_results):
        results.append(_result(case=case, artifact_registry=artifact_registry, target_kind="parity", state="fail", message="one or more target runs failed"))
        return
    unavailable = [result for result in target_results if result.get("state") == "unavailable"]
    if unavailable:
        results.append(
            _result(case=case, artifact_registry=artifact_registry, target_kind="parity", state="unavailable", message="one or more targets unavailable")
        )
        return
    comparable = [(result.get("exit_code"), result.get("selected_fields")) for result in target_results]
    state = "pass" if len(set(json.dumps(item, sort_keys=True) for item in comparable)) == 1 else "fail"
    message = "" if state == "pass" else f"parity drift across targets: {comparable!r}"
    results.append(_result(case=case, artifact_registry=artifact_registry, target_kind="parity", state=state, message=message))


def run_ir_cases(*, target_selection: str, case_filter: set[str], require_node: bool) -> dict[str, object]:
    manifest = operation_conformance_test_ir_manifest()
    registry = operation_artifact_registry_manifest()
    schema_errors = sorted(Draft202012Validator(contract_schema("operation_conformance_test_ir.schema.json")).iter_errors(manifest), key=str)
    registry_schema_errors = sorted(Draft202012Validator(contract_schema("operation_artifact_registry.schema.json")).iter_errors(registry), key=str)
    semantic_errors = contract_tooling_check._validate_operation_conformance_test_ir(manifest) + contract_tooling_check._validate_operation_artifact_registry(registry)
    all_schema_errors = schema_errors + registry_schema_errors
    if all_schema_errors or semantic_errors:
        return {
            "kind": "operation-conformance-proof/v1",
            "summary": {"state": "fail", "failure_count": len(all_schema_errors) + len(semantic_errors)},
            "cases": [],
            "validation_errors": [error.message for error in all_schema_errors] + semantic_errors,
        }
    cases = [case for case in manifest["initial_cases"] if not case_filter or str(case["id"]) in case_filter]
    artifact_registry = _artifact_by_id(registry)
    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="agentic-workspace-operation-conformance-test-ir-") as tmp:
        temp_root = Path(tmp)
        for case in cases:
            selected_targets = _case_targets(case, target_selection)
            if not selected_targets:
                results.append(_result(case=case, artifact_registry=artifact_registry, target_kind=target_selection, state="skipped", message="case not selected"))
                continue
            for target_kind in selected_targets:
                results.append(
                    _run_case_target(
                        case=case,
                        artifact_registry=artifact_registry,
                        target_kind=target_kind,
                        temp_root=temp_root,
                        require_node=require_node,
                    )
                )
            _append_parity_results(results, case, selected_targets, artifact_registry)
    fail_count = sum(1 for result in results if result.get("state") == "fail")
    unavailable_count = sum(1 for result in results if result.get("state") == "unavailable")
    skipped_count = sum(1 for result in results if result.get("state") == "skipped")
    return {
        "kind": "operation-conformance-proof/v1",
        "target_selection": target_selection,
        "artifact_registry": "operation_artifact_registry.json",
        "case_count": len(cases),
        "summary": {
            "state": "fail" if fail_count else "pass",
            "pass_count": sum(1 for result in results if result.get("state") == "pass"),
            "fail_count": fail_count,
            "unavailable_count": unavailable_count,
            "skipped_count": skipped_count,
        },
        "cases": results,
    }


def _print_text(payload: Mapping[str, object]) -> None:
    summary = payload.get("summary", {})
    state = summary.get("state") if isinstance(summary, Mapping) else "unknown"
    print(f"Operation conformance tests: {state}")
    if isinstance(summary, Mapping):
        print(
            "Cases: "
            f"pass={summary.get('pass_count', 0)} "
            f"fail={summary.get('fail_count', 0)} "
            f"unavailable={summary.get('unavailable_count', 0)} "
            f"skipped={summary.get('skipped_count', 0)}"
        )
    for result in payload.get("cases", []):
        if isinstance(result, Mapping) and result.get("state") != "pass":
            print(f"- {result.get('case_id')} [{result.get('target')}]: {result.get('state')} {result.get('message', '')}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run operation conformance tests.")
    parser.add_argument("--target", choices=["all", "python", "typescript", "parity"], default="all")
    parser.add_argument("--case", action="append", default=[], help="Run only a specific IR case id. May be repeated.")
    parser.add_argument("--require-node", action="store_true", help="Fail when TypeScript cases are selected but Node is unavailable.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = run_ir_cases(target_selection=str(args.target), case_filter=set(args.case), require_node=bool(args.require_node))
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_text(payload)
    return 1 if payload.get("summary", {}).get("state") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
