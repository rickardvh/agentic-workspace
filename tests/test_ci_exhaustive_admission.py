from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"
RULESET_PATH = ROOT / ".github" / "rulesets" / "master-support-bearing.json"


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

    aggregate = workflow.partition("  support-bearing-promotion:\n")[2]
    assert "needs: [workspace-checks, planning-handoff-checks, independent-owner-ingress, workspace-package-artifacts, package-checks, declared-runtime-matrix]" in aggregate
    assert "always() && github.event_name == 'workflow_dispatch'" in aggregate
    assert workflow.index("  exhaustive-admission:\n") < workflow.index("  workspace-checks:\n")


def test_pull_request_path_is_merge_sufficiency_only() -> None:
    workflow = CI_PATH.read_text(encoding="utf-8")
    merge = _job_block(workflow, "merge-sufficiency", "exhaustive-admission")

    assert "name: Merge sufficiency" in merge
    assert "pull_request" in workflow.partition("on:\n")[2].partition("permissions:\n")[0]
    assert "workflow_dispatch" in workflow.partition("on:\n")[2].partition("permissions:\n")[0]

    # Release-shaped work must stay behind explicit exact-head admission rather
    # than becoming an ambient requirement of every pull request.
    for release_only in (
        "uv build --wheel --sdist",
        "packed-artifact-conformance",
        "make check-memory-nosync",
        "make check-planning-nosync",
        "make check-verification-nosync",
        "Runtime ${{ matrix.os }}",
        "support-bearing-promotion",
    ):
        assert release_only not in merge

    # A broad workspace test is admissible only in the explicit exhaustive path,
    # not in the ordinary PR acceptance job.
    assert "cargo +stable test --workspace" not in merge
    assert "cargo +stable test --workspace" in workflow.partition("  workspace-checks:\n")[2]


def test_high_risk_or_release_claim_has_explicit_exact_head_escalation() -> None:
    workflow = CI_PATH.read_text(encoding="utf-8")
    dispatch = workflow.partition("workflow_dispatch:\n")[2].partition("permissions:\n")[0]
    admission = _job_block(workflow, "exhaustive-admission", "workspace-checks")

    assert "expected_head_sha:" in dispatch
    assert "reason:" in dispatch
    assert "required: true" in dispatch
    assert "github.event_name == 'workflow_dispatch'" in admission
    assert "${GITHUB_SHA}" in admission and "${EXPECTED_HEAD_SHA}" in admission
    assert "REASON" in admission


def test_master_ruleset_requires_merge_sufficiency_not_release_matrix() -> None:
    import json

    ruleset = json.loads(RULESET_PATH.read_text(encoding="utf-8"))
    checks = next(
        rule["parameters"]["required_status_checks"]
        for rule in ruleset["rules"]
        if rule["type"] == "required_status_checks"
    )
    contexts = {check["context"] for check in checks}

    assert "Merge sufficiency" in contexts
    assert "Review approval" in contexts
    assert "Support-bearing promotion" not in contexts
    assert not any(context.startswith("Runtime ") for context in contexts)
    assert not any("package" in context.lower() for context in contexts)
