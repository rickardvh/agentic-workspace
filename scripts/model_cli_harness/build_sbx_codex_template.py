"""Build and load the repo-owned Codex Docker Sandbox template."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCKERFILE = REPO_ROOT / "tools" / "model-cli-harness" / "sandbox" / "codex" / "Dockerfile"
DEFAULT_TAG = "agentic-workspace/codex-sbx:local"
DEFAULT_OUTPUT = REPO_ROOT / ".agentic-workspace" / "local" / "scratch" / "model-cli-harness-sbx-template" / "codex-sbx.tar"


def _run(command: list[str], *, cwd: Path = REPO_ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)  # noqa: S603


def _sbx_path(explicit: str | None) -> str:
    if explicit:
        return explicit
    resolved = shutil.which("sbx")
    if resolved:
        return resolved
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidate = Path(local_app_data) / "DockerSandboxes" / "bin" / "sbx.exe"
        if candidate.exists():
            return str(candidate)
    return "sbx"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--dockerfile", default=str(DEFAULT_DOCKERFILE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--sbx")
    args = parser.parse_args(argv)

    dockerfile = Path(args.dockerfile).resolve()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(["docker", "build", "-f", str(dockerfile), "-t", args.tag, str(dockerfile.parent)])
    _run(["docker", "save", args.tag, "-o", str(output)])
    _run([_sbx_path(args.sbx), "template", "load", str(output)])
    print(f"Loaded Docker Sandbox template {args.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
