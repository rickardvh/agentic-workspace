from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "start_chatgpt_review_poller.py"
_SPEC = importlib.util.spec_from_file_location("start_chatgpt_review_poller", _SCRIPT)
assert _SPEC and _SPEC.loader
poller = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = poller
_SPEC.loader.exec_module(poller)


def test_start_is_idempotent_for_a_live_recorded_poller(tmp_path: Path, monkeypatch) -> None:
    pid_path = tmp_path / poller.STATE_RELATIVE / "poller.pid"
    pid_path.parent.mkdir(parents=True)
    pid_path.write_text(json.dumps({"pid": 1234}) + "\n", encoding="utf-8")
    monkeypatch.setattr(poller, "_is_running", lambda pid: pid == 1234)

    assert poller.start(tmp_path) == {"status": "already-running", "pid": 1234}


def test_start_replaces_stale_pid_and_records_background_process(tmp_path: Path, monkeypatch) -> None:
    pid_path = tmp_path / poller.STATE_RELATIVE / "poller.pid"
    pid_path.parent.mkdir(parents=True)
    pid_path.write_text(json.dumps({"pid": 1234}) + "\n", encoding="utf-8")
    monkeypatch.setattr(poller, "_is_running", lambda _pid: False)

    class Process:
        pid = 5678

    captured = {}

    def popen(*args, **kwargs):
        captured["command"] = args[0]
        captured["kwargs"] = kwargs
        return Process()

    monkeypatch.setattr(poller.subprocess, "Popen", popen)
    result = poller.start(tmp_path)

    assert result["status"] == "started"
    assert json.loads(pid_path.read_text(encoding="utf-8"))["pid"] == 5678
    assert "--log-file" in captured["command"]
    if os.name == "nt":
        assert captured["kwargs"]["creationflags"] & poller.subprocess.CREATE_NEW_CONSOLE
        assert "stdout" not in captured["kwargs"]
