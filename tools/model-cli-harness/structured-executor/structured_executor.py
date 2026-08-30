"""Maintainer-only validate and replay entrypoint for the Structured Executor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import jsonschema
from kernel import canonical_json_bytes
from replay import replay

ROOT = Path(__file__).resolve().parent


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(name: str) -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(_read_json(ROOT / "contracts" / name))


def _validate(args: argparse.Namespace) -> int:
    state = _read_json(args.state)
    _validator("state.schema.json").validate(state)
    transition_validator = _validator("transition.schema.json")
    for transition in _read_json(args.transitions) if args.transitions else []:
        transition_validator.validate(transition)
    print(json.dumps({"status": "valid", "state_revision": state["revision"]}, sort_keys=True))
    return 0


def _replay(args: argparse.Namespace) -> int:
    initial_state = _read_json(args.initial_state)
    transition_inputs = _read_json(args.transitions)
    final_state, records = replay(initial_state, transition_inputs)
    payload = {"final_state": final_state, "transitions": records}
    print(canonical_json_bytes(payload).decode("utf-8"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--state", type=Path, required=True)
    validate.add_argument("--transitions", type=Path)
    validate.set_defaults(handler=_validate)
    replay_command = commands.add_parser("replay")
    replay_command.add_argument("--initial-state", type=Path, required=True)
    replay_command.add_argument("--transitions", type=Path, required=True)
    replay_command.set_defaults(handler=_replay)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
