# Archive Reference Cleanup

## Goal

- Design and implement a file-native follow-up to `archive-plan` that helps compress stale active-sounding references after a plan is archived.

## Non-Goals

- Broaden this into a full lifecycle manager or hidden stateful workflow.
- Auto-edit unrelated planning surfaces without making the proposed changes explicit.
- Change the core planning schema or startup contract.

## Active Milestone

- Status: completed
- Scope: defined the assisted archive cleanup workflow, implemented the smallest useful helper behavior, and proved it against the self-hosted repo.
- Ready: false
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed execplan now that the assisted cleanup workflow has passed verification.

## Blockers

- None.

## Touched Paths

- `src/repo_planning_bootstrap/`
- `scripts/check/`
- `tests/`
- `README.md`
- `docs/execplans/README.md`

## Invariants

- Archived plans must stay out of the active queue.
- Planning files remain the source of truth; helper commands may assist edits but must not create hidden state.
- Cleanup suggestions should stay explicit and reviewable when multiple surfaces might change.
- Memory remains optional and must not become the owner of archive cleanup state.

## Validation Commands

- `uv run pytest`
- `uv run ruff check .`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-planning-bootstrap doctor --target .`

## Completion Criteria

- The intended assisted archive cleanup behavior is captured in code and docs.
- The helper makes roadmap or TODO follow-up clearer without obscuring the resulting file changes.
- Tests cover the new assisted cleanup path and any added drift checks.

## Drift Log

- 2026-04-05: Plan created after dogfooding `archive-plan` surfaced a recurring manual follow-up step.
- 2026-04-05: Reduced scope to an explicit `--apply-cleanup` flow so archive assistance stays narrow and reviewable.
- 2026-04-05: Dogfooding showed the helper must still emit a suggested fix when cleanup is available but not requested.
- 2026-04-05: The promotion-linkage checker caught this follow-on thread until the roadmap carried the same signal language, which is useful feedback about how strict the cross-surface linkage currently feels in practice.
- 2026-04-05: Completed the assisted cleanup implementation, tests, docs, and self-hosted verification pass.
