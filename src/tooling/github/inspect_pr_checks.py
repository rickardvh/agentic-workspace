"""Inspect PR checks with compact failure summaries and attach-delay handling."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from typing import Any

ERROR_MARKERS = ("error", "failed", "failure", "traceback", "exception", "assertionerror")


def compact_check_summary(checks: list[dict[str, Any]]) -> dict[str, Any]:
    if not checks:
        return {
            "state": "pending_attach",
            "summary": "No checks are attached yet; retry before treating this as success or failure.",
            "failing": [],
        }
    failing = []
    for check in checks:
        state = str(check.get("state") or check.get("conclusion") or "").lower()
        if state not in {"fail", "failure", "failed", "error", "cancelled", "timed_out", "action_required"}:
            continue
        failing.append(
            {
                "name": str(check.get("name", "")),
                "state": state,
                "workflow": str(check.get("workflowName", check.get("workflow", ""))),
                "url": str(check.get("link", check.get("url", ""))),
                "local_reproduction": infer_local_reproduction(str(check.get("name", ""))),
            }
        )
    return {
        "state": "failed" if failing else "passed-or-pending",
        "summary": "Compact failing-check summary; use --verbose with gh logs for full snippets.",
        "failing": failing,
    }


def infer_local_reproduction(name: str) -> str:
    lowered = name.lower()
    if "planning" in lowered:
        return "make check-planning"
    if "memory" in lowered:
        return "make check-memory"
    if "workspace" in lowered:
        return "make test-workspace && make lint-workspace"
    return ""


def extract_error_lines(log_text: str, *, limit: int = 20) -> list[str]:
    lines = []
    for line in log_text.splitlines():
        lowered = line.lower()
        if any(marker in lowered for marker in ERROR_MARKERS):
            lines.append(line.strip())
        if len(lines) >= limit:
            break
    return lines


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", check=False)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or f"gh exited {result.returncode}")
    return json.loads(result.stdout or "[]")


def inspect_pr(pr: str, *, retries: int, interval: float) -> dict[str, Any]:
    last_summary: dict[str, Any] = {}
    for attempt in range(retries + 1):
        checks = run_gh_json(["pr", "checks", pr, "--json", "name,state,workflowName,link"])
        if not isinstance(checks, list):
            checks = []
        last_summary = compact_check_summary(checks)
        last_summary["attempt"] = attempt + 1
        if last_summary["state"] != "pending_attach":
            return last_summary
        if attempt < retries:
            time.sleep(interval)
    return last_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect PR checks with compact failure output.")
    parser.add_argument("pr", help="PR number, branch, or URL accepted by gh pr checks.")
    parser.add_argument("--retries", type=int, default=6)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args(argv)
    print(json.dumps(inspect_pr(args.pr, retries=args.retries, interval=args.interval), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
