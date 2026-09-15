from __future__ import annotations

from pathlib import Path

from agentic_workspace.config import load_workspace_config
from agentic_workspace.runtime_compatibility import (
    admit_runtime_compatibility,
    target_root_from_argv,
)


def _write_config(root: Path) -> Path:
    path = root / ".agentic-workspace/config.toml"
    path.parent.mkdir(parents=True)
    path.write_text('[workspace]\ncli_invoke = "agentic-workspace"\n', encoding="utf-8")
    return path


def test_current_source_is_admitted_before_managed_state(tmp_path: Path) -> None:
    _write_config(tmp_path)
    admission = admit_runtime_compatibility(tmp_path)
    assert admission["status"] == "admitted"
    assert admission["managed_state_interpreted"] is False
    assert admission["identity_digest"].startswith("sha256:")
    assert not load_workspace_config(target_root=tmp_path).warnings


def test_target_parser_preserves_paths_with_spaces(tmp_path: Path) -> None:
    target = tmp_path / "repo with spaces"
    target.mkdir()

    assert target_root_from_argv(["summary", "--target", str(target)], cwd=tmp_path) == target.resolve()
    assert target_root_from_argv(["summary", f"--target={target}"], cwd=tmp_path) == target.resolve()


def test_invalid_configuration_cannot_disappear_before_reader_admission(tmp_path: Path) -> None:
    source = _write_config(tmp_path)
    source.write_text("[broken")
    assert admit_runtime_compatibility(tmp_path)["status"] == "blocked"
