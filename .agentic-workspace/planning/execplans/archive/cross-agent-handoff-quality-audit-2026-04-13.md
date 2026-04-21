# Cross-Agent Handoff Quality Audit

## Goal

- Audit whether the repo's current external-agent and restart surfaces preserve enough intent, active state, durable context, proof expectations, and next action to support cheap cross-agent continuation.
- Fix any concrete trust bug found in those surfaces through the canonical ownership path.

## Non-Goals

- Build a new cross-agent orchestration layer.
- Prove every possible multi-agent transition pattern.
- Reopen the already-landed mixed-agent contract boundary.

## Intent Continuity

- Larger intended outcome: contributors should be able to switch agents, subscriptions, or tools without repaying orientation cost that the repo could have persisted.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Delegated Judgment

- Requested outcome: inspect the external-agent and restart surfaces, repair any concrete drift found there, and route unrelated follow-on into the smallest more-appropriate backlog lane.
- Hard constraints: use the canonical workspace path rather than hand-editing generated or managed surfaces; do not widen this slice into general bootstrap-policy redesign.
- Agent may decide locally: which handoff surfaces to inspect first, whether the fix belongs in source or root install, and which remaining issue should be rerouted instead of kept here.
- Escalate when: the handoff drift cannot be fixed without broader lifecycle or ownership redesign.

## Active Milestone

- Status: completed
- Scope: audit `llms.txt`, `.agentic-workspace/bootstrap-handoff.md`, and the default-path contract; repair concrete handoff drift if found.
- Ready: completed
- Blocked: none
- optional_deps: GitHub issue `#25`

## Immediate Next Action

- Promote `Selective-adoption proof refresh` from the highest-priority queue.

## Blockers

- None.

## Touched Paths

- `ROADMAP.md`
- `TODO.md`
- `llms.txt`
- `.agentic-workspace/planning/execplans/archive/cross-agent-handoff-quality-audit-2026-04-13.md`

## Invariants

- `llms.txt` remains the canonical external-agent handoff surface.
- Bootstrap next-action state remains `.agentic-workspace/bootstrap-handoff.md` only when bootstrap actually leaves review-required work.
- Unrelated bootstrap-policy problems should route into the narrower bootstrap-hardening queue rather than staying in this audit lane.

## Open Questions Closed

- Handoff-surface trust question: a real drift bug existed. `llms.txt` had fallen behind the current workspace contract and contained a malformed code fence.
- Remediation-path question: the correct fix was the canonical workspace upgrade path, not manual root editing.
- Residual-scope question: the remaining AGENTS-preservation concern belongs under bootstrap-hardening follow-through, not under this broader handoff audit lane.

## Validation Commands

- `uv run agentic-workspace status --target .`
- `uv run agentic-workspace doctor --target .`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- The audit either finds no concrete issue or fixes the concrete handoff drift it finds.
- The workspace status/doctor surfaces confirm the handoff file is current afterward.
- The broader queue is narrowed rather than left carrying a spent trust bug.

## Execution Summary

- Outcome delivered: yes. The audit found and fixed a concrete `llms.txt` drift bug.
- Validation confirmed: yes. Workspace status and doctor now report `llms.txt` as current.
- Follow-on routed to: none.
- Resume from: promote selective-adoption proof refresh.

## Audit Outcome

- What was fixed:
- `llms.txt` was stale relative to the current workspace contract and no longer matched the expected external-agent handoff shape.
- Running `agentic-workspace upgrade --target .` refreshed `llms.txt` to the canonical external-agent handoff contract and cleared the warning.

- What remains elsewhere:
- The workspace upgrade path also attempted to rewrite repo-owned `AGENTS.md`; that preservation concern is real, but it belongs under bootstrap hardening and conservative policy follow-through rather than this broader handoff lane.

## Drift Log

- 2026-04-13: Promoted after the strong-planner / cheap-implementer proof refresh narrowed the next unresolved question to external-agent and restart surface trust.
- 2026-04-13: Completed after a real `llms.txt` drift bug was fixed through the canonical workspace upgrade path and the broader lane was retired.
