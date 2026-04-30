from __future__ import annotations

import importlib.util
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

    returncode = runner.main(
        [
            "--label",
            "timeout test",
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
    assert "started" in logs[0].read_text(encoding="utf-8")
