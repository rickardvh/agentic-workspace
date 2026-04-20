---
name: planning-orchestrator-workflow
description: Run planner-to-worker delegated execution from checked-in planning using the local mixed-agent posture and a derived handoff contract.
---

# Planning Orchestrator Workflow

Use this skill when work is broad enough to benefit from stronger planning first and a bounded worker later.

This skill is agent-agnostic.
The worker may be:

- an internal delegated agent
- a local model run through CLI or API
- another vendor executor reached through CLI or API
- the same agent continuing directly when delegation is not worth it

## Read First

1. `AGENTS.md`
2. `.agentic-workspace/planning/state.toml`
3. the active execplan
4. `agentic-workspace config --target . --format json`
5. `agentic-workspace defaults --section relay --format json`
6. `agentic-planning-bootstrap handoff --format json`

## Workflow

1. Confirm the task is planning-backed and bounded enough for delegation.
2. Inspect the effective mixed-agent posture from local config.
3. If delegation is not supported or not worthwhile, stay direct.
4. If delegation is worthwhile, derive the worker handoff from `agentic-planning-bootstrap handoff --format json`.
5. Choose any execution method that preserves that contract:
   - internal delegation when the environment supports it and prefers it
   - external CLI or API handoff when another executor is cheaper or more available
   - direct single-agent fallback when delegation would cost more than it saves
6. Give the worker only the delegated handoff contract plus any explicit assignment for cleanup or commit.
7. Keep lane shaping, roadmap routing, and issue decisions with the orchestrator unless they are explicitly delegated.
8. Mirror durable residue back into checked-in planning before review, handoff, or session end.

## Worker Contract

Default worker ownership:

- bounded implementation
- narrow validation
- checked-in updates inside explicitly assigned owned surfaces
- cleanup and commit only when explicitly assigned and still bounded

Default worker stop conditions:

- the delegated task needs broad rereads outside the explicit read-first refs
- the task shape widens beyond the owned write scope
- the chosen delegation method cannot preserve the checked-in contract
- escalation boundaries are hit

## Boundaries

- Do not use this skill to turn repo config into a scheduler.
- Do not hardcode vendor-specific routing rules into checked-in planning.
- Do not let the delegated worker become the only place continuity lives.
- Do not widen requested ends just because a stronger planner is available.

## Output

For each orchestrated run, record:

- whether delegation stayed direct, internal, or external
- which bounded slice was delegated
- what the handoff contract contained
- what overhead remained
- what workflow improvement signal, if any, should survive in checked-in planning or review residue
