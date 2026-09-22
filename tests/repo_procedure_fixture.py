"""Source-bound test consumer for a substituted repository method, never authority."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from agentic_workspace import start

ROOT = Path(__file__).resolve().parents[1]


def install_method(root: Path, name: str, route: str) -> list[str]:
    destination = root / "tools/skills/host-method"
    shutil.copytree(ROOT / "tools/skills" / name, destination)
    skill = destination / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8").replace(f"name: {name}", "name: host-method"), encoding="utf-8")
    (destination.parent / "REGISTRY.json").write_text(
        json.dumps(
            {
                "skills": [
                    {"id": "host-method", "path": "host-method/SKILL.md", "semantic_routes": [route], "procedure_resource": "procedure.md"}
                ]
            }
        ),
        encoding="utf-8",
    )
    return ["tools/skills/host-method/SKILL.md", "tools/skills/host-method/procedure.md"]


def question(context: dict, route: str) -> tuple[dict, dict]:
    full = {**context, "projection": "full"}
    initial = start(full)
    request = next(r for r in initial["semantic_routes"]["requests"] if r["request_kind"] == "semantic-routes/discover/v1")
    request["arguments"]["parent"] = route
    selected = start({**full, "request": request})
    choice = selected["procedure"]["requests"][0]
    answer = start({**full, "request": choice})["procedure"]["requests"][0]
    return selected, answer
