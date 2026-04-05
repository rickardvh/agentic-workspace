# Integration Contract

This page records the explicit cross-module contract for repositories that use both Agentic Memory and Agentic Planning.

## Purpose

- Keep memory and planning selectively adoptable.
- Make legitimate cross-module references explicit.
- Preserve the workspace layer as a thin orchestrator instead of a shadow domain owner.

## Canonical-Source Precedence

When multiple surfaces mention the same concern, prefer the narrowest canonical owner in this order:

1. Repo-owned active execution surfaces for active-now state: `TODO.md`, `ROADMAP.md`, and active execplans.
2. Repo-owned durable memory or canonical docs for facts that outlive the current thread.
3. Product-managed module surfaces under `.agentic-workspace/memory/` or `.agentic-workspace/planning/` for shared workflow support, upgrade source, and generated support assets.
4. Generated mirrors such as `tools/` docs only as rendered outputs, never as editable source.

If two surfaces look equally authoritative, the contract is unclear and should be tightened instead of relying on contributor judgement.

## Branch-Vs-Trunk State

- Branch-local, low-half-life state belongs in active planning or `memory/current/` and should stay easy to compress, replace, or archive.
- Durable facts that should survive merges belong in canonical memory notes or normal checked-in docs.
- Product-managed support files under `.agentic-workspace/` should change through their owning package or managed source, not by ad hoc edits in downstream mirrors.
- Generated mirrors should change by rerendering from their canonical source.

## Write Authority By Surface

| Surface | Primary owner | Edit directly? | Notes |
| --- | --- | --- | --- |
| `TODO.md`, `ROADMAP.md`, `docs/execplans/` | Repo planning contract | Yes | Active execution state; keep compact and archive completed residue quickly. |
| `memory/decisions/`, `memory/domains/`, `memory/invariants/`, `memory/runbooks/`, `memory/mistakes/` | Repo memory contract | Yes | Durable repo knowledge; one fact should have one primary home. |
| `memory/current/` | Repo memory contract | Yes, but weak-authority only | Use for concise re-orientation and calibration, not as canonical durable truth. |
| `.agentic-workspace/memory/`, `.agentic-workspace/planning/` | Product-managed module layer | Only through the owning package or explicit managed source | Treat as upgrade-replaceable shared support surfaces. |
| `tools/AGENT_*.md`, `tools/agent-manifest.json` | Generated planning outputs | No | Update `.agentic-workspace/planning/agent-manifest.json` and rerender. |
| Root `agentic-workspace` CLI and shared Make targets | Workspace composition layer | Yes, when the behavior is truly cross-module | Keep thin; push module-specific logic back into the module packages. |

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

## Partial-Adoption Rules

- Memory-only repos should not need planning surfaces or planning-specific workflow assumptions.
- Planning-only repos should not need memory installs to interpret active execution state safely.
- Repos with both modules should keep memory and planning as separate owners, with references allowed but ownership not merged.
- The workspace layer should only appear when coordinating multiple installed modules; it is not the primary owner of memory or planning content.

## Shared Rules

- Memory owns durable repo knowledge.
- Planning owns active execution state.
- `memory/current/` owns only weak-authority current context.
- Generated maintainer docs must derive from canonical sources.
- Cross-module convenience belongs at the workspace layer only when the reason is truly cross-module.

## Failure Signals

Revisit this contract when you see repeated signs such as:

- memory notes mirroring active TODO or roadmap state
- execplans accumulating durable subsystem documentation
- workspace commands needing package-internal flags or policy exceptions to stay usable
- routing or checks becoming more authoritative than the docs and manifests they are supposed to reflect
