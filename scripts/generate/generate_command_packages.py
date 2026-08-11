from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

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

    The launcher uses the Git witness only as an acceleration hint and falls
    back to the canonical semantic identity when checkout state changes.
    """

    launcher = _load_launcher(repo_root=REPO_ROOT)
    manifest = launcher.source_cli_fingerprint_manifest(repo_root=REPO_ROOT)
    launcher.SOURCE_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_launcher(*, repo_root: Path) -> ModuleType:
    launcher_path = repo_root / "scripts" / "run_agentic_workspace.py"
    spec = importlib.util.spec_from_file_location("run_agentic_workspace", launcher_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load launcher from {launcher_path}")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    return launcher


def _source_cli_fingerprint_manifest_status(
    *,
    repo_root: Path = REPO_ROOT,
    launcher: ModuleType | None = None,
) -> dict[str, str]:
    try:
        effective_launcher = launcher or _load_launcher(repo_root=repo_root)
    except (OSError, RuntimeError):
        return {"status": "invalid", "reason": "launcher-unavailable", "auxiliary_witness": "not-evaluated"}
    return effective_launcher.source_cli_fingerprint_manifest_status(repo_root=repo_root)


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
        manifest_status = _source_cli_fingerprint_manifest_status()
        if manifest_status["status"] != "current":
            print(
                "generated/.agentic-workspace-cli-fingerprint.json "
                f"failed freshness validation ({manifest_status['reason']}); regenerate command packages."
            )
            return 1
        witness = manifest_status["auxiliary_witness"]
        detail = "" if manifest_status["reason"] == "git-index-fast-path" else f" (semantic fallback; Git witness: {witness})"
        print(f"[ok] generated command packages{detail}")
    else:
        _write_source_cli_fingerprint_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
