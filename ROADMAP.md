# Roadmap

Last reviewed: 2026-04-06

## Purpose

Inactive long-horizon candidate work.

## Active Handoff

- External entry, naming, architecture, maturity framing, and maintainer-boundary docs are now in a credible product shape.
- Installed-contract collaboration safety landed across the integration contract, package framing, shipped templates, payload verification, and the maintainer liveness lane.
- Docs-surface governance landed across the Memory README first screen, the root docs map, maintainer-doc role scoping, workflow-surface history, and a root maintainer-surface role-drift check.
- New maintainer feedback shows the simple-task fast path is often working well, but the contract should make that success mode explicit and define when direct execution must promote into planning.
- The current promoted tranche is execution scaling: direct-execution success criteria, promotion triggers, and minimal residue rules.
- Shared-tooling extraction remains the likely next candidate after that, but only if duplicated checks and renderers still create sustained maintenance drag.
- Promote the next candidate only when the scope is bounded enough for a short execplan and a narrow validation story.

## Next Candidate Queue

- Shared tooling extraction: evaluate a common checker core when the first stable monorepo release exposes repeated maintenance friction across duplicated scripts.

## Reopen Conditions

- Reopen roadmap planning when active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when active tranche dependencies are clear and bounded.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
