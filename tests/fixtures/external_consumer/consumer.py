from __future__ import annotations

import json
import sys
from pathlib import Path

from agentic_workspace import decision
from agentic_workspace.native_core import core_binary

request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
try:
    if request["action"] == "provenance":
        result = {"module": str(Path(decision.__file__).resolve()), "native": str(core_binary())}
    else:
        operation = {"start": decision.start, "invoke": decision.invoke}[request["action"]]
        result = operation(request["context"])
    payload = {"status": "ok", "result": result}
except decision.DecisionContractError as error:
    payload = {"status": "error", "message": str(error)}
print(json.dumps(payload))
