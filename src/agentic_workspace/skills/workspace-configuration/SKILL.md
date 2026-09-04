---
name: workspace-configuration
description: Resolve repository setup and configuration intent through Agentic Workspace's current source owners without introducing a separate questionnaire or configuration authority.
---

# Workspace configuration

Use this optional shipped procedure when a user wants help settling setup or
configuration judgments. It is a judgment aid over ordinary
`Workspace.start` and owner operations; it owns no state and grants no new
authority.

Start with the complete high-level intent. Then:

1. Call ordinary `start` with that intent.
2. If the result is actionable and the proposed consequence is safe, inferred,
   and within the requested scope, invoke its `primary_action` unchanged.
3. Continue only from the returned `next_decision`, repeating step 2 while the
   same conditions hold. Do not poll or reconstruct state between steps.
4. On a finite or open decision, ask the current question once. Submit the
   answer through that request's `response_operation_id`, preserving its owner,
   revision, effects, scope, and current typed arguments. Continue from the
   returned `next_decision`.
5. Stop on a direct, terminal, or blocked result, or before any consequence
   outside the maintainer's authorization. A direct result is a successful
   zero-question setup outcome.

Translate intent to an existing owner, not to a storage path:

- repository preferences and provider defaults go to the applicable Repository
  control and `repository.answer`;
- release-proof strength and claim coverage go to the current Verification
  route and its operation;
- best-fit worker or delegation intent goes to the current Assignment decision
  or dispatch operation;
- retained advice and changed execution scope remain Memory and Planning
  judgments respectively.

If no current owner exposes the needed decision or operation, stop and report
that missing capability. Never compensate by directly editing arbitrary TOML,
JSON, ignored local files, or another owner's state. Do not create a setup
ledger, questionnaire state, or second configuration model. Fresh state is
obtained by calling ordinary `start` again; previously settled current answers
must stay quiet, and stale requests must be discarded rather than replayed.
