# Local Chat Checkpoints

Local chat checkpoints are ignored, machine-local continuity hints stored at `.agentic-workspace/local/chat-checkpoint.json`.

They use `kind: agentic-workspace/local-chat-checkpoint/v1` and are intentionally not durable AW evidence. A checkpoint may record the current task, branch, PR or issue refs, short dirty-state notes, the last proof command names, blockers, and the next safe command. It must point to durable sources such as issues, PRs, checked-in Planning, Memory, docs, reviews, or proof receipts instead of copying raw transcript or policy text.

The required resume rule is: treat older chat as advisory and re-read `durable_sources` before making claims.

Guardrails:

- Store only under `.agentic-workspace/local/`, which is gitignored.
- Do not store secrets, auth tokens, raw chat transcripts, broad logs, or durable policy.
- Do not treat the checkpoint as closure evidence.
- Promote durable decisions to checked-in AW artifacts, issues, PRs, docs, reviews, or proof receipts.

Example:

```json
{
  "kind": "agentic-workspace/local-chat-checkpoint/v1",
  "created_at": "2026-06-23T10:00:00+00:00",
  "updated_at": "2026-06-23T10:05:00+00:00",
  "task": "Implement #1680 first tranche",
  "branch": "codex/example",
  "current_pr": 1699,
  "current_issue_refs": ["#1680"],
  "durable_sources": ["docs/reviews/example.md", "https://github.com/rickardvh/agentic-workspace/issues/1680"],
  "resume_rule": "Treat chat before this checkpoint as advisory. Re-read durable_sources before making claims.",
  "last_proof": ["make maintainer-surfaces"],
  "open_blockers": [],
  "dirty_state_summary": "No uncommitted durable state beyond the current slice.",
  "next_safe_command": "uv run python scripts/run_agentic_workspace.py start --target . --format json",
  "limits": {
    "local_only": true,
    "gitignored": true,
    "not_closure_evidence": true,
    "no_raw_transcripts": true,
    "no_secrets": true,
    "durable_decisions_require_durable_source": true
  }
}
```
