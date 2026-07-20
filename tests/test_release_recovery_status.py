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
    assert packet["will_prepare_release_pr"] is False
    assert "will not open a release PR" in packet["next_action"]


def test_package_affecting_semver_pr_requires_release_changeset() -> None:
    module = _load_module()
    ownership = json.loads((REPO_ROOT / ".github" / "release-ownership.json").read_text(encoding="utf-8"))

    packet = module.semver_pr_status(
        labels=["semver:patch"],
        changed_files=["src/agentic_workspace/workspace_runtime.py"],
        ownership=ownership,
    )

    assert packet["status"] == "blocked-release-changeset"
    assert packet["will_publish_release"] is False
    assert packet["will_prepare_release_pr"] is False
    assert "release changeset" in packet["next_action"]


def test_package_affecting_semver_pr_with_changeset_opens_release_pr() -> None:
    module = _load_module()
    ownership = json.loads((REPO_ROOT / ".github" / "release-ownership.json").read_text(encoding="utf-8"))

    packet = module.semver_pr_status(
        labels=["semver:patch"],
        changed_files=[
            "src/agentic_workspace/workspace_runtime.py",
            ".release/changes/runtime.toml",
        ],
        ownership=ownership,
    )

    assert packet["status"] == "will-open-release-pr"
    assert packet["will_publish_release"] is False
    assert packet["will_prepare_release_pr"] is True


def test_release_failure_fixture_identifies_failed_job_step_and_error() -> None:
    module = _load_module()
    packet = module.release_failure_status(
        {
            "run": {
                "workflowName": "Release",
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
    assert packet["workflow"] == "Release"
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
                    "workflowName": "Release",
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


def test_live_release_failure_status_identifies_active_failed_run(monkeypatch) -> None:
    module = _load_module()

    def fake_gh_json(args: list[str]):
        if args[:2] == ["run", "list"]:
            return [
                {
                    "databaseId": 101,
                    "url": "https://github.com/example/repo/actions/runs/101",
                    "conclusion": "failure",
                    "updatedAt": "2026-06-28T10:00:00Z",
                    "workflowName": "Release",
                    "headBranch": "v0.34.1",
                    "headSha": "abc123",
                }
            ]
        if args[:2] == ["run", "view"]:
            return {
                "databaseId": 101,
                "url": "https://github.com/example/repo/actions/runs/101",
                "workflowName": "Release",
                "updatedAt": "2026-06-28T10:00:00Z",
                "jobs": [
                    {
                        "name": "release",
                        "conclusion": "failure",
                        "steps": [{"name": "Run proof", "conclusion": "failure"}],
                    }
                ],
            }
        raise AssertionError(args)

    monkeypatch.setattr(module, "_run_gh_json", fake_gh_json)
    monkeypatch.setattr(module, "_run_gh_text", lambda args, allow_failure=False: "AssertionError: release proof failed")

    packet = module.live_release_failure_status(repo="example/repo")

    assert packet["status"] == "failed-release-run"
    assert packet["run_url"] == "https://github.com/example/repo/actions/runs/101"
    assert packet["failed_job"] == "release"
    assert packet["failed_step"] == "Run proof"
    assert packet["freshness"]["status"] == "active_failed_release"
    assert packet["error_summary"] == ["AssertionError: release proof failed"]


def test_recovery_packet_marks_failed_release_superseded_by_newer_success(monkeypatch) -> None:
    module = _load_module()

    def fake_gh_json(args: list[str]):
        if args[:2] == ["run", "list"]:
            return [
                {
                    "databaseId": 202,
                    "url": "https://github.com/example/repo/actions/runs/202",
                    "conclusion": "success",
                    "updatedAt": "2026-06-28T11:00:00Z",
                    "workflowName": "Release",
                },
                {
                    "databaseId": 201,
                    "url": "https://github.com/example/repo/actions/runs/201",
                    "conclusion": "failure",
                    "updatedAt": "2026-06-28T10:00:00Z",
                    "workflowName": "Release",
                },
            ]
        if args[:2] == ["run", "view"]:
            return {
                "databaseId": 201,
                "url": "https://github.com/example/repo/actions/runs/201",
                "workflowName": "Release",
                "updatedAt": "2026-06-28T10:00:00Z",
                "jobs": [{"name": "release", "conclusion": "failure", "steps": []}],
            }
        raise AssertionError(args)

    monkeypatch.setattr(module, "_run_gh_json", fake_gh_json)
    monkeypatch.setattr(module, "_run_gh_text", lambda args, allow_failure=False: "ERROR old failure")

    failure = module.live_release_failure_status(repo="example/repo")
    packet = module.recovery_packet(
        repo_root=REPO_ROOT,
        labels=["semver:patch"],
        changed_files=["packages/agentic-workspace/pyproject.toml"],
        release_failure=failure,
    )

    assert failure["freshness"]["status"] == "superseded_by_newer_success"
    assert failure["freshness"]["superseding_success"]["run_url"] == "https://github.com/example/repo/actions/runs/202"
    assert packet["release_publication_state"]["status"] == "cleared-by-newer-success"
    assert packet["coordinated_recovery"]["status"] == "not-required"


def test_failed_release_recovery_retries_existing_verified_tag(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(
        module,
        "local_publisher_retry_status",
        lambda *, repo_root: {
            "kind": "agentic-workspace/release-publisher-retry/v1",
            "status": "ready",
            "tag": "v0.34.1",
            "source_commit": "abc123",
            "command": 'gh workflow run release.yml --ref master -f tag="v0.34.1" -f source_commit="abc123"',
        },
    )

    packet = module.recovery_packet(
        repo_root=REPO_ROOT,
        labels=[],
        changed_files=[],
        release_failure={
            "kind": "agentic-workspace/release-ci-failure-summary/v1",
            "status": "failed-release-run",
            "workflow": "Release",
            "run_url": "https://github.com/example/repo/actions/runs/301",
            "freshness": {"status": "active_failed_release"},
        },
    )

    assert packet["release_publication_state"]["status"] == "failed-release-unpublished"
    assert packet["release_publication_state"]["publisher_retry"]["status"] == "ready"
    assert packet["coordinated_recovery"]["status"] == "required"
    assert packet["coordinated_recovery"]["next_action"] == (
        'gh workflow run release.yml --ref master -f tag="v0.34.1" -f source_commit="abc123"'
    )
