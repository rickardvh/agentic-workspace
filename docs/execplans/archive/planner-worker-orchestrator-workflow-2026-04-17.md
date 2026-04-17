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
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: planner-worker-orchestrator-workflow

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: planning can emit a reusable delegated handoff contract and a bundled workflow for orchestrated execution instead of relying on handwritten prompts alone.
- Intentionally deferred: any future runtime-specific adapter or CLI helper beyond the first agent-agnostic contract and skill.
- Discovered implications: the base handoff is strong enough to carry a delegated slice, but target capability confidence still belongs in a local-only advisory layer rather than in repo-owned planning policy.
- Proof achieved now: the reusable handoff command, bundled skill, relay/config integration, and one real delegated docs slice all completed cleanly.
- Validation still needed: none for this lane beyond archive and issue closure.
- Next likely slice: promote `#172` if local target-confidence notes are worth productizing as the next delegation-cost reduction.

## Delegated Judgment

- Requested outcome: define and ship a formal delegated workflow that uses the existing local mixed-agent posture, stays agent-agnostic, and supports internal delegation or external CLI/API handoff without making the repo prescriptive about executor choice.
- Hard constraints: keep repo-owned planning canonical; settings stay in local config rather than checked-in scheduler policy; use the existing planner/implementer posture fields instead of inventing new preference sprawl; preserve one-home ownership for planning state; keep the workflow usable for internal delegation, local models, or other vendors.
- Agent may decide locally: exact contract field shape, whether the formal workflow lives as a skill plus command or equivalent checked-in surface, how to dogfood the new workflow on one bounded slice, and which narrow validations prove the tranche.
- Escalate when: a proposed workflow surface starts dictating runtime routing by vendor/model, requires hidden repo-local state, or cannot remain useful when delegation happens outside this runtime.

## Active Milestone

- ID: planner-worker-workflow-contract
- Status: completed
- Scope: shipped the first reusable delegated handoff contract and bundled workflow, then proved it on one real delegated slice.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this lane, close `#171`, and route the local target-confidence follow-on into `ROADMAP.md` as `#172`.

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

- Outcome delivered: the repo now ships a formal orchestrator workflow contract, a reusable `agentic-planning-bootstrap handoff --format json` surface, a bundled `planning-orchestrator-workflow` skill, and front-door docs that explain how the local mixed-agent posture and active handoff fit together.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace defaults --section relay --format json`; `uv run agentic-planning-bootstrap handoff --format json`.
- Follow-on routed to: `docs/reviews/orchestrator-workflow-dogfood-2026-04-17.md`, GitHub issue `#172`, and `ROADMAP.md`.
- Resume from: `#172` if local delegation-target capability/confidence support is promoted.

## Drift Log

- 2026-04-17: Promoted from roadmap issue `#171` immediately after the planning-surface-clarity dogfood pass showed the workflow value was real but still too manual.
- 2026-04-17: Core workflow tranche landed with a reusable handoff command, bundled orchestrator skill, and relay/config integration; next proof is a real delegated slice on top of that contract.
- 2026-04-17: Delegated docs dogfood pass landed through the new workflow and confirmed the next uncovered cost class is local target-confidence, not repo-owned orchestration policy.
