#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPACT_RUNNER = REPO_ROOT / "scripts" / "check" / "run_compact_command.py"
GENERATED_PACKAGE_CHECK = REPO_ROOT / "scripts" / "check" / "check_generated_command_packages.py"


class ProofStep(NamedTuple):
    label: str
    args: list[str]


def _format_duration(duration_seconds: float) -> str:
    if duration_seconds < 1:
        return f"{duration_seconds * 1000:.0f}ms"
    return f"{duration_seconds:.2f}s"


def _proof_steps(args: argparse.Namespace) -> list[ProofStep]:
    requested = {
        "static": bool(args.static),
        "conformance": bool(args.conformance),
        "docker": bool(args.docker),
        "docker_conformance": bool(args.docker_conformance),
    }
    if args.all:
        requested = dict.fromkeys(requested, True)
    if not any(requested.values()):
        requested["docker"] = True
        requested["docker_conformance"] = True

    steps: list[ProofStep] = []
    if requested["static"]:
        steps.append(ProofStep("generated packages static", []))
    if requested["conformance"]:
        steps.append(ProofStep("generated packages conformance", ["--conformance", "--require-node"]))
    if requested["docker"]:
        steps.append(ProofStep("generated packages docker", ["--docker", "--require-docker"]))
    if requested["docker_conformance"]:
        steps.append(ProofStep("generated packages docker conformance", ["--docker-conformance", "--require-docker"]))
    return steps


def _run_step(step: ProofStep, *, timeout_seconds: float | None, failure_tail_lines: int) -> int:
    command = [
        sys.executable,
        str(COMPACT_RUNNER),
        "--label",
        step.label,
        "--failure-tail-lines",
        str(failure_tail_lines),
    ]
    if timeout_seconds is not None:
        command.extend(["--timeout-seconds", f"{timeout_seconds:g}"])
    command.extend(
        [
            "--",
            sys.executable,
            str(GENERATED_PACKAGE_CHECK),
            *step.args,
        ]
    )
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run generated command package proof through compact command wrappers.",
    )
    parser.add_argument("--static", action="store_true", help="Run static generated-package proof.")
    parser.add_argument("--conformance", action="store_true", help="Run local Node adapter conformance proof.")
    parser.add_argument("--docker", action="store_true", help="Run Docker package proof.")
    parser.add_argument("--docker-conformance", action="store_true", help="Run Docker adapter conformance proof.")
    parser.add_argument("--all", action="store_true", help="Run static, local conformance, Docker, and Docker conformance proof.")
    parser.add_argument(
        "--timeout-seconds",
        type=_positive_float,
        default=300,
        help="Per-step timeout passed to the compact runner. Defaults to 300 seconds.",
    )
    parser.add_argument(
        "--failure-tail-lines",
        type=int,
        default=80,
        help="Per-step failure tail lines passed to the compact runner.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.perf_counter()
    steps = _proof_steps(args)
    for step in steps:
        status = _run_step(
            step,
            timeout_seconds=args.timeout_seconds,
            failure_tail_lines=max(1, int(args.failure_tail_lines)),
        )
        if status:
            return status
    print(f"[ok] generated command package proof ({len(steps)} steps, {_format_duration(time.perf_counter() - started)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
