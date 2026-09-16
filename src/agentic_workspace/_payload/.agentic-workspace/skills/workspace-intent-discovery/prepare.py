"""Selected procedure mechanics over fresh native owner results; never effect authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def prepare(current: dict, *, procedure: str, judgment: str, scope: str) -> dict:
    config = current.get("configuration")
    if not isinstance(config, dict) or current.get("managed_state_interpreted") is False:
        return {"status": "unavailable", "reason": "current-configuration-unavailable", "executed": False}
    blockers = current.get("decision_packet", {}).get("blockers", [])
    result: dict[str, Any] = {"procedure": procedure, "judgment": judgment, "scope": scope, "effects": [], "authority": "procedure-only"}
    if judgment == "required-decision":
        result.update(
            posture="await-required-owner",
            remaining_judgment="Obtain the required current owner decision; a procedural preference supplies no answer or waiver.",
        )
    elif procedure == "intent":
        mode = (config.get("clarification") or {}).get("mode", "suggest")
        result["preference"] = mode
        if judgment == "clear":
            posture = "direct"
        else:
            posture = {
                "ask-first": "await-human-answer",
                "suggest": "surface-question-and-safe-assumptions",
                "auto-continue": "state-bounded-interpretation",
            }[mode]
        result.update(
            posture=posture,
            remaining_judgment="Choose the bounded question/interpretation and determine which progress is safe; never answer a required owner decision.",
        )
    elif procedure == "improvement":
        improvement_mode = {value: value for value in ("none", "reporting", "conservative", "proactive")}[
            config.get("improvement_latitude") or "conservative"
        ]
        result["preference"] = improvement_mode
        if judgment == "clear" or improvement_mode == "none":
            posture = "no-action"
        elif improvement_mode == "reporting" or (scope == "proactive" and improvement_mode != "proactive"):
            posture = "report"
        else:
            posture = "prepare-current-owner-proposal"
        result.update(
            posture=posture,
            remaining_judgment="Determine future value and the smallest responsible owner. A proposal still needs exact destination admission; trusted corrections and hard defects keep their own authority.",
        )
    else:
        planning = current.get("planning", {})
        result.update(
            posture="judge-planning-value",
            owner_context={key: planning.get(key) for key in ("status", "task_relation", "task_posture", "requests", "creation_requests")},
        )
        result["instructions"] = [row for row in current.get("instructions", {}).get("sources", []) if row.get("applicable")]
        result["remaining_judgment"] = (
            "Keep direct work direct; choose durable Planning only when continuity is valuable or current policy requires it. Use the exact native relation/posture and creation request."
        )
    result["owner_blockers"] = blockers
    result["status"] = "prepared"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--native-cli", default="agentic-workspace", help="Current installed native/CLI entrypoint; no shell command string."
    )
    parser.add_argument("--target", default=".")
    parser.add_argument("--task", required=True)
    parser.add_argument("--changed", action="append", default=[])
    parser.add_argument("--procedure", choices=["intent", "improvement", "planning"], default="intent")
    parser.add_argument(
        "--judgment",
        choices=["clear", "ambiguous", "required-decision"],
        required=True,
        help="Acting-agent semantic judgment, never inferred from task text. For improvement, clear means no material opportunity.",
    )
    parser.add_argument("--scope", choices=["current-work", "proactive"], default="current-work")
    parser.add_argument("--expected-revision")
    args = parser.parse_args()
    command = [args.native_cli, "start", "--target", args.target, "--task", args.task, "--projection", "full", "--format", "json"]
    for path in args.changed:
        command.extend(["--changed", path])
    try:
        response = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=60, check=True)
        current = json.loads(response.stdout)
        result = prepare(current, procedure=args.procedure, judgment=args.judgment, scope=args.scope)
        skills = Path(__file__).parent.parent
        references = [Path(__file__), skills / "workspace-intent-discovery/SKILL.md", skills / "workspace-instruction-correction/SKILL.md"]
        material = {
            "result": result,
            "task": args.task,
            "changed": args.changed,
            "procedure_sources": [hashlib.sha256(path.read_bytes()).hexdigest() for path in references],
        }
        revision = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()
        if args.expected_revision and args.expected_revision != revision:
            result = {"status": "stale", "reason": "Reprepare from current owners and renewed judgment.", "effects": []}
        result["revision"] = revision
        print(json.dumps(result))
        return 0
    except (OSError, subprocess.SubprocessError, ValueError, KeyError) as error:
        print(json.dumps({"status": "unavailable", "executed": False, "reason": type(error).__name__, "effects": []}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
