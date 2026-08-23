"""Publish the review authority required before merging a PR."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = REPO_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from chatgpt_review_loop import REVIEW_MARKER_RE, REVIEW_POLICY, parse_reviews  # noqa: E402

CHECK_NAME = "Review approval"
TRUSTED_ASSOCIATIONS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
REVIEW_AUTHORITY_MARKER_RE = re.compile(
    r"<!-- aw-review-authority-v1 key=(?P<key>[A-Za-z0-9._-]+) "
    r"class=(?P<producer_class>human|independent|separate-actor|fresh-context|distinct-provider) "
    r"producer=(?P<producer>[A-Za-z0-9._:@/-]+) pr=(?P<pr>[1-9][0-9]*) "
    r"head=(?P<head>[0-9a-f]{40}) decision=(?P<decision>blocked|merge-ready) "
    r"nonce=(?P<nonce>[A-Za-z0-9._:-]+) signature=(?P<signature>[0-9a-f]{64}) -->"
)
REVIEW_MODES = frozenset({"human", "independent", "same-agent", "github-association"})
_AUTHORITY_CLASSES = {
    "human": frozenset({"human"}),
    "independent": frozenset({"human", "independent", "separate-actor", "fresh-context", "distinct-provider"}),
}


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


def _authority_payload(
    *,
    key_id: str,
    producer_class: str,
    producer: str,
    pr_number: int,
    head_sha: str,
    decision: str,
    nonce: str,
) -> bytes:
    return "\n".join(
        ["aw-review-authority-v1", key_id, producer_class, producer, str(pr_number), head_sha, decision, nonce]
    ).encode("utf-8")


def sign_authority_receipt(
    *,
    secret: str,
    key_id: str,
    producer_class: str,
    producer: str,
    pr_number: int,
    head_sha: str,
    decision: str,
    nonce: str,
) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        _authority_payload(
            key_id=key_id,
            producer_class=producer_class,
            producer=producer,
            pr_number=pr_number,
            head_sha=head_sha,
            decision=decision,
            nonce=nonce,
        ),
        hashlib.sha256,
    ).hexdigest()


def _has_valid_authority_receipt(
    comment: dict[str, Any],
    *,
    pr_number: int,
    required_mode: str,
    authority_keys: dict[str, str],
) -> bool:
    if required_mode in {"same-agent", "github-association"}:
        return str(comment.get("author_association", "")).upper() in TRUSTED_ASSOCIATIONS
    allowed_classes = _AUTHORITY_CLASSES[required_mode]
    body = str(comment.get("body", ""))
    receipts = list(REVIEW_AUTHORITY_MARKER_RE.finditer(body))
    review_markers = list(REVIEW_MARKER_RE.finditer(body))
    if len(receipts) != 1 or len(review_markers) != 1:
        return False
    receipt = receipts[0]
    review_marker = review_markers[0]
    key_id = receipt.group("key")
    secret = authority_keys.get(key_id, "")
    if not secret or receipt.group("producer_class") not in allowed_classes:
        return False
    if (
        int(receipt.group("pr")) != pr_number
        or receipt.group("pr") != review_marker.group("pr")
        or receipt.group("head") != review_marker.group("head")
        or receipt.group("decision") != review_marker.group("decision")
    ):
        return False
    expected = sign_authority_receipt(
        secret=secret,
        key_id=key_id,
        producer_class=receipt.group("producer_class"),
        producer=receipt.group("producer"),
        pr_number=pr_number,
        head_sha=receipt.group("head"),
        decision=receipt.group("decision"),
        nonce=receipt.group("nonce"),
    )
    return hmac.compare_digest(expected, receipt.group("signature"))


def _comment_order(comment: dict[str, Any]) -> tuple[str, int]:
    timestamp = str(comment.get("updated_at") or comment.get("created_at") or "")
    identifier = int(comment.get("id") or comment.get("databaseId") or 0)
    return timestamp, identifier


def review_gate_decision(
    *,
    pr_number: int,
    head_sha: str,
    comments: Sequence[dict[str, Any]],
    carry_forward: Callable[[str, str], CarryForwardVerdict] | None = None,
    required_mode: str = "github-association",
    authority_keys: dict[str, str] | None = None,
) -> GateDecision:
    if required_mode not in REVIEW_MODES:
        raise ValueError(f"unsupported review authority mode: {required_mode}")
    resolved_keys = authority_keys or {}
    candidates = [
        comment
        for comment in comments
        if "aw-chatgpt-review" in str(comment.get("body", ""))
        and _has_valid_authority_receipt(
            comment,
            pr_number=pr_number,
            required_mode=required_mode,
            authority_keys=resolved_keys,
        )
    ]
    if not candidates:
        return GateDecision(
            status="review-missing",
            conclusion="failure",
            title="Pull request has no authoritative review",
            summary=(
                f"Run {REVIEW_POLICY} for head {head_sha} through the configured {required_mode} authority; "
                "green CI, GitHub association, and unsigned marker text are not merge authority."
            ),
        )

    latest = max(candidates, key=_comment_order)
    matches, rejected = parse_reviews([latest], expected_pr=pr_number, expected_head=head_sha)
    if not matches:
        reason = str((rejected or [{}])[0].get("reason") or "invalid-review-marker")
        reviewed_head = str((rejected or [{}])[0].get("reviewed_head") or "")
        if reason == "stale-head" and reviewed_head:
            reviewed, reviewed_rejections = parse_reviews(
                [latest], expected_pr=pr_number, expected_head=reviewed_head
            )
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


def _git(args: Sequence[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=check, capture_output=True, text=True, input=input_text
    )


def _patch_id(base: str, head: str) -> str:
    patch = _git(["diff", "--binary", "--full-index", "--no-renames", base, head]).stdout
    if not patch:
        return "empty"
    result = _git(["patch-id", "--verbatim"], input_text=patch).stdout.strip()
    return result.split()[0] if result else "empty"


def _trusted_base_carry_forward(
    *, pr_number: int, reviewed_head: str, current_head: str, base_head: str
) -> CarryForwardVerdict:
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
        base_ancestor = _git(
            ["merge-base", "--is-ancestor", integrated_parent, base_head], check=False
        )
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
    parser.add_argument("--required-mode", choices=sorted(REVIEW_MODES), default="github-association")
    parser.add_argument("--authority-key-env", default="AW_REVIEW_AUTHORITY_KEY")
    parser.add_argument("--authority-key-id", default="primary")
    args = parser.parse_args(argv)

    event = json.loads(args.event.read_text(encoding="utf-8"))
    pr_number = _pr_number(event)
    if pr_number is None:
        print(json.dumps({"status": "not-a-pull-request"}, sort_keys=True))
        return 0
    pull_request = _gh_json(["api", f"repos/{args.repository}/pulls/{pr_number}"])
    head_sha = str(pull_request["head"]["sha"])
    pages = _gh_json(["api", "--paginate", "--slurp", f"repos/{args.repository}/issues/{pr_number}/comments?per_page=100"])
    comments = [comment for page in pages for comment in page]
    authority_secret = os.environ.get(args.authority_key_env, "")
    authority_keys = {args.authority_key_id: authority_secret} if authority_secret else {}
    decision = review_gate_decision(
        pr_number=pr_number,
        head_sha=head_sha,
        comments=comments,
        required_mode=args.required_mode,
        authority_keys=authority_keys,
        carry_forward=lambda reviewed, current: _trusted_base_carry_forward(
            pr_number=pr_number,
            reviewed_head=reviewed,
            current_head=current,
            base_head=str(pull_request["base"]["sha"]),
        ),
    )
    _post_check(repository=args.repository, head_sha=head_sha, decision=decision)
    print(json.dumps({"pr_number": pr_number, "head_sha": head_sha, **decision.__dict__}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
