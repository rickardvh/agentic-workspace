from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from tests import native_artifact_consumers

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def shared_core_binary(tmp_path_factory) -> Iterator[Path]:
    artifact_dir = os.environ.get("AW_NATIVE_ARTIFACT_DIR")
    if artifact_dir:
        consumers = native_artifact_consumers.install(Path(artifact_dir), tmp_path_factory.mktemp("installed-native-consumers"))
        previous = os.environ.get("AGENTIC_WORKSPACE_CORE_BINARY")
        os.environ["AGENTIC_WORKSPACE_CORE_BINARY"] = str(consumers["core"])
        native_artifact_consumers.CURRENT = consumers
        try:
            yield consumers["core"]
        finally:
            native_artifact_consumers.CURRENT = None
            if previous is None:
                os.environ.pop("AGENTIC_WORKSPACE_CORE_BINARY", None)
            else:
                os.environ["AGENTIC_WORKSPACE_CORE_BINARY"] = previous
        return
    cargo = shutil.which("cargo")
    if cargo is None:
        fallback = Path.home() / ".cargo" / "bin" / ("cargo.exe" if os.name == "nt" else "cargo")
        cargo = str(fallback) if fallback.is_file() else None
    if cargo is None:
        pytest.fail("Rust cargo is required to build the shared operating-decision core")

    subprocess.run([cargo, "build", "-p", "agentic-workspace-core"], cwd=ROOT, check=True)
    binary = ROOT / "target" / "debug" / ("agentic-workspace-core.exe" if os.name == "nt" else "agentic-workspace-core")
    previous = os.environ.get("AGENTIC_WORKSPACE_CORE_BINARY")
    os.environ["AGENTIC_WORKSPACE_CORE_BINARY"] = str(binary)
    try:
        yield binary
    finally:
        if previous is None:
            os.environ.pop("AGENTIC_WORKSPACE_CORE_BINARY", None)
        else:
            os.environ["AGENTIC_WORKSPACE_CORE_BINARY"] = previous
