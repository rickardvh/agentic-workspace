# Required Follow-On Routing

## Goal

- Make required continuation for unfinished larger intent a first-class part of the planning contract so follow-on work is recorded in checked-in planning surfaces instead of prose or chat residue.

## Non-Goals

- Do not turn planning into a broad epic tracker.
- Do not require optional nice-to-have follow-ups to block archive.
- Do not add retrospective status journaling to active plans.

## Intent Continuity

- Larger intended outcome: planning should not let required follow-on for unfinished larger intent disappear into archived prose or chat residue.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md` candidate `Required follow-on routing follow-through`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `ROADMAP.md` candidate `Required follow-on routing follow-through`
- Activation trigger: promote when another bounded slice finishes part of a larger intended outcome and must leave an explicit next owner behind.

## Active Milestone

- ID: required-follow-on-routing
- Status: completed
- Scope: add first-class required-continuation fields to execplans, enforce them in the planning checker and archive flow, and teach cleanup to preserve explicit required follow-on owners.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed slice now that required follow-on routing is part of the contract and the broader continuation candidate is preserved in `ROADMAP.md`.

## Blockers

- None.

## Touched Paths

- `docs/execplans/README.md`
- `docs/execplans/TEMPLATE.md`
- `packages/planning/bootstrap/docs/execplans/README.md`
- `packages/planning/bootstrap/docs/execplans/TEMPLATE.md`
- `.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`
- `packages/planning/bootstrap/.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`
- `packages/planning/src/repo_planning_bootstrap/installer.py`
- `packages/planning/tests/test_check_planning_surfaces.py`
- `packages/planning/tests/test_installer.py`
- `ROADMAP.md`
- `TODO.md`

## Invariants

- Unfinished larger intent must keep one explicit checked-in owner after a slice completes.
- Required follow-on must be recorded as structured plan state, not only prose.
- Optional follow-up must not block archive if the larger intended outcome is actually complete.

## Validation Commands

- `uv run pytest packages/planning/tests/test_check_planning_surfaces.py`
- `uv run pytest packages/planning/tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`
- `make check`

## Completion Criteria

- Execplans include first-class required-continuation fields.
- Planning checks warn when unfinished larger intent lacks required follow-on owner or activation trigger.
- Archive flow blocks completed slices that leave required follow-on unrecorded.
- Cleanup preserves explicit required follow-on owners instead of deleting them as archived residue.

## Drift Log

- 2026-04-09: Promoted after dogfooding showed that intent continuity still needs explicit required-follow-on routing to keep larger work alive after bounded slice archive.
- 2026-04-09: Added first-class Required Continuation fields, archive gating, cleanup preservation, and regression coverage for follow-on ownership.
