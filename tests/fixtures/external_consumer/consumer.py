from __future__ import annotations

import json
import sys

from agentic_workspace import invoke_operation


def main() -> int:
    target = sys.argv[1]
    payload = invoke_operation(
        "config.report",
        {},
        target=target,
        invocation=[sys.executable, "-c", "from agentic_workspace import cli; import sys; raise SystemExit(cli.main(sys.argv[1:]))"],
        allow_runtime_backed=True,
    )
    print(json.dumps({"operation": "config.report", "result": payload}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
