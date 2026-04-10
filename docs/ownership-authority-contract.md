# Ownership And Authority Contract

## Purpose

This document records the normal ownership and authority boundaries for the repository.

Use it when the question is:

- who owns this concern?
- which checked-in surface is authoritative?
- is this repo-owned, product-managed, or only a managed fence inside a repo-owned file?

## Rule

Resolve the owner and authoritative surface before changing or trusting a contract.

Do not infer ownership from whichever copy is most visible in the current working tree.

## Default Ownership Surface

Use:

```bash
agentic-workspace ownership --target ./repo --format json
```

That command is the workspace-level query surface for:

- the canonical ownership contract
- the current ownership ledger path
- ownership classes
- module-managed roots
- managed fences
- the main authority surfaces by concern

## Main Authority Surfaces

| Concern | Primary surface | Owner | Ownership class |
| --- | --- | --- | --- |
| Repo startup instructions | `AGENTS.md` | repo | `repo_owned` |
| Active execution state | `TODO.md` | repo | `repo_owned` |
| Long-horizon candidate queue | `ROADMAP.md` | repo | `repo_owned` |
| Design constraints for product-shape changes | `docs/design-principles.md` | repo | `repo_owned` |
| Repo-owned workspace lifecycle defaults | `agentic-workspace.toml` | repo | `repo_owned` |
| Shared workflow contract | `.agentic-workspace/WORKFLOW.md` | workspace | `module_managed` |
| Ownership ledger | `.agentic-workspace/OWNERSHIP.toml` | workspace | `module_managed` |
| Product-managed planning install tree | `.agentic-workspace/planning/` | planning | `module_managed` |
| Product-managed memory install tree | `.agentic-workspace/memory/` | memory | `module_managed` |
| Workflow pointer block inside `AGENTS.md` | fenced block in `AGENTS.md` | workspace | `managed_fence` |

## Ownership Classes

- `repo_owned`
  - Repository-native state owned by the repo.
  - Installed packages should not silently replace it.
- `managed_fence`
  - Product-managed content inside an explicit fence within a repo-owned file.
  - The file stays repo-owned; only the fenced block is managed.
- `module_managed`
  - Upgrade-replaceable content owned by one installed module under `.agentic-workspace/`.

## Boundaries

- Keep one primary owner per concern.
- Keep package-local behavior package-local.
- Keep the workspace layer queryable and thin; it should expose ownership, not absorb domain ownership from planning or memory.
- Treat generated-surface trust as related but separate: ownership says who owns a surface, not whether a mirror is fresh.

## Relationship To Other Docs

- Use [`docs/proof-surfaces-contract.md`](docs/proof-surfaces-contract.md) when the question is which proof lane establishes trust.
- Use [`docs/generated-surface-trust.md`](docs/generated-surface-trust.md) when the question is whether a generated mirror is stale or hand-edited.
- Use [`docs/compatibility-policy.md`](docs/compatibility-policy.md) when the question is whether a surface is stable, mutable, or generated.
