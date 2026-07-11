from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    profile_path, executable, runner, target = sys.argv[1:5]
    profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    operation = next(item for item in profile["operations"] if item["id"] == "config.report")
    if operation["external_consumption"]["status"] not in {"supported", "runtime-backed"}:
        raise SystemExit("config.report is not consumable")
    completed = subprocess.run(
        [executable, runner, "config", "--target", target, "--select", "workspace.workflow_obligations", "--format", "json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        sys.stderr.write(completed.stderr)
        return completed.returncode
    payload = json.loads(completed.stdout)
    print(json.dumps({"operation": "config.report", "result": payload}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
