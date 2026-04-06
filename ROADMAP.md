# Roadmap

Last reviewed: 2026-04-06

## Purpose

Inactive long-horizon candidate work.

## Active Handoff

- External entry, naming, architecture, maturity framing, and maintainer-boundary docs are now in a credible product shape.
- Installed-contract collaboration safety landed across the integration contract, package framing, shipped templates, payload verification, and the maintainer liveness lane.
- Docs-surface governance landed across the Memory README first screen, the root docs map, maintainer-doc role scoping, workflow-surface history, and a root maintainer-surface role-drift check.
- A draft bootstrap UX specification now defines the next public-product tranche: one root `init` entrypoint, conservative adopt detection, structured lifecycle reports, repo-specific handoff prompts, and thin module orchestration.
- The current promoted tranche is workspace bootstrap UX; it should land in the root CLI, tests, and adopter docs without pulling module-specific logic into the workspace layer.
- Execution-scaling contract work remains a likely next candidate after that so installed planning can make the simple-task fast path and promotion triggers explicit.
- Shared-tooling extraction remains the follow-on candidate after the active UX tranche and any required execution-scaling cleanup, but only if duplicated checks and renderers still create sustained maintenance drag.
- Promote the next candidate only when the scope is bounded enough for a short execplan and a narrow validation story.

## Next Candidate Queue

- Execution scaling contract: make direct execution an explicit success mode and define operational promotion triggers plus minimal residue rules.
- Shared tooling extraction: evaluate a common checker core when the first stable monorepo release exposes repeated maintenance friction across duplicated scripts.

## Reopen Conditions

- Reopen roadmap planning when active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when active tranche dependencies are clear and bounded.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
