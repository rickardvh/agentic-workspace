# Intent Contract

This page defines the compact planning-side intent contract for active work.

Use it when the question is not "what happened after completion?" but "what did the human ask for, what constraints still bind the work, and what proof or escalation boundary should survive restart?"

## Purpose

- Preserve the requested end state in checked-in form.
- Make active work cheaper to resume across sessions and agents.
- Keep the first machine-readable contract derived from the existing execplan shape instead of introducing a second plan schema.

## Canonical Surface

Use:

```bash
agentic-planning-bootstrap summary --format json
```

That summary now carries a top-level schema envelope:

- `kind = "planning-summary/v1"`
- `schema.schema_version = "planning-summary-schema/v1"`

The `planning_record` object is the compact machine-readable active record for current work when planning has one active TODO item and one active execplan. The `active_contract` object remains as the narrower intent view over that canonical record.

The canonical planning record currently carries:

- the active task id and execplan surface
- `status`
- `requested_outcome`
- `hard_constraints`
- `agent_may_decide`
- `next_action`
- `touched_scope`
- `proof_expectations`
- `tool_verification`
- `escalate_when`
- `continuation_owner`
- `completion_criteria`
- `blockers`
- `minimal_refs`

`active_contract` remains available as a compatibility projection focused on intent and escalation boundaries.

## Rules

- Derive the canonical planning record and its views from the existing execplan fields rather than adding a second required authoring section.
- Keep it small enough that a weaker or later agent can recover the intended end state without broad rereading.
- Treat it as unavailable when active planning is ambiguous instead of fabricating certainty from several partial surfaces.
- Preserve explicit escalation boundaries; the contract must not silently widen requested outcome, ownership scope, or time horizon.
- When a plan declares `Required Tools`, expose that requirement directly so weaker agents can stop or escalate before attempting impossible work.

## Relationship To Other Contracts

- Use `docs/delegated-judgment-contract.md` for the prose rule about what the human sets and what the agent may decide locally.
- Use `docs/execution-summary-contract.md` for completed-slice summaries.
- Use `docs/execplans/README.md` for the active execplan authoring rules that supply this compact contract.

## Non-Goals

- This is not a second execplan.
- This is not a narrative handoff history.
- This is not the full minimal resumable execution contract for every active task shape.
