"""Fail closed when any required hosted claim failed, was cancelled or was skipped."""

import json
import os


def require_success(results):
    if not results:
        raise ValueError("Required CI claims are absent")
    failed = {name: result.get("result") for name, result in results.items() if result.get("result") != "success"}
    if failed:
        raise ValueError(f"Required CI claims failed or are absent: {failed}")


if __name__ == "__main__":
    results = json.loads(os.environ["RESULTS"])
    require_success(results)
