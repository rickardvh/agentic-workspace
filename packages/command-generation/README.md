# Agentic Command Generation

Internal package boundary for generic command package generation.

This package owns rendering and freshness comparison for command package targets. Agentic Workspace remains the consumer: it owns command definitions, operation contracts, runtime primitives, and wrapper scripts that provide workspace-specific input.

## Schemas

`schemas/command_package_ir.schema.json` is the package-owned generic schema mirror for command-package IR. The workspace-owned IR data remains in `src/agentic_workspace/contracts/command_package_ir.json`, and root contract tooling verifies that the package schema mirror stays identical to the workspace validation schema until a later extraction slice can switch consumers to the package-owned schema path directly.

`agentic_command_generation.load_command_package_ir(ir_path, schema_path)` loads and validates an explicit IR file against an explicit schema file. Host repositories provide those paths from their own integration wrappers; this package does not import Agentic Workspace contract tooling.

## Lift-Out Readiness

Extraction is intentionally deferred until the checklist below is true. Until then, this package remains internal and Agentic Workspace consumes it through `scripts/generate/workspace_command_generation.py`.

Technical criteria:

- Generic package code has no imports from `agentic_workspace` or other host runtime packages.
- Generic schemas are owned and shipped by this package.
- Loaders and renderers consume explicit file paths or in-memory payloads, not host-specific loaders.
- At least one renderer is useful without Agentic Workspace command names, runtime modules, tracker systems, or repository layout assumptions.
- Generated output freshness, static checks, and container proof can run from a Python development environment plus dedicated Docker/Node proof lanes.

Ownership criteria:

- Agentic Workspace command truth remains in workspace-owned contracts such as `src/agentic_workspace/contracts/command_package_ir.json`.
- Runtime primitives, live workspace inspection, mutation guards, and output assembly remain outside this package.
- Host repositories own their integration wrapper, runtime handoff defaults, generated output locations, and any tracker-specific evidence refresh.

Migration criteria:

- Replace local path injection with normal package imports in host wrappers.
- Move or alias schema references so host IR can validate against the package-owned schema without a workspace mirror.
- Keep host checks as consumer checks that call package APIs rather than reimplementing generic validation or rendering.
- Regenerate all derived outputs from the host-owned IR and prove no hand-edited generated files remain.
- Keep Agentic Workspace-specific generated outputs in this repo unless a separate package has its own release and conformance contract.

Stability criteria:

- The IR shape, schema versioning rules, generated-output layout, and renderer API have at least one completed change cycle without incompatible churn.
- Docker/Node proof lanes are dedicated generated-package proof, not required for ordinary Python-only development.
- Documentation can explain extraction status from this README and host wrapper names without reconstructing issue history.

This package is intentionally internal for now. It is shaped so schema ownership, generic loaders, checks, and eventual lift-out criteria can move here without adding a first-contact product surface.
