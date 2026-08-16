from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agentic_workspace import cli
from agentic_workspace.config import WorkspaceUsageError, load_workspace_config
from agentic_workspace.runtime_compatibility import (
    READER_CONTRACT_EPOCH,
    admit_runtime_compatibility,
    target_root_from_argv,
)


def _write_config(
    root: Path,
    *,
    minimum_epoch: int | None = None,
    capabilities: tuple[str, ...] = (),
    invocation: str = "agentic-workspace",
) -> Path:
    config_dir = root / ".agentic-workspace"
    config_dir.mkdir(parents=True)
    lines = [
        "schema_version = 1",
        "",
        "[workspace]",
        f"cli_invoke = {json.dumps(invocation)}",
        "",
        "[cli_compatibility]",
        'contract_schema = "agentic-workspace/installed-state-compatibility/v1"',
    ]
    if minimum_epoch is not None:
        lines.append(f"minimum_reader_epoch = {minimum_epoch}")
    if capabilities:
        lines.append(f"required_reader_capabilities = {json.dumps(list(capabilities))}")
    path = config_dir / "config.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_matching_reader_is_admitted_before_managed_state(tmp_path: Path) -> None:
    _write_config(
        tmp_path,
        minimum_epoch=READER_CONTRACT_EPOCH,
        capabilities=("pre-state-runtime-compatibility-v1",),
    )

    admission = admit_runtime_compatibility(tmp_path)

    assert admission["status"] == "admitted"
    assert admission["managed_state_interpreted"] is False
    assert admission["observed_runtime"]["reader_epoch"] == READER_CONTRACT_EPOCH
    assert admission["identity_digest"].startswith("sha256:")
    loaded = load_workspace_config(target_root=tmp_path)
    assert loaded.cli_compatibility.minimum_reader_epoch == READER_CONTRACT_EPOCH
    assert loaded.cli_compatibility.required_reader_capabilities == ("pre-state-runtime-compatibility-v1",)
    assert not loaded.warnings


def test_new_reader_accepts_repository_without_epoch_contract(tmp_path: Path) -> None:
    _write_config(tmp_path)

    admission = admit_runtime_compatibility(tmp_path)

    assert admission["status"] == "admitted"
    assert admission["expected_repository"]["minimum_reader_epoch"] == 0


def test_forward_epoch_and_capability_fail_closed_without_loading_runtime(tmp_path: Path, monkeypatch, capsys) -> None:
    invocation = 'python "tools with spaces/agentic workspace.py" start --target .'
    _write_config(
        tmp_path,
        minimum_epoch=READER_CONTRACT_EPOCH + 1,
        capabilities=("future-reader-v2",),
        invocation=invocation,
    )
    loaded = False

    def forbidden_load():
        nonlocal loaded
        loaded = True
        raise AssertionError("generated runtime must not load")

    monkeypatch.setattr(cli, "_load_main", forbidden_load)

    assert cli._run_cli(["start", "--target", str(tmp_path), "--format", "json"]) == 2
    payload = json.loads(capsys.readouterr().out)

    assert loaded is False
    assert payload["status"] == "blocked"
    assert payload["managed_state_interpreted"] is False
    assert payload["recovery_command"] == invocation
    assert payload["failed_checks"] == ["minimum_reader_epoch", "required_reader_capabilities"]
    assert "owner-selection" in payload["unavailable_effects"]
    assert not {"selected_owner", "primary_action", "implementation_allowed", "completion_claim"} & payload.keys()


def test_missing_configured_source_runner_does_not_trigger_state_fallback(tmp_path: Path) -> None:
    missing_runner = "python missing/source runner.py"
    _write_config(tmp_path, minimum_epoch=READER_CONTRACT_EPOCH + 1, invocation=missing_runner)

    admission = admit_runtime_compatibility(tmp_path)

    assert admission["status"] == "blocked"
    assert admission["recovery_command"] == missing_runner
    assert admission["managed_state_interpreted"] is False


def test_target_parser_preserves_paths_with_spaces(tmp_path: Path) -> None:
    target = tmp_path / "repo with spaces"
    target.mkdir()

    assert target_root_from_argv(["summary", "--target", str(target)], cwd=tmp_path) == target.resolve()
    assert target_root_from_argv(["summary", f"--target={target}"], cwd=tmp_path) == target.resolve()


def test_full_config_rejects_malformed_reader_epoch(tmp_path: Path) -> None:
    _write_config(tmp_path, minimum_epoch=READER_CONTRACT_EPOCH)
    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace("minimum_reader_epoch = 1", "minimum_reader_epoch = 0"), encoding="utf-8"
    )

    admission = admit_runtime_compatibility(tmp_path)
    assert admission["status"] == "blocked"
    assert admission["failed_checks"] == ["compatibility_contract_shape"]
    with pytest.raises(WorkspaceUsageError, match="minimum_reader_epoch must be a positive integer"):
        load_workspace_config(target_root=tmp_path)


def _isolated_runtime(
    root: Path,
    *,
    old_reader: bool,
    handler_source: str,
) -> tuple[Path, Path]:
    runtime_root = root / ("old installed runtime" if old_reader else "current installed runtime")
    site = runtime_root / "site"
    package = site / "agentic_workspace"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "0.0.test"\n', encoding="utf-8")
    compatibility_source = (Path(__file__).resolve().parents[1] / "src/agentic_workspace/runtime_compatibility.py").read_text(
        encoding="utf-8"
    )
    if old_reader:
        compatibility_source = compatibility_source.replace("READER_CONTRACT_EPOCH = 1", "READER_CONTRACT_EPOCH = 0").replace(
            'READER_CAPABILITIES = ("pre-state-runtime-compatibility-v1",)', "READER_CAPABILITIES = ()"
        )
    (package / "runtime_compatibility.py").write_text(compatibility_source, encoding="utf-8")
    (package / "cli.py").write_text(
        (Path(__file__).resolve().parents[1] / "src/agentic_workspace/cli.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (package / "session_logging.py").write_text(
        "def run_with_session_logging(args, generated_main):\n    return generated_main(args)\n", encoding="utf-8"
    )
    generated = package / "_generated_cli_package_impl"
    generated.mkdir()
    (generated / "__init__.py").write_text("", encoding="utf-8")
    (generated / "cli.py").write_text(handler_source, encoding="utf-8")
    runner = runtime_root / "bin with spaces" / "agentic workspace.py"
    runner.parent.mkdir()
    runner.write_text("from agentic_workspace.cli import main\nraise SystemExit(main())\n", encoding="utf-8")
    return runner, site


def _invoke_isolated_runtime(runner: Path, site: Path, target: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(site), "PYTHONNOUSERSITE": "1", "PYTHONUTF8": "1"}
    return subprocess.run(
        [sys.executable, str(runner), "start", "--target", str(target), "--format", "json"],
        cwd=runner.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_independently_resolved_old_reader_is_rejected_before_any_authority(tmp_path: Path) -> None:
    target = tmp_path / "new checkout without source runner"
    configured = 'python "tools with spaces/agentic workspace.py"'
    _write_config(
        target,
        minimum_epoch=READER_CONTRACT_EPOCH,
        capabilities=("pre-state-runtime-compatibility-v1",),
        invocation=configured,
    )
    state_load = tmp_path / "generated-handler-loaded"
    handler_source = (
        "import json\n"
        f"from pathlib import Path\nPath({str(state_load)!r}).write_text('loaded', encoding='utf-8')\n"
        "def main(args):\n"
        "    print(json.dumps({'selected_owner': 'must-not-be-visible', 'implementation_allowed': True}))\n"
        "    return 0\n"
    )
    runner, site = _isolated_runtime(tmp_path, old_reader=True, handler_source=handler_source)

    result = _invoke_isolated_runtime(runner, site, target)

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["kind"] == "agentic-workspace/runtime-compatibility-incompatibility/v1"
    assert payload["status"] == "blocked"
    assert payload["managed_state_interpreted"] is False
    assert payload["recovery_command"] == configured
    assert payload["failed_checks"] == ["minimum_reader_epoch", "required_reader_capabilities"]
    assert not state_load.exists()
    assert (
        not {
            "selected_owner",
            "next_safe_action",
            "primary_action",
            "implementation_allowed",
            "mutation_authority",
            "proof",
            "closeout",
            "completion_claim",
        }
        & payload.keys()
    )


def test_independently_resolved_current_package_reader_proceeds_without_source_runner(tmp_path: Path) -> None:
    target = tmp_path / "checkout without scripts"
    _write_config(
        target,
        minimum_epoch=READER_CONTRACT_EPOCH,
        capabilities=("pre-state-runtime-compatibility-v1",),
        invocation="agentic-workspace",
    )
    state_load = tmp_path / "current-handler-loaded"
    handler_source = (
        "import json\n"
        f"from pathlib import Path\nPath({str(state_load)!r}).write_text('loaded', encoding='utf-8')\n"
        "def main(args):\n"
        "    print(json.dumps({'kind': 'fixture/current-reader', 'status': 'admitted', 'selected_owner': 'fixture-owner'}))\n"
        "    return 0\n"
    )
    runner, site = _isolated_runtime(tmp_path, old_reader=False, handler_source=handler_source)

    result = _invoke_isolated_runtime(runner, site, target)

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "kind": "fixture/current-reader",
        "status": "admitted",
        "selected_owner": "fixture-owner",
    }
    assert state_load.read_text(encoding="utf-8") == "loaded"
