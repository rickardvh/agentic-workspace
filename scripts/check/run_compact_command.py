#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_ROOT = REPO_ROOT / "scratch" / "command-logs"
RESULT_ROOT = REPO_ROOT / "scratch" / "validation-results"
DEFAULT_FAILURE_TAIL_LINES = 80
TIMEOUT_EXIT_CODE = 124
DUPLICATE_EXIT_CODE = 125


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _result_path(*, result_root: Path, run_id: str, constituent_id: str) -> Path:
    return result_root / _slugify(run_id) / f"{_slugify(constituent_id)}.json"


def _write_result(
    *,
    result_root: Path,
    run_id: str,
    constituent_id: str,
    label: str,
    command: list[str],
    cwd: Path,
    dependencies: list[str],
    proof_purpose: str,
    started_at: str,
    ended_at: str,
    duration_seconds: float,
    outcome: str,
    exit_code: int | None,
    timed_out: bool,
    log_path: Path | None,
) -> Path:
    result_path = _result_path(result_root=result_root, run_id=run_id, constituent_id=constituent_id)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "agentic-workspace/validation-constituent-result/v1",
        "constituent_id": constituent_id,
        "label": label,
        "command": command,
        "cwd": cwd.relative_to(REPO_ROOT).as_posix() if cwd.is_relative_to(REPO_ROOT) else cwd.as_posix(),
        "dependencies": dependencies,
        "proof_purpose": proof_purpose,
        "run_id": run_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": round(duration_seconds, 6),
        "outcome": outcome,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "log_path": log_path.relative_to(REPO_ROOT).as_posix() if log_path is not None else None,
    }
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result_path


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


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def _combine_output(stdout: str | bytes | None, stderr: str | bytes | None) -> str:
    combined_output = ""
    for output in (stdout, stderr):
        if not output:
            continue
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        if combined_output and not combined_output.endswith("\n"):
            combined_output += "\n"
        combined_output += output
    return combined_output


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return
    try:
        os.killpg(process.pid, 9)
    except ProcessLookupError:
        return


def _run_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: float | None,
) -> tuple[int | None, str, str, bool]:
    popen_kwargs: dict[str, object] = {
        "cwd": cwd,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    process = subprocess.Popen(command, **popen_kwargs)
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        return process.returncode, stdout or "", stderr or "", False
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(process)
        stdout, stderr = process.communicate()
        combined_stdout = _combine_output(exc.stdout, stdout)
        combined_stderr = _combine_output(exc.stderr, stderr)
        return None, combined_stdout, combined_stderr, True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a command with compact success output and tailed failure logs.")
    parser.add_argument("--label", required=True, help="Short human-readable label for the command.")
    parser.add_argument("--id", default="", help="Stable constituent id. Defaults to a slug of --label.")
    parser.add_argument("--cwd", default=".", help="Working directory relative to the repository root.")
    parser.add_argument(
        "--depends-on",
        action="append",
        default=[],
        help="Stable constituent id this command depends on. May be repeated.",
    )
    parser.add_argument("--proof-purpose", default="", help="Short description of the proof claim this constituent supplies.")
    parser.add_argument(
        "--allow-repeat",
        action="store_true",
        help="Allow an existing result record for the same run id and constituent id to be overwritten.",
    )
    parser.add_argument(
        "--result-dir",
        default=str(RESULT_ROOT.relative_to(REPO_ROOT)),
        help="Directory for versioned machine-readable validation result records.",
    )
    parser.add_argument(
        "--run-id",
        default=os.environ.get("VALIDATION_RUN_ID", "local"),
        help="Validation run id used under --result-dir. Defaults to VALIDATION_RUN_ID or 'local'.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=_positive_float,
        default=None,
        help="Fail with compact timeout output after this many seconds.",
    )
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
    constituent_id = args.id or _slugify(args.label)
    result_root = (REPO_ROOT / args.result_dir).resolve()
    pending_result_path = _result_path(result_root=result_root, run_id=args.run_id, constituent_id=constituent_id)
    if pending_result_path.exists() and not args.allow_repeat:
        print(
            f"[duplicate] {args.label} ({constituent_id}) already has a result for run {args.run_id}: "
            f"{pending_result_path.relative_to(REPO_ROOT).as_posix()}",
            file=sys.stderr,
        )
        return DUPLICATE_EXIT_CODE
    started_at = _utc_now()
    print(f"[run] {args.label} ({constituent_id})", flush=True)
    started = time.perf_counter()
    returncode, stdout, stderr, timed_out = _run_command(
        args.command,
        cwd=working_directory,
        timeout_seconds=args.timeout_seconds,
    )
    duration_seconds = time.perf_counter() - started
    duration = _format_duration(duration_seconds)
    ended_at = _utc_now()
    if returncode == 0:
        _write_result(
            result_root=result_root,
            run_id=args.run_id,
            constituent_id=constituent_id,
            label=args.label,
            command=args.command,
            cwd=working_directory,
            dependencies=[str(item) for item in args.depends_on],
            proof_purpose=str(args.proof_purpose or args.label),
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            outcome="passed",
            exit_code=returncode,
            timed_out=False,
            log_path=None,
        )
        print(f"[ok] {args.label} ({duration})")
        return 0

    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = _log_path(label=args.label)
    combined_output = _combine_output(stdout, stderr)
    if timed_out:
        timeout_line = f"Command timed out after {args.timeout_seconds:g} seconds."
        if combined_output and not combined_output.endswith("\n"):
            combined_output += "\n"
        combined_output += timeout_line + "\n"
    log_path.write_text(combined_output, encoding="utf-8")
    result_path = _write_result(
        result_root=result_root,
        run_id=args.run_id,
        constituent_id=constituent_id,
        label=args.label,
        command=args.command,
        cwd=working_directory,
        dependencies=[str(item) for item in args.depends_on],
        proof_purpose=str(args.proof_purpose or args.label),
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=duration_seconds,
        outcome="timeout" if timed_out else "failed",
        exit_code=None if timed_out else int(returncode),
        timed_out=timed_out,
        log_path=log_path,
    )

    if timed_out:
        print(f"[timeout] {args.label} ({duration}, after {args.timeout_seconds:g}s)", file=sys.stderr)
    else:
        print(f"[fail] {args.label} ({duration}, exit {returncode})", file=sys.stderr)
    _print_failure_output(
        combined_output=combined_output,
        tail_lines=max(1, int(args.failure_tail_lines)),
        log_path=log_path,
    )
    print(f"Result: {result_path.relative_to(REPO_ROOT).as_posix()}", file=sys.stderr)
    return TIMEOUT_EXIT_CODE if timed_out else int(returncode)


if __name__ == "__main__":
    raise SystemExit(main())
