from __future__ import annotations

import os
from pathlib import Path

from agentic_workspace import reporting_support, workspace_runtime_core, workspace_runtime_startup


def test_command_targets_fall_back_to_absolute_paths_across_windows_drives(monkeypatch) -> None:
    target = Path("different-drive-target").resolve()

    def cross_drive(*_args, **_kwargs):
        raise ValueError("path and start are on different mounts")

    monkeypatch.setattr(os.path, "relpath", cross_drive)

    assert workspace_runtime_core._command_target_arg(target) == target.as_posix()
    assert workspace_runtime_startup._startup_command_target_arg(target) == target.as_posix()
    assert reporting_support._target_arg_from_payload({"target": str(target)}) == target.as_posix()
