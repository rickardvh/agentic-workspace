# AW local chat checkpoint resume dogfood

Date: 2026-06-26

Related issues: #1700, #1704

## Scenario

This dogfood pass exercised the local checkpoint flow as a simulated fresh-session boundary for the #1700 local checkpoint experiment.

The checkpoint was written with durable issue sources only; the local checkpoint file remains ignored under `.agentic-workspace/local/chat-checkpoint.json` and is not closure evidence.

```powershell
uv run python scripts/run_agentic_workspace.py checkpoint write `
  --target . `
  --task "Dogfood #1700/#1704 local checkpoint resume" `
  --issue "#1700" `
  --issue "#1704" `
  --durable-source "https://github.com/rickardvh/agentic-workspace/issues/1700" `
  --durable-source "https://github.com/rickardvh/agentic-workspace/issues/1704" `
  --last-proof "checkpoint dogfood proof pending" `
  --next-safe-command "uv run python scripts/run_agentic_workspace.py start --target . --select local_chat_checkpoint --format json" `
  --dirty-state-summary "clean branch before durable dogfooding review artifact" `
  --replace `
  --format json
```

## Result

The write command created `agentic-workspace/local-chat-checkpoint-write/v1` with status `written`, two durable sources, issue refs `#1700` and `#1704`, and no warnings.

The selected startup projection was compact and sufficient to recover the current checkpoint context:

```powershell
uv run python scripts/run_agentic_workspace.py start --target . --select local_chat_checkpoint --format json
```

The projection reported:

- `status`: `present`
- `checkpoint_kind`: `agentic-workspace/local-chat-checkpoint/v2`
- branch: `codex/1704-checkpoint-dogfood`
- current issue refs: `#1700`, `#1704`
- durable sources: the two GitHub issues
- resume rule: re-read durable sources and recheck fresh local/remote truth before claims
- volatile observations for branch, HEAD, remote, dirty-state summary, CI, comments, and dependency state
- resume checklist covering remote comments, git status/HEAD, dependencies, and proof freshness

## Fresh-Session Simulation

A startup run with only the resume-style task text also surfaced the checkpoint in ordinary context:

```powershell
uv run python scripts/run_agentic_workspace.py start `
  --target . `
  --task "Resume from local checkpoint for #1700/#1704" `
  --format json
```

This confirmed the checkpoint is visible early enough to prevent relying on compressed chat history. It also correctly kept the checkpoint advisory: the resume rule and checklist required fresh issue/PR, git, dependency, and proof checks before claims.

## What Was Missing

The ordinary resume run also hit the lane-shaping gate because `#1700` and `#1704` matched roadmap candidates and there was no active planning owner yet. That safety behavior was correct, but the checkpoint did not help pick the bounded candidate route or explain that the next safe durable step was promoting the already-matched #1704 candidate.

This means local checkpoints reduced chat-history dependence, but they did not fully reduce planning reorientation cost for roadmap-backed resume tasks.

## Follow-Up

Filed follow-up #1810 for startup/checkpoint integration: when a local checkpoint names issue refs that match roadmap candidates, the checkpoint packet or lane-shaping gate should surface the matched candidate IDs and the safest promote command without requiring a verbose planning read.

## Boundary

This review is the durable dogfooding record. The ignored local checkpoint remains advisory, local-only state and must not be treated as proof, closure evidence, or durable policy.
