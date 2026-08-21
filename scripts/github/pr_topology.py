"""Resolve GitHub PR topology and admit it into AW's existing stack owner."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from agentic_workspace.review_stack_topology import (
    TOPOLOGY_OBSERVATION_KIND,
    TopologyAdmissionError,
    admit_pr_topology_observation,
    current_git_head_sha,
)


def _validated_pull_requests(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise TopologyAdmissionError("GitHub PR topology provider returned an unexpected shape")
    required_fields = ("number", "headRefName", "baseRefName", "headRefOid")
    if any(not isinstance(item, dict) or any(not str(item.get(field) or "").strip() for field in required_fields) for item in payload):
        raise TopologyAdmissionError("GitHub PR topology provider returned an incomplete PR record")
    return payload


def _github_pull_requests(*, repository: str) -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                repository,
                "--state",
                "open",
                "--limit",
                "100",
                "--json",
                "number,url,headRefName,baseRefName,headRefOid",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise TopologyAdmissionError("GitHub PR topology provider is unavailable") from exc
    if result.returncode != 0:
        raise TopologyAdmissionError("GitHub PR topology provider read failed")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise TopologyAdmissionError("GitHub PR topology provider returned malformed JSON") from exc
    return _validated_pull_requests(payload)


def github_topology_observation(*, repository: str, branch: str, head_sha: str, pull_requests: list[dict[str, Any]]) -> dict[str, Any]:
    pull_requests = _validated_pull_requests(pull_requests)
    by_branch: dict[str, list[dict[str, Any]]] = {}
    for pull_request in pull_requests:
        by_branch.setdefault(str(pull_request.get("headRefName") or "").strip(), []).append(pull_request)
    selected = by_branch.get(branch, [])
    if not selected:
        raise TopologyAdmissionError("no open pull request matches the current branch")
    if len(selected) != 1:
        raise TopologyAdmissionError("multiple open pull requests match the current branch")
    descending: list[dict[str, Any]] = []
    visited: set[str] = set()
    current = selected[0]
    while current:
        current_branch = str(current.get("headRefName") or "").strip()
        if current_branch in visited:
            raise TopologyAdmissionError("GitHub PR topology contains a dependency cycle")
        visited.add(current_branch)
        descending.append(current)
        base_branch = str(current.get("baseRefName") or "").strip()
        candidates = by_branch.get(base_branch, [])
        if len(candidates) > 1:
            raise TopologyAdmissionError("GitHub PR topology contains an ambiguous base branch")
        current = candidates[0] if candidates else None
    members = list(reversed(descending))
    return {
        "kind": TOPOLOGY_OBSERVATION_KIND,
        "provider": "github-gh-read-only",
        "repository": repository,
        "branch": branch,
        "head_sha": head_sha,
        "members": members,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--target", default=".")
    parser.add_argument("--input", type=Path, help="Read a saved gh pr list JSON fixture instead of calling GitHub.")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    target_root = Path(args.target).resolve()
    try:
        if args.input:
            loaded = json.loads(args.input.read_text(encoding="utf-8"))
            pull_requests = _validated_pull_requests(loaded)
        else:
            pull_requests = _github_pull_requests(repository=args.repo)
        observation = github_topology_observation(
            repository=args.repo,
            branch=args.branch,
            head_sha=current_git_head_sha(target_root),
            pull_requests=pull_requests,
        )
        result = admit_pr_topology_observation(
            target_root=target_root,
            observation=observation,
            expected_repository=args.repo,
            expected_branch=args.branch,
        )
    except (OSError, json.JSONDecodeError, TopologyAdmissionError) as exc:
        result = {
            "kind": "agentic-workspace/pr-topology-admission/v1",
            "status": "rejected",
            "reason": str(exc),
            "github_writes_performed": False,
            "safe_recovery": "Refresh the bounded read or resolve ambiguous repository/branch/PR identity before retrying.",
        }
        print(json.dumps(result, indent=2) if args.format == "json" else f"rejected: {exc}")
        return 1
    print(json.dumps(result, indent=2) if args.format == "json" else f"admitted PR #{result['current_pr_number']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
