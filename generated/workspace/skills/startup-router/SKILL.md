---
name: generated-startup-router
description: Generated SkillSpec target projection for Agentic Workspace startup routing. Use as a compact adapter target, not as the source of product behavior.
---

# Generated Startup Router Skill

Generated from `src/agentic_workspace/contracts/skill_specs.json`. Do not hand-edit generated output.

## Applies When
- An agent begins or resumes work in a repository before opening broad workspace state.
- The task shape, active planning state, or applicable package skill is not yet known.

## Preferred CLI
- `uv run agentic-workspace start --task "<task>" --format json`
- Purpose: Resolve work shape, active state, skill routing, next-safe-action, proof hints, and proportional read budget before raw workspace reads.
- Mutates state: false

## Interpret These Fields
- `immediate_next_allowed_action`: The next allowed action before any broad file reads.
- `skill_routing.preferred_routes`: The skill guidance to load when task-specific instructions are useful.
- `next_safe_action.implementation_allowed`: Whether implementation can start without additional planning or proof setup.

## Allowed Actions
- Run the configured startup CLI command before broad workspace inspection.
- Use selector or detail commands when compact output identifies the needed field.
- Proceed with direct work when compact routing permits it and proof is obvious.

## Forbidden Actions
- Open raw planning or memory state before compact startup routing points there.
- Create planning, review, memory, or handoff artifacts for routine direct work.
- Treat generated skill or adapter output as the source of product behavior.

## No-CLI Fallback
- Read `.agentic-workspace/WORKFLOW.md` before other workspace files.
- Use the smallest safe manual path and preserve no-artifact-by-default behavior.
- Escalate to planning only when the work shape, risk, or continuation need requires durable state.

## Proof And Closeout
- Use the proof command or compact proof hints before claiming completion.
- For direct work, name the narrow validation or inspection that proves the change.
- Report delivered behavior, proof, and any deferred scope.
- Do not claim completion when compact routing reports closure blockers or missing continuation ownership.

## Generated Target Contract
- CLI-first startup routing when available.
- Conservative no-CLI fallback.
- No-artifact-by-default behavior for ordinary direct work.
- Forbidden raw planning/memory reads before compact routing.

## Behavior Fixture
- Direct task: continue without durable artifacts only when compact routing permits it and proof is obvious.
- Lane or epic task: block implementation until compact routing, planning ownership, and proof expectations are present.
- Fallback task: when the CLI is unavailable, read the workflow fallback and preserve forbidden actions.
