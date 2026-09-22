from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from tests.test_native_public_cli import native_cli as native_cli

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_agentic_workspace.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_agentic_workspace", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load launcher from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_source_launcher_uses_documented_pair_and_preserves_explicit_selection(tmp_path, monkeypatch, capsys):
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("AGENTIC_WORKSPACE_CORE_BINARY", raising=False)
    resolver = tmp_path / "src/agentic_workspace/native_core.py"
    _write(resolver, (SCRIPT_PATH.parent.parent / "src/agentic_workspace/native_core.py").read_text())
    for marker in ("Cargo.lock", "src/core/Cargo.toml", "src/cli/rust/Cargo.toml"):
        _write(tmp_path / marker, "source fixture")
    suffix = ".exe" if os.name == "nt" else ""
    directory = tmp_path / "target/debug"
    cli = directory / f"agentic-workspace{suffix}"
    core = directory / f"agentic-workspace-core{suffix}"
    calls = []
    monkeypatch.setattr(module.subprocess, "call", lambda argv: calls.append(argv) or 0)
    for missing in (cli, core):
        other = core if missing == cli else cli
        _write(other, "fixture binary")
        missing.unlink(missing_ok=True)
        assert module._dispatch_to_source_cli(["start"]) == 2
        assert "cargo build --locked --workspace --bins" in capsys.readouterr().err
        assert not calls
    _write(core, "fixture binary")
    assert module._dispatch_to_source_cli(["start", "--task", "Unicode å context"]) == 0
    assert calls == [[str(cli), "start", "--task", "Unicode å context"]]
    monkeypatch.setenv("AGENTIC_WORKSPACE_CORE_BINARY", "explicit-core")
    assert module._dispatch_to_source_cli(["start"]) == 2
    assert "shared Agentic Workspace core is unavailable" in capsys.readouterr().err
    assert len(calls) == 1
    monkeypatch.delenv("AGENTIC_WORKSPACE_CORE_BINARY")
    # A damaged installed artifact must never borrow a source build.
    resolver.with_name("_native").mkdir()
    assert module._dispatch_to_source_cli(["start"]) == 2
    assert "shared Agentic Workspace core is unavailable" in capsys.readouterr().err
    assert len(calls) == 1


def test_source_launcher_reaches_current_native_start_without_environment_override(tmp_path, native_cli):
    env = dict(os.environ)
    env.pop("AGENTIC_WORKSPACE_CORE_BINARY", None)
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "start", "--target", str(tmp_path), "--task", "Read ordinary prose"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert packet["decision_packet"]["status"] == "direct"
    assert not (tmp_path / ".agentic-workspace").exists()


def test_launcher_maps_codex_thread_to_portable_session_identity_without_output_leak(monkeypatch, capsys) -> None:
    module = _load_module()
    monkeypatch.setenv(module.CODEX_SESSION_IDENTITY_ENV, "private-codex-thread")
    monkeypatch.delenv(module.AW_SESSION_IDENTITY_ENV, raising=False)
    monkeypatch.setattr(
        module,
        "_dispatch_to_source_cli",
        lambda _argv: 0 if os.environ[module.AW_SESSION_IDENTITY_ENV] == "private-codex-thread" else 1,
    )

    assert module.main(["start", "--target", ".", "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert "private-codex-thread" not in captured.out
    assert "private-codex-thread" not in captured.err


def test_launcher_preserves_existing_portable_session_identity(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setenv(module.CODEX_SESSION_IDENTITY_ENV, "codex-thread")
    monkeypatch.setenv(module.AW_SESSION_IDENTITY_ENV, "portable-session")
    monkeypatch.setattr(
        module,
        "_dispatch_to_source_cli",
        lambda _argv: 0 if os.environ[module.AW_SESSION_IDENTITY_ENV] == "portable-session" else 1,
    )

    assert module.main(["start", "--target", ".", "--format", "json"]) == 0


def test_launcher_leaves_session_identity_unset_outside_codex(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.delenv(module.CODEX_SESSION_IDENTITY_ENV, raising=False)
    monkeypatch.delenv(module.AW_SESSION_IDENTITY_ENV, raising=False)
    monkeypatch.setattr(
        module,
        "_dispatch_to_source_cli",
        lambda _argv: 0 if module.AW_SESSION_IDENTITY_ENV not in os.environ else 1,
    )

    assert module.main(["start", "--target", ".", "--format", "json"]) == 0


def test_codex_identity_vocabulary_stays_outside_portable_aw_surfaces() -> None:
    module = _load_module()
    repo_root = SCRIPT_PATH.parents[1]
    portable_roots = [repo_root / "src", repo_root / "packages", repo_root / "generated"]
    text_suffixes = {".json", ".md", ".mjs", ".py", ".toml", ".ts"}

    leaked_paths = []
    for root in portable_roots:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in text_suffixes:
                if module.CODEX_SESSION_IDENTITY_ENV in path.read_text(encoding="utf-8-sig"):
                    leaked_paths.append(path.relative_to(repo_root).as_posix())

    assert leaked_paths == []
