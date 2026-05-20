from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agentic_workspace.contract_tooling import (  # noqa: E402
    render_skillspec_plugin_target,
    render_skillspec_target_skill,
    skill_specs_manifest,
)

DEFAULT_OUTPUT_ROOT = Path("generated/workspace/skills")
DEFAULT_SKILL_IDS = ("startup-router",)
DEFAULT_PLUGIN_TARGET_IDS = ("codex-plugin",)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate compact target skills from SkillSpec contracts.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Repo-relative directory for generated skill targets.")
    parser.add_argument(
        "--skip-plugin-targets",
        action="store_true",
        help="Only render generated skill targets, not framework-native plugin targets.",
    )
    parser.add_argument("--check", action="store_true", help="Fail if checked-in generated targets are stale.")
    parser.add_argument("skill_ids", nargs="*", default=list(DEFAULT_SKILL_IDS), help="SkillSpec ids to render.")
    return parser.parse_args(argv)


def _target_path(output_root: Path, skill_id: str) -> Path:
    return output_root / skill_id / "SKILL.md"


def _plugin_target_paths(manifest: dict[str, object]) -> dict[str, Path]:
    targets = manifest.get("generated_plugin_targets", [])
    if not isinstance(targets, list):
        return {}
    paths: dict[str, Path] = {}
    for target in targets:
        if not isinstance(target, dict):
            continue
        target_id = target.get("id")
        output_path = target.get("output_path")
        if isinstance(target_id, str) and isinstance(output_path, str):
            paths[target_id] = Path(output_path)
    return paths


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
    if not args.skip_plugin_targets:
        plugin_paths = _plugin_target_paths(manifest)
        for target_id in DEFAULT_PLUGIN_TARGET_IDS:
            relative_path = plugin_paths[target_id]
            path = REPO_ROOT / relative_path
            rendered = render_skillspec_plugin_target(manifest, target_id)
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
