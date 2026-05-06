---
name: workspace-startup
description: Orient through compact Agentic Workspace commands before opening raw planning, memory, or docs surfaces.
---

# Workspace Startup

Use this skill when the task is about ordinary startup, task routing, config obligations, proof selection, closeout, or module boundaries in an installed Agentic Workspace repo.

## Route

1. Run `agentic-workspace start --profile tiny --target . --task "<task>" --format json` for ordinary first contact.
2. If changed paths are already known, run `agentic-workspace implement --profile tiny --target . --changed <paths> --format json`.
3. Run `agentic-workspace preflight --target . --format json` only for takeover, recovery, or uncertain state.
4. Run `agentic-workspace summary --target . --format json` when active work, planning, handoff, or continuation matters.
5. Run `agentic-workspace config --target . --profile tiny --format json` when local posture, configured obligations, startup file, or CLI invocation matters; use `--profile compact` only when the tiny answer is insufficient.
6. Run `agentic-workspace proof --profile tiny --target . --changed <paths> --format json` before claiming validation.

Open raw `.agentic-workspace/` files only after a compact command points there.

## Module Map

- Workspace orchestrates startup, lifecycle, config, ownership, proof routing, reports, and module composition.
- Planning owns active execution state, checked-in execplans, decomposition records, proof expectations, and closeout routing.
- Memory owns durable anti-rediscovery knowledge: invariants, boundaries, runbooks, routing hints, and recurring failure lessons.
- Generated references own exact field names and structured output shapes after conceptual docs explain the behavior.

Use `.agentic-workspace/docs/module-map.md` when a short installed-repo module map is enough and broader package docs would cost too much context.

## Closeout

For planned work, closeout is not only validation success. Separate proof, intent satisfaction, issue completion, durable residue, and dogfooding findings. Route future-relevant learning to Memory, docs, checks, contracts, config, Planning, or an issue. Do not keep completed execplans as the ordinary knowledge base.
