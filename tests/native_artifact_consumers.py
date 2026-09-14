"""Session-local installed consumers for the existing native owner scenarios."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

CURRENT: dict[str, Path] | None = None


def install(directory: Path, work: Path) -> dict[str, Path]:
    def one(pattern: str) -> Path:
        paths = list(directory.glob(pattern))
        if len(paths) != 1:
            raise ValueError(f"Expected one admission artifact {pattern}: {paths}")
        return paths[0].resolve()

    wheel = one("agentic_workspace-*.whl")
    npm_archive = one("agentic-workspace-workspace-cli-*.tgz")
    archive = one("agentic-workspace-native-*.zip")
    root = Path(__file__).resolve().parents[1]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, encoding="utf-8").strip()
    native = work / "native"
    native.mkdir()
    suffix = ".exe" if os.name == "nt" else ""
    with zipfile.ZipFile(archive) as packed:
        manifest = json.loads(packed.read("artifact.json"))
        if manifest["source_head"] != head:
            raise ValueError("Admission archive belongs to another source commit")
        for name, field in (("agentic-workspace", "cli_sha256"), ("agentic-workspace-core", "sha256")):
            data = packed.read(name + suffix)
            if hashlib.sha256(data).hexdigest() != manifest[field]:
                raise ValueError("Admission native binary digest mismatch")
            path = native / (name + suffix)
            path.write_bytes(data)
            path.chmod(0o755)

    venv = work / "venv"
    subprocess.run(["uv", "venv", "--python", sys.executable, str(venv)], check=True, capture_output=True)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(
        ["uv", "pip", "install", "--python", str(python), "--no-index", "--no-deps", "--no-cache", "--link-mode", "copy", str(wheel)],
        check=True,
        capture_output=True,
    )
    consumer = work / "consumer"
    consumer.mkdir()
    (consumer / "package.json").write_text('{"private":true}', encoding="utf-8")
    npm, node = shutil.which("npm"), shutil.which("node")
    if npm is None or node is None:
        raise ValueError("Admission requires installed Node and npm")
    subprocess.run(
        [npm, "install", "--offline", "--no-audit", "--no-fund", "--ignore-scripts", str(npm_archive)],
        cwd=consumer,
        check=True,
        capture_output=True,
    )
    package = consumer / "node_modules/@agentic-workspace/workspace-cli"
    node_manifest = json.loads((package / "src/native/bin/artifact.json").read_text(encoding="utf-8"))
    python_manifest_path = next(venv.rglob("agentic_workspace/_native/artifact.json"))
    python_manifest = json.loads(python_manifest_path.read_text(encoding="utf-8"))
    for identity in (node_manifest, python_manifest):
        if any(
            identity[key] != manifest[key]
            for key in ("source_head", "source_dirty", "package_version", "rust_toolchain", "sha256", "cli_sha256")
        ):
            raise ValueError("Installed admission package identities disagree")
    for name in ("agentic-workspace", "agentic-workspace-core"):
        data = (native / (name + suffix)).read_bytes()
        if (package / "src/native/bin" / (name + suffix)).read_bytes() != data or (
            python_manifest_path.parent / (name + suffix)
        ).read_bytes() != data:
            raise ValueError("Installed admission binary bytes disagree")
    return {
        "core": native / ("agentic-workspace-core" + suffix),
        "cli": native / ("agentic-workspace" + suffix),
        "python": python,
        "node": Path(node),
        "package": package,
        "cwd": consumer,
    }
