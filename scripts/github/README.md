# GitHub Helpers

This directory holds read-only helpers for GitHub review and maintainer workflows.

## PR Topology Admission

When AW reports that stack topology is unavailable, use the routed
`pr_topology.py` command to perform one bounded, read-only GitHub lookup and
admit its repository/branch/head-bound result into the existing local review
stack owner:

```powershell
uv run python scripts/github/pr_topology.py `
  --repo rickardvh/agentic-workspace `
  --branch codex/example-stack-head `
  --target . `
  --format json
```

The admitted result supplies PR identity and dependency order only. It does
not prove review-thread freshness, absence of comments, or stack readiness.
Ordinary unrelated startup remains network-quiet; this adapter runs only when
the agent explicitly follows the PR-topology recovery route.

## PR Comment Delta Packet

Use `pr_comment_delta.py` at the start of a review-response turn when a PR may have new comments, reviews, or inline review threads. The helper emits `agentic-workspace/pr-comment-delta/v1` so the next action can stay narrow:

- inline review comments with a file path become focused code/doc changes;
- PR title/body/closure comments stay metadata-only;
- CI, label, draft, or mergeability comments route to PR checks or metadata first;
- ambiguous comments route to clarification instead of broad local edits;
- resolved or outdated threads become informational.

Each item also carries an `addressing_status` so AW report/startup can derive a closeout packet without rereading raw comments:

- `unresolved_action` needs a code, docs, metadata, or checks action;
- `reply_only` needs clarification or a human response before local edits;
- `already_addressed` was resolved in the inspected thread evidence;
- `outdated` was superseded by later diff state;
- `informational` does not require local action.

The packet includes `comment_surfaces` and `review_intake` so closeout can distinguish complete GraphQL reads from incomplete fixtures or caches. A complete implementation-side intake covers top-level issue comments, submitted reviews, inline review threads, hosted checks, and current-head ordering. If any required surface is unavailable or truncated, `review_intake.status` is `incomplete`; consumers must not conclude that a referenced blocker is absent.

Use `--referenced-comment <database-id>` when the user names a particular blocker. The bounded result reports whether that comment was found and classifies the current implementation posture as patch changes requested, ready for re-review/distinct authority required, hosted-check failure, stale/superseded, incomplete, or clean. Hosted failures remain visible but do not replace a referenced review comment. Complete intake never grants the implementation agent self-approval or `merge-ready` authority; that remains owned by `tools/skills/pr-review-recheck/SKILL.md` and a distinct configured reviewer.

Live read-only use:

```powershell
uv run python scripts/github/pr_comment_delta.py `
  --repo rickardvh/agentic-workspace `
  --pr 1713 `
  --referenced-comment 123456789 `
  --format json
```

Fresh-session or repeated-review use can suppress known comments with a baseline file:

```json
{
  "seen_comment_urls": [
    "https://github.com/rickardvh/agentic-workspace/pull/1713#discussion_r123"
  ]
}
```

```powershell
uv run python scripts/github/pr_comment_delta.py `
  --repo rickardvh/agentic-workspace `
  --pr 1713 `
  --baseline-json .agentic-workspace/local/pr-1713-comments.json `
  --format json
```

The helper does not write to GitHub. Do not reply to comments, resolve review threads, or submit reviews from the packet unless the human explicitly approves that write.

Live GitHub reads include `pagination.truncated`, `pagination.truncated_surfaces`, and GraphQL page limits. When `pagination.truncated` is `true`, treat the packet as incomplete and fetch complete paginated comments before deciding there are no actionable review obligations.
