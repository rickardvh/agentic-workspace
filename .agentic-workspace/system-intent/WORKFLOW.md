# System Intent Workflow

## Purpose

This surface tells agents how to refresh the workspace-owned mirrored system-intent contract without imposing a schema on the host repository's source files.

## Surfaces

- Repo-owned source declaration: `.agentic-workspace/config.toml [system_intent]`
- Workspace-owned interpreted mirror: `.agentic-workspace/system-intent/intent.toml`
- Workspace-owned scoped intent store: `.agentic-workspace/system-intent/subsystems.toml`

## Rules

- Read the declared source files first.
- Treat those repo-owned sources as directional input, not as if they already match the workspace mirror schema.
- Preserve the difference between quoted source meaning and interpreted normalization.
- Keep ambiguous or weakly supported interpretations visible through low confidence, open questions, or `needs_review = true`.
- Update source metadata through `agentic-workspace system-intent --target ./repo --sync --format json` before refining the interpreted fields.
- Keep the mirror easy for humans to inspect and patch directly.
- Keep subsystem intent scoped. Use it for durable component or concern direction, not active task state.
- Treat task intent as closable work. Promote from task intent only when the task reveals reusable durable direction.

## What To Extract

- one compact summary of the larger system direction
- the main governing intents worth preserving during local decision-making
- anti-intents or things the system should resist becoming
- decision tests that should shape future work and review
- open questions where the source direction is still ambiguous
- subsystem/component-scoped direction that should guide future decisions in that area
- provenance, confidence, review status, and supersession when intent is inferred

## Promotion From Task Intent

At planning or closeout, classify any discovered durable direction as one of:

- do not promote
- promote to Memory
- propose subsystem intent
- propose system intent
- refine existing durable intent
- supersede existing durable intent

Promotion should be evidence-backed and reviewable. Do not silently make inferred intent authoritative.

## What Not To Do

- do not turn system intent into an active task plan
- do not promote one-off task goals into durable intent
- do not silently replace the repo's direction with a cheaper interpretation
- do not freeze the mirror as final; refine it when the source direction changes materially
- do not move repo-owned prose into the workspace mirror verbatim when a normalized summary is enough
