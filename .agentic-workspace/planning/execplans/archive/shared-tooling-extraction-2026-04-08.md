# Shared Tooling Extraction

## Goal

- Resolve the shared-tooling candidate by defining when the correct response is a single managed source, when it is a small internal helper extraction, and when broad shared-tooling extraction should still be deferred.

## Non-Goals

- Create a new top-level package.
- Generalize all checks and renderers behind one abstraction layer.
- Rework memory and planning tooling into one common engine.

## Active Milestone

- Status: completed
- Scope: codify the post-composition rule for shared tooling, tighten the docs that govern extraction, and leave the roadmap with only the remaining memory candidate.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and archived after the extraction rule landed in canonical docs and the planning surfaces passed cleanly.

## Blockers

- None.

## Touched Paths

- `docs/`
- `TODO.md`
- `ROADMAP.md`

## Invariants

- Shared tooling should be extracted only when it lowers cost more than it adds abstraction.
- A single managed source is preferred over a new helper layer when only one contract family owns the behavior.
- The workspace layer must not become a dumping ground for module-internal helper logic.

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- Canonical docs define the decision rule for managed-source reuse versus helper extraction versus broader shared-tooling extraction.
- The roadmap no longer carries a vague shared-tooling candidate once that rule is explicit.
- Planning surfaces remain clean after promotion and completion.

## Drift Log

- 2026-04-08: Promoted after composition hardening showed the immediate duplication problem was better solved by one managed source than by a new broad helper layer, but the repo still lacked one explicit rule for making that choice again.
- 2026-04-08: Completed after documenting the shared-tooling decision rule in the canonical boundary and integration docs.
