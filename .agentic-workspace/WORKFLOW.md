# Workspace Workflow

## Purpose

Shared product-managed startup and ownership contract for Agentic Workspace systems installed in a repository.

Keep this file concise, product-managed, and replaceable. It is a compatibility router, not the full operating layer.

When skill support is available, prefer task-specific package skills discovered through `agentic-workspace skills --target . --task "<task>" --format json`. When skill support is unavailable, fall back to this file plus compact CLI commands.

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

- Treat this file as the only required top-level startup handoff from `AGENTS.md`.
- Use package skills for procedural work when available; use this file to recover the fallback route.
- Use `.agentic-workspace/memory/WORKFLOW.md` for memory-specific operating rules.
- Read module-local workflow files only when the shared workspace contract routes you there or when the task directly changes that module's behavior or workflow.
- Add module-local workflow files only when a module needs guidance that should not live in the shared workspace contract.

## Self-Optimisation

- Treat dogfooding evaluation as a standing workflow requirement, not an optional closeout flourish.
- During implementation and before claiming completion, identify what could have been safer, cheaper, or more efficient.
- Fix actionable findings immediately when they are in scope; otherwise route them into checked-in planning, issue follow-up, Memory, docs, or config with a clear owner.
- Surface actionable self-optimisation findings in handoff or final output even when the user did not ask for them explicitly.
