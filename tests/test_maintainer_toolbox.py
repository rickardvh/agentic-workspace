from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_required_maintainer_skills_are_current_and_outside_packages() -> None:
    names = {path.parent.name for path in (ROOT / "tools/skills").glob("*/SKILL.md")}
    assert names == {
        "pr-review-recheck",
        "github-issue-shaping",
        "github-issue-creation",
        "self-improvement-dogfooding",
    }
    text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "tools/skills").glob("*/SKILL.md"))
    for removed in (
        "agentic-workspace report",
        "agentic-workspace reconcile",
        "agentic-workspace proof",
        "external-intent refresh",
    ):
        assert removed not in text


def test_minimal_model_evaluation_runs_and_reports_provider_availability() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools/model-evaluation/run.py"), "--root", str(ROOT)],
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(completed.stdout)
    assert all(item["passed"] for item in report["results"])
    assert report["provider_availability"] == {
        "provider": None,
        "available": False,
        "source": "explicit local environment",
    }
