# Roadmap

Last reviewed: 2026-04-05

## Purpose

Inactive long-horizon candidate work.

## Active Handoff

- Monorepo scaffold is in place.
- No active execution tranche is currently promoted.
- Maintainer feedback favors sharper documentation, liveness checks, and naming consistency over adding new layers.
- Promote the next candidate only when the scope is bounded enough for a short execplan and a narrow validation story.

## Next Candidate Queue

- Naming and chooser cleanup: decide whether stable external product names are `agentic-memory` / `agentic-planning` or the current `*-bootstrap` names, add a very short external package chooser, and move excess maintainer/architecture detail out of the root README so it stays primarily an external entrypoint. Promote when naming choices and external entrypoint scope can be bounded into one short documentation tranche.

- Maintainer startup and routing liveness checks: add cheap checks for `.agentic-workspace/planning/agent-manifest.json` vs generated `tools/` docs and for the repeated maintainer startup path across root maintainer surfaces; make generated routing docs visibly non-manual. Promote when the canonical sources and expected compared surfaces are enumerated clearly enough for one narrow validation tranche.

- Boundary and ecosystem policy hardening: create one canonical boundary/extraction-policy doc, add a compact ecosystem roadmap note for routing/checks extraction evidence, make workspace-layer thinness and the dogfooding fix-the-product rule more explicit, and document collaboration-safety rules plus the root-install versus package-workspace boundary. Promote when those policy surfaces can be grouped into one bounded doc set without rewriting the whole maintainer stack.

- External adoption and maturity guidance: strengthen package fit examples and adoption scenarios, reposition the memory package around the repo-memory contract instead of "small CLI" framing, clarify alpha/beta meaning, add a partial-adoption compatibility matrix, and add a small public architecture diagram and design-principles page. Promote when adopter-facing examples and maturity language can be delivered as one bounded documentation tranche with a narrow review surface.

- Shared tooling extraction: evaluate a common checker core when the first stable monorepo release exposes repeated maintenance friction across duplicated scripts.

## Reopen Conditions

- Reopen roadmap planning when active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when active tranche dependencies are clear and bounded.
- Keep detailed execution in `docs/execplans/` once promoted.
