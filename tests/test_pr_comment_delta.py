from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "github" / "pr_comment_delta.py"
README = REPO_ROOT / "scripts" / "github" / "README.md"
REVIEW_HEAD = "a" * 40
PR2746_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "pr_review_intake" / "pr2746.json"


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


def _complete_review_payload(*, comments=None, reviews=None, threads=None, checks=None, head: str = REVIEW_HEAD) -> dict:
    return {
        "repository": "rickardvh/agentic-workspace",
        "pr_number": 99,
        "data": {
            "repository": {
                "pullRequest": {
                    "url": "https://github.com/rickardvh/agentic-workspace/pull/99",
                    "headRefOid": head,
                    "updatedAt": "2026-08-26T12:00:00Z",
                    "comments": {"pageInfo": {"hasNextPage": False}, "nodes": comments or []},
                    "reviews": {"pageInfo": {"hasNextPage": False}, "nodes": reviews or []},
                    "reviewThreads": {"pageInfo": {"hasNextPage": False}, "nodes": threads or []},
                    "commits": {
                        "nodes": [
                            {
                                "commit": {
                                    "committedDate": "2026-08-26T10:00:00Z",
                                    "statusCheckRollup": {"contexts": {"pageInfo": {"hasNextPage": False}, "nodes": checks or []}},
                                }
                            }
                        ]
                    },
                }
            }
        },
    }


def _structured_review_body(
    *,
    decision: str = "blocked",
    marker_decision: str | None = None,
    unresolved: str,
    next_action: str = "Refresh the PR after the structured blocker is resolved.",
    closure_honest: str = "no",
) -> str:
    marker = marker_decision or decision
    return (
        f"decision: {decision}\n"
        "what_landed:\n"
        "- Rechecked the exact PR head against the current review policy.\n"
        "\n"
        "intent_served:\n"
        "- Preserve the linked issue intent and proof boundary.\n"
        "\n"
        "proof:\n"
        "- Focused review completed against the current head.\n"
        "\n"
        "unresolved:\n"
        f"{unresolved}\n"
        "\n"
        f"closure_honest: {closure_honest}\n"
        "\n"
        "next_action:\n"
        f"{next_action}\n"
        "\n"
        f"<!-- aw-chatgpt-review pr=2329 head={REVIEW_HEAD} policy=pr-review-recheck-v1 decision={marker} -->"
    )


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


def test_pr_comment_delta_uses_multiline_structured_blocker_before_next_action_prose() -> None:
    module = _load_module()

    category, reason, proof_hint = module._classify(
        {
            "kind": "issue_comment",
            "body": _structured_review_body(
                unresolved=(
                    "1. The PR remains a draft.\n2. The PR Semver Label workflow is stale.\n3. Required CI checks are still pending."
                ),
                next_action=(
                    "Update `scripts/github/pr_comment_delta.py` if source changes become necessary, "
                    "then mark the PR ready after checks and labels are correct."
                ),
            ),
        }
    )

    assert category == "ci_label_only_issue"
    assert "structured blocked" in reason
    assert proof_hint.startswith("Inspect PR checks/metadata")


def test_pr_comment_delta_keeps_multiline_structured_source_blockers_actionable() -> None:
    module = _load_module()

    category, _, proof_hint = module._classify(
        {
            "kind": "issue_comment",
            "body": _structured_review_body(
                unresolved=(
                    "1. `scripts/github/pr_comment_delta.py` only captures one-line review fields.\n"
                    "2. Add a focused regression test in tests/test_pr_comment_delta.py for multiline review bodies."
                ),
                next_action="Mark the PR ready after the proof passes.",
            ),
        }
    )

    assert category == "actionable_code_doc_body_change"
    assert "source and test surfaces" in proof_hint


def test_pr_comment_delta_keeps_canonical_merge_ready_informational() -> None:
    module = _load_module()

    category, reason, proof_hint = module._classify(
        {
            "kind": "issue_comment",
            "body": _structured_review_body(
                decision="merge-ready",
                unresolved="- none",
                closure_honest="yes",
                next_action="No local action; the human retains merge authority.",
            ),
        }
    )

    assert category == "informational_no_local_change"
    assert "readiness" in reason
    assert proof_hint.startswith("No local proof required")


def test_pr_comment_delta_marks_legacy_ready_structured_status_ambiguous() -> None:
    module = _load_module()

    category, reason, _ = module._classify(
        {
            "kind": "issue_comment",
            "body": _structured_review_body(
                decision="ready",
                marker_decision="merge-ready",
                unresolved="- none",
                closure_honest="yes",
                next_action="No local action.",
            ),
        }
    )

    assert category == "ambiguous_needs_human"
    assert "unsupported" in reason


def test_pr_comment_delta_marks_missing_structured_marker_or_header_ambiguous() -> None:
    module = _load_module()

    missing_marker, marker_reason, _ = module._classify(
        {
            "kind": "issue_comment",
            "body": _structured_review_body(
                unresolved="1. PR draft state remains.",
                next_action="Mark ready after metadata is fixed.",
            ).split("\n<!-- aw-chatgpt-review", 1)[0],
        }
    )
    missing_unresolved, unresolved_reason, _ = module._classify(
        {
            "kind": "issue_comment",
            "body": (
                "decision: blocked\n"
                "next_action:\n"
                "Mark ready after metadata is fixed.\n"
                f"<!-- aw-chatgpt-review pr=2329 head={REVIEW_HEAD} policy=pr-review-recheck-v1 decision=blocked -->"
            ),
        }
    )

    assert missing_marker == "ambiguous_needs_human"
    assert "missing required fields" in marker_reason
    assert missing_unresolved == "ambiguous_needs_human"
    assert "missing required fields" in unresolved_reason


def test_pr_comment_delta_marks_duplicate_required_structured_fields_ambiguous() -> None:
    module = _load_module()

    body = _structured_review_body(
        unresolved="1. PR draft state remains.",
        next_action="Mark ready after metadata is fixed.",
    ).replace(
        "\nclosure_honest:",
        "\nunresolved:\n2. Duplicate unresolved section should force manual inspection.\n\nclosure_honest:",
    )

    category, reason, _ = module._classify({"kind": "issue_comment", "body": body})

    assert category == "ambiguous_needs_human"
    assert "missing required fields" in reason


def test_pr_comment_delta_marks_inconsistent_structured_status_ambiguous() -> None:
    module = _load_module()

    category, reason, _ = module._classify(
        {
            "kind": "issue_comment",
            "body": _structured_review_body(
                marker_decision="merge-ready",
                unresolved="1. PR draft state remains.",
                next_action="Mark ready.",
            ),
        }
    )

    assert category == "ambiguous_needs_human"
    assert "conflicting" in reason


def test_pr_comment_delta_uses_structured_unresolved_for_mixed_blocker_lists() -> None:
    module = _load_module()

    category, reason, proof_hint = module._classify(
        {
            "kind": "issue_comment",
            "body": _structured_review_body(
                unresolved=(
                    "1. The PR remains a draft.\n"
                    "2. Update scripts/github/pr_comment_delta.py so multiline structured fields parse correctly.\n"
                    "3. Add a focused regression test before claiming the blocker is resolved."
                ),
                next_action="Fix labels only after the source blocker is handled.",
            ),
        }
    )

    assert category == "actionable_code_doc_body_change"
    assert "structured blocked" in reason
    assert "source and test surfaces" in proof_hint


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


def test_pr2746_complete_intake_finds_top_level_blocker_and_preserves_independent_authority() -> None:
    module = _load_module()
    packet = module.build_packet(
        json.loads(PR2746_FIXTURE.read_text(encoding="utf-8")),
        referenced_comment_ids={"5425598890"},
    )

    intake = packet["review_intake"]
    assert intake["status"] == "complete"
    assert intake["classification"] == "ready_for_re_review_distinct_authority"
    assert intake["found_referenced_comment_ids"] == ["5425598890"]
    assert intake["referenced_items"][0]["kind"] == "issue_comment"
    assert intake["hosted_check_failures"][0]["name"] == "Review approval"
    assert intake["independent_review_authority"] == {
        "implementation_agent_eligible": False,
        "merge_ready_authority": False,
        "owner": "tools/skills/pr-review-recheck/SKILL.md",
        "rule": "Complete intake may support fixes-applied / ready-for-re-review reporting; it never grants self-approval or merge-ready authority.",
    }
    assert intake["history_residue"] == {"checked_in_ledger_created": False, "full_history_dumped": False}
    assert intake["tool_call_comparison"]["human_surface_redirection_required"] is False
    assert len(intake["tool_call_comparison"]["after"]) == 1


def test_complete_intake_classifies_submitted_review_and_inline_patch_requests() -> None:
    module = _load_module()
    review_packet = module.build_packet(
        _complete_review_payload(
            reviews=[
                {
                    "databaseId": 7,
                    "url": "https://example.test/review/7",
                    "body": "Please update src/app.py and add a focused test.",
                    "state": "CHANGES_REQUESTED",
                    "submittedAt": "2026-08-26T11:00:00Z",
                    "author": {"login": "reviewer"},
                    "commit": {"oid": REVIEW_HEAD},
                }
            ]
        )
    )
    assert review_packet["review_intake"]["classification"] == "patch_changes_requested"
    assert review_packet["items"][0]["kind"] == "review"

    inline_packet = module.build_packet(
        _complete_review_payload(
            threads=[
                {
                    "isResolved": False,
                    "isOutdated": False,
                    "comments": {
                        "pageInfo": {"hasNextPage": False},
                        "nodes": [
                            {
                                "databaseId": 8,
                                "url": "https://example.test/thread/8",
                                "body": "Please fix this assertion.",
                                "createdAt": "2026-08-26T11:00:00Z",
                                "path": "tests/test_app.py",
                                "line": 8,
                                "author": {"login": "reviewer"},
                                "commit": {"oid": REVIEW_HEAD},
                            }
                        ],
                    },
                }
            ]
        )
    )
    assert inline_packet["review_intake"]["classification"] == "patch_changes_requested"
    assert inline_packet["items"][0]["kind"] == "review_thread_comment"


def test_complete_intake_distinguishes_stale_blocker_hosted_failure_and_clean_state() -> None:
    module = _load_module()
    old_head = "b" * 40
    stale = module.build_packet(
        _complete_review_payload(
            comments=[
                {
                    "databaseId": 9,
                    "url": "https://example.test/comment/9",
                    "body": f"Please update src/app.py. <!-- aw-chatgpt-review pr=99 head={old_head} policy=pr-review-recheck-v1 decision=blocked -->",
                    "createdAt": "2026-08-25T11:00:00Z",
                    "author": {"login": "reviewer"},
                }
            ]
        )
    )
    assert stale["review_intake"]["classification"] == "stale_superseded_comment"
    assert stale["items"][0]["implementation_posture"] == "stale_superseded_comment"
    assert stale["items"][0]["action_required"] is False

    failed = module.build_packet(_complete_review_payload(checks=[{"name": "windows", "status": "COMPLETED", "conclusion": "FAILURE"}]))
    assert failed["review_intake"]["classification"] == "hosted_check_failure"
    assert failed["new_comment_count"] == 0

    clean = module.build_packet(_complete_review_payload())
    assert clean["review_intake"]["classification"] == "no_current_blocker"
    assert clean["review_intake"]["status"] == "complete"


def test_exact_head_resolution_notes_link_prior_findings_without_reopening_actions() -> None:
    module = _load_module()
    old_head = "b" * 40
    payload = _complete_review_payload(
        comments=[
            {
                "databaseId": 21,
                "url": "https://example.test/comment/21",
                "body": f"Please update src/app.py. <!-- aw-chatgpt-review pr=99 head={old_head} policy=pr-review-recheck-v1 decision=blocked -->",
                "createdAt": "2026-08-25T11:00:00Z",
                "author": {"login": "reviewer"},
            },
            {
                "databaseId": 22,
                "url": "https://example.test/comment/22",
                "body": f"Addressed at this head; ready for re-review. <!-- aw-chatgpt-review pr=99 head={REVIEW_HEAD} policy=pr-review-recheck-v1 decision=merge-ready -->",
                "createdAt": "2026-08-26T11:00:00Z",
                "author": {"login": "author"},
            },
        ],
        reviews=[
            {
                "databaseId": 23,
                "url": "https://example.test/review/23",
                "body": f"Resolved at this head; no remaining review blocker. <!-- aw-chatgpt-review pr=99 head={REVIEW_HEAD} policy=pr-review-recheck-v1 decision=merge-ready -->",
                "state": "COMMENTED",
                "submittedAt": "2026-08-26T11:01:00Z",
                "author": {"login": "author"},
                "commit": {"oid": REVIEW_HEAD},
            }
        ],
        threads=[
            {
                "isResolved": False,
                "isOutdated": False,
                "comments": {
                    "pageInfo": {"hasNextPage": False},
                    "nodes": [
                        {
                            "databaseId": 24,
                            "url": "https://example.test/thread/24",
                            "body": "Fixed at this head; ready for re-review.",
                            "createdAt": "2026-08-26T11:02:00Z",
                            "path": "src/app.py",
                            "author": {"login": "author"},
                            "replyTo": {"databaseId": 21},
                            "commit": {"oid": REVIEW_HEAD},
                        }
                    ],
                },
            }
        ],
    )

    packet = module.build_packet(payload)
    assert packet["category_counts"]["actionable_code_doc_body_change"] == 0
    assert all(item["action_required"] is False for item in packet["items"])
    resolutions = [item for item in packet["items"] if item.get("resolution_of")]
    assert {item["kind"] for item in resolutions} == {"issue_comment", "review", "review_thread_comment"}
    assert all(item["addressing_status"] == "already_addressed" for item in resolutions)


def test_exact_head_resolution_wording_with_new_request_remains_actionable() -> None:
    module = _load_module()
    packet = module.build_packet(
        _complete_review_payload(
            comments=[
                {
                    "databaseId": 25,
                    "url": "https://example.test/comment/25",
                    "body": f"Fixes applied on exact head `{REVIEW_HEAD}`; ready for fresh re-review; please also update src/new.py.",
                    "createdAt": "2026-08-26T11:00:00Z",
                    "author": {"login": "reviewer"},
                }
            ]
        )
    )

    assert packet["items"][0]["addressing_status"] == "unresolved_action"
    assert packet["items"][0]["action_required"] is True


def test_pr2887_replay_treats_prose_resolution_and_merge_ready_verdict_as_evidence() -> None:
    module = _load_module()
    old_head = "b" * 40
    packet = module.build_packet(
        _complete_review_payload(
            comments=[
                {
                    "databaseId": 26,
                    "url": "https://example.test/comment/26",
                    "body": (
                        "decision: blocked\n"
                        "unresolved:\n"
                        "Update scripts/github/pr_comment_delta.py and add a focused regression test.\n"
                        f"<!-- aw-chatgpt-review pr=99 head={old_head} policy=pr-review-recheck-v1 decision=blocked -->"
                    ),
                    "createdAt": "2026-08-25T11:00:00Z",
                    "author": {"login": "reviewer"},
                },
                {
                    "databaseId": 27,
                    "url": "https://example.test/comment/27",
                    "body": f"Fixes applied on exact head `{REVIEW_HEAD}`; ready for fresh re-review.",
                    "createdAt": "2026-08-26T11:00:00Z",
                    "author": {"login": "author"},
                },
                {
                    "databaseId": 28,
                    "url": "https://example.test/comment/28",
                    "body": (
                        "decision: merge-ready\n\n"
                        f"Exact head `{REVIEW_HEAD}` is merge-ready. The prior blockers are resolved.\n\n"
                        "closure_honest: yes\n\n"
                        "next_action: merge this exact head.\n\n"
                        f"<!-- aw-chatgpt-review pr=99 head={REVIEW_HEAD} policy=pr-review-recheck-v1 decision=merge-ready -->"
                    ),
                    "createdAt": "2026-08-26T11:01:00Z",
                    "author": {"login": "independent-reviewer"},
                },
            ]
        )
    )

    assert packet["review_intake"]["status"] == "complete"
    assert packet["review_intake"]["classification"] == "stale_superseded_comment"
    assert all(item["action_required"] is False for item in packet["items"])
    resolution = next(item for item in packet["items"] if item["database_id"] == "27")
    verdict = next(item for item in packet["items"] if item["database_id"] == "28")
    assert resolution["addressing_status"] == "already_addressed"
    assert resolution["resolution_of"] == ["https://example.test/comment/26"]
    assert verdict["category"] == "informational_no_local_change"
    assert verdict["addressing_status"] == "informational"
    assert packet["review_intake"]["independent_review_authority"]["implementation_agent_eligible"] is False
    assert packet["review_intake"]["independent_review_authority"]["merge_ready_authority"] is False


def test_complete_intake_treats_markerless_top_level_blocker_after_head_as_current() -> None:
    module = _load_module()
    packet = module.build_packet(
        _complete_review_payload(
            comments=[
                {
                    "databaseId": 10,
                    "url": "https://example.test/comment/10",
                    "body": "Please update src/app.py and add a regression test.",
                    "createdAt": "2026-08-26T11:00:00Z",
                    "author": {"login": "reviewer"},
                }
            ]
        )
    )

    assert packet["review_intake"]["classification"] == "patch_changes_requested"
    assert packet["items"][0]["currentness"] == "current"


def test_complete_intake_treats_markerless_prior_head_blocker_as_stale_with_later_review_evidence() -> None:
    module = _load_module()
    packet = module.build_packet(
        _complete_review_payload(
            comments=[
                {
                    "databaseId": 11,
                    "url": "https://example.test/comment/11",
                    "body": "Please update src/app.py and add a regression test.",
                    "createdAt": "2026-08-26T09:00:00Z",
                    "author": {"login": "reviewer"},
                }
            ],
            reviews=[
                {
                    "databaseId": 12,
                    "url": "https://example.test/review/12",
                    "body": "Recheck result: ready; no remaining review blocker.",
                    "state": "APPROVED",
                    "submittedAt": "2026-08-26T11:00:00Z",
                    "author": {"login": "independent-reviewer"},
                    "commit": {"oid": REVIEW_HEAD},
                }
            ],
        )
    )

    assert packet["review_intake"]["classification"] == "stale_superseded_comment"
    assert packet["items"][0]["currentness"] == "stale"


def test_referenced_markerless_comment_with_unknown_head_fails_closed() -> None:
    module = _load_module()
    payload = _complete_review_payload(
        comments=[
            {
                "databaseId": 13,
                "url": "https://example.test/comment/13",
                "body": "Please update src/app.py and add a regression test.",
                "createdAt": "2026-08-26T09:00:00Z",
                "author": {"login": "reviewer"},
            }
        ]
    )
    del payload["data"]["repository"]["pullRequest"]["commits"]["nodes"][0]["commit"]["committedDate"]
    packet = module.build_packet(payload, referenced_comment_ids={"13"})

    assert packet["review_intake"]["status"] == "incomplete"
    assert packet["review_intake"]["classification"] == "currentness_unresolved"
    assert packet["review_intake"]["incomplete_surfaces"] == ["ordinary_comment_currentness"]
    assert packet["review_intake"]["currentness_unresolved_items"][0]["database_id"] == "13"


def test_missing_referenced_blocker_fails_closed_when_any_surface_is_incomplete() -> None:
    module = _load_module()
    payload = _complete_review_payload()
    del payload["data"]["repository"]["pullRequest"]["commits"]
    packet = module.build_packet(payload, referenced_comment_ids={"5425598890"})

    assert packet["review_intake"]["status"] == "incomplete"
    assert packet["review_intake"]["classification"] == "intake_incomplete"
    assert packet["review_intake"]["incomplete_surfaces"] == ["hosted_checks"]
    assert packet["review_intake"]["missing_referenced_comment_ids"] == ["5425598890"]


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
