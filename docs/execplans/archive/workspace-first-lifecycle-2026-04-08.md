# Workspace-First Lifecycle

## Goal

- Make `agentic-workspace` the normal public lifecycle entrypoint for memory-only, planning-only, and combined installs through the existing generic module contract, while keeping module lifecycle logic package-local and preserving package CLIs as advanced/package-local paths.

## Non-Goals

- Redesign the orchestrator or replace the existing module descriptor model.
- Build a third-party plugin system.
- Remove direct module CLIs.

## Active Milestone

- Status: completed
- Scope: add the root prompt surface, tighten the public docs contract around workspace-first lifecycle use, and validate that the orchestrator still stays thin while routing module-specific work back into the packages.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and archived after the root prompt lane, workspace-first docs pass, and root workspace validation lane all passed.

## Blockers

- None.

## Touched Paths

- `src/agentic_workspace/`
- `tests/`
- `README.md`
- `docs/`
- `packages/memory/`
- `packages/planning/`

## Invariants

- The orchestrator remains thin and generic; module-specific lifecycle implementation stays package-local.
- Memory and planning remain selectively adoptable through workspace presets as well as package-local paths.
- Direct module CLIs remain available for maintainers, package-local workflows, and advanced debugging, but they no longer carry the normal public lifecycle contract.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py tests/test_workspace_lifecycle.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- The workspace CLI exposes a public prompt lane for lifecycle handoff work.
- Root and package docs consistently present `agentic-workspace` as the normal public lifecycle entrypoint for all supported module selections.
- The remaining docs keep package-local CLIs framed as advanced or package-local rather than the default repo-adopter path.

## Drift Log

- 2026-04-08: Promoted from GitHub issue `#7` after the orchestrator, registry, and module contract already existed but the public lifecycle contract still underclaimed the workspace layer and left the root CLI without an explicit prompt lane.
- 2026-04-08: Completed after adding the root `prompt` surface, routing root and package docs through workspace presets as the normal public path, and keeping package CLIs framed as advanced/package-local workflows.
