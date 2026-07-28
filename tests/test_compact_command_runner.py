from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "run_compact_command.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_compact_command", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_compact_runner_timeout_writes_tailed_log(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"

    returncode = runner.main(
        [
            "--label",
            "timeout test",
            "--run-id",
            "local",
            "--timeout-seconds",
            "0.1",
            "--failure-tail-lines",
            "20",
            "--",
            sys.executable,
            "-c",
            "import time; print('started', flush=True); time.sleep(30)",
        ]
    )

    captured = capsys.readouterr()
    logs = list(runner.LOG_ROOT.glob("*-timeout-test.log"))
    assert returncode == runner.TIMEOUT_EXIT_CODE
    assert len(logs) == 1
    assert "[timeout] timeout test" in captured.err
    assert "Command timed out after 0.1 seconds." in captured.err
    assert "Full log: scratch/command-logs/" in captured.err
    assert "Result: scratch/validation-results/local/timeout-test.json" in captured.err
    assert "started" in logs[0].read_text(encoding="utf-8")
    result = json.loads((tmp_path / "scratch" / "validation-results" / "local" / "timeout-test.json").read_text(encoding="utf-8"))
    assert result["kind"] == "agentic-workspace/validation-constituent-result/v1"
    assert result["constituent_id"] == "timeout-test"
    assert result["outcome"] == "timeout"
    assert result["timed_out"] is True
    assert result["log_path"].startswith("scratch/command-logs/")


def test_compact_runner_success_writes_machine_readable_result(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"

    returncode = runner.main(
        [
            "--label",
            "workspace lint",
            "--id",
            "lint.workspace",
            "--run-id",
            "run-1",
            "--depends-on",
            "sync.root",
            "--proof-purpose",
            "workspace lint proof",
            "--",
            sys.executable,
            "-c",
            "print('ok')",
        ]
    )

    captured = capsys.readouterr()
    result = json.loads((tmp_path / "scratch" / "validation-results" / "run-1" / "lint.workspace.json").read_text(encoding="utf-8"))
    assert returncode == 0
    assert "[run] workspace lint (lint.workspace)" in captured.out
    assert "[ok] workspace lint" in captured.out
    assert result["outcome"] == "passed"
    assert result["dependencies"] == ["sync.root"]
    assert result["proof_purpose"] == "workspace lint proof"
    assert result["log_path"] is None


def test_compact_runner_rejects_duplicate_constituent_in_same_run(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"

    args = [
        "--label",
        "workspace lint",
        "--id",
        "lint.workspace",
        "--run-id",
        "same-run",
        "--",
        sys.executable,
        "-c",
        "print('ok')",
    ]

    assert runner.main(args) == 0
    assert runner.main(args) == runner.DUPLICATE_EXIT_CODE
    captured = capsys.readouterr()
    assert "[duplicate] workspace lint (lint.workspace)" in captured.err
    assert "scratch/validation-results/same-run/lint.workspace.json" in captured.err
