# Archive Cleanup Heuristic Tuning

## Goal

- Tighten the archive follow-up heuristic so it only flags genuine stale thread residue in `ROADMAP.md`, not generic planning language.

## Non-Goals

- Remove roadmap follow-up guidance from `archive-plan`.
- Expand this into a broad semantic diff or NLP system.
- Change the planning contract outside the narrow archive-followup behavior.

## Active Milestone

- Status: completed
- Scope: reproduced the false-positive archive-followup case, tuned the roadmap matching logic, and proved the narrower behavior with focused tests.
- Ready: false
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed execplan now that the narrowed heuristic has passed verification.

## Blockers

- None.

## Touched Paths

- `src/repo_planning_bootstrap/`
- `tests/`
- `README.md`
- `docs/execplans/README.md`

## Invariants

- `archive-plan` should still warn when roadmap text genuinely keeps an archived thread sounding active.
- Archive cleanup remains explicit and file-native.
- Generic terms like `promotion`, `rules`, or shared planning vocabulary should not on their own count as stale thread residue.
- The helper should stay understandable from its result output alone.

## Validation Commands

- `uv run pytest`
- `uv run ruff check .`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-planning-bootstrap doctor --target .`

## Completion Criteria

- The self-hosted false-positive archive-followup case no longer warns.
- The archive helper still warns when a roadmap active-handoff line clearly references the archived thread.
- Tests cover both the narrowed false-positive case and the preserved true-positive case.

## Drift Log

- 2026-04-05: Plan created after a self-hosted archive run showed the roadmap follow-up heuristic still overmatching generic planning language.
- 2026-04-05: Narrowed the roadmap follow-up matcher to `Active Handoff` so generic planning vocabulary elsewhere in `ROADMAP.md` does not count as stale thread residue.
- 2026-04-05: Self-refresh dogfooding after the milestone surfaced a separate payload-hygiene issue: generated `__pycache__` content is still being picked up by the packaged payload.
