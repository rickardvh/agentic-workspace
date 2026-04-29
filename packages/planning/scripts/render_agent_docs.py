from __future__ import annotations

import json
from pathlib import Path

from repo_planning_bootstrap._render import load_manifest as _load_manifest
from repo_planning_bootstrap._render import render_quickstart, render_routing

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / ".agentic-workspace" / "planning" / "agent-manifest.json"


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    return _load_manifest(path)


render_readme_entrypoints = render_quickstart


def main() -> int:
    manifest = load_manifest()
    outputs = {
        REPO_ROOT / "tools" / "agent-manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        REPO_ROOT / "tools" / "AGENT_QUICKSTART.md": render_quickstart(manifest),
        REPO_ROOT / "tools" / "AGENT_ROUTING.md": render_routing(manifest),
    }
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
