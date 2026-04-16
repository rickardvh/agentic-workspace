# Vague Instruction Failure Capture

## Status

Active

## Canonicality

agent_only

## Improvement signal metadata

- `memory_role`: `improvement_signal`
- `preferred_remediation`: `docs`
- `elimination_target`: `promote`

## Scope

Repeated vague-prompt failures where the same missing repo knowledge keeps forcing extra clarification, proof-lane discovery, or owner inference.

## Applies to

- `docs/intent-contract.md`
- `docs/default-path-contract.md`
- `docs/reporting-contract.md`
- `docs/delegated-judgment-contract.md`
- `src/agentic_workspace/cli.py`
- `memory/domains/vague-prompt-domain-understanding.md`

## Load when

- The same vague prompt class shows up more than once.
- Clarification keeps asking for the same repo facts.
- Prompt routing keeps choosing the wrong proof lane or owner on the first try.

## Review when

- A new prompt class appears.
- Intent, clarification, prompt-routing, or relay surfaces change.
- Routed Memory is absent or incomplete for the current repo.

## Failure signals

- The agent rewrites the prompt instead of clarifying it.
- Repeated broad rereads are needed to choose the owner or proof lane.
- The same missing domain fact shows up across tasks.
- Memory exists but does not change the interpretation choice.

## Rule or lesson

- Treat repeated vague-instruction failures as a signal that the repo is missing durable domain knowledge.
- Capture the missing knowledge in Memory first when it is repo-specific and recurring.
- Promote the knowledge into canonical docs when it has become a stable contract.

## What to do

- Record the repeated failure pattern.
- Link the failure to the smallest prompt class that recurred.
- Decide whether the remediation is a Memory note, a docs update, or both.
- Prefer a durable note that points to the upstream contract change instead of leaving the issue in chat.

## Verify

- `agentic-workspace defaults --section clarification --format json`
- `agentic-workspace defaults --section prompt_routing --format json`
- `agentic-workspace defaults --section relay --format json`

## Verified against

- `docs/intent-contract.md`
- `docs/default-path-contract.md`
- `docs/reporting-contract.md`
- `docs/delegated-judgment-contract.md`
- `src/agentic_workspace/cli.py`

## Last confirmed

2026-04-16 during intent interpretation tranche
