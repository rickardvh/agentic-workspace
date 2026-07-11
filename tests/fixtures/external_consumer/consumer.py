from __future__ import annotations

import json
import subprocess
import sys
from importlib.resources import files


def main() -> int:
    target = sys.argv[1]
    profile = json.loads(
        files("agentic_workspace._generated_cli_package_impl").joinpath("external_consumer_profile.json").read_text(encoding="utf-8")
    )
    operation = next(item for item in profile["operations"] if item["id"] == "config.report")
    if operation["external_consumption"]["status"] not in {"supported", "runtime-backed"}:
        raise SystemExit("config.report is not consumable")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from agentic_workspace import cli; import sys; raise SystemExit(cli.main(sys.argv[1:]))",
            "config",
            "--target",
            target,
            "--select",
            "workspace.workflow_obligations",
            "--format",
            "json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        sys.stderr.write(completed.stderr or completed.stdout)
        return completed.returncode
    payload = json.loads(completed.stdout)
    print(json.dumps({"operation": "config.report", "result": payload}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
