"""Build the wheel-owned Rust executables; installed hosts need no Cargo."""

from __future__ import annotations

import json
import subprocess
import sysconfig
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        if self.target_name != "wheel" or version == "editable":
            return
        root = Path(self.root)
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
