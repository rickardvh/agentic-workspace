from __future__ import annotations

from pathlib import Path

from repo_planning_bootstrap._render import render_quickstart, render_routing

REPO_ROOT = Path(__file__).resolve().parents[3]
render_readme_entrypoints = render_quickstart


def main() -> int:
    for name, text in (("AGENT_QUICKSTART.md", render_quickstart()), ("AGENT_ROUTING.md", render_routing())):
        path = REPO_ROOT / "tools" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
