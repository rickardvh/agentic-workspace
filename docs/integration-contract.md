# Integration Contract

This page records the explicit cross-module contract for repositories that use both Agentic Memory and Agentic Planning.

## Purpose

- Keep memory and planning selectively adoptable.
- Make legitimate cross-module references explicit.
- Preserve the workspace layer as a thin orchestrator instead of a shadow domain owner.

## Memory May Consume From Planning

Memory may use planning only as routing context, not as durable source ownership.

Allowed examples:

- current task scope when deciding which memory notes are worth loading
- touched-path hints from an active execplan when routing durable notes
- compact continuation context that helps an agent restart the current thread

Not allowed:

- copying TODO or roadmap state into memory as a second active queue
- treating execplans as the durable home for repo knowledge

## Planning May Reference Memory

Planning may point at memory when active execution depends on durable repo knowledge.

Allowed examples:

- an execplan links to an invariant, runbook, or recurring-failure note
- a blocker points at a memory note that explains an authority boundary or operator sequence
- a completed thread promotes a durable lesson into memory instead of leaving it in planning surfaces

Not allowed:

- moving durable technical guidance into TODO or execplans just because it is active right now
- making planning the primary home for subsystem orientation or runbooks

## Workspace Layer May Orchestrate

The workspace layer may own only cross-module composition behavior.

Allowed examples:

- install, adopt, upgrade, uninstall, doctor, and status flows that coordinate both modules
- shared lifecycle presets and combined validation entrypoints
- narrow wrappers and generated docs that make package contracts easier to operate together

Not allowed:

- module-specific policy that belongs inside Agentic Memory or Agentic Planning
- hidden cross-module state that becomes more authoritative than the package-owned surfaces

## Shared Rules

- Memory owns durable repo knowledge.
- Planning owns active execution state.
- Generated maintainer docs must derive from canonical sources.
- Cross-module convenience belongs at the workspace layer only when the reason is truly cross-module.

## Failure Signals

Revisit this contract when you see repeated signs such as:

- memory notes mirroring active TODO or roadmap state
- execplans accumulating durable subsystem documentation
- workspace commands needing package-internal flags or policy exceptions to stay usable
- routing or checks becoming more authoritative than the docs and manifests they are supposed to reflect
