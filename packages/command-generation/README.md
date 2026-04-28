# Agentic Command Generation

Internal package boundary for generic command package generation.

This package owns rendering and freshness comparison for command package targets. Agentic Workspace remains the consumer: it owns command definitions, operation contracts, runtime primitives, and wrapper scripts that provide workspace-specific input.

## Schemas

`schemas/command_package_ir.schema.json` is the package-owned generic schema mirror for command-package IR. The workspace-owned IR data remains in `src/agentic_workspace/contracts/command_package_ir.json`, and root contract tooling verifies that the package schema mirror stays identical to the workspace validation schema until a later extraction slice can switch consumers to the package-owned schema path directly.

`agentic_command_generation.load_command_package_ir(ir_path, schema_path)` loads and validates an explicit IR file against an explicit schema file. Host repositories provide those paths from their own integration wrappers; this package does not import Agentic Workspace contract tooling.

This package is intentionally internal for now. It is shaped so schema ownership, generic loaders, checks, and eventual lift-out criteria can move here without adding a first-contact product surface.
