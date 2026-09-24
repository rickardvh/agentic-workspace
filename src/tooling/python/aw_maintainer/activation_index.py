"""Thin source-maintenance binding to native activation-index derivation."""

from __future__ import annotations

import argparse
from pathlib import Path

from aw_maintainer.native_conformance import _request


def derive(registry: Path, mode: str) -> dict:
    registry = registry.absolute()
    return _request({"activation-index": {"target": str(registry.parent), "request": {"registry": registry.name, "mode": mode}}})


def render(registry: Path) -> dict:
    return derive(registry, "render")["projection"]


def synchronize(registry: Path, *, check: bool = False) -> bool:
    result = derive(registry, "render" if check else "write")
    return result["drift"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    drift = synchronize(args.registry, check=args.check)
    raise SystemExit(1 if args.check and drift else 0)
