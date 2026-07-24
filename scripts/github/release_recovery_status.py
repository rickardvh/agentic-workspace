"""Build compact release recovery status packets for release PRs and release runs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKET_KIND = "agentic-workspace/release-recovery-status/v1"
DEFAULT_WORKFLOW = "Release"
ERROR_MARKERS = ("error", "failed", "failure", "traceback", "exception", "assertionerror")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ownership_payload(repo_root: Path) -> dict[str, Any]:
    return _load_json(repo_root / ".github" / "release-ownership.json")


def _path_matches(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        candidate = pattern.replace("\\", "/")
        if normalized == candidate or normalized.startswith(candidate):
            return True
    return False


def semver_pr_status(*, labels: list[str], changed_files: list[str], ownership: dict[str, Any]) -> dict[str, Any]:
    semver_labels = [label for label in labels if label in set(ownership.get("semver_labels", []))]
    package_affecting = any(_path_matches(path, list(ownership.get("package_affecting_paths", []))) for path in changed_files)
    changeset_dir = str(ownership.get("changeset_dir", ".release/changes")).rstrip("/")
    changesets = [path for path in changed_files if path.startswith(f"{changeset_dir}/") and path.endswith(".toml")]
    if not package_affecting:
        status = "repair-only-semver-pr" if semver_labels else "no-release-needed"
        return {
            "kind": "agentic-workspace/semver-pr-release-action/v1",
            "status": status,
            "will_publish_release": False,
            "will_prepare_release_pr": False,
            "package_affecting": False,
            "semver_labels": semver_labels,
            "changesets": changesets,
            "changed_file_count": len(changed_files),
            "next_action": (
                "This PR can repair release blockers, but merge will not open a release PR; add a changeset-backed package-affecting PR if publication is still needed."
                if semver_labels
                else "No release action is expected because no package-affecting paths changed."
            ),
        }
    if len(semver_labels) != 1:
        return {
            "kind": "agentic-workspace/semver-pr-release-action/v1",
            "status": "blocked-semver-label-selection",
            "will_publish_release": False,
            "will_prepare_release_pr": False,
            "package_affecting": True,
            "semver_labels": semver_labels,
            "changesets": changesets,
            "changed_file_count": len(changed_files),
            "next_action": "Apply exactly one semver label and add a matching release changeset before merge.",
        }
    if not changesets:
        return {
            "kind": "agentic-workspace/semver-pr-release-action/v1",
            "status": "blocked-release-changeset",
            "will_publish_release": False,
            "will_prepare_release_pr": False,
            "package_affecting": True,
            "semver_labels": semver_labels,
            "changesets": changesets,
            "changed_file_count": len(changed_files),
            "next_action": f"Add a release changeset under {changeset_dir}/ whose bump matches {semver_labels[0]}.",
        }
    return {
        "kind": "agentic-workspace/semver-pr-release-action/v1",
        "status": "will-open-release-pr",
        "will_publish_release": False,
        "will_prepare_release_pr": True,
        "package_affecting": True,
        "semver_labels": semver_labels,
        "changesets": changesets,
        "changed_file_count": len(changed_files),
        "next_action": "Merge will let the Prepare Coordinated Release workflow open or update a release PR from pending changesets.",
    }


def _publisher_retry_command(tag: str, source_commit: str) -> str:
    return f'gh workflow run release.yml --ref master -f tag="{tag}" -f source_commit="{source_commit}"'


def _local_tag_plan(*, repo_root: Path) -> dict[str, Any]:
    script = repo_root / "scripts" / "release" / "coordinated_release.py"
    if not script.exists():
        raise RuntimeError(f"{script} does not exist")
    result = subprocess.run(
        [sys.executable, str(script), "tag-plan"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip())
    try:
        plan = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"tag-plan did not return JSON: {exc}") from exc
    return plan if isinstance(plan, dict) else {}


def local_publisher_retry_status(*, repo_root: Path) -> dict[str, Any]:
    try:
        plan = _local_tag_plan(repo_root=repo_root)
    except RuntimeError as exc:
        return {
            "kind": "agentic-workspace/release-publisher-retry/v1",
            "status": "unavailable",
            "reason": str(exc),
        }
    tag = _text(plan.get("tag"))
    source_commit = _text(plan.get("release_commit"))
    if plan.get("tag_needed"):
        return {
            "kind": "agentic-workspace/release-publisher-retry/v1",
            "status": "tag-not-created",
            "tag": tag,
            "source_commit": source_commit,
            "reason": "The release tag is not present yet; rerun Prepare Coordinated Release before publisher dispatch.",
        }
    if not plan.get("publish_candidate") or not tag or not source_commit:
        return {
            "kind": "agentic-workspace/release-publisher-retry/v1",
            "status": "no-existing-publishable-tag",
            "tag": tag,
            "source_commit": source_commit,
            "reason": _text(plan.get("reason")) or "No existing verified release tag is ready for publisher retry.",
        }
    return {
        "kind": "agentic-workspace/release-publisher-retry/v1",
        "status": "ready",
        "tag": tag,
        "source_commit": source_commit,
        "command": _publisher_retry_command(tag, source_commit),
        "rule": "Retry publication for the existing verified tag; do not create another changeset release just to recover artifacts.",
    }


def release_publication_status(*, repo_root: Path, repo: str | None = None) -> dict[str, Any]:
    """Classify release publication from explicit version/tag/release state."""

    try:
        plan = _local_tag_plan(repo_root=repo_root)
    except RuntimeError as exc:
        return {
            "kind": "agentic-workspace/release-publication-state/v1",
            "status": "unavailable",
            "recovery_required": False,
            "reason": str(exc),
            "evidence": {"source": "local-tag-plan"},
        }
    tag = _text(plan.get("tag"))
    release_commit = _text(plan.get("release_commit"))
    reason = _text(plan.get("reason"))
    if reason == "pending-changesets-require-release-pr":
        return {
            "kind": "agentic-workspace/release-publication-state/v1",
            "status": "pending-release-pr",
            "recovery_required": False,
            "reason": reason,
            "evidence": {"source": "local-tag-plan", "tag_plan": plan},
        }
    if reason.startswith("version-not-newer-than-existing-tag-floor-"):
        return {
            "kind": "agentic-workspace/release-publication-state/v1",
            "status": "unresolved-version-publication-debt",
            "recovery_required": True,
            "reason": reason,
            "version": _text(plan.get("version")),
            "tag": tag,
            "release_commit": release_commit,
            "evidence": {
                "source": "local-tag-plan",
                "tag_plan": plan,
                "rule": "A successful release workflow run does not clear recovery when checked-in package versions are behind the tag floor.",
            },
        }
    if plan.get("tag_needed"):
        return {
            "kind": "agentic-workspace/release-publication-state/v1",
            "status": "verified-release-tag-missing",
            "recovery_required": True,
            "reason": "The coordinated release commit exists, but the matching release tag is missing.",
            "version": _text(plan.get("version")),
            "tag": tag,
            "release_commit": release_commit,
            "evidence": {"source": "local-tag-plan", "tag_plan": plan},
        }
    if not plan.get("publish_candidate") or not tag or not release_commit:
        return {
            "kind": "agentic-workspace/release-publication-state/v1",
            "status": "no-existing-publishable-tag",
            "recovery_required": False,
            "reason": reason or "No existing verified release tag is ready for publication.",
            "version": _text(plan.get("version")),
            "tag": tag,
            "release_commit": release_commit,
            "evidence": {"source": "local-tag-plan", "tag_plan": plan},
        }
    release_view: dict[str, Any] = {}
    if repo:
        try:
            release_view_payload = _run_gh_json(
                [
                    "release",
                    "view",
                    tag,
                    "--repo",
                    repo,
                    "--json",
                    "tagName,url,isDraft,isPrerelease,publishedAt",
                ]
            )
            release_view = release_view_payload if isinstance(release_view_payload, dict) else {}
        except SystemExit as exc:
            return {
                "kind": "agentic-workspace/release-publication-state/v1",
                "status": "github-release-missing",
                "recovery_required": True,
                "reason": str(exc) or f"GitHub Release {tag} is not visible.",
                "version": _text(plan.get("version")),
                "tag": tag,
                "release_commit": release_commit,
                "evidence": {
                    "source": "local-tag-plan + gh-release-view",
                    "tag_plan": plan,
                    "release_view": {},
                },
            }
    return {
        "kind": "agentic-workspace/release-publication-state/v1",
        "status": "published" if release_view else "verified-local-tag",
        "recovery_required": False,
        "reason": "Verified release tag and coordinated version commit agree."
        if not release_view
        else "Verified release tag, coordinated version commit, and GitHub Release are present.",
        "version": _text(plan.get("version")),
        "tag": tag,
        "release_commit": release_commit,
        "release_url": _text(release_view.get("url")) if release_view else "",
        "evidence": {
            "source": "local-tag-plan + gh-release-view" if release_view else "local-tag-plan",
            "tag_plan": plan,
            "release_view": release_view,
        },
    }


def _timestamp(value: Any) -> str:
    text = _text(value)
    if text:
        return text
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _error_lines(text: str, *, limit: int = 8) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if any(marker in lowered for marker in ERROR_MARKERS):
            lines.append(line.strip())
        if len(lines) >= limit:
            break
    return lines


def release_failure_status(payload: dict[str, Any]) -> dict[str, Any]:
    run = payload.get("run") if isinstance(payload.get("run"), dict) else payload
    jobs = run.get("jobs", []) if isinstance(run.get("jobs"), list) else payload.get("jobs", [])
    failed_job: dict[str, Any] | None = None
    failed_step: dict[str, Any] | None = None
    for job in jobs if isinstance(jobs, list) else []:
        if not isinstance(job, dict):
            continue
        conclusion = _text(job.get("conclusion") or job.get("status")).lower()
        steps = job.get("steps", []) if isinstance(job.get("steps"), list) else []
        step = next(
            (
                item
                for item in steps
                if isinstance(item, dict) and _text(item.get("conclusion") or item.get("status")).lower() in {"failure", "failed", "error"}
            ),
            None,
        )
        if conclusion in {"failure", "failed", "error", "cancelled", "timed_out"} or step is not None:
            failed_job = job
            failed_step = step if isinstance(step, dict) else None
            break
    status = "failed-release-run" if failed_job is not None else "no-failed-release-run"
    log_text = _text(payload.get("log") or run.get("log"))
    error_summary = _error_lines(log_text)
    return {
        "kind": "agentic-workspace/release-ci-failure-summary/v1",
        "status": status,
        "workflow": _text(run.get("workflowName") or run.get("workflow") or payload.get("workflow") or DEFAULT_WORKFLOW),
        "run_url": _text(run.get("url") or run.get("html_url") or payload.get("run_url")),
        "run_id": _text(run.get("databaseId") or run.get("id") or payload.get("run_id")),
        "failed_job": _text(failed_job.get("name") if failed_job else ""),
        "failed_step": _text(failed_step.get("name") if failed_step else ""),
        "error_summary": error_summary,
        "freshness": {
            "observed_at": _timestamp(payload.get("observed_at") or run.get("updatedAt") or run.get("updated_at")),
            "source": "fixture-or-gh-actions-run",
            "stale_when": "a newer release workflow run succeeds or supersedes this run",
        },
        "next_command": "gh run view <run-id> --log-failed",
    }


def _run_sort_key(run: dict[str, Any]) -> datetime:
    return _parse_timestamp(run.get("updatedAt") or run.get("updated_at") or run.get("createdAt") or run.get("created_at")) or datetime.min.replace(
        tzinfo=timezone.utc
    )


def _run_conclusion(run: dict[str, Any]) -> str:
    return _text(run.get("conclusion") or run.get("status")).lower()


def _run_identity(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": _text(run.get("databaseId") or run.get("id")),
        "run_url": _text(run.get("url") or run.get("html_url")),
        "head_branch": _text(run.get("headBranch") or run.get("head_branch")),
        "head_sha": _text(run.get("headSha") or run.get("head_sha")),
        "updated_at": _timestamp(run.get("updatedAt") or run.get("updated_at") or run.get("createdAt") or run.get("created_at")),
        "conclusion": _text(run.get("conclusion") or run.get("status")),
    }


def _run_gh_text(args: list[str], *, allow_failure: bool = False) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", check=False)
    if result.returncode != 0 and not allow_failure:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or f"gh exited {result.returncode}")
    return result.stdout if result.returncode == 0 else ""


def live_release_failure_status(*, repo: str, workflow: str = DEFAULT_WORKFLOW, limit: int = 10) -> dict[str, Any]:
    try:
        runs = _run_gh_json(
            [
                "run",
                "list",
                "--repo",
                repo,
                "--workflow",
                workflow,
                "--limit",
                str(limit),
                "--json",
                "databaseId,url,conclusion,status,updatedAt,createdAt,workflowName,headBranch,headSha,event",
            ]
        )
    except SystemExit as exc:
        return {
            "kind": "agentic-workspace/release-ci-failure-summary/v1",
            "status": "release_run_status_unavailable",
            "workflow": workflow,
            "reason": str(exc),
            "freshness": {"status": "unavailable", "source": "gh-run-list-failed"},
            "next_command": f"gh run list --repo {repo} --workflow {json.dumps(workflow)} --limit {limit}",
        }
    if not isinstance(runs, list):
        runs = []
    ordered_runs = sorted([run for run in runs if isinstance(run, dict)], key=_run_sort_key, reverse=True)
    failed_run = next((run for run in ordered_runs if _run_conclusion(run) in {"failure", "failed", "error", "timed_out"}), None)
    latest_success = next((run for run in ordered_runs if _run_conclusion(run) in {"success", "completed"}), None)
    if failed_run is None:
        return {
            "kind": "agentic-workspace/release-ci-failure-summary/v1",
            "status": "no-failed-release-run",
            "workflow": workflow,
            "latest_run": _run_identity(ordered_runs[0]) if ordered_runs else {},
            "freshness": {
                "status": "clear" if ordered_runs else "no-runs-found",
                "source": "gh-run-list",
                "observed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            },
            "next_command": f"gh run list --repo {repo} --workflow {json.dumps(workflow)} --limit {limit}",
        }
    failed_id = _text(failed_run.get("databaseId") or failed_run.get("id"))
    try:
        detail = _run_gh_json(["run", "view", failed_id, "--repo", repo, "--json", "jobs,url,databaseId,workflowName,updatedAt,headBranch,headSha"])
    except SystemExit:
        detail = dict(failed_run)
    log = _run_gh_text(["run", "view", failed_id, "--repo", repo, "--log-failed"], allow_failure=True)
    run_payload = dict(failed_run)
    if isinstance(detail, dict):
        run_payload.update(detail)
        if "jobs" not in run_payload and isinstance(detail.get("jobs"), list):
            run_payload["jobs"] = detail["jobs"]
    summary = release_failure_status({"run": run_payload, "log": log})
    failed_at = _run_sort_key(failed_run)
    superseding_success = None
    if latest_success is not None and _run_sort_key(latest_success) > failed_at:
        superseding_success = latest_success
    summary["freshness"] = {
        **summary.get("freshness", {}),
        "status": "superseded_by_newer_success" if superseding_success else "active_failed_release",
        "source": "gh-run-list + gh-run-view",
        "observed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "superseding_success": _run_identity(superseding_success) if superseding_success else {},
    }
    summary["next_command"] = f"gh run view {failed_id} --repo {repo} --log-failed"
    return summary


def recovery_packet(
    *,
    repo_root: Path,
    labels: list[str],
    changed_files: list[str],
    run_payload: dict[str, Any] | None = None,
    release_failure: dict[str, Any] | None = None,
    release_publication: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ownership = _ownership_payload(repo_root)
    semver = semver_pr_status(labels=labels, changed_files=changed_files, ownership=ownership)
    release_failure = release_failure or (
        release_failure_status(run_payload)
        if run_payload
        else {
            "kind": "agentic-workspace/release-ci-failure-summary/v1",
            "status": "not-fetched",
            "workflow": DEFAULT_WORKFLOW,
            "next_command": "gh run list --workflow 'Release' --limit 5",
            "freshness": {"status": "unavailable", "source": "not-fetched"},
        }
    )
    active_failed_release = (
        release_failure["status"] == "failed-release-run"
        and release_failure.get("freshness", {}).get("status") != "superseded_by_newer_success"
    )
    release_publication = release_publication or {}
    publication_recovery_required = bool(release_publication.get("recovery_required"))
    superseded_by_verified_publication = (
        release_failure.get("freshness", {}).get("status") == "superseded_by_newer_success" and not publication_recovery_required
    )
    recovery_needed = semver["status"] == "repair-only-semver-pr" or active_failed_release or publication_recovery_required
    publisher_retry = local_publisher_retry_status(repo_root=repo_root) if active_failed_release else {}
    version_paths = [package["pyproject"] for package in ownership.get("packages", []) if isinstance(package, dict)] + [
        package["package_json"] for package in ownership.get("typescript_packages", []) if isinstance(package, dict)
    ]
    publication_status = _text(release_publication.get("status")) if release_publication else "not-checked"
    publication_status_value = publication_status if publication_status != "not-checked" else ""
    return {
        "kind": PACKET_KIND,
        "semver_release_action": semver,
        "release_ci_failure": release_failure,
        "release_publication_state": {
            "status": "failed-release-unpublished"
            if active_failed_release
            else publication_status
            if publication_recovery_required
            else "repair-only-pr-does-not-publish"
            if semver["status"] == "repair-only-semver-pr"
            else "cleared-by-newer-success"
            if superseded_by_verified_publication
            else "no-active-failed-release",
            "failed_run_url": release_failure.get("run_url", ""),
            "superseding_run_url": release_failure.get("freshness", {}).get("superseding_success", {}).get("run_url", "")
            if isinstance(release_failure.get("freshness"), dict)
            else "",
            "release_action": semver["status"],
            "publication_status": publication_status_value,
            "publication": release_publication,
            "publisher_retry": publisher_retry,
            "rule": "Repair-only PRs can fix blockers but do not open a release PR; an active failed Release workflow should be retried for the existing verified tag unless a newer successful publisher run has verified publication state.",
        },
        "coordinated_recovery": {
            "status": "required" if recovery_needed else "not-required",
            "next_action": (
                publisher_retry["command"]
                if active_failed_release and publisher_retry.get("status") == "ready"
                else "Rerun Prepare Coordinated Release to create the verified release tag before dispatching the publisher."
                if active_failed_release
                else "Create or merge a package-affecting PR with a release changeset, then let the generated release PR carry the version bump."
                if semver["status"] == "repair-only-semver-pr"
                else "Repair release publication state; successful no-op workflow runs do not clear version/tag/release disagreement."
                if publication_recovery_required
                else "No failed-release recovery action is active in this packet."
            ),
            "pr_shape": {
                "required_paths": version_paths,
                "proof": [
                    "uv lock",
                    "make test-workspace",
                    "make lint-workspace",
                    "uv run pytest tests/test_release_workflows.py -q",
                ],
            },
        },
        "write_safety": {
            "github_writes_performed": False,
            "rule": "This packet is read-only; create recovery branches or labels separately and intentionally.",
        },
    }


def _run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", check=False)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or f"gh exited {result.returncode}")
    return json.loads(result.stdout or "[]")


def _live_pr_inputs(repo: str, pr: int) -> tuple[list[str], list[str]]:
    labels_payload = _run_gh_json(["pr", "view", str(pr), "--repo", repo, "--json", "labels,files"])
    labels = [item["name"] for item in labels_payload.get("labels", []) if isinstance(item, dict) and item.get("name")]
    files = [item["path"] for item in labels_payload.get("files", []) if isinstance(item, dict) and item.get("path")]
    return labels, files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--repo", help="GitHub repository in owner/name form for live PR reads.")
    parser.add_argument("--pr", type=int, help="Pull request number for live PR reads.")
    parser.add_argument("--include-release-runs", action="store_true", help="Fetch recent release workflow runs through gh.")
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW, help="Release workflow name for --include-release-runs.")
    parser.add_argument("--run-limit", type=int, default=10, help="Number of release workflow runs to inspect.")
    parser.add_argument("--labels", nargs="*", default=[], help="Semver and other labels for fixture mode.")
    parser.add_argument("--changed-file", action="append", default=[], help="Changed file path for fixture mode.")
    parser.add_argument("--run-fixture", type=Path, help="Optional failed release run fixture JSON.")
    parser.add_argument("--format", choices=("json",), default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if bool(args.repo) ^ bool(args.pr) and not (args.repo and args.include_release_runs):
        raise SystemExit("--repo and --pr must be supplied together unless --include-release-runs is used")
    labels, changed_files = (args.labels, args.changed_file)
    if args.repo and args.pr:
        labels, changed_files = _live_pr_inputs(args.repo, args.pr)
    run_payload = _load_json(args.run_fixture) if args.run_fixture else None
    release_failure = (
        live_release_failure_status(repo=args.repo, workflow=args.workflow, limit=args.run_limit)
        if args.repo and args.include_release_runs
        else None
    )
    release_publication = release_publication_status(repo_root=args.repo_root, repo=args.repo) if args.repo and args.include_release_runs else None
    packet = recovery_packet(
        repo_root=args.repo_root,
        labels=labels,
        changed_files=changed_files,
        run_payload=run_payload,
        release_failure=release_failure,
        release_publication=release_publication,
    )
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
