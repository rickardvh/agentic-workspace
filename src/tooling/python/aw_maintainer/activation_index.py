"""Derive compact activation discovery from existing procedure sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def render(registry: Path) -> dict:
    body = json.loads(registry.read_text(encoding="utf-8"))
    rows = []
    for skill in body.get("skills", []):
        if not skill.get("procedure_resource"):
            continue
        for value in (skill["path"], skill["procedure_resource"]):
            if "\\" in value or ":" in value or any(part in {"", ".", ".."} for part in value.split("/")):
                raise ValueError("Activation sources require confined relative paths")
        resource = registry.parent / Path(skill["path"]).parent / skill["procedure_resource"]
        if not resource.is_file():
            continue
        text = resource.read_text(encoding="utf-8")
        marker = "```agentic-procedure\n"
        if text.count(marker) != 1:
            continue
        question = json.loads(text.split(marker)[1].split("\n```", 1)[0])
        if "activation" in question:
            rows.append({key: skill[key] for key in ("id", "path", "procedure_resource")})
            route = skill.get("semantic_routes", [None])[0]
            rows[-1]["semantic_routes"] = [route.get("id") if isinstance(route, dict) else route]
            rows[-1]["activation"] = question["activation"]
    if len(rows) > 128:
        raise ValueError("Activation index exceeds 128 entries")
    if rows:
        body["activation_index"] = rows
    else:
        body.pop("activation_index", None)
    return body


def synchronize(registry: Path, *, check: bool = False) -> bool:
    expected = render(registry)
    if json.loads(registry.read_text(encoding="utf-8")) == expected:
        return False
    if not check:
        registry.write_text(json.dumps(expected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    drift = synchronize(args.registry, check=args.check)
    raise SystemExit(1 if args.check and drift else 0)
