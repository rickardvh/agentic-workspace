# Selector-First Output Policy

Date: 2026-06-28

This note records the visibility rule used for low-risk direct work after the long-thread dogfooding review. The goal is lower successful-completion cost: the first packet should let an agent choose the next safe action without scanning bulky context, while hard gates and claim boundaries remain visible.

## Always First Packet

- `next_safe_action` and `action_signals`: hard blockers, allowed next action, proof requirement, and compact changed signals.
- Scope facts: changed paths or the likely work surface.
- Required proof summary: narrow proof commands and missing-proof closeout state.
- Blocking compatibility, stale proof, payload drift, or safety-critical claim boundaries.

## Selector-Only by Default

- `local_chat_checkpoint` when it is present but unrelated to the current low-risk task.
- `routine_work_context`, broad candidate-route detail, compatibility detail, and generated-surface detail when they are non-blocking.
- `pr_comment_attention` when no PR context is detected.
- Full `dogfooding_signal_status` detail when no planned lane, stacked PR, release/recovery, or maintainer-dogfooding context is active.

## Escalates Into First Packet

- `local_chat_checkpoint` when stale, unreadable, explicitly resumed, or carrying matched planning candidate routes.
- `pr_comment_attention` when the task or branch is PR-oriented, or a cached PR comment delta is present.
- `dogfooding_signal_status` for planned lanes, stacked PR sequences, release/recovery work, or maintainer-mode dogfooding.
- Any selector-only surface that becomes a hard blocker or required-before-claim boundary.

This policy is a routing rule, not a deletion rule. Detailed packets remain available through `--select` or `report --section`.
