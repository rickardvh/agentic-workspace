from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agentic_workspace.contract_tooling import (  # noqa: E402
    render_skillspec_target_skill,
    skill_specs_manifest,
)

DEFAULT_OUTPUT_ROOT = Path("generated/workspace/skills")
DEFAULT_SKILL_IDS = ("startup-router",)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate compact target skills from SkillSpec contracts.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Repo-relative directory for generated skill targets.")
    parser.add_argument("--check", action="store_true", help="Fail if checked-in generated targets are stale.")
    parser.add_argument("skill_ids", nargs="*", default=list(DEFAULT_SKILL_IDS), help="SkillSpec ids to render.")
    return parser.parse_args(argv)


def _target_path(output_root: Path, skill_id: str) -> Path:
    return output_root / skill_id / "SKILL.md"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest = skill_specs_manifest()
    output_root = Path(args.output_root)
    stale: list[str] = []
    for skill_id in args.skill_ids:
        relative_path = _target_path(output_root, skill_id)
        path = REPO_ROOT / relative_path
        rendered = render_skillspec_target_skill(manifest, skill_id)
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != rendered:
                stale.append(relative_path.as_posix())
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    if stale:
        print("Stale generated SkillSpec targets: " + ", ".join(stale), file=sys.stderr)
        return 1
    if args.check:
        print("[ok] generated SkillSpec targets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
