# Agentic Command Generation

Internal package boundary for generic command package generation.

This package owns rendering and freshness comparison for command package targets. Agentic Workspace remains the consumer: it owns command definitions, operation contracts, runtime primitives, and wrapper scripts that provide workspace-specific input.

This package is intentionally internal for now. It is shaped so schema ownership, generic loaders, checks, and eventual lift-out criteria can move here without adding a first-contact product surface.
