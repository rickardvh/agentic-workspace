"""Build-time compiler observation shared by native artifact producers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path


def observe(root: Path) -> dict[str, str]:
    declaration = (root / "rust-toolchain.toml").read_bytes()
    channel = tomllib.loads(declaration.decode())["toolchain"]["channel"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", channel):
        raise ValueError("Native packaging requires an exact rust-toolchain.toml release")
    if any(os.environ.get(key) for key in ("RUSTC", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER")):
        raise ValueError("Native packaging requires the declared Rust compiler without compiler overrides/wrappers")
    output = subprocess.check_output(["rustc", "-vV"], cwd=root, text=True)
    fields = dict(line.split(": ", 1) for line in output.splitlines() if ": " in line)
    if fields.get("release") != channel or not fields.get("commit-hash") or not fields.get("host"):
        raise ValueError(f"Native packaging requires Rust {channel} from rust-toolchain.toml; observed {fields.get('release')}")
    deployment = {}
    if fields["host"].endswith("-apple-darwin"):
        rows = json.loads((root / ".github/release-platforms.json").read_text())["platforms"]
        deployment["macos_deployment_target"] = next(row["macos_deployment_target"] for row in rows if row["target"] == fields["host"])
    return {
        **deployment,
        "channel": channel,
        "declaration_sha256": hashlib.sha256(declaration).hexdigest(),
        "release": fields["release"],
        "commit_hash": fields["commit-hash"],
        "commit_date": fields["commit-date"],
        "host": fields["host"],
        "llvm_version": fields["LLVM version"],
    }


def source_identity(root: Path) -> dict[str, object]:
    checkout = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root, capture_output=True, text=True, check=False)
    if checkout.returncode or Path(checkout.stdout.strip()).resolve() != root.resolve():
        return {"source_head": None, "source_dirty": None}
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    if result.returncode:
        return {"source_head": None, "source_dirty": None}
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, text=True)
    return {"source_head": result.stdout.strip(), "source_dirty": bool(dirty.strip())}


def build_environment(toolchain: dict[str, str] | None = None) -> dict[str, str]:
    # Bind Cargo to the same compiler observed above, including when a local
    # Cargo config names a different compiler or wrapper.
    deployment = (
        {"MACOSX_DEPLOYMENT_TARGET": toolchain["macos_deployment_target"]} if toolchain and "macos_deployment_target" in toolchain else {}
    )
    return {**os.environ, **deployment, "RUSTC": shutil.which("rustc") or "rustc", "RUSTC_WRAPPER": "", "RUSTC_WORKSPACE_WRAPPER": ""}
