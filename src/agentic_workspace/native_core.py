"""Native artifact resolution for installed packages and editable source hosts."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def core_binary() -> Path:
    configured = os.environ.get("AGENTIC_WORKSPACE_CORE_BINARY")
    if configured:
        path = Path(configured)
    else:
        name = "agentic-workspace-core.exe" if os.name == "nt" else "agentic-workspace-core"
        path = Path(__file__).with_name("_native") / name
        source_root = Path(__file__).resolve().parents[2]
        if not path.is_file() and (source_root / "crates/agentic-workspace-core/Cargo.toml").is_file():
            # Editable source checkouts have no wheel-owned binary. Let Cargo
            # validate/rebuild the active source instead of using a stale cache
            # or requiring an ordinary client to choose an executable path.
            try:
                built = subprocess.run(
                    [
                        "cargo",
                        "build",
                        "--quiet",
                        "--locked",
                        "--manifest-path",
                        str(source_root / "Cargo.toml"),
                        "--message-format=json",
                        "-p",
                        "agentic-workspace-core",
                    ],
                    cwd=source_root,
                    text=True,
                    capture_output=True,
                    check=False,
                )
            except OSError as error:
                raise RuntimeError("source checkout requires the Rust toolchain to build its shared core") from error
            if built.returncode != 0:
                raise RuntimeError(f"source checkout core build failed: {built.stderr.strip()}")
            artifacts = [json.loads(line) for line in built.stdout.splitlines() if line.strip()]
            executable = next(
                (
                    row.get("executable")
                    for row in artifacts
                    if row.get("reason") == "compiler-artifact"
                    and row.get("target", {}).get("name") == "agentic-workspace-core"
                    and row.get("executable")
                ),
                None,
            )
            if not executable:
                raise RuntimeError("Cargo did not return a current shared-core executable")
            path = Path(executable)
    if not path.is_file():
        raise RuntimeError(
            "shared Agentic Workspace core is unavailable; install a supported native package "
            "or set AGENTIC_WORKSPACE_CORE_BINARY to the admitted core binary"
        )
    return path
