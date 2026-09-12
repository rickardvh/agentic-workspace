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
import zipfile
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
        ["cargo", "build", "--locked", "--profile", profile, "--target", host, "--workspace", "--bins", "--message-format=json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    artifacts = [json.loads(line) for line in built.stdout.splitlines() if line.strip()]
    binaries = {
        row["target"]["name"]: Path(row["executable"])
        for row in artifacts
        if row.get("reason") == "compiler-artifact"
        and row.get("target", {}).get("name") in {"agentic-workspace-core", "agentic-workspace"}
        and row.get("executable")
    }
    if len(binaries) != 2:
        raise ValueError("Cargo did not identify both paired native executables")
    node_platform = {"win32": "win32", "linux": "linux", "darwin": "darwin"}[sys.platform]
    node_arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}[platform.machine().lower()]
    native = output / "src/native/bin"
    native.mkdir(parents=True)
    for name in ("semantic-decision.mjs", "operating.mjs", "operating.d.mts"):
        shutil.copy2(ROOT / "bindings/node" / name, native.parent / name)
    shutil.copy2(ROOT / "bindings/node/cli.mjs", output / "src/cli.mjs")
    shutil.copy2(ROOT / "LICENSE", output / "LICENSE")
    binary = binaries["agentic-workspace-core"]
    for executable in binaries.values():
        shutil.copy2(executable, native / executable.name)
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
                "cli_sha256": hashlib.sha256(binaries["agentic-workspace"].read_bytes()).hexdigest(),
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
    package = {
        key: package[key] for key in ("name", "version", "author", "license", "repository", "homepage", "bugs", "engines", "private")
    }
    package.update(
        {
            "type": "module",
            "description": "Thin Node/TypeScript projection of the shared Rust authority",
            "bin": {"agentic-workspace": "./src/cli.mjs"},
            "exports": {
                ".": "./src/native/operating.mjs",
                "./operating": "./src/native/operating.mjs",
                "./native": "./src/native/semantic-decision.mjs",
            },
            "files": ["src", "LICENSE"],
            "scripts": {"test": "node src/cli.mjs --help"},
            "agenticWorkspace": {"runtimeBinding": {}},
        }
    )
    package["os"] = [node_platform]
    package["cpu"] = [node_arch]
    package["agenticWorkspace"]["runtimeBinding"]["runtime_dependency"] = "node-and-packaged-rust-core"
    package["agenticWorkspace"]["nativeRuntime"] = {
        "operations": ["start", "invoke", "instructions.routes"],
        "manifest": "src/native/bin/artifact.json",
        "support": "current build host only",
    }
    (output / "package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=["dev", "release"], default="release")
    parser.add_argument("--native-archive-dir", type=Path)
    args = parser.parse_args()
    output = stage(args.output.resolve(), profile=args.profile)
    if args.native_archive_dir:
        native = output / "src/native/bin"
        manifest = json.loads((native / "artifact.json").read_text())
        args.native_archive_dir.mkdir(parents=True, exist_ok=True)
        archive = args.native_archive_dir / f"agentic-workspace-native-{manifest['package_version']}-{manifest['rust_host']}.zip"
        if archive.exists():
            raise ValueError("native archive destination must be absent")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(native.iterdir()):
                bundle.write(path, path.name)
            bundle.write(ROOT / "LICENSE", "LICENSE")
    print(output)


if __name__ == "__main__":
    main()
