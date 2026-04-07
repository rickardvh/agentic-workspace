# Workspace Workflow

## Purpose

Shared product-managed startup and ownership contract for Agentic Workspace systems installed in a repository.

Keep this file concise, product-managed, and replaceable.

## Ownership model

- `AGENTS.md` is the repo-owned entrypoint.
- `.agentic-workspace/` is the product-managed enclave.
- Repo-owned execution surfaces stay outside `.agentic-workspace/` unless they contain explicit managed fences.
- Product-managed startup guidance, ownership metadata, and module-local managed assets belong under `.agentic-workspace/`.

## Fence rule

- Product-managed text inserted into repo-owned files must live inside explicit `agentic-workspace:*` fences.
- Unfenced prose in repo-owned files is repo-owned by default.
- Prefer a short pointer fence over large managed prose blocks in repo-owned files.

## Module layout

- `.agentic-workspace/WORKFLOW.md` is the shared workspace-level startup contract.
- `.agentic-workspace/OWNERSHIP.toml` is the ownership ledger for managed paths, fences, and uninstall policy.
- `.agentic-workspace/<module>/` is the module-owned root for upgrade-replaceable assets.
- Module-specific workflow detail should live inside the relevant module directory when the shared contract is insufficient.

## Repo boundary

- Keep repo-owned execution, planning, and knowledge surfaces outside `.agentic-workspace/` unless they use explicit managed fences.
- Do not hide active execution state or durable repository knowledge behind product-managed indirection.
- Preserve strict boundaries between planning, memory, routing, checks, and workspace orchestration.

## Module delegation

- Use `.agentic-workspace/memory/WORKFLOW.md` for memory-specific operating rules.
- Add module-local workflow files only when a module needs guidance that should not live in the shared workspace contract.
