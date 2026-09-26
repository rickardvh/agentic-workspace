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
    if os.environ.get("SOURCE_RUN_ID"):
        # The dominating admission job verifies exact source proof and normalization.
        require_success({"exhaustive-admission": results.get("exhaustive-admission", {})})
        for reused in ("workspace-checks", "planning-handoff-checks", "independent-owner-ingress"):
            result = results.pop(reused, {})
            if result.get("result") != "skipped":
                raise ValueError(f"Unexpected candidate source-proof disposition: {reused}")
    require_success(results)
