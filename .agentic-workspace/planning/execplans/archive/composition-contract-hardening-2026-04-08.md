# Composition Contract Hardening

## Goal

- Tighten the internal workspace composition contract so shared orchestration behavior lives in one managed source, lifecycle wrappers stay thin, and future module addition remains generic instead of accumulating per-wrapper drift.

## Non-Goals

- Design the public plugin boundary.
- Add new module families.
- Redesign the workspace CLI lifecycle UX.

## Active Milestone

- Status: completed
- Scope: move the aggregate maintainer-surface composition behavior into one canonical managed source, restore thin wrapper behavior at root and package edges, and document the resulting orchestrator/module seam.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and archived after the canonical managed checker, thin wrapper mirrors, and maintainer validation lane all passed.

## Blockers

- None.

## Touched Paths

- `scripts/check/`
- `.agentic-workspace/planning/scripts/check/`
- `packages/planning/`
- `docs/`
- `tests/`

## Invariants

- Shared composition behavior must have one canonical managed source.
- The workspace layer stays thin and does not absorb module-specific domain policy.
- Root and package wrappers stay replaceable mirrors of the managed source rather than parallel logic owners.

## Validation Commands

- `uv run pytest tests/test_maintainer_surfaces.py`
- `cd packages/planning && uv run pytest tests/test_installer.py`
- `make maintainer-surfaces`

## Completion Criteria

- Maintainer-surface composition logic exists in one managed source.
- Root and shipped wrapper copies delegate instead of re-owning the composition behavior.
- Maintainer validation still passes across root and package payload paths.

## Drift Log

- 2026-04-08: Promoted after the maintainer-surface hardening slice proved the aggregate wrapper contract was right but also exposed duplicated composition logic across root, source, and bootstrap copies.
- 2026-04-08: Completed after moving the aggregate maintainer logic into the managed planning checker and returning outward wrappers to thin delegation.
