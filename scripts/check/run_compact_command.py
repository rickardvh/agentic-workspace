#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_ROOT = REPO_ROOT / "scratch" / "command-logs"
DEFAULT_FAILURE_TAIL_LINES = 80


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower())
    return slug.strip("-") or "command"


def _format_duration(duration_seconds: float) -> str:
    if duration_seconds < 1:
        return f"{duration_seconds * 1000:.0f}ms"
    return f"{duration_seconds:.2f}s"


def _log_path(*, label: str) -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return LOG_ROOT / f"{timestamp}-{_slugify(label)}.log"


def _print_failure_output(*, combined_output: str, tail_lines: int, log_path: Path) -> None:
    if not combined_output.strip():
        print("No command output captured.", file=sys.stderr)
        print(f"Full log: {log_path.relative_to(REPO_ROOT).as_posix()}", file=sys.stderr)
        return
    lines = combined_output.rstrip().splitlines()
    if len(lines) > tail_lines:
        omitted = len(lines) - tail_lines
        print(f"Output tail ({tail_lines} lines shown, {omitted} omitted):", file=sys.stderr)
        lines = lines[-tail_lines:]
    else:
        print("Command output:", file=sys.stderr)
    for line in lines:
        print(line, file=sys.stderr)
    print(f"Full log: {log_path.relative_to(REPO_ROOT).as_posix()}", file=sys.stderr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a command with compact success output and tailed failure logs.")
    parser.add_argument("--label", required=True, help="Short human-readable label for the command.")
    parser.add_argument("--cwd", default=".", help="Working directory relative to the repository root.")
    parser.add_argument(
        "--failure-tail-lines",
        type=int,
        default=DEFAULT_FAILURE_TAIL_LINES,
        help="How many trailing lines to print on failure.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute after '--'.")
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("missing command to execute; pass it after '--'")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    working_directory = (REPO_ROOT / args.cwd).resolve()
    started = time.perf_counter()
    result = subprocess.run(
        args.command,
        cwd=working_directory,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    duration = _format_duration(time.perf_counter() - started)
    if result.returncode == 0:
        print(f"[ok] {args.label} ({duration})")
        return 0

    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = _log_path(label=args.label)
    combined_output = ""
    if result.stdout:
        combined_output += result.stdout
    if result.stderr:
        if combined_output and not combined_output.endswith("\n"):
            combined_output += "\n"
        combined_output += result.stderr
    log_path.write_text(combined_output, encoding="utf-8")

    print(f"[fail] {args.label} ({duration}, exit {result.returncode})", file=sys.stderr)
    _print_failure_output(
        combined_output=combined_output,
        tail_lines=max(1, int(args.failure_tail_lines)),
        log_path=log_path,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
