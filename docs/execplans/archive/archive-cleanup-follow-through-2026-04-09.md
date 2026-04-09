# Archive Cleanup Follow-Through

## Goal

- Make `archive-plan --apply-cleanup` handle the normal active TODO pointer to the plan being archived, so archive cleanup works for the repo's standard active queue shape without manual pre-cleanup.

## Non-Goals

- Do not make archive cleanup rewrite unrelated TODO residue.
- Do not relax fail-closed behavior for unrelated active references or ambiguous queue state.
- Do not expand this slice into broader TODO-shape normalization.

## Active Milestone

- ID: archive-cleanup-follow-through
- Status: completed
- Scope: Teach archive cleanup to remove or rewrite the plan's own TODO pointer before blocking on it, add regression coverage, and refresh the root install from the updated planning payload.
- Ready: false
- Blocked: none
- optional_deps: none

Keep one active milestone by default.
Keep branch-local progress, blockers, and next-step state here rather than in durable docs or broad summaries.

## Immediate Next Action

- Archive this completed plan and clear the active queue residue.

## Blockers

- None.

## Touched Paths

- `packages/planning/src/repo_planning_bootstrap/installer.py`
- `packages/planning/tests/test_installer.py`

Keep this as a scope guard, not a broad file inventory.
Avoid large hand-maintained tables in active plans; compact bullets are easier to merge.

## Invariants

- `archive-plan --apply-cleanup` should stay explicit and conservative.
- The plan's own TODO pointer should not block cleanup when the user already asked for cleanup.
- Unrelated residue should still fail closed or surface as explicit follow-up.

Keep invariants contract-shaped and brief.

## Validation Commands

- `uv run pytest packages/planning/tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`

## Completion Criteria

- Archive cleanup removes the normal active TODO pointer to the plan being archived.
- Regression coverage proves the cleaned active-pointer case.
- Root install is refreshed from the updated planning payload.
- The plan archives without manual TODO pre-cleanup.

## Drift Log

- 2026-04-09: Promoted from the roadmap after dogfooding showed that archive cleanup still failed on the normal active TODO pointer shape.
- 2026-04-09: Completed by teaching archive cleanup to remove the plan's own TODO pointer, restoring the default Action hint when the queue empties, and proving the behavior with a regression test.
