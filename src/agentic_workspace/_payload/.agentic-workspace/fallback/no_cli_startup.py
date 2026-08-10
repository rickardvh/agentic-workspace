#!/usr/bin/env python3
"""Fail-closed Agentic Workspace startup when the configured CLI is unavailable."""

from __future__ import annotations

import json
import os
import shutil
import tomllib
from pathlib import Path


def _emit(payload: dict[str, object], *, code: int) -> int:
    print(json.dumps(payload, sort_keys=True))
    return code


def run_no_cli_fallback() -> int:
    workspace = Path(__file__).resolve().parents[1]
    policy_path = workspace / "fallback" / "no-cli-policy.json"
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _emit(
            {
                "kind": "agentic-workspace/no-cli-startup/v1",
                "status": "blocked",
                "completion_claim_allowed": False,
                "implementation_allowed": False,
                "next_safe_action": "repair-installed-fallback",
                "errors": [str(exc)],
            },
            code=2,
        )

    invocation = str(os.environ.get("AGENTIC_WORKSPACE_CONFIGURED_INVOCATION", "agentic-workspace")).split()[0]
    if shutil.which(invocation):
        return _emit(
            {
                "kind": "agentic-workspace/no-cli-startup/v1",
                "status": "not-applicable",
                "completion_claim_allowed": False,
                "implementation_allowed": False,
                "next_safe_action": "use-configured-agentic-workspace-invocation",
                "errors": ["configured Agentic Workspace invocation is available"],
            },
            code=3,
        )

    required = [str(value) for value in policy.get("required_surfaces", [])]
    missing = [relative for relative in required if not (workspace.parent / relative).is_file()]
    try:
        config = tomllib.loads((workspace / "config.toml").read_text(encoding="utf-8"))
        selected_modules = [str(value) for value in config.get("modules", {}).get("enabled", [])]
    except (OSError, tomllib.TOMLDecodeError, TypeError) as exc:
        return _emit(
            {
                "kind": "agentic-workspace/no-cli-startup/v1",
                "status": "blocked",
                "completion_claim_allowed": False,
                "implementation_allowed": False,
                "next_safe_action": "repair-installed-fallback",
                "errors": [f"cannot read installed module selection: {exc}"],
            },
            code=2,
        )
    module_boundaries: dict[str, str] = {}
    for module, entry in policy.get("module_boundaries", {}).items():
        if not isinstance(entry, dict):
            continue
        if str(module) in selected_modules:
            module_boundaries[str(module)] = str(entry.get("boundary", ""))
            surface = str(entry.get("surface", ""))
            if entry.get("required_when_selected") is True and not (workspace.parent / surface).is_file():
                missing.append(surface)
    if missing:
        return _emit(
            {
                "kind": "agentic-workspace/no-cli-startup/v1",
                "status": "blocked",
                "completion_claim_allowed": False,
                "implementation_allowed": False,
                "next_safe_action": "repair-installed-fallback",
                "selected_modules": selected_modules,
                "errors": [f"required installed fallback surface is missing: {value}" for value in missing],
            },
            code=2,
        )
    return _emit(
        {
            "kind": "agentic-workspace/no-cli-startup/v1",
            "status": "fallback",
            "completion_claim_allowed": False,
            "implementation_allowed": False,
            "forbidden_actions": list(policy.get("forbidden_actions", [])),
            "module_boundaries": module_boundaries,
            "network_access": "not-required",
            "next_safe_action": str(policy.get("next_safe_action", "repair-installed-fallback")),
            "selected_modules": selected_modules,
        },
        code=0,
    )


if __name__ == "__main__":
    raise SystemExit(run_no_cli_fallback())
