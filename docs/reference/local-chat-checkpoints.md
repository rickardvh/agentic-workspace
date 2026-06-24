# Local Chat Checkpoints

Local chat checkpoints are ignored, machine-local continuity hints stored at `.agentic-workspace/local/chat-checkpoint.json`.

They use `kind: agentic-workspace/local-chat-checkpoint/v2` and are intentionally not durable AW evidence. A checkpoint may record the current task, repo root, remote URL, branch, PR or issue refs, local HEAD, upstream HEAD, short dirty-state notes, the last proof command names, blockers, and the next safe command. It must point to durable sources such as issues, PRs, checked-in Planning, Memory, docs, reviews, or proof receipts instead of copying raw transcript or policy text. Older `agentic-workspace/local-chat-checkpoint/v1` records are legacy local hints and should be treated as stale until rewritten.

The required resume rule is: treat older chat as advisory and re-read `durable_sources` before making claims.

Guardrails:

- Store only under `.agentic-workspace/local/`, which is gitignored.
- Do not store secrets, auth tokens, raw chat transcripts, broad logs, or durable policy.
- Do not treat the checkpoint as closure evidence.
- Promote durable decisions to checked-in AW artifacts, issues, PRs, docs, reviews, or proof receipts.

Example:

```json
{
  "kind": "agentic-workspace/local-chat-checkpoint/v2",
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
  "volatile_observations": {
    "repo_root": {
      "value": "<repo-root>",
      "source": "resolved target root at checkpoint write",
      "observed_at": "2026-06-23T10:05:00+00:00"
    },
    "remote_origin_url": {
      "value": "git@github.com:rickardvh/agentic-workspace.git",
      "source": "git config remote.origin.url at checkpoint write",
      "observed_at": "2026-06-23T10:05:00+00:00"
    },
    "branch": {
      "value": "codex/example",
      "source": "git branch at checkpoint write",
      "observed_at": "2026-06-23T10:05:00+00:00"
    },
    "head_commit": {
      "value": "0123456789abcdef0123456789abcdef01234567",
      "source": "git rev-parse HEAD at checkpoint write",
      "observed_at": "2026-06-23T10:05:00+00:00"
    },
    "upstream_commit": {
      "value": "0123456789abcdef0123456789abcdef01234567",
      "source": "git rev-parse --verify @{upstream} at checkpoint write",
      "observed_at": "2026-06-23T10:05:00+00:00"
    },
    "current_issue_refs": {
      "value": ["#1680"],
      "source": "checkpoint write input",
      "observed_at": "2026-06-23T10:05:00+00:00"
    },
    "dirty_state_summary": {
      "value": "No uncommitted durable state beyond the current slice.",
      "source": "checkpoint write input or preserved local checkpoint value",
      "observed_at": "2026-06-23T10:05:00+00:00"
    },
    "remote_comments": {
      "value": {"status": "not-checked-by-local-checkpoint-writer"},
      "source": "checkpoint write does not fetch PR or issue comments",
      "observed_at": "2026-06-23T10:05:00+00:00"
    },
    "ci_state": {
      "value": {"status": "not-checked-by-local-checkpoint-writer"},
      "source": "checkpoint write does not inspect CI state",
      "observed_at": "2026-06-23T10:05:00+00:00"
    },
    "dependency_state": {
      "value": {"status": "not-checked-by-local-checkpoint-writer"},
      "source": "checkpoint write does not inspect dependency releases or availability",
      "observed_at": "2026-06-23T10:05:00+00:00"
    }
  },
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
