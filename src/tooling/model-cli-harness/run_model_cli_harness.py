"""Bounded consumer runs through current public operations and independent outcomes.

Retired command-mention suites do not select subjects or establish current proof.
Historical reports remain readable by external_agent_evaluation_lane.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from consumer_outcomes import Expected, evaluate, snapshot

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "release"))


class PublicClient:
    """Transport only: no private requests, choreography or proof grants."""

    def __init__(self, consumer):
        self.consumer = consumer

    def call(self, operation: str, *arguments: str):
        if operation not in {"setup", "start", "invoke", "resources", "worker"}:
            raise ValueError("Unsupported public operation")
        result = self.consumer.exec([*self.consumer.command, operation, *arguments, "--format", "json"])
        return json.loads(result.stdout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    score = commands.add_parser("score", help="Score stopped inert exports against trusted expectations")
    for name in ("before", "after", "expectations", "claim", "result"):
        score.add_argument("--" + name, type=Path, required=True)
    run = commands.add_parser("run", help="Execute one independently reset installed consumer case")
    subject = run.add_mutually_exclusive_group(required=True)
    subject.add_argument("--candidate", type=Path)
    subject.add_argument("--public-version")
    run.add_argument("--previous-public-version")
    run.add_argument("--family", required=True)
    run.add_argument("--backend", choices=["native", "docker"], required=True)
    run.add_argument("--profile", choices=["node", "python", "standalone", "cargo"], required=True)
    run.add_argument("--target", required=True)
    run.add_argument("--image")
    run.add_argument("--scratch", type=Path, required=True)
    run.add_argument("--result", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.result.exists():
        parser.error("Preserve initial results; use a separate diagnostic result")
    if args.operation == "run":
        return run_case(args)
    expected = Expected(**json.loads(args.expectations.read_text(encoding="utf-8")))
    # Offline scoring has no installation/execution witness and cannot pass a journey.
    result = evaluate(
        snapshot(args.before),
        snapshot(args.after),
        expected,
        claim=json.loads(args.claim.read_text(encoding="utf-8")),
        executed=False,
        subject_verified=False,
    )
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 1


def run_case(args):
    from consumer_environment import DockerConsumer, NativeConsumer, Subject, build_image
    from consumer_journeys import FAMILIES, execute, execute_pair

    started = time.monotonic()
    result = {
        "kind": "agentic-workspace/consumer-run/v1",
        "family": args.family,
        "driver": "deterministic",
        "status": "assigned",
        "executed": False,
        "cleanup": "not-started",
    }
    consumer = None
    try:
        if args.family not in FAMILIES:
            raise ValueError("Unknown scenario family")
        with tempfile.TemporaryDirectory(prefix="subjects-", dir=args.scratch) as directory:
            root = Path(directory)
            subject = Subject.candidate(args.candidate) if args.candidate else Subject.public(args.public_version, root / "current")
            result["requested"] = subject.identity()
            image = (args.image or build_image(args.profile, args.target)) if args.backend == "docker" else None

            def prepare(selected):
                if image:
                    return DockerConsumer(selected, args.profile, args.target, image)
                return NativeConsumer(selected, args.profile, args.target, args.scratch)

            if args.family in {"local-independence", "upgrade"}:
                if not args.previous_public_version:
                    raise ValueError("Paired family requires --previous-public-version")
                previous = Subject.public(args.previous_public_version, root / "previous")
                result.update(execute_pair(lambda: prepare(subject), lambda: prepare(previous), args.family, subject))
            else:
                consumer = prepare(subject)
                with consumer:
                    consumer.install()
                    result.update(execute(consumer, args.family))
    except (Exception, KeyboardInterrupt) as error:
        result.update(status="failed", error=str(error)[:2000], failure_class="environment-or-installation")
    finally:
        if consumer:
            result["cleanup"] = consumer.cleanup
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        with args.result.open("x", encoding="utf-8") as output:
            output.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
