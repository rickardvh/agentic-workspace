from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from agentic_workspace.workspace import Workspace


def run(root: Path, provider: str | None) -> dict[str, object]:
    definition = json.loads((root / "tools/model-evaluation/scenarios.json").read_text(encoding="utf-8"))
    results = []
    with tempfile.TemporaryDirectory(prefix="aw-model-evaluation-") as temporary:
        for scenario in definition["scenarios"]:
            repository = Path(temporary) / scenario["id"]
            repository.mkdir(parents=True)
            decision = Workspace(repository).start(intent=scenario["intent"])
            results.append(
                {
                    "id": scenario["id"],
                    "expected_status": scenario["expected_status"],
                    "observed_status": decision["status"],
                    "passed": decision["status"] == scenario["expected_status"],
                }
            )
    availability = {
        "provider": provider,
        "available": bool(provider and os.environ.get("AW_EVALUATION_PROVIDER_AVAILABLE") == "1"),
        "source": "explicit local environment",
    }
    return {"kind": "agentic-workspace/model-evaluation/v1", "provider_availability": availability, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--provider")
    args = parser.parse_args()
    report = run(args.root.resolve(), args.provider)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(item["passed"] for item in report["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
