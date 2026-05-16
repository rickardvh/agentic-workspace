from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMAND_GENERATION_SRC = REPO_ROOT / "packages" / "command-generation" / "src"
if str(COMMAND_GENERATION_SRC) not in sys.path:
    sys.path.insert(0, str(COMMAND_GENERATION_SRC))

from command_generation import (  # noqa: E402
    GeneratedOutput,
    generate_command_packages,
    load_command_package_ir,
    render_outputs,
)

SOURCE_PATH = "src/agentic_workspace/contracts/command_package_ir.json"
SCHEMA_PATH = "packages/command-generation/schemas/command_package_ir.schema.json"
REGENERATE_COMMAND = "uv run python scripts/generate/generate_command_packages.py"


def load_workspace_command_package_ir(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    return load_command_package_ir(repo_root / SOURCE_PATH, repo_root / SCHEMA_PATH)


def render_workspace_command_package_outputs(
    manifest: dict[str, object] | None = None,
    *,
    repo_root: Path = REPO_ROOT,
) -> list[GeneratedOutput]:
    effective_manifest = manifest if manifest is not None else load_workspace_command_package_ir(repo_root=repo_root)
    return render_outputs(
        effective_manifest,
        repo_root=repo_root,
        source_path=SOURCE_PATH,
        regenerate_command=REGENERATE_COMMAND,
    )


def generate_workspace_command_packages(*, repo_root: Path = REPO_ROOT, check: bool) -> list[str]:
    return generate_command_packages(
        load_workspace_command_package_ir(repo_root=repo_root),
        repo_root=repo_root,
        source_path=SOURCE_PATH,
        regenerate_command=REGENERATE_COMMAND,
        check=check,
    )
