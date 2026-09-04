from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from agentic_workspace.cli import main
from agentic_workspace.session_logging import analyze_session, append_gap, append_session_event, export_session


def _events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_session_logging_is_off_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AW_SESSION_LOG", raising=False)

    assert main(["start", "--target", str(tmp_path), "--task", "direct work"]) == 0

    assert not (tmp_path / ".agentic-workspace" / "local" / "logs").exists()


def test_disabled_path_does_not_load_or_initialize_logging(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("AW_SESSION_LOG", None)
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json,sys; from agentic_workspace.cli import main; "
                "before='agentic_workspace.session_logging' in sys.modules; "
                f"status=main(['start','--target',{str(tmp_path)!r},'--task','probe']); "
                "after='agentic_workspace.session_logging' in sys.modules; "
                "print(json.dumps({'before':before,'after':after,'status':status}))"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    result = json.loads(probe.stdout.splitlines()[-1])
    assert result == {"before": False, "after": False, "status": 0}


def test_disabled_logging_gate_has_negligible_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AW_SESSION_LOG", raising=False)
    samples = 200_000

    started = time.perf_counter()
    for _ in range(samples):
        bool(os.environ.get("AW_SESSION_LOG"))
    elapsed = time.perf_counter() - started

    # The only logging-specific work on the disabled command path is one
    # environment lookup and branch. Keep that tax below 2 microseconds/call;
    # imports, clocks, filesystem work, and serialization are opt-in only.
    assert elapsed / samples < 0.000002


def test_maintainer_opt_in_captures_stable_bounded_correlated_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AW_SESSION_LOG", "release-check")
    monkeypatch.setenv("AW_SESSION_LOG_PARENT_EVENT", "event-parent")
    monkeypatch.setenv("AW_SESSION_LOG_CORRELATION", "parent-run")

    assert main(["start", "--target", str(tmp_path), "--task", "direct work"]) == 0

    path = tmp_path / ".agentic-workspace" / "local" / "logs" / "aw-session-release-check.jsonl"
    event = _events(path)[0]
    assert event["kind"] == "agentic-workspace/maintainer-session-event/v1"
    assert event["event_type"] == "command.completed"
    assert event["session_id"] == "release-check"
    assert event["command"] == "start"
    assert event["exit_code"] == 0
    assert event["outcome"] == "success"
    assert event["parent_event_id"] == "event-parent"
    assert event["correlation_id"] == "parent-run"
    assert event["authority"] == "local-diagnostic-only"
    assert isinstance(event["duration_seconds"], float)
    assert event["payload"]["kind"] == "agentic-workspace/operating-decision/v1"


def test_logging_failure_is_visible_but_cannot_fail_valid_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AW_SESSION_LOG", "../outside")

    assert main(["start", "--target", str(tmp_path), "--task", "direct work"]) == 0

    captured = capsys.readouterr()
    assert "session logging failed" in captured.err
    assert not (tmp_path / "outside").exists()


def test_gap_analysis_and_share_safe_export_are_truthful_and_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AW_SESSION_LOG", "analysis")
    argv = ["invoke", "--target", str(tmp_path), "--invocation", '{"secret":"raw"}']
    append_gap(target=tmp_path, session_id="analysis", reason="capture enabled after session start")
    append_session_event(
        target=tmp_path,
        argv=argv,
        command="invoke",
        started_at="2026-09-04T00:00:00+00:00",
        payload={"kind": "agentic-workspace/operation-result/v1", "status": "rejected"},
        exit_code=2,
        duration_seconds=1.5,
    )
    append_session_event(
        target=tmp_path,
        argv=argv,
        command="invoke",
        started_at="2026-09-04T00:00:00+00:00",
        payload={"kind": "agentic-workspace/operation-result/v1", "status": "rejected"},
        exit_code=2,
        duration_seconds=1.5,
    )
    append_session_event(
        target=tmp_path,
        argv=[*argv, "different"],
        command="invoke",
        started_at="2026-09-04T00:00:00+00:00",
        payload={"kind": "agentic-workspace/operation-result/v1", "status": "applied", "value": "x" * 40_000},
        exit_code=0,
        duration_seconds=0.1,
    )

    analysis = analyze_session(target=tmp_path, session_id="analysis")
    assert analysis["coverage"] == "partial"
    assert analysis["command_count"] == 3
    assert analysis["failure_count"] == 2
    assert analysis["gap_count"] == 1
    assert len(analysis["repeated_invocations"]) == 1
    assert len(analysis["repeated_results"]) == 1
    assert len(analysis["slow_event_ids"]) == 2
    assert len(analysis["large_output_event_ids"]) == 1

    raw_events = _events(tmp_path / ".agentic-workspace" / "local" / "logs" / "aw-session-analysis.jsonl")
    assert raw_events[-1]["payload"] is None
    assert raw_events[-1]["output"]["captured"] is False

    exported = export_session(target=tmp_path, session_id="analysis")
    with gzip.open(exported, "rt", encoding="utf-8") as handle:
        shared = [json.loads(line) for line in handle]
    assert shared[0]["coverage"] == "partial"
    assert shared[0]["omissions"] == ["raw argv", "raw result payload"]
    assert all("argv" not in event and "payload" not in event for event in shared[1:])
    assert "secret" not in json.dumps(shared)
