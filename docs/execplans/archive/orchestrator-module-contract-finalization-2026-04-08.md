# Orchestrator Module-Contract Finalization

## Goal

- Make the internal workspace/module contract generic enough that future first-party modules can be added without scattered orchestrator special-casing around ordering, preset membership, startup guidance, and root-surface cleanup rules.

## Non-Goals

- Open the extension boundary to third-party modules.
- Design the full plugin-ready capability contract.
- Add a new module family.

## Active Milestone

- Status: completed
- Scope: move first-party selection and root-guidance metadata into module-owned descriptors, keep the workspace layer thin, and lock the generic contract with root CLI tests.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and archived after the root orchestrator selected modules, rendered root guidance, and cleaned root AGENTS pointer blocks from descriptor metadata instead of separate planning/memory globals.

## Blockers

- None.

## Touched Paths

- `src/agentic_workspace/`
- `tests/`
- `docs/`
- `TODO.md`
- `ROADMAP.md`

## Invariants

- The workspace layer remains a thin orchestrator over package-owned lifecycle logic.
- First-party module metadata should live with the module descriptor instead of separate orchestrator globals.
- The extension boundary stays closed until a later plugin-ready contract defines public capability and compatibility terms.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py tests/test_workspace_lifecycle.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- Module ordering and preset membership are derived from module descriptors rather than global planning/memory tables.
- Root `AGENTS.md` composition uses descriptor-provided startup guidance instead of hardcoded planning/memory branches.
- Root workspace tests lock the new descriptor-owned contract.

## Drift Log

- 2026-04-08: Promoted after roadmap review showed the remaining orchestrator gap was no longer public UX but the internal dependence on separate planning/memory globals and branches for selection and root guidance.
- 2026-04-08: Completed after moving ordering, presets, startup guidance, and root cleanup rules into module descriptors and updating root workspace tests to assert the generic contract.
