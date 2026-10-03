from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "src" / "tooling" / "github" / "release_recovery_status.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("release_recovery_status", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "path", ["docs/maintenance.md", ".github/workflows/ci.yml", "src/tooling/release/pr_semver_admission.py", "src/cli/typescript/cli.mjs"]
)
def test_explicit_none_reports_no_release_regardless_of_paths(path: str) -> None:
    module = _load_module()
    ownership = json.loads((REPO_ROOT / ".github" / "release-ownership.json").read_text(encoding="utf-8"))

    packet = module.semver_pr_status(
        labels=["semver:none"],
        changed_files=[path],
        ownership=ownership,
    )

    assert packet["status"] == "no-release-needed"
    assert packet["requested_bump"] is None
    assert packet["release_requested"] is False
    assert packet["will_publish_release"] is False
    assert packet["will_prepare_release_pr"] is False


@pytest.mark.parametrize(
    "path", ["docs/maintenance.md", ".github/workflows/ci.yml", "src/tooling/release/pr_semver_admission.py", "src/cli/typescript/cli.mjs"]
)
def test_every_pr_requires_an_explicit_decision(path: str) -> None:
    module = _load_module()
    ownership = json.loads((REPO_ROOT / ".github" / "release-ownership.json").read_text(encoding="utf-8"))

    packet = module.semver_pr_status(
        labels=[],
        changed_files=[path, path],
        ownership=ownership,
    )

    assert packet["status"] == "blocked-semver-label-selection"
    assert "package_affecting" not in packet
    assert "path_classification" not in packet


def test_none_cannot_coexist_with_a_release_fragment() -> None:
    module = _load_module()
    ownership = json.loads((REPO_ROOT / ".github" / "release-ownership.json").read_text(encoding="utf-8"))

    packet = module.semver_pr_status(labels=["semver:none"], changed_files=[".release/changes/new.toml"], ownership=ownership)

    assert packet["status"] == "blocked-release-intent"
    assert packet["release_requested"] is False


def test_multiple_decisions_are_blocked() -> None:
    module = _load_module()
    ownership = json.loads((REPO_ROOT / ".github" / "release-ownership.json").read_text(encoding="utf-8"))

    packet = module.semver_pr_status(
        labels=["semver:none", "semver:patch"],
        changed_files=[
            "docs/maintenance.md",
            "src/cli/typescript/cli.mjs",
        ],
        ownership=ownership,
    )

    assert packet["status"] == "blocked-semver-label-selection"
    assert packet["requested_bump"] is None


@pytest.mark.parametrize("bump", ["patch", "minor", "major"])
def test_release_bearing_decision_requires_release_changeset(bump: str) -> None:
    module = _load_module()
    ownership = json.loads((REPO_ROOT / ".github" / "release-ownership.json").read_text(encoding="utf-8"))

    packet = module.semver_pr_status(
        labels=[f"semver:{bump}"],
        changed_files=["docs/maintenance.md"],
        ownership=ownership,
    )

    assert packet["status"] == "blocked-release-changeset"
    assert packet["requested_bump"] == bump
    assert packet["release_requested"] is True
    assert packet["will_publish_release"] is False
    assert packet["will_prepare_release_pr"] is False
    assert "release changeset" in packet["next_action"]


@pytest.mark.parametrize("bump", ["patch", "minor", "major"])
def test_release_bearing_pr_with_changeset_is_ready_for_manual_release(bump: str) -> None:
    module = _load_module()
    ownership = json.loads((REPO_ROOT / ".github" / "release-ownership.json").read_text(encoding="utf-8"))

    packet = module.semver_pr_status(
        labels=[f"semver:{bump}"],
        changed_files=[
            "docs/maintenance.md",
            ".release/changes/runtime.toml",
        ],
        ownership=ownership,
    )

    assert packet["status"] == "ready-for-manual-release"
    assert packet["requested_bump"] == bump
    assert packet["will_publish_release"] is False
    assert packet["will_prepare_release_pr"] is False


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
            "semver:none",
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
    assert packet["semver_release_action"]["status"] == "no-release-needed"
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
        changed_files=["pyproject.toml", ".release/changes/fix.toml"],
        release_failure=failure,
    )

    assert failure["freshness"]["status"] == "superseded_by_newer_success"
    assert failure["freshness"]["superseding_success"]["run_url"] == "https://github.com/example/repo/actions/runs/202"
    assert packet["release_publication_state"]["status"] == "cleared-by-newer-success"
    assert packet["coordinated_recovery"]["status"] == "not-required"


def test_successful_release_run_does_not_clear_version_publication_debt() -> None:
    module = _load_module()

    packet = module.recovery_packet(
        repo_root=REPO_ROOT,
        labels=[],
        changed_files=[],
        release_failure={
            "kind": "agentic-workspace/release-ci-failure-summary/v1",
            "status": "no-failed-release-run",
            "workflow": "Release",
            "latest_run": {
                "run_id": "29765337976",
                "run_url": "https://github.com/example/repo/actions/runs/29765337976",
                "conclusion": "success",
            },
            "freshness": {"status": "clear", "source": "gh-run-list"},
        },
        release_publication={
            "kind": "agentic-workspace/release-publication-state/v1",
            "status": "unresolved-version-publication-debt",
            "recovery_required": True,
            "reason": "version-not-newer-than-existing-tag-floor-v0.34.0",
            "version": "0.33.9",
            "tag": "v0.33.9",
        },
    )

    assert packet["release_publication_state"]["status"] == "unresolved-version-publication-debt"
    assert packet["release_publication_state"]["publication_status"] == "unresolved-version-publication-debt"
    assert packet["coordinated_recovery"]["status"] == "required"


@pytest.mark.parametrize("partial", [[], ["v1.7.0"]])
def test_remote_completion_is_distinct_from_reserved_versions(monkeypatch, partial):
    module = _load_module()
    observation = {
        "completed": {"tag": "v1.6.0", "source_commit": "a" * 40, "version": "1.6.0"},
        "partial": partial,
        "reserved": ["1.6.0", "1.7.0"],
    }
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, json.dumps(observation), ""))
    packet = module.release_publication_status(repo_root=REPO_ROOT, repo="example/repo")
    assert packet["tag"] == "v1.6.0"
    assert packet["recovery_required"] is bool(partial)
    assert packet["status"] == ("partial-publication" if partial else "published")
    if partial:
        assert 'tag="v1.7.0"' in packet["next_action"]


def test_remote_observation_failure_does_not_infer_free_version(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        module.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "", "unknown registry state")
    )
    packet = module.release_publication_status(repo_root=REPO_ROOT, repo="example/repo")
    assert packet["status"] == "publication-observation-failed"
    assert packet["recovery_required"] is True


@pytest.mark.parametrize("status", ["publication-observation-failed", "github-release-unpublished"])
def test_recovery_packet_requires_fail_closed_publication_repair(status: str) -> None:
    module = _load_module()

    packet = module.recovery_packet(
        repo_root=REPO_ROOT,
        labels=[],
        changed_files=[],
        release_publication={"status": status, "recovery_required": True, "next_action": "inspect publication"},
    )

    assert packet["release_publication_state"]["status"] == status
    assert packet["coordinated_recovery"]["status"] == "required"


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
            "command": 'gh workflow run release.yml --ref master -f tag="v0.34.1"',
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
    assert packet["coordinated_recovery"]["next_action"] == ('gh workflow run release.yml --ref master -f tag="v0.34.1"')


@pytest.mark.parametrize(
    "identity,tag_source",
    [
        (None, None),
        ({}, None),
        ({"tag": "v1.7.0", "source_commit": "abc"}, None),
        ({"tag": "v1.7.0", "source_commit": "abc"}, "other"),
        ({"tag": "v1.7.0", "source_commit": "abc"}, "abc"),
    ],
)
def test_recovery_routes_follow_run_and_observed_tag(tmp_path, monkeypatch, identity, tag_source):
    module = _load_module()
    monkeypatch.setattr(module, "_ownership_payload", lambda root: module._load_json(REPO_ROOT / ".github/release-ownership.json"))
    if identity is not None:
        (tmp_path / "release-identity.json").write_text(json.dumps(identity))
    monkeypatch.setattr(
        module.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0 if tag_source else 1, tag_source or "", "")
    )
    recovery = module.recovery_packet(
        repo_root=tmp_path,
        labels=[],
        changed_files=[],
        release_failure={"status": "failed-release-run", "run_id": "301"},
    )["coordinated_recovery"]
    assert "pr_shape" not in recovery
    if tag_source == "abc":
        assert recovery["route"] == "existing-tag"
        assert recovery["next_action"] == 'gh workflow run release.yml --ref master -f tag="v1.7.0"'
    else:
        assert recovery["route"] == "rerun-failed-jobs"
        assert "Re-run failed jobs" in recovery["next_action"]
        assert "301" in recovery["next_action"]


def test_missing_fragment_routes_to_pr_release_decision():
    module = _load_module()
    recovery = module.recovery_packet(repo_root=REPO_ROOT, labels=["semver:patch"], changed_files=["docs/reviews/repair.md"])[
        "coordinated_recovery"
    ]
    assert recovery["route"] == "pr-release-decision"
    assert "changeset" in recovery["next_action"]
    assert "pr_shape" not in recovery


def test_live_inputs_ignore_consumed_deletions_and_unchanged_fragment_renames(monkeypatch):
    module = _load_module()

    def fake_gh_json(args):
        if args == ["pr", "view", "12", "--repo", "example/repo", "--json", "labels"]:
            return {"labels": [{"name": "semver:none"}]}
        assert args == ["api", "repos/example/repo/pulls/12/files", "--paginate", "--slurp"]
        return [
            [
                {"filename": ".release/changes/consumed.toml", "status": "removed"},
                {
                    "filename": ".release/changes/renamed.toml",
                    "previous_filename": ".release/changes/original.toml",
                    "status": "renamed",
                    "additions": 0,
                    "deletions": 0,
                },
                {"filename": "docs/release.md", "status": "modified"},
            ],
            [
                {"filename": ".release/changes/modified.toml", "status": "modified"},
                {
                    "filename": ".release/changes/moved.toml",
                    "previous_filename": "elsewhere.toml",
                    "status": "renamed",
                    "additions": 0,
                    "deletions": 0,
                },
            ],
        ]

    monkeypatch.setattr(module, "_run_gh_json", fake_gh_json)
    labels, files = module._live_pr_inputs("example/repo", 12, changeset_dir=".release/changes")
    assert labels == ["semver:none"]
    assert files == ["docs/release.md", ".release/changes/modified.toml", ".release/changes/moved.toml"]
