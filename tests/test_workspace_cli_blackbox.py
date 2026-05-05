from __future__ import annotations

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

    _assert_usage_error_without_traceback(result, expected="Did you mean: summary?")
    assert "Startup tip: run 'agentic-workspace start --profile tiny --task \"<task>\" --format json'" in result.stderr


def test_blackbox_selector_conflict_guides_to_correct_usage() -> None:
    result = _run_cli("report", "--profile", "full", "--section", "agent_aids", "--format", "json", cwd=Path.cwd())

    _assert_usage_error_without_traceback(result, expected="report selectors are mutually exclusive")
    assert "use either --profile or --section" in result.stderr
