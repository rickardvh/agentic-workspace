from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(command: list[str]) -> int:
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return int(completed.returncode)


def _python_executable() -> str:
    return sys.executable or "python"


def _validate_static_surfaces() -> list[str]:
    errors: list[str] = []
    dockerfile = REPO_ROOT / "generated" / "typescript" / "Dockerfile"
    if not dockerfile.is_file():
        errors.append("generated/typescript/Dockerfile is missing")
    for package in ("workspace-cli", "planning-cli", "memory-cli"):
        package_root = REPO_ROOT / "generated" / "typescript" / package
        for relative in ("package.json", "src/commandPackage.ts", "test/command-package.test.mjs"):
            if not (package_root / relative).is_file():
                errors.append(f"generated/typescript/{package}/{relative} is missing")
        package_json_path = package_root / "package.json"
        if package_json_path.is_file():
            payload = json.loads(package_json_path.read_text(encoding="utf-8"))
            maturity = payload.get("agenticWorkspace", {}).get("maturity", {})
            if maturity.get("weak_agent_routing") != "forbidden" or maturity.get("runnable") is not False:
                errors.append(f"generated/typescript/{package}/package.json maturity does not mark proof fixture as non-runnable")
    return errors


def _run_docker(tag: str, *, require_docker: bool) -> int:
    if shutil.which("docker") is None:
        print("docker is not available; cannot run generated TypeScript package container proof")
        return 1 if require_docker else 0
    info = subprocess.run(["docker", "info"], cwd=REPO_ROOT, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if info.returncode:
        detail = info.stderr.strip().splitlines()
        suffix = f": {detail[0]}" if detail else ""
        print(f"docker daemon is not available; skipped generated TypeScript package container proof{suffix}")
        return 1 if require_docker else 0
    dockerfile = "generated/typescript/Dockerfile"
    build = _run(["docker", "build", "-f", dockerfile, "-t", tag, "."])
    if build:
        return build
    return _run(["docker", "run", "--rm", tag])


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check generated command package outputs.")
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Run generated TypeScript package tests inside Docker.",
    )
    parser.add_argument(
        "--tag",
        default="agentic-workspace-generated-typescript-cli-test",
        help="Docker image tag used for generated TypeScript package tests.",
    )
    parser.add_argument(
        "--require-docker",
        action="store_true",
        help="Fail instead of skipping when Docker is unavailable.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    generator = REPO_ROOT / "scripts" / "generate" / "generate_command_packages.py"
    freshness = _run([_python_executable(), str(generator), "--check"])
    if freshness:
        return freshness
    errors = _validate_static_surfaces()
    if errors:
        for error in errors:
            print(error)
        return 1
    if args.docker:
        return _run_docker(str(args.tag), require_docker=bool(args.require_docker))
    print("[ok] generated command package static proof")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
