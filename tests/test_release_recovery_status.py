from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "github" / "release_recovery_status.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("release_recovery_status", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_semver_repair_only_pr_reports_that_it_will_not_publish() -> None:
    module = _load_module()
    ownership = json.loads((REPO_ROOT / ".github" / "release-ownership.json").read_text(encoding="utf-8"))

    packet = module.semver_pr_status(
        labels=["semver:patch"],
        changed_files=["docs/reviews/release-repair-note.md"],
        ownership=ownership,
    )

    assert packet["status"] == "repair-only-semver-pr"
    assert packet["will_publish_release"] is False
    assert "will not publish" in packet["next_action"]


def test_release_failure_fixture_identifies_failed_job_step_and_error() -> None:
    module = _load_module()
    packet = module.release_failure_status(
        {
            "run": {
                "workflowName": "Release From Semver Label",
                "databaseId": 28300736651,
                "url": "https://github.com/example/repo/actions/runs/28300736651",
                "updatedAt": "2026-06-28T10:00:00Z",
                "jobs": [
                    {
                        "name": "release-from-label",
                        "conclusion": "failure",
                        "steps": [
                            {"name": "Run coordinated release proof", "conclusion": "failure"},
                        ],
                    }
                ],
            },
            "log": "ok\nERROR tests/test_external_agent_evaluation_lane.py::test_model_cli_harness failed\n",
        }
    )

    assert packet["status"] == "failed-release-run"
    assert packet["workflow"] == "Release From Semver Label"
    assert packet["failed_job"] == "release-from-label"
    assert packet["failed_step"] == "Run coordinated release proof"
    assert packet["error_summary"] == ["ERROR tests/test_external_agent_evaluation_lane.py::test_model_cli_harness failed"]
    assert packet["next_command"] == "gh run view <run-id> --log-failed"


def test_release_recovery_cli_reads_fixture_inputs(tmp_path: Path) -> None:
    fixture = tmp_path / "run.json"
    fixture.write_text(
        json.dumps(
            {
                "run": {
                    "workflowName": "Release From Semver Label",
                    "url": "https://github.com/example/repo/actions/runs/1",
                    "jobs": [{"name": "release", "conclusion": "failure", "steps": []}],
                },
                "log": "AssertionError: release proof failed",
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(REPO_ROOT),
            "--labels",
            "semver:patch",
            "--changed-file",
            "docs/reviews/release-repair-note.md",
            "--run-fixture",
            str(fixture),
            "--format",
            "json",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert packet["kind"] == "agentic-workspace/release-recovery-status/v1"
    assert packet["semver_release_action"]["status"] == "repair-only-semver-pr"
    assert packet["release_ci_failure"]["status"] == "failed-release-run"
    assert packet["coordinated_recovery"]["status"] == "required"
