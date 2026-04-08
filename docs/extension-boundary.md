# Extension Boundary

This page is the canonical statement of the current extension boundary for Agentic Workspace.

Use it when you need to know what kinds of modules or integrations are supported today, what the workspace layer may assume about them, and what must be true before any external module or plugin contract is treated as public.

## Current Boundary

Today, the supported module boundary is first-party only.

Supported:

- Agentic Memory
- Agentic Planning
- the thin `agentic-workspace` composition layer that orchestrates those first-party modules

Not yet supported as a public contract:

- third-party modules
- plugin loading
- dynamic registry extension by downstream repos
- undocumented external modules that imitate first-party descriptor fields

## What The Workspace Layer May Assume

The workspace layer may assume first-party modules provide:

- explicit capability declarations
- explicit lifecycle commands for install, adopt, upgrade, uninstall, doctor, and status
- dependency/conflict metadata when compatibility rules exist
- result-contract metadata that the workspace adapter can preserve and report
- owned writable surfaces
- install-signal detection
- generated-artifact classification when generated files are part of the contract
- package-local ownership of domain logic

The workspace layer must not assume:

- external modules can satisfy the same contract yet
- module internals are interchangeable across different products
- hidden plugin hooks that are not documented here

## Why The Boundary Stays Closed For Now

The first-party module contract is real and useful, but still optimized around two closely related shipped modules that are dogfooded in this monorepo.

Opening that boundary too early would risk:

- freezing private assumptions as a fake public API
- pushing plugin pressure into the workspace layer before module seams are fully stable
- raising support and compatibility expectations faster than the repo can justify

## Readiness Gates For A Public Extension Contract

Do not treat external extension as supported until all of the following are true:

1. The first-party module contract is stable enough that new first-party modules could be added from descriptor-owned metadata without bespoke orchestrator globals or hardcoded root-guidance branches.
2. The registry and lifecycle model are documented in public-contract terms rather than only internal descriptor terms.
3. Selective adoption still works cleanly when the workspace layer coordinates more than the current first-party pair.
4. Compatibility, upgrade, uninstall, and doctor expectations are explicit for non-core modules.
5. At least one realistic external-use case exists that is better solved by extension than by keeping the capability inside an existing module.

## Current Maintainer Rule

- Treat extension-boundary work as design work until those readiness gates are met.
- Prefer sharpening first-party module seams, docs, tests, and lifecycle reporting over inventing a plugin API.
- If a new capability is only useful as a helper to memory or planning, keep it package-local or capability-local instead of making it look like an external module surface.

## Relationship To Other Docs

- Use [`docs/integration-contract.md`](docs/integration-contract.md) for how memory, planning, managed surfaces, and generated docs interact today.
- Use [`docs/module-capability-contract.md`](docs/module-capability-contract.md) for the current first-party capability/dependency/result contract that prepares the registry for later extension without opening it yet.
- Use [`docs/boundary-and-extraction.md`](docs/boundary-and-extraction.md) for extraction criteria and ownership rules.
- Use [`docs/ecosystem-roadmap.md`](docs/ecosystem-roadmap.md) for long-horizon stance without treating it as a promise of immediate extension support.
