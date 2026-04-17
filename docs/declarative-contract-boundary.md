# Declarative Contract Boundary

This page defines the first bounded declarative contract boundary for Agentic Workspace.

Use it when deciding whether a stable contract answer belongs in a checked-in manifest or schema, or should remain Python-owned because it still depends on live repo state, reconciliation, or procedural shaping.

## Purpose

- Keep stable query and report metadata inspectable outside Python branches.
- Preserve explicit boundaries around what is still procedural.
- Avoid turning the workspace package into a second workflow engine just to make contracts look more declarative.
- Give future extraction work a checked-in inventory instead of relying on chat memory.

## First Boundary

The first declarative tranche covers:

- compact answer envelope and selector metadata
- proof route ids and commands
- report schema metadata

These now live in checked-in manifests under [`src/agentic_workspace/contracts/`](../src/agentic_workspace/contracts/).

The first tranche explicitly does **not** extract:

- lifecycle execution logic
- reconciliation and drift decisions
- live report derivation from repo state
- dynamic defaults assembly that still combines declarative and procedural answers

Those remain Python-owned in the first slice.

## Classification Rule

Treat a surface as `declarative` when:

- the data is stable enough to be versioned directly
- the same answer should be inspectable without reading procedural branches
- a schema can validate the shape meaningfully

Treat a surface as `procedural` when:

- the answer depends on live repo state, reconciliation, or dynamic branching
- a manifest would mostly mirror control flow instead of reducing it
- extraction would freeze unstable policy or workflow logic too early

Treat a surface as `derived` when:

- the emitted answer is assembled from stable manifests plus live repo or config state
- the value should stay queryable, but not become a second editable source of truth

## Current Inventory

The machine-readable inventory is [`src/agentic_workspace/contracts/contract_inventory.json`](../src/agentic_workspace/contracts/contract_inventory.json).

Current high-level classification:

- `declarative`
  - compact answer profile and selector definitions
  - proof routes
  - report schema metadata
- `derived`
  - combined workspace report payload
- `procedural`
  - defaults payload assembly
  - lifecycle execution
  - reconciliation and drift handling

## Boundaries

- Do not extract unstable workflow policy into manifests just to reduce Python line count.
- Do not create schemas for data that is mostly live-state shaped and not meaningfully versioned.
- Keep declarative files subordinate to canonical docs and emitted CLI behavior.
- Prefer one bounded extraction slice at a time over broad contract-tooling rewrites.

## Relationship To Other Docs

- Use [`docs/contract-schema-index.md`](contract-schema-index.md) for the first schema and manifest inventory.
- Use [`docs/compact-contract-profile.md`](compact-contract-profile.md), [`docs/proof-surfaces-contract.md`](proof-surfaces-contract.md), and [`docs/reporting-contract.md`](reporting-contract.md) for the canonical human-facing semantics of the surfaces now backed by manifests.
