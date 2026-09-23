"""Existing release consumers reuse the complete installed first-contact case."""

from __future__ import annotations

import subprocess
from pathlib import Path

from consumer_journeys import execute, snapshot, validate_pointer_files


def journey(command: list[str], target: Path, env: dict[str, str]) -> None:
    class InstalledConsumer:
        repo = target
        root = target.parent
        observation = {"installed": {"boundary": "calling-release-owner"}}

        def exec(self, argv, *, timeout=120):
            return subprocess.run(argv, cwd=target, env=env, check=True, capture_output=True, text=True, timeout=timeout)

    consumer = InstalledConsumer()
    consumer.command = command
    result = execute(consumer, "first-contact")
    if result["status"] != "passed":
        raise ValueError(f"Installed first-contact journey failed: {result}")


def validate_pointer(target: Path) -> None:
    validate_pointer_files(snapshot(target))
