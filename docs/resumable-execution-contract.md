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

The `resumable_contract` object is the compact machine-readable restart contract for current active work when planning has one active execplan and a present `active_contract`.

That contract currently carries:

- `current_next_action`
- `active_milestone`
- `completion_criteria`
- `proof_expectations`
- `escalate_when`
- `blockers`
- `minimal_refs`

## Rules

- Keep the resumable contract smaller than the full execplan.
- Derive it from existing execplan sections instead of requiring a new section.
- Treat it as unavailable when active planning is ambiguous or under-specified rather than fabricating restart certainty.
- Preserve proof and escalation boundaries explicitly so a weaker or later agent does not have to infer them from prose.

## Relationship To Other Contracts

- Use `docs/intent-contract.md` for the broader requested outcome and hard constraints.
- Use `docs/environment-recovery-contract.md` for the planning-side recovery rules and ordered repo-level remediation path.
- Use `docs/execution-summary-contract.md` for completed-slice summaries.

## Non-Goals

- This is not a replacement for the active execplan.
- This is not the full ordinary-work cross-agent handoff contract.
- This is not a generic task-history object.
