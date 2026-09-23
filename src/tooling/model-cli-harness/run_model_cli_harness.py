"""Bounded consumer runs through current public operations and independent outcomes.

Retired command-mention suites do not select subjects or establish current proof.
Historical reports remain readable by external_agent_evaluation_lane.py.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from consumer_outcomes import Expected, evaluate, snapshot


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
    args = parser.parse_args(argv)
    if args.result.exists():
        parser.error("Preserve initial results; use a separate diagnostic result")
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


if __name__ == "__main__":
    raise SystemExit(main())
