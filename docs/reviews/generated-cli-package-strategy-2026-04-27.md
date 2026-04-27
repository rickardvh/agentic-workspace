# Generated CLI Package Strategy

Date: 2026-04-27

Issues: #395, parent #393

Purpose: choose an off-the-shelf-first strategy for generated Python and TypeScript CLI packages. This is evidence/history, not ordinary startup input.

## Decision

Use the repo's existing JSON contracts as the canonical source and add a compact derived command-package IR rather than adopting a new standalone DSL.

Reason:

- Existing command, option, operation, primitive, generated-adapter, and conformance contracts already encode most needed truth.
- A new DSL would add another authoring surface and increase product residue.
- JSON Schema works for validation across Python and TypeScript ecosystems.
- A derived IR can be generated or checked from existing contracts and consumed by small target renderers.

## Off-The-Shelf-First Tooling Posture

Python:

- Keep `argparse` as the runtime parser library.
- Generate or mechanically assemble parser metadata and dispatch tables from the command-package IR.
- Use `jsonschema` for contract validation.

TypeScript:

- Prefer Commander.js for CLI parsing if the TypeScript package moves past fixture/proof stage.
- Prefer `json-schema-to-typescript` or `quicktype` for generated TypeScript types when type volume justifies it.
- Keep initial proof small enough that committed custom TypeScript generation is metadata rendering, not a hand-built framework.

Docker proof:

- Put Node/TypeScript setup inside generated-package test containers.
- Expose generated-package tests through Python-owned proof/check commands so ordinary repo development stays Python-centered.
- Do not require Docker for root unit tests unless generated-package paths are touched.

Shell adapters:

- Defer bash and PowerShell generation until the IR has proven Python and TypeScript targets.
- Treat shell outputs as thin wrappers, completion/help projections, or runtime package delegates.
- Do not let shell behavior become authoritative.

## Custom Codegen Boundary

Allowed custom code:

- small renderers that transform one validated command-package IR into target files
- freshness checks
- no-direct-edit sentinels
- Docker command wrappers

Avoid custom code:

- handwritten option parsers per target
- target-specific copies of command semantics
- runtime primitive implementations inside generators
- generator logic that infers behavior from Python source

## Canonical Flow

```text
existing contracts
  -> validated command-package IR
  -> generated Python package adapter
  -> generated TypeScript package adapter
  -> Docker-isolated conformance
```

## Success Test

The first implementation should prove that a command/interface change can be made in contracts and propagated to generated Python/TypeScript targets without editing shipped CLI implementation code for that interface surface.

## Rejected Alternatives

Adopt OpenAPI as the primary source:

- Rejected for now because this is a process CLI surface, not an HTTP API, and the existing contracts already model command effects and runtime primitive ownership.

Build a bespoke full generator:

- Rejected because the user explicitly prefers off-the-shelf tools and minimal custom code.

Generate shell adapters first:

- Rejected because shell quoting and parameter binding would force target-specific complexity before the shared IR is proven.

## Acceptance Evidence

#395 is satisfied when this strategy is paired with the #394 audit and the later #396 IR keeps universal command truth separate from target rendering details.
