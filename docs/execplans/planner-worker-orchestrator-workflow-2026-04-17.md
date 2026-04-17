# Planner-Worker Orchestrator Workflow

## Goal

- Productize the planner-to-worker delegated workflow so lane-scale execution can use a reusable checked-in handoff instead of ad hoc prompting, while staying agent-agnostic and local-config-driven.

## Non-Goals

- Turn the repo into a scheduler for runtime model or vendor choice.
- Require only internal subagents or only external delegation.
- Make planning own account-specific or machine-specific preferences that already belong in `agentic-workspace.local.toml`.
- Replace the canonical planning surfaces with a second durable state store.

## Intent Continuity

- Larger intended outcome: make delegated execution cheaper than ad hoc prompting while preserving checked-in continuity across agents, tools, subscriptions, and local models.
- This slice completes the larger intended outcome: no
- Continuation surface: ROADMAP.md
- Parent lane: planner-worker-orchestrator-workflow

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: ROADMAP.md
- Activation trigger: when this lane either reveals another repeated workflow-cost class or leaves one unresolved boundary that still needs a later bounded slice.

## Iterative Follow-Through

- What this slice enabled: planning can emit a reusable delegated handoff contract and a bundled workflow for orchestrated execution instead of relying on handwritten prompts alone.
- Intentionally deferred: any future runtime-specific adapter or CLI helper beyond the first agent-agnostic contract and skill.
- Discovered implications: the first derived handoff is good enough for lane-level continuity but still too broad to be a perfect worker write-scope without an explicit slice assignment from the orchestrator.
- Proof achieved now: the reusable handoff command, bundled skill, and relay/default-path reporting surfaces are implemented and queryable.
- Validation still needed: one real delegated dogfood pass using the new workflow, then closure routing for any remaining workflow-cost class.
- Next likely slice: dogfood the workflow on a bounded docs-only delegated slice, then decide whether narrow slice-assignment support or local target-capability notes should become the next candidate.

## Delegated Judgment

- Requested outcome: define and ship a formal delegated workflow that uses the existing local mixed-agent posture, stays agent-agnostic, and supports internal delegation or external CLI/API handoff without making the repo prescriptive about executor choice.
- Hard constraints: keep repo-owned planning canonical; settings stay in local config rather than checked-in scheduler policy; use the existing planner/implementer posture fields instead of inventing new preference sprawl; preserve one-home ownership for planning state; keep the workflow usable for internal delegation, local models, or other vendors.
- Agent may decide locally: exact contract field shape, whether the formal workflow lives as a skill plus command or equivalent checked-in surface, how to dogfood the new workflow on one bounded slice, and which narrow validations prove the tranche.
- Escalate when: a proposed workflow surface starts dictating runtime routing by vendor/model, requires hidden repo-local state, or cannot remain useful when delegation happens outside this runtime.

## Active Milestone

- ID: planner-worker-workflow-contract
- Status: in-progress
- Scope: ship the first reusable delegated handoff contract and bundled workflow, then prove it on one real delegated slice.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Use the new handoff contract and skill on one bounded delegated docs slice, then capture the remaining workflow friction in checked-in evidence.

## Blockers

- None.

## Touched Paths

- TODO.md
- docs/execplans/planner-worker-orchestrator-workflow-2026-04-17.md
- docs/
- packages/planning/src/
- packages/planning/bootstrap/
- packages/planning/skills/
- packages/planning/tests/
- src/agentic_workspace/cli.py
- tests/test_workspace_cli.py

## Invariants

- Runtime execution method stays tool-owned and agent-agnostic.
- Local capability and cost posture stays in `agentic-workspace.local.toml`, not checked-in repo config.
- The workflow must remain usable whether delegation is internal, external over CLI/API, or unavailable.
- Durable continuity must remain in checked-in planning surfaces rather than in tool-local subagent state alone.

## Contract Decisions To Freeze

- The reusable worker handoff should be derivable from active planning state rather than authored from scratch every run.
- The formal workflow should describe boundaries and handoff shape, not prescribe vendor-specific executor routing.
- Worker-owned closure should be explicit and bounded; lane shaping, roadmap routing, and product-shape decisions remain orchestrator-owned.
- The existing mixed-agent posture fields should remain the only local settings this workflow depends on.

## Open Questions To Close

- Which handoff fields are genuinely needed to keep an external or smaller worker bounded without broad rereads?
- Which cleanup and validation steps can safely move into the worker contract by default?
- What is the smallest formal workflow surface that still works across internal delegation and external CLI/API delegation?

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q
- uv run pytest packages/planning/tests/test_installer.py -q
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-workspace defaults --section relay --format json
- uv run agentic-workspace config --target . --format json
- uv run agentic-planning-bootstrap handoff --format json

## Required Tools

- uv
- gh

## Completion Criteria

- A formal delegated workflow exists in shipped checked-in surfaces.
- The workflow uses the existing local mixed-agent posture instead of inventing a scheduler.
- A reusable handoff can be derived from active planning state for internal or external delegation.
- One real delegated dogfood pass uses the new workflow and captures evidence about remaining cost or friction.

## Execution Summary

- Outcome delivered: pending
- Validation confirmed: pending
- Follow-on routed to: pending
- Resume from: current milestone

## Drift Log

- 2026-04-17: Promoted from roadmap issue `#171` immediately after the planning-surface-clarity dogfood pass showed the workflow value was real but still too manual.
- 2026-04-17: Core workflow tranche landed with a reusable handoff command, bundled orchestrator skill, and relay/config integration; next proof is a real delegated slice on top of that contract.
