# Module Registry Capability Model

## Goal

- Turn the now-explicit first-party module contract into a queryable registry-style model so the workspace layer can enumerate installed modules and lifecycle capabilities without re-encoding that knowledge across commands.

## Non-Goals

- Publish a third-party plugin API yet.
- Add new lifecycle verbs.
- Blur module ownership by moving package semantics into the root tool.

## Active Milestone

- Status: completed
- Scope: make first-party module metadata discoverable enough that the workspace layer can enumerate capabilities and lifecycle support from registry-like structures instead of only internal descriptor assembly.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and move the compatibility-policy milestone into active execution.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- .agentic-workspace/planning/execplans/
- src/
- tests/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- The registry model must stay internal and first-party scoped until the extension boundary is intentionally designed.
- The workspace layer must enumerate module capabilities without becoming the owner of module semantics.
- Queryable module metadata should reduce repeated orchestration knowledge instead of adding parallel sources of truth.
- Planning and memory must remain independently meaningful and selectively adoptable.
- Validation should prove clearer enumeration and lifecycle reporting, not just new metadata fields.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py
- uv run python scripts/check/check_planning_surfaces.py

## Completion Criteria

- First-party module metadata is explicit enough that the workspace layer can enumerate capabilities and lifecycle support from one narrow internal model.
- Root commands rely less on hand-maintained module lists and branching.
- The resulting registry shape is still clearly internal and does not pretend to be the final public plugin contract.
- Planning surfaces stay compact while the active tranche remains bounded.

## Drift Log

- 2026-04-06: Promoted after the first-party module contract tranche made descriptor metadata, owned surfaces, generated artifacts, and descriptor construction explicit enough that the next orchestration gap is discoverability rather than hidden contract shape.
- 2026-04-06: Milestone complete: the root CLI now exposes a registry-style module view, target-aware installation state, and registry snapshots in lifecycle reports, and the corresponding tests cover the new reporting shape.