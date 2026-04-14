# GitHub Issues 69-72 Follow-Through

## Goal

- Close the remaining open GitHub intake tranche issues in priority order, starting after the already-implemented `#65` and `#66` slice.

## Non-Goals

- Do not widen the scope beyond the eight-item intake tranche.
- Do not add new product concepts unrelated to the listed issues.
- Do not collapse planning, memory, and workspace ownership boundaries.

## Intent Continuity

- Larger intended outcome: ingest the open GitHub intake tranche into checked-in planning and implement the resulting work in priority order.
- This slice completes the larger intended outcome: no
- Continuation surface: TODO.md and this execplan

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: TODO.md
- Activation trigger: when the current milestone is completed and the next tranche item is ready to implement

## Delegated Judgment

- Requested outcome: implement the remaining open intake tranche in priority order and commit after each milestone.
- Hard constraints: keep each milestone bounded, preserve repo/package ownership boundaries, and keep the checked-in planning surfaces current.
- Agent may decide locally: narrow implementation shape, validation scope, and whether multiple related issue requirements belong in one bounded milestone.
- Escalate when: a proposed fix changes the requested outcome, owned surface, or time horizon, or when the minimal safe implementation is unclear.

## Active Milestone

- Status: in-progress
- Scope: implement the setup command tranche first, then the execplan guidance tranche, then memory doctor signal tuning.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Implement a public `agentic-workspace setup` command that stays separate from `proof` and can say when no new seed surfaces are needed.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- src/agentic_workspace/cli.py
- tests/test_workspace_cli.py
- docs/jumpstart-contract.md
- docs/default-path-contract.md
- docs/workspace-config-contract.md
- docs/execplans/
- packages/planning/tests/test_installer.py
- packages/memory/src/repo_memory_bootstrap/
- packages/memory/tests/

## Invariants

- Issue work proceeds in roadmap priority order.
- Each milestone gets its own commit.
- Setup remains bounded and distinct from proof.
- Existing repo-owned config and planning contracts stay authoritative.

## Contract Decisions To Freeze

- Setup gets a real public command instead of relying on `defaults` as a concept-only surface.
- The setup command should stay compact and should not spill into the full proof backlog.
- Mature repos should be able to get an explicit no-new-seed-surface result.
- Repo-owned execplan upgrades should surface clearer guidance rather than only generic drift pressure.
- Memory doctor should keep useful warnings while lowering low-signal overlap pressure for mature custom corpora.

## Open Questions To Close

- What exact compact shape should the new `setup` command expose?
- Which setup recommendation, if any, should `skills --task setup` surface?
- Which execplan upgrade warnings should become migration hints versus standard drift?
- Which memory doctor advisories should be downgraded or reclassified for mature corpora?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q -k "setup or config_command or skills"`
- `uv run pytest tests/test_maintainer_surfaces.py -q`
- `uv run pytest packages/planning/tests/test_installer.py -q -k "render_wrapper or config or upgrade"`
- `uv run pytest packages/memory/tests -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run python scripts/check/check_maintainer_surfaces.py`

## Completion Criteria

- The remaining open intake tranche issues are implemented in priority order.
- Each milestone has been committed separately.
- The roadmap no longer needs the tranche entries once the corresponding work is complete.

## Execution Summary

- Outcome delivered: pending
- Validation confirmed: pending
- Follow-on routed to: TODO.md
- Resume from: current milestone
- Product improvement signal: pending

## Drift Log

- 2026-04-14: Promoted the remaining open intake tranche into a single bounded execplan after the top two priority issues had already been implemented locally.
