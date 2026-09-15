"""Project current authoring from single-owned, versioned source definitions.

Former recognition is intentionally broader. This build-time projection is not
a runtime policy registry or a fallback for invalid current documents.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "src/agentic_workspace/contracts/schemas"


def current(node: object) -> object:
    if isinstance(node, list):
        return [current(item) for item in node]
    if not isinstance(node, dict):
        return node
    result = {
        key: current(value) for key, value in node.items() if key not in {"x-current-authoring", "x-delegation-compatibility-lifecycle"}
    }
    if "properties" in node:
        result["properties"] = {
            key: current(value)
            for key, value in node["properties"].items()
            if not value.get("deprecated") and not value.get("readOnly") and value.get("x-current-authoring", True)
        }
        # Fixed objects are closed; explicit owner schema/pattern slots survive.
        if node.get("type") == "object" and (node.get("additionalProperties") is True or "additionalProperties" not in node):
            result["additionalProperties"] = False
        if "required" in result:
            result["required"] = [key for key in result["required"] if key in result["properties"]]
    return result


def render(name: str) -> str:
    former = json.loads((SCHEMAS / f"{name}_former.schema.json").read_text(encoding="utf-8"))
    schema = current(copy.deepcopy(former))
    assert isinstance(schema, dict)
    schema["$id"] = former["$id"].replace("_former", "")
    schema["title"] = former["title"].removeprefix("Former source recognition: ")
    schema["x-agentic-workspace-doc-role"] = "public-reference"
    schema["x-agentic-workspace-unknown-properties"] = "reject"
    schema["description"] = (
        "Current human configuration authoring, version 2. Version 1 sources are read separately; never use former syntax for new settings."
    )
    schema["properties"]["schema_version"] = {"const": 2, "default": 2, "description": "Current authoring contract version."}
    # Retain only reachable local definitions, including transitive references.
    definitions = schema.pop("$defs", {})
    retained: dict = {}
    pending = json.dumps(schema)
    while True:
        found = [key for key in definitions if key not in retained and f"#/$defs/{key}" in pending]
        if not found:
            break
        for key in found:
            retained[key] = definitions[key]
        pending = json.dumps(retained)
    if retained:
        schema["$defs"] = retained
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    for name in ("workspace_config", "workspace_local_override"):
        path = SCHEMAS / f"{name}.schema.json"
        expected = render(name)
        if args.check:
            if path.read_text(encoding="utf-8") != expected:
                print(f"[error] stale current authoring schema: {path.relative_to(ROOT)}")
                return 1
        else:
            path.write_text(expected, encoding="utf-8")
    print("[ok] current configuration authoring schemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
