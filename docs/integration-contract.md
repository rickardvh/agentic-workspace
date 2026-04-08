# Integration Contract

This page records the compact interaction contract for repositories that use both Agentic Memory and Agentic Planning.

## Purpose

- Keep memory and planning selectively adoptable.
- Make the allowed interaction model explicit for adopter repositories.
- Preserve the workspace layer as a thin orchestrator instead of a shadow domain owner.

## Core Interaction Model

| Concern | Primary owner | May reference | Must not become |
| --- | --- | --- | --- |
| Durable repo knowledge | Memory | Planning when active work needs durable context | A second task tracker or backlog |
| Active execution state | Planning | Memory when work depends on durable repo knowledge | A durable knowledge base or subsystem manual |
| Shared module workflow support | Product-managed `.agentic-workspace/` surfaces | Repo planning and memory surfaces as inputs | Repo-owned canonical content |
| Generated maintainer guidance | Rendered `tools/` docs | Managed manifest and renderers only | Editable source of truth |

The shortest operating model is:

1. Planning says what matters now.
2. Memory says what is expensive to forget.
3. Managed module surfaces support those contracts.
4. Generated docs mirror managed sources and should be rerendered, not edited.

## Canonical-Source Precedence

When multiple surfaces mention the same concern, prefer the narrowest canonical owner in this order:

1. Repo-owned active execution surfaces for active-now state: `TODO.md`, `ROADMAP.md`, and active execplans.
2. Repo-owned durable memory or canonical docs for facts that outlive the current thread.
3. Product-managed module surfaces under `.agentic-workspace/memory/` or `.agentic-workspace/planning/` for shared workflow support, upgrade source, and generated support assets.
4. Generated mirrors such as `tools/` docs only as rendered outputs, never as editable source.

If two surfaces look equally authoritative, the contract is unclear and should be tightened instead of relying on contributor judgement.

## Interaction Rules

### Memory -> Planning

Memory may consume planning only as routing or restart context.

Allowed:

- current task scope when deciding which notes to load
- touched-path hints from an active execplan when routing durable notes
- compact continuation context that helps an agent restart the current thread

Not allowed:

- copying TODO or roadmap state into memory as a second active queue
- treating execplans as the durable home for repo knowledge

### Planning -> Memory

Planning may reference memory when active execution depends on durable repo knowledge.

Allowed:

- an execplan links to an invariant, runbook, or recurring-failure note
- a blocker points at a memory note that explains an authority boundary or operator sequence
- a completed thread promotes a durable lesson into memory instead of leaving it in planning surfaces

Not allowed:

- moving durable technical guidance into TODO or execplans just because it is active right now
- making planning the primary home for subsystem orientation or runbooks

### Managed -> Repo-Owned Surfaces

Product-managed `.agentic-workspace/` surfaces may support repo execution, but they should stay upgrade-replaceable and subordinate to repo-owned planning and memory content.

Allowed:

- the shared workspace layer: `.agentic-workspace/WORKFLOW.md`, `.agentic-workspace/OWNERSHIP.toml`, and the managed workflow pointer fence in `AGENTS.md`
- workflow helpers, upgrade sources, managed skills, and check scripts
- renderers and manifests that regenerate maintainer guidance
- thin wrappers that preserve package-owned behavior at predictable repo paths

Not allowed:

- hidden policy that becomes more authoritative than repo docs or manifests
- repo-specific rules that belong in the adopting repository instead of the package contract

### Generated -> Canonical Sources

Generated maintainer guidance under `tools/` may summarize the operating model, but it must always point back to its managed source.

Allowed:

- rerendering `tools/` docs from `.agentic-workspace/planning/agent-manifest.json`
- checking generated docs for drift against the managed manifest and renderer output

Not allowed:

- hand-editing generated docs as if they were the canonical contract
- letting generated mirrors silently diverge from the managed source they summarize

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

## Workspace Layer May Orchestrate

The workspace layer may own only cross-module composition behavior.

Allowed examples:

- install, adopt, upgrade, uninstall, doctor, and status flows that coordinate both modules
- shared lifecycle presets and combined validation entrypoints
- narrow wrappers and generated docs that make package contracts easier to operate together

Not allowed:

- module-specific policy that belongs inside Agentic Memory or Agentic Planning
- hidden cross-module state that becomes more authoritative than the package-owned surfaces

## Checks And Liveness

- Planning-surface checks should catch drift in TODO, ROADMAP, execplans, startup policy, and generated planning docs.
- Memory freshness checks should keep current notes weak-authority and durable notes in their primary homes.
- Package payload verification should keep shipped package surfaces present and structurally consistent before release or upgrade work.
- Maintainer validation should cover both modules when a change touches shared package contracts or collaboration-sensitive installed surfaces.

## Partial-Adoption Rules

- Memory-only repos should not need planning surfaces or planning-specific workflow assumptions.
- Planning-only repos should not need memory installs to interpret active execution state safely.
- Repos with both modules should keep memory and planning as separate owners, with references allowed but ownership not merged.
- The workspace layer may be the public lifecycle entrypoint for single-module or combined installs, but it is still not the primary owner of memory or planning content.

## Shared Rules

- Memory owns durable repo knowledge.
- Planning owns active execution state.
- `memory/current/` owns only weak-authority current context.
- Generated maintainer docs must derive from canonical sources.
- Package payload checks must stay on the maintainer path when installed contract drift could affect adopters.
- Cross-module convenience belongs at the workspace layer only when the reason is truly cross-module.

## Failure Signals

Revisit this contract when you see repeated signs such as:

- memory notes mirroring active TODO or roadmap state
- execplans accumulating durable subsystem documentation
- workspace commands needing package-internal flags or policy exceptions to stay usable
- routing or checks becoming more authoritative than the docs and manifests they are supposed to reflect
