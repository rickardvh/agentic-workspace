# Plugin-Ready Capability Contract

## Goal

- Define the next internal module contract layer in plugin-ready terms by making capabilities, lifecycle hooks, result-schema guarantees, and dependency/conflict metadata first-class in the workspace registry without opening external extension yet.

## Non-Goals

- Publish a third-party plugin API.
- Add dynamic module loading.
- Change package-local lifecycle ownership.

## Active Milestone

- Status: completed
- Scope: add explicit capability/dependency/conflict/result metadata to the first-party module descriptors and registry output, enforce the narrow dependency/conflict rules during selection, and document the resulting contract honestly as first-party-only.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and archived after the workspace registry exposed first-class capability, compatibility, and result-contract metadata and the selector enforced declared dependency/conflict rules.

## Blockers

- None.

## Touched Paths

- `src/agentic_workspace/`
- `tests/`
- `docs/`
- `TODO.md`
- `ROADMAP.md`

## Invariants

- The extension boundary stays closed while the contract is still first-party only.
- Capability and compatibility metadata should reduce interpretation cost, not create a speculative plugin API.
- Dependency or conflict rules should be enforced by the orchestrator once declared.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py tests/test_workspace_lifecycle.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- Module descriptors and registry output expose capabilities, dependency/conflict metadata, lifecycle hook expectations, and result-contract metadata.
- Module selection rejects declared dependency/conflict violations instead of relying on maintainer interpretation.
- Docs describe the contract as plugin-ready internal structure, not as supported third-party extension.

## Drift Log

- 2026-04-08: Promoted after descriptor-owned first-party metadata stopped the obvious orchestrator special-casing, leaving capability/dependency/result semantics as the next missing contract layer before any credible external extension work.
- 2026-04-08: Completed after the workspace registry and `modules` output exposed first-class capability, dependency/conflict, and result-contract metadata, and the selector began enforcing declared compatibility rules.
