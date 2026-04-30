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

## Runtime Artifact Shims

A runtime artifact shim is a local-only bridge from agent/runtime artifacts into ordinary Agentic Workspace surfaces. Use it when a runtime has internal plans, check bundles, exported handoff state, or other machine-local artifacts that need a compact workspace-facing summary without making the local file authoritative.

Each shim should keep compact output separate from full evidence:

- Compact output: short status, next action, and proof pointer for the agent.
- Full evidence: an inspectable local artifact, manifest, command log, or exported source file.

Each shim should record metadata before its output is promoted or acted on:

- `kind`
- `source_runtime`
- `artifact_class`
- `input_owner`
- `output_target`
- `authority`
- `promotion_target`
- `proof_command`
- `created_at`

Local shim output is never shared authority by itself. Promote useful results only through checked-in planning, memory, agent-aid, docs, or repo-native review surfaces, with proof attached to the promoted surface.

## Scratch Space

Use `.agentic-workspace/local/scratch/` freely for temporary agent working files. It is git-ignored local space and is there so agents do not need to invent a repo-specific scratch convention.

## Boundary Rules

- The area is local-only and git-ignored.
- Ordinary workspace commands must not require it to exist.
- It is non-authoritative for planning, memory, startup, review, and workflow state.
- It must be safe to delete without changing repo-owned shared behavior.
- It is not a plugin registry, shared compatibility framework, or source of canonical workflow truth.

Durable facts that should survive across agents belong in the appropriate checked-in workspace, planning, memory, or repo-owned documentation surface instead.
