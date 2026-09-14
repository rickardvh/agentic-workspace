#!/usr/bin/env python3
"""Compatibility pointer to the canonical skill; never a fallback runtime."""

import json


def run_no_cli_fallback() -> int:
    print(json.dumps({
        "kind": "agentic-workspace/procedure-pointer/v1",
        "procedure": ".agentic-workspace/skills/workspace-startup/SKILL.md",
        "runtime_facts": "unknown",
        "authority": "none",
    }, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(run_no_cli_fallback())
