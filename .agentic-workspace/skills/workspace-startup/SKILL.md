---
name: workspace-startup
description: Orient through compact Agentic Workspace commands before opening raw planning, memory, or docs surfaces.
---

# Workspace Startup

Use this skill when the task is about ordinary startup, task routing, config obligations, proof selection, closeout, or module boundaries in an installed Agentic Workspace repo.

## Route

1. Run `agentic-workspace start --target . --task "<task>" --format json` for ordinary first contact.
2. If changed paths are already known, run `agentic-workspace implement --target . --changed <paths> --format json`.
3. Run `agentic-workspace preflight --target . --format json` only for takeover, recovery, or uncertain state.
4. Run `agentic-workspace summary --target . --format json` when active work, planning, handoff, or continuation matters.
5. Run `agentic-workspace config --target . --format json` when local posture, configured obligations, startup file, or CLI invocation matters; use `--select <field.path>` when one field is needed or `--verbose` for broad diagnostics.
6. Run `agentic-workspace proof --target . --changed <paths> --format json` before claiming validation.

Open raw `.agentic-workspace/` files only after a compact command points there.

## SkillSpec Pilot

This skill is the hand-authored startup pilot for the `startup-router` SkillSpec contract in `src/agentic_workspace/contracts/skill_specs.json`.

- Preferred CLI: `agentic-workspace start --target . --task "<task>" --format json`.
- Interpreted fields: `immediate_next_allowed_action`, `next_safe_action`, `planning_safety_gate`, `skill_routing.preferred_routes`, and `detail_commands`.
- Direct work: if compact startup does not require planning and proof is obvious, keep the work direct and avoid planning, review, Memory, or handoff artifacts.
- Planning work: if `planning_safety_gate.implementation_allowed` is false, run the named planning command before implementation.
- No-CLI fallback: read `.agentic-workspace/WORKFLOW.md` only far enough to preserve the same forbidden actions and no-artifact-by-default rule.

## Sufficiency

- If `workflow_sufficiency.nothing_more_needed` is true, stop exploring package surfaces for this step and proceed with the named next action.
- If the packet says evidence is still required, gather only that evidence; do not broaden into raw planning, memory, review, or archive surfaces.
- Use `agentic-workspace report --section authority_hierarchy --format json` only when current authority is unclear.
- Use `agentic-workspace report --section compliance_economics --format json` only when judging whether missing workflow evidence lowers trust.

## Module Map

- Workspace orchestrates startup, lifecycle, config, ownership, proof routing, reports, and module composition.
- Planning owns active execution state, checked-in execplans, decomposition records, proof expectations, and closeout routing.
- Memory owns durable anti-rediscovery knowledge: invariants, boundaries, runbooks, routing hints, and recurring failure lessons.
- Generated references own exact field names and structured output shapes after conceptual docs explain the behavior.

Generated reports, historical reviews, and archived plans are audit/detail surfaces. They are not current authority unless promoted into code/tests/config, active Planning, Memory, docs, or accepted system intent.

Use `.agentic-workspace/docs/module-map.md` when a short installed-repo module map is enough and broader package docs would cost too much context.

## Closeout

For planned work, closeout is not only validation success. Separate proof, intent satisfaction, issue completion, durable residue, and dogfooding findings. Route future-relevant learning to Memory, docs, checks, contracts, config, Planning, or an issue. Do not keep completed execplans as the ordinary knowledge base.
