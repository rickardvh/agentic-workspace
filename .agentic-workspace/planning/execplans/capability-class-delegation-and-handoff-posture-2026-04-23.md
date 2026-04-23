# Capability-Class Delegation And Handoff Posture

## Goal

- Make planning and workflow contracts carry compact capability-class execution guidance that can be resolved against local targets without binding to one runtime.

## Non-Goals

- Do not turn workspace config into a scheduler.
- Do not hard-code vendor, model, or machine names into the durable work contract.
- Do not widen this slice into machine-first planning-chain work beyond the minimal active execplan updates needed here.

## Intent Continuity

- Larger intended outcome: let bounded work express weak, medium, strong, local, or external execution posture directly in the planning/workflow contract so runtime resolution stops depending on ambient local config alone.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: capability-class-delegation-and-handoff-posture

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger:

## Iterative Follow-Through

- What this slice enabled: planning-backed work can now declare typed capability posture, planning handoff can carry it, and workspace mixed-agent reporting can resolve it against local target hints.
- Intentionally deferred: richer workflow-engine semantics, full scheduler policy, and broader machine-first planning extraction.
- Discovered implications: the current lane can close without changing ownership boundaries because the new posture remains advisory and compact.
- Proof achieved now: milestone 1 is landed because the active execplan template, compact planning record, and delegated handoff view now carry typed capability posture.
- Validation still needed: finish workspace target-resolution follow-through, then run focused planning and workspace CLI tests plus compact contract checks together.
- Next likely slice: archive the lane and continue to the machine-first planning chain only if a new owner deliberately promotes it.

## Intent Interpretation

- Literal request: Implement the next lane in full, and commit after each milestone.
- Inferred intended outcome: close the next open roadmap lane with real shipped capability-class handoff behavior, not just more doctrine.
- Chosen concrete what: add a compact capability posture section to active planning work, project it through the handoff contract, resolve it against local target hints in workspace reporting, and retire the lane honestly.
- Interpretation distance: low
- Review guidance: reject the closeout if the new posture is still prose-only, cannot be queried compactly, or effectively behaves like runtime-specific scheduler policy.

## Execution Bounds

- Allowed paths: .agentic-workspace/docs/, .agentic-workspace/planning/, src/agentic_workspace/, packages/planning/src/repo_planning_bootstrap/, tests/, packages/planning/tests/
- Max changed files: 30
- Required validation commands: uv run pytest packages/planning/tests/test_installer.py -q -k capability; uv run pytest tests/test_workspace_cli.py -q -k delegation; uv run python scripts/check/check_contract_tooling_surfaces.py; uv run python scripts/check/check_planning_surfaces.py; uv run agentic-workspace summary --format json
- Ask-before-refactor threshold: stop before introducing a new runtime target registry, scheduler policy engine, or broad planning-storage redesign.
- Stop before touching: unrelated graceful-compliance work, machine-first planning-chain persistence refactors, or vendor-specific runtime integrations.

## Stop Conditions

- Stop when: the slice would require choosing exact execution targets in durable planning by default.
- Escalate when boundary reached: the work needs a broader workflow engine or a second config authority to express the posture safely.
- Escalate on scope drift: the lane spreads into machine-first planning-chain extraction or unrelated planning closure work.
- Escalate on proof failure: the planning handoff and workspace report cannot expose the same capability posture compactly after the new fields land.

## Context Budget

- Live working set: the current roadmap lane, planning handoff projection, workspace mixed-agent target profile reporting, local override schema, and focused CLI/planning tests for those surfaces.
- Recoverable later: older delegation doctrine, archived lane history, and broad architecture prose can be reloaded from compact summary plus the active plan.
- Externalize before shift: the typed capability posture shape, the runtime-resolution rule, milestone proof state, and lane-closeout decision.
- Pre-work config pull: ask which local override fields and compact defaults must reflect the new posture so resolution stays advisory and reviewable.
- Pre-work memory pull: ask whether any durable mixed-agent or planning dogfood evidence should shape the first capability-class field set before implementation.
- Tiny resumability note: keep the posture typed, advisory, and shared across planning handoff plus workspace resolution.
- Context-shift triggers: shift after a milestone commit, after proof passes or fails, or when the lane-closeout residue has been mirrored into planning.

## Delegated Judgment

- Requested outcome: close the capability-class delegation and handoff posture lane in full.
- Hard constraints: keep the contract vendor-generic, portable, compact, and advisory; preserve checked-in planning as authority; avoid turning config into a scheduler.
- Agent may decide locally: the minimum capability posture field set, the narrowest local target-profile additions needed for resolution, the exact milestone split, and the smallest doc/test refresh that keeps the lane honest.
- Escalate when: the requested outcome would require hard target binding, scheduler-like orchestration, or a second durable execution authority.

## Capability Posture

- Execution class: boundary-shaping
- Recommended strength: strong
- Preferred location: either
- Delegation friendly: yes
- Strong external reasoning: allowed
- Why: the lane changes cross-cutting planning and workspace contracts, so the shaping pass benefits from stronger judgment before bounded implementation and validation.

## Active Milestone

- ID: milestone-2
- Status: in-progress
- Scope: extend workspace mixed-agent target profiles and execution-shape reporting so the active capability posture resolves against available local targets compactly.
- Ready: ready
- Blocked: none
- Optional_deps: milestone-3 lane closeout and archive

## Immediate Next Action

- Extend local target-profile metadata and workspace reporting so the active capability posture resolves without turning local config into scheduler policy.

## Blockers

- None.

## Touched Paths

- .agentic-workspace/planning/state.toml
- .agentic-workspace/planning/execplans/capability-class-delegation-and-handoff-posture-2026-04-23.md
- .agentic-workspace/planning/execplans/TEMPLATE.plan.json
- packages/planning/src/repo_planning_bootstrap/installer.py
- packages/planning/src/repo_planning_bootstrap/cli.py
- packages/planning/tests/test_installer.py

## Invariants

- Planning remains the owner of active work contracts.
- Capability posture stays advisory and vendor-generic.
- Local runtime resolution remains separate from checked-in lane shaping.

## Contract Decisions To Freeze

- The capability posture field set stays compact and typed.
- Planning handoff carries capability posture directly instead of inferring it from chat.
- Workspace resolution matches against local target hints without turning into scheduler policy.

## Open Questions To Close

- Which minimal target-profile fields are necessary to resolve local versus external preference honestly?
- Should stronger-than-requested targets count as acceptable but lower-preference matches for advisory resolution?

## Validation Commands

- uv run pytest packages/planning/tests/test_installer.py -q -k capability
- uv run pytest tests/test_workspace_cli.py -q -k delegation
- uv run python scripts/check/check_contract_tooling_surfaces.py
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-workspace summary --format json

## Required Tools

- gh

## Completion Criteria

- Active planning and handoff surfaces expose a typed capability posture.
- Workspace mixed-agent reporting resolves that posture against configured local targets compactly.
- Docs and tests describe the posture as advisory rather than scheduler policy.
- The lane can archive honestly and the related GitHub issues can close without a follow-on owner.

## Execution Run

- Run status: in-progress
- Executor: Codex
- Handoff source: agentic-planning-bootstrap handoff --format json
- What happened: activated the lane in checked-in planning, added typed capability posture to the active execplan template, and projected that posture through the compact planning record plus delegated handoff contract.
- Scope touched: .agentic-workspace/planning state and execplan surfaces plus planning installer, CLI, and focused planning tests.
- Changed surfaces: .agentic-workspace/planning/state.toml; .agentic-workspace/planning/execplans/capability-class-delegation-and-handoff-posture-2026-04-23.md; .agentic-workspace/planning/execplans/TEMPLATE.plan.json; packages/planning/src/repo_planning_bootstrap/installer.py; packages/planning/src/repo_planning_bootstrap/cli.py; packages/planning/tests/test_installer.py
- Validations run: uv run pytest packages/planning/tests/test_installer.py -q -k handoff; uv run python scripts/check/check_planning_surfaces.py; uv run agentic-workspace summary --format json
- Result for continuation: workspace still needs to resolve the new posture against local target hints before the lane can close.
- Next step: implement milestone 2 and commit it.

## Finished-Run Review

- Review status: pending
- Scope respected: pending
- Proof status: pending
- Intent served: pending
- Config compliance: pending
- Misinterpretation risk: pending
- Follow-on decision: pending

## Execution Summary

- Outcome delivered: not completed yet
- Validation confirmed: pending
- Follow-on routed to: none yet
- Post-work posterity capture: pending
- Knowledge promoted (Memory/Docs/Config): pending
- Resume from: current milestone

## Closure Check

- Slice status: in progress
- Larger-intent status: open
- Closure decision: keep-active
- Why this decision is honest: the capability posture is not yet projected through planning handoff and workspace resolution together.
- Evidence carried forward: active execplan plus roadmap lane state.
- Reopen trigger: finish the bounded milestones and reassess the lane closeout.

## Drift Log

- 2026-04-23: Activated the capability-class delegation and handoff posture lane for end-to-end execution.
