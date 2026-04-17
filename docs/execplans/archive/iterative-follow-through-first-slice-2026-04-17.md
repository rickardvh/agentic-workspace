# Iterative Follow-Through First Slice

## Goal

- Add one compact iterative follow-through contract to planning so bounded slices can stop intentionally without losing deferred work, discovered implications, or proof/validation carry-forward.

## Non-Goals

- Rework the broader planning system into long-range roadmap tracking.
- Add a second canonical planning record separate from `planning_record`.
- Expand into optimization-bias or setup-findings promotion in the same slice.

## Intent Continuity

- Larger intended outcome: Planning preserves iterative carry-forward as first-class checked-in residue for bounded slices that stop before the broader goal is complete.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: Planning now exposes iterative carry-forward as a queryable `follow_through_contract` projection backed by a stable execplan section.
- Intentionally deferred: none
- Discovered implications: The contract only stays trustworthy when package source, payload docs, root installed surfaces, and the checker all move together.
- Proof achieved now: The active execplan, summary output, checker, and payload docs all agree on the new section and projection.
- Validation still needed: none beyond ordinary future dogfooding on later bounded slices.
- Next likely slice: Move to the output/residue optimization-bias lane unless future ordinary work exposes another follow-through gap.

## Delegated Judgment

- Requested outcome: Land the first compact follow-through contract and expose it through planning summary, payload docs, and one real dogfood plan.
- Hard constraints: Keep the change as a thin projection over existing planning state and stable execplan sections; do not invent a second planning authority.
- Agent may decide locally: Exact field names, whether the residue lives in a dedicated execplan section or a narrow extension of the current closure contract, and the narrowest validation that proves source/payload/root alignment.
- Escalate when: The best-looking change would turn this into broad roadmap semantics, force long narrative plans, or require a second canonical summary record.

## Active Milestone

- ID: iterative-follow-through-first-slice
- Status: completed
- Scope: Add the first compact iterative carry-forward contract and dogfood it on this plan.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed slice, close issue `#128`, and advance the roadmap to the optimization-bias lane.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/iterative-follow-through-first-slice-2026-04-17.md
- packages/planning/src/repo_planning_bootstrap/installer.py
- packages/planning/src/repo_planning_bootstrap/cli.py
- packages/planning/bootstrap/docs/execplans/TEMPLATE.md
- packages/planning/bootstrap/docs/execplans/README.md
- packages/planning/bootstrap/docs/execution-summary-contract.md
- packages/planning/bootstrap/docs/iterative-follow-through-contract.md
- packages/planning/bootstrap/docs/intent-contract.md
- packages/planning/bootstrap/.agentic-workspace/planning/scripts/check/check_planning_surfaces.py
- packages/planning/README.md
- packages/planning/tests/test_installer.py
- packages/planning/tests/test_check_planning_surfaces.py

## Invariants

- `planning_record` stays canonical.
- The new contract must reduce rereading rather than create a second notebook surface.
- Any follow-through fields must distinguish intentional deferral from newly discovered implications.

## Contract Decisions To Freeze

- Preserve iterative follow-through as a projection over existing planning state rather than a new authority.
- Keep the carry-forward contract compact enough for weaker agents to query directly.

## Open Questions To Close

- Which minimum fields are necessary to separate deferred work from discovered implications without turning the section into a backlog dump?
- How should the contract relate to `Execution Summary`, `Intent Continuity`, and `Required Continuation` without duplicating them?

## Validation Commands

- uv run pytest packages/planning/tests/test_installer.py -q
- uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q
- uv run python scripts/check/check_planning_surfaces.py

## Required Tools

- uv

## Completion Criteria

- Planning summary exposes a compact iterative follow-through projection derived from the active execplan when present.
- The execplan template and package docs define the contract clearly enough for ordinary bounded slices.
- This active plan itself dogfoods the new section without conflicting with existing closure and continuation sections.

## Execution Summary

- Outcome delivered: Added the `Iterative Follow-Through` execplan section, the `follow_through_contract` planning summary projection, and the matching package/root contract docs and checker support.
- Validation confirmed: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap summary --format json`
- Follow-on routed to: `ROADMAP.md` next candidate `Output/residue optimization bias`
- Resume from: No further action in this plan; start from the next roadmap lane when another bounded slice is promoted.

## Drift Log

- 2026-04-17: Promoted issue #128 from the roadmap into an active first-slice execplan.
- 2026-04-17: Landed the first iterative follow-through contract, refreshed the root install, and prepared the plan for archive.
