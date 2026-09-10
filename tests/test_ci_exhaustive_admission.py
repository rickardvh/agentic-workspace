from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"


def _job_block(workflow: str, name: str, next_name: str) -> str:
    return workflow.partition(f"  {name}:\n")[2].partition(f"\n  {next_name}:\n")[0]


def test_exhaustive_dispatch_is_admitted_before_broad_runner_fanout() -> None:
    workflow = CI_PATH.read_text(encoding="utf-8")
    admission = _job_block(workflow, "exhaustive-admission", "workspace-checks")

    assert "name: Exhaustive admission" in admission
    assert "if: github.event_name == 'workflow_dispatch'" in admission
    assert "timeout-minutes: 2" in admission
    assert "Verify dispatched release head" in admission
    assert "${{ inputs.expected_head_sha }}" in admission
    assert "${{ inputs.reason }}" in admission
    assert '"${GITHUB_SHA}" != "${EXPECTED_HEAD_SHA}"' in admission
    assert "requires a non-empty reason" in admission

    job_pairs = (
        ("workspace-checks", "planning-handoff-checks"),
        ("planning-handoff-checks", "independent-owner-ingress"),
        ("independent-owner-ingress", "workspace-package-artifacts"),
        ("workspace-package-artifacts", "package-checks"),
        ("package-checks", "declared-runtime-matrix"),
        ("declared-runtime-matrix", "support-bearing-promotion"),
    )
    for name, next_name in job_pairs:
        block = _job_block(workflow, name, next_name)
        assert "needs: exhaustive-admission" in block
        assert "if: ${{ github.event_name == 'workflow_dispatch' }}" in block
        assert "Verify dispatched release head" not in block

    assert workflow.index("  exhaustive-admission:\n") < workflow.index("  workspace-checks:\n")
