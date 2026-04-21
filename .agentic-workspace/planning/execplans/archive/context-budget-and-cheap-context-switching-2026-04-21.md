# Context Budget And Cheap Context Switching

Compact inactive-plan residue generated at archive time.
Use git history for superseded active-step detail; keep only the closure, continuation, proof, and cheap-resume residue here.

## Origin

- Archived from: .agentic-workspace/planning/execplans/context-budget-and-cheap-context-switching-2026-04-21.md

## Intent Continuity

- Larger Intended Outcome: Keep the live working set minimal, make context shifts cheaper and safer, and preserve only the residue needed for later reload, review, proof, or continuation.
- This Slice Completes The Larger Intended Outcome: yes
- Continuation Surface: none
- Parent Lane: `context-budget-and-cheap-context-switching`

## Required Continuation

- Required Follow-On For The Larger Intended Outcome: no
- Owner Surface: none
- Activation Trigger: none

## Delegated Judgment

- Requested Outcome: implement the context-budget and cheap-context-switching lane in full across planning contracts, projections, archive behavior, and mixed-agent resume surfaces.
- Hard Constraints: keep the solution compact, queryable, and repo-visible; do not invent a heavyweight context runtime or broad narrative archive system.
- Agent May Decide Locally: exact field names, the smallest shared context-budget form, archive-residue rendering details, and how to thread the contract through summary/report/handoff surfaces.
- Escalate When: the lane would require model-internals assumptions, a second planning state store, or a heavyweight orchestration framework.

## Context Budget

- Live Working Set: the active planning contract, archive behavior, resume/handoff projections, and the current issue cluster for this lane.
- Recoverable Later: older archived planning tranches, surrounding product-compression history, and broader package doctrine that can be reloaded from checked-in docs if needed.
- Externalize Before Shift: the exact next implementation slice, the remaining issue-closeout state, any archive-shape decisions, and the smallest mixed-agent resume cues that later work should not have to reconstruct.
- Tiny Resumability Note: keep the live-vs-recoverable-vs-externalize distinction explicit when touching summary, report, handoff, and archive surfaces.
- Context-Shift Triggers: shift when the active projection/archive tranche lands, when moving from planning contracts into another package domain, or when interruption/delegation stops the pass.

## Proof Report

- Validation proof: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest --no-cov packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run pytest --no-cov tests/test_workspace_cli.py -k "summary or report or defaults" -q`; `uv run agentic-planning-bootstrap verify-payload`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace summary --format json`; `uv run agentic-planning-bootstrap report --format json`.
- Proof achieved now: context-budget, cheap-resume, and inactive-residue behavior all land end to end across source, payload, and installed planning surfaces.
- Evidence for "proof achieved" state: active planning exposes `context_budget_contract` and hierarchy/handoff context-shift fields; archive output compacts completed execplans; payload verification passes; planning-surface checks are clean; targeted planning and workspace CLI tests pass.

## Intent Satisfaction

- Original intent: Implement the context-budget and cheap-context-switching lane in full.
- Was original intent fully satisfied?: yes
- Evidence of intent satisfaction: the lane now ships the context-budget contract, context-budget summary/report/handoff projections, compact inactive-plan residue, and mixed-agent cheap-resume guidance with passing proof.
- Unsolved intent passed to: none

## Closure Check

- Slice status: bounded slice complete
- Larger-intent status: closed
- Closure decision: archive-and-close
- Why this decision is honest: the lane-level context-budget outcome is now implemented across the planning contract, archive behavior, and mixed-agent resume path with no required continuation left in this lane.
- Evidence carried forward: the compact archived residue, the shipped context-budget contract, and the updated planning summary/report/handoff surfaces.
- Reopen trigger: none

## Execution Summary

- Outcome delivered: shipped a compact context-budget contract, added `context_budget_contract` plus hierarchy/handoff context-shift projections, made archive output compact inactive-plan residue, and aligned mixed-agent resume around the same checked-in planning surfaces.
- Validation confirmed: targeted planning package tests, workspace CLI selector tests, payload verification, planning-surface checks, planning report, and workspace summary all passed after source/payload/install sync.
- Follow-on routed to: none; the next independent work remains in the inactive roadmap queue.
- Knowledge promoted (memory/docs/config): `.agentic-workspace/docs/context-budget-contract.md`
- Resume from: promote `bounded-delegation-and-run-review` when the next bounded lane should start
