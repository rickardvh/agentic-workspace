---
name: workspace-startup
description: Use the main Agentic Workspace operating loop in an installed AW repo. Start from the configured compact router, preserve routed actions and proof boundaries, and load specialized AW skills only when routed.
---

# Workspace Startup / Operating Loop

Use this skill for ordinary AW startup, resume, changed-path implementation, proof approach, closeout, or routed fallback in an installed Agentic Workspace repo.
When Agentic Workspace is enabled, this is the canonical main operating skill. Advisory skill routing and `implementation_allowed` never bypass startup, Planning gates, proof, or closeout.

Do not use this as a broad manual. Load specialized AW subskills only when the compact router, task shape, or this skill names their narrower job.

## Configured Invocation

Use the configured AW invocation exposed by the repo adapter, config, or compact startup/config output. In an installed repo this may look like `agentic-workspace ...`; in a source checkout or dev-dependency install it may be a repo-local command. Do not prefer a bare selector when adapter/config names a different invocation.

## Procedure

1. Run the configured invocation with `start --target . --task "<task>" --format json` for ordinary first contact.
2. If changed paths are already known, run the configured invocation with `implement --target . --changed <paths> --task "<task>" --format json`.
3. Preserve `module_slot`, `next_safe_action`, `allowed_actions`, `forbidden_actions`, `proof_required`, and `completion_claim_allowed`.
4. Follow `next_safe_action` before opening raw `.agentic-workspace/` files or running drill-down commands.
5. Keep direct work direct when the router allows no-artifact work; do not create Planning, Memory, review, or handoff artifacts just to show work.
6. Load specialized subskills only for routed intent/shape, proof, setup, or fallback/reference needs.
7. Before claiming completion, reconcile intent, proof, residue, issue/PR closure, and next owner separately.

## Planning Route Contract

When startup exposes `planning_safety_gate.route_decision`, consume that object as the authoritative Planning route. Do not independently reclassify task-switch prose or choose from legacy route menus.

- Follow its `next_safe_action`, `required_transition`, `implementation_allowed`, `mutation_authority`, claim boundaries, proof expectation, and state-update policy together.
- A `required_transition = none` route is read-only Planning orientation by default: do not create carry, owner-selection, or route-residue state merely because startup ran.
- If `route_decision.binding.status` is `provisional`, perform the named branch/worktree/repository/target/owner transition first, then rerun startup before any Planning mutation or route adoption.
- Ask for user direction only when the route reports genuine ambiguity or missing authority; a bounded independent route may proceed while preserving the selected owner’s claim boundary.

## Subskill Routes

- `workspace-intent-discovery`: ambiguous human intent, vague outcome prompts, or direct/bounded/lane/epic work-shape decisions.
- `workspace-proof-selection`: proof selection or interpretation for task, slice, lane, epic, skipped, warning, retry, crash, or negative evidence.
- `workspace-setup-jumpstart`: newly installed or adopted AW in a lived-in repo that needs bounded post-bootstrap seeding.
- `workspace-operating-loop` / `workspace-transition-gates`: reference support only when `module_slot`, `forbidden_actions`, preferred invocation fallback, or transition gate details need interpretation.

## Red Flags

Red flag:
  I can inspect raw planning or memory files first because the request seems simple.

Use instead:
  Run the configured invocation with `start --target . --task "<task>" --format json`, or the known dedicated AW command when the request already names one, then follow `next_safe_action`.

## SkillSpec Pilot

This skill is the hand-authored startup pilot for the `startup-router` SkillSpec contract in `src/agentic_workspace/contracts/skill_specs.json`.

- Preferred route: configured AW invocation with `start --target . --task "<task>" --format json`.
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
