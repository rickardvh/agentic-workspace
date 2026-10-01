"""Derive passive skill-entry distribution from one maintained bridge."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NAME = "agentic-workspace-entry"
BUNDLE = f"plugins/{NAME}"
SOURCE = "src/adapters/skill-entry/SKILL.md"
NPM_SKILL = f"src/cli/typescript/skills/{NAME}/SKILL.md"


def release_version(root: Path) -> str:
    spec = importlib.util.spec_from_file_location("entry_release", root / "src/tooling/release/coordinated_release.py")
    module = importlib.util.module_from_spec(spec)
    # The release module's dataclasses require their module during evaluation.
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.npm_version(tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"])


def render(root: Path = ROOT, *, version: str | None = None) -> dict[str, str]:
    body = (root / SOURCE).read_text(encoding="utf-8").replace("\r\n", "\n")
    # Source Git installations use Claude's native commit identity. Only staged
    # coordinated artifacts supply an explicit release version.
    portable_version = version or release_version(root)
    # Codex reuses local caches by manifest version. Development bundles need a
    # distinct identity when their passive bridge changes, even between releases.
    if version is None and portable_version == "0.0.0-dev.0":
        portable_version += "+" + hashlib.sha256(body.encode()).hexdigest()[:16]
    metadata = {
        "name": NAME,
        "description": "A passive entry to the current target repository's agentic-workspace procedure.",
        "author": {"name": "Rickard von Haugwitz"},
        "repository": "https://github.com/rickardvh/agentic-workspace",
        "license": "MIT",
    }

    def encoded(value):
        return json.dumps(value, indent=2) + "\n"

    outputs = {
        NPM_SKILL: body,
        f"{BUNDLE}/skills/{NAME}/SKILL.md": body,
        f"{BUNDLE}/plugin.json": encoded(
            {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json", **metadata, "version": portable_version}
        ),
        f"{BUNDLE}/.claude-plugin/plugin.json": encoded({**metadata, **({"version": version} if version else {})}),
        ".agents/plugins/marketplace.json": encoded(
            {
                "name": "agentic-workspace",
                "plugins": [
                    {
                        "name": NAME,
                        "source": {"source": "local", "path": f"./{BUNDLE}"},
                        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                        "category": "Productivity",
                    }
                ],
            }
        ),
        ".claude-plugin/marketplace.json": encoded(
            {
                "name": "agentic-workspace",
                "description": metadata["description"],
                "owner": metadata["author"],
                "plugins": [{"name": NAME, "source": f"./{BUNDLE}", **({"version": version} if version else {})}],
            }
        ),
    }
    # Repository adoption consumes the same maintained passive bundle. Host
    # catalogues and enablement are optional Configuration-owned projections.
    for suffix in (f"skills/{NAME}/SKILL.md", "plugin.json", ".claude-plugin/plugin.json"):
        outputs[f".agentic-workspace/plugins/{NAME}/{suffix}"] = outputs[f"{BUNDLE}/{suffix}"]
    return outputs


def synchronize(*, root: Path = ROOT, check: bool = False) -> list[str]:
    changed = []
    for reference, body in render(root).items():
        path = root / reference
        if not path.is_file() or path.read_text(encoding="utf-8") != body:
            changed.append(reference)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8", newline="\n")
    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = synchronize(check=args.check)
    print(json.dumps({"drift" if args.check else "updated": changed}))
    raise SystemExit(bool(args.check and changed))
