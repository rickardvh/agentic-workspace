"""Build compact release recovery status packets for semver PRs and release runs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKET_KIND = "agentic-workspace/release-recovery-status/v1"
DEFAULT_WORKFLOW = "Release From Semver Label"
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
    if not package_affecting:
        status = "repair-only-semver-pr" if semver_labels else "no-release-needed"
        return {
            "kind": "agentic-workspace/semver-pr-release-action/v1",
            "status": status,
            "will_publish_release": False,
            "package_affecting": False,
            "semver_labels": semver_labels,
            "changed_file_count": len(changed_files),
            "next_action": (
                "This PR can repair release blockers, but merge will not publish a release; follow with a coordinated explicit version bump if a failed release still needs publication."
                if semver_labels
                else "No release action is expected because no package-affecting paths changed."
            ),
        }
    if len(semver_labels) != 1:
        return {
            "kind": "agentic-workspace/semver-pr-release-action/v1",
            "status": "blocked-semver-label-selection",
            "will_publish_release": False,
            "package_affecting": True,
            "semver_labels": semver_labels,
            "changed_file_count": len(changed_files),
            "next_action": "Apply exactly one semver label before merge so the release workflow can compute the coordinated version.",
        }
    return {
        "kind": "agentic-workspace/semver-pr-release-action/v1",
        "status": "will-publish-release",
        "will_publish_release": True,
        "package_affecting": True,
        "semver_labels": semver_labels,
        "changed_file_count": len(changed_files),
        "next_action": "Merge will attempt a coordinated release bump through the Release From Semver Label workflow.",
    }


def _timestamp(value: Any) -> str:
    text = _text(value)
    if text:
        return text
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def recovery_packet(
    *,
    repo_root: Path,
    labels: list[str],
    changed_files: list[str],
    run_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ownership = _ownership_payload(repo_root)
    semver = semver_pr_status(labels=labels, changed_files=changed_files, ownership=ownership)
    release_failure = release_failure_status(run_payload) if run_payload else {
        "kind": "agentic-workspace/release-ci-failure-summary/v1",
        "status": "not-fetched",
        "workflow": DEFAULT_WORKFLOW,
        "next_command": "gh run list --workflow 'Release From Semver Label' --limit 5",
        "freshness": {"status": "unavailable", "source": "not-fetched"},
    }
    recovery_needed = semver["status"] == "repair-only-semver-pr" or release_failure["status"] == "failed-release-run"
    version_paths = [package["pyproject"] for package in ownership.get("packages", []) if isinstance(package, dict)] + [
        package["package_json"] for package in ownership.get("typescript_packages", []) if isinstance(package, dict)
    ]
    return {
        "kind": PACKET_KIND,
        "semver_release_action": semver,
        "release_ci_failure": release_failure,
        "coordinated_recovery": {
            "status": "required" if recovery_needed else "not-required",
            "next_action": (
                "Create a coordinated explicit version-bump PR touching all release-owned version files, then run release proof."
                if recovery_needed
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
    parser.add_argument("--labels", nargs="*", default=[], help="Semver and other labels for fixture mode.")
    parser.add_argument("--changed-file", action="append", default=[], help="Changed file path for fixture mode.")
    parser.add_argument("--run-fixture", type=Path, help="Optional failed release run fixture JSON.")
    parser.add_argument("--format", choices=("json",), default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if bool(args.repo) ^ bool(args.pr):
        raise SystemExit("--repo and --pr must be supplied together")
    labels, changed_files = (args.labels, args.changed_file)
    if args.repo and args.pr:
        labels, changed_files = _live_pr_inputs(args.repo, args.pr)
    run_payload = _load_json(args.run_fixture) if args.run_fixture else None
    packet = recovery_packet(
        repo_root=args.repo_root,
        labels=labels,
        changed_files=changed_files,
        run_payload=run_payload,
    )
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
