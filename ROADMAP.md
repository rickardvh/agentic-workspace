# Roadmap

Last reviewed: 2026-04-05

## Purpose

Inactive long-horizon candidate work.

## Active Handoff

- Monorepo scaffold is in place.
- Current architecture stance: keep `agentic-memory-bootstrap` and `agentic-planning-bootstrap` as the standalone products, with the workspace layer owning orchestration; treat routing and checks as cross-cutting capabilities until dogfooding proves they deserve package extraction.
- A thin root `agentic-workspace` lifecycle CLI now exists; remaining orchestrator work should deepen composition and operator ergonomics without pulling domain logic out of the module packages.
- No active execution tranche is currently promoted.
- Promote the next candidate only when the scope is bounded enough for a short execplan and a narrow validation story.

## Next Candidate Queue

- Unified lifecycle orchestrator follow-through: deepen the new workspace-level lifecycle CLI with presets, richer shared UX, and broader composition flows while keeping module-specific logic in the module packages.
- Capability extraction criteria: define the contract and promotion bar for when routing or checks should graduate from cross-cutting capabilities into standalone packages, using stable schemas, explicit ownership, adapter-friendly validation, partial-adoption support, and real reuse pressure as the gate.
- Shared tooling extraction: evaluate a common checker core when the first stable monorepo release exposes repeated maintenance friction across duplicated scripts.
- Unified integration lane: add a dual-bootstrap coexistence smoke-test harness when release dry-runs show the monorepo install topology is stable enough to freeze expectations.
- Contributor onboarding: add package ownership CODEOWNERS and contributor playbooks when package boundaries are stable enough to freeze ownership expectations.

## Reopen Conditions

- Reopen roadmap planning when active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when active tranche dependencies are clear and bounded.
- Keep detailed execution in `docs/execplans/` once promoted.
