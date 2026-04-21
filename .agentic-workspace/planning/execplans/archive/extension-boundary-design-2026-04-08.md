# Extension Boundary Design

## Goal

- Define the current extension boundary explicitly so the repo is honest about what is first-party-only today, what the workspace layer may assume about modules, and what must be true before any external module or plugin contract is treated as supported.

## Non-Goals

- Ship a third-party plugin API.
- Add dynamic module loading.
- Rework the existing first-party registry model.

## Active Milestone

- Status: completed
- Scope: add a canonical extension-boundary doc, align the main architecture/chooser surfaces to it, and keep the contract first-party-only until the stated readiness gates are met.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and archived after the canonical extension-boundary doc landed and the main public docs pointed at it.

## Blockers

- None.

## Touched Paths

- `docs/`
- `README.md`
- `docs/which-package.md`
- `TODO.md`
- `ROADMAP.md`

## Invariants

- The workspace layer stays thin and first-party-scoped.
- The doc must be honest about unsupported external extension today.
- Readiness gates for a public extension contract stay explicit and testable.

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- A canonical doc defines the current extension boundary and the readiness gates for future external extension.
- Public docs that mention composition or future modules point at that canonical boundary instead of leaving it implicit.
- Planning surfaces remain clean after promotion and completion.

## Drift Log

- 2026-04-08: Promoted after the workspace-first and composition-contract slices made the first-party contract explicit enough that the remaining ambiguity was the absence of one honest public statement about external extension support.
- 2026-04-08: Completed after adding the canonical extension-boundary doc and aligning the main public docs to it.
