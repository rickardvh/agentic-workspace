from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "agentic-workspace", *args],
        cwd=cwd,
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
    result = _run_cli("summry", "--format", "json", cwd=Path.cwd())

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
