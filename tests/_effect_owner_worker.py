from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from agentic_workspace.modules import Module
from agentic_workspace.operations import Operation
from agentic_workspace.workspace import Workspace


def main() -> int:
    target = Path(sys.argv[1])
    owner = sys.argv[2]
    operation_id = f"{owner}.mutate"
    shared = target / "shared-effect.json"

    def apply(_: dict[str, Any]) -> dict[str, Any]:
        values = json.loads(shared.read_text(encoding="utf-8")) if shared.exists() else []
        time.sleep(0.1)
        shared.write_text(json.dumps([*values, owner]), encoding="utf-8")
        return {"status": "applied", "effects": ["shared-effect"], "value": owner}

    operation = Operation(operation_id, {"type": "object"}, ("shared-effect",), apply)
    module = Module(
        owner,
        lambda _: {
            "revision": "stable",
            "actions": [{"operation_id": operation_id, "arguments": {}, "effects": ["shared-effect"]}],
        },
        operations=(operation,),
    )
    workspace = Workspace(target, modules=[module])
    result = workspace.invoke(workspace.start(task=owner)["primary_action"])
    return 0 if result["status"] == "applied" else 1


if __name__ == "__main__":
    raise SystemExit(main())
