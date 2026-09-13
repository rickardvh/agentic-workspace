"""Publish the review authority required before merging a PR."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence
from urllib.parse import urlencode

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = REPO_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from chatgpt_review_loop import REVIEW_POLICY, parse_reviews  # noqa: E402

CHECK_NAME = "Review approval"
REVIEWER_APP_SLUG = "chatgpt-codex-connector"


@dataclass(frozen=True)
class GateDecision:
    status: str
    conclusion: str
    title: str
    summary: str
    review_url: str = ""


@dataclass(frozen=True)
class CarryForwardVerdict:
    allowed: bool
    reason: str


def _comment_order(comment: dict[str, Any]) -> tuple[str, int]:
    timestamp = str(comment.get("created_at") or comment.get("submitted_at") or "")
    identifier = int(comment.get("id") or comment.get("databaseId") or 0)
    return timestamp, identifier


def _reviewer_markers(comments: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        comment
        for comment in comments
        if "aw-chatgpt-review" in str(comment.get("body", ""))
        and isinstance(comment.get("performed_via_github_app"), dict)
        and comment["performed_via_github_app"].get("slug") == REVIEWER_APP_SLUG
    ]


def _integrity_failure(detail: str) -> GateDecision:
    return GateDecision(
        "review-integrity-blocked",
        "failure",
        "Review decision integrity is not established",
        detail + " Publish a newer unedited marker through the configured reviewer App.",
    )


def advance_watermark(state: dict[str, Any], comments: Sequence[dict[str, Any]], event: dict[str, Any]) -> dict[str, Any]:
    """Retain the highest observed decision, including deletion/edit tombstones."""
    result = deepcopy(state)
    candidates = _reviewer_markers(comments)
    if event.get("action") in ("deleted", "edited"):
        candidates += _reviewer_markers([event.get("comment", {})])
    latest = max(candidates, key=_comment_order) if candidates else None
    previous = result["latest"]
    if latest and (previous is None or list(_comment_order(latest)) > previous["order"]):
        result["latest"] = {
            "order": list(_comment_order(latest)),
            "node_id": latest.get("node_id"),
            "digest": hashlib.sha256(str(latest["body"]).encode()).hexdigest(),
            "tainted": False,
        }
    retained = result["latest"]
    if retained is None:
        return result
    current = next((row for row in _reviewer_markers(comments) if row.get("node_id") == retained["node_id"]), None)
    altered_event = event.get("action") in ("deleted", "edited") and event.get("comment", {}).get("node_id") == retained["node_id"]
    if (
        not current
        or current.get("_source_unedited") is not True
        or altered_event
        or list(_comment_order(current)) != retained["order"]
        or retained["order"][0] <= result["after"]
        or hashlib.sha256(str(current.get("body", "")).encode()).hexdigest() != retained["digest"]
    ):
        retained["tainted"] = True
    return result


def review_gate_decision(
    *,
    pr_number: int,
    head_sha: str,
    comments: Sequence[dict[str, Any]],
    carry_forward: Callable[[str, str], CarryForwardVerdict] | None = None,
) -> GateDecision:
    # GitHub API provenance is the repository's configured producer boundary.
    # Login, association and copied marker text cannot substitute for it.
    associated = _reviewer_markers(comments)
    if not associated:
        return GateDecision(
            status="review-missing",
            conclusion="failure",
            title="Pull request has no authoritative review",
            summary=(
                f"Run {REVIEW_POLICY} for head {head_sha}; green CI is not merge authority. "
                f"An exact-head terminal marker from the configured {REVIEWER_APP_SLUG} reviewer App is required."
            ),
        )

    latest = max(associated, key=_comment_order)
    if latest.get("_source_unedited") is not True:
        return _integrity_failure("The latest terminal marker is edited or its mutation metadata is unavailable.")
    matches, rejected = parse_reviews([latest], expected_pr=pr_number, expected_head=head_sha)
    if not matches:
        reason = str((rejected or [{}])[0].get("reason") or "invalid-review-marker")
        reviewed_head = str((rejected or [{}])[0].get("reviewed_head") or "")
        if reason == "stale-head" and reviewed_head:
            reviewed, reviewed_rejections = parse_reviews([latest], expected_pr=pr_number, expected_head=reviewed_head)
            if not reviewed:
                reason = str((reviewed_rejections or [{}])[0].get("reason") or "invalid-review-marker")
            else:
                review = reviewed[0]
                review_url = str(latest.get("html_url") or review.url)
                if review.decision != "merge-ready":
                    return GateDecision(
                        status="review-blocked",
                        conclusion="failure",
                        title="Latest authoritative review is blocked",
                        summary="Resolve the review blocker and obtain a merge-ready decision.",
                        review_url=review_url,
                    )
                if carry_forward is None:
                    return GateDecision(
                        status="review-ancestry-unverified",
                        conclusion="failure",
                        title="Approved review ancestry was not verified",
                        summary=f"Verify that reviewed head {reviewed_head} is an ancestor of {head_sha}.",
                        review_url=review_url,
                    )
                try:
                    verdict = carry_forward(reviewed_head, head_sha)
                except Exception as exc:  # pragma: no cover - exercised through the command boundary
                    return GateDecision(
                        status="review-ancestry-unverified",
                        conclusion="failure",
                        title="Approved review ancestry could not be verified",
                        summary=f"GitHub could not verify {reviewed_head} as an ancestor of {head_sha}: {exc}",
                        review_url=review_url,
                    )
                if verdict.allowed:
                    return GateDecision(
                        status="merge-ready-carried-forward",
                        conclusion="success",
                        title="Prior merge-ready review remains authoritative",
                        summary=(
                            f"{REVIEW_POLICY} marked {reviewed_head} merge-ready; every later commit is "
                            f"a trusted-base merge that preserves the reviewed patch through {head_sha}."
                        ),
                        review_url=review_url,
                    )
                return GateDecision(
                    status="review-carry-forward-rejected",
                    conclusion="failure",
                    title="Unreviewed delta is not a patch-preserving base integration",
                    summary=f"Review head {head_sha} again ({verdict.reason}; reviewed head {reviewed_head}).",
                    review_url=review_url,
                )
        detail = f"; latest review covers {reviewed_head}" if reviewed_head else ""
        return GateDecision(
            status=f"review-{reason}",
            conclusion="failure",
            title="Latest review does not authorize this pull request",
            summary=f"Review head {head_sha} again ({reason}{detail}).",
            review_url=str(latest.get("html_url") or latest.get("url") or ""),
        )

    review = matches[0]
    review_url = str(latest.get("html_url") or review.url)
    if review.decision != "merge-ready":
        return GateDecision(
            status="review-blocked",
            conclusion="failure",
            title="Latest authoritative review is blocked",
            summary="Resolve the review blocker and obtain a merge-ready decision.",
            review_url=review_url,
        )
    return GateDecision(
        status="merge-ready",
        conclusion="success",
        title="Current head is review-approved",
        summary=f"{REVIEW_POLICY} marked {head_sha} merge-ready.",
        review_url=review_url,
    )


def _gh_json(args: Sequence[str]) -> Any:
    completed = subprocess.run(["gh", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def _review_records(*, repository: str, pr_number: int) -> list[dict[str, Any]]:
    comment_pages = _gh_json(["api", "--paginate", "--slurp", f"repos/{repository}/issues/{pr_number}/comments?per_page=100"])
    review_pages = _gh_json(["api", "--paginate", "--slurp", f"repos/{repository}/pulls/{pr_number}/reviews?per_page=100"])
    comments = [comment for page in comment_pages for comment in page]
    reviews = [review for page in review_pages for review in page if str(review.get("state") or "").upper() != "DISMISSED"]
    records = [*comments, *reviews]
    candidates = _reviewer_markers(records)
    # REST attribution does not prove that a terminal body was never edited.
    # GraphQL lastEditedAt also detects edits within the creation timestamp's second.
    for offset in range(0, len(candidates), 100):
        batch = candidates[offset : offset + 100]
        if any(not row.get("node_id") for row in batch):
            raise ValueError("Reviewer source node identity is unavailable")
        response = _gh_payload(
            "POST",
            "graphql",
            {
                "query": "query($ids:[ID!]!){nodes(ids:$ids){id ... on IssueComment{body lastEditedAt} ... on PullRequestReview{body lastEditedAt}}}",
                "variables": {"ids": [row["node_id"] for row in batch]},
            },
        )
        if response.get("errors"):
            raise ValueError("Reviewer mutation metadata is unavailable")
        nodes = {node["id"]: node for node in response["data"]["nodes"] if node}
        for row in batch:
            node = nodes.get(row["node_id"], {})
            row["_source_unedited"] = "lastEditedAt" in node and node["lastEditedAt"] is None and node.get("body") == row["body"]
    return records


def _gh_payload(method: str, endpoint: str, payload: dict[str, Any]) -> Any:
    result = subprocess.run(
        ["gh", "api", "--method", method, endpoint, "--input", "-"],
        cwd=REPO_ROOT,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def _watermark_check(repository: str, pr_number: int, app_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    # A stable trusted-history anchor keeps the same PR state across head changes
    # and publisher upgrades. This is one App-owned check, not a repository ledger.
    roots = _git(["rev-list", "--max-parents=0", "HEAD"]).stdout.split()
    if len(roots) != 1:
        raise ValueError("Review state requires one stable trusted repository root")
    anchor = roots[0]
    name = f"Review decision watermark / PR {pr_number}"
    query = urlencode({"check_name": name, "app_id": app_id, "filter": "all", "per_page": 100})
    pages = _gh_json(["api", "--paginate", "--slurp", f"repos/{repository}/commits/{anchor}/check-runs?{query}"])
    checks = [
        check for page in pages for check in page["check_runs"] if check.get("app", {}).get("id") == app_id and check.get("name") == name
    ]
    identity = {"kind": "review-decision-watermark/v1", "repository": repository, "pr_number": pr_number, "anchor": anchor}
    if not checks:
        state = {**identity, "after": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "latest": None}
        check = _gh_payload(
            "POST",
            f"repos/{repository}/check-runs",
            {
                "name": name,
                "head_sha": anchor,
                "status": "completed",
                "conclusion": "neutral",
                "output": _watermark_output(state),
            },
        )
    elif len(checks) == 1:
        check = checks[0]
        state = json.loads(check["output"]["text"])
    else:
        raise ValueError("Ambiguous publisher watermark checks")
    if check.get("app", {}).get("id") != app_id or check.get("head_sha") != anchor:
        raise ValueError("Watermark publisher/anchor identity mismatch")
    if any(state.get(key) != value for key, value in identity.items()) or not isinstance(state.get("after"), str) or not state["after"]:
        raise ValueError("Invalid publisher watermark identity")
    latest = state["latest"]
    if latest is not None and (
        not isinstance(latest, dict)
        or set(latest) != {"order", "node_id", "digest", "tainted"}
        or not isinstance(latest["order"], list)
        or len(latest["order"]) != 2
        or not isinstance(latest["order"][0], str)
        or type(latest["order"][1]) is not int
        or not isinstance(latest["node_id"], str)
        or not isinstance(latest["digest"], str)
        or type(latest["tainted"]) is not bool
    ):
        raise ValueError("Malformed retained reviewer decision")
    return check, state


def _watermark_output(state: dict[str, Any]) -> dict[str, str]:
    return {
        "title": "Retained reviewer decision identity",
        "summary": "Publisher-owned integrity state; not merge approval.",
        "text": json.dumps(state, sort_keys=True),
    }


def _save_watermark(repository: str, check: dict[str, Any], state: dict[str, Any]) -> None:
    endpoint = f"repos/{repository}/check-runs/{check['id']}"
    _gh_payload("PATCH", endpoint, {"output": _watermark_output(state)})
    observed = _gh_json(["api", endpoint])
    if observed.get("app", {}).get("id") != check["app"]["id"] or json.loads(observed["output"]["text"]) != state:
        raise ValueError("Publisher watermark readback mismatch")


def _git(args: Sequence[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, check=check, capture_output=True, text=True, input=input_text)


def _patch_id(base: str, head: str) -> str:
    patch = _git(["diff", "--binary", "--full-index", "--no-renames", base, head]).stdout
    if not patch:
        return "empty"
    result = _git(["patch-id", "--verbatim"], input_text=patch).stdout.strip()
    return result.split()[0] if result else "empty"


def _trusted_base_carry_forward(*, pr_number: int, reviewed_head: str, current_head: str, base_head: str) -> CarryForwardVerdict:
    _git(["fetch", "--no-tags", "origin", f"pull/{pr_number}/head"])
    cursor = current_head
    visited: set[str] = set()
    while cursor != reviewed_head:
        if cursor in visited:
            return CarryForwardVerdict(False, "first-parent-cycle")
        visited.add(cursor)
        fields = _git(["rev-list", "--parents", "-n", "1", cursor]).stdout.strip().split()
        if len(fields) != 3:
            return CarryForwardVerdict(False, "ordinary-or-octopus-commit-after-review")
        _, first_parent, integrated_parent = fields
        base_ancestor = _git(["merge-base", "--is-ancestor", integrated_parent, base_head], check=False)
        if base_ancestor.returncode != 0:
            return CarryForwardVerdict(False, "merge-parent-is-not-trusted-base-history")
        merge_base = _git(["merge-base", first_parent, integrated_parent]).stdout.strip()
        if not merge_base or _patch_id(merge_base, first_parent) != _patch_id(integrated_parent, cursor):
            return CarryForwardVerdict(False, "merge-does-not-preserve-reviewed-patch")
        cursor = first_parent
    return CarryForwardVerdict(True, "trusted-base-merges-preserve-reviewed-patch")


def _post_check(*, repository: str, head_sha: str, decision: GateDecision) -> None:
    output: dict[str, str] = {"title": decision.title, "summary": decision.summary}
    payload = {
        "name": CHECK_NAME,
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": decision.conclusion,
        "output": output,
    }
    if decision.review_url:
        payload["details_url"] = decision.review_url
    subprocess.run(
        ["gh", "api", "--method", "POST", f"repos/{repository}/check-runs", "--input", "-"],
        cwd=REPO_ROOT,
        check=True,
        input=json.dumps(payload),
        text=True,
    )


def _pr_number(event: dict[str, Any]) -> int | None:
    pull_request = event.get("pull_request")
    if isinstance(pull_request, dict):
        return int(pull_request["number"])
    issue = event.get("issue")
    if isinstance(issue, dict) and issue.get("pull_request"):
        return int(issue["number"])
    workflow_run = event.get("workflow_run")
    if isinstance(workflow_run, dict):
        pull_requests = workflow_run.get("pull_requests")
        if isinstance(pull_requests, list) and pull_requests and isinstance(pull_requests[0], dict):
            return int(pull_requests[0]["number"])
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--publisher-app-id", type=int, required=True)
    args = parser.parse_args(argv)
    if args.publisher_app_id <= 0 or args.publisher_app_id == 15368:
        parser.error("A dedicated publisher App ID is required")

    event = json.loads(args.event.read_text(encoding="utf-8"))
    pr_number = _pr_number(event)
    if pr_number is None:
        print(json.dumps({"status": "not-a-pull-request"}, sort_keys=True))
        return 0
    pull_request = _gh_json(["api", f"repos/{args.repository}/pulls/{pr_number}"])
    head_sha = str(pull_request["head"]["sha"])
    # Invalidate any earlier success before observing mutable source or state.
    # Exceptions/interruption after this point leave the exact head blocked.
    _post_check(repository=args.repository, head_sha=head_sha, decision=_integrity_failure("Publisher re-evaluation is in progress."))
    watermark_check, state = _watermark_check(args.repository, pr_number, args.publisher_app_id)
    comments = _review_records(repository=args.repository, pr_number=pr_number)
    state = advance_watermark(state, comments, event)
    _save_watermark(args.repository, watermark_check, state)
    # Reobserve after durable state publication; preserve any newly seen change
    # before an approval can be published.
    comments = _review_records(repository=args.repository, pr_number=pr_number)
    state = advance_watermark(state, comments, event)
    _save_watermark(args.repository, watermark_check, state)
    decision = review_gate_decision(
        pr_number=pr_number,
        head_sha=head_sha,
        comments=comments,
        carry_forward=lambda reviewed, current: _trusted_base_carry_forward(
            pr_number=pr_number,
            reviewed_head=reviewed,
            current_head=current,
            base_head=str(pull_request["base"]["sha"]),
        ),
    )
    if state["latest"] is None or state["latest"]["tainted"]:
        decision = _integrity_failure("The retained reviewer decision is absent, changed, or predates state initialization.")
    _post_check(repository=args.repository, head_sha=head_sha, decision=decision)
    print(json.dumps({"pr_number": pr_number, "head_sha": head_sha, **decision.__dict__}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
