"""Independent provider-neutral consumer of the released AW operation client."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentic_workspace.client import invoke_operation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--host-result-ref", required=True)
    args = parser.parse_args()
    target = Path(args.target).resolve()
    candidate_json = Path(args.candidate).read_text(encoding="utf-8")
    submitted = invoke_operation(
        "external-evidence.submit",
        {"candidate_json": candidate_json, "host_result_ref": args.host_result_ref},
        target=target,
        invocation=["uv", "run", "agentic-workspace"],
        allow_runtime_backed=True,
    )
    queried = invoke_operation(
        "external-evidence.query",
        {"candidate_json": candidate_json, "host_result_ref": args.host_result_ref},
        target=target,
        invocation=["uv", "run", "agentic-workspace"],
        allow_runtime_backed=True,
    )
    print(json.dumps({"submitted": submitted, "queried": queried}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
