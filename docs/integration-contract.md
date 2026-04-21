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

In combined installs, the interaction should be stronger than simple compatibility:

1. Planning borrows durable context from Memory instead of re-explaining it.
2. Completed Planning work promotes durable residue into Memory or canonical docs instead of leaving it in chat or archived plan prose.
3. Repeated restart friction or repeated plan re-explanation is a product signal that the combined install still needs clearer docs, memory, validation, or decomposition.

## Canonical-Source Precedence

When multiple surfaces mention the same concern, prefer the narrowest canonical owner in this order:

1. Module-managed active execution state for active-now work: `.agentic-workspace/planning/state.toml` plus active execplans.
2. Package-managed durable memory or canonical docs for facts that outlive the current thread, with the package home kept compact under `.agentic-workspace/`.
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
- a direct task or execplan uses a short memory reference instead of restating the same durable subsystem explanation again

Not allowed:

- moving durable technical guidance into TODO or execplans just because it is active right now
- making planning the primary home for subsystem orientation or runbooks
- copying broad memory prose into every execplan when one routed note or canonical doc would do

### Combined-Install Borrow Rule

When both modules are installed, planning should borrow from memory when the active work depends on:

- durable invariants
- recurring traps
- operator runbooks
- subsystem context that should survive the current thread
- authority boundaries that would otherwise be re-explained in each plan

Prefer a short reference to the relevant memory note or canonical doc over re-stating the same durable background in an execplan.

If an execplan needs to repeat the same repo explanation more than once, treat that as a missing-synergy signal:

- the memory note may be missing, too broad, or too task-local
- a canonical doc may be missing
- the task may need better decomposition so the plan can stay local

### Combined-Install Residue Rule

When active execution finishes, classify leftover detail before it drifts into archived plan prose or chat-only residue.

Promote residue into memory when it is:

- a durable invariant
- a recurring trap
- a reusable operator sequence
- a durable subsystem orientation fact
- an anti-rediscovery lesson that future agents are unlikely to recover cheaply from code alone

Promote residue into canonical docs when it is:

- stable human-facing engineering guidance
- policy, lifecycle, or maintainer instruction
- a subsystem explanation that should be primary outside memory

Drop the residue instead of promoting it when it is:

- task-local narration
- milestone history
- one-off implementation detail that is already cheap to recover from code or tests

### Combined Startup And Resume Model

For combined installs, the cheap restart path should be:

1. planning surfaces for active-now state
2. the smallest routed memory bundle needed for durable context
3. canonical docs only when memory or planning points there as the primary owner

The goal is not to read both systems broadly by default.
The goal is to let planning say what matters now while memory supplies only the durable context needed to avoid rediscovery.

### Managed -> Repo-Owned Surfaces

Product-managed `.agentic-workspace/` surfaces may support repo execution, but they should stay upgrade-replaceable and subordinate to package-managed memory content and module-managed planning state, not spread new authority into the wider repo.

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

- Branch-local, low-half-life state belongs in active planning or `.agentic-workspace/memory/repo/current/` and should stay easy to compress, replace, or archive.
- Durable facts that should survive merges belong in memory notes or normal checked-in docs.
- Product-managed support files under `.agentic-workspace/` should change through their owning package or managed source, not by ad hoc edits in downstream mirrors.
- Generated mirrors should change by rerendering from their canonical source.

## Write Authority By Surface

| Surface | Primary owner | Edit directly? | Notes |
| --- | --- | --- | --- |
| `.agentic-workspace/planning/state.toml`, `.agentic-workspace/planning/execplans/` | Repo planning contract | Yes | Active execution state; keep compact and archive completed residue quickly. |
| `.agentic-workspace/memory/repo/decisions/`, `.agentic-workspace/memory/repo/domains/`, `.agentic-workspace/memory/repo/invariants/`, `.agentic-workspace/memory/repo/runbooks/`, `.agentic-workspace/memory/repo/mistakes/` | Repo memory contract | Yes | Durable repo knowledge; one fact should have one primary home. |
| `.agentic-workspace/memory/repo/current/` | Repo memory contract | Yes, but weak-authority only | Use for concise re-orientation and calibration, not as canonical durable truth. |
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

## Module Descriptor Rule

- The orchestrator should learn first-party module behavior from module descriptors, not from separate planning/memory global tables.
- Selection order, preset membership, install signals, startup guidance, root-surface cleanup rules, capabilities, dependencies/conflicts, and result-contract metadata should live on the descriptor when they are truly module-scoped.
- If adding or changing a first-party module still requires updating parallel orchestrator globals, the module contract is not finished yet.

## Composition Source Rule

- If a cross-module or shared maintainer behavior needs implementation logic, give it one canonical managed source before exposing thin root or package wrappers.
- Root wrappers, package mirrors, and bootstrap copies may forward to that managed source, but they should not become parallel logic owners.
- When this rule is violated, the duplicated wrapper logic is a composition-contract bug, not only a maintenance nuisance.
- If duplication pressure persists after that step and affects more than one owning module, re-evaluate under `.agentic-workspace/docs/extraction-and-discovery-contract.md` before extracting broader shared tooling.

## Checks And Liveness

- Planning-surface checks should catch drift in TODO, ROADMAP, execplans, startup policy, and generated planning docs.
- Memory freshness checks should keep current notes weak-authority and durable notes in their primary homes.
- Package payload verification should keep shipped package surfaces present and structurally consistent before release or upgrade work.
- Maintainer validation should cover both modules when a change touches shared package contracts or collaboration-sensitive installed surfaces.

## Missing-Synergy Signals

Treat the following as signals that combined installs are not yet reducing restart cost enough:

- execplans repeatedly re-explain the same repo or subsystem background
- restart still requires broad reading even when both modules are installed
- durable residue keeps staying in completed plans instead of moving into memory or canonical docs
- memory notes still need too much task-local context to help active execution

These are not only local habits.
They are product signals for better decomposition, tighter memory routing, stronger canonical docs, or clearer improvement-targeting.

## Partial-Adoption Rules

- Memory-only repos should not need planning surfaces or planning-specific workflow assumptions.
- Planning-only repos should not need memory installs to interpret active execution state safely.
- Repos with both modules should keep memory and planning as separate owners, with references allowed but ownership not merged.
- The workspace layer may be the public lifecycle entrypoint for single-module or combined installs, but it is still not the primary owner of memory or planning content.

## Shared Rules

- Memory owns durable repo knowledge.
- Planning owns active execution state.
- `.agentic-workspace/memory/repo/current/` owns only weak-authority current context.
- Generated maintainer docs must derive from canonical sources.
- Package payload checks must stay on the maintainer path when installed contract drift could affect adopters.
- Cross-module convenience belongs at the workspace layer only when the reason is truly cross-module.

## Failure Signals

Revisit this contract when you see repeated signs such as:

- memory notes mirroring active TODO or roadmap state
- execplans accumulating durable subsystem documentation
- workspace commands needing package-internal flags or policy exceptions to stay usable
- routing or checks becoming more authoritative than the docs and manifests they are supposed to reflect
