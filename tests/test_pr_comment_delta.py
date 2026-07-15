from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "github" / "pr_comment_delta.py"
README = REPO_ROOT / "scripts" / "github" / "README.md"


def _load_module():
    spec = importlib.util.spec_from_file_location("pr_comment_delta", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fixture() -> dict:
    return {
        "repository": "rickardvh/agentic-workspace",
        "pr_number": 1689,
        "pr_url": "https://github.com/rickardvh/agentic-workspace/pull/1689",
        "comments": [
            {
                "kind": "issue_comment",
                "database_id": 1,
                "url": "https://example.test/pr#old",
                "body": "Old note",
                "created_at": "2026-06-22T10:00:00Z",
                "author": {"login": "maintainer"},
            },
            {
                "kind": "issue_comment",
                "database_id": 2,
                "url": "https://example.test/pr#closure",
                "body": "Please stop closing #1680 in the PR body and reframe this as a slice.",
                "created_at": "2026-06-23T10:00:00Z",
                "author": {"login": "maintainer"},
            },
            {
                "kind": "review_thread_comment",
                "database_id": 3,
                "url": "https://example.test/pr#code",
                "body": "This assertion should cover the empty state.",
                "created_at": "2026-06-23T10:01:00Z",
                "author": {"login": "reviewer"},
                "path": "tests/test_widget.py",
                "line": 42,
                "is_resolved": False,
                "is_outdated": False,
            },
            {
                "kind": "issue_comment",
                "database_id": 4,
                "url": "https://example.test/pr#ci",
                "body": "The CI check is failing on Windows.",
                "created_at": "2026-06-23T10:02:00Z",
                "author": {"login": "reviewer"},
            },
            {
                "kind": "issue_comment",
                "database_id": 5,
                "url": "https://example.test/pr#question",
                "body": "Which behavior should win here?",
                "created_at": "2026-06-23T10:03:00Z",
                "author": {"login": "reviewer"},
            },
            {
                "kind": "review_thread_comment",
                "database_id": 6,
                "url": "https://example.test/pr#resolved",
                "body": "Resolved nit.",
                "created_at": "2026-06-23T10:04:00Z",
                "author": {"login": "reviewer"},
                "path": "README.md",
                "is_resolved": True,
            },
        ],
    }


def test_pr_comment_delta_classifies_new_review_response_scope() -> None:
    module = _load_module()
    packet = module.build_packet(_fixture(), since=module._parse_timestamp("2026-06-23T09:59:00Z"))

    assert packet["kind"] == "agentic-workspace/pr-comment-delta/v1"
    assert packet["new_comment_count"] == 5
    assert packet["freshness"]["status"] == "baseline_only"
    assert packet["freshness"]["readiness_claim_rule"].startswith("Refresh PR comments")
    assert packet["category_counts"]["pr_metadata_body_only_change"] == 1
    assert packet["category_counts"]["actionable_code_doc_body_change"] == 1
    assert packet["category_counts"]["ci_label_only_issue"] == 1
    assert packet["category_counts"]["ambiguous_needs_human"] == 1
    assert packet["category_counts"]["informational_no_local_change"] == 1
    assert packet["comment_surfaces"]["inspected"] == ["normalized_comments"]
    assert packet["comment_surfaces"]["unavailable"] == ["thread_surface_completeness"]
    closure = next(item for item in packet["items"] if item["url"].endswith("#closure"))
    assert closure["category"] == "pr_metadata_body_only_change"
    assert "no source proof" in closure["proof_hint"].lower()
    anchored = next(item for item in packet["items"] if item["url"].endswith("#code"))
    assert anchored["path"] == "tests/test_widget.py"
    assert anchored["addressing_status"] == "unresolved_action"
    assert anchored["action_required"] is True
    assert "focused tests" in anchored["proof_hint"]
    question = next(item for item in packet["items"] if item["url"].endswith("#question"))
    assert question["addressing_status"] == "reply_only"
    resolved = next(item for item in packet["items"] if item["url"].endswith("#resolved"))
    assert resolved["addressing_status"] == "already_addressed"


def test_pr_comment_delta_prioritizes_source_change_evidence_over_closure_metadata() -> None:
    module = _load_module()
    payload = _fixture()
    payload["comments"] = [
        {
            "kind": "issue_comment",
            "database_id": 7,
            "url": "https://example.test/pr#mixed-review",
            "body": (
                "Changes needed before this PR should close the lane. "
                "`repair_session_log_index()` preserves stale entries and `_segment_metadata()` uses an over-broad test. "
                "Remove or quarantine the extras and add focused negative tests. Closes #2142 only after both fixes."
            ),
            "created_at": "2026-06-23T10:05:00Z",
            "author": {"login": "maintainer"},
        }
    ]

    packet = module.build_packet(payload)

    item = packet["items"][0]
    assert item["category"] == "actionable_code_doc_body_change"
    assert item["addressing_status"] == "unresolved_action"
    assert "source and test surfaces" in item["proof_hint"]
    assert packet["smallest_next_action"] == "Inspect the referenced files and implement focused fixes with matching proof."


def test_pr_comment_delta_keeps_ready_recheck_summaries_informational() -> None:
    module = _load_module()

    category, reason, proof_hint = module._classify(
        {
            "kind": "review",
            "body": (
                "Recheck result: ready. Previous blockers resolved: stale entries were removed and focused tests now pass. "
                "No remaining review blocker found."
            ),
        }
    )

    assert category == "informational_no_local_change"
    assert "readiness" in reason
    assert proof_hint.startswith("No local proof required")


def test_pr_comment_delta_uses_structured_blocker_before_next_action_prose() -> None:
    module = _load_module()

    category, reason, proof_hint = module._classify(
        {
            "kind": "issue_comment",
            "body": (
                "decision: blocked\n"
                "unresolved: The PR remains a draft and the PR Semver Label workflow is stale.\n"
                "next_action: Update `scripts/github/pr_comment_delta.py` and then mark the PR ready.\n"
                "<!-- aw-chatgpt-review decision=blocked -->"
            ),
        }
    )

    assert category == "ci_label_only_issue"
    assert "structured blocked" in reason
    assert proof_hint.startswith("Inspect PR checks/metadata")


def test_pr_comment_delta_keeps_structured_source_blockers_actionable() -> None:
    module = _load_module()

    category, _, proof_hint = module._classify(
        {
            "kind": "issue_comment",
            "body": (
                "decision: blocked\n"
                "unresolved: Update scripts/github/pr_comment_delta.py and add a focused regression test.\n"
                "next_action: Mark the PR ready after the proof passes.\n"
                "<!-- aw-chatgpt-review decision=blocked -->"
            ),
        }
    )

    assert category == "actionable_code_doc_body_change"
    assert "source and test surfaces" in proof_hint


def test_pr_comment_delta_marks_inconsistent_structured_status_ambiguous() -> None:
    module = _load_module()

    category, reason, _ = module._classify(
        {
            "kind": "issue_comment",
            "body": (
                "decision: blocked\n"
                "unresolved: PR draft state remains.\n"
                "next_action: Mark ready.\n"
                "<!-- aw-chatgpt-review decision=ready -->"
            ),
        }
    )

    assert category == "ambiguous_needs_human"
    assert "inconsistent" in reason


def test_pr_comment_delta_filters_seen_comment_urls(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"seen_comment_urls": ["https://example.test/pr#ci"]}), encoding="utf-8")

    packet = module.build_packet(
        _fixture(),
        since=module._parse_timestamp("2026-06-23T09:59:00Z"),
        seen_urls=module._baseline_seen_urls(baseline),
    )

    assert packet["baseline"]["skipped_seen_count"] == 1
    assert all(not item["url"].endswith("#ci") for item in packet["items"])


def test_pr_comment_delta_normalizes_graphql_review_threads() -> None:
    module = _load_module()
    payload = {
        "repository": "rickardvh/agentic-workspace",
        "pr_number": 42,
        "data": {
            "repository": {
                "pullRequest": {
                    "url": "https://github.com/rickardvh/agentic-workspace/pull/42",
                    "headRefOid": "abc123",
                    "comments": {"nodes": []},
                    "reviews": {"nodes": []},
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": False},
                        "nodes": [
                            {
                                "isResolved": False,
                                "isOutdated": False,
                                "comments": {
                                    "pageInfo": {"hasNextPage": False},
                                    "nodes": [
                                        {
                                            "databaseId": 99,
                                            "url": "https://example.test/pr#thread",
                                            "body": "Please update this branch.",
                                            "createdAt": "2026-06-23T11:00:00Z",
                                            "path": "src/app.py",
                                            "line": 12,
                                            "author": {"login": "reviewer"},
                                            "replyTo": None,
                                        }
                                    ],
                                },
                            }
                        ],
                    },
                }
            }
        },
    }

    packet = module.build_packet(payload)

    assert packet["new_comment_count"] == 1
    assert packet["freshness"]["status"] == "current_at_observed_head"
    assert packet["freshness"]["pr_head_sha"] == "abc123"
    assert packet["comment_surfaces"]["inspected"] == ["issue_comments", "reviews", "review_threads"]
    assert packet["comment_surfaces"]["unavailable"] == []
    item = packet["items"][0]
    assert item["kind"] == "review_thread_comment"
    assert item["category"] == "actionable_code_doc_body_change"
    assert item["addressing_status"] == "unresolved_action"
    assert item["path"] == "src/app.py"
    assert item["line"] == 12


def test_pr_comment_delta_separates_outdated_threads_from_addressed_threads() -> None:
    module = _load_module()
    packet = module.build_packet(
        {
            "repository": "rickardvh/agentic-workspace",
            "pr_number": 42,
            "comments": [
                {
                    "kind": "review_thread_comment",
                    "url": "https://example.test/pr#outdated",
                    "body": "Old inline note",
                    "created_at": "2026-06-23T11:00:00Z",
                    "path": "src/app.py",
                    "is_resolved": False,
                    "is_outdated": True,
                },
                {
                    "kind": "review_thread_comment",
                    "url": "https://example.test/pr#resolved",
                    "body": "Handled inline note",
                    "created_at": "2026-06-23T11:01:00Z",
                    "path": "src/app.py",
                    "is_resolved": True,
                    "is_outdated": False,
                },
            ],
        }
    )

    statuses = {item["url"].split("#")[-1]: item["addressing_status"] for item in packet["items"]}
    assert statuses == {"outdated": "outdated", "resolved": "already_addressed"}
    assert all(item["action_required"] is False for item in packet["items"])


def test_pr_comment_delta_reports_graphql_truncation_boundaries() -> None:
    module = _load_module()
    payload = {
        "repository": "rickardvh/agentic-workspace",
        "pr_number": 43,
        "data": {
            "repository": {
                "pullRequest": {
                    "url": "https://github.com/rickardvh/agentic-workspace/pull/43",
                    "comments": {
                        "pageInfo": {"hasNextPage": True, "endCursor": "issue-cursor"},
                        "nodes": [],
                    },
                    "reviews": {
                        "pageInfo": {"hasNextPage": False},
                        "nodes": [],
                    },
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": True, "endCursor": "thread-cursor"},
                        "nodes": [
                            {
                                "isResolved": False,
                                "isOutdated": False,
                                "comments": {
                                    "pageInfo": {"hasNextPage": True, "endCursor": "comment-cursor"},
                                    "nodes": [
                                        {
                                            "databaseId": 100,
                                            "url": "https://example.test/pr#thread",
                                            "body": "Please update this branch.",
                                            "createdAt": "2026-06-23T11:00:00Z",
                                            "path": "src/app.py",
                                            "line": 12,
                                            "author": {"login": "reviewer"},
                                            "replyTo": None,
                                        }
                                    ],
                                },
                            }
                        ],
                    },
                }
            }
        },
    }

    packet = module.build_packet(payload)

    assert packet["pagination"]["truncated"] is True
    assert packet["pagination"]["truncated_surfaces"] == [
        "comments",
        "reviewThreads",
        "reviewThreads[0].comments",
    ]
    assert packet["pagination"]["limits"] == {
        "comments_first": 100,
        "reviews_first": 100,
        "review_threads_first": 100,
        "thread_comments_first": 20,
    }
    assert packet["smallest_next_action"] == "Fetch complete paginated PR comments before treating this packet as complete."


def test_pr_comment_delta_cli_reads_fixture(tmp_path: Path) -> None:
    fixture_path = tmp_path / "comments.json"
    fixture_path.write_text(json.dumps(_fixture()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--fixture",
            str(fixture_path),
            "--since",
            "2026-06-23T09:59:00Z",
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
    assert packet["repository"] == "rickardvh/agentic-workspace"
    assert packet["pr_number"] == 1689
    assert packet["smallest_next_action"] == "Clarify ambiguous comments before editing or fetching broad patch context."


def test_pr_comment_delta_fetch_forces_utf8_subprocess_decoding(monkeypatch) -> None:
    module = _load_module()
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed["command"] = command
        observed["encoding"] = kwargs.get("encoding")
        observed["errors"] = kwargs.get("errors")
        payload = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "url": "https://github.com/rickardvh/agentic-workspace/pull/1893",
                        "headRefOid": "abc123",
                        "comments": {
                            "nodes": [
                                {
                                    "databaseId": 1,
                                    "url": "https://example.test/pr#unicode",
                                    "body": "Please keep the snowman \u2603 in the body.",
                                    "createdAt": "2026-06-29T21:00:00Z",
                                    "author": {"login": "reviewer"},
                                }
                            ],
                            "pageInfo": {"hasNextPage": False},
                        },
                        "reviews": {"nodes": [], "pageInfo": {"hasNextPage": False}},
                        "reviewThreads": {"nodes": [], "pageInfo": {"hasNextPage": False}},
                    }
                }
            }
        }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload, ensure_ascii=False), stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    payload = module._fetch_with_gh(repo="rickardvh/agentic-workspace", pr_number=1893)

    assert observed["encoding"] == "utf-8"
    assert observed["errors"] == "replace"
    assert payload["repository"] == "rickardvh/agentic-workspace"
    assert "snowman" in payload["data"]["repository"]["pullRequest"]["comments"]["nodes"][0]["body"]


def test_pr_comment_delta_readme_keeps_live_workflow_discoverable() -> None:
    text = README.read_text(encoding="utf-8")

    assert "agentic-workspace/pr-comment-delta/v1" in text
    assert "uv run python scripts/github/pr_comment_delta.py" in text
    assert "--baseline-json" in text
    assert "pagination.truncated" in text
    assert "does not write to GitHub" in text
