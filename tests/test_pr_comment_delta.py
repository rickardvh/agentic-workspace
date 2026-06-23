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
    assert packet["category_counts"]["pr_metadata_body_only_change"] == 1
    assert packet["category_counts"]["actionable_code_doc_body_change"] == 1
    assert packet["category_counts"]["ci_label_only_issue"] == 1
    assert packet["category_counts"]["ambiguous_needs_human"] == 1
    assert packet["category_counts"]["informational_no_local_change"] == 1
    closure = next(item for item in packet["items"] if item["url"].endswith("#closure"))
    assert closure["category"] == "pr_metadata_body_only_change"
    assert "no source proof" in closure["proof_hint"].lower()
    anchored = next(item for item in packet["items"] if item["url"].endswith("#code"))
    assert anchored["path"] == "tests/test_widget.py"
    assert "focused tests" in anchored["proof_hint"]


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
                    "comments": {"nodes": []},
                    "reviews": {"nodes": []},
                    "reviewThreads": {
                        "nodes": [
                            {
                                "isResolved": False,
                                "isOutdated": False,
                                "comments": {
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
                                    ]
                                },
                            }
                        ]
                    },
                }
            }
        },
    }

    packet = module.build_packet(payload)

    assert packet["new_comment_count"] == 1
    item = packet["items"][0]
    assert item["kind"] == "review_thread_comment"
    assert item["category"] == "actionable_code_doc_body_change"
    assert item["path"] == "src/app.py"
    assert item["line"] == 12


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


def test_pr_comment_delta_readme_keeps_live_workflow_discoverable() -> None:
    text = README.read_text(encoding="utf-8")

    assert "agentic-workspace/pr-comment-delta/v1" in text
    assert "uv run python scripts/github/pr_comment_delta.py" in text
    assert "--baseline-json" in text
    assert "does not write to GitHub" in text
