"""Installed interpreter entry: carry only Configuration's pending-notice effect."""

from __future__ import annotations

import sys
from pathlib import Path


def observe() -> None:
    # Wheel installation has no executable callback. The installed .pth runs at
    # the next ordinary interpreter entry, not only when a client imports AW.
    prefix = Path(sys.prefix).resolve()
    if not Path(__file__).resolve().is_relative_to(prefix):
        return
    target = prefix.parent
    if not (target / ".agentic-workspace/adoption.json").is_file():
        return
    try:
        # The stable bridge already directs session entry to Configuration.
        # This is only a no-write fast path, never an assessment/currentness claim.
        if b"<!-- agentic-workspace:update-observation:start -->" in (target / "AGENTS.md").read_bytes():
            return
        from ._binding import invoke, start

        context = {"target": str(target), "task": "Observe installed AW dependency", "projection": "full"}
        configuration = start(context).get("configuration_write", {})
        if configuration.get("update_notice_status") == "unavailable":
            raise RuntimeError("Configuration update notice requires recovery")
        notice = configuration.get("update_notice_request")
        if notice is None:
            return
        action = start({**context, "request": notice}).get("decision_packet", {}).get("primary_action", {})
        if (
            action.get("operation_id") != "configuration.write"
            or action.get("arguments", {}).get("request", {}).get("arguments", {}).get("key") != "package.update-notice"
        ):
            raise RuntimeError("Configuration notice is not executable")
        result = invoke({**context, "invocation": action})
        if result.get("effect_outcome", {}).get("status") != "committed":
            raise RuntimeError("Configuration notice publication needs recovery")
    except (OSError, RuntimeError, ValueError, KeyError, ImportError) as error:
        # Never prevent the user's Python command or guess an alternative write.
        print(f"AW update notice unavailable ({type(error).__name__}); use the configured AW start entry for recovery.", file=sys.stderr)
