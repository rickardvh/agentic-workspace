from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
from tests.workspace_cli_support import aw_subprocess_env

from agentic_workspace import cli as source_cli


def _run_cli(
    *args: str,
    cwd: Path,
    purpose_id: str | None = None,
    scenario_id: str | None = None,
    invocation_class: str | None = None,
    expected_exit: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = None
    if any((purpose_id, scenario_id, invocation_class, expected_exit)):
        env = aw_subprocess_env(
            purpose_id=purpose_id,
            scenario_id=scenario_id,
            invocation_class=invocation_class,
            expected_exit=expected_exit,
        )
    return subprocess.run(
        ["uv", "run", "agentic-workspace", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _assert_usage_error_without_traceback(result: subprocess.CompletedProcess[str], *, expected: str) -> None:
    combined = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 2
    assert "Traceback" not in combined
    assert "usage: agentic-workspace" in result.stderr
    assert expected in result.stderr


def test_blackbox_invalid_targets_report_usage_errors_without_tracebacks(tmp_path: Path) -> None:
    repo_root = Path.cwd()
    missing = tmp_path / "missing"

    cases = [
        ("modules", "--target", str(missing), "--format", "json"),
        ("start", "--target", str(missing), "--format", "json"),
        ("summary", "--target", str(missing), "--format", "json"),
        ("preflight", "--target", str(missing), "--format", "json"),
        ("implement", "--target", str(missing), "--format", "json"),
        ("skills", "--target", str(missing), "--format", "json"),
    ]

    for args in cases:
        result = _run_cli(*args, cwd=repo_root)
        _assert_usage_error_without_traceback(result, expected="Target path does not exist")


def test_blackbox_near_miss_command_guides_to_startup() -> None:
    result = _run_cli(
        "summry",
        "--format",
        "json",
        cwd=Path.cwd(),
        purpose_id="blackbox-recovery",
        scenario_id="near-miss-summary",
        invocation_class="negative-fixture",
        expected_exit="failure",
    )

    combined = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 2
    assert "Traceback" not in combined
    payload = json.loads(result.stdout)
    assert payload["kind"] == "agentic-workspace/retryable-cli-error/v1"
    assert payload["exit_status"] == 2
    assert payload["failure_class"] == "invalid-command"
    assert payload["safe_to_retry"] is True
    assert payload["suggested_command"] == "agentic-workspace summary --format json"
    assert "Did you mean: summary?" in payload["message"]
    assert "Startup tip: run 'agentic-workspace start --task \"<task>\" --format json'" in payload["message"]


def test_unexpected_json_runtime_exception_has_structured_recovery(monkeypatch, capsys) -> None:
    def fail(_argv: list[str]) -> int:
        raise RuntimeError("representative package failure")

    monkeypatch.setattr(source_cli, "_load_main", lambda: fail)
    assert source_cli.main(["summary", "--format", "json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/runtime-error/v1"
    assert payload["exception_class"] == "RuntimeError"
    assert payload["failure_class"] == "unexpected-runtime-exception"
    assert payload["safe_to_retry"] is False
    assert payload["completion_boundary"] == "command-did-not-complete"


def test_blackbox_selector_conflict_guides_to_correct_usage() -> None:
    result = _run_cli("report", "--verbose", "--section", "agent_aids", "--format", "json", cwd=Path.cwd())

    combined = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 2
    assert "Traceback" not in combined
    payload = json.loads(result.stdout)
    assert payload["kind"] == "agentic-workspace/retryable-cli-error/v1"
    assert payload["failure_class"] == "selector-conflict"
    assert payload["safe_to_retry"] is True
    assert "report detail selectors are mutually exclusive" in payload["message"]
    assert any("--section agent_aids --format json" in command and "--verbose" not in command for command in payload["alternatives"])


def test_blackbox_module_cli_retryable_error_kind_uses_module_namespace() -> None:
    result = subprocess.run(
        ["uv", "run", "agentic-memory", "rout", "--format", "json"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["kind"] == "agentic-memory/retryable-cli-error/v1"


@pytest.mark.parametrize(("module", "misspelled", "expected"), [("memory", "rout", "route"), ("planning", "repor", "report")])
def test_nested_module_recovery_is_canonical_and_executable(module: str, misspelled: str, expected: str) -> None:
    result = _run_cli(module, module, misspelled, "--target", ".", "--format", "json", cwd=Path.cwd())
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    suggested = payload["suggested_command"]
    assert suggested.startswith(f"agentic-workspace {module} {expected}")
    assert f"{module} {module}" not in suggested

    rerun = subprocess.run(shlex.split(suggested), cwd=Path.cwd(), capture_output=True, text=True, encoding="utf-8", check=False)
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr
    assert payload["failure_class"] == "invalid-command"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required for generated TypeScript recovery proof")
@pytest.mark.parametrize(("module", "misspelled", "expected"), [("memory", "rout", "route"), ("planning", "repor", "report")])
def test_generated_typescript_recovery_is_ir_derived_and_round_trips(module: str, misspelled: str, expected: str) -> None:
    result = subprocess.run(
        ["node", "generated/workspace/typescript/src/cli.mjs", module, module, misspelled, "--target", ".", "--format", "json"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    suggested = payload["suggested_command"]
    assert suggested.startswith(f"agentic-workspace {module} {expected}")
    assert f"{module} {module}" not in suggested

    rerun = subprocess.run(shlex.split(suggested), cwd=Path.cwd(), capture_output=True, text=True, encoding="utf-8", check=False)
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr


def test_generated_typescript_root_recovery_round_trips() -> None:
    result = subprocess.run(
        ["node", "generated/workspace/typescript/src/cli.mjs", "statuz", "--format", "json"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 2
    suggested = json.loads(result.stdout)["suggested_command"]
    assert suggested.startswith("agentic-workspace status")
    rerun = subprocess.run(shlex.split(suggested), cwd=Path.cwd(), capture_output=True, text=True, encoding="utf-8", check=False)
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr


def test_generated_recovery_routes_required_root_structure_to_help() -> None:
    argv = ["checkpoin", "--format", "json"]
    python_result = _run_cli(*argv, cwd=Path.cwd())
    typescript_result = subprocess.run(
        ["node", "generated/workspace/typescript/src/cli.mjs", *argv],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    python_payload = json.loads(python_result.stdout)
    typescript_payload = json.loads(typescript_result.stdout)
    assert python_payload["suggested_command"] == typescript_payload["suggested_command"] == "agentic-workspace checkpoint --help"
    assert python_payload["safe_to_retry"] is typescript_payload["safe_to_retry"] is True
    rerun = subprocess.run(
        shlex.split(python_payload["suggested_command"]), cwd=Path.cwd(), capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr


def test_generated_typescript_unrelated_root_typo_has_no_unsafe_recovery() -> None:
    result = subprocess.run(
        ["node", "generated/workspace/typescript/src/cli.mjs", "zzzzzz", "--format", "json"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["suggested_command"] == ""
    assert payload["safe_to_retry"] is False


def test_generated_typescript_nested_recovery_preserves_spaced_argument(tmp_path: Path) -> None:
    target = tmp_path / "target with spaces"
    target.mkdir()
    result = subprocess.run(
        ["node", "generated/workspace/typescript/src/cli.mjs", "memory", "memory", "rout", "--target", str(target), "--format", "json"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 2
    suggested = json.loads(result.stdout)["suggested_command"]
    assert str(target) in suggested
    rerun = subprocess.run(shlex.split(suggested), cwd=Path.cwd(), capture_output=True, text=True, encoding="utf-8", check=False)
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr


@pytest.mark.parametrize(
    "argv",
    [
        ["statuz", "--format", "json"],
        ["stauts", "--format", "json"],
        ["zzzzzz", "--format", "json"],
        ["memory", "memory", "rout", "--target", ".", "--format", "json"],
        ["planning", "planning", "repor", "--target", ".", "--format", "json"],
    ],
)
def test_generated_python_and_typescript_recovery_match(argv: list[str]) -> None:
    python_result = _run_cli(*argv, cwd=Path.cwd())
    typescript_result = subprocess.run(
        ["node", "generated/workspace/typescript/src/cli.mjs", *argv],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert python_result.returncode == typescript_result.returncode == 2
    python_payload = json.loads(python_result.stdout)
    typescript_payload = json.loads(typescript_result.stdout)
    for field in ("suggested_command", "safe_to_retry", "failure_class"):
        assert python_payload[field] == typescript_payload[field]
    if argv[0] == "stauts":
        assert python_payload["suggested_command"].startswith("agentic-workspace status")


def test_generated_typescript_strict_preflight_refuses_without_token() -> None:
    result = subprocess.run(
        ["node", "generated/workspace/typescript/src/cli.mjs", "upgrade", "--dry-run", "--strict-preflight", "--format", "json"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 2
    assert "Strict preflight gate is enabled" in result.stderr


def test_generated_python_recovery_uses_command_ir_not_parser_error_choices() -> None:
    generated_cli = (Path.cwd() / "generated/workspace/python/cli.py").read_text(encoding="utf-8")
    assert "_extract_command_choices" not in generated_cli
    assert "_authoritative_command_authority(argv)" in generated_cli
    assert "_authoritative_command_choices(authority)" in generated_cli


def test_blackbox_memory_route_task_misuse_guides_to_memory_consult() -> None:
    result = _run_cli(
        "memory",
        "route",
        "--target",
        ".",
        "--task",
        "Prioritise open GitHub issues for planning intake",
        "--format",
        "json",
        cwd=Path.cwd(),
        purpose_id="blackbox-memory-route",
        scenario_id="task-misuse-guides-consult",
        invocation_class="product-operation",
        expected_exit="success",
    )

    assert result.returncode == 0
    assert "Traceback" not in f"{result.stdout}\n{result.stderr}"
    assert '"task_supplied": true' in result.stdout
    assert '"task_used_for_matching": false' in result.stdout


def test_blackbox_memory_capture_note_accepts_stage_and_task_context() -> None:
    result = _run_cli(
        "memory",
        "capture-note",
        "--target",
        ".",
        "--slug",
        "memory-decision-packet-closeout-state-evidence",
        "--summary",
        "Closeout Memory decision states are enforced by runtime contract and tests.",
        "--files",
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "tests/test_workspace_summary_cli.py",
        "--stage",
        "closeout",
        "--task",
        "Route reusable learning before completion",
        "--format",
        "json",
        cwd=Path.cwd(),
    )

    assert result.returncode == 0
    assert "Traceback" not in f"{result.stdout}\n{result.stderr}"
    assert '"stage": "closeout"' in result.stdout
    assert '"task_supplied": true' in result.stdout


def test_blackbox_memory_create_note_supports_local_dry_run() -> None:
    result = _run_cli(
        "memory",
        "create-note",
        "--target",
        ".",
        "--slug",
        "blackbox-local-python-invocation-dry-run",
        "--summary",
        "Bare python is unavailable in this local shell.",
        "--local",
        "--local-reason",
        "machine-local shell behavior",
        "--dry-run",
        "--format",
        "json",
        cwd=Path.cwd(),
    )

    assert result.returncode == 0
    assert "Traceback" not in f"{result.stdout}\n{result.stderr}"
    assert '"kind": "would create"' in result.stdout
    assert ".agentic-workspace/local/memory/blackbox-local-python-invocation-dry-run.md" in result.stdout
