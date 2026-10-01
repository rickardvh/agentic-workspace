"""Stage the passive plugin marketplace with the coordinated release identity."""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def outputs(root: Path = ROOT, *, version: str | None = None) -> dict[str, str]:
    spec = importlib.util.spec_from_file_location("entry_generator", root / "src/tooling/generate/generate_skill_entry.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render(root, version=version)


def stage(directory: Path, version: str) -> Path:
    archive = directory / f"agentic-workspace-entry-{version}.zip"
    directory.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as bundle:
        for reference, body in outputs(version=version).items():
            if not reference.startswith(("src/", ".agentic-workspace/")):
                bundle.writestr(reference, body)
        bundle.write(ROOT / "LICENSE", "LICENSE")
    return archive
