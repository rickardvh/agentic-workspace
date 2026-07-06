# GitHub Helpers

This directory holds read-only helpers for GitHub review and maintainer workflows.

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

The packet includes `comment_surfaces` so closeout can distinguish complete GraphQL comment/thread reads from normalized fixtures or legacy caches with incomplete thread-surface proof.

Live read-only use:

```powershell
uv run python scripts/github/pr_comment_delta.py `
  --repo rickardvh/agentic-workspace `
  --pr 1713 `
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
