from __future__ import annotations

import json
import sys
from pathlib import Path

import agentic_workspace as binding
from agentic_workspace.native_core import core_binary

request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
try:
    if request["action"] == "provenance":
        result = {"module": str(Path(binding.__file__).resolve()), "native": str(core_binary())}
    else:
        operation = {"start": binding.start, "invoke": binding.invoke}[request["action"]]
        result = operation(request["context"])
    payload = {"status": "ok", "result": result}
except binding.DecisionContractError as error:
    payload = {"status": "error", "message": str(error)}
print(json.dumps(payload))
