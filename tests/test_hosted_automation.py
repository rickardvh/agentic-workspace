"""The hosted entrypoints preserve admission while contracting orchestration."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    return yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)


def test_ci_admission_requires_semver_merge_and_blocking_security():
    ci = workflow("ci.yml")
    assert {"labeled", "unlabeled"} <= set(ci["on"]["pull_request"]["types"])
    readiness = ci["jobs"]["readiness"]
    assert readiness["name"] == "Merge sufficiency"
    assert set(readiness["needs"]) == {"merge-sufficiency", "security", "current-public-install"}
    assert "always()" in readiness["if"]
    assert ci["jobs"]["security"]["uses"] == "./.github/workflows/security.yml"
    steps = ci["jobs"]["merge-sufficiency"]["steps"]
    admission = next(step for step in steps if step.get("name") == "Validate semver label")
    assert admission["run"] == "python src/tooling/release/pr_semver_admission.py"
    assert admission["if"] == "github.event_name == 'pull_request'"
    assert not (ROOT / ".github/workflows/pr-semver-label.yml").exists()


def test_security_and_consumers_keep_their_schedule_and_permission_boundaries():
    security = workflow("security.yml")
    assert set(security["on"]) == {"workflow_call"}
    assert set(security["jobs"]) == {"baseline", "codeql"}
    assert security["jobs"]["codeql"]["permissions"]["security-events"] == "write"
    assert security["jobs"]["baseline"]["permissions"] == {"contents": "read", "pull-requests": "read"}
    maintenance = workflow("maintenance.yml")
    assert {row["cron"] for row in maintenance["on"]["schedule"]} == {"23 7 * * *", "17 4 * * 1"}
    assert "17 4 * * 1" in maintenance["jobs"]["security"]["if"]
    assert "!= '17 4 * * 1'" in maintenance["jobs"]["freeze"]["if"]
    assert not (ROOT / ".github/workflows/consumer-validation.yml").exists()


@pytest.mark.parametrize("status", ["success", "failure", "skipped", "cancelled"])
def test_required_ci_status_cannot_hide_missing_or_failed_claims(status):
    import json

    result = subprocess.run(
        [sys.executable, str(ROOT / "src/tooling/check/check_ci_results.py")],
        env={**os.environ, "SOURCE_RUN_ID": "", "RESULTS": json.dumps({"security": {"result": status}})},
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) is (status == "success")


@pytest.mark.parametrize("admission", ["success", "failure", "skipped"])
def test_candidate_summary_reuses_source_claims_only_after_admission(admission):
    import json

    results = {name: {"result": "skipped"} for name in ("workspace-checks", "planning-handoff-checks", "independent-owner-ingress")}
    results.update(
        {
            "exhaustive-admission": {"result": admission},
            "workspace-package-artifacts": {"result": "success"},
            "declared-runtime-matrix": {"result": "success"},
        }
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "src/tooling/check/check_ci_results.py")],
        env={**os.environ, "SOURCE_RUN_ID": "7", "RESULTS": json.dumps(results)},
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) is (admission == "success")
