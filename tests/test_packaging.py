from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path


def test_release_artifacts_have_one_runtime_and_no_host_state(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["uv", "build", "--wheel", "--sdist", "--out-dir", str(tmp_path)], check=True)
    wheel = next(tmp_path.glob("*.whl"))
    sdist = next(tmp_path.glob("*.tar.gz"))

    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
    assert any(name == "agentic_workspace/decision.py" for name in wheel_names)
    assert not any(name.startswith(("repo_", "generated/", "packages/", ".agentic-workspace/")) for name in wheel_names)

    with tarfile.open(sdist) as archive:
        sdist_names = archive.getnames()
    assert not any(
        "/.agentic-workspace/" in name or "/packages/" in name or "/generated/" in name for name in sdist_names
    )
