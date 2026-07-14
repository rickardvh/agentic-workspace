from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


STATE_RELATIVE = Path(".agentic-workspace/local/chatgpt-review-loop")


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def start(root: Path) -> dict[str, object]:
    root = root.resolve()
    state_dir = root / STATE_RELATIVE
    state_dir.mkdir(parents=True, exist_ok=True)
    pid_path = state_dir / "poller.pid"
    if pid_path.is_file():
        try:
            existing = json.loads(pid_path.read_text(encoding="utf-8"))
            pid = int(existing["pid"])
        except (OSError, ValueError, TypeError, json.JSONDecodeError, KeyError):
            pid = 0
        if pid and _is_running(pid):
            return {"status": "already-running", "pid": pid}
        pid_path.unlink(missing_ok=True)

    log = state_dir / "poller.log"
    command = [
        sys.executable,
        "tools/chatgpt_review_loop.py",
        "poll",
        "--target",
        root.as_posix(),
        "--all-open",
        "--watch",
    ]
    with log.open("a", encoding="utf-8") as stream:
        kwargs: dict[str, object] = {"cwd": root, "stdin": subprocess.DEVNULL, "stdout": stream, "stderr": subprocess.STDOUT}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        process = subprocess.Popen(command, **kwargs)  # noqa: S603
    pid_path.write_text(json.dumps({"pid": process.pid, "command": command}) + "\n", encoding="utf-8")
    return {"status": "started", "pid": process.pid, "log": log.relative_to(root).as_posix()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start one detached global ChatGPT review poller for this checkout.")
    parser.add_argument("--target", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    print(json.dumps(start(args.target), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
