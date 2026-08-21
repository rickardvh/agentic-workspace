"""Admit bounded live PR topology into the existing review-stack context owner."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

TOPOLOGY_OBSERVATION_KIND = "agentic-workspace/pr-topology-observation/v1"
TOPOLOGY_ADMISSION_KIND = "agentic-workspace/pr-topology-admission/v1"
STACK_CACHE_KIND = "agentic-workspace/pr-comment-stack/v2"
STACK_CACHE_PATH = Path(".agentic-workspace/local/cache/pr-comment-stack.json")


class TopologyAdmissionError(ValueError):
    """Raised when a provider observation cannot be admitted safely."""


def current_git_head_sha(target_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(target_root), "rev-parse", "HEAD"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise TopologyAdmissionError("current Git HEAD could not be resolved") from exc
    head_sha = result.stdout.strip() if result.returncode == 0 else ""
    if not head_sha:
        raise TopologyAdmissionError("current Git HEAD could not be resolved")
    return head_sha


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized_members(raw_members: Any) -> list[dict[str, str]]:
    if not isinstance(raw_members, list) or not raw_members:
        raise TopologyAdmissionError("topology observation must contain at least one stack member")
    if len(raw_members) > 100:
        raise TopologyAdmissionError("topology observation exceeds the 100-member admission bound")
    members: list[dict[str, str]] = []
    for raw in raw_members:
        if not isinstance(raw, dict):
            raise TopologyAdmissionError("every topology member must be an object")
        member = {
            "pr_number": _text(raw.get("pr_number") or raw.get("number")),
            "branch": _text(raw.get("branch") or raw.get("head_ref") or raw.get("headRefName")),
            "base_branch": _text(raw.get("base_branch") or raw.get("base_ref") or raw.get("baseRefName")),
            "head_sha": _text(raw.get("head_sha") or raw.get("headRefOid")),
            "url": _text(raw.get("url")),
        }
        if not all(member[field] for field in ("pr_number", "branch", "base_branch", "head_sha")):
            raise TopologyAdmissionError("every topology member requires PR number, head branch, base branch, and head SHA")
        members.append(member)
    if len({member["pr_number"] for member in members}) != len(members):
        raise TopologyAdmissionError("topology observation contains duplicate PR identities")
    if len({member["branch"] for member in members}) != len(members):
        raise TopologyAdmissionError("topology observation contains ambiguous head branches")
    return members


def _ordered_current_chain(*, members: list[dict[str, str]], current_branch: str) -> list[dict[str, str]]:
    by_branch = {member["branch"]: member for member in members}
    current = by_branch.get(current_branch)
    if current is None:
        raise TopologyAdmissionError("topology observation does not contain the current branch PR")
    descending: list[dict[str, str]] = []
    visited: set[str] = set()
    member = current
    while member:
        branch = member["branch"]
        if branch in visited:
            raise TopologyAdmissionError("topology observation contains a dependency cycle")
        visited.add(branch)
        descending.append(member)
        member = by_branch.get(member["base_branch"])
    if len(visited) != len(members):
        raise TopologyAdmissionError("topology observation contains members outside the current PR dependency chain")
    return list(reversed(descending))


def _observation_digest(observation: dict[str, Any]) -> str:
    encoded = json.dumps(observation, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def admit_pr_topology_observation(
    *,
    target_root: Path,
    observation: dict[str, Any],
    expected_repository: str,
    expected_branch: str,
) -> dict[str, Any]:
    """Validate and atomically admit one provider observation into the stack cache."""

    if not isinstance(observation, dict):
        raise TopologyAdmissionError("topology observation must be an object")
    repository = _text(observation.get("repository"))
    branch = _text(observation.get("branch") or observation.get("current_branch"))
    provider = _text(observation.get("provider") or observation.get("provider_class")) or "external-read-adapter"
    if repository != expected_repository:
        raise TopologyAdmissionError("topology repository does not match the requested repository")
    if branch != expected_branch:
        raise TopologyAdmissionError("topology branch does not match the current branch")
    current_head_sha = current_git_head_sha(target_root)
    observed_head_sha = _text(observation.get("head_sha") or observation.get("current_head_sha"))
    if observed_head_sha != current_head_sha:
        raise TopologyAdmissionError("topology observation is stale for the current Git HEAD")
    members = _ordered_current_chain(members=_normalized_members(observation.get("members")), current_branch=branch)
    current_member = next(member for member in members if member["branch"] == branch)
    if current_member["head_sha"] != current_head_sha:
        raise TopologyAdmissionError("current PR head does not match the current Git HEAD")

    normalized_observation = {
        "kind": TOPOLOGY_OBSERVATION_KIND,
        "status": "admitted",
        "provider": provider,
        "repository": repository,
        "current_branch": branch,
        "current_head_sha": current_head_sha,
        "current_pr_number": current_member["pr_number"],
        "members": members,
    }
    cache_path = target_root / STACK_CACHE_PATH
    prior: dict[str, Any] = {}
    if cache_path.is_file():
        try:
            loaded = json.loads(cache_path.read_text(encoding="utf-8"))
            prior = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            prior = {}
    prior_members = {
        (_text(item.get("pr_number")), _text(item.get("head_sha"))): item
        for item in prior.get("stack_members", [])
        if isinstance(item, dict)
    }
    cache_members: list[dict[str, Any]] = []
    for member in members:
        cached_member: dict[str, Any] = {
            **member,
            "topology_freshness": {
                "status": "current_at_admitted_head",
                "head_sha": member["head_sha"],
                "observation_digest": _observation_digest(normalized_observation),
            },
        }
        prior_member = prior_members.get((member["pr_number"], member["head_sha"]), {})
        if isinstance(prior_member.get("delta"), dict):
            cached_member["delta"] = prior_member["delta"]
        cache_members.append(cached_member)
    cache = {
        "kind": STACK_CACHE_KIND,
        "repository": repository,
        "topology_observation": {
            **normalized_observation,
            "observation_digest": _observation_digest(normalized_observation),
        },
        "stack_members": cache_members,
        "workflow_events": prior.get("workflow_events", []) if isinstance(prior.get("workflow_events"), list) else [],
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = cache_path.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(cache, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    temporary_path.replace(cache_path)
    return {
        "kind": TOPOLOGY_ADMISSION_KIND,
        "status": "admitted",
        "repository": repository,
        "current_branch": branch,
        "current_head_sha": current_head_sha,
        "current_pr_number": current_member["pr_number"],
        "dependency_order": [member["pr_number"] for member in members],
        "stack_member_count": len(members),
        "thread_comment_state": "unverified",
        "github_writes_performed": False,
        "cache_path": STACK_CACHE_PATH.as_posix(),
        "observation_digest": cache["topology_observation"]["observation_digest"],
        "claim_boundary": "Topology admission does not prove review-thread freshness or stack readiness.",
    }


def validate_admitted_pr_topology(
    *, target_root: Path, cache: dict[str, Any], expected_repository: str, expected_branch: str
) -> tuple[bool, str, dict[str, Any]]:
    """Revalidate an admitted cached observation against current repository state."""

    observation = cache.get("topology_observation")
    if not isinstance(observation, dict):
        return True, "legacy-stack-cache", {}
    if observation.get("status") != "admitted":
        return False, "topology-observation-not-admitted", observation
    if _text(observation.get("repository")) != expected_repository:
        return False, "topology-repository-mismatch", observation
    if _text(observation.get("current_branch")) != expected_branch:
        return False, "topology-branch-mismatch", observation
    try:
        current_head_sha = current_git_head_sha(target_root)
    except TopologyAdmissionError:
        return False, "current-head-unavailable", observation
    if _text(observation.get("current_head_sha")) != current_head_sha:
        return False, "topology-head-stale", observation
    try:
        members = _ordered_current_chain(members=_normalized_members(cache.get("stack_members")), current_branch=expected_branch)
    except TopologyAdmissionError:
        return False, "topology-cache-shape-invalid", observation
    current_member = next(member for member in members if member["branch"] == expected_branch)
    if current_member["head_sha"] != current_head_sha:
        return False, "topology-current-pr-head-stale", observation
    return True, "current", observation
