"""Fail closed when any required hosted claim failed, was cancelled or was skipped."""

import json
import os


def require_success(results, *, windows_mode_scope=None):
    if not results:
        raise ValueError("Required CI claims are absent")
    if windows_mode_scope is not None and windows_mode_scope not in {"required", "unrelated"}:
        raise ValueError("Exact Windows proof applicability is absent")
    if windows_mode_scope is not None and "proof-modes-windows" not in results:
        raise ValueError("Windows proof result is absent")
    failed = {
        name: result.get("result")
        for name, result in results.items()
        if result.get("result") != "success"
        and not (name == "proof-modes-windows" and windows_mode_scope == "unrelated" and result.get("result") == "skipped")
    }
    if failed:
        raise ValueError(f"Required CI claims failed or are absent: {failed}")


if __name__ == "__main__":
    results = json.loads(os.environ["RESULTS"])
    require_success(results, windows_mode_scope=os.environ.get("WINDOWS_MODE_SCOPE"))
