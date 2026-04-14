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

The `active_contract` object is the compact machine-readable intent contract for current active work when planning has exactly one active TODO item and one active execplan.

That contract currently carries:

- the active TODO item id and execplan surface
- `requested_outcome`
- `hard_constraints`
- `agent_may_decide`
- `escalate_when`
- compact `touched_scope`
- compact `proof_expectations`
- minimal refs back to the checked-in active surfaces

## Rules

- Derive the contract from the existing execplan fields rather than adding a second required authoring section.
- Keep it small enough that a weaker or later agent can recover the intended end state without broad rereading.
- Treat it as unavailable when active planning is ambiguous instead of fabricating certainty from several partial surfaces.
- Preserve explicit escalation boundaries; the contract must not silently widen requested outcome, ownership scope, or time horizon.

## Relationship To Other Contracts

- Use `docs/delegated-judgment-contract.md` for the prose rule about what the human sets and what the agent may decide locally.
- Use `docs/execution-summary-contract.md` for completed-slice summaries.
- Use `docs/execplans/README.md` for the active execplan authoring rules that supply this compact contract.

## Non-Goals

- This is not a second execplan.
- This is not a narrative handoff history.
- This is not the full minimal resumable execution contract for every active task shape.
