# Maintainer-Surface Consistency Hardening

## Goal

- Restore trust in maintainer-facing contract surfaces by aligning the documented source/payload/root-install boundary path, the actual maintainer check wiring, and the canonical file references that agents are told to trust during startup.

## Non-Goals

- Redesign the whole planning checker stack.
- Expand the scope into unrelated memory or orchestrator work.
- Add new review modes beyond what is needed to close this maintainer-contract gap.

## Active Milestone

- Status: completed
- Scope: restore the missing `docs/source-payload-operational-install.md` path or its documented equivalent, make `make maintainer-surfaces` and the command docs accurately reflect what the root wrapper actually checks, and validate the resulting contract with the narrow maintainer lanes.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and archived after the boundary guide, aggregate maintainer wrapper, and narrow maintainer validation lane all passed.

## Blockers

- None.

## Touched Paths

- `docs/`
- `scripts/check/`
- `.agentic-workspace/planning/scripts/check/`
- `TODO.md`
- `ROADMAP.md`

## Invariants

- Maintainer-facing docs must not point to missing canonical files.
- Root maintainer wrappers must not overclaim enforcement beyond the checks they actually run.
- Source, payload, and operational-install boundaries stay explicit rather than being folded into vague lifecycle wording.

## Validation Commands

- `uv run python scripts/check/check_maintainer_surfaces.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`

## Completion Criteria

- The startup path and maintainer docs point to an existing canonical source/payload/root-install boundary surface.
- The documented purpose of `make maintainer-surfaces` matches the real root wrapper behavior.
- The maintainer-surface and planning-surface checks pass without boundary-contract drift warnings.

## Drift Log

- 2026-04-08: Promoted after dogfooding exposed that `AGENTS.md` still referenced a missing source/payload/root-install doc while `docs/maintainer-commands.md` already claimed the maintainer lane enforced that boundary contract.
- 2026-04-08: Completed after restoring the missing boundary guide, making the direct maintainer wrapper aggregate boundary warnings when available, and passing the maintainer-surface validation lane.
