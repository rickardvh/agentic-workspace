"""Stage the existing workspace npm artifact with this host's current Rust core."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def stage(output: Path, *, profile: str = "release") -> Path:
    source = ROOT / "generated/workspace/typescript"
    package = json.loads((source / "package.json").read_text(encoding="utf-8"))
    product = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if package["version"] != product["project"]["version"]:
        raise ValueError("npm and compiled product versions differ")
    if (source / "src/native/semantic-decision.mjs").read_text(encoding="utf-8") != (
        ROOT / "bindings/node/semantic-decision.mjs"
    ).read_text(encoding="utf-8"):
        raise ValueError("generated native binding is stale")
    if output.exists():
        raise ValueError("staging destination must be absent")
    rust = subprocess.run(["rustc", "-vV"], check=True, capture_output=True, text=True)
    host = next(line.removeprefix("host: ") for line in rust.stdout.splitlines() if line.startswith("host: "))
    machine = platform.machine().lower()
    architecture = host.split("-", 1)[0]
    compatible_arch = {"x86_64": {"amd64", "x86_64"}, "aarch64": {"arm64", "aarch64"}}
    compatible_os = {"win32": "windows", "linux": "linux", "darwin": "darwin"}
    if machine not in compatible_arch.get(architecture, set()) or compatible_os.get(sys.platform, "unsupported") not in host:
        raise ValueError(f"Rust host {host} does not match Node artifact host {sys.platform}/{machine}")
    built = subprocess.run(
        ["cargo", "build", "--locked", "--profile", profile, "--target", host, "-p", "agentic-workspace-core", "--message-format=json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    artifacts = [json.loads(line) for line in built.stdout.splitlines() if line.strip()]
    binaries = [
        Path(row["executable"])
        for row in artifacts
        if row.get("reason") == "compiler-artifact"
        and row.get("target", {}).get("name") == "agentic-workspace-core"
        and row.get("executable")
    ]
    if len(binaries) != 1:
        raise ValueError("Cargo did not identify exactly one current core executable")
    node_platform = {"win32": "win32", "linux": "linux", "darwin": "darwin"}[sys.platform]
    node_arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}[platform.machine().lower()]
    shutil.copytree(source, output, ignore=shutil.ignore_patterns("node_modules", "bin"))
    native = output / "src/native/bin"
    native.mkdir(parents=True)
    binary = binaries[0]
    shutil.copy2(binary, native / binary.name)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    head = revision.stdout.strip() if revision.returncode == 0 else None
    dirty = (
        bool(
            subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, capture_output=True, text=True, check=True
            ).stdout.strip()
        )
        if head
        else None
    )
    (native / "artifact.json").write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/native-npm-artifact/v1",
                "package_version": package["version"],
                "platform": node_platform,
                "arch": node_arch,
                "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                "source_head": head,
                "source_dirty": dirty,
                "profile": profile,
                "rust_host": host,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    package["os"] = [node_platform]
    package["cpu"] = [node_arch]
    package["agenticWorkspace"]["runtimeBinding"]["runtime_dependency"] = "node-and-packaged-rust-core"
    package["agenticWorkspace"]["nativeRuntime"] = {
        "operations": ["instructions.routes"],
        "manifest": "src/native/bin/artifact.json",
        "support": "current build host only",
    }
    (output / "package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=["dev", "release"], default="release")
    args = parser.parse_args()
    print(stage(args.output.resolve(), profile=args.profile))


if __name__ == "__main__":
    main()
