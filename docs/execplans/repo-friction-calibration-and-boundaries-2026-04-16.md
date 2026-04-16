# Repo Friction Calibration And Boundaries

## Goal

- Finish the current top-priority improvement-latitude lane by calibrating it from real repo-friction signals, freezing the boundary test for local improvement versus changed task, and keeping the ownership of policy/evidence explicitly workspace-level.

## Non-Goals

- Do not add a new core module.
- Do not turn repo-friction evidence into heavy telemetry or a generic code-quality platform.
- Do not turn improvement latitude into a scheduler or a loophole for broad unsignaled refactors.
- Do not broaden this slice into optimization-bias or broader planning-residue work.

## Intent Continuity

- Larger intended outcome: make bounded repo-friction reduction safe, evidence-backed, and cheap enough that agent-driven repos can stay cleaner with less human moderation burden.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Convergence Context

- Larger intended outcome: workspace-level policy and evidence should lower moderation burden without adding a new top-level product concept.
- Convergence owner: workspace config/reporting/contracts
- What must remain intact after interruption: repo-friction policy and evidence stay workspace-level, proof/ownership/delegated-judgment remain authoritative boundaries, and the shipped default remains evidence-backed rather than preference-only.
- Current interruption boundary: this tranche only needs one additional evidence class, one compact boundary test, and one bounded audit/review outcome.

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Delegated Judgment

- Requested outcome: complete the current roadmap lane in the smallest honest tranche that closes or narrows the live issues.
- Hard constraints: keep the work inside workspace/reporting/planning contracts, avoid new modules or hidden state, and prove the calibration with bounded repo evidence rather than chat preference.
- Agent may decide locally: the exact concept-friction evidence shape, the smallest audit sample that still proves the calibration point, and the minimum docs/tests to update.
- Escalate when: the tranche would require a heavier analyzer, a new state file, or a change in canonical planning/memory semantics.

## Active Milestone

- Status: in progress
- Scope: add concept-friction evidence, make the boundary test queryable, and archive one bounded audit that calibrates the repo posture.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Run the bounded calibration review against current repo-friction evidence and recent agent-driven work, then use it to close or narrow the remaining top-priority issues.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/`
- `docs/workspace-config-contract.md`
- `docs/reporting-contract.md`
- `docs/delegated-judgment-contract.md`
- `docs/design-principles.md`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`
- `docs/reviews/`

## Invariants

- Improvement-latitude policy and repo-friction evidence remain shared workspace-level surfaces.
- Repo-friction evidence remains derived and queryable rather than a second editable state store.
- Improvement initiative may widen means only; it must not silently rewrite requested ends or proof scope.
- The repo-owned config stays the only checked-in policy surface for this lane.

## Contract Decisions To Freeze

- Repo-friction calibration for this lane should stay inside workspace reporting/defaults/contracts rather than becoming a new module.
- One concept-friction evidence class is enough for this tranche if it is queryable and clearly bounded.
- The shipped boundary test must answer when friction reduction is still local means versus a changed task.

## Open Questions To Close

- Which concept-friction signal is small enough to ship now without inventing a weak proxy?
- What is the smallest bounded audit shape that justifies the repo's current `proactive` posture honestly?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-workspace defaults --section improvement_latitude --format json`
- `uv run agentic-workspace report --target . --format json`
- `git diff --check`

## Required Tools

- `uv`
- `gh`

## Completion Criteria

- The workspace report exposes at least one compact concept-friction evidence class in addition to code hotspots.
- `agentic-workspace defaults --section improvement_latitude --format json` answers the local-improvement versus changed-task test in structured form.
- The docs freeze the workspace-level ownership rule for this lane.
- A bounded review or audit captures whether recent agent-driven work is increasing or reducing repo friction and uses that result to justify the current posture.
- The current top-priority issues are closed or narrowed accurately after the tranche lands.

## Execution Summary

- Outcome delivered: pending
- Validation confirmed: pending
- Follow-on routed to: pending
- Resume from: pending

## Drift Log

- 2026-04-16: Promoted after the first improvement-latitude slice and the `#130` follow-on landed; the remaining top-priority lane is now calibration, boundaries, and closure rather than new policy invention.
- 2026-04-16: Extended the workspace report/defaults contract with concept-surface hotspots, a queryable local-improvement decision test, and an explicit workspace-level ownership rule for repo-friction policy and evidence.
