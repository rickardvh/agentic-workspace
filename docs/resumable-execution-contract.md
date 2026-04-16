# Resumable Execution Contract

This page defines the compact planning-side resumable execution contract for active work.

Use it when the question is "what does the next agent need right now to continue safely?" rather than "what is the broader requested outcome?" or "what happened after completion?"

## Purpose

- Keep restart cheap for ordinary active work.
- Carry the current next step, current scope, proof, and escalation boundary in one smaller checked-in object.
- Reuse the active execplan contract instead of adding another required authoring layer.

## Canonical Surface

Use:

```bash
agentic-planning-bootstrap summary --format json
```

That summary now carries a top-level schema envelope:

- `kind = "planning-summary/v1"`
- `schema.schema_version = "planning-summary-schema/v1"`

The `planning_record` object is the compact machine-readable active record for current work when planning has one active TODO item and one active execplan. The `resumable_contract` object remains the thinner restart view over that canonical record.

Use the summary first when the question is "how do I continue safely right now?".
Do not start by rereading raw execplan prose unless the compact summary leaves the restart boundary ambiguous.

The resumable view currently carries:

- `current_next_action`
- `active_milestone`
- `completion_criteria`
- `proof_expectations`
- `tool_verification`
- `escalate_when`
- `blockers`
- `minimal_refs`

`planning_record` is the canonical active state. `resumable_contract` is a restart projection over that state.
When the slice belongs to a larger line of work, `minimal_refs` should include the continuation surface or convergence owner that preserves the bigger arc, not only the immediate task file.

## Rules

- Keep the resumable view smaller than the full execplan.
- Derive the canonical planning record and its views from existing execplan sections instead of requiring a new section.
- Treat `planning_record` as the canonical active planning state when it is available; `resumable_contract` is a restart projection over that state.
- Treat it as unavailable when active planning is ambiguous or under-specified rather than fabricating restart certainty.
- Preserve proof and escalation boundaries explicitly so a weaker or later agent does not have to infer them from prose.
- Preserve the larger convergence arc explicitly when the current slice is only one part of it, so a later contributor can recover the bigger picture after interruption.
- Keep tool verification advisory in the first slice: declare required tools clearly, then stop or escalate when they are unavailable.
- If the runtime also used native planning artifacts, make sure the resumable view has already absorbed the durable next step before relying on cross-agent continuation.
- Treat raw planning prose as the semantic fallback and maintenance layer rather than the default restart-inspection path.

## Relationship To Other Contracts

- Use `docs/intent-contract.md` for the broader requested outcome and hard constraints.
- Use `docs/environment-recovery-contract.md` for the planning-side recovery rules and ordered repo-level remediation path.
- Use `docs/execution-summary-contract.md` for completed-slice summaries.

## Non-Goals

- This is not a replacement for the active execplan.
- This is not the full ordinary-work cross-agent handoff contract.
- This is not a generic task-history object.
