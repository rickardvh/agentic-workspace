"""Run the single pinned Rust advisory/license/source gate; no audit reimplementation."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = Path("src/agentic_workspace/contracts/security_supply_chain_policy.json")


def check(root: Path = ROOT, *, install: bool = False) -> None:
    policy = json.loads((root / POLICY).read_text(encoding="utf-8"))["rust_dependencies"]
    version = policy["version"]
    if install:
        subprocess.run(["cargo", "install", "cargo-deny", "--version", version, "--locked"], cwd=root, check=True)
    observed = subprocess.run(["cargo", "deny", "--version"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    if observed != f"cargo-deny {version}":
        raise ValueError(f"Expected cargo-deny {version}, observed {observed!r}; run with --install")
    # --locked protects Cargo.lock; do not use --frozen/--offline/--disable-fetch:
    # admission must fetch current RustSec data and fail on unavailable data.
    subprocess.run(
        ["cargo", "deny", "--locked", "--config", policy["config"], "check", "advisories", "licenses", "sources"],
        cwd=root,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="Install the exact policy-owned cargo-deny version using its lockfile")
    args = parser.parse_args()
    try:
        check(install=args.install)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Rust dependency policy failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
