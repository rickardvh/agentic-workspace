"""Build the wheel-owned Rust executables; installed hosts need no Cargo."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sysconfig
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        if self.target_name == "sdist":
            root = Path(self.root).resolve()
            metadata = (root / "pyproject.toml").read_text(encoding="utf-8")
            for section in ("dependency-groups", "tool.uv.sources", "tool.uv.workspace"):
                metadata = re.sub(r"(?ms)^\[" + re.escape(section) + r"\]\n.*?(?=^\[|\Z)", "", metadata)
            projection = root / "target" / "sdist-native" / "pyproject.toml"
            projection.parent.mkdir(parents=True, exist_ok=True)
            projection.write_text(metadata, encoding="utf-8")
            build_data.setdefault("force_include", {})[str(projection)] = "pyproject.toml"
            # Preserve exact compile-time Rust inputs, not the former Python host.
            for source in (root / "crates").rglob("*.rs"):
                for reference in re.findall(r'include_(?:str|bytes)!\(\s*"([^"]+)"', source.read_text(encoding="utf-8")):
                    path = (source.parent / reference).resolve()
                    relative = path.relative_to(root)
                    if relative.as_posix() == "pyproject.toml":
                        continue
                    if not path.is_file():
                        raise RuntimeError(f"Missing native compile input: {relative}")
                    build_data.setdefault("force_include", {})[str(path)] = relative.as_posix()
            return
        if self.target_name != "wheel" or version == "editable":
            return
        root = Path(self.root)
        build_data.setdefault("force_include", {})[str(root / "bindings/python/__init__.py")] = "agentic_workspace/__init__.py"
        # An explicit host target prevents an ambient cross-compilation target
        # from being silently labelled as a locally executable wheel.
        rust = subprocess.run(["rustc", "-vV"], check=True, capture_output=True, text=True)
        host = next(line.removeprefix("host: ") for line in rust.stdout.splitlines() if line.startswith("host: "))
        platform_tag = sysconfig.get_platform().replace("-", "_").replace(".", "_")
        architectures = {"x86_64": ("x86_64", "amd64"), "aarch64": ("aarch64", "arm64"), "i686": ("i686", "i386", "win32")}
        architecture = host.split("-", 1)[0]
        if architecture not in architectures or not any(platform_tag.endswith(suffix) for suffix in architectures[architecture]):
            raise RuntimeError(f"Rust host {host} does not match Python wheel platform {platform_tag}; build on a matching host")
        # Linux stays linux_*: an ordinary local build establishes no manylinux
        # compatibility. No Python ABI is involved in this subprocess binary.
        built = subprocess.run(
            [
                "cargo",
                "build",
                "--locked",
                "--release",
                "--target",
                host,
                "--message-format=json",
                "-p",
                "agentic-workspace-core",
                "-p",
                "agentic-workspace-cli",
                "--bins",
            ],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        artifacts = [json.loads(line) for line in built.stdout.splitlines() if line.strip()]
        executables = {
            row["target"]["name"]: Path(row["executable"])
            for row in artifacts
            if row.get("reason") == "compiler-artifact"
            and row.get("target", {}).get("name") in {"agentic-workspace-core", "agentic-workspace"}
            and row.get("executable")
        }
        if set(executables) != {"agentic-workspace-core", "agentic-workspace"} or any(
            not executable.is_file() for executable in executables.values()
        ):
            raise RuntimeError("Cargo did not produce both current Rust executables")
        build_data["pure_python"] = False
        build_data["tag"] = f"py3-none-{platform_tag}"
        for executable in executables.values():
            build_data.setdefault("force_include", {})[str(executable)] = f"agentic_workspace/_native/{executable.name}"
        import tomllib

        manifest = root / "target" / "wheel-native" / host / "artifact.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            json.dumps(
                {
                    "kind": "agentic-workspace/native-python-artifact/v1",
                    "package_version": tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"],
                    "rust_host": host,
                    "sha256": hashlib.sha256(executables["agentic-workspace-core"].read_bytes()).hexdigest(),
                    "cli_sha256": hashlib.sha256(executables["agentic-workspace"].read_bytes()).hexdigest(),
                }
            ),
            encoding="utf-8",
        )
        build_data.setdefault("force_include", {})[str(manifest)] = "agentic_workspace/_native/artifact.json"
