# Ecosystem direction

This page records current product-packaging direction. It is supporting context,
not a promise to create more packages.

For current product behaviour, start with [Documentation](index.md) and
[How AW fits into a project](package/overview.md). For maturity labels, see
[Maturity model](maturity-model.md).

## What ships today

The current first-party components are distributed with Agentic Workspace:

- Memory;
- Planning;
- Verification;
- the main `agentic-workspace` entry point and shared Rust core.

The main package supplies repository setup, task-relevant routing and the common
interfaces used by those components.

## What is proven

The first-party components can be installed and used selectively in ordinary
repositories through the shared AW setup path.

What is **not** yet a general product promise is a third-party plugin/module
ecosystem with the same support guarantees. New extension mechanisms should be
added only when a real external use case needs them.

## When a capability should become separate

Consider extracting a capability into a separate reusable component only when:

- multiple repositories or components need it;
- keeping it inside the current component causes repeated maintenance cost;
- its inputs, outputs and lifecycle are stable;
- it can be used independently without importing unrelated AW machinery.

Do not create a package merely because an internal concept has a name.

## What should remain internal

Keep implementation helpers internal when they exist only to support the current
first-party packages, depend on sibling internals, or have no independent user
value.

Prefer simpler docs and sharper component boundaries over another top-level
package when both solve the problem.
