# Long-Horizon Doctrine Refresh Discipline

## Goal

- Make doctrine refresh a repeatable checked-in rule instead of an implicit maintainer habit.

## Non-Goals

- Re-argue the whole product direction.
- Turn doctrine pages into a shadow backlog.
- Expand this slice into extension-boundary design changes.

## Intent Continuity

- Larger intended outcome: Keep long-horizon product direction current without letting doctrine decay into stale narrative or hidden backlog.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Active Milestone

- Status: completed
- Scope: define the refresh discipline, add explicit review markers to the main doctrine pages, and align the doctrine-maintenance language across those pages.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Update the review portfolio and doctrine pages so doctrine refresh has one named lane and one consistent last-reviewed signal.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/reviews/`
- `docs/agent-os-capabilities.md`
- `docs/ecosystem-roadmap.md`
- `docs/maturity-model.md`

## Invariants

- Keep doctrine pages doctrinal, not queue-shaped.
- Prefer lightweight review metadata over process-heavy maintenance ceremony.
- Keep this slice focused on refresh discipline, not on reopening settled product decisions.

## Contract Decisions To Freeze

- Doctrine refresh should be expressed as a named review discipline rather than implicit maintainer folklore.
- Core doctrine pages should carry a lightweight `Last doctrinal review` marker.
- Concrete next work discovered during doctrine refresh still belongs in `ROADMAP.md`, not inside doctrine pages.

## Open Questions To Close

- No blocking open questions remain for this slice.

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`

## Completion Criteria

- The review portfolio includes a doctrine-refresh lane or equivalent explicit doctrine-review rule.
- The core doctrine pages carry consistent review markers and refresh guidance.
- The roadmap candidate is removed after archival.

## Execution Summary

- Outcome delivered: Doctrine refresh is now a named review discipline, the core doctrine pages carry lightweight doctrinal review markers, and the doctrine pages now share the same “refresh doctrine, route concrete work into ROADMAP” rule.
- Validation confirmed: `uv run pytest packages/planning/tests/test_installer.py`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap upgrade --target .`
- Follow-on routed to: none
- Resume from: archive this slice, then promote `Extension-boundary readiness review`

## Drift Log

- 2026-04-10: Promoted from `ROADMAP.md` after the doctrine consolidation pass left refresh discipline as explicit remaining work.
