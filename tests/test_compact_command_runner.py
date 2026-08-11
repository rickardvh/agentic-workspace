from __future__ import annotations

import importlib.util
import json
import subprocess
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
    assert "runtime" in result["repository"]
    manifest = json.loads((tmp_path / "scratch" / "validation-results" / "run-1" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["kind"] == "agentic-workspace/validation-run-manifest/v1"
    assert manifest["result_count"] == 1
    assert manifest["outcomes"] == {"passed": 1}
    assert manifest["results"][0]["constituent_id"] == "lint.workspace"
    assert manifest["critical_path_seconds"] >= 0
    assert abs(manifest["summed_work_seconds"] - manifest["critical_path_seconds"]) < 0.01


def test_compact_runner_records_no_heartbeat_for_short_success(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"

    returncode = runner.main(
        [
            "--label",
            "short proof",
            "--",
            sys.executable,
            "-c",
            "print('captured detail', flush=True)",
        ]
    )

    captured = capsys.readouterr()
    assert returncode == 0
    assert "[heartbeat]" not in captured.err
    assert "captured detail" not in captured.out
    assert "captured detail" not in captured.err
    assert "[ok] short proof" in captured.out
    result = json.loads((runner.RESULT_ROOT / "local" / "short-proof.json").read_text(encoding="utf-8"))
    assert result["heartbeat"]["count"] == 0
    assert result["heartbeat"]["claim"] == "process-liveness-only"


def test_run_command_emits_rate_limited_heartbeats_with_fake_clock_and_process(tmp_path) -> None:
    runner = _load_runner()
    clock = type("Clock", (), {"now": 0.0})()

    class FakeProcess:
        returncode = 0

        def __init__(self) -> None:
            self.waits = 0

        def communicate(self, timeout=None):
            self.waits += 1
            clock.now += float(timeout)
            if self.waits <= 3:
                raise subprocess.TimeoutExpired(["fake"], timeout)
            return "buffered child output", ""

        def poll(self):
            return None

    messages: list[str] = []
    returncode, stdout, stderr, timed_out, heartbeat = runner._run_command(
        ["fake"],
        cwd=tmp_path,
        timeout_seconds=None,
        progress_interval_seconds=10.0,
        progress_threshold_seconds=20.0,
        progress_label="long proof",
        constituent_id="proof.long",
        durable_result_path="scratch/validation-results/run/proof.long.json",
        monotonic=lambda: clock.now,
        process_factory=lambda *_args, **_kwargs: FakeProcess(),
        emit_heartbeat=messages.append,
    )

    assert returncode == 0
    assert stdout == "buffered child output"
    assert stderr == ""
    assert timed_out is False
    assert heartbeat["count"] == 3
    assert heartbeat["elapsed_seconds"] == [20.0, 30.0, 40.0]
    assert all("long proof (proof.long)" in message for message in messages)
    assert all("process liveness only" in message for message in messages)
    assert all("scratch/validation-results/run/proof.long.json" in message for message in messages)


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


def test_compact_runner_uses_plan_metadata_and_keeps_repeat_attempts(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"
    runner.PLAN_PATH = tmp_path / "docs" / "maintainer" / "validation-runtime-2435" / "validation-plan.json"
    runner.PLAN_PATH.parent.mkdir(parents=True)
    runner.PLAN_PATH.write_text(
        json.dumps(
            {
                "compact_label_map": {
                    "workspace lint": {
                        "id": "lint.workspace",
                        "dependencies": ["sync.all"],
                        "proof_purpose": "workspace lint proof from plan",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    args = [
        "--label",
        "workspace lint",
        "--run-id",
        "same-run",
        "--allow-repeat",
        "--",
        sys.executable,
        "-c",
        "print('ok')",
    ]

    assert runner.main(args) == 0
    assert runner.main(args) == 0
    captured = capsys.readouterr()
    assert "[run] workspace lint (lint.workspace)" in captured.out
    first = json.loads((tmp_path / "scratch" / "validation-results" / "same-run" / "lint.workspace.json").read_text(encoding="utf-8"))
    second = json.loads(
        (tmp_path / "scratch" / "validation-results" / "same-run" / "attempts" / "lint.workspace.attempt-2.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = json.loads((tmp_path / "scratch" / "validation-results" / "same-run" / "manifest.json").read_text(encoding="utf-8"))
    assert first["dependencies"] == ["sync.all"]
    assert second["proof_purpose"] == "workspace lint proof from plan"
    assert manifest["result_count"] == 2
