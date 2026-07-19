"""Build a compact PR comment/review delta packet.

The helper is read-only. It can consume a saved GraphQL/normalized fixture for
tests and dogfooding, or fetch a PR's comments and review threads through
``gh api graphql`` for live use.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKET_KIND = "agentic-workspace/pr-comment-delta/v1"
ISSUE_COMMENT_LIMIT = 100
REVIEW_LIMIT = 100
REVIEW_THREAD_LIMIT = 100
THREAD_COMMENT_LIMIT = 20
CATEGORIES = (
    "actionable_code_doc_body_change",
    "pr_metadata_body_only_change",
    "ci_label_only_issue",
    "informational_no_local_change",
    "ambiguous_needs_human",
)
ACTIONABLE_CATEGORIES = (
    "actionable_code_doc_body_change",
    "pr_metadata_body_only_change",
    "ci_label_only_issue",
)
_STRUCTURED_REVIEW_SECTION_RE = re.compile(
    r"(?mi)^(decision|what_landed|intent_served|proof|unresolved|closure_honest|next_action)\s*:\s*"
)
_STRUCTURED_REVIEW_MARKER_RE = re.compile(r"<!--\s*aw-chatgpt-review\b[^>]*\bdecision=([a-z_-]+)", re.IGNORECASE)
_STRUCTURED_REVIEW_SUPPORTED_DECISIONS = {"blocked", "merge-ready"}


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SystemExit(f"invalid --since timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _timestamp_value(item: dict[str, Any]) -> datetime | None:
    for key in ("created_at", "createdAt", "submitted_at", "submittedAt", "updated_at", "updatedAt"):
        parsed = _parse_timestamp(str(item.get(key) or ""))
        if parsed is not None:
            return parsed
    return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _excerpt(body: str, limit: int = 220) -> str:
    collapsed = " ".join(body.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 1]}..."


def _author_login(raw: Any) -> str:
    if isinstance(raw, dict):
        return _text(raw.get("login"))
    return _text(raw)


def _normalize_graphql(payload: dict[str, Any]) -> dict[str, Any]:
    graphql_shape = False
    pr = payload.get("pull_request") if isinstance(payload.get("pull_request"), dict) else None
    if pr is None:
        pr = payload.get("data", {}).get("repository", {}).get("pullRequest", {})
        graphql_shape = bool(pr)
    else:
        graphql_shape = True
    if not isinstance(pr, dict):
        pr = {}

    comments: list[dict[str, Any]] = []
    truncated_surfaces: list[str] = []
    page_info = _page_info(pr.get("comments"))
    if page_info.get("hasNextPage") is True:
        truncated_surfaces.append("comments")
    for node in pr.get("comments", {}).get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        comments.append(
            {
                "kind": "issue_comment",
                "database_id": node.get("databaseId"),
                "url": node.get("url"),
                "body": node.get("body"),
                "created_at": node.get("createdAt"),
                "updated_at": node.get("updatedAt"),
                "author": node.get("author"),
            }
        )
    page_info = _page_info(pr.get("reviews"))
    if page_info.get("hasNextPage") is True:
        truncated_surfaces.append("reviews")
    for review in pr.get("reviews", {}).get("nodes", []) or []:
        if not isinstance(review, dict):
            continue
        comments.append(
            {
                "kind": "review",
                "database_id": review.get("databaseId"),
                "url": review.get("url"),
                "body": review.get("body"),
                "created_at": review.get("submittedAt"),
                "author": review.get("author"),
                "review_state": review.get("state"),
            }
        )
    page_info = _page_info(pr.get("reviewThreads"))
    if page_info.get("hasNextPage") is True:
        truncated_surfaces.append("reviewThreads")
    for index, thread in enumerate(pr.get("reviewThreads", {}).get("nodes", []) or []):
        if not isinstance(thread, dict):
            continue
        page_info = _page_info(thread.get("comments"))
        if page_info.get("hasNextPage") is True:
            truncated_surfaces.append(f"reviewThreads[{index}].comments")
        for comment in thread.get("comments", {}).get("nodes", []) or []:
            if not isinstance(comment, dict):
                continue
            comments.append(
                {
                    "kind": "review_thread_comment",
                    "database_id": comment.get("databaseId"),
                    "url": comment.get("url"),
                    "body": comment.get("body"),
                    "created_at": comment.get("createdAt"),
                    "updated_at": comment.get("updatedAt"),
                    "author": comment.get("author"),
                    "path": comment.get("path"),
                    "line": comment.get("line") or comment.get("originalLine"),
                    "diff_hunk": comment.get("diffHunk"),
                    "is_resolved": thread.get("isResolved"),
                    "is_outdated": thread.get("isOutdated"),
                    "reply_to_database_id": (comment.get("replyTo") or {}).get("databaseId"),
                }
            )
    return {
        "repository": payload.get("repository") or payload.get("repo"),
        "pr_number": payload.get("pr_number") or payload.get("number"),
        "pr_url": pr.get("url") or payload.get("pr_url"),
        "pr_head_sha": pr.get("headRefOid") or payload.get("pr_head_sha") or payload.get("head_sha"),
        "comments": comments if comments else payload.get("comments", []),
        "pagination": {
            "truncated": bool(truncated_surfaces),
            "truncated_surfaces": truncated_surfaces,
            "limits": {
                "comments_first": ISSUE_COMMENT_LIMIT,
                "reviews_first": REVIEW_LIMIT,
                "review_threads_first": REVIEW_THREAD_LIMIT,
                "thread_comments_first": THREAD_COMMENT_LIMIT,
            },
            "rule": "When truncated is true, do not treat this packet as a complete review-comment delta.",
        },
        "comment_surfaces": {
            "inspected": ["issue_comments", "reviews", "review_threads"] if graphql_shape else ["normalized_comments"],
            "unavailable": [] if graphql_shape else ["thread_surface_completeness"],
            "rule": "Use unavailable surfaces to bound review-readiness claims; normalized fixtures may not prove complete thread coverage.",
        },
    }


def _page_info(connection: Any) -> dict[str, Any]:
    if not isinstance(connection, dict):
        return {}
    page_info = connection.get("pageInfo")
    return page_info if isinstance(page_info, dict) else {}


def _baseline_seen_urls(path: Path | None) -> set[str]:
    if path is None:
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    urls = payload.get("seen_comment_urls", []) if isinstance(payload, dict) else []
    return {_text(item) for item in urls if _text(item)}


def _requests_source_change(body: str) -> bool:
    lower = body.lower()
    source_evidence = (
        re.search(r"(?:^|[\s`])(?:[\w.-]+/)+[\w.-]+\.(?:py|pyi|js|mjs|ts|tsx|json|toml|ya?ml|md)(?:[\s`]|$)", body)
        or re.search(r"`?[A-Za-z_][A-Za-z0-9_.]*\(\)`?", body)
        or any(token in lower for token in ("source code", "code change", "implementation", "focused test", "regression test"))
    )
    requested_change = any(
        token in lower
        for token in ("fix", "change", "update", "add ", "remove", "replace", "quarantine", "correct", "must ", "should ")
    )
    return bool(source_evidence and requested_change)


def _is_positive_review_summary(body: str) -> bool:
    lower = body.lower()
    ready_signal = any(token in lower for token in ("recheck result: ready", "review result: ready", "no remaining review blocker"))
    unresolved_signal = any(token in lower for token in ("changes needed", "blocking issue")) or (
        "remaining blocker" in lower and "no remaining review blocker" not in lower
    )
    return ready_signal and not unresolved_signal


def _parse_structured_review_sections(body: str) -> tuple[dict[str, str], set[str], list[str]]:
    section_matches = list(_STRUCTURED_REVIEW_SECTION_RE.finditer(body))
    marker_matches = list(_STRUCTURED_REVIEW_MARKER_RE.finditer(body))
    fields: dict[str, str] = {}
    duplicates: set[str] = set()
    marker_starts = [match.start() for match in marker_matches]

    for index, match in enumerate(section_matches):
        name = match.group(1).lower()
        value_start = match.end()
        next_stops = [section_matches[index + 1].start()] if index + 1 < len(section_matches) else []
        next_stops.extend(marker_start for marker_start in marker_starts if marker_start >= value_start)
        value_end = min(next_stops) if next_stops else len(body)
        if name in fields:
            duplicates.add(name)
            continue
        fields[name] = body[value_start:value_end].strip()

    marker_decisions = [match.group(1).lower() for match in marker_matches]
    return fields, duplicates, marker_decisions


def _classify_structured_review_status(body: str) -> tuple[str, str, str] | None:
    fields, duplicates, marker_decisions = _parse_structured_review_sections(body)
    if not fields and not marker_decisions:
        return None

    decision = fields.get("decision", "").lower()
    unresolved = fields.get("unresolved")
    if (
        "decision" in duplicates
        or "unresolved" in duplicates
        or not decision
        or unresolved is None
        or len(marker_decisions) != 1
    ):
        return (
            "ambiguous_needs_human",
            "structured review-status signal is missing required fields or is inconsistent",
            "Inspect the structured review status manually before editing or treating next_action prose as a local blocker.",
        )
    marker_decision = marker_decisions[0]
    if (
        decision not in _STRUCTURED_REVIEW_SUPPORTED_DECISIONS
        or marker_decision not in _STRUCTURED_REVIEW_SUPPORTED_DECISIONS
        or marker_decision != decision
    ):
        return (
            "ambiguous_needs_human",
            "structured review status uses an unsupported or conflicting decision",
            "Resolve the inconsistent structured review status before acting on next_action prose.",
        )

    unresolved_lower = unresolved.lower()
    if decision == "merge-ready":
        if _requests_source_change(unresolved) or any(token in unresolved_lower for token in ("blocked", "remaining blocker")):
            return (
                "ambiguous_needs_human",
                "structured merge-ready decision conflicts with its unresolved blocker summary",
                "Resolve the inconsistent structured review status before acting on next_action prose.",
            )
        return (
            "informational_no_local_change",
            "structured review status explicitly reports readiness with no unresolved local blocker",
            "No local proof required unless a later review reopens a blocker.",
        )
    if not unresolved:
        return (
            "ambiguous_needs_human",
            "structured blocked review status has no unresolved blocker content",
            "Classify the unresolved blocker manually before acting on next_action prose.",
        )
    if _requests_source_change(unresolved):
        return (
            "actionable_code_doc_body_change",
            "structured blocked review status identifies a source or test change",
            "Inspect the referenced source and test surfaces; run focused proof for the changed behavior.",
        )
    if any(token in unresolved_lower for token in ("ci", "check", "workflow", "label", "draft", "mergeable")):
        return (
            "ci_label_only_issue",
            "structured blocked review status identifies CI, labels, draft state, or mergeability",
            "Inspect PR checks/metadata; run local proof only if CI points to a reproducible failure.",
        )
    if any(token in unresolved_lower for token in ("pr body", "pull request body", "description", "title", "close #", "closes #", "closing #")):
        return (
            "pr_metadata_body_only_change",
            "structured blocked review status identifies PR metadata or closure text",
            "Update PR metadata/body only; no source proof unless the body is generated from checked-in files.",
        )
    return (
        "ambiguous_needs_human",
        "structured blocked review status does not identify a recognized blocker type",
        "Classify the unresolved blocker manually before acting on next_action prose.",
    )


def _classify(item: dict[str, Any]) -> tuple[str, str, str]:
    body = _text(item.get("body"))
    lower = body.lower()
    path = _text(item.get("path"))
    if item.get("is_resolved") is True or item.get("is_outdated") is True:
        return (
            "informational_no_local_change",
            "review thread is resolved or outdated",
            "No local proof unless the thread is reopened.",
        )
    if path:
        return (
            "actionable_code_doc_body_change",
            "inline review comment anchors to a changed file",
            f"Inspect {path}; run focused tests or `agentic-workspace proof --changed {path} --format json`.",
        )
    structured_status = _classify_structured_review_status(body)
    if structured_status is not None:
        return structured_status
    if _is_positive_review_summary(body):
        return (
            "informational_no_local_change",
            "review summary explicitly reports readiness with no remaining blocker",
            "No local proof required unless a later review reopens a blocker.",
        )
    if _requests_source_change(body):
        return (
            "actionable_code_doc_body_change",
            "comment explicitly requests source or test changes",
            "Inspect the referenced source and test surfaces; run focused proof for the changed behavior.",
        )
    if any(token in lower for token in ("pr body", "pull request body", "description", "title", "close #", "closes #", "closing #")):
        return (
            "pr_metadata_body_only_change",
            "comment appears to target PR title/body/closure metadata",
            "Update PR metadata/body only; no source proof unless the body is generated from checked-in files.",
        )
    if any(token in lower for token in ("ci", "check", "workflow", "label", "draft", "mergeable")):
        return (
            "ci_label_only_issue",
            "comment appears to target CI, labels, draft state, or mergeability",
            "Inspect PR checks/metadata; run local proof only if CI points to a reproducible failure.",
        )
    if "?" in body or any(token in lower for token in ("unclear", "which", "maybe", "could you", "can you")):
        return (
            "ambiguous_needs_human",
            "comment asks a question or leaves scope ambiguous",
            "Ask or draft a response before editing; no local proof yet.",
        )
    if any(token in lower for token in ("approve", "approved", "thanks", "nit:", "fyi", "note:")):
        return (
            "informational_no_local_change",
            "comment is approval, FYI, or low-action note",
            "No local proof required.",
        )
    return (
        "ambiguous_needs_human",
        "comment is not anchored and does not clearly identify a local change",
        "Classify manually before fetching patch context or editing.",
    )


def _addressing_status(item: dict[str, Any], category: str) -> str:
    if item.get("is_outdated") is True:
        return "outdated"
    if item.get("is_resolved") is True:
        return "already_addressed"
    if category == "ambiguous_needs_human":
        return "reply_only"
    if category in ACTIONABLE_CATEGORIES:
        return "unresolved_action"
    return "informational"


def _item_identity(item: dict[str, Any]) -> str:
    for key in ("url", "database_id", "databaseId", "id"):
        value = _text(item.get(key))
        if value:
            return value
    return _excerpt(_text(item.get("body")), limit=80)


def build_packet(payload: dict[str, Any], *, since: datetime | None = None, seen_urls: set[str] | None = None) -> dict[str, Any]:
    normalized = _normalize_graphql(payload)
    seen_urls = seen_urls or set()
    items: list[dict[str, Any]] = []
    skipped_old = 0
    skipped_seen = 0
    for raw in normalized.get("comments", []) or []:
        if not isinstance(raw, dict):
            continue
        created = _timestamp_value(raw)
        if since is not None and created is not None and created <= since:
            skipped_old += 1
            continue
        url = _text(raw.get("url"))
        if url and url in seen_urls:
            skipped_seen += 1
            continue
        category, reason, proof_hint = _classify(raw)
        addressing_status = _addressing_status(raw, category)
        item = {
            "id": _item_identity(raw),
            "kind": _text(raw.get("kind") or "comment"),
            "category": category,
            "addressing_status": addressing_status,
            "action_required": addressing_status in {"unresolved_action", "reply_only"},
            "reason": reason,
            "proof_hint": proof_hint,
            "url": url,
            "author": _author_login(raw.get("author")),
            "created_at": created.isoformat().replace("+00:00", "Z") if created else "",
            "body_excerpt": _excerpt(_text(raw.get("body"))),
        }
        for key in ("path", "line", "is_resolved", "is_outdated"):
            if key in raw and raw.get(key) not in (None, ""):
                item[key] = raw.get(key)
        items.append(item)

    counts = {category: 0 for category in CATEGORIES}
    for item in items:
        counts[item["category"]] += 1
    pagination = _as_pagination(normalized.get("pagination"))
    return {
        "kind": PACKET_KIND,
        "repository": normalized.get("repository") or "",
        "pr_number": normalized.get("pr_number") or "",
        "pr_url": normalized.get("pr_url") or "",
        "freshness": {
            "observed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "pr_head_sha": normalized.get("pr_head_sha") or "",
            "status": "current_at_observed_head" if normalized.get("pr_head_sha") else "baseline_only",
            "source": "gh-graphql-pr-head" if normalized.get("pr_head_sha") else "fixture-or-legacy-cache",
            "readiness_claim_rule": (
                "A no-actionable-comments result may support readiness only for the recorded PR head."
                if normalized.get("pr_head_sha")
                else "Refresh PR comments before readiness claims; this packet has no PR-head freshness proof."
            ),
        },
        "baseline": {
            "since": since.isoformat().replace("+00:00", "Z") if since else "",
            "seen_comment_url_count": len(seen_urls),
            "skipped_old_count": skipped_old,
            "skipped_seen_count": skipped_seen,
        },
        "new_comment_count": len(items),
        "category_counts": counts,
        "items": items,
        "pagination": pagination,
        "comment_surfaces": normalized.get("comment_surfaces", {}),
        "smallest_next_action": _smallest_next_action(counts, pagination=pagination),
        "write_safety": {
            "github_writes_performed": False,
            "rule": "Do not reply, resolve, or submit reviews from this packet without explicit user approval.",
        },
    }


def _as_pagination(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {
            "truncated": False,
            "truncated_surfaces": [],
            "limits": {
                "comments_first": ISSUE_COMMENT_LIMIT,
                "reviews_first": REVIEW_LIMIT,
                "review_threads_first": REVIEW_THREAD_LIMIT,
                "thread_comments_first": THREAD_COMMENT_LIMIT,
            },
            "rule": "When truncated is true, do not treat this packet as a complete review-comment delta.",
        }
    return {
        "truncated": bool(raw.get("truncated")),
        "truncated_surfaces": [str(item) for item in raw.get("truncated_surfaces", []) if str(item)],
        "limits": raw.get("limits") if isinstance(raw.get("limits"), dict) else {},
        "rule": str(raw.get("rule") or "When truncated is true, do not treat this packet as a complete review-comment delta."),
    }


def _smallest_next_action(counts: dict[str, int], *, pagination: dict[str, Any] | None = None) -> str:
    if pagination and pagination.get("truncated"):
        return "Fetch complete paginated PR comments before treating this packet as complete."
    if counts["ambiguous_needs_human"]:
        return "Clarify ambiguous comments before editing or fetching broad patch context."
    if counts["actionable_code_doc_body_change"]:
        return "Inspect the referenced files and implement focused fixes with matching proof."
    if counts["pr_metadata_body_only_change"]:
        return "Update PR metadata/body; avoid source edits unless generated metadata is checked in."
    if counts["ci_label_only_issue"]:
        return "Inspect checks or labels before local source proof."
    if counts["informational_no_local_change"]:
        return "No local change required."
    return "No new PR comment delta."


def _fetch_with_gh(*, repo: str, pr_number: int) -> dict[str, Any]:
    owner, name = repo.split("/", 1)
    query = """
query($owner: String!, $name: String!, $number: Int!) {
    repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      url
      headRefOid
      comments(first: 100) {
        nodes { databaseId url body createdAt updatedAt author { login } }
        pageInfo { hasNextPage endCursor }
      }
      reviews(first: 100) {
        nodes { databaseId url body state submittedAt author { login } }
        pageInfo { hasNextPage endCursor }
      }
      reviewThreads(first: 100) {
        pageInfo { hasNextPage endCursor }
        nodes {
          isResolved
          isOutdated
          comments(first: 20) {
            pageInfo { hasNextPage endCursor }
            nodes {
              databaseId
              url
              body
              createdAt
              updatedAt
              path
              line
              originalLine
              diffHunk
              author { login }
              replyTo { databaseId }
            }
          }
        }
      }
    }
  }
}
"""
    result = subprocess.run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"owner={owner}",
            "-f",
            f"name={name}",
            "-F",
            f"number={pr_number}",
            "-f",
            f"query={query}",
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "gh api graphql failed")
    payload = json.loads(result.stdout)
    payload["repository"] = repo
    payload["pr_number"] = pr_number
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--fixture", type=Path, help="Read normalized or GraphQL-like PR comment JSON from a file.")
    source.add_argument("--repo", help="GitHub repository in owner/name form; requires --pr.")
    parser.add_argument("--pr", type=int, help="Pull request number when fetching through gh.")
    parser.add_argument("--since", help="Only include comments created after this ISO timestamp.")
    parser.add_argument("--baseline-json", type=Path, help="JSON with seen_comment_urls to suppress already-seen comments.")
    parser.add_argument("--format", choices=("json",), default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.repo and args.pr is None:
        raise SystemExit("--repo requires --pr")
    payload = json.loads(args.fixture.read_text(encoding="utf-8")) if args.fixture else _fetch_with_gh(repo=args.repo, pr_number=args.pr)
    packet = build_packet(payload, since=_parse_timestamp(args.since), seen_urls=_baseline_seen_urls(args.baseline_json))
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
