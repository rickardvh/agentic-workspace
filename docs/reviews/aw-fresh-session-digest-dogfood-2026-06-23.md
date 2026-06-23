# AW Fresh-Session Digest Dogfood

Date: 2026-06-23

Scope: #1692 slice under #1680.

## Observation

The #1680 lane is already being continued through many stacked PRs. A fresh session needs the current branch, issue refs, closure boundary, proof posture, and durable source pointers without replaying the whole chat or copying long issue bodies.

## Dogfood Command

```powershell
uv run python scripts/run_agentic_workspace.py summary `
  --task "Continue #1680 lane" `
  --select fresh_session_digest `
  --format json
```

## Expected Digest Shape

- `kind`: `agentic-workspace/fresh-session-digest/v1`
- `issue_refs`: contains `#1680`
- `current_branch_or_state`: reports the current git branch/state
- `closure_boundary.may_claim_parent_closure`: `false`
- `source_artifacts`: points to cached external intent evidence and compact review artifacts
- `detail_commands.refresh_issue_evidence`: keeps issue refresh explicit instead of embedding issue bodies

## Boundary

The digest is a fresh-session handoff aid. It does not replace `start`, `implement`, `proof`, issue evidence refresh, PR review, or closeout checks, and it cannot close #1680 by itself.
