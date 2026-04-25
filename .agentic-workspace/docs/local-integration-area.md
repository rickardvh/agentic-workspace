# Local Integration Area

## Purpose

`.agentic-workspace/local/integrations/` is the sanctioned local-only home for vendor-specific or runtime-specific integration aids.

Use it for disposable helpers that make it cheaper for a local agent/runtime to reach the checked-in workspace outcome without turning those helpers into shared workflow state.

## Folder Convention

Create one direct subfolder per vendor or runtime:

```text
.agentic-workspace/local/integrations/<vendor-or-runtime>/
```

Examples:

```text
.agentic-workspace/local/integrations/codex/
.agentic-workspace/local/integrations/custom-cli/
```

Subfolders may contain prompt helpers, wrappers, export/import shims, native-workflow adapters, resumable handoff helpers, or runtime scratch files.

## Boundary Rules

- The area is local-only and git-ignored.
- Ordinary workspace commands must not require it to exist.
- It is non-authoritative for planning, memory, startup, review, and workflow state.
- It must be safe to delete without changing repo-owned shared behavior.
- It is not a plugin registry, shared compatibility framework, or source of canonical workflow truth.

Durable facts that should survive across agents belong in the appropriate checked-in workspace, planning, memory, or repo-owned documentation surface instead.
