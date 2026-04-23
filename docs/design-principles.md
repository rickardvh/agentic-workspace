# Agentic Workspace Design Principles

## Purpose

Agentic Workspace should make repositories easier to enter, easier to resume, and cheaper to operate for both agents and humans while staying quiet about its own machinery.

The product should feel smaller than the internals behind it and should earn every visible surface it keeps.

## Must-Internalize Doctrine

### 1. Repository-native state beats chat residue

If a fact materially affects restart cost, safe execution, or future work, the repository should be able to carry it.

### 2. Reduce reading, not increase it

The system succeeds when it narrows the working set:

- load the smallest useful guidance bundle
- route to the right owner quickly
- avoid broad exploratory scans when the repo can already point the way

### 3. Preserve one home per concern

Each concern should have one primary owner.

- durable technical residue belongs in memory
- active execution state belongs in planning
- routing belongs in routing surfaces
- validation belongs in checks
- orchestration belongs in the workspace layer
- broad enduring explanation belongs in canonical docs

### 4. Make the repo easier to enter

A new agent or human should be able to answer, cheaply:

- what matters now
- what to read first
- what rules govern the repo
- what not to touch

### 5. Structure should lower reasoning cost

The product should reduce inference through clearer ownership, narrower startup paths, explicit routing, bounded validation, and fewer hidden conventions.

### 6. Simplicity should remain viable

Small local work should stay cheap. Add structure when ambiguity, restart cost, collaboration risk, or proof burden justify it, not by default.

### 7. Be quiet by default

Visible machinery should justify its visibility. If a surface can move into reporting, routing, or background structure without losing safety or clarity, prefer the quieter shape.

### 8. Improve the repo, not just the agent experience

Repeated workaround residue is pressure to improve the repo or the product. New surfaces should replace, merge, or materially simplify older paths instead of only adding precision.

### 9. Favor explicit seams over hidden coupling

Prefer explicit ownership rules, manifests, schemas, stable contracts, and narrow adapters over private cross-module convenience.

### 10. Selective adoption must remain valid

Memory, planning, and future modules should remain useful alone. The stack may get stronger when combined, but it must still make sense in parts.

### 11. Lifecycle should be centralized, domain logic should not

The workspace layer may centralize lifecycle entrypoints, presets, orchestration, and shared reporting, but it must not absorb module-owned domain logic.

Workspace self-improvement should also stay distinct from repo-directed improvement: the workspace may improve its own routing, reporting, recovery, or contract surfaces without using that as cover for repo-specific product drift.

### 12. Do not preserve both the old and new model by default

Compatibility layers, shims, transitional helper surfaces, and generated adapter artefacts should not be the automatic response to change.

They are justified only when they protect a specific real boundary or user of the system. Otherwise they usually:

- preserve ambiguity instead of resolving it
- multiply visible surfaces
- delay convergence on the intended product shape
- convert temporary uncertainty into durable residue

Prefer direct convergence when the system already knows which shape it wants.

### 13. Compatibility layers must earn their keep

Do not add or preserve a compatibility layer unless all three are true:

1. it protects a named consumer or boundary
2. it exists for a concrete transition reason
3. it has a credible path to removal, narrowing, or demotion

If those are missing, the layer is probably clutter wearing the language of caution.

### 14. Static routing aids are different from mutable compatibility shims

A small, obviously named, stable routing surface may be justified when it only helps weaker agents find the canonical next workflow.

Such a surface should:

- be static or slow-changing
- remain clearly non-authoritative
- point toward canonical config, query, planning, or ownership surfaces
- avoid restating changing operational truth
- stay narrow enough that it does not become a second operating layer

Do not confuse a routing aid with a prose mirror of live state.

### 15. Generated surfaces are suspect by default

Generated docs are only useful when they derive from canonical sources, stay easy to regenerate, and remove more cost than they create.

Do not keep generated checked-in prose merely because it is possible to generate it.

Generated surfaces are a poor fit when they:

- restate changing state
- duplicate canonical routing or authority
- ask maintainers to preserve both a structured source and a prose byproduct
- create more agent-facing surfaces than weak-agent discoverability actually requires

Prefer on-demand prose generation in chat or tooling over checked-in generated prose when the prose is explanatory rather than authoritative.

### 16. Collaboration safety matters

The product must degrade gracefully under normal git pressure:

- keep shared hot files small
- archive completed active surfaces promptly
- prefer bounded feature-scoped files over giant mutable dashboards
- keep generated or derived surfaces reproducible when they must exist

### 17. Help the agent do the job, do not script the job

The product should be opinionated about what boundary must remain true, not about the exact local choreography used to get there.

Prefer thin guidance, capability-shaped contracts, and explicit escalation cues over scheduler-like repo policy.

### 18. Portability matters more than local cleverness

Prefer narrow assumptions, conservative adoption, and plain checked-in surfaces over solutions that only feel elegant inside one well-understood monorepo.

### 19. Checked-in leverage should complement runtime leverage

Assume a capable runtime may already be better at delegation, model choice, or execution shaping than the repo should prescribe.

The repo should therefore focus on:

- explicit execution contracts
- durable handoff state
- smaller restart surfaces
- machine-readable proof expectations
- clear escalation boundaries

### 20. Proof should beat preference

Features that claim to reduce restart cost, token cost, or handoff burden should earn their place through repeated ordinary work, bounded review, or other real evidence.

### 21. Optimize total operating cost

Do not optimize for single-run cheapness if it raises total cost across planning, execution, interruption, handoff, review, or restart.

Do not save model tokens by creating human bureaucracy.

## Design Tests

A change is moving in the right direction when it helps answer yes to questions like:

- Does this reduce startup or restart friction?
- Does this reduce rediscovery and unnecessary rereading?
- Does this preserve or sharpen ownership boundaries?
- Does this keep visible product shape smaller than the internal machinery behind it?
- Does this lower total operating cost rather than shifting cost onto humans?
- Does this strengthen checked-in leverage without trying to out-orchestrate the runtime?
- Can it remain quiet in normal use?
- Can it be adopted selectively and removed cleanly?
- Would it still make sense outside this monorepo?
- Does it replace, merge, demote, or remove an older surface rather than merely adding another one?
- If it is a compatibility layer, does it name the consumer, transition reason, and likely removal path?
- If it is a routing surface, is it clearly just routing rather than a second source of changing truth?

A change is suspicious when it tends to:

- create new shared hot files
- duplicate source-of-truth surfaces
- require broad reading
- hide ownership
- add ceremony to simple work
- save tokens mainly by shifting work onto humans
- add a new contract surface without naming what older path it replaces, merges, or demotes
- preserve both an old and new model without a named beneficiary
- leave behind generated helper artefacts because removal feels riskier than commitment
- turn temporary compatibility into a durable product layer

## Tactical Policy Lives Elsewhere

Use narrower owner docs for tactical maintainer policy instead of growing this page:

- `docs/contributor-playbook.md` for maintainer routing, ownership, and validation lanes
- `docs/dogfooding-feedback.md` for dogfooding, product-friction routing, and new-work admission policy
- `.agentic-workspace/docs/lifecycle-and-config-contract.md` and `.agentic-workspace/docs/reporting-contract.md` for tactical contract details

## Short Version

Agentic Workspace should make repositories quietly well-run for agents and humans:

- durable state over chat residue
- smaller startup and restart burden
- one owner per concern
- explicit seams
- selective adoption
- quiet leverage over visible ceremony
- direct convergence over compatibility sprawl
- static routing help only when it clearly earns its keep

That is the bar.
