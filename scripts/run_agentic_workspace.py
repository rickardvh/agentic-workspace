"""Source-checkout launcher for the paired native product binaries."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CODEX_SESSION_IDENTITY_ENV = "CODEX_THREAD_ID"
AW_SESSION_IDENTITY_ENV = "AW_SESSION_LOGICAL_IDENTITY"

def _dispatch_to_source_cli(argv: Sequence[str]) -> int:
    # Load only this checkout's artifact resolver. Installed/editable Python
    # package identity cannot choose the product implementation for this source.
    path = REPO_ROOT / "src/cli/python/agentic_workspace/native_core.py"
    spec = importlib.util.spec_from_file_location("aw_source_native_artifacts", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("source native artifact resolver unavailable")
    resolver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resolver)
    try:
        return subprocess.call([str(resolver.cli_binary()), *argv])
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

def _bridge_codex_session_identity() -> bool:
    """Map Codex's opaque thread identity into AW's portable session contract."""

    if os.environ.get(AW_SESSION_IDENTITY_ENV, "").strip():
        return False
    codex_identity = os.environ.get(CODEX_SESSION_IDENTITY_ENV, "").strip()
    if not codex_identity:
        return False
    os.environ[AW_SESSION_IDENTITY_ENV] = codex_identity
    return True

def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    _bridge_codex_session_identity()
    return _dispatch_to_source_cli(args)

if __name__ == "__main__":
    raise SystemExit(main())
