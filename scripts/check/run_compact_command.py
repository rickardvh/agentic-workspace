#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_ROOT = REPO_ROOT / "scratch" / "command-logs"
RESULT_ROOT = REPO_ROOT / "scratch" / "validation-results"
PLAN_PATH = REPO_ROOT / "docs" / "maintainer" / "validation-runtime-2435" / "validation-plan.json"
DEFAULT_FAILURE_TAIL_LINES = 80
DEFAULT_PROGRESS_INTERVAL_SECONDS = 30.0
DEFAULT_PROGRESS_THRESHOLD_SECONDS = 30.0
TIMEOUT_EXIT_CODE = 124
DUPLICATE_EXIT_CODE = 125
MANIFEST_LOCK_WAIT_SECONDS = 10.0
MANIFEST_LOCK_POLL_SECONDS = 0.05


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
    return datetime.now(timezone.utc).isoformat()


def _result_path(*, result_root: Path, run_id: str, constituent_id: str) -> Path:
    return result_root / _slugify(run_id) / f"{_slugify(constituent_id)}.json"


def _attempt_result_path(*, result_root: Path, run_id: str, constituent_id: str) -> Path:
    attempt_root = result_root / _slugify(run_id) / "attempts"
    attempt_root.mkdir(parents=True, exist_ok=True)
    attempt_index = 2
    while True:
        candidate = attempt_root / f"{_slugify(constituent_id)}.attempt-{attempt_index}.json"
        if not candidate.exists():
            return candidate
        attempt_index += 1


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(path)


def _acquire_lock(lock_path: Path, *, wait_seconds: float = MANIFEST_LOCK_WAIT_SECONDS) -> int:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            return os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"timed out waiting for validation result lock: {lock_path.relative_to(REPO_ROOT).as_posix()}") from exc
            time.sleep(MANIFEST_LOCK_POLL_SECONDS)


def _release_lock(lock_path: Path, fd: int) -> None:
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        lock_path.unlink()
    except OSError:
        pass


def _load_plan() -> dict[str, object] | None:
    if not PLAN_PATH.is_file():
        return None
    try:
        plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return plan if isinstance(plan, dict) else None


def _repo_relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _plan_graph_payload(plan: dict[str, object]) -> dict[str, object]:
    trace_fixtures = []
    for trace in plan.get("trace_fixtures", []):
        if not isinstance(trace, dict):
            continue
        events = [
            {
                "constituent_id": str(event.get("constituent_id", "")),
                "outcome": str(event.get("outcome", "")),
                **({"repeat_allowed": True} if event.get("repeat_allowed") else {}),
            }
            for event in trace.get("events", [])
            if isinstance(event, dict)
        ]
        trace_fixtures.append({"id": trace.get("id"), "command": trace.get("command"), "events": events})
    return {
        "kind": plan.get("kind"),
        "schema_version": plan.get("schema_version"),
        "issue": plan.get("issue"),
        "parallel_modes": plan.get("parallel_modes", []),
        "compact_label_map": plan.get("compact_label_map", {}),
        "constituents": plan.get("constituents", []),
        "duplicate_dispositions": plan.get("duplicate_dispositions", []),
        "trace_fixtures": trace_fixtures,
    }


def _sha256_json(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _plan_identity(plan: dict[str, object]) -> dict[str, object]:
    raw = PLAN_PATH.read_bytes() if PLAN_PATH.is_file() else b""
    graph_payload = _plan_graph_payload(plan)
    return {
        "kind": "agentic-workspace/validation-plan-identity/v1",
        "path": _repo_relative(PLAN_PATH),
        "schema_version": plan.get("schema_version"),
        "issue": plan.get("issue"),
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "graph_sha256": _sha256_json(graph_payload),
    }


def _git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _repository_identity() -> dict[str, object]:
    status = _git_value("status", "--porcelain=v1", "--untracked-files=no")
    try:
        runtime = json.loads(os.environ.get("AW_RUNTIME_IDENTITY", "{}"))
    except json.JSONDecodeError:
        runtime = {}
    return {
        "kind": "agentic-workspace/validation-repository-identity/v1",
        "head": _git_value("rev-parse", "HEAD"),
        "tree": _git_value("rev-parse", "HEAD^{tree}"),
        "tracked_dirty": bool(status.strip()),
        "runtime": runtime if isinstance(runtime, dict) else {},
    }


def _load_plan_metadata(label: str) -> dict[str, object]:
    plan = _load_plan()
    if plan is None:
        return {}
    label_map = plan.get("compact_label_map")
    if not isinstance(label_map, dict):
        return {}
    metadata = label_map.get(label)
    if not isinstance(metadata, dict):
        return {}
    constituent_id = str(metadata.get("id") or "")
    constituents = {str(item.get("id")): item for item in plan.get("constituents", []) if isinstance(item, dict) and item.get("id")}
    constituent = constituents.get(constituent_id, {})
    merged = dict(constituent)
    merged.update(metadata)
    merged["plan_identity"] = _plan_identity(plan)
    return merged


def _record_paths_for_run(run_root: Path) -> list[Path]:
    paths = [path for path in run_root.glob("*.json") if path.name != "manifest.json"]
    attempts_root = run_root / "attempts"
    if attempts_root.is_dir():
        paths.extend(attempts_root.glob("*.json"))
    return sorted(paths)


def _update_manifest(*, result_root: Path, run_id: str) -> None:
    run_root = result_root / _slugify(run_id)
    manifest_path = run_root / "manifest.json"
    lock_path = run_root / "manifest.lock"
    fd = _acquire_lock(lock_path)
    try:
        records: list[dict[str, object]] = []
        for path in _record_paths_for_run(run_root):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict) and payload.get("kind") == "agentic-workspace/validation-constituent-result/v1":
                payload["result_path"] = path.relative_to(REPO_ROOT).as_posix()
                records.append(payload)
        records.sort(key=lambda item: (str(item.get("started_at", "")), str(item.get("constituent_id", ""))))
        outcomes = {}
        for record in records:
            outcome = str(record.get("outcome") or "unknown")
            outcomes[outcome] = int(outcomes.get(outcome, 0)) + 1
        started_values: list[datetime] = []
        ended_values: list[datetime] = []
        summed_work_seconds = 0.0
        for record in records:
            summed_work_seconds += float(record.get("duration_seconds") or 0.0)
            for field, target in (("started_at", started_values), ("ended_at", ended_values)):
                value = record.get(field)
                if not isinstance(value, str):
                    continue
                try:
                    target.append(datetime.fromisoformat(value))
                except ValueError:
                    continue
        if started_values and ended_values:
            critical_path_seconds = max((max(ended_values) - min(started_values)).total_seconds(), 0.0)
        else:
            critical_path_seconds = summed_work_seconds
        plan_identity = next((record.get("plan_identity") for record in records if isinstance(record.get("plan_identity"), dict)), {})
        repository_identity = next((record.get("repository") for record in records if isinstance(record.get("repository"), dict)), {})
        payload = {
            "kind": "agentic-workspace/validation-run-manifest/v1",
            "run_id": run_id,
            "updated_at": _utc_now(),
            "plan_identity": plan_identity,
            "repository": repository_identity,
            "result_count": len(records),
            "outcomes": outcomes,
            "critical_path_seconds": round(critical_path_seconds, 6),
            "summed_work_seconds": round(summed_work_seconds, 6),
            "results": records,
        }
        _atomic_write_json(manifest_path, payload)
    finally:
        _release_lock(lock_path, fd)


def _write_result(
    *,
    result_path: Path,
    run_id: str,
    constituent_id: str,
    label: str,
    command: list[str],
    cwd: Path,
    dependencies: list[str],
    proof_purpose: str,
    execution_posture: str,
    owner_boundary: str,
    plan_identity: dict[str, object],
    repository_identity: dict[str, object],
    started_at: str,
    ended_at: str,
    duration_seconds: float,
    outcome: str,
    exit_code: int | None,
    timed_out: bool,
    log_path: Path | None,
    heartbeat: dict[str, object],
) -> Path:
    payload = {
        "kind": "agentic-workspace/validation-constituent-result/v1",
        "constituent_id": constituent_id,
        "label": label,
        "command": command,
        "cwd": cwd.relative_to(REPO_ROOT).as_posix() if cwd.is_relative_to(REPO_ROOT) else cwd.as_posix(),
        "dependencies": dependencies,
        "proof_purpose": proof_purpose,
        "execution_posture": execution_posture,
        "owner_boundary": owner_boundary,
        "plan_identity": plan_identity,
        "repository": repository_identity,
        "run_id": run_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": round(duration_seconds, 6),
        "outcome": outcome,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "log_path": log_path.relative_to(REPO_ROOT).as_posix() if log_path is not None else None,
        "heartbeat": heartbeat,
    }
    _atomic_write_json(result_path, payload)
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
    progress_interval_seconds: float,
    progress_threshold_seconds: float,
    progress_label: str,
    constituent_id: str,
    durable_result_path: str,
    monotonic: Callable[[], float] = time.monotonic,
    process_factory: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
    emit_heartbeat: Callable[[str], None] | None = None,
) -> tuple[int | None, str, str, bool, dict[str, object]]:
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

    process = process_factory(command, **popen_kwargs)
    started = monotonic()
    deadline = started + timeout_seconds if timeout_seconds is not None else None
    next_progress = started + progress_threshold_seconds
    heartbeat_elapsed_seconds: list[float] = []
    heartbeat_writer = emit_heartbeat or (lambda message: print(message, file=sys.stderr, flush=True))
    while True:
        now = monotonic()
        wait_until = next_progress if deadline is None else min(next_progress, deadline)
        wait_seconds = max(0.001, wait_until - now)
        try:
            stdout, stderr = process.communicate(timeout=wait_seconds)
            return process.returncode, stdout or "", stderr or "", False, {
                "kind": "agentic-workspace/validation-heartbeat/v1",
                "count": len(heartbeat_elapsed_seconds),
                "elapsed_seconds": heartbeat_elapsed_seconds,
                "threshold_seconds": progress_threshold_seconds,
                "interval_seconds": progress_interval_seconds,
                "claim": "process-liveness-only",
            }
        except subprocess.TimeoutExpired as exc:
            now = monotonic()
            if deadline is not None and now >= deadline:
                _terminate_process_tree(process)
                stdout, stderr = process.communicate()
                combined_stdout = _combine_output(exc.stdout, stdout)
                combined_stderr = _combine_output(exc.stderr, stderr)
                return None, combined_stdout, combined_stderr, True, {
                    "kind": "agentic-workspace/validation-heartbeat/v1",
                    "count": len(heartbeat_elapsed_seconds),
                    "elapsed_seconds": heartbeat_elapsed_seconds,
                    "threshold_seconds": progress_threshold_seconds,
                    "interval_seconds": progress_interval_seconds,
                    "claim": "process-liveness-only",
                }
            elapsed = now - started
            heartbeat_elapsed_seconds.append(round(elapsed, 6))
            heartbeat_writer(
                f"[heartbeat] {progress_label} ({constituent_id}) still running "
                f"({_format_duration(elapsed)} elapsed; process liveness only; output buffered); result: {durable_result_path}"
            )
            next_progress = now + progress_interval_seconds


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
        "--progress-threshold-seconds",
        type=_positive_float,
        default=DEFAULT_PROGRESS_THRESHOLD_SECONDS,
        help="Wait this many seconds before the first still-running heartbeat (default: 30).",
    )
    parser.add_argument(
        "--progress-interval-seconds",
        type=_positive_float,
        default=DEFAULT_PROGRESS_INTERVAL_SECONDS,
        help="Emit a compact still-running heartbeat after this many seconds (default: 30).",
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
    plan_metadata = _load_plan_metadata(str(args.label))
    constituent_id = args.id or str(plan_metadata.get("id") or _slugify(args.label))
    dependencies = [str(item) for item in args.depends_on] or [str(item) for item in plan_metadata.get("dependencies", [])]
    proof_purpose = str(args.proof_purpose or plan_metadata.get("proof_purpose") or args.label)
    execution_posture = str(plan_metadata.get("execution_posture") or "")
    owner_boundary = str(plan_metadata.get("owner_boundary") or "")
    plan_identity = plan_metadata.get("plan_identity") if isinstance(plan_metadata.get("plan_identity"), dict) else {}
    repository_identity = _repository_identity()
    result_root = (REPO_ROOT / args.result_dir).resolve()
    pending_result_path = _result_path(result_root=result_root, run_id=args.run_id, constituent_id=constituent_id)
    result_lock_path = pending_result_path.with_suffix(".lock")
    result_lock_fd: int | None = None
    if pending_result_path.exists() and not args.allow_repeat:
        print(
            f"[duplicate] {args.label} ({constituent_id}) already has a result for run {args.run_id}: "
            f"{pending_result_path.relative_to(REPO_ROOT).as_posix()}",
            file=sys.stderr,
        )
        return DUPLICATE_EXIT_CODE
    if args.allow_repeat and pending_result_path.exists():
        result_path = _attempt_result_path(result_root=result_root, run_id=args.run_id, constituent_id=constituent_id)
    else:
        try:
            result_lock_fd = _acquire_lock(result_lock_path, wait_seconds=0.0)
        except RuntimeError:
            print(
                f"[duplicate] {args.label} ({constituent_id}) is already running for run {args.run_id}: "
                f"{result_lock_path.relative_to(REPO_ROOT).as_posix()}",
                file=sys.stderr,
            )
            return DUPLICATE_EXIT_CODE
        result_path = pending_result_path
    started_at = _utc_now()
    print(f"[run] {args.label} ({constituent_id})", flush=True)
    started = time.perf_counter()
    durable_result_path = _repo_relative(result_path)
    returncode, stdout, stderr, timed_out, heartbeat = _run_command(
        args.command,
        cwd=working_directory,
        timeout_seconds=args.timeout_seconds,
        progress_interval_seconds=args.progress_interval_seconds,
        progress_threshold_seconds=args.progress_threshold_seconds,
        progress_label=args.label,
        constituent_id=constituent_id,
        durable_result_path=durable_result_path,
    )
    duration_seconds = time.perf_counter() - started
    duration = _format_duration(duration_seconds)
    ended_at = _utc_now()
    if returncode == 0:
        try:
            _write_result(
                result_path=result_path,
                run_id=args.run_id,
                constituent_id=constituent_id,
                label=args.label,
                command=args.command,
                cwd=working_directory,
                dependencies=dependencies,
                proof_purpose=proof_purpose,
                execution_posture=execution_posture,
                owner_boundary=owner_boundary,
                plan_identity=plan_identity,
                repository_identity=repository_identity,
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=duration_seconds,
                outcome="passed",
                exit_code=returncode,
                timed_out=False,
                log_path=None,
                heartbeat=heartbeat,
            )
            _update_manifest(result_root=result_root, run_id=args.run_id)
        finally:
            if result_lock_fd is not None:
                _release_lock(result_lock_path, result_lock_fd)
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
    try:
        result_path = _write_result(
            result_path=result_path,
            run_id=args.run_id,
            constituent_id=constituent_id,
            label=args.label,
            command=args.command,
            cwd=working_directory,
            dependencies=dependencies,
            proof_purpose=proof_purpose,
            execution_posture=execution_posture,
            owner_boundary=owner_boundary,
            plan_identity=plan_identity,
            repository_identity=repository_identity,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            outcome="timeout" if timed_out else "failed",
            exit_code=None if timed_out else int(returncode),
            timed_out=timed_out,
            log_path=log_path,
            heartbeat=heartbeat,
        )
        _update_manifest(result_root=result_root, run_id=args.run_id)
    finally:
        if result_lock_fd is not None:
            _release_lock(result_lock_path, result_lock_fd)

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
