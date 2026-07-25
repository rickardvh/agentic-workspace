from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = REPO_ROOT / "scripts" / "generate"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from workspace_command_generation import (  # noqa: E402
    generate_workspace_command_packages,
    load_workspace_command_package_ir,
    render_workspace_command_package_outputs,
)


def _render_outputs(manifest: dict[str, object]) -> list[tuple[Path, str]]:
    return [(output.path, output.content) for output in render_workspace_command_package_outputs(manifest, repo_root=REPO_ROOT)]


def _is_line_ending_only_drift(path: Path, expected: str) -> bool:
    if not path.exists():
        return False
    with path.open("r", encoding="utf-8", newline="") as handle:
        current = handle.read()
    return current != expected and current.replace("\r\n", "\n") == expected


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate command package metadata from the command-package IR.")
    parser.add_argument("--check", action="store_true", help="Fail if generated command package files are stale.")
    return parser.parse_args(argv)


def _write_source_cli_fingerprint_manifest() -> None:
    """Publish the generator-owned cold-start freshness witness.

    The launcher accepts it when the manifest's exact Git-tracked inputs are
    unchanged; unrelated worktree edits do not force a full content scan.
    """

    launcher_path = REPO_ROOT / "scripts" / "run_agentic_workspace.py"
    spec = importlib.util.spec_from_file_location("run_agentic_workspace", launcher_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load launcher from {launcher_path}")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    manifest = launcher.source_cli_fingerprint_manifest(repo_root=REPO_ROOT)
    launcher.SOURCE_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _source_cli_fingerprint_manifest_is_current() -> bool:
    launcher_path = REPO_ROOT / "scripts" / "run_agentic_workspace.py"
    spec = importlib.util.spec_from_file_location("run_agentic_workspace", launcher_path)
    if spec is None or spec.loader is None:
        return False
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    try:
        actual = json.loads(launcher.SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return actual == launcher.source_cli_fingerprint_manifest(repo_root=REPO_ROOT)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    stale_outputs = generate_workspace_command_packages(repo_root=REPO_ROOT, check=bool(args.check))
    if args.check:
        if stale_outputs:
            rendered = dict(_render_outputs(load_workspace_command_package_ir(repo_root=REPO_ROOT)))
            for output in stale_outputs:
                path = REPO_ROOT / output
                expected = rendered.get(path)
                if expected is not None and _is_line_ending_only_drift(path, expected):
                    print(f"{output} has line-ending drift; regenerate command packages to normalize LF output.")
                else:
                    print(f"{output} is stale; regenerate command packages.")
            return 1
        if not _source_cli_fingerprint_manifest_is_current():
            print("generated/.agentic-workspace-cli-fingerprint.json is stale; regenerate command packages.")
            return 1
        print("[ok] generated command packages")
    else:
        _write_source_cli_fingerprint_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
