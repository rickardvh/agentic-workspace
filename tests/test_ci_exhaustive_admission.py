"""The explicit exhaustive gate dominates all broad CI jobs."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_exhaustive_admission_is_single_gate_for_broad_runner_fanout():
    workflow = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    broad = (
        "workspace-checks",
        "planning-handoff-checks",
        "independent-owner-ingress",
        "workspace-package-artifacts",
        "declared-runtime-matrix",
    )
    assert jobs["exhaustive-admission"]["timeout-minutes"] == "2"
    for name in broad:
        needs = jobs[name]["needs"]
        assert "exhaustive-admission" in ([needs] if isinstance(needs, str) else needs)
        assert "github.event_name == 'workflow_dispatch'" in jobs[name]["if"]
        if name in {"workspace-checks", "planning-handoff-checks", "declared-runtime-matrix"}:
            assert "workspace-package-artifacts" in needs
            assert any(step.get("with", {}).get("name") == "agentic-workspace-package-artifacts" for step in jobs[name]["steps"])
