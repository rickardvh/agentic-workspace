"""Carry selected Configuration requests or one action and its native consequence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def method_revision() -> str:
    here = Path(__file__).resolve()
    material = [hashlib.sha256(path.read_bytes()).hexdigest() for path in (here, here.with_name("SKILL.md"))]
    return hashlib.sha256(json.dumps(material).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-cli", default="agentic-workspace")
    parser.add_argument("--target", default=".")
    parser.add_argument("--task", required=True)
    parser.add_argument("--changed", action="append", default=[])
    parser.add_argument("--input", type=Path, help="One exact current Configuration request or already-authorized action.")
    parser.add_argument("--concern", choices=["instructions", "diagnostics", "assignment", "modules", "invocation", "preferences"])
    parser.add_argument("--no-change", action="store_true", help="No retained value or source change is justified; perform no owner calls.")
    parser.add_argument("--expected-method-revision")
    args = parser.parse_args()
    calls = 0
    effect_entered = False
    try:
        revision = method_revision()
    except OSError as error:
        print(json.dumps({"status": "unavailable", "effect_outcome": "not-invoked", "reason": str(error), "owner_calls": 0}))
        return 2

    def emit(result: dict) -> None:
        print(
            json.dumps(
                {"kind": "agentic-workspace/configuration-procedure-result/v1", "method_revision": revision, "owner_calls": calls, **result}
            )
        )

    def call(command: str, payload: dict | list | None = None, context: dict | None = None) -> dict:
        nonlocal calls, effect_entered
        context = context or {"target": args.target, "task": args.task, "changed": args.changed}
        argv = [args.native_cli, command, "--target", context["target"], "--task", context["task"], "--format", "json"]
        if command == "start":
            argv += ["--projection", "full"]
        for path in context.get("changed", []):
            argv += ["--changed", path]
        if payload is not None:
            argv += ["--input", "-"]
        if method_revision() != revision:
            raise ValueError("method material changed before native entry; reprepare")
        calls += 1
        effect_entered = effect_entered or command == "invoke"
        response = subprocess.run(
            argv, input=json.dumps(payload) if payload is not None else None, capture_output=True, text=True, encoding="utf-8", timeout=60
        )
        # Native failure packets preserve their own effect/continuation truth.
        result = json.loads(response.stdout)
        if not isinstance(result, dict):
            raise ValueError("native response must be an object")
        return result

    try:
        if args.expected_method_revision and args.expected_method_revision != revision:
            emit({"status": "stale-method", "effect_outcome": "not-invoked", "retry_effect": False})
            return 2
        if args.no_change:
            if args.input or args.concern:
                raise ValueError("no-change cannot carry a request or selected concern")
            emit({"status": "no-change", "retained": False, "effect_outcome": "not-required"})
            return 0
        if args.input:
            if args.concern:
                raise ValueError("an exact input already selects its concern")
            selected = json.loads(args.input.read_text(encoding="utf-8"))
            if isinstance(selected, list):
                if (
                    not selected
                    or not all(isinstance(row, dict) and row.get("kind") == "agentic-workspace/public-request/v1" for row in selected)
                    or not any(row.get("owner") == "configuration" for row in selected)
                ):
                    raise ValueError("expected a current request set containing its Configuration concern")
                result = call("start", selected)
            elif selected.get("kind") == "agentic-workspace/operation-invocation/v1" and selected.get("source_owner") == "configuration":
                result = call("invoke", selected)
            elif selected.get("kind") == "agentic-workspace/public-request/v1" and selected.get("owner") == "configuration":
                result = call("start", selected)
            else:
                raise ValueError("expected an exact Configuration request or invocation")
        else:
            if not args.concern:
                raise ValueError("select a concern, supply an exact input, or choose no-change")
            current = call("start")
            request = current.get("configuration_write", {}).get("behavior_request")
            if not request:
                emit({"status": "unavailable", "native_result": current, "effect_outcome": "not-invoked"})
                return 2
            request["arguments"]["concern"] = args.concern
            result = call("start", request)
        # Do not replay a write, infer success from process exit, or manufacture
        # a source owner's satisfaction from saved bytes. Keep exact results.
        emit({"status": "returned-owner-result", "native_result": result, "retry_effect": False})
        return 0 if "error" not in result else 2
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        emit(
            {
                "status": "reentry-required" if effect_entered else "unavailable",
                "effect_outcome": "unknown" if effect_entered else "not-invoked",
                "reason": str(error),
                "context": {"target": args.target, "task": args.task, "changed": args.changed},
                "retry_effect": False,
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
