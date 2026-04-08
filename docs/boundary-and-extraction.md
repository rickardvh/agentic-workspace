# Boundary And Extraction Policy

This page is the canonical policy surface for module boundaries and extraction decisions.

It operationalizes the higher-level product rules in `docs/design-principles.md`, especially one-home-per-concern ownership, selective adoption, explicit seams, and thin workspace orchestration.

## Ownership Tests

| Concern | Owns | Does not own |
| --- | --- | --- |
| Memory | durable knowledge that is expensive to rediscover | active task sequencing and backlog state |
| Planning | active execution state, next actions, and completion criteria | durable technical knowledge and long-lived subsystem memory |
| Routing | task-class decisions about what to read, trust, and run | shadow planning or shadow memory state |
| Checks | drift and liveness validation for installed surfaces | hidden ownership of the source-of-truth content |
| Workspace | multi-module lifecycle entrypoints and composition | package-internal domain behavior |

## Boundary Rules

- Memory must not become a task tracker or backlog mirror.
- Planning must not become a durable knowledge base.
- Routing must not become a shadow planning or memory system.
- Checks must not silently become the policy owner for source-of-truth content.
- Workspace must orchestrate domain packages without absorbing their internal rules.

## Workspace Thinness Rule

New module-specific lifecycle flags, installer rules, or domain policy should land in the package CLI first unless there is a strong workspace-level reason to expose them centrally.

## Extraction Criteria

Treat routing and checks as capabilities first, not packages by default.

Extract a new package only when all of the following are true:

- the ownership boundary is stable and not better explained as memory, planning, or workspace composition
- the capability exposes explicit seams such as manifests, schemas, adapters, or generated artifacts
- the capability is independently useful in selective-adoption repos
- dogfooding shows repeated reuse pressure or maintenance friction that is better solved by extraction

Do not extract a package when the result would mostly be a shell around one module's helper logic.

## Shared Tooling Decision Rule

When repeated duplication appears across root wrappers, payload mirrors, and package-local helpers, choose the smallest fix that restores one clear owner:

1. Prefer one canonical managed source when the behavior still belongs to one module contract.
2. Extract a small internal helper only when two or more owned surfaces need the same logic and the helper still has one clear owner.
3. Consider broader shared-tooling extraction only when the logic is stable, cross-module, independently valuable, and cheaper to maintain as a shared capability than as explicit module-owned code.

Do not introduce a shared helper layer just because two wrappers look similar. Similarity alone is weaker evidence than ownership and maintenance cost.

## Root Versus Package Workspace Rule

For this monorepo, root installed planning and memory surfaces are authoritative for live operation. Package roots are source, payload, skills, tests, and fixtures; do not recreate package-local operational installs as a workaround for missing product behavior.

Use `docs/source-payload-operational-install.md` when a change crosses package source, package payload, and the root install boundary so the three layers stay separate.
