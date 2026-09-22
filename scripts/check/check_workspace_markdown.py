"""Lint declared shipped Workspace Markdown and its canonical sources."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(root: Path = ROOT) -> int:
    host = json.loads((root / "src/core/contracts/workspace_surfaces.json").read_text(encoding="utf-8"))
    paths: set[str] = set()
    for surface in host["surfaces"]:
        if not surface["path"].endswith(".md"):
            continue
        paths.add("src/core/payload/" + surface["path"])
        paths.add(surface["materialization"]["source"])
    if not paths:
        raise ValueError("Workspace declaration contains no Markdown surfaces")
    return subprocess.run(
        [sys.executable, "-m", "pymarkdown", "--enable-extensions", "front-matter", "-d", "MD013,MD024,MD041", "scan", *sorted(paths)],
        cwd=root,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
