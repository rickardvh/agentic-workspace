from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".agentic-workspace"
    / "agent-aids"
    / "scripts"
    / "codex-session-identity"
    / "codex_session_identity.py"
)
_SPEC = importlib.util.spec_from_file_location("codex_session_identity_agent_aid", _SCRIPT)
assert _SPEC and _SPEC.loader
aid = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = aid
_SPEC.loader.exec_module(aid)


def _configured_target(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    config = target / ".agentic-workspace" / "config.local.toml"
    config.parent.mkdir(parents=True)
    config.write_text('schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n', encoding="utf-8")
    return target


def test_dry_run_maps_codex_identity_without_exposing_raw_value(tmp_path: Path, monkeypatch, capsys) -> None:
    target = _configured_target(tmp_path)
    monkeypatch.setenv(aid.HOST_IDENTITY_ENV, "private-codex-thread")
    monkeypatch.delenv(aid.AW_IDENTITY_ENV, raising=False)

    assert aid.main(["--dry-run", "--", "session-log", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"][:3] == ["uv", "run", "agentic-workspace"]
    assert payload["identity_bridge"] == {
        "source": "CODEX_THREAD_ID",
        "destination": "AW_SESSION_LOGICAL_IDENTITY",
        "raw_identity_exposed": False,
    }
    assert "private-codex-thread" not in json.dumps(payload)


def test_existing_portable_identity_takes_precedence(tmp_path: Path, monkeypatch) -> None:
    target = _configured_target(tmp_path)
    monkeypatch.setenv(aid.HOST_IDENTITY_ENV, "codex-thread")
    monkeypatch.setenv(aid.AW_IDENTITY_ENV, "portable-session")
    captured: dict[str, object] = {}

    def fake_run(command, *, cwd, env, check):
        captured.update(command=command, cwd=cwd, env=env, check=check)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(aid.subprocess, "run", fake_run)

    assert aid.main(["--", "status", "--target", str(target)]) == 0
    assert captured["cwd"] == target
    assert captured["env"][aid.AW_IDENTITY_ENV] == "portable-session"
    assert captured["check"] is False


def test_missing_host_identity_fails_without_invoking_aw(tmp_path: Path, monkeypatch, capsys) -> None:
    target = _configured_target(tmp_path)
    monkeypatch.delenv(aid.HOST_IDENTITY_ENV, raising=False)
    monkeypatch.delenv(aid.AW_IDENTITY_ENV, raising=False)

    assert aid.main(["--", "status", "--target", str(target)]) == 2

    payload = json.loads(capsys.readouterr().err)
    assert payload["status"] == "identity-unavailable"
    assert payload["rule"].startswith("Do not invent")
