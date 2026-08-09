from __future__ import annotations

import json
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

import agentic_workspace
from agentic_workspace import (
    AWClientError,
    detect_workspace,
    external_operation_conformance_receipts,
    external_readiness_report,
    invoke_operation,
    negotiate_requirements,
)


def _execute(request: dict[str, Any]) -> Any:
    action = str(request["action"])
    target = Path(str(request.get("target") or ".")).resolve()
    if action == "provenance":
        return {
            "module": Path(agentic_workspace.__file__).resolve().as_posix(),
            "resources": Path(str(files("agentic_workspace._generated_cli_package_impl"))).resolve().as_posix(),
        }
    if action == "detect":
        return detect_workspace(target)
    if action == "readiness":
        return external_readiness_report(
            [str(item) for item in request.get("operations", [])],
            allow_runtime_backed=bool(request.get("allow_runtime_backed", False)),
        )
    if action == "receipts":
        return external_operation_conformance_receipts()
    if action == "negotiate":
        return negotiate_requirements(
            {str(key): value for key, value in request.get("requirements", {}).items()},
            allow_runtime_backed=bool(request.get("allow_runtime_backed", False)),
        )
    if action == "invoke":
        return invoke_operation(
            str(request["operation_id"]),
            dict(request.get("values", {})),
            target=target,
            invocation=[str(item) for item in request.get("invocation", [])] or None,
            allow_runtime_backed=bool(request.get("allow_runtime_backed", False)),
        )
    raise ValueError(f"unknown consumer action: {action}")


def main() -> int:
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    try:
        payload = {"status": "ok", "result": _execute(request)}
    except AWClientError as error:
        payload = {
            "status": "error",
            "kind": error.kind,
            "message": error.message,
            "details": dict(error.details),
        }
    print(json.dumps(payload, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
