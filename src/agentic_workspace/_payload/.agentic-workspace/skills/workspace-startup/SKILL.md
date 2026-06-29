---
name: workspace-startup
description: Orient through compact Agentic Workspace commands before opening raw planning, memory, or docs surfaces.
---

# Workspace Startup

Use this skill when the task is about ordinary startup, task routing, config obligations, proof selection, closeout, or module boundaries in an installed Agentic Workspace repo.
When Agentic Workspace is enabled, this skill is inside mandatory workflow participation; advisory skill routing and `implementation_allowed` never mean startup, planning gates, proof, or closeout can be skipped.

## Route

1. Run `agentic-workspace start --target . --task "<task>" --format json` for ordinary first contact.
2. If changed paths are already known, run `agentic-workspace implement --target . --changed <paths> --format json`.
3. Run `agentic-workspace preflight --target . --format json` only for takeover, recovery, or uncertain state.
4. Run `agentic-workspace summary --target . --format json` when active work, planning, handoff, or continuation matters.
5. Run `agentic-workspace config --target . --format json` when local posture, configured obligations, startup file, or CLI invocation matters; use `--verbose` only when the tiny answer is insufficient.
6. Run `agentic-workspace proof --target . --changed <paths> --format json` before claiming validation.

Open raw `.agentic-workspace/` files only after a compact command points there.

## Red Flags

Red flag:
  I can inspect raw planning or memory files first because the request seems simple.

Use instead:
  Run `agentic-workspace start --target . --task "<task>" --format json`, or the known dedicated AW command when the request already names one, then follow `next_safe_action`.

## SkillSpec Pilot

This skill is the hand-authored startup pilot for the `startup-router` SkillSpec contract in `src/agentic_workspace/contracts/skill_specs.json`.

- Preferred CLI: `agentic-workspace start --target . --task "<task>" --format json`.
- Interpreted fields: `workflow_participation`, `immediate_next_allowed_action`, `next_safe_action`, `planning_safety_gate`, `skill_routing.preferred_routes`, and `detail_commands`.
- Direct work: if compact startup does not require planning and proof is obvious, keep the work direct and avoid planning, review, Memory, or handoff artifacts.
- Planning work: if `planning_safety_gate.implementation_allowed` is false, run the named planning command before implementation.
- No-CLI fallback: read `.agentic-workspace/WORKFLOW.md` only far enough to preserve the same forbidden actions and no-artifact-by-default rule.

## Module Map

- Workspace orchestrates startup, lifecycle, config, ownership, proof routing, reports, and module composition.
- Planning owns active execution state, checked-in execplans, decomposition records, proof expectations, and closeout routing.
- Memory owns durable anti-rediscovery knowledge: invariants, boundaries, runbooks, routing hints, and recurring failure lessons.
- Generated references own exact field names and structured output shapes after conceptual docs explain the behavior.

Use `.agentic-workspace/docs/module-map.md` when a short installed-repo module map is enough and broader package docs would cost too much context.

## Closeout

For planned work, closeout is not only validation success. Separate proof, intent satisfaction, issue completion, durable residue, and dogfooding findings. Route future-relevant learning to Memory, docs, checks, contracts, config, Planning, or an issue. Do not keep completed execplans as the ordinary knowledge base.
