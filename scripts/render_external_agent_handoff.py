from __future__ import annotations

import argparse
from pathlib import Path

from agentic_workspace import cli

REPO_ROOT = Path(__file__).resolve().parents[1]


def render_external_agent_handoff(*, target_root: Path = REPO_ROOT) -> dict[str, str]:
    expected = cli._external_agent_handoff_text_for_target(target_root=target_root)  # type: ignore[attr-defined]
    path = target_root / cli.WORKSPACE_EXTERNAL_AGENT_PATH
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing != expected:
        path.write_text(expected, encoding="utf-8")
        return {"status": "updated" if existing is not None else "created", "path": path.relative_to(target_root).as_posix()}
    return {"status": "current", "path": path.relative_to(target_root).as_posix()}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the root llms.txt external-agent handoff adapter.")
    parser.add_argument("--target", default=str(REPO_ROOT), help="Repository root to update.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = render_external_agent_handoff(target_root=Path(args.target).resolve())
    print(f"{result['status']}: {result['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
