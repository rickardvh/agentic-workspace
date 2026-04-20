# Agent OS Capabilities

Last doctrinal review: 2026-04-10

## Purpose

This document records the long-horizon capability model for the Agentic Workspace ecosystem.

It is the durable home for the capability structure of an agent-oriented checked-in operating system: what capabilities the system may contain, which are already shipped, which remain important internal capabilities, which may become future candidates, and which are unlikely to justify standalone product status.

This document is not a bounded roadmap, backlog, or implementation plan.

Long-horizon direction can change as the product evolves.
When a capability description, promotion stance, or architectural emphasis no longer matches current dogfooding reality, update this document directly and route any newly-bounded follow-on into `roadmap` in `.agentic-workspace/planning/state.toml` instead of leaving stale intent embedded here.

## How To Read This

Use these categories when reading the capability map:

- `shipped module`: a first-party product or composition layer that is already part of the supported ecosystem shape
- `internal capability`: an important capability that exists today inside a shipped module or the workspace layer but is not a standalone product
- `future candidate`: a capability that may justify stronger promotion later if repeated dogfooding pressure and stable boundaries emerge
- `extraction candidate`: a capability that has enough selective-adoption value and contract stability to be considered for promotion beyond its current home
- `unlikely to stand alone`: a capability that matters, but is more useful as supporting infrastructure than as its own package

These categories describe architectural position, not delivery priority.

## Doctrine Maintenance

Treat this page as durable doctrine, not frozen doctrine.

- Refresh it when major shipped contracts land, when dogfooding changes what matters most, or when a capability's current category no longer matches real usage.
- Prefer changing or deleting stale long-horizon statements over preserving historical wording that no longer drives the product.
- When a doctrinal change reveals concrete next work, record that work in `roadmap` in `.agentic-workspace/planning/state.toml` as a bounded candidate instead of letting this document become a shadow queue.
- Treat a doctrine-refresh review as the normal audit lane for revisiting this page rather than relying on ad hoc memory or chat residue.

## Role Boundary

This page owns the capability taxonomy and the current architectural role of those capabilities.

It does not own:

- bounded sequencing decisions
- current ecosystem packaging stance
- the current maturity label of each shipped surface

Route those concerns to:

- `roadmap` in `.agentic-workspace/planning/state.toml` for bounded future candidates
- `docs/ecosystem-roadmap.md` for ecosystem stance and extraction discipline
- `docs/maturity-model.md` for maturity labels and the rationale behind them

## Refresh Triggers

Update this page directly when any of the following happens:

- a shipped surface materially changes which internal capabilities matter most
- a capability changes category, current home, or extraction stance
- dogfooding reveals that the capability map is missing a recurring pressure or still reflects retired work
- another long-horizon page starts carrying capability-taxonomy content that belongs here instead

## Current Shipped Modules

### Agentic Memory

- Category: `shipped module`
- Role: anti-rediscovery knowledge for the repository
- Current home: `agentic-memory-bootstrap`

### Agentic Planning

- Category: `shipped module`
- Role: active execution state for bounded work
- Current home: `agentic-planning-bootstrap`

### Workspace Composition Layer

- Category: `shipped module`
- Role: thin workspace-level lifecycle orchestration and reporting across first-party modules
- Current home: `agentic-workspace`

The composition layer is intentionally thin. It exists to centralize lifecycle entrypoints and cross-module reporting without absorbing module-owned domain logic.
Its shared workspace report now gives a compact combined-state view for installed modules, mixed-agent posture, effective repo output posture, and next-action guidance so agents do not need to inspect raw module files first.
That output posture is repo-owned through `workspace.optimization_bias`: it should be legible during ordinary recovery and reporting, but it must stay an output/residue preference rather than an execution-routing policy.

## Important Internal Capabilities

- Checks / proof surfaces
- Ownership / authority mapping
- Bounded delegated judgment
- Generated-surface trust
- Review / audit lane
- Intake / triage
- Collaboration / concurrency safety
- Capability / module registry
- Environment / recovery guidance
- Handoff / execution summaries

These capabilities are architecturally important today, but they are not automatically destined to become standalone packages.

## Capability Descriptions

### Memory

- Current category: `shipped module`
- Problem solved: expensive repository context is repeatedly rediscovered, lost between sessions, or trapped in one contributor's head
- Why an agent wants it in checked-in form: durable notes, traps, invariants, and runbooks reduce restart cost and token waste while improving continuity across sessions and contributors
- Current home: Agentic Memory as a first-party module
- What would justify promoting it further: stronger independent adoption, stable extension seams, and clearer external contracts for complementary memory-specific capabilities

### Planning

- Current category: `shipped module`
- Problem solved: active work drifts, broadens, or becomes hard to resume when execution state is left in chat or implied context
- Why an agent wants it in checked-in form: bounded active work, clear next actions, explicit validation, and prompt archival make execution cheaper and safer
- Current home: Agentic Planning as a first-party module
- What would justify promoting it further: broader reuse of planning-specific sub-capabilities outside the current module boundary

### Checks / Proof Surfaces

- Current category: `internal capability`
- Problem solved: documentation, installed surfaces, generated artifacts, and memory can drift away from the real contract without fast detection
- Why an agent wants it in checked-in form: lightweight proof surfaces reduce rereading and lower the need for manual trust calibration
- Current home: primarily inside module-owned checks and workspace aggregation
- Promotion stance: keep internal unless repeated cross-module reuse produces a stable, selectively adoptable proof contract
- Evidence required for further promotion: repeated dogfooding pressure across more than one module, shared schemas that stop depending on sibling internals, and a clear ownership boundary

### Ownership / Authority Mapping

- Current category: `internal capability`
- Problem solved: agents waste effort when they must infer which file or layer actually owns a concern
- Why an agent wants it in checked-in form: explicit authority boundaries reduce interpretation cost and prevent drift between repo-owned and product-managed surfaces
- Current home: workspace ownership surfaces, lifecycle docs, and module contracts
- Promotion stance: important internal capability, not currently a standalone product target
- Evidence required for further promotion: repeated cross-repo demand for a reusable ownership contract with stable schemas and selective-adoption value

### Bounded Delegated Judgment

- Current category: `internal capability`
- Problem solved: repositories lose efficiency when humans must micromanage routine execution or when agents continue confidently past the point where escalation is warranted
- Why an agent wants it in checked-in form: explicit decision authority, confidence-sensitive escalation, and constraint-driven execution make it possible for humans to set direction while agents own bounded local judgment
- Current home: planning and workflow contracts, capability-aware execution guidance, and startup instructions that define when to proceed, when to improve the proposed approach, and when to stop and ask
- Promotion stance: future candidate, but only if the contract proves stable enough to stand apart from planning rather than duplicating it
- Evidence required for further promotion: repeated dogfooding showing that task intent, local authority, and escalation boundaries can be expressed portably across repos and tools without vendor-specific routing assumptions

### Capability / Module Registry

- Current category: `internal capability`
- Problem solved: module and skill discovery become brittle when availability, capabilities, and compatibility are inferred indirectly
- Why an agent wants it in checked-in form: explicit registries make discovery, recommendation, and lifecycle composition cheaper and more explainable
- Current home: workspace module registry plus bundled and repo-owned skill registries
- Promotion stance: keep internal while the ecosystem remains first-party and the public extension boundary stays closed
- Evidence required for further promotion: external module or plugin support with stable capability declarations, compatibility rules, and result contracts

### Collaboration / Concurrency Safety

- Current category: `internal capability`
- Problem solved: high-churn workflow files and ambiguous ownership create merge pressure, lost updates, and recoverability problems
- Why an agent wants it in checked-in form: explicit safety rules make normal git-based collaboration less fragile and reduce costly repair work
- Current home: canonical collaboration docs, archive discipline, generated-surface rules, and install/doctor checks
- Promotion stance: likely to remain internal
- Evidence required for further promotion: repeated need for a reusable, independently adoptable collaboration contract outside the current first-party modules

### Intake / Triage

- Current category: `internal capability`
- Problem solved: externally tracked tasks, review signals, and friction reports can create noisy parallel planning systems
- Why an agent wants it in checked-in form: clear intake boundaries keep upstream trackers and ad hoc findings from becoming shadow execution systems
- Current home: planning skills, review docs, roadmap discipline, and dogfooding guidance
- Promotion stance: future candidate only if cross-repo intake pressure becomes strong and stable
- Evidence required for further promotion: repeated dogfooding showing a reusable intake schema and clear selective-adoption value separate from planning itself

### Review / Audit Lane

- Current category: `internal capability`
- Problem solved: repositories need a disciplined way to capture bounded findings without turning review into permanent management overhead
- Why an agent wants it in checked-in form: explicit review modes and promotion thresholds keep quality checks useful while containing residue
- Current home: planning-managed review surfaces and templates
- Promotion stance: future candidate, but only with strong evidence
- Evidence required for further promotion: repeated use across distinct repo shapes, stable review schemas, and a contract that does not simply duplicate planning

### Generated-Surface Trust

- Current category: `internal capability`
- Problem solved: generated maintainer and routing surfaces become liabilities when they are stale or unclear in origin
- Why an agent wants it in checked-in form: trusted generated artifacts can reduce orientation cost only when provenance and freshness are explicit
- Current home: planning-owned manifest, render path, freshness checks, and canonical docs
- Promotion stance: unlikely to stand alone
- Evidence required for further promotion: strong cross-module or cross-repo demand for a generic generated-surface trust layer with stable shared rules

### Environment / Recovery Guidance

- Current category: `internal capability`
- Problem solved: agents lose time when environment constraints, recovery paths, or maintenance preconditions must be rediscovered manually
- Why an agent wants it in checked-in form: concise recovery guidance lowers operational dead-ends and reduces repeated diagnosis cost
- Current home: the planning-side recovery contract plus module docs, maintainer docs, and selected workflow contracts
- Promotion stance: future candidate at most; likely to stay supporting infrastructure
- Evidence required for further promotion: repeated, reusable need for a stable checked-in recovery contract that is not better served by module-local docs

### Handoff / Execution Summaries

- Current category: `unlikely to stand alone`
- Problem solved: work becomes harder to resume when results, blockers, and validation outcomes are not summarized in a consistent shape
- Why an agent wants it in checked-in form: structured handoff makes continuation and review cheaper across sessions and contributors
- Current home: planning outputs, lifecycle reports, and selected memory or review surfaces
- Promotion stance: supporting capability, not a standalone product target today
- Evidence required for further promotion: repeated proof that a reusable summary contract has independent value across repos without simply duplicating planning state

## Human Direction And Agent Judgment

The long-horizon target is not unrestricted autonomy. It is bounded delegated judgment.

The intended operating shape is:

- humans provide direction, priorities, and constraints
- agents improve local execution plans when a better bounded path is apparent
- agents proceed autonomously when the contract makes that safe
- agents escalate promptly when confidence, authority, or validation conditions are no longer strong enough

In the ideal case, a maintainer can hand an agent a durable product or architectural direction surface and rely on the checked-in system to do most of the remaining routing and shaping work.

That requires the ecosystem to encode, cheaply and explicitly:

- what the human is setting versus what the agent may decide locally
- what kinds of tasks should stay simple and direct
- what requires stronger planning or decomposition first
- what should be improved rather than followed literally when the original suggestion is weak
- what conditions require stopping and asking instead of continuing wastefully

This is primarily a planning and workflow-contract concern today, not a separate product promise.
The value of the capability is that it lets humans step back to intent and constraints while keeping agent judgment bounded, auditable, and restartable.

## Extraction / Productization Criteria

Promote or extract a capability only when dogfooding shows all of the following:

- repeated pressure that is hard to solve cleanly inside the current modules or workspace layer
- stable contract shape that no longer depends on sibling internals or informal conventions
- clear ownership and boundaries
- real selective-adoption value for repositories that would benefit from the capability without adopting the whole current stack

The default stance is internal capability first.

Extraction is evidence-driven, not taxonomy-driven. A capability appearing in this document does not mean it should become its own package.

## Relationship To planning.state roadmap

`roadmap` in `.agentic-workspace/planning/state.toml` should stay the short bounded sequencing queue.

It should hold only bounded future candidates, promotion triggers, and sequencing guidance derived from this broader capability model. It should not become the home for the full long-horizon capability taxonomy.

## Relationship To docs/ecosystem-roadmap.md

`docs/ecosystem-roadmap.md` records the current ecosystem stance: what is shipped today, what remains internal for now, and the discipline for extraction.

This document is broader. It records the capability map itself and the intended architectural role of those capabilities without turning them into a queue or package promise.
