# Required Follow-On Routing Follow-Through

## Goal

- Make required follow-on routing part of the normal Planning contract surfaces so maintainers and agents can rely on it going forward without re-deriving the rule from archived execplans or tests.

## Non-Goals

- Do not add new planning mechanics if the current contract is already sufficient.
- Do not reopen the broader bounded delegated judgment capability model.
- Do not leave another continuation candidate behind for this same capability unless validation exposes a fresh defect.

## Intent Continuity

- Larger intended outcome: the planning system should preserve parent intent and required continuation as standard behavior during normal use, not as a one-off dogfood fix.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Active Milestone

- ID: required-follow-on-routing-follow-through
- Status: completed
- Scope: update the main planning-facing docs and startup guidance so required follow-on routing is part of the discoverable everyday contract, then validate and archive the capability tranche.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed slice now that required follow-on routing is part of the normal planning-facing contract and no roadmap candidate remains for this capability.

## Blockers

- None.

## Touched Paths

- `packages/planning/README.md`
- `docs/contributor-playbook.md`
- `packages/planning/bootstrap/AGENTS.md`
- `packages/planning/tests/test_installer.py`
- `ROADMAP.md`
- `TODO.md`

## Invariants

- Required follow-on remains a planning concern, not chat residue.
- The front-door contract stays compact and bounded.
- This slice should end with no remaining roadmap candidate for the same capability unless validation finds a fresh gap.

## Validation Commands

- `uv run pytest packages/planning/tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`
- `make check`

## Completion Criteria

- Normal planning-facing docs describe required follow-on routing as part of the default contract.
- Bootstrap guidance tells agents not to close a bounded slice with required continuation only in prose or chat.
- The remaining roadmap candidate for this capability is removed.
- The slice archives cleanly and the active queue returns to empty.

## Drift Log

- 2026-04-09: Promoted to finish the capability as a normal discoverable contract rather than leaving the last piece implied by archived dogfood slices.
- 2026-04-09: Updated the standard planning-facing docs and bootstrap guidance so required follow-on routing is discoverable without re-deriving it from archived slices or tests.
