# Delegated Judgment Operational Follow-Through

## Goal

- Make delegated judgment operational in active execplans rather than leaving it as a separate doctrine page.

## Non-Goals

- Build a new approval workflow.
- Add heavy process to direct tasks.
- Turn planning into a generic permissions engine.

## Intent Continuity

- Larger intended outcome: Finish the bounded delegated-judgment capability so broad direction can survive across sessions without silent scope inflation.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Delegated Judgment

- Requested outcome: Operationalize delegated judgment inside the planning contract so active execplans preserve intended outcome, hard constraints, allowed local latitude, and escalation triggers explicitly.
- Hard constraints: Keep the change inside planning and delegated-judgment contract surfaces; do not invent a broader approval system or widen direct-task ceremony.
- Agent may decide locally: Add the compact execplan section, enforce it in planning checks and archive flow, update payload copies and tests, and use this slice to dogfood the result.
- Escalate when: The cleaner fix requires changing planning ownership, adding new top-level workflow surfaces, or forcing heavy delegated-judgment structure onto simple direct tasks.

## Active Milestone

- Status: completed
- Scope: wire delegated judgment into the execplan template, checker, archive helper, and planning docs with regression coverage.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Finish the planning and test updates, then validate the package and root planning surfaces under the new section.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `.agentic-workspace/planning/execplans/`
- `docs/delegated-judgment-contract.md`
- `packages/planning/`
- `.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`

## Invariants

- Keep delegated judgment compact and execution-shaped.
- Preserve cheap direct execution for truly local work.
- Make archive fail closed when an active plan did not preserve the delegated-judgment boundary it depended on.

## Contract Decisions To Freeze

- Delegated judgment should be part of active execplan shape, not a separate optional note when the work is broad enough to need a plan.
- The compact section should preserve requested outcome, hard constraints, allowed local latitude, and escalation triggers.
- Enforcement should stay in the existing planning checker and archive path rather than creating a second review lane.

## Open Questions To Close

- No blocking open questions remain for this slice.

## Validation Commands

- `uv run pytest packages/planning/tests/test_check_planning_surfaces.py`
- `uv run pytest packages/planning/tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-planning-bootstrap upgrade --target .`

## Completion Criteria

- Execplan docs and scaffold include `## Delegated Judgment`.
- Planning checks warn when active execplans omit delegated-judgment fields.
- Archive fails closed when delegated-judgment fields are missing.
- This slice archives cleanly using the new contract.

## Execution Summary

- Outcome delivered: Active execplans now carry a compact delegated-judgment section, the planning checker warns when it is missing, archive fails closed when delegated-judgment fields are absent, and promoted plans scaffold the section automatically.
- Validation confirmed: `uv run pytest packages/planning/tests/test_check_planning_surfaces.py`; `uv run pytest packages/planning/tests/test_installer.py`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `make maintainer-surfaces`
- Follow-on routed to: none
- Resume from: no further delegated-judgment follow-through is queued right now

## Drift Log

- 2026-04-10: Promoted directly from maintainer choice after the capability review identified operational follow-through as the main remaining delegated-judgment gap.
