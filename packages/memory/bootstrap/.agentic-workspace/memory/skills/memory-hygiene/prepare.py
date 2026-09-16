"""Run explicitly selected native Memory hygiene; no semantic fallback or writes."""

from __future__ import annotations

import argparse
import json
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-cli", default="agentic-workspace")
    parser.add_argument("--target", default=".")
    parser.add_argument("--task", required=True)
    args = parser.parse_args()
    command = [args.native_cli, "start", "--target", args.target, "--task", args.task, "--projection", "full", "--format", "json"]
    try:
        initial = json.loads(subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", timeout=60).stdout)
        request = next(row for row in initial["semantic_routes"]["requests"] if row["request_kind"] == "semantic-routes/select/v1")
        request["arguments"] = {"posture": "selected", "routes": ["memory/hygiene"]}
        current = json.loads(
            subprocess.run(
                command + ["--input", "-"],
                input=json.dumps(request),
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=60,
            ).stdout
        )
        result = current.get("memory", {}).get("hygiene")
        if not result or result.get("status") != "checked":
            result = {
                "status": "unexecuted",
                "reason": "Current native Memory hygiene unavailable",
                "diagnostics": current.get("memory", {}).get("diagnostics", []),
            }
        print(json.dumps({"hygiene": result, "owner_blockers": current.get("decision_packet", {}).get("blockers", []), "effects": []}))
        return 0 if result["status"] == "checked" else 1
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, StopIteration) as error:
        print(json.dumps({"hygiene": {"status": "unexecuted", "reason": type(error).__name__}, "effects": []}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
