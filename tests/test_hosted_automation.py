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


def test_label_changes_only_revalidate_the_semver_claim():
    workflows = [workflow(p.name) for p in (ROOT / ".github/workflows").glob("*.yml")]
    handlers = [w for w in workflows if "labeled" in (w["on"].get("pull_request") or {}).get("types", [])]
    assert handlers
    for handler in handlers:
        commands = [s.get("run", "") for j in handler["jobs"].values() for s in j.get("steps", [])]
        assert any("pr_semver_admission.py" in command for command in commands)
        assert all("cargo " not in command and "pytest " not in command for command in commands)
        assert all("uses" not in job for job in handler["jobs"].values())
    ci = workflow("ci.yml")
    assert not {"labeled", "unlabeled"} & set(ci["on"]["pull_request"]["types"])
    readiness = ci["jobs"]["readiness"]
    assert readiness["name"] == "Merge sufficiency"
    assert "security" in readiness["needs"]
    assert "always()" in readiness["if"]
    assert "current_install.py" not in str(ci)


def test_security_and_consumers_keep_their_schedule_and_permission_boundaries():
    ci = workflow("ci.yml")
    security = workflow(Path(ci["jobs"]["security"]["uses"]).name)
    assert "continue-on-error" not in str(security)
    assert "check_rust_dependencies.py" in str(security)
    assert "codeql-action/analyze@" in str(security)
    maintenance = workflow("maintenance.yml")
    assert maintenance["on"]["schedule"]
    projection = [s for j in maintenance["jobs"].values() for s in j.get("steps", []) if "current_install.py" in s.get("run", "")]
    assert len(projection) == 1 and "--observe" in projection[0]["run"]
    assert "continue-on-error" not in projection[0]


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
