"""Derive shipped agent procedure bytes from the declared repository sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def synchronize(*, check: bool = False) -> list[str]:
    manifest = json.loads((ROOT / "src/agentic_workspace/contracts/workspace_surfaces.json").read_text())
    payload = ROOT / "src/agentic_workspace/_payload"
    from agentic_workspace.static_read_profile import LEDGER, PROFILE, render

    drift = []
    profile = ROOT / PROFILE
    expected_profile = render((ROOT / LEDGER).read_text(encoding="utf-8"))
    if not profile.is_file() or profile.read_text(encoding="utf-8") != expected_profile:
        drift.append(PROFILE)
        if not check:
            profile.write_text(expected_profile, encoding="utf-8", newline="\n")
    for reference in manifest["payload_files"]:
        # Only the declared source set participates; no workspace traversal.
        source, destination = ROOT / reference, payload / reference
        expected = source.read_text(encoding="utf-8").replace("\r\n", "\n")
        if not destination.is_file() or destination.read_text(encoding="utf-8") != expected:
            drift.append(reference)
            if not check:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(expected, encoding="utf-8", newline="\n")
    # Standalone first-party packages fall back to these shipped declarations.
    # Keep them derived from the same owner as the root payload.
    for module in ("memory", "planning"):
        destination = ROOT / f"packages/{module}/src/repo_{module}_bootstrap/_ownership.toml"
        expected = (ROOT / LEDGER).read_text(encoding="utf-8")
        if destination.read_text(encoding="utf-8") != expected:
            drift.append(destination.relative_to(ROOT).as_posix())
            if not check:
                destination.write_text(expected, encoding="utf-8", newline="\n")
    for retired in manifest.get("retired_surface_files", []):
        destination = payload / retired["path"]
        if destination.exists():
            drift.append(retired["path"])
            if not check:
                destination.unlink()
    return drift


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = synchronize(check=args.check)
    print(json.dumps({"drift" if args.check else "updated": changed}))
    raise SystemExit(1 if args.check and changed else 0)
